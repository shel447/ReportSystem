"""Development-support operations with infrastructure-owned transactions."""

from __future__ import annotations

import base64
from datetime import datetime
import io
import zipfile

from .persistence.dev_models import Feedback
from .persistence.unit_of_work import DevSqlAlchemyUnitOfWork
from .settings.system_settings import (
    build_completion_provider_config,
    build_embedding_provider_config,
    get_settings_payload,
    save_settings,
)
from .ai.openai_compat import OpenAICompatGateway


class DevSupportService:
    def get_settings(self) -> dict:
        with DevSqlAlchemyUnitOfWork() as uow:
            payload = get_settings_payload(uow.session)
            payload["index_status"] = _empty_index_status()
            return payload

    def update_settings(self, payload: dict) -> dict:
        with DevSqlAlchemyUnitOfWork() as uow:
            result = save_settings(uow.session, payload, commit=False)
            uow.commit()
            result["index_status"] = _empty_index_status()
            return result

    def test_settings(self, target: str) -> dict:
        gateway = OpenAICompatGateway()
        result = {"target": target}
        with DevSqlAlchemyUnitOfWork() as uow:
            if target in ("completion", "both"):
                result["completion"] = _test_completion(uow.session, gateway)
            if target in ("embedding", "both"):
                result["embedding"] = _test_embedding(uow.session, gateway)
        return result

    def create_feedback(self, *, user_ip: str | None, submitter: str, content: str, priority: str, images: list[str]) -> dict:
        with DevSqlAlchemyUnitOfWork() as uow:
            row = Feedback(user_ip=user_ip, submitter=submitter, content=content, priority=priority, images=images)
            uow.session.add(row)
            uow.session.flush()
            feedback_id = row.id
            uow.commit()
            return {"status": "success", "feedback_id": feedback_id}

    def list_feedbacks(self) -> list[dict]:
        with DevSqlAlchemyUnitOfWork() as uow:
            rows = uow.session.query(Feedback).order_by(Feedback.created_at.desc()).all()
            return [_feedback_to_dict(row) for row in rows]

    def delete_feedback(self, feedback_id: str) -> dict | None:
        with DevSqlAlchemyUnitOfWork() as uow:
            row = uow.session.get(Feedback, feedback_id)
            if row is None:
                return None
            uow.session.delete(row)
            uow.commit()
            return {"status": "success", "message": "Feedback deleted successfully"}

    def export_feedbacks(self) -> bytes:
        feedbacks = self.list_feedbacks()
        output = io.BytesIO()
        lines = ["# 系统意见反馈汇总报告", "", f"导出时间: {datetime.now():%Y-%m-%d %H:%M:%S}", f"总计反馈: {len(feedbacks)} 条", "", "---", ""]
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for feedback in feedbacks:
                lines.extend([f"### {feedback['content'][:30]}...", "", f"- **提出人**: {feedback['submitter'] or '匿名'}", f"- **时间**: {feedback['created_at']}", f"- **IP**: {feedback['user_ip']}", "", feedback["content"], ""])
                for index, value in enumerate(feedback["images"]):
                    try:
                        header, encoded = value.split(",", 1)
                        ext = "jpg" if "image/jpeg" in header else "png"
                        path = f"assets/{feedback['id']}_{index}.{ext}"
                        archive.writestr(path, base64.b64decode(encoded))
                        lines.extend([f"![相关截图 {index + 1}]({path})", ""])
                    except Exception:
                        lines.extend(["> [图片解析失败]", ""])
                lines.extend(["---", ""])
            archive.writestr("feedbacks_report.md", "\n".join(lines).encode("utf-8"))
        return output.getvalue()


def _feedback_to_dict(row) -> dict:
    return {"id": row.id, "user_ip": row.user_ip, "submitter": row.submitter, "content": row.content, "priority": row.priority, "images": list(row.images or []), "created_at": row.created_at.isoformat() if row.created_at else None}


def _empty_index_status() -> dict:
    return {"ready_count": 0, "stale_count": 0, "error_count": 0, "total_count": 0}


def _test_completion(db, gateway) -> dict:
    try:
        config = build_completion_provider_config(db)
        response = gateway.chat_completion(config, [{"role": "user", "content": "请只回复：completion test ok"}], temperature=0, max_tokens=32)
        return {"ok": True, "model": response["model"], "preview": response["content"][:120]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _test_embedding(db, gateway) -> dict:
    try:
        config = build_embedding_provider_config(db)
        vector = gateway.create_embedding(config, ["embedding test"])[0]
        return {"ok": True, "model": config.model, "dimension": len(vector)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
