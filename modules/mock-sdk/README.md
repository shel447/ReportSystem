# Mock Runtime SDK

`modules/mock-sdk` 是平台 `runtime.server` Python SDK 的本地开发实现。它提供注解路由、Controller 注册、Backend 生命周期调用和 Tornado Server 托管，用于本地调试与自动化测试。

ReportSystem Backend 仅依赖以下公开接口：

```python
from runtime.server import router

@router.POST("/rest/example", user_handler=True, use_body=True)
async def example(req, body, **query):
    return {"ok": True}
```

Runtime 加载的 Backend 包必须提供：

- `register_initialize()`
- `register_handler()`
- `register_destroy()`

启动示例：

```bash
cd modules/backend
uv run python -m runtime.server --module src --host 0.0.0.0 --port 8300
```
