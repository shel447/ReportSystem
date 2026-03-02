"""Mock LLM 服务 - 模拟大模型生成报告内容"""
from typing import List, Dict, Any
from datetime import datetime


def generate_report_content(template_name: str, outline: List[Any],
                            params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根据模板大纲和输入参数，模拟 LLM 生成报告章节内容。
    """
    date_str = params.get("date", params.get("inspection_date",
                          datetime.now().strftime("%Y-%m-%d")))
    devices = params.get("devices", params.get("device_list", ["Device-001"]))
    if isinstance(devices, str):
        devices = [d.strip() for d in devices.split(",")]

    # 如果模板有大纲定义，按大纲生成
    if outline:
        return _generate_from_outline(outline, template_name, date_str, devices)

    # 否则生成默认结构
    return _generate_default(template_name, date_str, devices)


def _generate_from_outline(outline, template_name, date_str, devices):
    sections = []
    for item in outline:
        title = item.get("title", "章节")
        sections.append({
            "title": title,
            "content": f"【{title}】\n\n"
                       f"报告日期：{date_str}\n"
                       f"涉及设备：{', '.join(devices)}\n\n"
                       f"经过系统分析，{title}相关指标均处于正常范围。"
                       f"所有设备运行稳定，未发现重大异常。",
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        })
    return sections


def _generate_default(template_name, date_str, devices):
    device_details = "\n".join([
        f"  - **{d}**: CPU 使用率 45%, 内存占用 62%, 运行正常" for d in devices
    ])

    return [
        {
            "title": "1. 执行摘要",
            "content": f"# 执行摘要\n\n"
                       f"本报告基于 **{template_name}** 模板生成，"
                       f"报告日期为 {date_str}。\n\n"
                       f"共巡检 {len(devices)} 台设备，"
                       f"整体运行状况良好，健康评分 **92/100**。",
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
        {
            "title": "2. 设备状态概览",
            "content": f"# 设备状态概览\n\n"
                       f"巡检设备列表：\n{device_details}\n\n"
                       f"所有设备各项指标均处于正常阈值范围内。",
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
        {
            "title": "3. 异常分析",
            "content": f"# 异常分析\n\n"
                       f"在 {date_str} 的巡检周期内，未发现严重告警。\n\n"
                       f"有 2 条低优先级告警：\n"
                       f"- {devices[0]} 网络延迟偶尔超过 50ms\n"
                       f"- 日志磁盘使用率达到 75%，建议清理",
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
        {
            "title": "4. 建议与跟进",
            "content": f"# 建议与跟进\n\n"
                       f"1. 建议对日志磁盘进行清理或扩容\n"
                       f"2. 持续关注 {devices[0]} 的网络延迟趋势\n"
                       f"3. 下一次巡检建议重点关注存储指标",
            "generated_at": datetime.now().isoformat(),
            "model": "mock-llm-v1",
        },
    ]


def generate_chat_response(user_message: str, context: dict) -> str:
    """模拟对话式 LLM 响应"""
    msg_lower = user_message.lower()

    if any(kw in msg_lower for kw in ["巡检", "检查", "设备", "报告"]):
        return ("我可以帮您生成设备巡检报告。请告诉我：\n"
                "1. 巡检日期（如：2026-03-02）\n"
                "2. 需要巡检的设备（如：Router-001, Switch-001）")

    if any(kw in msg_lower for kw in ["模板", "列表", "有什么"]):
        return "您可以在「模板管理」页面查看已有的报告模板，或者直接告诉我您想生成什么类型的报告。"

    if any(kw in msg_lower for kw in ["定时", "自动", "周期"]):
        return ("可以的！您可以在「定时任务」页面创建自动化任务。\n"
                "支持一次性执行和周期性执行两种模式。")

    return f"收到您的消息：「{user_message}」。我是报告系统的 AI 助手，可以帮您生成各类报告，请告诉我您的需求。"
