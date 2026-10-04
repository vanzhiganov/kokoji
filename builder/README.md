# builder/

`koji-builder` is the daemon that runs on Koji **build machines**. It polls the
hub for work, and executes whatever tasks the scheduler hands it — compiling
RPMs in mock chroots, building Maven artifacts, assembling disk images, and
generating repository metadata.

It is the only component in the tree that must be installed on a node that is
*not* part of the hub itself. A builder node needs no database, no web server
and no local hub; it only needs the hub's XML-RPC and file endpoints to be
reachable, plus a shared `topdir`.

## Contents

| File | Lines | Purpose |
|---|---:|---|
| `kojid` | 6981 | the daemon itself |
| `kojid.conf` | 208 | configuration, fully commented |
| `kojid.service` | 18 | systemd unit |
| `kojid.init` | 99 | legacy SysV init script (reads `kojid.sysconfig`) |
| `kojid.sysconfig` | 3 | variables consumed by `kojid.init` |
| `mergerepos` | 370 | legacy repo-merge helper, **Python 2 only** (see below) |
| `Makefile` | 38 | standalone install target, used by `koji.spec` |

`kojid` is an extensionless executable script, not an importable module — it is
installed to `%{_sbindir}` and is run directly, never imported.

### Code that does *not* live here

The task framework is shared with the other daemons and lives in the top-level
package:

- `koji/daemon.py` — `TaskManager` (`daemon.py:720`), the scheduling loop,
  per-task `fork`, log upload, and `SCM` (`:186`) which dispatches to SCM plugins
- `koji/tasks.py` — `BaseTaskHandler` (`:296`) and the generic handlers
  (`sleep`, `fork`, `subtask`, `restartHosts`, …)
- `koji/__init__.py` — `ClientSession`, the RPC client and its auth methods

This is why `kojid` cannot be tested or imported as a unit: it executes its
options parser and login at import time.

## Execution model

`main()` (`kojid:123-186`) runs a single flat loop:

```
while True:
    updateBuildroots()      # create/reclaim buildroots; reap expired ones
    updateTasks()           # notice tasks that were reassigned away from us
    getNextTask()           # ask the hub for work, fork and execute
    if nothing was taken: sleep(sleeptime)
```

Two consequences worth knowing:

- **Each task runs in its own forked process.** `TaskManager.forkTask()`
  (`koji/daemon.py:1392`) calls `os.fork()`, sets a new process group, and
  hands the child a `subsession()`. Nothing a task does can take the daemon
  down; the parent keeps polling. Sleep is skipped while a task is held, so a
  busy builder does not idle between tasks.
- **Signals are minimal.** `SIGTERM` exits, `SIGUSR1` triggers a graceful
  restart by re-`execv`ing itself (`kojid:143-144`, handler at `:140-142`). A
  task process that ignores `SIGTERM` is escalated by `_killChildren` in
  `koji/daemon.py:1205`.

`getNextTask()` never searches for a task. The **hub** decides what a host may
run and pushes assignments; kojid filters its own assignment list
(`koji/daemon.py:1039-1073`) and refuses anything whose `host_id` is not its
own. Load balancing is the hub's scheduler, not kojid's.

### Readiness

`readyForTask()` (`koji/daemon.py:1272`) gates every claim on disk space
(`minspace`, default 8192 MB per buildroot), job count (`maxjobs`, default 10),
and buildroot availability. `checkSpace()` reports a host as busy rather than
failing a task when a buildroot cannot be created.

## Task handlers

A class becomes a task handler by declaring `Methods`. Handlers are discovered
by scanning, not by a registry: `findHandlers(globals())` and
`findHandlers(vars(koji.tasks))` at startup (`kojid:127-129`), and
`registerEntries` for each plugin (`koji/daemon.py:757-765`).

### Declared in `builder/kojid`

