CREATE TABLE IF NOT EXISTS llm_runtime_settings (
    setting_key VARCHAR(64) PRIMARY KEY,
    provider    VARCHAR(32)  NOT NULL,
    model       VARCHAR(128) NOT NULL,
    updated_by  UUID REFERENCES users (id) ON DELETE SET NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

INSERT INTO llm_runtime_settings (setting_key, provider, model)
VALUES ('global', 'openai', 'gpt-4o')
ON CONFLICT (setting_key) DO NOTHING;
