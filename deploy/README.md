# `deploy` — Ansible role for Koji (RPM, RHEL-based)

Installs and configures Koji from the PlatformOS RPM repository on
RHEL / Rocky Linux / AlmaLinux 9 and 10. This role replaces the pip-based
install used by `containers/` with proper RPM packages.

`deploy/` **is** the role root (the role name is `deploy`). The example
playbook, inventory and `group_vars/` live next to the role files.

## What it does

For each host it:

1. asserts the OS is a supported EL release and all required variables are set;
2. adds the `platformos-koji` yum repository;
3. installs the RPM package set for the components enabled on that host;
4. renders the Koji config files from Jinja2 templates;
5. creates `/mnt/koji`;
6. enables/starts the relevant systemd services (`httpd`, `kojira`, `kojid`,
   `kojivmd`) and optionally the `koji-sweep-db` / `koji-gc` timers.

### Components and packages

| Component | RPMs installed | Services |
|---|---|---|
| `client` (always) | `koji`, `python3-koji`, `python3-koji-cli-plugins` | — |
| `hub` | `koji-hub`, `python3-koji-hub`, `koji-hub-plugins`, `python3-koji-hub-plugins` | `httpd`, optional `koji-sweep-db.timer` |
| `web` | `koji-web`, `python3-koji-web` | `httpd` |
| `kojira` | `koji-utils` | `kojira.service`, optional `koji-gc.timer` |
| `builder` | `koji-builder`, `koji-builder-plugins` | `kojid.service` |
| `vm` | `koji-vm` | `kojivmd.service` |

`dnf` resolves the remaining runtime dependencies (`httpd`,
`python3-mod_wsgi`, `python3-psycopg2`, `python3-cheetah`, `python3-defusedxml`,
`python3-qpid-proton`, `mock`, `createrepo_c`, `python3-libcomps`,
`python3-multilib`, `squashfs-tools`, `python3-libvirt`, `qemu-img`,
`virt-clone`, …) from the standard repositories.

## Prerequisites

- **Ansible >= 2.15**, `become: true` on the target hosts.
- **EPEL and CRB/PowerTools enabled on every host.** The role does not manage
  OS-level repositories. For example on EL9:

  ```sh
  dnf install -y epel-release dnf-plugins-core
  dnf config-manager --set-enabled crb
  ```

- **An existing PostgreSQL instance.** The role does not install PostgreSQL or
  load `schemas/schema.sql`. It only writes the `DB*` values into
  `/etc/koji-hub/hub.conf`. The hub, web and kojira hosts must be able to reach
  the database. See `containers/db/` for the schema and the `admin`/`kojira`
  seed users used by the container deployment.
- **Shared storage.** `/mnt/koji` (`koji_topdir`) is created locally and owned
  by `apache` on hub/web hosts. Making it a shared/NFS volume across hub,
  builder, kojira and vm hosts is an operator task.
- **Network access** to `https://dl.platform-os.org/platformos/<major>/koji/`.

## Repository layout and EL10

The repository is versioned by EL major version:

| URL | Status |
|---|---|
| `https://dl.platform-os.org/platformos/9/koji/` | published (13 `noarch` RPMs, `1.35.3-1.el9`) |
| `https://dl.platform-os.org/platformos/10/koji/` | **not published yet** (404) |

`koji_repo_baseurl` is templated with
`ansible_facts['distribution_major_version']`, so EL10 starts working as soon
as the packages are published. Until then, EL10 hosts will fail at the `dnf`
step. Because every Koji RPM is `noarch`, a temporary workaround is to
override the baseurl to the EL9 repository:

```yaml
# group_vars/koji_el10.yml
koji_repo_baseurl: "https://dl.platform-os.org/platformos/9/koji/"
```

The published repository has **no GPG key and no signed `repomd.xml`**, so
`koji_repo_gpgcheck` and `koji_repo_repo_gpgcheck` default to `false`. Set them
to `true` and provide `koji_repo_gpgkey` once signing is available.

## Layout

```
deploy/
├── ansible.cfg                # roles_path = .. so `roles: [deploy]` resolves
├── .ansible-lint
├── playbook.yml               # example playbook
├── inventory.ini              # example inventory with component groups
├── group_vars/                # per-component koji_components + shared secrets
├── defaults/main.yml          # every tunable variable
├── meta/main.yml              # galaxy metadata, EL9/EL10 platforms
├── handlers/main.yml          # restart httpd / kojira / kojid / kojivmd
├── tasks/
│   ├── main.yml               # orchestration
│   ├── assert.yml             # OS + component + secret validation
│   ├── repo.yml               # yum_repository
│   ├── packages.yml           # dnf
│   ├── config.yml             # templates
│   ├── storage.yml            # /mnt/koji
│   └── services.yml           # systemd
├── templates/                 # koji.conf, hub.conf, web.conf, kojira.conf,
│                              # kojid.conf, kojivmd.conf
└── molecule/default/          # docker scenario (rockylinux:9)
                               # molecule.yml, Dockerfile.j2,
                               # prepare/converge/verify.yml
```

