-- =============================================================================
-- Migration 001: Rename users.role 'operator' → 'client'
--
-- Context: the original schema used roles (admin, operator, expert). The new
-- three-role UI uses (admin, client, expert). This migration is idempotent and
-- safe to re-run.
-- =============================================================================

DO $$
BEGIN
    -- Drop the old CHECK constraint so we can relax it before updating rows.
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'users_role_check' AND conrelid = 'users'::regclass
    ) THEN
        ALTER TABLE users DROP CONSTRAINT users_role_check;
    END IF;

    -- Relax to any VARCHAR during the data migration.
    UPDATE users SET role = 'client' WHERE role = 'operator';

    -- Flip the default.
    ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client';

    -- Re-add the CHECK with the new allowed set.
    ALTER TABLE users
        ADD CONSTRAINT users_role_check
        CHECK (role IN ('admin', 'client', 'expert'));
END $$;
