"""上下文变量"""

import contextvars

# 1. 用于create_device2kpi_wide_table函数
current_fk_whitelist = contextvars.ContextVar("current_fk_whitelist", default=[])  # 外键关系白名单
current_table_config = contextvars.ContextVar("current_table_config", default=None)  # 表列配置