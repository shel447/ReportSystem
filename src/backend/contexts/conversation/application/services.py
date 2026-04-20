"""统一对话应用服务，负责编排对话、模板实例与报告生成。"""

from __future__ import annotations

import copy
import math
import re
from typing import Any

from ....infrastructure.ai.openai_compat import OpenAICompatGateway
from ....infrastructure.settings.system_settings import build_completion_provider_config, build_embedding_provider_config
from ....shared.kernel.errors import NotFoundError, ValidationError
from ...report_runtime.application.models import DocumentView, GenerationProgressView, ReportAnswerView
from ...report_runtime.domain.models import ReportInstance, TemplateInstance, report_dsl_from_dict, template_instance_from_dict
from ...report_runtime.domain.services import (
    collect_instance_parameters,
    collect_template_parameters,
    instantiate_template_instance,
    merge_parameter_values,
    parameters_to_value_map,
    parameters_by_id,
)
from ...template_catalog.application.models import TemplateImportPreview
from ...template_catalog.domain.models import (
    Parameter,
    ParameterValue,
    ReportTemplate,
    parameter_from_dict,
    report_template_from_dict,
)
from ...report_runtime.domain.services import (
    serialize_template_instance,
)
from .models import (
    ChatAnswerEnvelope,
    ChatAsk,
    ChatCommand,
    ChatResponse,
    DeleteResult,
    ConversationMessageAction,
    ConversationMessageContent,
    ConversationMessageMeta,
    ForkSessionCommand,
    ForkSessionResult,
    SessionDetail,
    SessionMessage,
    SessionSummary,
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

    def list_sessions(self, *, user_id: str) -> list[SessionSummary]:
        """返回会话列表视图，仅包含最后一条消息预览。"""
        result = []
        for conversation in self.conversation_repository.list_all(user_id=user_id):
            messages = self.chat_repository.list_by_conversation(conversation.id, user_id=user_id)
            latest = messages[-1] if messages else None
            result.append(
                SessionSummary(
                    conversation_id=conversation.id,
                    title=conversation.title or "未命名会话",
                    status=conversation.status,
                    updated_at=conversation.updated_at.isoformat().replace("+00:00", "Z") if conversation.updated_at else None,
                    last_message_preview=_message_preview(_message_content_from_row(latest) if latest else ConversationMessageContent()),
                )
            )
        return result

    def get_session(self, *, conversation_id: str, user_id: str) -> SessionDetail:
        """加载单个会话，并按顺序组装聊天消息流。"""
        conversation = self.conversation_repository.get(conversation_id, user_id=user_id)
        if conversation is None:
            raise NotFoundError("Conversation not found")
        messages = self.chat_repository.list_by_conversation(conversation_id, user_id=user_id)
        return SessionDetail(
            conversation_id=conversation.id,
            title=conversation.title,
            status=conversation.status,
            messages=[
                SessionMessage(
                    chat_id=row.id,
                    role=row.role,
                    content=_message_content_from_row(row),
                    action=_message_action_from_row(row),
                    meta=_message_meta_from_row(row),
                    created_at=row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else None,
                )
                for row in messages
            ],
        )

    def delete_session(self, *, conversation_id: str, user_id: str) -> DeleteResult:
        if not self.conversation_repository.delete(conversation_id, user_id=user_id):
            raise NotFoundError("Conversation not found")
        return DeleteResult(message="deleted")

    def fork_session(self, *, data: ForkSessionCommand, user_id: str) -> ForkSessionResult:
        """从历史聊天节点派生出一个新会话。"""
        source_conversation_id = str(data.source_conversation_id or "").strip()
        source_chat_id = str(data.source_chat_id or "").strip()
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
            content=_message_content_from_row(target),
            action=_message_action_from_row(target),
            meta=ConversationMessageMeta(status=None, forked_from={"conversationId": source_conversation_id, "chatId": source_chat_id}),
        )
        new_conversation.title = source.title or _message_preview(_message_content_from_row(target))
        self.conversation_repository.save(new_conversation)
        return ForkSessionResult(conversation_id=new_conversation.id)

    def send_message(self, *, data: ChatCommand, user_id: str) -> ChatResponse:
        """分派公开的聊天指令契约。"""
        instruction = str(data.instruction or "generate_report").strip() or "generate_report"
        if instruction == "extract_report_template":
            return self._extract_report_template(data=data, user_id=user_id)
        if instruction != "generate_report":
            raise ValidationError(f"Unsupported instruction: {instruction}")
        return self._generate_report(data=data, user_id=user_id)

    def _extract_report_template(self, *, data: ChatCommand, user_id: str) -> ChatResponse:
        """将自由文本输入投影为模板导入预览结果。"""
        normalized = self.template_catalog_service.preview_import_template(data.question or {})
        return ChatResponse(
            conversation_id=data.conversation_id or "",
            chat_id=data.chat_id or "",
            status="finished",
            ask=None,
            answer=ChatAnswerEnvelope(answer_type="REPORT_TEMPLATE", report_template_preview=normalized),
            errors=[],
            request_id=data.request_id,
            timestamp=_epoch_ms(),
            api_version=data.api_version or "v1",
        )

    def _generate_report(self, *, data: ChatCommand, user_id: str) -> ChatResponse:
        """围绕模板实例驱动报告对话状态机。"""
        conversation = self._ensure_conversation(data=data, user_id=user_id)
        user_chat = self.chat_repository.append_message(
            conversation_id=conversation.id,
            user_id=user_id,
            role="user",
            content=ConversationMessageContent(question=str(data.question or "")),
            chat_id=data.chat_id,
        )

        reply = data.reply
        current_instance = self.runtime_service.get_latest_template_instance(conversation_id=conversation.id, user_id=user_id)

        if reply and str(reply.type or "") in {"fill_params", "confirm_params"}:
            # 结构化 reply 必须精确指向它所消费的 assistant 追问消息，不允许按最近一条 pending ask 猜测。
            source_chat_id = str(reply.source_chat_id or "").strip()
            if not source_chat_id:
                raise ValidationError("reply.sourceChatId is required")
            if not self.chat_repository.mark_ask_replied(
                conversation_id=conversation.id,
                user_id=user_id,
                source_chat_id=source_chat_id,
            ):
                raise ValidationError("reply.sourceChatId must reference a pending ask in the same conversation")

        if reply and str(reply.type or "") == "confirm_params":
            # 只有确认参数分支允许把当前模板实例冻结成报告，
            # 其它分支都必须继续停留在追问态推进收参流程。
            template_instance_payload = reply.template_instance
            if template_instance_payload is None:
                raise ValidationError("confirm_params requires reportContext.templateInstance")
            template_id = str(template_instance_payload.template_id or "").strip()
            template = self.template_catalog_service.get_template(template_id)
            missing = _missing_required_parameters(template=template, template_instance=template_instance_payload)
            if missing:
                missing_ids = ", ".join(item.id for item in missing)
                raise ValidationError(f"confirm_params requires all required parameters: {missing_ids}")
            persisted = self.runtime_service.persist_template_instance(
                _template_instance_from_payload(template_instance_payload, chat_id=user_chat.id, status="confirmed", capture_stage="confirm_params"),
                user_id=user_id,
            )
            assistant_chat_id = _random_id("chat")
            answer = self.runtime_service.generate_report_from_template_instance(
                template_instance_id=persisted.id,
                user_id=user_id,
                source_conversation_id=conversation.id,
                source_chat_id=user_chat.id,
            )
            response = _chat_response(
                conversation_id=conversation.id,
                chat_id=assistant_chat_id,
                status="finished",
                ask=None,
                answer=ChatAnswerEnvelope(answer_type="REPORT", report=answer),
                request_id=data.request_id,
                api_version=data.api_version,
            )
            self._append_assistant_message(conversation_id=conversation.id, user_id=user_id, chat_id=assistant_chat_id, response=response)
            return response

        if current_instance:
            # 一旦模板实例已存在，后续每轮都必须更新同一个聚合，
            # 不能在消息流上再派生旁路状态。
            current_instance_model = copy.deepcopy(current_instance)
            template_id = current_instance_model.template_id
            template = self.template_catalog_service.get_template(template_id)
            template_parameter_definitions = collect_template_parameters(template)
            current_instance_parameters = collect_instance_parameters(
                parameters=current_instance_model.parameters,
                catalogs=current_instance_model.catalogs,
            )
            merged_values = merge_parameter_values(
                parameter_definitions=template_parameter_definitions,
                current_values=parameters_to_value_map(current_instance_parameters),
                incoming_values=_reply_parameter_values_to_value_map(
                    (reply.parameters if reply else None),
                    parameter_definitions=template_parameter_definitions,
                    current_parameters=current_instance_parameters,
                )
                if reply is not None
                else self._extract_parameter_values(template, str(data.question or "")),
            )
            instance = instantiate_template_instance(
                instance_id=current_instance_model.id,
                template=template,
                conversation_id=conversation.id,
                chat_id=user_chat.id,
                status="ready_for_confirmation",
                capture_stage="fill_params",
                revision=int(current_instance_model.revision or 1) + 1,
                parameter_values=merged_values,
                current_parameters=current_instance_parameters,
                warnings=current_instance_model.warnings,
                created_at=current_instance_model.created_at,
            )
            persisted = self.runtime_service.persist_template_instance(instance, user_id=user_id)
            assistant_chat_id = _random_id("chat")
            response = self._build_ask_response(conversation_id=conversation.id, chat_id=assistant_chat_id, template=template, template_instance=persisted, request_id=data.request_id, api_version=data.api_version)
            self._append_assistant_message(conversation_id=conversation.id, user_id=user_id, chat_id=assistant_chat_id, response=response)
            return response

        # 首轮先完成模板匹配，再用抽取值和默认值初始化第一版模板实例。
        template = self._match_template(str(data.question or ""))
        initial_values = self._extract_parameter_values(template, str(data.question or ""))
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
            conversation.title = template.name
            self.conversation_repository.save(conversation)
        assistant_chat_id = _random_id("chat")
        response = self._build_ask_response(
            conversation_id=conversation.id,
            chat_id=assistant_chat_id,
            template=template,
            template_instance=persisted,
            request_id=data.request_id,
            api_version=data.api_version,
        )
        self._append_assistant_message(conversation_id=conversation.id, user_id=user_id, chat_id=assistant_chat_id, response=response)
        return response

    def _ensure_conversation(self, *, data: ChatCommand, user_id: str):
        conversation_id = str(data.conversation_id or "").strip()
        if conversation_id:
            existing = self.conversation_repository.get(conversation_id, user_id=user_id)
            if existing is None:
                raise NotFoundError("Conversation not found")
            return existing
        return self.conversation_repository.create(conversation_id=None, user_id=user_id)

    def _match_template(self, question: str) -> ReportTemplate:
        """结合词法与向量信号选择最匹配的正式模板。"""
        templates = list(self.template_repository.list_all())
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

    def _extract_parameter_values(self, template: ReportTemplate, question: str) -> dict[str, list[ParameterValue]]:
        """对用户文本执行轻量首轮参数抽取。"""
        template_model = template
        parameter_values: dict[str, list[ParameterValue]] = {}
        question_text = question or ""
        for parameter in collect_template_parameters(template_model):
            param_id = str(parameter.id or "").strip()
            input_type = str(parameter.input_type or "")
            matched = None
            if input_type == "date":
                date_match = DATE_PATTERN.search(question_text)
                if date_match:
                    value = date_match.group(0)
                    matched = [ParameterValue(label=value, value=value, query=value)]
            elif input_type == "enum":
                for option in list(parameter.options or []):
                    label = str(option.label or "")
                    value = str(option.value or "")
                    if label and label in question_text or value and value in question_text:
                        matched = [copy.deepcopy(option)]
                        break
            elif input_type == "dynamic":
                source = str(parameter.source or "").strip()
                try:
                    resolved = self.parameter_option_service.resolve(
                        user_id="default",
                        parameter_id=param_id,
                        source=source,
                        context_values=parameter_values,
                    )
                except Exception:
                    resolved = None
                choices = []
                for option in list((resolved.options if resolved is not None else []) or []):
                    label = str(option.label or "")
                    value = str(option.value or "")
                    if label and label in question_text or value and value in question_text:
                        choices.append(copy.deepcopy(option))
                        if not parameter.multi:
                            break
                if choices:
                    matched = choices
            elif input_type == "free_text":
                if question_text.strip():
                    matched = [ParameterValue(label=question_text.strip(), value=question_text.strip(), query=question_text.strip())]

            if matched:
                parameter_values[param_id] = matched
        return merge_parameter_values(parameter_definitions=collect_template_parameters(template_model), current_values={}, incoming_values=parameter_values)

    def _build_ask_response(self, *, conversation_id: str, chat_id: str, template: ReportTemplate, template_instance: TemplateInstance, request_id: str | None, api_version: str | None) -> ChatResponse:
        """根据模板实例当前完整度直接构造下一轮追问。"""
        template_model = template
        template_instance_model = template_instance
        missing = _missing_required_parameters(template=template_model, template_instance=template_instance_model)
        if missing:
            next_parameter = missing[0]
            next_parameter_state = next(
                (
                    copy.deepcopy(parameter)
                    for parameter in collect_instance_parameters(
                        parameters=template_instance_model.parameters,
                        catalogs=template_instance_model.catalogs,
                    )
                    if parameter.id == next_parameter.id
                ),
                copy.deepcopy(next_parameter),
            )
            ask = ChatAsk(
                status="pending",
                mode="natural_language" if next_parameter.interaction_mode == "natural_language" else "form",
                type="fill_params",
                title="请补充报告参数",
                text=f"请补充参数：{next_parameter.label}",
                parameters=[next_parameter_state],
                template_instance=template_instance,
            )
        else:
            ask = ChatAsk(
                status="pending",
                mode="form",
                type="confirm_params",
                title="请确认报告诉求",
                text="请确认报告诉求后开始生成。",
                parameters=collect_instance_parameters(parameters=template_instance_model.parameters, catalogs=template_instance_model.catalogs),
                template_instance=template_instance,
            )
        return _chat_response(
            conversation_id=conversation_id,
            chat_id=chat_id,
            status="waiting_user",
            ask=ask,
            answer=None,
            request_id=request_id,
            api_version=api_version,
        )

    def _append_assistant_message(self, *, conversation_id: str, user_id: str, chat_id: str, response: ChatResponse) -> None:
        """持久化统一聊天响应，确保聊天与报告视图都可重放。"""
        self.chat_repository.append_message(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=ConversationMessageContent(response=response),
            action=ConversationMessageAction(type="chat_response"),
            meta=ConversationMessageMeta(status=response.status),
            chat_id=chat_id,
        )


