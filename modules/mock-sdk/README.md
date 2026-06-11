# Mock Runtime SDK

`modules/mock-sdk` 是平台 Runtime Python SDK 的本地开发实现。它提供注解路由、Controller 注册、Backend 生命周期调用、`runtime.config.Ini` 和 `runtime.client` 共享 HTTP Session，用于本地调试与自动化测试。

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

平台 HTTP 调用使用：

```python
from runtime.client._session import GLOBAL_HTTP_SESSION

response = GLOBAL_HTTP_SESSION.get("/rest/example")
```

本地实现通过 `RUNTIME_CLIENT_BASE_URL` 解析相对路径，默认连接 `http://127.0.0.1:8310`。Runtime INI 文件通过 `RUNTIME_CONFIG_FILE` 指定。

启动示例：

```bash
cd modules/backend
uv run python -m runtime.server --module src --host 0.0.0.0 --port 8300
```
