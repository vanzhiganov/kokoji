
Koji 1.36.0 Release notes
=========================

All changes can be found in `the roadmap <https://pagure.io/koji/roadmap/1.36/>`_.
Most important changes are listed here.

This is a fairly substantial release. Notable changes include:

* :ref:`rpm v6 support <add-rpmv6-support>`
* :ref:`porting the web ui to jinja2 <jinja2-port>`
* :ref:`adding web visibility for repo requests <add-requests-webui>`


Migrating from Koji 1.35.x
-------------------------------

For details on migrating see :doc:`../migrations/migrating_to_1.36`


Security Fixes
--------------

None


System Changes
--------------

.. _add-rpmv6-support:

**Support rpm v6 format**

| PR: https://pagure.io/koji/pull-request/4446

This adds initial support for v6 format rpms in Koji.
The main issue was Koji's past reliance on the sigmd5 field, which does not exist in v6.
Koji will now store and report multiple digest values from the rpm header, not just sigmd5.

In light of these changes the
:doc:`Content Generator Metadata <../content_generator_metadata>`
guidelines have been updated.

One notable omission -- the oz/imagefactory feature (i.e. createImage) is not covered here
(it will fail if an image includes v6 rpms).


**Show more info on waitrepo task failures**

| PR: https://pagure.io/koji/pull-request/4496

This causes the client and waitrepo tasks to show a little more detail when repo requests fail.


**Client specified signature keys**

| PR: https://pagure.io/koji/pull-request/4373
| PR: https://pagure.io/koji/pull-request/4428
| PR: https://pagure.io/koji/pull-request/4444
| PR: https://pagure.io/koji/pull-request/4459

More complex signature headers cannot be described by a single key. RPM now supports cases like:

* rpms signed with multiple keys
* rpms signed with newer types of keys
* rpms that include ima signing

Koji now takes the approach of treating the ``sigkey`` field as a descriptive label for the
signature that can be specified at import or changed later.
This gives us the ability to handle more complex signing without radically altering the
api or file layout.


**Policy enhancements**

| PR: https://pagure.io/koji/pull-request/3704

This extends the existing policy handling code adding support for:

* negated tests -- use ``!`` before a test to negate it
* break N action -- break out of subrules without matching
* stop action -- stop the policy check
* flag action -- set a named flag (and continue) when a rule matches
* flagged test -- test for a named flag
* multi match rules -- option for policy hooks to check for multiple results

These changes are backwards compatible; no policies should require update.
Admins may find that using these new options can help simplify complex logic
in their existing policies.

The new support for multi-match is forward looking, and is not currently utilized in current
policy checks.


**Deprecate pathinfo.tmpdir**

| PR: https://pagure.io/koji/pull-request/4382

The ``pathinfo.tmpdir`` method in the koji library has never been used by Koji and is now deprecated.



Hub Changes
-----------

**Disable url sessions by default**

| PR: https://pagure.io/koji/pull-request/4448

The ``DisableURLSessions`` setting on the hub now defaults to True.
Koji clients before 1.31 will not be able to authenticate

If an admin want to support auth for clients before 1.31, they can turn this back on.


**Allow querying headers from signed copy**

| PR: https://pagure.io/koji/pull-request/4532

This adds a sigkey option to getRPMHeaders. If given, the corresponding signed copy will be queried instead of the primary copy. This allows querying signature headers that have changed in the signed copy (i.e. the signatures)


**Adjust repo log logic**

| PR: https://pagure.io/koji/pull-request/4498

This change adjusts the repo lag logic and obsoletes the ``RepoLagWindow`` setting.

The lag window was intended to keep avoid redundant regenerations for duplicate requests within a short span of time. Unfortunately, there are still a number of cases where nearby requests fall into separate windows. Depending on settings and repo regen time, this can even result in overlapping newRepo tasks for the same tag.


**Recursive task policy data**

| PR: https://pagure.io/koji/pull-request/4514

When creating a new task, the data used for the policy tests includes values pulled from the task parameters.
This is now handled recursively. That is, the parameters of any parent task also apply.
In particular, this allows making channel policy rules for ``buildArch`` tasks based on the target value
of the parent ``build`` task.


