-- upgrade script to migrate the Koji database schema
-- from version 1.35 to 1.36

BEGIN;

-- Kerberos/GSSAPI authentication has been removed, so the principals
-- associated with user accounts are no longer tracked.
DROP TABLE IF EXISTS user_krb_principals;

-- The sessions.authtype enum lost its KERBEROS (1) and GSSAPI (3) members,
-- which renumbers SSL from 2 to 1. Sessions are short lived, so we close out
-- anything still carrying a removed authtype and remap the old SSL value.
-- Order matters: the DELETE must see the pre-migration numbering.
DELETE FROM sessions WHERE authtype IN (1, 3);
UPDATE sessions SET authtype = 1 WHERE authtype = 2;

COMMIT;