def _message_preview(content: ConversationMessageContent) -> str:
    if content.question:
        return str(content.question)[:80]
    response = content.response
    if response is not None and response.ask is not None:
        return str(response.ask.title or response.ask.text or "")[:80]
    return ""


def _chat_response(
    *,
    conversation_id: str,
    chat_id: str,
    status: str,
    ask: ChatAsk | None,
    answer: ChatAnswerEnvelope | None,
    request_id: str | None,
    api_version: str | None,
) -> ChatResponse:
    return ChatResponse(
        conversation_id=conversation_id,
        chat_id=chat_id,
        status=status,
        steps=[],
        ask=ask,
        answer=answer,
        errors=[],
        request_id=request_id,
        timestamp=_epoch_ms(),
        api_version=api_version or "v1",
    )


def _template_match_text(template: ReportTemplate) -> str:
    parts = [
        str(template.name or ""),
        str(template.description or ""),
        str(template.category or ""),
    ]
    for parameter in list(template.parameters or []):
        parts.append(str(parameter.label or parameter.id or ""))
    for catalog in list(template.catalogs or []):
        parts.extend(_catalog_match_text(catalog))
    return "\n".join([part for part in parts if part])


def _lexical_score(question: str, template: ReportTemplate) -> float:
    lowered = question.lower()
    score = 0.0
    for part in [template.name, template.category, template.description]:
        text = str(part or "").lower()
        if text and text in lowered:
            score += 1.0
    return score


