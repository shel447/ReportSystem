"""ORM rows stored in the development-support database."""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.sql import func

from .dev_database import DevBase


def gen_id() -> str:
    return str(uuid.uuid4())


class SystemSetting(DevBase):
    __tablename__ = "dev_system_settings"

    id = Column(String, primary_key=True, default="global")
    completion_config = Column(JSON, nullable=False, default=dict)
    embedding_config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Feedback(DevBase):
    __tablename__ = "dev_feedbacks"

    id = Column(String, primary_key=True, default=gen_id)
    user_ip = Column(String, nullable=True)
    submitter = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    priority = Column(String, nullable=False, default="medium")
    images = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
