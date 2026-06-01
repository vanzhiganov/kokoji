Migrating to Koji 1.36
======================

You should consider the following changes when migrating to 1.36:

DB Updates
----------

The changes to support rpm v6 include new fields in the ``rpminfo`` table.
Additionally, we have added new archive types and new indexes.

As in previous releases, we provide a migration script that updates the database.

::

    # psql koji koji < /usr/share/koji/schema-upgrade-1.35-1.36.sql


Volume toplinks
---------------

.. warning:: Action required for non-default volumes

In order to address a previous issue with promoting builds, the system now
requires that each volume directory contain a ``toplink`` symlink that points
to the main volume.
This is simply a symlink that points to the main volume. E.g.

::

     $ file /mnt/koji/vol/vol3/toplink
     /mnt/koji/vol/vol3/toplink: symbolic link to /mnt/koji

You **must** create this symlink for any existing volumes used in your system.
Failure to do so can result in build promotion failures.

We recommend using an absolute symlink, as in the example above.

When adding a new volume, admins should create this symlink when they create
the volume directory. If not, the hub will automatically create it using the
configured topdir path and log a warning.

For more information, see

* :ref:`Fix draft symlink handling <draft-symlink-fix-1-36>`
* :ref:`adding-new-volume`


Notable configuration changes
-----------------------------

The ``RepoLagWindow`` hub option is no longer used.
For details see https://pagure.io/koji/issue/4499

The ``DisableURLSessions`` hub option now defaults to True.
This will prevent clients older than Koji 1.31 from authenticating.
For details see https://pagure.io/koji/issue/4420



Other changes
-------------

There are numerous other changes in 1.36 that should not have a direct impact
on migration. For details see: :doc:`../release_notes/release_notes_1.36`
