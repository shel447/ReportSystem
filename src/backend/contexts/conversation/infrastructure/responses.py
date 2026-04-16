from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from ....infrastructure.ai.openai_compat import OpenAICompatGateway
from ....infrastructure.settings.system_settings import build_completion_provider_config


def generate_chat_reply(
    db: Session,
    gateway: OpenAICompatGateway,
    user_message: str,
    *,
    matched_template: Dict[str, Any] | None = None,
    candidates: List[Dict[str, Any]] | None = None,
) -> str:
    config = build_completion_provider_config(db)
    user_lines = [f"用户消息: {user_message}"]
    if matched_template:
        user_lines.extend([
            "当前已命中的模板:",
            f"- 模板名称: {matched_template.get('name')}",
            f"- 分类: {matched_template.get('category') or '未设置'}",
            f"- 描述: {matched_template.get('description') or '未设置'}",
            "请告诉用户已为其匹配到该模板，并提示其填写下方参数表单。",
        ])
    if candidates:
        user_lines.append("当前存在多个候选模板，请告诉用户系统尚未完全确定，并建议其从候选模板中选择：")
        for item in candidates:
            user_lines.append(
                f"- {item.get('template_name')} | 分类: {item.get('category') or '未设置'} | 描述: {item.get('description') or '未设置'} | 报告类型: {item.get('report_type') or '未设置'} | 评分: {item.get('score')} | 原因: {', '.join(item.get('match_reasons') or [])}"
            )
    user_lines.append("输出要求：简洁、专业、中文，不要编造未提供的数据。")
    response = gateway.chat_completion(
        config,
        [
            {
                "role": "system",
                "content": "你是智能报告系统的对话助手，负责帮助用户选择模板并开始生成报告。",
            },
            {"role": "user", "content": "\n".join(user_lines)},
        ],
        temperature=min(config.temperature, 0.3),
        max_tokens=220,
    )
    return response["content"]