## Usage

```sh
cd deploy
ansible-playbook -i inventory.ini playbook.yml
```

Run playbooks **from inside `deploy/`**: `ansible.cfg` sets `roles_path = ..`
so that the role named `deploy` resolves to `../deploy`. If you run from the
repository root instead, set `ANSIBLE_ROLES_PATH` explicitly:

```sh
ANSIBLE_ROLES_PATH=. ansible-playbook -i deploy/inventory.ini deploy/playbook.yml
```

`inventory.ini` defines the groups `koji_hub`, `koji_web`, `koji_kojira`,
`koji_builder`, `koji_vm` and `koji_db`, aggregated into `koji_servers`.
`group_vars/<group>.yml` selects the components for each group; `client` is
always added automatically.

To target a single group:

```sh
ansible-playbook -i inventory.ini playbook.yml --limit koji_hub
```

## Secrets

`group_vars/all.yml` ships development placeholders matching the container
defaults (`koji`, `change-me-secret`, `kojira`). Replace them before any real
deployment — encrypt the file with Ansible Vault:

```sh
ansible-vault encrypt group_vars/all.yml
ansible-playbook -i inventory.ini playbook.yml --ask-vault-pass
```

`tasks/assert.yml` fails early when a required secret is missing:

| Secret | Required for |
|---|---|
| `koji_db_password` | `hub` |
| `koji_web_secret` | `web` |
| `koji_kojira_password` | `kojira` |

All endpoints (`koji_hub_url`, `koji_files_url`, `koji_web_url`) are validated
as non-empty as well.

## Variables

All variables are defined in `defaults/main.yml`.

### Repository

| Variable | Default | Description |
|---|---|---|
| `koji_repo_name` | `platformos-koji` | Repository id used by `yum_repository` and `enablerepo`. |
| `koji_repo_file` | `platformos-koji` | Repo file name in `/etc/yum.repos.d/`. |
| `koji_repo_description` | `PlatformOS Koji RPM repository` | Repo description. |
| `koji_repo_baseurl` | `https://dl.platform-os.org/platformos/{{ distribution_major_version }}/koji/` | Templated by EL major version. |
| `koji_repo_enabled` | `true` | Enable the repo. |
| `koji_repo_gpgcheck` | `false` | Package GPG check (no key published). |
| `koji_repo_repo_gpgcheck` | `false` | Metadata GPG check (repomd.xml is unsigned). |
| `koji_repo_gpgkey` | `""` | Optional GPG key URL. |
| `koji_version` | `""` | Optional version pin appended to package names, e.g. `1.35.3-1.el9`. |

### Components and platform

| Variable | Default | Description |
|---|---|---|
| `koji_components` | `[client]` | Components to deploy on this host. |
| `koji_known_components` | `[client, hub, web, kojira, builder, vm]` | Used for validation. |
| `koji_component_packages` | see `defaults/main.yml` | Component → RPM name mapping. |
| `koji_supported_major_versions` | `["9", "10"]` | Allowed `distribution_major_version` values. |

### Endpoints and storage

| Variable | Default | Description |
|---|---|---|
| `koji_hub_host` | first host in `koji_hub` group, else `localhost` | Hub hostname used to build URLs. |
| `koji_web_host` | first host in `koji_web` group, else `localhost` | Web hostname. |
| `koji_db_host` | first host in `koji_db` group, else `localhost` | PostgreSQL host for `hub.conf`. |
| `koji_hub_url` | `http://{{ koji_hub_host }}/kojihub` | XML-RPC endpoint. |
| `koji_files_url` | `http://{{ koji_hub_host }}/kojifiles` | File/package endpoint. |
| `koji_web_url` | `http://{{ koji_web_host }}/koji` | Web UI endpoint. |
| `koji_topdir` | `/mnt/koji` | Shared Koji top directory. |
| `koji_manage_storage` | `true` | Create/manage `koji_topdir`. |
| `koji_topdir_mode` | `0755` | Mode of `koji_topdir`. |
| `koji_topdir_owner` / `koji_topdir_group` | `apache` | Used only on hub/web hosts; other hosts keep `root`. |

### Database (existing, not managed)

| Variable | Default |
|---|---|
| `koji_db_name` | `koji` |
| `koji_db_user` | `koji` |
| `koji_db_host` | see above |
| `koji_db_port` | `5432` |
| `koji_db_password` | `""` (required for `hub`) |

### Authentication and logging

