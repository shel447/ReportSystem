from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON
from sqlalchemy.sql import func
from .database import Base
import uuid


def gen_id():
    return str(uuid.uuid4())


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    template_id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    report_type = Column(String, default="daily")
    scenario = Column(String, default="")
    match_keywords = Column(JSON, default=list)
    content_params = Column(JSON, default=list)
    outline = Column(JSON, default=list)
    output_formats = Column(JSON, default=lambda: ["pdf"])
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String, default="system")
    version = Column(String, default="1.0")


class ReportInstance(Base):
    __tablename__ = "report_instances"

    instance_id = Column(String, primary_key=True, default=gen_id)
    template_id = Column(String, nullable=False)
    template_version = Column(String, default="1.0")
    status = Column(String, default="draft")
    input_params = Column(JSON, default=dict)
    outline_content = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(String, default="system")


class ReportDocument(Base):
    __tablename__ = "report_documents"

    document_id = Column(String, primary_key=True, default=gen_id)
    instance_id = Column(String, nullable=False)
    template_id = Column(String, default="")
    format = Column(String, default="md")
    file_path = Column(String, default="")
    file_size = Column(Integer, default=0)
    version = Column(Integer, default=1)
    status = Column(String, default="ready")
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String, default="system")


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    task_id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, nullable=False, default="default")
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    source_instance_id = Column(String, default="")
    template_id = Column(String, default="")
    schedule_type = Column(String, default="recurring")
    cron_expression = Column(String, default="")
    timezone = Column(String, default="Asia/Shanghai")
    enabled = Column(Boolean, default=True)
    auto_generate_doc = Column(Boolean, default=True)
    time_param_name = Column(String, default="date")
    time_format = Column(String, default="%Y-%m-%d")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")
    total_runs = Column(Integer, default=0)
    success_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)


class ScheduledTaskExecution(Base):
    __tablename__ = "scheduled_task_executions"

    execution_id = Column(String, primary_key=True, default=gen_id)
    task_id = Column(String, nullable=False)
    status = Column(String, default="success")
    generated_instance_id = Column(String, nullable=True)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    input_params_used = Column(JSON, default=dict)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, default="default")
    messages = Column(JSON, default=list)
    matched_template_id = Column(String, nullable=True)
    instance_id = Column(String, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class SystemSetting(Base):
    __tablename__ = "system_settings"

    settings_id = Column(String, primary_key=True, default="global")
    completion_config = Column(JSON, default=dict)
    embedding_config = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TemplateSemanticIndex(Base):
    __tablename__ = "template_semantic_indices"

    template_id = Column(String, primary_key=True)
    semantic_text = Column(Text, default="")
    embedding_vector = Column(JSON, default=list)
    embedding_model = Column(String, default="")
    status = Column(String, default="stale")
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Feedback(Base):
    __tablename__ = "feedbacks"

    feedback_id = Column(String, primary_key=True, default=gen_id)
    user_ip = Column(String, nullable=True)
    submitter = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    priority = Column(String, default="medium")
    images = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
