import unittest
from unittest import mock

import koji
import kojihub


class TestHostTagBuild(unittest.TestCase):

    def setUp(self):
        self.Host = mock.patch('kojihub.kojihub.Host').start()
        self.Task = mock.patch('kojihub.kojihub.Task').start()
        self.Task().assertHost = mock.MagicMock()
        self.get_build = mock.patch('kojihub.kojihub.get_build').start()
        self.get_tag = mock.patch('kojihub.kojihub.get_tag').start()
        self.assert_policy = mock.patch('kojihub.kojihub.assert_policy').start()
        self.readPackageList = mock.patch('kojihub.kojihub.readPackageList').start()
        self._tag_build = mock.patch('kojihub.kojihub._tag_build').start()
        self._untag_build = mock.patch('kojihub.kojihub._untag_build').start()
        self._tag_build = mock.patch('kojihub.kojihub._tag_build').start()
        self.pkglist_add = mock.patch('kojihub.kojihub.pkglist_add').start()
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context.session.assertPerm = mock.MagicMock()

        # just in case
        self.dml1 = mock.patch('kojihub.db._dml').start()
        self.dml2 = mock.patch('kojihub.kojihub._dml').start()

        self.tagBuild = kojihub.HostExports().tagBuild

    def tearDown(self):
        # our other mocks should prevent dml from ever being called
        self.dml1.assert_not_called()
        self.dml2.assert_not_called()
        mock.patch.stopall()

    def test_simple_host_tag(self):
        # call args
        task_id = 12345
        tag = "my-tag"
        build = 'foo-1-3.x'

        # mocked values
        binfo = {'name': 'foo', 'version': '1', 'release': '3.x', 'package_id': 100}
        self.get_build.return_value = binfo
        user_id = 1701
        self.Task().getOwner.return_value = user_id
        self.Task().getInfo.return_value = {'id': task_id, 'parent': 12340}
        self.readPackageList.return_value = {100: {'package_name': 'foo', 'blocked': False}}

        # make the call
        self.tagBuild(task_id, tag, build)

        # check
        self._tag_build.assert_called_once_with(tag, binfo, user_id=user_id, force=False)
        self._untag_build.assert_not_called()
        self.pkglist_add.assert_not_called()
        self.assert_policy.assert_called_once()
        self.get_tag.assert_called_once()
        policy_name = self.assert_policy.call_args[0][0]
        policy_data = self.assert_policy.call_args[0][1]
        policy_force = self.assert_policy.call_args[1]['force']
        self.assertEqual(policy_name, 'tag')
        self.assertEqual(policy_force, False)
        expected = {'build': binfo, 'by_tag_subtask': True, 'fromtag': None,
                    'operation': 'tag', 'tag': tag, 'user_id': user_id}
        self.assertEqual(policy_data, expected)

    def test_simple_host_move(self):
        # call args
        task_id = 12345
        tag = 'my-tag'
        fromtag = 'other-tag'
        build = 'foo-1-3.x'

        # mocked values
        binfo = {'name': 'foo', 'version': '1', 'release': '3.x', 'package_id': 100}
        self.get_build.return_value = binfo
        user_id = 1701
        self.Task().getOwner.return_value = user_id
        self.Task().getInfo.return_value = {'id': task_id, 'parent': None}
        self.readPackageList.return_value = {100: {'package_name': 'foo', 'blocked': False}}

        # make the call
        self.tagBuild(task_id, tag, build, fromtag=fromtag)

        # check
        self._untag_build.assert_called_once_with(fromtag, binfo, user_id=user_id, force=False, strict=True)
        self._tag_build.assert_called_once_with(tag, binfo, user_id=user_id, force=False)
        self.pkglist_add.assert_not_called()
        self.assert_policy.assert_called_once()
        policy_name = self.assert_policy.call_args[0][0]
        policy_data = self.assert_policy.call_args[0][1]
        policy_force = self.assert_policy.call_args[1]['force']
        self.assertEqual(policy_name, 'tag')
        self.assertEqual(policy_force, False)
        expected = {'build': binfo, 'by_tag_subtask': False, 'fromtag': fromtag,
                    'operation': 'move', 'tag': tag, 'user_id': user_id}
        self.assertEqual(policy_data, expected)

        # non-string from tag
        fromtag = 137
        self.get_tag.side_effect = [{'id': 100, 'name': tag}, {'id':fromtag, 'name': 'other-tag'}]
        self.tagBuild(task_id, tag, build, fromtag=fromtag)
        policy_data = self.assert_policy.call_args[0][1]
        self.assertEqual(policy_data['fromtag'], 'other-tag')

    def test_tag_errors(self):
        # call args
        task_id = 12345
        tag = "my-tag"
        build = 'foo-1-3.x'

        # mocked values
        binfo = {'name': 'foo', 'version': '1', 'release': '3.x', 'package_id': 100}
        self.get_build.return_value = binfo
        user_id = 1701
        self.Task().getOwner.return_value = user_id
        self.Task().getInfo.return_value = {'id': task_id, 'parent': 12340}
        self.readPackageList.return_value = {}  # not in list

        # make the call
        with self.assertRaises(koji.TagError):
            self.tagBuild(task_id, tag, build)

        # blocked case
        self.readPackageList.return_value = {100: {'package_name': 'foo', 'blocked': True}}
        with self.assertRaises(koji.TagError):
            self.tagBuild(task_id, tag, build)

        # confirm no actions
        self._tag_build.assert_not_called()
        self._untag_build.assert_not_called()
        self.pkglist_add.assert_not_called()

    def test_force_pkg(self):
        # call args
        task_id = 12345
        tag = "my-tag"
        build = 'foo-1-3.x'

        # mocked values
        binfo = {'name': 'foo', 'version': '1', 'release': '3.x', 'package_id': 100, 'nvr': 'NVR'}
        self.get_build.return_value = binfo
        user_id = 1701
        self.Task().getOwner.return_value = user_id
        self.Task().getInfo.return_value = {'id': task_id, 'parent': 12340}
        self.readPackageList.return_value = {}  # not in list

        # should error without perms
        self.context.session.hasPerm.return_value = False
        with self.assertRaises(koji.TagError):
            self.tagBuild(task_id, tag, build, force=True)

        # confirm no actions
        self._tag_build.assert_not_called()
        self._untag_build.assert_not_called()
        self.pkglist_add.assert_not_called()

        # should succeed with admin perm
        self.context.session.hasPerm.return_value = True
        self.tagBuild(task_id, tag, build, force=True)

        # check
        self._tag_build.assert_called_once_with(tag, binfo, user_id=user_id, force=True)
        self._untag_build.assert_not_called()
        self.pkglist_add.assert_called_once()
        policy_name = self.assert_policy.call_args[0][0]
        policy_data = self.assert_policy.call_args[0][1]
        policy_force = self.assert_policy.call_args[1]['force']
        self.assertEqual(policy_name, 'tag')
        self.assertEqual(policy_force, True)
        expected = {'build': binfo, 'by_tag_subtask': True, 'fromtag': None,
                    'operation': 'tag', 'tag': tag, 'user_id': user_id}
        self.assertEqual(policy_data, expected)



# the end
