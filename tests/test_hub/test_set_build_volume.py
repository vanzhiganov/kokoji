from unittest import mock
import os
import os.path
import shutil
import tempfile
import unittest
import koji
from kojihub import kojihub


class TestChangeBuildVolume(unittest.TestCase):

    def setUp(self):
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context.session.assertPerm = mock.MagicMock()
        mock.patch('kojihub.kojihub.lookup_name').start()
        mock.patch('kojihub.kojihub.get_build').start()
        self.set_build_volume = mock.patch('kojihub.kojihub._set_build_volume').start()
        mock.patch('kojihub.db._dml').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_change_volume(self):
        kojihub.change_build_volume('build', 'volume')
        self.set_build_volume.assert_called_once()
        self.context.session.assertPerm.assert_called_once_with('admin')


class TestSetBuildVolume(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.topdir = self.tempdir + '/koji'
        self.pathinfo = koji.PathInfo(self.topdir)
        self.volumes = {
            'DEFAULT': {'id': 0, 'name': 'DEFAULT'}
        }
        mock.patch('koji.pathinfo', new=self.pathinfo).start()
        self.list_volumes = mock.patch('kojihub.kojihub.list_volumes').start()
        self.list_volumes.side_effect = self.my_list_volumes
        self.list_tags = mock.patch('kojihub.kojihub.list_tags').start()
        self.set_tag_update = mock.patch('kojihub.kojihub.set_tag_update').start()
        mock.patch('kojihub.kojihub.lookup_name', new=self.my_lookup_name).start()
        mock.patch('kojihub.kojihub.get_build').start()
        self.UpdateProcessor = mock.patch('kojihub.kojihub.UpdateProcessor').start()
        mock.patch('kojihub.db._dml').start()

    def tearDown(self):
        mock.patch.stopall()
        shutil.rmtree(self.tempdir)

    def my_lookup_name(self, table, info, **kw):
        if table != 'volume':
            raise Exception("Cannot fake call")
        # we assume the volume name was passed
        return self.volumes[info]

    def my_list_volumes(self):
        return [self.volumes[n] for n in sorted(self.volumes)]

    def make_volume(self, name, volume_id=None):
        if name in self.volumes:
            return self.volumes[name]

        # first dir simulates the mount for the volume
        mnt = self.tempdir + '/vol_mount_' + name
        toplink = mnt + '/toplink'
        koji.ensuredir(mnt)
        os.symlink(self.topdir, toplink)

        # then we set up the symlink to the mount under /mnt/koji/vol
        voldir = self.pathinfo.volumedir(name)
        koji.ensuredir(os.path.dirname(voldir))  # koji/vol_xx
        os.symlink(mnt, voldir)

        # return volume info
        if volume_id is None:
            # just pick based on existing
            volume_id = len(os.listdir(self.topdir + '/vol')) + 1
        vinfo = {'id': volume_id, 'name': name, '_mnt': mnt}
        self.volumes[name] = vinfo
        return vinfo

    def make_build(self, volume=None, state='COMPLETE'):
        buildinfo = {
            'id': 137,
            'task_id': 'TASK_ID',
            'name': 'some-image',
            'version': '1.2.3.4',
            'release': '3',
            'nvr': 'some-image-1.2.3.4-3',
            'epoch': None,
            'source': None,
            'state': koji.BUILD_STATES[state],
            # 'volume_id': 1,
            'volume_name': volume,
        }
        if volume is None:
            buildinfo['volume_id'] = 0
            buildinfo['volume_name'] = 'DEFAULT'
        else:
            # should be vinfo
            buildinfo['volume_id'] = volume['id']
            buildinfo['volume_name'] = volume['name']
        if state == 'COMPLETE':
            # also create the build dir
            builddir = self.pathinfo.build(buildinfo)
            koji.ensuredir(builddir)
            buildinfo['_orig_dir'] = builddir
        return buildinfo

    def test_simple_move(self):
        binfo = self.make_build()  # DEFAULT volume
        vinfo = self.make_volume('other')

        kojihub._set_build_volume(binfo, vinfo)

        # expected files
        files = list(find_files(vinfo['_mnt']))
        expected = [
            'packages',
            'toplink',
            'packages/some-image',
            'packages/some-image/1.2.3.4',
            'packages/some-image/1.2.3.4/3',
        ]
        self.assertEqual(files, expected)

        # check the link
        orig = binfo['_orig_dir']
        new_binfo = binfo.copy()
        new_binfo['volume_id'] = vinfo['id']
        new_binfo['volume_name'] = vinfo['name']
        newdir = self.pathinfo.build(new_binfo)
        self.assertTrue(os.path.samefile(orig, newdir))

    def test_tag_updates(self):
        binfo = self.make_build()  # DEFAULT volume
        vinfo = self.make_volume('other')
        self.list_tags.return_value = [{'id': 23, 'name': 'TAG'}]

        kojihub._set_build_volume(binfo, vinfo)

        self.set_tag_update.assert_called_once_with(23, 'VOLUME_CHANGE')

    def test_move_loop(self):
        binfo = self.make_build()  # DEFAULT volume

        for i in range(5):
            name = 'vol_%02i' % i
            vinfo = self.make_volume(name)
            kojihub._set_build_volume(binfo, vinfo)
        # and back to default
        vinfo = {'id': 0, 'name': 'DEFAULT'}
        kojihub._set_build_volume(binfo, vinfo)

        # expected files
        files = list(find_files(self.topdir))
        expected = [
            'packages',
            'vol',
            'packages/some-image',
            'packages/some-image/1.2.3.4',
            'packages/some-image/1.2.3.4/3',
            'vol/vol_00',
            'vol/vol_01',
            'vol/vol_02',
            'vol/vol_03',
            'vol/vol_04'
        ]
        self.assertEqual(files, expected)

    def test_same_volume(self):
        vinfo = self.make_volume('other')
        binfo = self.make_build(volume=vinfo)
        orig = list(find_files(vinfo['_mnt']))

        with self.assertRaises(koji.GenericError) as ex:
            kojihub._set_build_volume(binfo, vinfo)

        self.assertIn('already on volume', str(ex.exception))

        # no error unless strict
        kojihub._set_build_volume(binfo, vinfo, strict=False)

        self.list_volumes.assert_not_called()

        # no files changes
        files = list(find_files(vinfo['_mnt']))
        self.assertEqual(files, orig)

    def test_wrong_state(self):
        vinfo = self.make_volume('other')
        binfo = self.make_build(state='BUILDING')

        with self.assertRaises(koji.GenericError) as ex:
            kojihub._set_build_volume(binfo, vinfo)

        self.assertEqual('Build some-image-1.2.3.4-3 is BUILDING', str(ex.exception))
        self.list_volumes.assert_not_called()

    def test_missing_volume(self):
        binfo = self.make_build()  # DEFAULT

        vinfo = self.make_volume('other')
        orig = list(find_files(self.topdir))
        shutil.rmtree(vinfo['_mnt'])
        with self.assertRaises(koji.GenericError) as ex:
            kojihub._set_build_volume(binfo, vinfo)

        self.assertIn('Directory entry missing for volume', str(ex.exception))
        self.list_volumes.assert_not_called()
        self.UpdateProcessor.assert_not_called()

        # no files changes
        files = list(find_files(self.topdir))
        self.assertEqual(files, orig)

    def test_destination_exists(self):
        binfo = self.make_build()  # DEFAULT
        vinfo = self.make_volume('other')
        bad_binfo = binfo.copy()
        bad_binfo['volume_id'] = vinfo['id']
        bad_binfo['volume_name'] = vinfo['name']
        dest = self.pathinfo.build(bad_binfo)
        koji.ensuredir(dest)
        with open(dest + '/stray_content', 'wt') as fp:
            fp.write('stray build content\n')

        orig = list(find_files(self.topdir))
        with self.assertRaises(koji.GenericError) as ex:
            kojihub._set_build_volume(binfo, vinfo)

        self.assertIn('Destination directory exists:', str(ex.exception))
        self.UpdateProcessor.assert_not_called()

        # no files changes
        files = list(find_files(self.topdir))
        self.assertEqual(files, orig)

    def test_stray_cross_volume(self):
        binfo = self.make_build()  # DEFAULT
        vinfo = self.make_volume('other')
        vinfo2 = self.make_volume('yet_another')
        bad_binfo = binfo.copy()
        bad_binfo['volume_id'] = vinfo2['id']
        bad_binfo['volume_name'] = vinfo2['name']
        dest = self.pathinfo.build(bad_binfo)
        koji.ensuredir(dest)
        with open(dest + '/stray_content', 'wt') as fp:
            fp.write('stray build content\n')

        orig = list(find_files(self.topdir))
        with self.assertRaises(koji.GenericError) as ex:
            kojihub._set_build_volume(binfo, vinfo)

        self.assertIn('Unexpected cross-volume content:', str(ex.exception))
        self.UpdateProcessor.assert_not_called()

        # no files changes
        files = list(find_files(self.topdir))
        self.assertEqual(files, orig)

    def test_build_dir_missing(self):
        binfo = self.make_build()  # DEFAULT
        vinfo = self.make_volume('other')
        bdir = binfo['_orig_dir']
        os.rename(bdir, bdir + '_MOVED')

        orig = list(find_files(self.topdir))
        with self.assertRaises(koji.GenericError) as ex:
            kojihub._set_build_volume(binfo, vinfo)

        self.assertIn('Build directory missing:', str(ex.exception))
        self.UpdateProcessor.assert_not_called()

        # no files changes
        files = list(find_files(self.topdir))
        self.assertEqual(files, orig)

    def test_build_not_a_dir(self):
        binfo = self.make_build()  # DEFAULT
        vinfo = self.make_volume('other')
        bdir = binfo['_orig_dir']
        os.rename(bdir, bdir + '_MOVED')
        os.symlink('junk', bdir)
        junk = os.path.dirname(bdir) + '/junk'
        with open(junk, 'wt') as fp:
            fp.write('Not a build directory\n')

        orig = list(find_files(self.topdir))
        with self.assertRaises(koji.GenericError) as ex:
            kojihub._set_build_volume(binfo, vinfo)

        self.assertIn('Not a directory:', str(ex.exception))
        self.UpdateProcessor.assert_not_called()

        # no files changes
        files = list(find_files(self.topdir))
        self.assertEqual(files, orig)


def find_files(dirpath):
    '''Find all files under dir, report relative paths'''
    for path, dirs, files in os.walk(dirpath, topdown=True):
        # sort dirs in place for consistent traversal
        dirs.sort()
        for fn in sorted(dirs + files):
            yield os.path.relpath(os.path.join(path, fn), dirpath)


# the end