**Capture more events in scheduler logs**

| PR: https://pagure.io/koji/pull-request/4506

The scheduler now includes more detail in the scheduler logs.
This data will appear in the output of ``koji scheduler-logs``


**Enable parent tag as name, not ID only**

| PR: https://pagure.io/koji/pull-request/4481

Previously the ``setInheritanceData`` call required specifying parent tags by id.
Now they can be specified by name as well.


**Addition data for cg volume policy**

| PR: https://pagure.io/koji/pull-request/4484

This makes it possible to consider cg and draft status in the volume policy.


**Channel defaults**

| PR: https://pagure.io/koji/pull-request/4396

This change allows policy to distinguish between a user channel override and a system provided
default that is different from ``default`` (e.g. for maven and image builds).

There is a new action for the channel policy named ``default`` which indicates that the default channel should be used,
regardless of what that default is.

Currently, this change must be enabled by setting ``DefaultChannelCompat = False``.
This default will change to True in a future release.


**Add listBuilds query params for promotion data**

| PR: https://pagure.io/koji/pull-request/4392

This allows querying builds by promoter or promotion time


**Less log noise for empty or invalid requests**

| PR: https://pagure.io/koji/pull-request/4391

Avoid noisy log output for invalid requests


**Adjust upload offset and overwrite logic**

| PR: https://pagure.io/koji/pull-request/4370

This fix addresses a corner case that could cause failed uploads.



**Accept both comma-separated and space-separated arches for external repos**

| PR: https://pagure.io/koji/pull-request/4354
| PR: https://pagure.io/koji/pull-request/4385

This makes calls like ``addExternalRepoToTag`` and ``editTagExternalRepo`` a bit friendlier.


**Match longest extension first for archivetype**

| PR: https://pagure.io/koji/pull-request/4224

This addresses a longstanding bug in get_archive_type. In cases of layered extensions, the code would match a shorter extension before a longer one. E.g. ".gz" would match before ".tar.gz". We have avoided such overlapping archivetypes for this reason, however we can't control what instances do.


**Report tag_external_repos.arches in query_history**

| PR: https://pagure.io/koji/pull-request/4145

This fixes an oversight in query_history. The arches field of this table was omitted.


**Allow setting ttl in protonmsg plugin**

| PR: https://pagure.io/koji/pull-request/4259

A new configuration option for the protonmsg plugin


**Partial draft support for cg_import**

| PR: https://pagure.io/koji/pull-request/4125
| PR: https://pagure.io/koji/pull-request/4472

The removes *some* obstacles for importing draft builds via the CG interface.

Generators can now set ``draft: true`` in the metadata to import draft builds, but this is
currently only allowed for rpm builds.
Admins can control such imports in the ``cg_import`` policy by using the ``is_draft`` test in a
match rule.

Additionally, the new ``AllowDraftComponents`` hub option allows content generator imports to
reference draft builds as components (e.g. a buildroot or image component for an imported build).
We recommend that admins keep this option off (the default) unless they are sure that they need it.



Client Changes
--------------

**Enable anonymous retries by default**

| PR: https://pagure.io/koji/pull-request/4517

The default value for the ``anon_retry`` setting is now True.
This will cause the client to retry hub calls even when not authenticated.



**Add override option to assign-task**

| PR: https://pagure.io/koji/pull-request/4486

This adds an ``--override`` option to the ``assign-task`` command.
This option prevents the scheduler from reassigning the task.


**Print build in import-cg**

| PR: https://pagure.io/koji/pull-request/4369

Print basic build info after import


**Clean up cli for comps management**

| PR: https://pagure.io/koji/pull-request/4397

Adds missing commands for comps management and some new documentation for using these commands.

See also:
:doc:`Managing Comps Data <../managing_comps_data>`


**Enable specific number of builds for dist-repo tasks**

| PR: https://pagure.io/koji/pull-request/4304


The ``dist-repo`` command now accepts a ``--latest-n N`` argument to use the N latest builds per
package instead of just the latest.


**Support --wait-repo/--wait-build in wrapper-rpm command**

