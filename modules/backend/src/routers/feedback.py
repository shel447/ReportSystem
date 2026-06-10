from __future__ import annotations

from pydantic import BaseModel

from ..infrastructure.dev_support import DevSupportService
from ..shared.kernel.errors import NotFoundError
from ..web.base import DevHandler


class FeedbackCreate(BaseModel):
    submitter: str
    content: str
    priority: str = "medium"
    images: list[str] = []


class FeedbacksHandler(DevHandler):
    async def get(self):
        self.write_json(await self.run_blocking(DevSupportService().list_feedbacks))

    async def post(self):
        data = self.parse_json(FeedbackCreate)
        payload = await self.run_blocking(
            DevSupportService().create_feedback,
            user_ip=self.request.remote_ip,
            **data.model_dump(),
        )
        self.write_json(payload)


class FeedbackHandler(DevHandler):
    async def delete(self, feedback_id: str):
        payload = await self.run_blocking(DevSupportService().delete_feedback, feedback_id)
        if payload is None:
            raise NotFoundError("Feedback not found")
        self.write_json(payload)


class FeedbackExportHandler(DevHandler):
    async def get(self):
        payload = await self.run_blocking(DevSupportService().export_feedbacks)
        self.set_header("Content-Type", "application/x-zip-compressed")
        self.set_header("Content-Disposition", 'attachment; filename="feedbacks_export.zip"')
        self.finish(payload)


ROUTES = [
    (r"/rest/dev/feedback/?", FeedbacksHandler),
    (r"/rest/dev/feedback/export\.zip", FeedbackExportHandler),
    (r"/rest/dev/feedback/([^/]+)", FeedbackHandler),
]
