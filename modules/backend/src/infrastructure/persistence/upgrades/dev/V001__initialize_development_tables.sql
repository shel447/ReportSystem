CREATE TABLE IF NOT EXISTS dev_system_settings (
    id VARCHAR NOT NULL,
    completion_config JSON NOT NULL,
    embedding_config JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS dev_feedbacks (
    id VARCHAR NOT NULL,
    user_ip VARCHAR,
    submitter VARCHAR,
    content TEXT NOT NULL,
    priority VARCHAR NOT NULL,
    images JSON NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);