| PR: https://pagure.io/koji/pull-request/4411

Added ``--wait-repo/--wait-build`` options similar to those for the ``build`` command.


**Download fallback to unsigned**

| PR: https://pagure.io/koji/pull-request/4342

Previously, if you passed ``--key`` to download-build and signed packages weren't available,
Koji would either skip the unsigned package or error out.
This adds a modified behavior controlled by the new ``--fallback-unsigned arg``.
If this is passed with ``--key``, unsigned copies will be downloaded for packages for which no
signed copy can be found.



Web Changes
-----------

.. _jinja2-port:

**Port kojiweb to jinja2**

| PR: https://pagure.io/koji/pull-request/4346
| PR: https://pagure.io/koji/pull-request/4418

The Koji web interface now uses Jinja2 templates instead of Cheetah templates.

Compatibility was a major focus in this port.
The web output remains predominantly the same, and url compatibility is maintained.

Note: Cheetah3 is still required on builders for wrapper rpm templates


.. _add-requests-webui:

**Add repo requests web ui**

| PR: https://pagure.io/koji/pull-request/4387

This makes repo requests more visible in the web interface.

* new page for listing repo requests
* new page for request details
* new details on the repoinfo page
* link from taginfo page to related requests
* link from taskinfo page if it is for a request


**Add weblink to NVR build for draft builds**

| PR: https://pagure.io/koji/pull-request/4480

This change provides a convenient link from the draft build page when it has
been superceded by another build.


**Add cg and draft filters for builds page**

| PR: https://pagure.io/koji/pull-request/4475

This change adds more filter options to the builds page in the web ui.


**Show source files on srpm info page**

| PR: https://pagure.io/koji/pull-request/4473

When viewing a source rpm in the web ui, the source files are now listed.




Builder Changes
---------------

**Ensure macros and env values passed to mock are strings**

| PR: https://pagure.io/koji/pull-request/4268

If an admin sets a macro value to a non-string value (which is easy to do by accident
if the value is a number), the builder will now convert the value to a string rather.


**Improve reliability of kojid service start**

| PR: https://pagure.io/koji/pull-request/4442

If chrony is enabled, wait for it to start before starting kojid.


**Return BuildError when kickstart file does not exist**

| PR: https://pagure.io/koji/pull-request/4322

Clarify an error condition


**Handle new mock option - bootstrap_image_ready**

| PR: https://pagure.io/koji/pull-request/4287

Admins can set ``mock.bootstrap_image_ready`` for a tag and this option will be added to the mock config.

See also: https://rpm-software-management.github.io/mock/Feature-container-for-bootstrap



Devel and testing
-----------------

**New dev tool: fakepolicy**

| PR: https://pagure.io/koji/pull-request/4483

This adds a new script under devtools that facilitates testing policy code against a remote
instance. The script runs some heavily mocked hub code that calls out to a remote instance
for actual data access.

The reason for this tool's existence is that policy code is very hard to test without actual data,
which is usually locked up inside a Koji instance.
This script allows you to see what a given policy would do, without actually deploying it.


**Add kojid --single mode**

| PR: https://pagure.io/koji/pull-request/4348

This is an option for debugging kojid.
Using this option makes it feasible to use the python debugger on a task handler.


**Unit test fixes**

| PR: https://pagure.io/koji/pull-request/4457
| PR: https://pagure.io/koji/pull-request/4456
| PR: https://pagure.io/koji/pull-request/4432
| PR: https://pagure.io/koji/pull-request/4433

This release includes numerous fixes that could cause unit tests to fail in
certain environments.



Bug fixes
---------

**Work around nfs glitch in ensuredir**

| PR: https://pagure.io/koji/pull-request/4427

In a multi-hub + nfs scenario, we've seen race situations where mkdir fails with EEXIST, but an
immediate lstat does not find the directory.
This change works around the unexpected kernel behavior.


**Fixes for get_next_build**

| PR: https://pagure.io/koji/pull-request/4413
| PR: https://pagure.io/koji/pull-request/4494

These fixes address cases where the automatic release incrementing mechanisms for image builds could fail.


