
Koji 1.36.1 Release notes
=========================

All changes can be found in `the roadmap <https://forge.fedoraproject.org/koji/koji/milestone/1114>`_.
Most important changes are listed here.

This is a fairly small bugfix release to address some pain points in 1.36.



Migrating from Koji 1.36.0
-------------------------------

No special actions are needed.



Bug fixes
---------

**Better handling of volume topdir problems**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4558
| PR: https://forge.fedoraproject.org/koji/koji/pulls/4557

Fixes issues related to handling the volume toplink that Koji started
requiring in 1.36.

See also: :doc:`../migrations/migrating_to_1.36`


**Reset callnum when a session is renewed**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4588

This fixes issues with session renewal in 1.36.


**Make templates compatible for jinja 2.10**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4563

This addresses issues with running kojiweb on rhel8 (jinja 2.10).


**Avoid error in daemon.py if "single" option is unset**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4583

This fixes a startup error in kojivmd


**Fix flag data leaks**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4553

Fixes a potential logic issue with the ``flag`` action that was added for policies in 1.36.


**Fix kojihash calculation in rpmdiff**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4546
| PR: https://forge.fedoraproject.org/koji/koji/pulls/4542

Fixes for multiple issues in the kojihash calculation that resulted
in unnecessary duplicate runs of rpmdiff.


**Fix string escapes in archivetype queries**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4573

Fix string escapes in archivetype queries for older postgres


System Changes
--------------

**Better scm path normalization**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4585

This does a better job of normalizing the scm path


**Add by_tag_subtask policy test**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4578

This hub policy test is true if a tag operation is triggered by a tagBuild subtask.

When this is true, it means the tag operation is part of a builder workflow. E.g. tagging at the end of a build task
This can be used to avoid breaking build target workflows when crafting strict tag policies.

See also: :doc:`../defining_hub_policies`



Client Changes
--------------

**Option for download-build to not fail on missing arch**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4575

This arg makes ``koji download-build`` warn, but exit 0, if the
specified build has no packages for any of the specified arches.



Devel and testing
-----------------

**Enhancements to fakepolicy tool**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4599
| PR: https://forge.fedoraproject.org/koji/koji/pulls/4586
| PR: https://forge.fedoraproject.org/koji/koji/pulls/4538

- handle BuildRoot.getList in fakepolicy
- support testing scm-policy
- support testing cg policy


**Unit test fixes and additions**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4592
| PR: https://forge.fedoraproject.org/koji/koji/pulls/4564
| PR: https://forge.fedoraproject.org/koji/koji/pulls/4577

- fixes for parallel tests
- fixes for rhel8
- additional tests



Other changes
-------------

**Unify format of CLI help messages**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4594

Minor cleanup for help text in the cli


**Minor multicall fix**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4610

Minor fix for a potentially confusing error case, plus some docstring updates
to discourage use of old multiCall method.


**Extend sidetag documentation**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4280


**Additional docs for policy tests**

| PR: https://forge.fedoraproject.org/koji/koji/pulls/4294



..
    the end
