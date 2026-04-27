-- =============================================================================
-- Migration 002: Create interview_sessions table.
--
-- Stores persisted client interviews so that experts (technologists) can pick
-- them up later and continue the pipeline from the technologist node onwards.
-- Idempotent: IF NOT EXISTS everywhere.
-- =============================================================================

CREATE TABLE IF NOT EXISTS interview_sessions (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id            UUID         NOT NULL UNIQUE,
    client_user_id       UUID         NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title                TEXT,
    status               VARCHAR(20)  NOT NULL
                                      CHECK (status IN ('in_progress', 'completed', 'processed')),
    messages             JSONB        NOT NULL DEFAULT '[]'::jsonb,
    collected_data       JSONB,
    expert_user_id       UUID         REFERENCES users (id) ON DELETE SET NULL,
    production_thread_id UUID,
    work_order           JSONB,
    cost_estimates       JSONB,
    excel_bytes          BYTEA,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at         TIMESTAMPTZ,
    processed_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_interviews_status ON interview_sessions (status);
CREATE INDEX IF NOT EXISTS idx_interviews_client ON interview_sessions (client_user_id);
CREATE INDEX IF NOT EXISTS idx_interviews_expert ON interview_sessions (expert_user_id);
