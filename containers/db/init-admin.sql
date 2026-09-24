-- Seed the default admin user (usertype 0 = USER, password: admin) and grant
-- the 'admin' permission. Makes the fresh database usable out of the box.
-- WARNING: change the default password immediately after first login!

DO $$
DECLARE
    uid INTEGER;
    pid INTEGER;
BEGIN
    -- Create the admin user if it doesn't exist yet
    SELECT id INTO uid FROM users WHERE name = 'admin';
    IF uid IS NULL THEN
        INSERT INTO users (name, password, status, usertype)
        VALUES ('admin', 'admin', 0, 0)
        RETURNING id INTO uid;
    END IF;

    -- Grant the 'admin' permission (permission inserted by schema.sql)
    SELECT id INTO pid FROM permissions WHERE name = 'admin';
    IF pid IS NOT NULL THEN
        INSERT INTO user_perms (user_id, perm_id, creator_id)
        VALUES (uid, pid, uid)
        ON CONFLICT DO NOTHING;
    END IF;

    -- Create the 'kojira' service user (used by the kojira container)
    SELECT id INTO uid FROM users WHERE name = 'kojira';
    IF uid IS NULL THEN
        INSERT INTO users (name, password, status, usertype)
        VALUES ('kojira', 'kojira', 0, 0)
        RETURNING id INTO uid;
    END IF;

    -- Grant 'repo' permission to kojira so it can manage repositories
    SELECT id INTO pid FROM permissions WHERE name = 'repo';
    IF pid IS NOT NULL THEN
        INSERT INTO user_perms (user_id, perm_id, creator_id)
        VALUES (uid, pid, uid)
        ON CONFLICT DO NOTHING;
    END IF;
END $$;