def _catalog_match_text(catalog) -> list[str]:
    parts = [str(catalog.title or "")]
    for sub_catalog in list(catalog.sub_catalogs or []):
        parts.extend(_catalog_match_text(sub_catalog))
    for section in list(catalog.sections or []):
        parts.append(str(section.outline.requirement or ""))
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


def _missing_required_parameters(*, template: ReportTemplate, template_instance: TemplateInstance) -> list[Parameter]:
    values = parameters_to_value_map(
        collect_instance_parameters(
            parameters=template_instance.parameters,
            catalogs=template_instance.catalogs,
        )
    )
    missing = []
    for parameter in collect_template_parameters(template):
        if not parameter.required:
            continue
        if not list(values.get(parameter.id) or []):
            missing.append(parameter)
    return missing


def _template_instance_from_payload(payload: TemplateInstance, *, chat_id: str, status: str, capture_stage: str):
    instance = copy.deepcopy(payload)
    instance.chat_id = chat_id
    instance.status = status
    instance.capture_stage = capture_stage
    if capture_stage in {"confirm_params", "generate_report", "report_ready"}:
        instance.parameter_confirmation.missing_parameter_ids = []
        instance.parameter_confirmation.confirmed = True
        instance.parameter_confirmation.confirmed_at = instance.parameter_confirmation.confirmed_at or _iso_timestamp()
    return instance


