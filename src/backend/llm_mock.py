"""Mock LLM service used by the report system demo."""
from datetime import datetime
from typing import Any, Dict, List


def generate_report_content(template_name: str, outline: List[Any],
                            params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate section content from outline (or fallback template)."""
    date_str = params.get("date", params.get("inspection_date", datetime.now().strftime("%Y-%m-%d")))
    devices = params.get("devices", params.get("device_list", ["Device-001"]))
    if isinstance(devices, str):
        devices = [d.strip() for d in devices.split(",") if d.strip()]
    if not isinstance(devices, list) or not devices:
        devices = ["Device-001"]

    if outline:
        return _generate_from_outline(outline, date_str, devices)
    return _generate_default(template_name, date_str, devices)


def _generate_from_outline(outline: List[Any], date_str: str, devices: List[str]) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    for item in outline:
        if not isinstance(item, dict):
            continue

        title = item.get("title", "Section")
        description = item.get("description", "")
        level = int(item.get("level", 1) or 1)
        level = max(1, min(6, level))
        heading = "#" * level

        body_lines = [
            f"{heading} {title}",
            "",
            f"Date: {date_str}",
            f"Devices: {', '.join(devices)}",
        ]
        if description:
            body_lines.extend(["", f"Description: {description}"])
        body_lines.extend([
            "",
            f"This section summarizes '{title}' based on current input parameters.",
            "All key indicators are in normal range in this mock environment.",
        ])

        section = {
            "title": title,
            "description": description,
            "content": "\n".join(body_lines),
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1-hierarchical",
        }
        if "dynamic_meta" in item:
            section["dynamic_meta"] = item["dynamic_meta"]
        sections.append(section)
    return sections


def _generate_default(template_name: str, date_str: str, devices: List[str]) -> List[Dict[str, Any]]:
    device_details = "\n".join([
        f"- **{d}**: CPU 45%, Memory 62%, status normal" for d in devices
    ])

    return [
        {
            "title": "1. Executive Summary",
            "content": (
                f"# Executive Summary\n\n"
                f"This report is generated from template **{template_name}**.\n"
                f"Date: {date_str}.\n\n"
                f"{len(devices)} devices inspected, overall health score **92/100**."
            ),
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
        {
            "title": "2. Device Overview",
            "content": (
                f"# Device Overview\n\n"
                f"Inspected devices:\n{device_details}\n\n"
                "All key metrics are in expected range."
            ),
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
        {
            "title": "3. Exception Analysis",
            "content": (
                f"# Exception Analysis\n\n"
                f"No critical alerts found in cycle {date_str}.\n\n"
                f"Sample low-priority item: {devices[0]} latency occasionally exceeds 50ms."
            ),
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
        {
            "title": "4. Recommendations",
            "content": (
                "# Recommendations\n\n"
                "1. Continue weekly capacity checks.\n"
                f"2. Keep tracking network latency trend on {devices[0]}."
            ),
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
    ]


def generate_chat_response(user_message: str, context: dict) -> str:
    """Mock chat response."""
    msg_lower = user_message.lower()

    if any(kw in msg_lower for kw in ["巡检", "检查", "设备", "报告"]):
        return (
            "我可以帮您生成设备巡检报告。\n"
            "请提供：\n"
            "1. 巡检日期（例如 2026-03-02）\n"
            "2. 设备列表（例如 Router-001, Switch-001）"
        )

    if any(kw in msg_lower for kw in ["模板", "列表", "有什么"]):
        return "您可以在‘模板管理’页查看已有报告模板，或直接描述您要生成的报告类型。"

    if any(kw in msg_lower for kw in ["定时", "自动", "周期"]):
        return "可以。您可以在‘定时任务’页创建一次性或周期性任务。"

    matched_template = context.get("matched_template")
    if matched_template:
        return f"已识别模板：{matched_template}。请继续补充参数。"
    return f"收到：{user_message}。请告诉我您希望生成哪一类报告。"
