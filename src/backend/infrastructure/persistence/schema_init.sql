-- SQLite bootstrap schema for ReportSystemV2.
-- Runtime authority remains SQLAlchemy ORM metadata in src/backend/infrastructure/persistence/models.py.
-- Keep this file aligned with the current ORM target schema; do not regenerate from report_system.db.

PRAGMA foreign_keys = ON;

-- tbl_feedbacks

CREATE TABLE IF NOT EXISTS tbl_feedbacks (
	id VARCHAR NOT NULL, 
	user_ip VARCHAR, 
	submitter VARCHAR, 
	content TEXT NOT NULL, 
	priority VARCHAR NOT NULL, 
	images JSON NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

-- tbl_report_templates

CREATE TABLE IF NOT EXISTS tbl_report_templates (
	id VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT NOT NULL, 
	schema_version VARCHAR NOT NULL, 
	content JSON NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

-- tbl_system_settings

CREATE TABLE IF NOT EXISTS tbl_system_settings (
	id VARCHAR NOT NULL, 
	completion_config JSON NOT NULL, 
	embedding_config JSON NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id)
);

-- tbl_users

CREATE TABLE IF NOT EXISTS tbl_users (
	id VARCHAR NOT NULL, 
	display_name VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	profile_json JSON NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	last_seen_at DATETIME, 
	PRIMARY KEY (id)
);

-- tbl_conversations

CREATE TABLE IF NOT EXISTS tbl_conversations (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	fork_meta JSON NOT NULL, 
	status VARCHAR NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES tbl_users (id)
);

CREATE INDEX IF NOT EXISTS ix_tbl_conversations_user_id ON tbl_conversations (user_id);

-- tbl_chats

CREATE TABLE IF NOT EXISTS tbl_chats (
	id VARCHAR NOT NULL, 
	conversation_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	content JSON NOT NULL, 
	action JSON, 
	meta JSON NOT NULL, 
	seq_no INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES tbl_conversations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES tbl_users (id)
);

CREATE INDEX IF NOT EXISTS ix_tbl_chats_conversation_id ON tbl_chats (conversation_id);

CREATE INDEX IF NOT EXISTS ix_tbl_chats_user_id ON tbl_chats (user_id);

-- tbl_template_instances

CREATE TABLE IF NOT EXISTS tbl_template_instances (
	id VARCHAR NOT NULL, 
	template_id VARCHAR NOT NULL, 
	conversation_id VARCHAR NOT NULL, 
	chat_id VARCHAR, 
	user_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	capture_stage VARCHAR NOT NULL, 
	revision INTEGER NOT NULL, 
	schema_version VARCHAR NOT NULL, 
	content JSON NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(template_id) REFERENCES tbl_report_templates (id), 
	FOREIGN KEY(conversation_id) REFERENCES tbl_conversations (id), 
	FOREIGN KEY(chat_id) REFERENCES tbl_chats (id), 
	FOREIGN KEY(user_id) REFERENCES tbl_users (id)
);

CREATE INDEX IF NOT EXISTS ix_tbl_template_instances_chat_id ON tbl_template_instances (chat_id);

CREATE INDEX IF NOT EXISTS ix_tbl_template_instances_conversation_id ON tbl_template_instances (conversation_id);

CREATE INDEX IF NOT EXISTS ix_tbl_template_instances_template_id ON tbl_template_instances (template_id);

CREATE INDEX IF NOT EXISTS ix_tbl_template_instances_user_id ON tbl_template_instances (user_id);

-- tbl_report_instances

CREATE TABLE IF NOT EXISTS tbl_report_instances (
	id VARCHAR NOT NULL, 
	template_id VARCHAR NOT NULL, 
	template_instance_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	source_conversation_id VARCHAR, 
	source_chat_id VARCHAR, 
	status VARCHAR NOT NULL, 
	schema_version VARCHAR NOT NULL, 
	content JSON NOT NULL, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(template_id) REFERENCES tbl_report_templates (id), 
	FOREIGN KEY(template_instance_id) REFERENCES tbl_template_instances (id), 
	FOREIGN KEY(user_id) REFERENCES tbl_users (id), 
	FOREIGN KEY(source_conversation_id) REFERENCES tbl_conversations (id), 
	FOREIGN KEY(source_chat_id) REFERENCES tbl_chats (id)
);

CREATE INDEX IF NOT EXISTS ix_tbl_report_instances_source_chat_id ON tbl_report_instances (source_chat_id);

CREATE INDEX IF NOT EXISTS ix_tbl_report_instances_source_conversation_id ON tbl_report_instances (source_conversation_id);

CREATE INDEX IF NOT EXISTS ix_tbl_report_instances_template_id ON tbl_report_instances (template_id);

CREATE INDEX IF NOT EXISTS ix_tbl_report_instances_template_instance_id ON tbl_report_instances (template_instance_id);

CREATE INDEX IF NOT EXISTS ix_tbl_report_instances_user_id ON tbl_report_instances (user_id);

-- tbl_export_jobs

CREATE TABLE IF NOT EXISTS tbl_export_jobs (
	id VARCHAR NOT NULL, 
	report_instance_id VARCHAR NOT NULL, 
	current_format VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	dependency_job_id VARCHAR, 
	exporter_backend VARCHAR NOT NULL, 
	request_payload_hash VARCHAR NOT NULL, 
	started_at DATETIME, 
	finished_at DATETIME, 
	error_code VARCHAR, 
	error_message TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(report_instance_id) REFERENCES tbl_report_instances (id), 
	FOREIGN KEY(dependency_job_id) REFERENCES tbl_export_jobs (id)
);

CREATE INDEX IF NOT EXISTS ix_tbl_export_jobs_report_instance_id ON tbl_export_jobs (report_instance_id);

-- tbl_report_documents

CREATE TABLE IF NOT EXISTS tbl_report_documents (
	id VARCHAR NOT NULL, 
	report_instance_id VARCHAR NOT NULL, 
	artifact_kind VARCHAR NOT NULL, 
	source_format VARCHAR, 
	generation_mode VARCHAR NOT NULL, 
	mime_type VARCHAR NOT NULL, 
	storage_key VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	error_message TEXT, 
	created_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	updated_at DATETIME DEFAULT (CURRENT_TIMESTAMP) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(report_instance_id) REFERENCES tbl_report_instances (id)
);

CREATE INDEX IF NOT EXISTS ix_tbl_report_documents_report_instance_id ON tbl_report_documents (report_instance_id);
