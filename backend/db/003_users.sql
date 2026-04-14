-- =============================================================================
-- Dyz-Art MAS — Users & Authentication
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'operator'
                               CHECK (role IN ('admin', 'operator', 'expert')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Default seed users
-- Passwords are pre-hashed with bcrypt (rounds=12).
-- IMPORTANT: change these passwords before deploying to production!
--
--   admin    / admin123   → role: admin
--   operator / operator123 → role: operator
--   expert   / expert123  → role: expert
-- ---------------------------------------------------------------------------

INSERT INTO users (email, username, password_hash, role) VALUES
    ('admin@dyzart.local',
     'admin',
     '$2b$12$wSWfWrGEyvPn4QD6dwDRu.rTYEYpML.jVJxyRO/snZkAxs92sfZ6W',
     'admin'),
    ('operator@dyzart.local',
     'operator',
     '$2b$12$ebJEzEH3vdYMzj6mUytTwOXHfUsBARwPoh9gxfQy.VEX1sPhFc.K6',
     'operator'),
    ('expert@dyzart.local',
     'expert',
     '$2b$12$0WKBWEerWIHym7yALxjejOdHfSHqfNUTA6EHXE9II1VmqS0DYUXKS',
     'expert')
ON CONFLICT (username) DO NOTHING;
