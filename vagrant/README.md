# Koji all-in-one Vagrant VM

This Vagrant setup provisions a single Rocky Linux 9 VM with Koji installed from
the PlatformOS RPM repository:

- Repo: https://dl.platform-os.org/platformos/9/koji/
- Components: `client`, `hub`, `web`, `kojira`, `builder` (`kojid`), `vm` (`kojivmd`)
- Local PostgreSQL with the hub schema created by Alembic migrations and
  default users seeded

Provisioning uses `ansible_local` inside the guest and reuses the repository's
`deploy/` Ansible role.

## Requirements

- Vagrant
- VirtualBox or libvirt provider
- Enough RAM/CPU for an all-in-one Koji host (defaults: 4 vCPU, 4096 MB)

## Usage

```bash
cd vagrant
vagrant up
```

After provisioning:

- Web UI: `http://localhost:8080/koji/` (forwarded) or `http://192.168.56.10/koji/`
- Hub XML-RPC: `http://localhost:8081/kojihub` or `http://192.168.56.10/kojihub`
- Files: `http://192.168.56.10/kojifiles/`

## Default credentials

Development defaults, defined in `group_vars/all.yml`:

- Koji admin user: `admin` / `admin`
- Kojira user: `kojira` / `kojira`
- Builder user (used by `kojid`): `builder` / `builder`
- PostgreSQL: `koji` / `koji`
- Web secret: `change-me-secret`

**Change all secrets before using this VM outside a disposable local environment.**

## Useful commands

```bash
vagrant ssh
sudo systemctl status postgresql httpd kojira kojid kojivmd
sudo /usr/sbin/koji-hub-migrate current   # current schema revision (0001_baseline)
sudo /usr/sbin/koji-hub-migrate check     # no pending migrations
koji --server=http://localhost/kojihub --user=admin --password=admin --authtype=password hello
```

## Environment overrides

`Vagrantfile` supports:

- `KOJI_VAGRANT_BOX` (default `rockylinux/9`, has libvirt+virtualbox providers)
- `KOJI_VAGRANT_CPUS` (default `4`)
- `KOJI_VAGRANT_MEMORY` (default `4096`)
- `KOJI_VAGRANT_DISK_GB` (default `14`) — libvirt root disk size in GB; applied
  only when the VM is created (`vagrant destroy` + `vagrant up` to change an
  existing VM). The box's own declared size wins if it is larger.
- `KOJI_VAGRANT_IP` (default `192.168.56.10`)
- `KOJI_VAGRANT_HOST_HTTP` (default `8080`)
- `KOJI_VAGRANT_HOST_HUB` (default `8081`)

## Notes

- PostgreSQL is bootstrapped by `vagrant/playbook.yml`; the `deploy/` role only
  configures Koji to use an existing database. The hub schema is created by
  `koji-hub-migrate upgrade head` (the baseline Alembic revision), not by
  importing `schemas/schema.sql` by hand. If you are re-provisioning an older
  VM whose schema was loaded from `schema.sql`, the playbook detects that and
  runs `koji-hub-migrate stamp head` instead, so no tables are re-created.
  The VM sets `max_connections = 150` and caps Apache at 32 workers
  (`MaxRequestWorkers`)
  because the hub holds one DB connection per worker for the worker's lifetime;
  without those limits a busy hub can exhaust Postgres' connection slots.
  Seeding is done as the `postgres` superuser over the local socket, so a
  provisioning run is not blocked by exhausted non-superuser slots.
- Provisioning enables the SELinux booleans `httpd_can_network_connect_db`
  (hub → PostgreSQL) and `httpd_can_network_connect` (web → hub XML-RPC), so
  both work with SELinux in enforcing mode.
- The VM syncs this repository to `/opt/koji-src` via rsync.
- The libvirt provider uses `qemu:///system` (`qemu_use_session = false`).
  `qemu:///session` cannot create libvirt networks, so a `private_network` with
  an IP would fail with `Network <ip> is not available` unless that network
  already exists. The system connection creates the `192.168.56.0/24` network
  automatically; it requires access to the system libvirt socket.
- Builder/VM components are installed and enabled, but full build/VM operation
  may require additional host-specific configuration (mock/buildroots, libvirt
  storage/network, certificates/auth).
