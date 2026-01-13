-- upgrade script to migrate the Koji database schema
-- from version 1.35 to 1.36

BEGIN;

INSERT INTO archivetypes (name, description, extensions) VALUES ('erofs', 'erofs image', 'erofs') ON CONFLICT DO NOTHING;
INSERT INTO archivetypes (name, description, extensions) VALUES ('erofs-compressed', 'Compressed erofs image', 'erofs.gz erofs.xz') ON CONFLICT DO NOTHING;
INSERT INTO archivetypes (name, description, extensions) VALUES ('squashfs', 'SquashFS image', 'squashfs') ON CONFLICT DO NOTHING;
INSERT INTO archivetypes (name, description, extensions) VALUES ('squashfs-compressed', 'Compressed SquashFS image', 'squashfs.gz squashfs.xz') ON CONFLICT DO NOTHING;
INSERT INTO archivetypes (name, description, extensions) VALUES ('wsl', 'Compressed tarball for Windows Subsystem for Linux', 'wsl') ON CONFLICT DO NOTHING;

-- https://pagure.io/koji/issue/3963
CREATE INDEX IF NOT EXISTS standard_buildroot_host_id on standard_buildroot(host_id);
CREATE INDEX IF NOT EXISTS standard_buildroot_repo_id on standard_buildroot(repo_id);
CREATE INDEX IF NOT EXISTS standard_buildroot_task_id on standard_buildroot(task_id);
CREATE INDEX IF NOT EXISTS standard_buildroot_create_event on standard_buildroot(create_event);
CREATE INDEX IF NOT EXISTS standard_buildroot_retire_event on standard_buildroot(retire_event);

-- new rpminfo fields for v6 support
ALTER TABLE rpminfo ADD COLUMN sigmd5 TEXT;
ALTER TABLE rpminfo ADD COLUMN sha1header TEXT;
ALTER TABLE rpminfo ADD COLUMN sha256header TEXT;
ALTER TABLE rpminfo ADD COLUMN sha3_256header TEXT;
CREATE INDEX rpminfo_sigmd5 ON rpminfo(sigmd5);
CREATE INDEX rpminfo_sha1header ON rpminfo(sha1header);
CREATE INDEX rpminfo_sha256header ON rpminfo(sha256header);
CREATE INDEX rpminfo_sha3_256header ON rpminfo(sha3_256header);
-- rpminfo.size can be null
ALTER TABLE rpminfo ALTER COLUMN size DROP NOT NULL;


COMMIT;