| Method | Class | Group |
|---|---|---|
| `build` | `BuildTask` | RPM |
| `buildArch` | `BuildArchTask` | RPM |
| `chainbuild` | `ChainBuildTask` | RPM |
| `wrapperRPM` | `WrapperRPMTask` | RPM |
| `rebuildSRPM` | `RebuildSRPM` | RPM |
| `buildSRPMFromSCM` | `BuildSRPMFromSCMTask` | RPM |
| `tagBuild` | `TagBuildTask` | RPM |
| `maven` | `MavenTask` | Maven |
| `buildMaven` | `BuildMavenTask` | Maven |
| `chainmaven` | `ChainMavenTask` | Maven |
| `image` | `BuildBaseImageTask` | image |
| `createImage` | `BaseImageTask` | image |
| `indirectionimage` | `BuildIndirectionImageTask` | image |
| `appliance` | `BuildApplianceTask` | image |
| `createAppliance` | `ApplianceTask` | image |
| `livecd` | `BuildLiveCDTask` | image |
| `createLiveCD` | `LiveCDTask` | image |
| `livemedia` | `BuildLiveMediaTask` | image |
| `createLiveMedia` | `LiveMediaTask` | image |
| `newRepo` | `NewRepoTask` | repo |
| `createrepo` | `CreaterepoTask` | repo |
| `distRepo` | `NewDistRepoTask` | repo |
| `createdistrepo` | `createDistRepoTask` | repo |
| `tagNotification` | `TagNotificationTask` | notification |
| `buildNotification` | `BuildNotificationTask` | notification |

Image work is a three-stage chain: the `Build*Image*` classes generate a kickstart
or appliance description, `createImage`/`createLiveCD`/… run it through **oz**
(`koji.daemon.OzImageTask`, `kojid:3980`), and `indirectionimage` resolves a
minimal boot image. The `OzImageTask` family drives a KVM/qemu guest, which is
why `qemu-img`, `guestfs` and `mksquashfs` appear in the requirements.

### Declared in `koji/tasks.py` (also served by kojid)

`someMethod`, `sleep`, `fork`, `waittest`, `subtask`, `default`, `shutdown`,
`restart`, `restartVerify`, `restartHosts`, `dependantTask`, `waitrepo`.

## Buildroots and mock

`BuildRoot` (`kojid:190`) wraps one chroot. Its constructor is dual-mode:
called with a dict or an id it *adopts* an existing buildroot via `_load`,
called with a tag it creates one via `_new`. `_new` then writes a mock config
into `/etc/mock/koji/` (`_writeMockConfig`, `kojid:268`) and registers the
buildroot with the hub so it appears in the web UI.

Buildroot identity is the triple `tag-<buildroot_id>-<repo_id>`. Expiry is
driven by two delays: `buildroot_basic_cleanup_delay` (default 120s) and
`buildroot_final_cleanup_delay` (default 86400s). kojid only *reaps* them on
its next `updateBuildroots()` pass, so an offline builder's buildroots linger
until it returns.

`BuildRootLogs` (`kojid:929`) uploads task output, optionally with timestamps
when `log_timestamps` is set — that doubles the number of files transferred, so
it is off by default.

Note that `armhfp` is silently rewritten to `armv7hl` as `target_arch`
(`kojid:249-252`) because `armhfp` is not a valid autoconf architecture.

## Plugins

Two independent plugin mechanisms:

**Task handlers** — loaded from `pluginpath` (default
`/usr/lib/koji-builder-plugins`) via `plugin =` in `kojid.conf`. A plugin module
may export task handler classes and callables carrying a `callbacks` attribute.
Shipped in `plugins/builder/`: `dud`, `kiwi`, `runroot`, `save_failed_tree`,
`scmpolicy`. None are enabled by default.

**SCM handlers** — registered through `koji.daemon.SCM`, which dispatches a
source URL to a plugin implementing `checkout`/`get_source`. This is how
`allowed_scms` tuples (`host:repository[:use_common[:source_cmd]]`) are
enforced. `assert_allowed` (`koji/daemon.py:341`) is checked against
`allowed_scms_use_config` and, when `allowed_scms_use_policy` is enabled,
against the hub's `build_from_scm` policy — if both are active **both**
assertions apply and the policy result overrides the config one.

**Callback points** fired by handlers:

| Callback | Where |
|---|---|
| `preSCMCheckout` / `postSCMCheckout` | `kojid:1920,1925,1945,1951,2263,2267,3275,3279,4015,4019,4863,4868,5318,5323` |
| `postCreateRepo` | `kojid:5989` |
| `postCreateDistRepo` | `kojid:6295` |

`save_failed_tree.conf` ships with `paths = */tmp/krb5cc */etc/*.keytab` — a
Kerberos-era filter that is now inert but harmless. Remove it if you want the
config to reflect the current codebase.

## Authentication

kojid must log in to the hub as *some* user. Two methods are supported; at
startup kojid picks one (`kojid:6939-6956`) and quits if neither yields a
login.