**Handle disabled hosts in scheduler**

| PR: https://pagure.io/koji/pull-request/4505

This fixes an issue with the how the scheduler handles tasks assigned to disabled builders.


**Catch nvra duplicates when promoting**

| PR: https://pagure.io/koji/pull-request/4534

When promoting a build, we check for existing NVR conflicts and give a nice error.
However, we did not do the same for the included NVRAs, which are also required to be unique.
There are corner cases where a draft can have nvra overlap without nvr overlap.
This is still an error case, but the error is now more informative.


**Always prefer task arch in find_arch()**

| PR: https://pagure.io/koji/pull-request/4519

This addresses an issue where arch-independent tasks like rebuildSRPM and buildSRPMFromSCM
could choose the wrong buildroot architecture.


**Fix callnum lookup on hub**

| PR: https://pagure.io/koji/pull-request/4150

Since 1.31, Koji clients have used http headers to pass their session info.
However, the hub has been misreading the callnum since that time.


**Fix draft symlink handling**

| PR: https://pagure.io/koji/pull-request/4383
| PR: https://pagure.io/koji/pull-request/4452

When a draft build is promoted, Koji maintains a symlink at the original location.
These fixes address cases where the hub did not create that link.


**Fix listUsers type check**

| PR: https://pagure.io/koji/pull-request/4355

Support passing a list for ``userType``


**Ensure repos dir**

| PR: https://pagure.io/koji/pull-request/4316

Create the repos dir if it does not exist.


**Write-signed-rpm: fix nvr fallback**

| PR: https://pagure.io/koji/pull-request/4470

This fixes a bug in the ``write-signed-rpm`` command where it would fail on valid NVR values.


**Use label for waitrepo subtasks**

| PR: https://pagure.io/koji/pull-request/4467

This change prevents restarted tasks from spawning a redundant ``waitrepo`` subtask


**Prefer getBuildLogs for downloading logs**

| PR: https://pagure.io/koji/pull-request/4123

Fixes a common failure case for log downloads


**Windows build fixes**

| PR: https://pagure.io/koji/pull-request/4311
| PR: https://pagure.io/koji/pull-request/4380
| PR: https://pagure.io/koji/pull-request/4388
| PR: https://pagure.io/koji/pull-request/4389

Various small fixes to the windows build daemon.


**Handle x86_64_v2 arch for dist-repos**

| PR: https://pagure.io/koji/pull-request/4416

This fixes a KeyError when trying to make a distrepo for the arch "x86_64_v2".



Other changes
-------------

**Update Cheetah3 to CT3 PyPI repository**

| PR: https://pagure.io/koji/pull-request/4375

Note: While Koji now uses Jinja2 in the web ui, Cheetah3 is still required for wrapper rpm templates.

This simply updates our requirements to point to the new upstream.


**koji-gc: Add ccache to koji-gc options**

| PR: https://pagure.io/koji/pull-request/4171

Allows specifying a Kerberos credential cache for koji-gc, similar to kojira and kojid.


**Indexes for standard_buildroot**

| PR: https://pagure.io/koji/pull-request/4134

Adds database indexes for query performance


**Schemas: wsl file suffix**

| PR: https://pagure.io/koji/pull-request/4403

The "new" WSL images need a WSL suffix. Currently this is managed on a
per-instance basis but it's a bit of work to sync across them.


**Add archive types for erofs and squashfs**

| PR: https://pagure.io/koji/pull-request/4219

Add archive types produced by Kiwi


**Drop custom threadlocal implementation**

| PR: https://pagure.io/koji/pull-request/4330

Koji previously used its own ``ThreadLocal`` class.
Now it just uses ``threading.local``.


**Raise weight cap**

| PR: https://pagure.io/koji/pull-request/4349

This adjusts the cap on how much kojid can adjust the weight of a ``buildArch`` task.


**Documentation updates**

| PR: https://pagure.io/koji/pull-request/4409
| PR: https://pagure.io/koji/pull-request/4437
| PR: https://pagure.io/koji/pull-request/4436
| PR: https://pagure.io/koji/pull-request/4423

Various documentation changes

..
    the end
