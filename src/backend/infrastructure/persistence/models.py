from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class User(Base):
    __tablename__ = "tbl_users"

    id = Column(String, primary_key=True)
    display_name = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default="active")
    profile_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_seen_at = Column(DateTime, nullable=True)


class Conversation(Base):
    __tablename__ = "tbl_conversations"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("tbl_users.id"), nullable=False, index=True)
    title = Column(String, nullable=False, default="")
    fork_meta = Column(JSON, nullable=False, default=dict)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    chats = relationship(
        "Chat",
        cascade="all, delete-orphan",
        order_by="Chat.seq_no",
        lazy="selectin",
    )


class Chat(Base):
    __tablename__ = "tbl_chats"

    id = Column(String, primary_key=True, default=gen_id)
    conversation_id = Column(String, ForeignKey("tbl_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("tbl_users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(JSON, nullable=False, default=dict)
    action = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=False, default=dict)
    seq_no = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class ReportTemplate(Base):
    __tablename__ = "tbl_report_templates"

    id = Column(String, primary_key=True)
    category = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False, default="")
    schema_version = Column(String, nullable=False)
    content = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class TemplateInstance(Base):
    __tablename__ = "tbl_template_instances"

    id = Column(String, primary_key=True, default=gen_id)
    template_id = Column(String, ForeignKey("tbl_report_templates.id"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("tbl_conversations.id"), nullable=False, index=True)
    chat_id = Column(String, ForeignKey("tbl_chats.id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("tbl_users.id"), nullable=False, index=True)
    status = Column(String, nullable=False)
    capture_stage = Column(String, nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    schema_version = Column(String, nullable=False)
    content = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ReportInstance(Base):
    __tablename__ = "tbl_report_instances"

    id = Column(String, primary_key=True, default=gen_id)
    template_id = Column(String, ForeignKey("tbl_report_templates.id"), nullable=False, index=True)
    template_instance_id = Column(String, ForeignKey("tbl_template_instances.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("tbl_users.id"), nullable=False, index=True)
    source_conversation_id = Column(String, ForeignKey("tbl_conversations.id"), nullable=True, index=True)
    source_chat_id = Column(String, ForeignKey("tbl_chats.id"), nullable=True, index=True)
    status = Column(String, nullable=False)
    schema_version = Column(String, nullable=False)
    content = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ReportDocument(Base):
    __tablename__ = "tbl_report_documents"

    id = Column(String, primary_key=True, default=gen_id)
    report_instance_id = Column(String, ForeignKey("tbl_report_instances.id"), nullable=False, index=True)
    artifact_kind = Column(String, nullable=False)
    source_format = Column(String, nullable=True)
    generation_mode = Column(String, nullable=False, default="sync")
    mime_type = Column(String, nullable=False)
    storage_key = Column(String, nullable=False)
    status = Column(String, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ExportJob(Base):
    __tablename__ = "tbl_export_jobs"

    id = Column(String, primary_key=True, default=gen_id)
    report_instance_id = Column(String, ForeignKey("tbl_report_instances.id"), nullable=False, index=True)
    current_format = Column(String, nullable=False)
    status = Column(String, nullable=False)
    dependency_job_id = Column(String, ForeignKey("tbl_export_jobs.id"), nullable=True)
    exporter_backend = Column(String, nullable=False, default="local")
    request_payload_hash = Column(String, nullable=False, default="")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)


class SystemSetting(Base):
    __tablename__ = "tbl_system_settings"

    id = Column(String, primary_key=True, default="global")
    completion_config = Column(JSON, nullable=False, default=dict)
    embedding_config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Feedback(Base):
    __tablename__ = "tbl_feedbacks"

    id = Column(String, primary_key=True, default=gen_id)
    user_ip = Column(String, nullable=True)
    submitter = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    priority = Column(String, nullable=False, default="medium")
    images = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
