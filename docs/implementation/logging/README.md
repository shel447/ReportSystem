# 日志实现

ReportSystem 的日志分为 Runtime SDK、系统日志门面和业务调用三层。业务代码不自行创建 logger，也不读取 Runtime 日志配置。

## 1. 职责边界

| 层级 | 职责 |
|---|---|
| `runtime.log` | 提供 `get_log(name)`、`set_level(level)` 和最小 logger 方法集合 |
| `shared.kernel.log` | 固定 ChatBI logger 名称，统一脱敏、控制字符转义和动态日志级别监听 |
| 业务与基础设施代码 | 只使用 `shared.kernel.log.logger` |

`runtime.log` 不感知 ReportSystem、`chatbi`、`ir_flow` 或 `PY_RUNTIME_FILE`。本仓库 `modules/mock-sdk` 只提供与平台 Runtime 一致的开发态接口。

## 2. Logger

系统门面固定暴露：

```python
from src.shared.kernel.log import logger

logger.info("report generated report_id=%s", report_id)
logger.warn("dataset returned no rows dataset_id=%s", dataset_id)
logger.exception("report generation failed: %s", error)
```

Runtime logger 只提供：

- `debug`
- `info`
- `warn`
- `error`
- `critical`
- `exception`

不提供 `warning`。`algo_logger = get_log("ir_flow")` 只供 AgentFlow 或算法流程内部实现使用；普通业务代码不得使用。

## 3. 日志安全处理

`shared.kernel.log` 在调用 Runtime 前统一处理 message、位置参数和关键字参数：

- 换行、回车、制表、垂直制表、换页和退格转换为可见的字面转义序列。
- password、token、cookie、session、auth、API key、SSL/Kafka key password 等字段值统一脱敏。
- 脱敏值只保留首字符，后续显示为 `******`。

包装以 logger 实例为单位保持幂等，重复导入或初始化不会重复处理同一条日志。

## 4. 动态日志级别

`ChatBIServer.initialize()` 启动日志级别监控，`destroy()` 停止并回收线程。

监控规则：

1. 从 `PY_RUNTIME_FILE` 获取 Runtime INI 路径。
2. 启动时立即读取 `[log] level`。
3. 此后每 30 秒检查文件修改时间。
4. 级别变化时调用 `runtime.log.set_level()`。
5. 环境变量缺失、文件缺失、配置非法或读取失败只记录日志，不阻断服务启动。

日志级别属于 Runtime 运行控制，不进入 ChatBI ConfigCenter。
