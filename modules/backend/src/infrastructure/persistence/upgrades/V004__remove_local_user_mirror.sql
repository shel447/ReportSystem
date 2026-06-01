DROP INDEX IF EXISTS ix_tbl_export_jobs_report_instance_id;
DROP INDEX IF EXISTS ix_tbl_export_jobs_user_id;
DROP INDEX IF EXISTS ix_tbl_report_documents_report_instance_id;
DROP INDEX IF EXISTS ix_tbl_report_instances_source_chat_id;
DROP INDEX IF EXISTS ix_tbl_report_instances_source_conversation_id;
DROP INDEX IF EXISTS ix_tbl_report_instances_template_id;
DROP INDEX IF EXISTS ix_tbl_report_instances_template_instance_id;
DROP INDEX IF EXISTS ix_tbl_report_instances_user_id;
DROP INDEX IF EXISTS ix_tbl_template_instances_chat_id;
DROP INDEX IF EXISTS ix_tbl_template_instances_conversation_id;
DROP INDEX IF EXISTS ix_tbl_template_instances_template_id;
DROP INDEX IF EXISTS ix_tbl_template_instances_user_id;

ALTER TABLE tbl_export_jobs RENAME TO legacy_v004_export_jobs;
ALTER TABLE tbl_report_documents RENAME TO legacy_v004_report_documents;
ALTER TABLE tbl_report_instances RENAME TO legacy_v004_report_instances;
ALTER TABLE tbl_template_instances RENAME TO legacy_v004_template_instances;

CREATE TABLE tbl_template_instances (
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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(template_id) REFERENCES tbl_report_templates (id)
);
CREATE INDEX ix_tbl_template_instances_chat_id ON tbl_template_instances (chat_id);
CREATE INDEX ix_tbl_template_instances_conversation_id ON tbl_template_instances (conversation_id);
CREATE INDEX ix_tbl_template_instances_template_id ON tbl_template_instances (template_id);
CREATE INDEX ix_tbl_template_instances_user_id ON tbl_template_instances (user_id);

INSERT INTO tbl_template_instances SELECT * FROM legacy_v004_template_instances;

CREATE TABLE tbl_report_instances (
    id VARCHAR NOT NULL,
    template_id VARCHAR NOT NULL,
    template_instance_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    source_conversation_id VARCHAR,
    source_chat_id VARCHAR,
    status VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    content JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(template_id) REFERENCES tbl_report_templates (id),
    FOREIGN KEY(template_instance_id) REFERENCES tbl_template_instances (id)
);
CREATE INDEX ix_tbl_report_instances_source_chat_id ON tbl_report_instances (source_chat_id);
CREATE INDEX ix_tbl_report_instances_source_conversation_id ON tbl_report_instances (source_conversation_id);
CREATE INDEX ix_tbl_report_instances_template_id ON tbl_report_instances (template_id);
CREATE INDEX ix_tbl_report_instances_template_instance_id ON tbl_report_instances (template_instance_id);
CREATE INDEX ix_tbl_report_instances_user_id ON tbl_report_instances (user_id);

INSERT INTO tbl_report_instances SELECT * FROM legacy_v004_report_instances;

CREATE TABLE tbl_export_jobs (
    id VARCHAR NOT NULL,
    report_instance_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
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
CREATE INDEX ix_tbl_export_jobs_report_instance_id ON tbl_export_jobs (report_instance_id);
CREATE INDEX ix_tbl_export_jobs_user_id ON tbl_export_jobs (user_id);

INSERT INTO tbl_export_jobs SELECT * FROM legacy_v004_export_jobs;

CREATE TABLE tbl_report_documents (
    id VARCHAR NOT NULL,
    report_instance_id VARCHAR NOT NULL,
    artifact_kind VARCHAR NOT NULL,
    source_format VARCHAR,
    generation_mode VARCHAR NOT NULL,
    mime_type VARCHAR NOT NULL,
    storage_key VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(report_instance_id) REFERENCES tbl_report_instances (id)
);
CREATE INDEX ix_tbl_report_documents_report_instance_id ON tbl_report_documents (report_instance_id);

INSERT INTO tbl_report_documents SELECT * FROM legacy_v004_report_documents;

DROP TABLE legacy_v004_export_jobs;
DROP TABLE legacy_v004_report_documents;
DROP TABLE legacy_v004_report_instances;
DROP TABLE legacy_v004_template_instances;
DROP TABLE tbl_users;