def _reply_parameter_values_to_value_map(
    payload: Any,
    *,
    parameter_definitions: list[Parameter],
    current_parameters: list[Parameter] | None,
) -> dict[str, list[ParameterValue]]:
    if not isinstance(payload, dict):
        return {}

    definition_by_id = parameters_by_id(parameter_definitions)
    current_by_id = parameters_by_id(current_parameters)
    resolved: dict[str, list[ParameterValue]] = {}
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


def _scalar_to_parameter_value(raw_value: Any, *, definition: Parameter) -> ParameterValue:
    candidates = []
    for field in (definition.options, definition.values, definition.default_value):
        candidates.extend(list(field or []))
    for candidate in candidates:
        if raw_value in {candidate.label, candidate.value, candidate.query}:
            return copy.deepcopy(candidate)
    return ParameterValue(label=raw_value, value=raw_value, query=raw_value)


def _message_content_from_row(row) -> ConversationMessageContent:
    content = row.content if isinstance(row.content, dict) else {}
    response_payload = content.get("response") if isinstance(content.get("response"), dict) else None
    response = _chat_response_from_payload(response_payload) if response_payload is not None else None
    return ConversationMessageContent(question=content.get("question"), response=response)


def _message_action_from_row(row) -> ConversationMessageAction | None:
    if not isinstance(row.action, dict):
        return None
    action_type = str(row.action.get("type") or "").strip()
    return ConversationMessageAction(type=action_type) if action_type else None


