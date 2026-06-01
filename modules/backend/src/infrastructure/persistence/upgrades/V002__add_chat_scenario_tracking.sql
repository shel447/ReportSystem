ALTER TABLE tbl_chats ADD COLUMN scenario_key VARCHAR;

CREATE INDEX IF NOT EXISTS ix_tbl_chats_scenario_key ON tbl_chats (scenario_key);
