from __future__ import absolute_import

try:
    from unittest import mock
except ImportError:
    import mock
import six

from koji_cli.commands import handle_remove_group_req

import koji
from . import utils


class TestRemoveGroupReq(utils.CliTestCase):

    def setUp(self):
        # Show long diffs in error output...
        self.maxDiff = None
        self.options = mock.MagicMock()
        self.options.debug = False
        self.session = mock.MagicMock()
        self.session.getAPIVersion.return_value = koji.API_VERSION
        self.activate_session_mock = mock.patch('koji_cli.commands.activate_session').start()
        self.error_format = """Usage: %s remove-group-req [options] <tag> <group> <req> [<req> ...]
(Specify the --help global option for a list of other help options)

%s: error: {message}
""" % (self.progname, self.progname)

    def tearDown(self):
        mock.patch.stopall()

    def test_wrong_count_args(self):
        tag = 'tag'
        group = 'group'
        args = [tag, group]
        expected_error = self.format_error_message(
            'You must specify a tag name, group name, and one or more requirement names')
        self.assert_system_exit(
            handle_remove_group_req,
            self.options, self.session, args,
            stderr=expected_error,
            stdout='',
            activate_session=None,
            exit_code=2)
        # Finally, assert that things were called as we expected.
        self.activate_session_mock.assert_not_called()
        self.session.getTag.assert_not_called()
        self.session.groupReqListRemove.assert_not_called()
        self.session.multicall.assert_not_called()

    def test_no_such_tag(self):
        tag = 'tag'
        group = 'group'
        req = 'other_group'
        args = [tag, group, req]
        self.session.getTag.return_value = None

        self.assert_system_exit(
            handle_remove_group_req,
            self.options, self.session, args,
            stderr='No such tag: tag\n',
            stdout='',
            activate_session=None,
            exit_code=1)

        # Finally, assert that things were called as we expected.
        self.session.getTag.assert_called_once()
        self.session.groupReqListRemove.assert_not_called()
        self.session.multicall.assert_not_called()

    @mock.patch('sys.stdout', new_callable=six.StringIO)
    @mock.patch('sys.stderr', new_callable=six.StringIO)
    def test_success(self, stderr, stdout):
        tag = 'tag'
        tagID = 1
        dsttag = {'name': tag, 'id': tagID}
        group = 'group'
        req = 'other_group'
        args = [tag, group, req]

        self.session.getTag.return_value = dsttag
        self.session.getTagGroups.return_value = [
            {'name': group, 'group_id': 'groupId', 'blocked': False, 'tag_id': tagID,
             'grouplist': [{'name': req, 'blocked': False, 'tag_id': tagID}]
            }]

        handle_remove_group_req(self.options, self.session, args)

        actual = stderr.getvalue()
        expected = ''
        self.assertMultiLineEqual(actual, expected)
        actual = stdout.getvalue()
        expected = ''
        self.assertMultiLineEqual(actual, expected)
        # Finally, assert that things were called as we expected.
        self.activate_session_mock.assert_called_once_with(self.session, self.options)
        self.session.getTag.assert_called_once_with(tag)
        self.session.multicall.assert_called_once()

    def test_handle_group_not_present(self):
        tag = 'tag'
        tagID = 1
        dsttag = {'name': tag, 'id': tagID}
        group = 'group'
        req = 'other_group'
        args = [tag, group, req]

        self.session.getTag.return_value = dsttag
        self.session.getTagGroups.return_value = []

        self.assert_system_exit(
            handle_remove_group_req,
            self.options, self.session, args,
            stderr='Group group is not present in tag tag\n',
            stdout='',
            exit_code=1)

        self.session.getTag.assert_called_once_with(tag)
        self.session.groupReqListRemove.assert_not_called()
        self.session.multicall.assert_not_called()

    def test_handle_req_not_included(self):
        tag = 'tag'
        tagID = 1
        dsttag = {'name': tag, 'id': tagID}
        group = 'group'
        req = 'other_group'
        args = [tag, group, req]

        self.session.getTag.return_value = dsttag
        self.session.getTagGroups.return_value = [
            {'name': group, 'group_id': 'groupId', 'blocked': False, 'tag_id': tagID,
             'grouplist': []
            }]

        self.assert_system_exit(
            handle_remove_group_req,
            self.options, self.session, args,
            stdout='Req other_group is not included in this group\n',
            stderr='Invalid parameters\n',
            exit_code=1)

        self.session.getTag.assert_called_once_with(tag)
        self.session.groupReqListRemove.assert_not_called()
        self.session.multicall.assert_not_called()

    def test_handle_req_blocked(self):
        tag = 'tag'
        tagID = 1
        dsttag = {'name': tag, 'id': tagID}
        group = 'group'
        req = 'other_group'
        args = [tag, group, req]

        self.session.getTag.return_value = dsttag
        self.session.getTagGroups.return_value = [
            {'name': group, 'group_id': 'groupId', 'blocked': False, 'tag_id': tagID,
             'grouplist': [{'name': req, 'blocked': True, 'tag_id': tagID}]
            }]

        self.assert_system_exit(
            handle_remove_group_req,
            self.options, self.session, args,
            stdout='Req other_group is blocked in this group. '
                   'You could use unblock-group-req to unblock it\n',
            stderr='Invalid parameters\n',
            exit_code=1)

        self.session.getTag.assert_called_once_with(tag)
        self.session.groupReqListRemove.assert_not_called()
        self.session.multicall.assert_not_called()

    def test_handle_req_inherited(self):
        tag = 'tag'
        tagID = 1
        dsttag = {'name': tag, 'id': tagID}
        parentID = 20
        ptag = {'name': 'parent', 'id': parentID}
        group = 'group'
        req = 'other_group'
        args = [tag, group, req]

        self.session.getTag.side_effect = [dsttag, ptag]
        self.session.getTagGroups.return_value = [
            {'name': group, 'group_id': 'groupId', 'blocked': False, 'tag_id': tagID,
             'grouplist': [{'name': req, 'blocked': False, 'tag_id': parentID}]
            }]

        self.assert_system_exit(
            handle_remove_group_req,
            self.options, self.session, args,
            stdout='The entry for req other_group is inherited from parent. You could use block-group-req to prevent this\n',
            stderr='Invalid parameters\n',
            exit_code=1)
        self.session.groupReqListRemove.assert_not_called()
        self.session.multicall.assert_not_called()


# the end
