Migrating to Koji 1.36
======================

You should consider the following changes when migrating to 1.36:

DB Updates
----------

Kerberos principals are no longer tracked, so the ``user_krb_principals``
table is dropped. As in previous releases, we provide a migration script that
updates the database.

::

    # psql koji koji < /usr/share/koji/schema-upgrade-1.35-1.36.sql

The script also cleans up ``sessions.authtype``. The enum lost its
``KERBEROS`` (1) and ``GSSAPI`` (3) members, which renumbers ``SSL`` from 2
to 1. Sessions carrying a removed authtype are closed out; the rest have
their old ``SSL`` value remapped.

Removed Kerberos/GSSAPI authentication
--------------------------------------

Kerberos/GSSAPI authentication has been removed. SSL client certificate and
username/password authentication are unaffected. This is a breaking change for
clients and deployments that relied on it.

The following Python dependencies and RPM requirements were dropped:

* ``requests-gssapi`` (and the older ``requests-kerberos``)
* ``mod_auth_gssapi``

Because ``gssapi`` has no Linux wheels on PyPI, dropping it also removes the
``krb5-devel`` build requirement from the container images and from the
documented build dependencies.

Removed hub configuration options
---------------------------------

These ``hub.conf`` options are no longer recognized:

* ``ProxyPrincipals``
* ``HostPrincipalFormat``
* ``AllowedKrbRealms``

These ``kojiweb`` (``web.conf``) options are no longer recognized:

* ``WebPrincipal``
* ``WebKeytab``
* ``WebCCache``
* ``KrbService``
* ``KrbRDNS``
* ``KrbCanonHost``
* ``KrbServerRealm``

``WebAuthType`` now accepts only ``password`` and ``ssl``. Configuring kojiweb
with ``mod_auth_gssapi`` in the httpd config no longer has any effect.

Removed CLI options and commands
--------------------------------

* ``koji --authtype kerberos`` now errors out. Use ``--authtype ssl`` or
  ``--authtype password``.
* ``koji --keytab`` and ``koji --principal`` were removed.
* ``koji add-host --krb-principal`` was removed.
* ``koji add-user --principal`` was removed.
* ``koji edit-user --edit-krb``, ``--add-krb``, and ``--remove-krb`` were
  removed. ``--rename`` still works.

Removed XMLRPC calls and arguments
-----------------------------------

The following hub calls were removed. Calling them raises an XMLRPC fault:

* ``addUserKrbPrincipal``
* ``removeUserKrbPrincipal``
* ``getUserByKrbPrincipal``
* ``listUserKrbPrincipals``

These calls no longer accept or return Kerberos arguments:

* ``getUser`` dropped ``krb_princs`` and no longer returns ``krb_principals``
  in its result.
* ``editUser`` dropped ``krb_principal_mappings``.
* ``createUser`` dropped ``krb_principal``.
* ``addHost`` dropped ``krb_principal``.

Removed Python API
------------------

* ``koji.ClientSession.gssapi_login()`` was removed.
* ``koji.GSSAPIAuthError`` was removed. Fault code 1023 is no longer used.
* ``koji.reqgssapi`` was removed.
* ``koji.AUTHTYPES['KERBEROS']`` and ``koji.AUTHTYPES['GSSAPI']`` were removed,
  and ``koji.AUTHTYPES['SSL']`` changed from 2 to 1.

Callers should catch ``koji.AuthError`` instead of ``koji.GSSAPIAuthError``.
