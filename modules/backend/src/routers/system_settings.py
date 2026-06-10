from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from ..infrastructure.dev_support import DevSupportService
from ..web.base import DevHandler


class CompletionSettingsUpdate(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    clear_api_key: bool = False
    temperature: Optional[float] = None
    timeout_sec: Optional[int] = None


class EmbeddingSettingsUpdate(BaseModel):
    base_url: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    clear_api_key: bool = False
    timeout_sec: Optional[int] = None
    use_completion_auth: Optional[bool] = None


class SettingsUpdateRequest(BaseModel):
    completion: CompletionSettingsUpdate
    embedding: EmbeddingSettingsUpdate


class SettingsTestRequest(BaseModel):
    target: Literal["completion", "embedding", "both"] = "both"


class SystemSettingsHandler(DevHandler):
    async def get(self):
        self.write_json(await self.run_blocking(DevSupportService().get_settings))

    async def put(self):
        data = self.parse_json(SettingsUpdateRequest)
        self.write_json(await self.run_blocking(DevSupportService().update_settings, data.model_dump(exclude_unset=True)))


class SystemSettingsTestHandler(DevHandler):
    async def post(self):
        data = self.parse_json(SettingsTestRequest)
        self.write_json(await self.run_blocking(DevSupportService().test_settings, data.target))


class SystemSettingsReindexHandler(DevHandler):
    async def post(self):
        self.write_json({"message": "当前版本不再维护独立模板语义索引，模板匹配直接基于正式模板对象进行。", "index_status": {"ready_count": 0, "stale_count": 0, "error_count": 0, "total_count": 0}})


ROUTES = [
    (r"/rest/dev/system-settings", SystemSettingsHandler),
    (r"/rest/dev/system-settings/test", SystemSettingsTestHandler),
    (r"/rest/dev/system-settings/reindex", SystemSettingsReindexHandler),
]
