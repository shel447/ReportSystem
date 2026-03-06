from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .ai_gateway import OpenAICompatGateway
from .system_settings_service import build_completion_provider_config


def generate_report_sections(
    db: Session,
    gateway: OpenAICompatGateway,
    template_name: str,
    outline: List[Any],
    params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    config = build_completion_provider_config(db)
    effective_outline = outline or _default_outline(template_name)
    results: List[Dict[str, Any]] = []
    for item in effective_outline:
        if not isinstance(item, dict):
            continue
        results.append(_generate_single_section(config, gateway, template_name, item, params))
    return results


def generate_single_section(
    db: Session,
    gateway: OpenAICompatGateway,
    template_name: str,
    section: Dict[str, Any],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    config = build_completion_provider_config(db)
    return _generate_single_section(config, gateway, template_name, section, params)


def _generate_single_section(
    config,
    gateway: OpenAICompatGateway,
    template_name: str,
    section: Dict[str, Any],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    title = str(section.get("title") or "未命名章节").strip()
    description = str(section.get("description") or "").strip()
    dynamic_meta = section.get("dynamic_meta") if isinstance(section.get("dynamic_meta"), dict) else None
    level = max(1, min(6, int(section.get("level") or 1)))

    user_prompt = "\n".join([
        f"模板名称: {template_name}",
        f"章节标题: {title}",
        f"章节描述: {description}",
        f"标题层级: H{level}",
        "输入参数(JSON):",
        _to_json(params),
        "动态上下文(JSON):",
        _to_json(dynamic_meta or {}),
        "输出要求:",
        f"1. 使用中文撰写该章节内容，并以 {'#' * level} {title} 作为开头。",
        "2. 只输出 Markdown 正文，不要输出解释、前言、代码块围栏或多余说明。",
        "3. 结合输入参数给出有信息量的分析、结论和建议，不要写成模板占位语。",
    ])
    response = gateway.chat_completion(
        config,
        [
            {
                "role": "system",
                "content": "你是企业报告生成助手，负责输出专业、准确、结构清晰的中文 Markdown 章节。",
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.temperature,
    )
    result = {
        "title": title,
        "description": description,
        "content": response["content"],
        "generated_at": datetime.now().isoformat(),
        "model": response["model"],
    }
    if dynamic_meta:
        result["dynamic_meta"] = dynamic_meta
    return result


def _default_outline(template_name: str) -> List[Dict[str, Any]]:
    return [
        {"title": "执行摘要", "description": f"概述 {template_name} 的整体结论", "level": 1},
        {"title": "关键发现", "description": "总结最值得关注的事实与趋势", "level": 1},
        {"title": "风险与异常", "description": "分析潜在风险、异常点和影响", "level": 1},
        {"title": "建议与行动", "description": "给出可执行的改进建议和下一步动作", "level": 1},
    ]


def _to_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)
