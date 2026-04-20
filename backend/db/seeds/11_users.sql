-- =============================================================================
-- Seed: users — стандартні облікові записи для dev-середовища
-- Паролі пре-гешовані bcrypt (rounds=12). ЗМІНИ паролі перед деплоєм у prod!
--   admin    / admin123    → role: admin
--   operator / operator123 → role: operator
--   expert   / expert123   → role: expert
-- =============================================================================

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