### Username and password

The simplest option and the one to use against a plain-HTTP hub:

```ini
[kojid]
server = http://hub.example.com/kojihub
topurl  = http://hub.example.com/kojifiles
topdir  = /mnt/koji
workdir = /tmp/koji

user     = builder1.example.com
password = <the-password>
```

**The login name must be byte-identical to the hostname you passed to
`koji add-host`.** This is the single most common way to end up with a builder
that never works. The hub derives "which host is this session?" purely from
the session's `user_id`:

```python
# kojihub/auth.py:591-597
def _getHostId(self):
    query = QueryProcessor(tables=['host'], columns=['id'],
                           clauses=['user_id = %(uid)d'],
                           values={'uid': self.user_id})
    return query.singleValue(strict=False)
```

A name that does not match resolves to `None`, so `getLoadData()` returns an
empty task list and `verifyHost()` (`kojihub/kojihub.py:178`) rejects
everything. The builder logs in fine, reports itself healthy, and is never
given a single task — **no error is emitted anywhere.**

The account itself can be created either way, because the hub tolerates
builder self-registration:

```bash
# admin creates the host and its user up front, then sets the password
koji add-host builder1.example.com x86_64
koji enable-host builder1.example.com
koji add-host-to-channel builder1.example.com x86_64
koji set-host-password builder1.example.com     # prompts twice, never takes
                                                # the password in argv

# ...or let LoginCreatesUser do it: kojid logs in first and the hub creates
# the user, which addHost then finds and reuses (kojihub/kojihub.py:13739-13750)
```

### Setting the password

`set-host-password` is the supported way to (re)set the credential kojid logs
in with. It calls `RootExports.setHostPassword`
(`kojihub/kojihub.py:13782`), which requires the `admin` permission, resolves
the hostname through `get_host(strict=True)` — so the name must belong to a
**registered host** — and then writes to the linked user's `password` column.

`set-user-password <username>` does the same for any account, hosts included.
It is what you want to recover a locked-out human administrator; prefer
`set-host-password` for builders, since it also proves the name is a host.

Neither command accepts a password as an argument. Without
`--password-stdin` they prompt twice through `getpass`, so the value never
reaches `ps` or the shell history. For scripted use:

```bash
printf '%s' "$PASSWORD" | koji set-host-password builder1.example.com --password-stdin
```

An empty password is rejected (`Session.setPassword`,
`kojihub/auth.py:651`). Note the column is `VARCHAR(255)`
(`schemas/schema.sql:37`) — anything longer is not something you want to be
discovering on the builder.

If a user was auto-created as `usertype = NORMAL`, `add-host` needs `--force`
to convert it to `HOST`.

`add-host-to-channel` is **not optional**. A host that is registered and
enabled but in no channel receives no tasks, for the same silent-idle reason.

Passwords are stored in plaintext and compared with plain SQL equality
(`kojihub/auth.py:316-318`); there is no hashing anywhere in the path. Two
practical consequences:

- `chmod 0600 /etc/kojid/kojid.conf`, owned by root. The shipped sample is mode
  0644 and kojid does not tighten it.
- Do **not** pass `--password` on the command line. It is visible to every user
  on the box through `ps`. The config file is the lesser evil.

The credential is sent to the hub unencrypted over whatever transport `server`
specifies. On an untrusted network, terminate TLS in front of the hub — which
also unlocks the client-certificate method below.

### SSL client certificate

```ini
cert     = /etc/kojid/kojid.pem
serverca = /etc/kojid/koji_ca_cert.crt
```

Points where this trips people up, all verified against the current code:

- The certificate's DN username component (`DNUsernameComponent`, `CN` by
  default) becomes the login name, so it must match the registered hostname for
  exactly the same reason as above.
- **The file must exist.** The condition is
  `if options.cert and os.path.isfile(options.cert)` (`kojid:6939`). A `cert`
  pointing at a missing path falls through silently and kojid exits with the
  generic `No username/password/certificate supplied` — it never tells you the
  file is missing.
- **`cert` wins.** It is an `if`/`elif` chain, so if both `cert` and `user` are
  set, `user`/`password` are ignored entirely.
- **TLS is mandatory.** `ssl_login()` rewrites the base URL to `https://`
  regardless of how `server` is spelled (`koji/__init__.py:2738-2741`), and
  attempts an HTTPS connection. Against a plain-HTTP hub this method cannot work.
