# Runtime Schedule 接入

ReportSystem 使用平台 Runtime 提供的 `runtime.schedule` 执行进程级后台周期任务。业务模块不自行引入第三方调度框架，也不负责创建平台调度基础设施。

## 1. 职责边界

| 层级 | 职责 |
|---|---|
| `runtime.schedule.Job` | 封装任务函数、参数、首次延迟、周期和下次执行时间 |
| `runtime.schedule.Schedule` | 使用最小堆管理任务，并按执行时间调度任务 |
| Backend infrastructure | 注册 ReportSystem 拥有的后台任务，并管理调度线程启动 |
| application/domain/controller | 不直接依赖或操作 Runtime Schedule |

`modules/mock-sdk` 提供与平台 Runtime 接口一致的本地开发实现。生产环境由平台 Runtime SDK 提供同名能力。

## 2. 使用方式

单次任务：

```python
from runtime.schedule import Schedule

schedule = Schedule()
schedule.add(func=refresh_once, delay=10, params={"source": "manual"})
schedule.run()
```

周期任务：

```python
schedule.add(func=refresh_metadata, interval=300)
schedule.run()
```

任务函数统一接收一个 `params` 参数。`delay <= 0` 表示立即执行；`interval <= 0` 表示只执行一次。也可以通过 `add_job()` 注册具有 `run()` 方法的自定义 Job。

## 3. ReportSystem 接入

平台运行时启动时：

1. 同步检查一次 Metadata 版本。
2. 仅注册一次每 300 秒执行的 Metadata 刷新任务。
3. 使用名为 `runtime-schedule` 的 daemon 线程运行 `Schedule.run()`。
4. Metadata 版本变化时清理 DataCatalog 和 Knowledge/RAG 缓存。

重复初始化不会重复注册任务或创建线程。服务销毁时停止 MessageCenter，但调度线程作为进程级 daemon 线程继续存在；后续重新初始化复用同一调度线程。

## 4. 当前限制

- `Schedule.run()` 是阻塞式无限循环。
- 当前 Runtime Schedule 不提供停止、移除任务、暂停任务或持久化能力。
- 任务异常由 Runtime Job 隔离，不向调度循环传播。
- 当前实现适合进程生命周期内的轻量后台任务，不用于需要持久化、补偿或跨进程协调的业务调度。

这些限制属于当前 Runtime SDK 契约。未来若 Runtime 增加生命周期控制，Backend 再同步接入，不在业务模块中自行扩展兼容接口。