def _message_meta_from_row(row) -> ConversationMessageMeta | None:
    if not isinstance(row.meta, dict):
        return None
    forked_from = row.meta.get("forkedFrom") if isinstance(row.meta.get("forkedFrom"), dict) else None
    status = str(row.meta.get("status") or "").strip() or None
    return ConversationMessageMeta(status=status, forked_from=dict(forked_from) if forked_from else None)


def _chat_response_from_payload(payload: dict[str, Any]) -> ChatResponse:
    ask_payload = payload.get("ask") if isinstance(payload.get("ask"), dict) else None
    answer_payload = payload.get("answer") if isinstance(payload.get("answer"), dict) else None
    template_instance_payload = ((ask_payload.get("reportContext") or {}).get("templateInstance")) if isinstance(ask_payload, dict) and isinstance(ask_payload.get("reportContext"), dict) else None
    ask = None
    if ask_payload is not None:
        ask = ChatAsk(
            status=str(ask_payload.get("status") or ""),
            mode=str(ask_payload.get("mode") or ""),
            type=str(ask_payload.get("type") or ""),
            title=str(ask_payload.get("title") or ""),
            text=str(ask_payload.get("text") or ""),
            parameters=[parameter_from_dict(item) for item in list(ask_payload.get("parameters") or [])],
            template_instance=template_instance_from_dict(template_instance_payload) if isinstance(template_instance_payload, dict) else None,
        )
    answer = None
    if answer_payload is not None:
        answer_type = str(answer_payload.get("answerType") or "")
        answer_body = answer_payload.get("answer") if isinstance(answer_payload.get("answer"), dict) else {}
        answer = ChatAnswerEnvelope(answer_type=answer_type)
        if answer_type == "REPORT":
            answer.report = ReportAnswerView(
                report_id=str(answer_body.get("reportId") or ""),
                status=str(answer_body.get("status") or ""),
                report=report_dsl_from_dict(answer_body.get("report") or {}),
                template_instance=template_instance_from_dict(answer_body.get("templateInstance") or {}),
                documents=[
                    DocumentView(
                        id=str(item.get("id") or ""),
                        format=str(item.get("format") or ""),
                        mime_type=str(item.get("mimeType") or ""),
                        file_name=str(item.get("fileName") or ""),
                        download_url=str(item.get("downloadUrl") or ""),
                        status=str(item.get("status") or ""),
                    )
                    for item in list(answer_body.get("documents") or [])
                    if isinstance(item, dict)
                ],
                generation_progress=GenerationProgressView(
                    total_sections=int(((answer_body.get("generationProgress") or {}).get("totalSections") or 0)),
                    completed_sections=int(((answer_body.get("generationProgress") or {}).get("completedSections") or 0)),
                    total_catalogs=int(((answer_body.get("generationProgress") or {}).get("totalCatalogs") or 0)),
                    completed_catalogs=int(((answer_body.get("generationProgress") or {}).get("completedCatalogs") or 0)),
                )
                if isinstance(answer_body.get("generationProgress"), dict)
                else None,
            )
        elif answer_type == "REPORT_TEMPLATE":
            answer.report_template_preview = TemplateImportPreview(
                normalized_template=report_template_from_dict((answer_body.get("normalizedTemplate") or {})),
                warnings=[str(item) for item in list(answer_body.get("warnings") or [])],
            )
    return ChatResponse(
        conversation_id=str(payload.get("conversationId") or ""),
        chat_id=str(payload.get("chatId") or ""),
        status=str(payload.get("status") or ""),
        ask=ask,
        answer=answer,
        errors=[str(item) for item in list(payload.get("errors") or [])],
        request_id=str(payload.get("requestId") or "") or None,
        timestamp=int(payload.get("timestamp") or 0) or None,
        api_version=str(payload.get("apiVersion") or "v1"),
    )


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
