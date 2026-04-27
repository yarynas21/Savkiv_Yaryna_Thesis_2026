CREATE TABLE IF NOT EXISTS session_metrics (
    thread_id                 VARCHAR(64) PRIMARY KEY,
    graph_name                VARCHAR(32)  NOT NULL DEFAULT 'full',
    llm_calls_total           INTEGER      NOT NULL DEFAULT 0,
    llm_latency_total_ms      NUMERIC(18, 2) NOT NULL DEFAULT 0,
    llm_total_cost_usd        NUMERIC(18, 6) NOT NULL DEFAULT 0,
    agent_processing_total_ms NUMERIC(18, 2) NOT NULL DEFAULT 0,
    model_active              VARCHAR(128),
    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session_metrics_by_model (
    thread_id            VARCHAR(64)   NOT NULL REFERENCES session_metrics (thread_id) ON DELETE CASCADE,
    model                VARCHAR(128)  NOT NULL,
    calls_total          INTEGER       NOT NULL DEFAULT 0,
    input_tokens_total   BIGINT        NOT NULL DEFAULT 0,
    output_tokens_total  BIGINT        NOT NULL DEFAULT 0,
    latency_total_ms     NUMERIC(18, 2) NOT NULL DEFAULT 0,
    total_cost_usd       NUMERIC(18, 6) NOT NULL DEFAULT 0,
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (thread_id, model)
);

CREATE INDEX IF NOT EXISTS idx_session_metrics_updated_at
    ON session_metrics (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_session_metrics_by_model_model
    ON session_metrics_by_model (model);
