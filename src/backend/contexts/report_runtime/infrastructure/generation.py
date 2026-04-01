from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable, List

from sqlalchemy.orm import Session

from ....ai_gateway import AIRequestError, OpenAICompatGateway
from ...template_catalog.domain.models import ReportTemplate
from ....section_query_service import build_report_context, generate_section_evidence
from ....system_settings_service import build_completion_provider_config


def generate_report_sections(
    db: Session,
    gateway: OpenAICompatGateway,
    template: ReportTemplate | Dict[str, Any] | str,
    outline: List[Any],
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    config = build_completion_provider_config(db)
    template_context = _normalize_template_context(template)
    effective_outline = outline or _default_outline(template_context["name"])
    evidence_results: List[Dict[str, Any]] = []
    for item in effective_outline:
        if not isinstance(item, dict):
            continue
        evidence_results.append(
            generate_section_evidence(
                gateway=gateway,
                config=config,
                template_context=template_context,
                section=item,
                params=params,
            )
        )

    report_context = build_report_context(evidence_results)
    return [
        _render_section_content(
            config=config,
            gateway=gateway,
            template_context=template_context,
            section_result=item,
            params=params,
            report_context=report_context,
        )
        for item in evidence_results
    ]


def generate_single_section(
    db: Session,
    gateway: OpenAICompatGateway,
    template: ReportTemplate | Dict[str, Any] | str,
    section: Dict[str, Any],
    params: Dict[str, Any],
    *,
    existing_sections: List[Dict[str, Any]] | None = None,
    section_index: int | None = None,
) -> Dict[str, Any]:
    config = build_completion_provider_config(db)
    template_context = _normalize_template_context(template)
    evidence = generate_section_evidence(
        gateway=gateway,
        config=config,
        template_context=template_context,
        section=section,
        params=params,
    )
    combined_sections = _merge_sections(existing_sections or [], section_index, evidence)
    report_context = build_report_context(combined_sections)
    return _render_section_content(
        config=config,
        gateway=gateway,
        template_context=template_context,
        section_result=evidence,
        params=params,
        report_context=report_context,
    )


def _render_section_content(
    *,
    config,
    gateway: OpenAICompatGateway,
    template_context: Dict[str, Any],
    section_result: Dict[str, Any],
    params: Dict[str, Any],
    report_context: Dict[str, Any],
) -> Dict[str, Any]:
    title = str(section_result.get("title") or "未命名章节").strip()
    description = str(section_result.get("description") or "").strip()
    level = max(1, min(6, int(section_result.get("level") or 1)))
    dynamic_meta = section_result.get("dynamic_meta") if isinstance(section_result.get("dynamic_meta"), dict) else None
    debug = dict(section_result.get("debug") or {})
    data_status = str(section_result.get("data_status") or "failed")
    status = str(section_result.get("status") or "failed")

    if data_status != "success":
        return _finalize_section(
            title=title,
            description=description,
            content="该章节数据生成失败，请查看调试信息。",
            model=config.model,
            status="failed",
            data_status="failed",
            debug=debug,
            dynamic_meta=dynamic_meta,
        )

    user_prompt = "\n".join(
        [
            f"模板名称: {template_context.get('name') or '未命名模板'}",
            f"模板描述: {template_context.get('description') or '未提供'}",
            f"场景: {template_context.get('scenario') or '未提供'}",
            f"报告类型: {template_context.get('report_type') or '未提供'}",
            f"章节标题: {title}",
            f"章节描述: {description}",
            f"标题层级: H{level}",
            "用户输入参数(JSON):",
            _to_json(params),
            "动态章节上下文(JSON):",
            _to_json(dynamic_meta or {}),
            "章节查询证据(JSON):",
            _to_json(
                {
                    "row_count": debug.get("row_count", 0),
                    "sample_rows": debug.get("sample_rows", []),
                    "compiled_sql": debug.get("compiled_sql", ""),
                }
            ),
            "全报告证据概览(JSON):",
            _to_json(report_context),
            "输出要求:",
            f"1. 使用中文撰写该章节内容，并以 {'#' * level} {title} 作为开头。",
            "2. 内容必须基于给定证据，不要编造没有出现在证据中的指标。",
            "3. 尽量给出趋势、异常、风险或建议，而不是简单复述字段名。",
            "4. 如样本结果较少，可以明确说明样本范围和局限。",
            "5. 只输出 Markdown 正文，不要输出代码块围栏或额外解释。",
        ]
    )
    try:
        response = gateway.chat_completion(
            config,
            [
                {
                    "role": "system",
                    "content": "你是电信运维分析报告撰写助手，负责基于已查询到的数据证据输出专业、克制、结构清晰的中文 Markdown 章节。",
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=config.temperature,
            max_tokens=900,
        )
        content = response["content"]
        model = response["model"]
        section_status = "generated"
    except AIRequestError as exc:
        debug["error_message"] = _append_error(debug.get("error_message"), f"正文生成失败：{exc}")
        content = "该章节数据已查询成功，但正文生成失败，请查看调试信息。"
        model = config.model
        section_status = "failed"

    return _finalize_section(
        title=title,
        description=description,
        content=content,
        model=model,
        status=section_status,
        data_status=data_status,
        debug=debug,
        dynamic_meta=dynamic_meta,
    )


def _merge_sections(
    existing_sections: List[Dict[str, Any]],
    section_index: int | None,
    evidence: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not existing_sections:
        return [evidence]
    merged: List[Dict[str, Any]] = []
    inserted = False
    for idx, item in enumerate(existing_sections):
        if section_index is not None and idx == section_index:
            merged.append(evidence)
            inserted = True
            continue
        if isinstance(item, dict):
            merged.append(item)
    if not inserted:
        merged.append(evidence)
    return merged


def _finalize_section(
    *,
    title: str,
    description: str,
    content: str,
    model: str,
    status: str,
    data_status: str,
    debug: Dict[str, Any],
    dynamic_meta: Dict[str, Any] | None,
) -> Dict[str, Any]:
    result = {
        "title": title,
        "description": description,
        "content": content,
        "generated_at": datetime.now().isoformat(),
        "model": model,
        "status": status,
        "data_status": data_status,
        "debug": {
            "strategy": str(debug.get("strategy") or "legacy"),
            "nl_request": str(debug.get("nl_request") or ""),
            "schema_candidates": list(debug.get("schema_candidates") or []),
            "query_spec": dict(debug.get("query_spec") or {}),
            "ibis_code": str(debug.get("ibis_code") or ""),
            "compiled_sql": str(debug.get("compiled_sql") or ""),
            "attempts": int(debug.get("attempts") or 0),
            "row_count": int(debug.get("row_count") or 0),
            "sample_rows": list(debug.get("sample_rows") or []),
            "error_stage": str(debug.get("error_stage") or ""),
            "error_message": str(debug.get("error_message") or ""),
        },
    }
    if dynamic_meta:
        result["dynamic_meta"] = dynamic_meta
    return result


def _normalize_template_context(template: ReportTemplate | Dict[str, Any] | str) -> Dict[str, Any]:
    if isinstance(template, ReportTemplate):
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scenario,
            "match_keywords": template.match_keywords,
            "content_params": template.content_params,
            "outline": template.outline,
        }
    if isinstance(template, dict):
        return {
            "template_id": str(template.get("template_id") or ""),
            "name": str(template.get("name") or "报告模板"),
            "description": str(template.get("description") or ""),
            "report_type": str(template.get("report_type") or ""),
            "scenario": str(template.get("scenario") or ""),
            "match_keywords": list(template.get("match_keywords") or []),
            "content_params": list(template.get("content_params") or []),
            "outline": list(template.get("outline") or []),
        }
    return {
        "template_id": "",
        "name": str(template or "报告模板"),
        "description": "",
        "report_type": "",
        "scenario": "",
        "match_keywords": [],
        "content_params": [],
        "outline": [],
    }


def _default_outline(template_name: str) -> List[Dict[str, Any]]:
    return [
        {"title": "执行摘要", "description": f"概述 {template_name} 的整体结论", "level": 1},
        {"title": "关键发现", "description": "总结最值得关注的事实与趋势", "level": 1},
        {"title": "风险与异常", "description": "分析潜在风险、异常点和影响", "level": 1},
        {"title": "建议与行动", "description": "给出可执行的改进建议和下一步动作", "level": 1},
    ]


def _append_error(existing: Any, new_error: str) -> str:
    current = str(existing or "").strip()
    if not current:
        return new_error
    return current + " | " + new_error


def _to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


class OpenAIReportContentGenerator:
    def __init__(self, db: Session, gateway: OpenAICompatGateway | None = None) -> None:
        self.db = db
        self.gateway = gateway or OpenAICompatGateway()

    def generate(
        self,
        template: ReportTemplate,
        outline: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return generate_report_sections(self.db, self.gateway, template, outline, params)

    def generate_v2(
        self,
        template: ReportTemplate,
        params: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        from .rendering import generate_report_sections_v2

        config = build_completion_provider_config(self.db)
        template_context = {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scene or template.scenario,
        }

        def nl2sql_runner(*, description: str, params: dict[str, Any], locals_ctx: dict[str, Any], **_kwargs):
            section = {"title": "", "description": description}
            evidence = generate_section_evidence(
                gateway=self.gateway,
                config=config,
                template_context=template_context,
                section=section,
                params=params,
            )
            rows = evidence.get("debug", {}).get("sample_rows") or []
            columns = list(rows[0].keys()) if rows else []
            debug = evidence.get("debug") or {}
            return {"rows": rows, "columns": columns, "debug": debug}

        def ai_synthesis_runner(*, prompt: str, params: dict[str, Any], locals_ctx: dict[str, Any], **_kwargs):
            response = self.gateway.chat_completion(
                config,
                [
                    {"role": "system", "content": "你是报告撰写助手，负责基于上下文输出简洁的中文总结。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=config.temperature,
                max_tokens=600,
            )
            return response["content"]

        return generate_report_sections_v2(
            {
                "name": template.name,
                "sections": template.sections or [],
            },
            params,
            nl2sql_runner=nl2sql_runner,
            ai_synthesis_runner=ai_synthesis_runner,
        )

    def generate_v2_from_outline(
        self,
        template: ReportTemplate,
        outline: list[dict[str, Any]],
        params: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        from .rendering import generate_report_sections_from_outline_tree_v2

        config = build_completion_provider_config(self.db)
        template_context = {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "report_type": template.report_type,
            "scenario": template.scene or template.scenario,
        }

        def nl2sql_runner(*, description: str, params: dict[str, Any], locals_ctx: dict[str, Any], **_kwargs):
            section = {"title": "", "description": description}
            evidence = generate_section_evidence(
                gateway=self.gateway,
                config=config,
                template_context=template_context,
                section=section,
                params=params,
            )
            rows = evidence.get("debug", {}).get("sample_rows") or []
            columns = list(rows[0].keys()) if rows else []
            debug = evidence.get("debug") or {}
            return {"rows": rows, "columns": columns, "debug": debug}

        def ai_synthesis_runner(*, prompt: str, params: dict[str, Any], locals_ctx: dict[str, Any], **_kwargs):
            response = self.gateway.chat_completion(
                config,
                [
                    {"role": "system", "content": "你是报告撰写助手，负责基于上下文输出简洁的中文总结。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=config.temperature,
                max_tokens=600,
            )
            return response["content"]

        def freeform_runner(*, title: str, description: str, level: int, dynamic_meta: dict[str, Any], **_kwargs):
            response = self.gateway.chat_completion(
                config,
                [
                    {
                        "role": "system",
                        "content": "你是报告撰写助手，负责根据章节标题、描述和参数输出专业、克制的中文 Markdown 章节。",
                    },
                    {
                        "role": "user",
                        "content": "\n".join(
                            [
                                f"模板名称: {template.name}",
                                f"章节标题: {title}",
                                f"章节描述: {description}",
                                f"标题层级: H{level}",
                                "输入参数(JSON):",
                                str(params),
                                "动态章节上下文(JSON):",
                                str(dynamic_meta or {}),
                                "输出要求:",
                                f"1. 以 {'#' * max(1, min(level, 6))} {title} 开头。",
                                "2. 只输出 Markdown 正文，不输出解释。",
                                "3. 当缺少数据证据时，只围绕标题和描述给出结构化表述，不虚构指标。",
                            ]
                        ),
                    },
                ],
                temperature=config.temperature,
                max_tokens=700,
            )
            return {"content": response["content"], "debug": {}, "status": "generated", "data_status": "success"}

        return generate_report_sections_from_outline_tree_v2(
            {
                "name": template.name,
                "sections": template.sections or [],
            },
            outline,
            params,
            nl2sql_runner=nl2sql_runner,
            ai_synthesis_runner=ai_synthesis_runner,
            freeform_runner=freeform_runner,
        )
