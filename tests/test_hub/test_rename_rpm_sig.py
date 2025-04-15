import os
import tempfile
import shutil
import unittest

from unittest import mock

import koji
import kojihub
from koji.util import joinpath

UP = kojihub.UpdateProcessor


class TestRenameRPMSig(unittest.TestCase):

    def getUpdate(self, *args, **kwargs):
        update = UP(*args, **kwargs)
        update.execute = mock.MagicMock()
        self.updates.append(update)
        return update

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.pathinfo = koji.PathInfo(self.tempdir)
        mock.patch('koji.pathinfo', new=self.pathinfo).start()
        self.updates = []
        self.UpdateProcessor = mock.patch('kojihub.kojihub.UpdateProcessor',
                                          side_effect=self.getUpdate).start()
        self.get_rpm = mock.patch('kojihub.kojihub.get_rpm').start()
        self.query_rpm_sigs = mock.patch('kojihub.kojihub.query_rpm_sigs').start()
        self.get_build = mock.patch('kojihub.kojihub.get_build').start()
        self.get_user = mock.patch('kojihub.kojihub.get_user').start()
        self.verify_name_internal = mock.patch('kojihub.kojihub.verify_name_internal').start()
        self.buildinfo = {'build_id': 1,
                          'epoch': None,
                          'extra': None,
                          'id': 1,
                          'name': 'fs_mark',
                          'nvr': 'fs_mark-3.3-20.el8',
                          'owner_id': 1,
                          'owner_name': 'kojiadmin',
                          'package_id': 1,
                          'package_name': 'fs_mark',
                          'release': '20.el8',
                          'state': 1,
                          'task_id': None,
                          'version': '3.3'}
        self.rinfo = {'arch': 'x86_64',
                      'build_id': 1,
                      'buildroot_id': None,
                      'buildtime': 1564782768,
                      'epoch': None,
                      'external_repo_id': None,
                      'extra': None,
                      'id': 2,
                      'metadata_only': False,
                      'name': 'fs_mark',
                      'payloadhash': 'ed0690ab4b0508f2448d99a08e0a004a',
                      'release': '20.el8',
                      'size': 25644,
                      'version': '3.3'}
        self.rpmsigs = {
            '': {'rpm_id': 2, 'sighash': 'cb4d01bd3671b41ef51abc9be851e614', 'sigkey': ''},
            '2f86d6a1': {'rpm_id': 2, 'sighash': '78c245caa6deb70f0abc8b844c642cd6',
                         'sigkey': '2f86d6a1'}
        }
        self.queryrpmsigs = [self.rpmsigs[k] for k in sorted(self.rpmsigs)]
        self.userinfo = {'authtype': 2, 'id': 1, 'krb_principal': None, 'krb_principals': [],
                         'name': 'testuser', 'status': 0, 'usertype': 0}
        self.set_up_files()

    def set_up_files(self):
        builddir = self.pathinfo.build(self.buildinfo)
        os.makedirs(builddir)
        self.builddir = builddir
        self.signed = {}
        self.sighdr = {}
        for sig in self.queryrpmsigs:
            key = sig['sigkey']
            signed = joinpath(builddir, self.pathinfo.signed(self.rinfo, key))
            self.signed[key] = signed
            koji.ensuredir(os.path.dirname(signed))
            with open(signed, 'wt') as fo:
                fo.write('SIGNED COPY\n')

            sighdr = joinpath(builddir, self.pathinfo.sighdr(self.rinfo, key))
            self.sighdr[key] = sighdr
            koji.ensuredir(os.path.dirname(sighdr))
            with open(sighdr, 'wt') as fo:
                fo.write('DETACHED SIGHDR\n')

    def get_files(self, with_dirs=True):
        data = []
        for root, dirs, files in os.walk(self.builddir):
            for name in files:
                fn = os.path.join(root, name)
                with open(fn, 'rt') as fp:
                    contents = fp.read()
                # tuple because we will sort later
                data.append((fn, contents))
            if with_dirs:
                for name in dirs:
                    fn = os.path.join(root, name)
                    data.append((fn,))
        data.sort()
        return data

    def tearDown(self):
        mock.patch.stopall()
        shutil.rmtree(self.tempdir)

    def test_rpm_missing(self):
        rpm_id = 1234
        expected_msg = 'No such rpm: %s' % rpm_id
        self.get_rpm.side_effect = koji.GenericError("No such rpm: %s" % rpm_id)

        before = self.get_files()
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpm_id, 'foo', 'bar')

        self.assertEqual(len(self.updates), 0)
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpm_id, strict=True)
        self.query_rpm_sigs.assert_not_called()
        self.assertEqual(before, self.get_files())

    def test_external_repo(self):
        rpminfo = 1234
        rinfo = self.rinfo.copy()
        rinfo.update({'external_repo_id': 1, 'external_repo_name': 'INTERNAL'})
        self.get_rpm.return_value = rinfo

        before = self.get_files()
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, 'foo', 'bar')

        self.assertEqual(len(self.updates), 0)
        expected_msg = "Not an internal rpm: %s (from %s)" % (rpminfo, rinfo['external_repo_name'])
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpminfo, strict=True)
        self.query_rpm_sigs.assert_not_called()
        self.assertEqual(before, self.get_files())

    def test_no_oldsig(self):
        rpminfo = 1234
        nvra = "%s-%s-%s.%s" % (self.rinfo['name'], self.rinfo['version'], self.rinfo['release'],
                                self.rinfo['arch'])
        expected_msg = "No foo signature for rpm %s" % nvra
        self.get_rpm.return_value = self.rinfo
        self.query_rpm_sigs.return_value = []

        before = self.get_files()
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, 'foo', 'bar')

        self.assertEqual(len(self.updates), 0)
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpminfo, strict=True)
        self.query_rpm_sigs.assert_called_once_with(rpm_id=self.rinfo['id'], sigkey='foo')
        self.assertEqual(before, self.get_files())

    def test_already_got_one(self):
        rpminfo = 1234
        nvra = "%s-%s-%s.%s" % (self.rinfo['name'], self.rinfo['version'], self.rinfo['release'],
                                self.rinfo['arch'])
        expected_msg = "A bar signature already exists for rpm %s" % nvra
        self.get_rpm.return_value = self.rinfo
        self.query_rpm_sigs.side_effect = [self.query_rpm_sigs, [{'foo':1}]]

        before = self.get_files()
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, 'foo', 'bar')

        self.assertEqual(len(self.updates), 0)
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpminfo, strict=True)
        self.assertEqual(before, self.get_files())

    def test_header_missing(self):
        rpminfo = self.rinfo['id']
        self.get_rpm.return_value = self.rinfo
        self.get_build.return_value = self.buildinfo
        self.get_user.return_value = self.userinfo
        self.query_rpm_sigs.side_effect = [self.query_rpm_sigs, []]

        # a missing header should error
        builddir = self.pathinfo.build(self.buildinfo)
        sigkey = '2f86d6a1'
        os.remove(self.sighdr[sigkey])

        before = self.get_files()
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, sigkey, 'foobar')

        expected_msg = "Missing signature header file: %s" % self.sighdr[sigkey]
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.assertEqual(before, self.get_files())

    def test_valid(self):
        rpminfo = 2
        self.get_rpm.return_value = self.rinfo
        self.get_build.return_value = self.buildinfo
        self.get_user.return_value = self.userinfo
        self.query_rpm_sigs.side_effect = [self.query_rpm_sigs, []]
        oldkey = '2f86d6a1'
        kojihub.rename_rpm_sig(rpminfo, oldkey, 'foobar')

        # the old files should be gone
        if os.path.exists(self.signed[oldkey]):
            raise Exception('signed copy not deleted')
        if os.path.exists(self.sighdr[oldkey]):
            raise Exception('header still in place')

        # the new file should be there
        sighdr = joinpath(self.builddir, self.pathinfo.sighdr(self.rinfo, 'foobar'))
        signed = joinpath(self.builddir, self.pathinfo.signed(self.rinfo, 'foobar'))
        with open(sighdr, 'rt') as fp:
            self.assertEqual(fp.read(), 'DETACHED SIGHDR\n')
        with open(signed, 'rt') as fp:
            self.assertEqual(fp.read(), 'SIGNED COPY\n')

        self.assertEqual(len(self.updates), 1)
        update = self.updates[0]
        self.assertEqual(update.table, 'rpmsigs')
        self.assertEqual(update.clauses, ["rpm_id=%(rpm_id)s", "sigkey=%(oldkey)s"])

        self.get_build.assert_called_once_with(self.rinfo['build_id'], strict=True)

    def test_already_got_signed_copy(self):
        rpminfo = 2
        self.get_rpm.return_value = self.rinfo
        self.get_build.return_value = self.buildinfo
        self.get_user.return_value = self.userinfo
        self.query_rpm_sigs.side_effect = [self.query_rpm_sigs, []]
        oldkey = '2f86d6a1'
        signed = joinpath(self.builddir, self.pathinfo.signed(self.rinfo, 'foobar'))
        koji.ensuredir(os.path.dirname(signed))
        with open(signed, 'wt') as fp:
            fp.write('STRAY SIGNED COPY\n')

        before = self.get_files()
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, oldkey, 'foobar')

        expected_msg = f'Signed copy already exists: {signed}'
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpminfo, strict=True)
        self.assertEqual(before, self.get_files())

    def test_already_got_sighdr(self):
        rpminfo = 2
        self.get_rpm.return_value = self.rinfo
        self.get_build.return_value = self.buildinfo
        self.get_user.return_value = self.userinfo
        self.query_rpm_sigs.side_effect = [self.query_rpm_sigs, []]
        oldkey = '2f86d6a1'
        sighdr = joinpath(self.builddir, self.pathinfo.sighdr(self.rinfo, 'foobar'))
        koji.ensuredir(os.path.dirname(sighdr))
        with open(sighdr, 'wt') as fp:
            fp.write('STRAY HEADER\n')

        before = self.get_files()
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, oldkey, 'foobar')

        expected_msg = f'Signature header file already exists: {sighdr}'
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpminfo, strict=True)
        self.assertEqual(before, self.get_files())

    @mock.patch('os.rename')
    def test_first_rename_fails(self, rename):
        rpminfo = 2
        self.get_rpm.return_value = self.rinfo
        self.get_build.return_value = self.buildinfo
        self.get_user.return_value = self.userinfo
        self.query_rpm_sigs.side_effect = [self.query_rpm_sigs, []]
        oldkey = '2f86d6a1'
        rename.side_effect = FileNotFoundError('...')

        before = self.get_files(with_dirs=False)
        # this error case will leave a stray dir
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, oldkey, 'foobar')

        oldpath = joinpath(self.builddir, self.pathinfo.signed(self.rinfo, oldkey))
        expected_msg = f'Failed to rename {oldpath}'
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpminfo, strict=True)
        self.assertEqual(before, self.get_files(with_dirs=False))

    @mock.patch('os.rename')
    def test_second_rename_fails(self, rename):
        rpminfo = 2
        self.get_rpm.return_value = self.rinfo
        self.get_build.return_value = self.buildinfo
        self.get_user.return_value = self.userinfo
        self.query_rpm_sigs.side_effect = [self.query_rpm_sigs, []]
        oldkey = '2f86d6a1'
        rename.side_effect = [None, FileNotFoundError('...')]

        with self.assertRaises(koji.GenericError) as ex:
            kojihub.rename_rpm_sig(rpminfo, oldkey, 'foobar')

        oldpath = joinpath(self.builddir, self.pathinfo.sighdr(self.rinfo, oldkey))
        expected_msg = f'Failed to rename {oldpath}'
        self.assertEqual(ex.exception.args[0], expected_msg)
        self.get_rpm.assert_called_once_with(rpminfo, strict=True)


# the end