- The hub side needs an active block, which the shipped container config
  `containers/hub/koji-hub.conf` does **not** have:

  ```apache
  <Location /kojihub/ssllogin>
          SSLVerifyClient require
          SSLVerifyDepth  10
          SSLOptions +StdEnvVars
  </Location>
  ```

  Without `SSL_CLIENT_VERIFY=SUCCESS`, `sslLogin` rejects every certificate.

## Configuration

`kojid.conf` has exactly one section, `[kojid]`; any other is a fatal error
(`kojid:6774`). An **unknown key aborts startup** (`kojid:6859`), so a typo or
a removed option is a hard failure rather than a silent default.

`user` and `password` are valid keys and have been for a long time — they are
in the defaults table (`kojid:6799-6800`) and picked up by the generic branch at
`kojid:6855`.

Frequently relevant options:

| Key | Default | Notes |
|---|---|---|
| `server` | — | hub XML-RPC URL; required |
| `topurl` | — | hub file URL; required |
| `topdir` | `/mnt/koji` | shared with the hub; must **not** equal `workdir` |
| `workdir` | `/var/tmp/koji` | scratch, not shared |
| `sleeptime` | `15` | seconds between empty polls |
| `maxjobs` | `10` | concurrent task limit |
| `minspace` | `8192` | MB required per buildroot |
| `mockuser` | `kojibuilder` | unprivileged build user, created by `%post` |
| `mockdir` | `/var/lib/mock` | |
| `use_createrepo_c` | — | prefer the C implementation |
| `allowed_scms` | — | see the SCM section above |
| `scm_credentials_dir` | — | bind-mounted at `/credentials` in SRPM chroots |
| `plugin` / `pluginpath` | — | see Plugins |
| `cert` / `serverca` | — | see Authentication |

## External requirements

kojid is a Python driver; the real work is done by subprocesses:

| Program | Used for |
|---|---|
| `/usr/bin/mock` | every chroot build |
| `rpm` / `rpmbuild` | SRPM and binary builds |
| `/usr/bin/createrepo_c`, `/usr/bin/createrepo`, `/usr/bin/mergerepo_c` | repo metadata |
| `dnf` | dependency resolution in chroots |
| `/usr/bin/mvn` | Maven builds |
| `git`, `svn` | SCM checkout |
| `/usr/bin/qemu-img`, `/usr/sbin/mksquashfs`, `guestfs` | image builds |
| `/usr/bin/livecd-creator`, `/usr/bin/appliance-creator` | legacy image paths |

Python imports that are hard requirements: `librepo`, `multilib`, `Cheetah`,
`rpm`, `dnf`, `six`, `requests`.

`guestfs` is imported **before** `dnf` at `kojid:53-60`, guarded by
`try/except ImportError`. This is deliberate and load-bearing: importing
`guestfs` first forces the JSON library to load in a non-breaking order,
otherwise `ImageFactory`/oz fails later (BZ 1923971, Pagure 2964). Do not
"tidy" the import order.

Declared in `koji.spec:260-291` (`%package builder`): `mock >= 0.9.14`,
`createrepo_c >= 0.11.0`, `squashfs-tools`, `git`, `svn`, plus a `useradd` at
install time for `mockuser`.

## Building and installing

`builder/Makefile` is standalone (`make install DESTDIR=...`) and is what
`koji.spec` drives. It installs `kojid` to `$SBINDIR`, `kojid.conf` to
`/etc/kojid`, `kojid.service` to the systemd unit dir, and creates
`/etc/mock/koji`.

`mergerepos` is installed to `%{_libexecdir}/kojid` **only under
`py2_support > 1`** — the Makefile gates it on `PYVER_MAJOR < 3` and the spec's
`%files` on `%if 0%{py2_support} > 1`. On a Python 3 build the file is neither
installed nor packaged, and nothing in `kojid` calls it. The script itself is
hard-bound to Python 2 (`#!/usr/bin/python2`, `rpmUtils.miscutils`, `yum`), so
treat it as dead code kept for the legacy build.

Enabling the daemon: `kojid.service` runs `kojid --fg --force-lock --verbose`.
`--force-lock` matters — kojid takes an exclusive hub session
(`exclusiveSession`), and a session left behind by a killed container or a hard
reboot will block startup until it expires, with no self-healing.

## Install

dnf install python3-librepo