| Variable | Default |
|---|---|
| `koji_web_secret` | `""` (required for `web`) |
| `koji_web_site_name` | `Koji Web` |
| `koji_web_auth_type` | `password` |
| `koji_web_allow_registration` | `true` |
| `koji_web_force_ssl` | `false` |
| `koji_web_login_timeout` | `72` |
| `koji_hub_login_creates_user` | `true` |
| `koji_kojira_user` | `kojira` |
| `koji_kojira_password` | `""` (required for `kojira`) |
| `koji_kojira_logfile` | `/var/log/kojira.log` |
| `koji_log_level` | `INFO` |
| `koji_hub_log_format` / `koji_web_log_format` | `%(asctime)s [%(levelname)s] …` |

> Koji reads these INI files with `configparser` using `raw=True`, so the
> `%(...)s` fields in the log formats are safe.

### Services

| Variable | Default | Description |
|---|---|---|
| `koji_httpd_service` | `httpd` | httpd unit name. |
| `koji_kojira_service` | `kojira.service` | kojira unit name. |
| `koji_kojid_service` | `kojid.service` | kojid unit name. |
| `koji_kojivmd_service` | `kojivmd.service` | kojivmd unit name. |
| `koji_service_enabled` | `true` | Enable and start services; `false` stops and disables them. |
| `koji_sweep_db_timer_enabled` | `false` | Manage `koji-sweep-db.timer` on hub hosts. |
| `koji_gc_timer_enabled` | `false` | Manage `koji-gc.timer` on kojira hosts. |

### Builder / VM

| Variable | Default |
|---|---|
| `koji_builder_sleeptime` | `15` |
| `koji_builder_maxjobs` | `10` |
| `koji_builder_workdir` | `/tmp/koji` |
| `koji_builder_mockuser` | `kojibuilder` |
| `koji_builder_topurl` | `{{ koji_files_url }}` |
| `koji_vmd_sleeptime` / `koji_vmd_maxjobs` | `15` / `10` |
| `koji_vmd_workdir` | `/tmp/koji` |
| `koji_vmd_smtphost` | `localhost` |
| `koji_vmd_from_addr` | `Koji Build System <buildsys@localhost>` |

## Config files rendered

| Template | Destination | Owner / mode |
|---|---|---|
| `koji.conf.j2` | `/etc/koji.conf` | `root:root 0644` |
| `hub.conf.j2` | `/etc/koji-hub/hub.conf` | `root:apache 0640` |
| `web.conf.j2` | `/etc/kojiweb/web.conf` | `root:apache 0640` |
| `kojira.conf.j2` | `/etc/kojira/kojira.conf` | `root:root 0600` |
| `kojid.conf.j2` | `/etc/kojid/kojid.conf` | `root:root 0644` |
| `kojivmd.conf.j2` | `/etc/kojivmd/kojivmd.conf` | `root:root 0644` |

These are `%config(noreplace)` files in the RPMs. Rendering them from the role
is intentional — every value is a role variable — and `backup: true` keeps a
timestamped copy of the packaged default on the first change. Container-only
settings (`ErrorLog /dev/stderr`, `kojira -f --force-lock`) are deliberately
not carried over; the RPM-shipped httpd snippets
(`/etc/httpd/conf.d/kojihub.conf`, `kojiweb.conf`) are used as-is.

Each template notifies the matching handler, so a config change restarts the
affected service. Handlers are skipped when `koji_service_enabled: false` —
otherwise a restart would start a service the operator asked to keep stopped
and the next converge would report a spurious change.

## Testing

```sh
cd deploy
ansible-playbook -i inventory.ini playbook.yml --syntax-check
ansible-lint .
```

A Molecule scenario is included in `molecule/default/` (Docker driver,
`rockylinux:9` with systemd). The stock image has no `/usr/sbin/init`, so
`Dockerfile.j2` builds a systemd-enabled `molecule_local/rockylinux/rockylinux:9`
image and bakes in EPEL, CRB and the dnf metadata cache — otherwise every
converge spends several minutes refreshing metadata. `prepare.yml` verifies
those prerequisites, `converge.yml` deploys all components with services
stopped, and `verify.yml` checks packages, config files and rendered values.

```sh
pip install molecule 'molecule-plugins[docker]'
cd deploy && molecule test
```

Molecule requires Docker and outbound network access. The scenario deploys
with `koji_service_enabled: false` because there is no PostgreSQL or reachable
hub inside the test container.

## Known limitations

- EL10 packages are not published yet (see above).
- PostgreSQL, EPEL/CRB and shared `/mnt/koji` storage are operator
  responsibilities.
- HTTP only by default. Set `koji_hub_url` / `koji_web_url` / `koji_files_url`
  to `https://…` and `koji_web_force_ssl: true` behind a TLS terminator.
- Cert/Kerberos authentication is not configured by this role; the templates
  use password authentication to match `containers/`.
