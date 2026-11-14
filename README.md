koji - RPM building and tracking system
=======================================

Koji is an RPM-based build system. The Fedora Project uses Koji for [their build system](https://koji.fedoraproject.org/koji/), as do [several other projects](https://fedoraproject.org/wiki/Koji/RunsHere).

Koji's goal is to provide a flexible, secure, and reproducible way to build software.

Key features:

* New buildroot for each build
* Robust XML-RPC APIs for easy integration with other tools
* Web interface with SSL and Kerberos authentication
* Thin, portable command line client
* Users can create local buildroots
* Buildroot contents are tracked in the database
* Versioned data

Communicate
-----------

* Comments, questions, bugs, feedback, ideas, help requests? We'd love to hear from you.
* Mailing lists:
    * Development: [koji-devel AT lists.fedorahosted.org](https://lists.fedorahosted.org/archives/list/koji-devel@lists.fedorahosted.org/)
    * User discussion and Fedora-specific topics: [buildsys AT lists.fedoraproject.org](https://lists.fedoraproject.org/archives/list/buildsys@lists.fedoraproject.org/)
* IRC chat: #koji on [libera.chat](https://libera.chat/)

Bugs/RFEs
---------

If you have found a bug or would like to request a new feature, please [report an issue in Pagure](https://pagure.io/koji/issues).

Download
--------

The koji source code can be downloaded with git via:

    git clone https://pagure.io/koji.git

You may browse code at https://pagure.io/koji

Archived releases can be found at https://pagure.io/koji/releases

Building from source
--------------------

Building the RPM packages from this checkout requires ``rpm-build``. Install
it with dnf:

    dnf install rpm-build

Then run ``make srpm`` or ``make rpm`` from the repository root. The Makefile
also uses ``rpm``/``rpmspec`` to read the version from the spec file, so this
dependency is needed even for other make targets.

This fork: container stack and web interface
--------------------------------------------

This checkout adds a Docker Compose stack (PostgreSQL, hub, web) and a reworked
web interface. Upstream documentation above still applies to the hub, CLI and
builder.

### Running the stack

Requirements: Docker with the Compose plugin (the stack was verified with Docker 29).

    make containers        # build base, CLI and service images
    make containers-up     # start db, hub, web and kojira in the background
    make containers-down   # stop and remove the stack

`make containers-base` must run before the other images; the Makefile tags the
result as the base image the service Dockerfiles expect.

Endpoints on the host:

| URL                             | What                                   |
|---------------------------------|----------------------------------------|
| `http://localhost:8080/koji/`   | Web interface                          |
| `http://localhost/kojihub`      | Hub XML-RPC API                        |
| `http://localhost/kojifiles`    | Files (build outputs)                  |

The database is seeded with an `admin` user (password `admin`, `admin`
permission). **Change this password before using the stack anywhere else.**

Configuration is read from environment variables (see `containers/compose.yml`):

| Variable              | Default                  | Purpose                                      |
|-----------------------|--------------------------|----------------------------------------------|
| `HUB_URL`             | `http://hub/kojihub`     | Hub URL used by the web interface            |
| `FILES_URL`           | `http://hub/kojifiles`   | Files URL used by the web interface          |
| `WEB_SECRET`          | `change-me-secret`       | Secret that signs login cookies. **Change it.** |
| `ALLOW_REGISTRATION`  | `On`                     | Let new users register from the login page   |
| `LOG_LEVEL`           | `INFO`                   | Web log level (e.g. `WARNING koji.auth:INFO`) |
| `POSTGRES_*`          | `koji`                   | Database name, user and password             |

### Web interface

* Pages are Jinja2 templates in `www/lib/kojiweb/templates/` (`.html`). The
  Cheetah `.chtml` templates in `www/kojiweb/` are no longer used by the Flask
  application.
* The layout follows the [Carbon Design System](https://carbondesignsystem.com/):
  the UI shell header, data tables, structured lists, pagination and form
  controls use `cds--` classes from `www/static/carbon/carbon.min.css`.
  `www/static/koji.css` holds the Koji-specific overrides.
* Password login is enabled in the container (`WebAuthType = password` in
  `containers/web/web.conf`). After a successful login the hub session is kept
  in a signed `hubsession` cookie, so later requests can call the hub as that
  user. The cookie is `HttpOnly` and `SameSite=Strict`; it is `Secure` when
  `ForceSSL` is on.
* Relevant options in `web.conf`: `WebAuthType` (`password` or `ssl`),
  `ForceSSL`, `Secret`, `LoginTimeout` (hours), `AllowRegistration`.

### Permissions

* Managing tags (create, edit, parents, external repositories) requires the
  hub `tag` permission. The web interface shows these links to users with
  `tag`.
* Managing other users' permissions requires `admin`. Users with `admin` see a
  **Permissions** table on the user page with Grant and Revoke buttons. An
  admin cannot revoke their own `admin` permission from the web interface.
* A request the user is not allowed to make returns HTTP 403; other errors
  return 500.

### Tests

Web interface tests live in `tests/test_www/`:

    python3 -m pytest tests/test_www

The full suite is run with `make test` (tox, `py3` environment).

Last verified: 2026-11-14.

Documentation
-------------

See: https://docs.pagure.org/koji/


Related Software
----------------

* [Mock](https://fedoraproject.org/wiki/Projects/Mock): The tool Koji uses to generate buildroots
* [Yum](http://yum.baseurl.org/)
* [Pungi](https://pagure.io/pungi): Use Pungi to "compose" Koji builds into highly customizable Yum repositories.
* [Koji Tools](https://pagure.io/koji-tools): Various utilities for Koji
* [Kojiji](https://github.com/release-engineering/kojiji): Koji Java Interface
* [txkoji](https://github.com/ktdreyer/txkoji): Async interface to Koji, using Twisted
* [koji-hs](https://hackage.haskell.org/package/koji): Koji Haskell Interface
