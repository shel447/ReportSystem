"""统一对话应用服务，负责编排对话、模板实例与报告生成。"""

from __future__ import annotations

import copy
import json
import math
import re
from typing import Any

from ....infrastructure.ai.openai_compat import OpenAICompatGateway
from ....infrastructure.settings.system_settings import build_completion_provider_config, build_embedding_provider_config
from ....shared.kernel.errors import ConflictError, NotFoundError, ValidationError
from ...report_runtime.domain.services import (
    collect_instance_parameters,
    collect_template_parameters,
    instantiate_template_instance,
    merge_parameter_values,
    parameters_to_value_map,
    parameters_by_id,
    serialize_template_instance,
)


DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


class ConversationService:
    """拥有聊天接口协议与会话生命周期的应用服务。"""

    def __init__(
        self,
        *,
        conversation_repository,
        chat_repository,
        template_catalog_service,
        template_repository,
        runtime_service,
        parameter_option_service,
        db,
    ) -> None:
        self.conversation_repository = conversation_repository
        self.chat_repository = chat_repository
        self.template_catalog_service = template_catalog_service
        self.template_repository = template_repository
        self.runtime_service = runtime_service
        self.parameter_option_service = parameter_option_service
        self.db = db
        self.ai_gateway = OpenAICompatGateway()

    def list_sessions(self, *, user_id: str) -> list[dict[str, Any]]:
        """返回会话列表视图，仅包含最后一条消息预览。"""
        result = []
        for conversation in self.conversation_repository.list_all(user_id=user_id):
            messages = self.chat_repository.list_by_conversation(conversation.id, user_id=user_id)
            latest = messages[-1] if messages else None
            result.append(
                {
                    "conversationId": conversation.id,
                    "title": conversation.title or "未命名会话",
                    "status": conversation.status,
                    "updatedAt": conversation.updated_at.isoformat().replace("+00:00", "Z") if conversation.updated_at else None,
                    "lastMessagePreview": _message_preview(latest.content if latest else {}),
                }
            )
        return result

    def get_session(self, *, conversation_id: str, user_id: str) -> dict[str, Any]:
        """加载单个会话，并按顺序组装聊天消息流。"""
        conversation = self.conversation_repository.get(conversation_id, user_id=user_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        messages = self.chat_repository.list_by_conversation(conversation_id, user_id=user_id)
        return {
            "conversationId": conversation.id,
            "title": conversation.title,
            "status": conversation.status,
            "messages": [
                {
                    "chatId": row.id,
                    "role": row.role,
                    "content": row.content,
                    "action": row.action,
                    "meta": row.meta,
                    "createdAt": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
                }
                for row in messages
            ],
        }

    def delete_session(self, *, conversation_id: str, user_id: str) -> dict[str, Any]:
        if not self.conversation_repository.delete(conversation_id, user_id=user_id):
            raise NotFoundError("Conversation not found")
        return {"message": "deleted"}

    def fork_session(self, *, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """从历史聊天节点派生出一个新会话。"""
        source_conversation_id = str(data.get("source_conversation_id") or "").strip()
        source_chat_id = str(data.get("source_chat_id") or "").strip()
        source = self.conversation_repository.get(source_conversation_id, user_id=user_id)
        if source is None:
            raise NotFoundError("Source conversation not found")
        messages = self.chat_repository.list_by_conversation(source_conversation_id, user_id=user_id)
        target = next((row for row in messages if row.id == source_chat_id), None)
        if target is None:
            raise NotFoundError("Source chat not found")
        new_conversation = self.conversation_repository.create(conversation_id=None, user_id=user_id)
        self.chat_repository.append_message(
            conversation_id=new_conversation.id,
            user_id=user_id,
            role=target.role,
            content=target.content,
            action=target.action,
            meta={"forkedFrom": {"conversationId": source_conversation_id, "chatId": source_chat_id}},
        )
        new_conversation.title = source.title or _message_preview(target.content)
        self.conversation_repository.save(new_conversation)
        return {"conversationId": new_conversation.id}

    def send_message(self, *, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """分派公开的聊天指令契约。"""
        instruction = str(data.get("instruction") or "generate_report").strip() or "generate_report"
        if instruction == "extract_report_template":
            return self._extract_report_template(data=data, user_id=user_id)
        if instruction != "generate_report":
            raise ValidationError(f"Unsupported instruction: {instruction}")
        return self._generate_report(data=data, user_id=user_id)

    def _extract_report_template(self, *, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """将自由文本输入投影为模板导入预览结果。"""
        normalized = self.template_catalog_service.preview_import_template(data.get("question") or {})
        return {
            "conversationId": str(data.get("conversationId") or ""),
            "chatId": str(data.get("chatId") or ""),
            "status": "finished",
            "steps": [],
            "ask": None,
            "answer": {
                "answerType": "REPORT_TEMPLATE",
                "answer": {
                    "normalizedTemplate": normalized["normalizedTemplate"],
                    "warnings": normalized["warnings"],
                    "persisted": False,
                },
            },
            "errors": [],
            "requestId": data.get("requestId"),
            "timestamp": _epoch_ms(),
            "apiVersion": data.get("apiVersion") or "v1",
        }

    def _generate_report(self, *, data: dict[str, Any], user_id: str) -> dict[str, Any]:
        """围绕模板实例驱动报告对话状态机。"""
        conversation = self._ensure_conversation(data=data, user_id=user_id)
        user_chat = self.chat_repository.append_message(
            conversation_id=conversation.id,
            user_id=user_id,
            role="user",
            content={"question": str(data.get("question") or "")},
            chat_id=data.get("chatId"),
        )

        reply = data.get("reply") if isinstance(data.get("reply"), dict) else None
        current_instance = self.runtime_service.get_latest_template_instance(conversation_id=conversation.id, user_id=user_id)

        if reply and str(reply.get("type") or "") in {"fill_params", "confirm_params"}:
            # 结构化 reply 必须精确指向它所消费的 assistant 追问消息，不允许按最近一条 pending ask 猜测。
            source_chat_id = str(reply.get("sourceChatId") or "").strip()
            if not source_chat_id:
                raise ValidationError("reply.sourceChatId is required")
            if not self.chat_repository.mark_ask_replied(
                conversation_id=conversation.id,
                user_id=user_id,
                source_chat_id=source_chat_id,
            ):
                raise ValidationError("reply.sourceChatId must reference a pending ask in the same conversation")

        if reply and str(reply.get("type") or "") == "confirm_params":
            # 只有确认参数分支允许把当前模板实例冻结成报告，
            # 其它分支都必须继续停留在追问态推进收参流程。
            template_instance_payload = ((reply.get("reportContext") or {}).get("templateInstance")) if isinstance(reply.get("reportContext"), dict) else None
            if not isinstance(template_instance_payload, dict):
                raise ValidationError("confirm_params requires reportContext.templateInstance")
            template_id = str(template_instance_payload.get("templateId") or "").strip()
            template = self.template_catalog_service.get_template(template_id)
            missing = _missing_required_parameters(template=template, template_instance=template_instance_payload)
            if missing:
                missing_ids = ", ".join(str(item.get("id") or "") for item in missing)
                raise ValidationError(f"confirm_params requires all required parameters: {missing_ids}")
            persisted = self.runtime_service.persist_template_instance(
                _template_instance_from_payload(template_instance_payload, chat_id=user_chat.id, status="confirmed", capture_stage="confirm_params"),
                user_id=user_id,
            )
            assistant_chat_id = _random_id("chat")
            answer = self.runtime_service.generate_report_from_template_instance(
                template_instance_id=persisted["id"],
                user_id=user_id,
                source_conversation_id=conversation.id,
                source_chat_id=user_chat.id,
            )
            response = _chat_response(
                conversation_id=conversation.id,
                chat_id=assistant_chat_id,
                status="finished",
                ask=None,
                answer={"answerType": "REPORT", "answer": answer},
                request_id=data.get("requestId"),
                api_version=data.get("apiVersion"),
            )
            self._append_assistant_message(conversation_id=conversation.id, user_id=user_id, chat_id=assistant_chat_id, response=response)
            return response

        if current_instance:
            # 一旦模板实例已存在，后续每轮都必须更新同一个聚合，
            # 不能在消息流上再派生旁路状态。
            template_id = current_instance["templateId"]
            template = self.template_catalog_service.get_template(template_id)
            template_parameter_definitions = collect_template_parameters(template)
            current_instance_parameters = collect_instance_parameters(
                parameters=current_instance.get("parameters") or [],
                catalogs=current_instance.get("catalogs") or [],
            )
            merged_values = merge_parameter_values(
                parameter_definitions=template_parameter_definitions,
                current_values=parameters_to_value_map(current_instance_parameters),
                incoming_values=_reply_parameter_values_to_value_map(
                    (reply or {}).get("parameters"),
                    parameter_definitions=template_parameter_definitions,
                    current_parameters=current_instance_parameters,
                )
                if isinstance(reply, dict)
                else self._extract_parameter_values(template, str(data.get("question") or "")),
            )
            instance = instantiate_template_instance(
                instance_id=current_instance["id"],
                template=template,
                conversation_id=conversation.id,
                chat_id=user_chat.id,
                status="ready_for_confirmation",
                capture_stage="fill_params",
                revision=int(current_instance.get("revision") or 1) + 1,
                parameter_values=merged_values,
                current_parameters=current_instance_parameters,
                warnings=current_instance.get("warnings") or [],
                created_at=_parse_datetime(current_instance.get("createdAt")),
            )
            persisted = self.runtime_service.persist_template_instance(instance, user_id=user_id)
            assistant_chat_id = _random_id("chat")
            response = self._build_ask_response(conversation_id=conversation.id, chat_id=assistant_chat_id, template=template, template_instance=persisted, request_id=data.get("requestId"), api_version=data.get("apiVersion"))
            self._append_assistant_message(conversation_id=conversation.id, user_id=user_id, chat_id=assistant_chat_id, response=response)
            return response

        # 首轮先完成模板匹配，再用抽取值和默认值初始化第一版模板实例。
        template = self._match_template(str(data.get("question") or ""))
        initial_values = self._extract_parameter_values(template, str(data.get("question") or ""))
        instance = instantiate_template_instance(
            instance_id=_random_id("ti"),
            template=template,
            conversation_id=conversation.id,
            chat_id=user_chat.id,
            status="collecting_parameters",
            capture_stage="fill_params",
            revision=1,
            parameter_values=initial_values,
        )
        persisted = self.runtime_service.persist_template_instance(instance, user_id=user_id)
        if not conversation.title:
            conversation.title = template["name"]
            self.conversation_repository.save(conversation)
        assistant_chat_id = _random_id("chat")
        response = self._build_ask_response(
            conversation_id=conversation.id,
            chat_id=assistant_chat_id,
            template=template,
            template_instance=persisted,
            request_id=data.get("requestId"),
            api_version=data.get("apiVersion"),
        )
        self._append_assistant_message(conversation_id=conversation.id, user_id=user_id, chat_id=assistant_chat_id, response=response)
        return response

    def _ensure_conversation(self, *, data: dict[str, Any], user_id: str):
        conversation_id = str(data.get("conversationId") or "").strip()
        if conversation_id:
            existing = self.conversation_repository.get(conversation_id, user_id=user_id)
            if existing is None:
                raise NotFoundError("Conversation not found")
            return existing
        return self.conversation_repository.create(conversation_id=None, user_id=user_id)

    def _match_template(self, question: str) -> dict[str, Any]:
        """结合词法与向量信号选择最匹配的正式模板。"""
        templates = [self.template_catalog_service.serialize_detail(item) for item in self.template_repository.list_all()]
        if not templates:
            raise ValidationError("No report templates available")
        query_text = question.strip()
        if not query_text:
            return templates[0]

        scored = []
        query_embedding = self._embed_text(query_text)
        for template in templates:
            lexical = _lexical_score(query_text, template)
            semantic = _cosine_similarity(query_embedding, self._embed_text(_template_match_text(template))) if query_embedding else 0.0
            scored.append((lexical + semantic * 0.55, template))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _embed_text(self, text: str) -> list[float]:
        if not text.strip():
            return []
        try:
            config = build_embedding_provider_config(self.db)
        except Exception:
            return []
        try:
            return self.ai_gateway.create_embedding(config, [text])[0]
        except Exception:
            return []

    def _extract_parameter_values(self, template: dict[str, Any], question: str) -> dict[str, list[dict[str, Any]]]:
        """对用户文本执行轻量首轮参数抽取。"""
        parameter_values: dict[str, list[dict[str, Any]]] = {}
        question_text = question or ""
        for parameter in collect_template_parameters(template):
            param_id = str(parameter.get("id") or "").strip()
            input_type = str(parameter.get("inputType") or "")
            matched = None
            if input_type == "date":
                date_match = DATE_PATTERN.search(question_text)
                if date_match:
                    value = date_match.group(0)
                    matched = [{"label": value, "value": value, "query": value}]
            elif input_type == "enum":
                for option in list(parameter.get("options") or []):
                    label = str(option.get("label") or "")
                    value = str(option.get("value") or "")
                    if label and label in question_text or value and value in question_text:
                        matched = [copy_option(option)]
                        break
            elif input_type == "dynamic":
                source = str(parameter.get("source") or "").strip()
                try:
                    resolved = self.parameter_option_service.resolve(
                        user_id="default",
                        parameter_id=param_id,
                        source=source,
                        context_values=parameter_values,
                    )
                except Exception:
                    resolved = {"options": []}
                choices = []
                for option in list(resolved.get("options") or []):
                    label = str(option.get("label") or "")
                    value = str(option.get("value") or "")
                    if label and label in question_text or value and value in question_text:
                        choices.append(copy_option(option))
                        if not parameter.get("multi"):
                            break
                if choices:
                    matched = choices
            elif input_type == "free_text":
                if question_text.strip():
                    matched = [{"label": question_text.strip(), "value": question_text.strip(), "query": question_text.strip()}]

            if matched:
                parameter_values[param_id] = matched
        return merge_parameter_values(parameter_definitions=collect_template_parameters(template), current_values={}, incoming_values=parameter_values)

    def _build_ask_response(self, *, conversation_id: str, chat_id: str, template: dict[str, Any], template_instance: dict[str, Any], request_id: str | None, api_version: str | None) -> dict[str, Any]:
        """根据模板实例当前完整度直接构造下一轮追问。"""
        missing = _missing_required_parameters(template=template, template_instance=template_instance)
        if missing:
            next_parameter = missing[0]
            next_parameter_state = next(
                (
                    copy.deepcopy(parameter)
                    for parameter in collect_instance_parameters(
                        parameters=template_instance.get("parameters") or [],
                        catalogs=template_instance.get("catalogs") or [],
                    )
                    if str(parameter.get("id") or "") == str(next_parameter.get("id") or "")
                ),
                copy.deepcopy(next_parameter),
            )
            ask = {
                "status": "pending",
                "mode": "natural_language" if next_parameter.get("interactionMode") == "natural_language" else "form",
                "type": "fill_params",
                "title": "请补充报告参数",
                "text": f"请补充参数：{next_parameter.get('label')}",
                "parameters": [next_parameter_state],
                "reportContext": {"templateInstance": template_instance},
            }
        else:
            ask = {
                "status": "pending",
                "mode": "form",
                "type": "confirm_params",
                "title": "请确认报告诉求",
                "text": "请确认报告诉求后开始生成。",
                "parameters": collect_instance_parameters(
                    parameters=template_instance.get("parameters") or [],
                    catalogs=template_instance.get("catalogs") or [],
                ),
                "reportContext": {"templateInstance": template_instance},
            }
        return _chat_response(
            conversation_id=conversation_id,
            chat_id=chat_id,
            status="waiting_user",
            ask=ask,
            answer=None,
            request_id=request_id,
            api_version=api_version,
        )

    def _append_assistant_message(self, *, conversation_id: str, user_id: str, chat_id: str, response: dict[str, Any]) -> None:
        """持久化统一聊天响应，确保聊天与报告视图都可重放。"""
        self.chat_repository.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content={"response": response},
            action={"type": "chat_response"},
            meta={"status": response.get("status")},
            chat_id=chat_id,
        )


def _message_preview(content: dict[str, Any]) -> str:
    if not isinstance(content, dict):
        return ""
    if isinstance(content.get("question"), str):
        return str(content["question"])[:80]
    response = content.get("response")
    if isinstance(response, dict):
        ask = response.get("ask")
        if isinstance(ask, dict):
            return str(ask.get("title") or ask.get("text") or "")[:80]
    return ""


def _chat_response(
    *,
    conversation_id: str,
    chat_id: str,
    status: str,
    ask: dict[str, Any] | None,
    answer: dict[str, Any] | None,
    request_id: str | None,
    api_version: str | None,
) -> dict[str, Any]:
    return {
        "conversationId": conversation_id,
        "chatId": chat_id,
        "status": status,
        "steps": [],
        "ask": ask,
        "answer": answer,
        "errors": [],
        "requestId": request_id,
        "timestamp": _epoch_ms(),
        "apiVersion": api_version or "v1",
    }


def _template_match_text(template: dict[str, Any]) -> str:
    parts = [
        str(template.get("name") or ""),
        str(template.get("description") or ""),
        str(template.get("category") or ""),
    ]
    for parameter in list(template.get("parameters") or []):
        parts.append(str(parameter.get("label") or parameter.get("id") or ""))
    for catalog in list(template.get("catalogs") or []):
        parts.extend(_catalog_match_text(catalog))
    return "\n".join([part for part in parts if part])


def _lexical_score(question: str, template: dict[str, Any]) -> float:
    lowered = question.lower()
    score = 0.0
    for part in [template.get("name"), template.get("category"), template.get("description")]:
        text = str(part or "").lower()
        if text and text in lowered:
            score += 1.0
    return score


def _catalog_match_text(catalog: dict[str, Any]) -> list[str]:
    parts = [str(catalog.get("title") or "")]
    for sub_catalog in list(catalog.get("subCatalogs") or []):
        parts.extend(_catalog_match_text(sub_catalog))
    for section in list(catalog.get("sections") or []):
        outline = section.get("outline") or {}
        parts.append(str(outline.get("requirement") or ""))
    return [part for part in parts if part]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _missing_required_parameters(*, template: dict[str, Any], template_instance: dict[str, Any]) -> list[dict[str, Any]]:
    values = parameters_to_value_map(
        collect_instance_parameters(
            parameters=template_instance.get("parameters") or [],
            catalogs=template_instance.get("catalogs") or [],
        )
    )
    missing = []
    for parameter in collect_template_parameters(template):
        if not parameter.get("required"):
            continue
        if not list(values.get(parameter.get("id")) or []):
            missing.append(parameter)
    return missing


def _template_instance_from_payload(payload: dict[str, Any], *, chat_id: str, status: str, capture_stage: str):
    from ...report_runtime.domain.models import TemplateInstance

    parameter_confirmation = payload.get("parameterConfirmation") or {"missingParameterIds": [], "confirmed": False}
    if capture_stage in {"confirm_params", "generate_report", "report_ready"}:
        parameter_confirmation = {
            **parameter_confirmation,
            "missingParameterIds": [],
            "confirmed": True,
            "confirmedAt": parameter_confirmation.get("confirmedAt") or _iso_timestamp(),
        }

    return TemplateInstance(
        id=str(payload.get("id") or ""),
        schema_version=str(payload.get("schemaVersion") or "template-instance.vNext-draft"),
        template_id=str(payload.get("templateId") or ""),
        template=copy.deepcopy(payload.get("template") or {}),
        conversation_id=str(payload.get("conversationId") or ""),
        chat_id=chat_id,
        status=status,
        capture_stage=capture_stage,
        revision=int(payload.get("revision") or 1),
        parameters=payload.get("parameters") or [],
        parameter_confirmation=parameter_confirmation,
        catalogs=payload.get("catalogs") or [],
        warnings=payload.get("warnings") or [],
        created_at=_parse_datetime(payload.get("createdAt")),
        updated_at=_parse_datetime(payload.get("updatedAt")),
    )


def copy_option(option: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": option.get("label"),
        "value": option.get("value"),
        "query": option.get("query"),
    }


def _reply_parameter_values_to_value_map(
    payload: Any,
    *,
    parameter_definitions: list[dict[str, Any]],
    current_parameters: list[dict[str, Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        return {}

    definition_by_id = parameters_by_id(parameter_definitions)
    current_by_id = parameters_by_id(current_parameters)
    resolved: dict[str, list[dict[str, Any]]] = {}
    for param_id, raw_values in payload.items():
        normalized_id = str(param_id or "").strip()
        if not normalized_id:
            continue
        definition = current_by_id.get(normalized_id) or definition_by_id.get(normalized_id)
        if definition is None:
            raise ValidationError(f"reply.parameters contains unknown parameter id: {normalized_id}")
        if not isinstance(raw_values, list):
            raise ValidationError(f"reply.parameters.{normalized_id} must be an array")
        resolved[normalized_id] = [_scalar_to_parameter_value(item, definition=definition) for item in raw_values]
    return resolved


def _scalar_to_parameter_value(raw_value: Any, *, definition: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    for field in ("options", "values", "defaultValue"):
        if isinstance(definition.get(field), list):
            candidates.extend(list(definition.get(field) or []))
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if raw_value in {candidate.get("label"), candidate.get("value"), candidate.get("query")}:
            return copy_option(candidate)
    return {"label": raw_value, "value": raw_value, "query": raw_value}


def _random_id(prefix: str) -> str:
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _epoch_ms() -> int:
    import time
    return int(time.time() * 1000)


def _iso_timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: Any):
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        from datetime import datetime

        return datetime.fromisoformat(candidate)
    except ValueError:
        return None
