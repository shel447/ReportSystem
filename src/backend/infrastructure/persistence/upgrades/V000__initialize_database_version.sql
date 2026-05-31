CREATE TABLE IF NOT EXISTS __db_schema_version (
    id INTEGER PRIMARY KEY,
    current_version INTEGER NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO __db_schema_version (id, current_version)
VALUES (1, 0);
