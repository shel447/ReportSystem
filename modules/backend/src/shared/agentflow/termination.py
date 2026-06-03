"""Agent Flow 终止语义。"""

from __future__ import annotations


class FlowCancelled(Exception):
    """流程被外部取消。"""


class FlowTerminated(Exception):
    """流程被系统主动终止。"""


class FlowRefused(Exception):
    """流程拒绝继续回答。"""
