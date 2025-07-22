from __future__ import absolute_import

try:
    from unittest import mock
except ImportError:
    import mock
import six
import koji

from koji_cli.commands import handle_unblock_group
from . import utils


class TestBlockGroup(utils.CliTestCase):
    # Show long diffs in error output...
    maxDiff = None

    def setUp(self):
        self.maxDiff = None
        self.options = mock.MagicMock()
        self.options.debug = False
        self.session = mock.MagicMock()
        self.session.getAPIVersion.return_value = koji.API_VERSION
        self.activate_session_mock = mock.patch('koji_cli.commands.activate_session').start()
        self.error_format = """Usage: %s unblock-group [options] <tag> <group>
(Specify the --help global option for a list of other help options)

%s: error: {message}
""" % (self.progname, self.progname)

    def tearDown(self):
        mock.patch.stopall()

    def test_handle_unblock_group_badargs(self):
        tag = 'tag'
        group = 'group'
        arguments = [tag, group, 'extra_arg']
        self.session.hasPerm.return_value = True
        self.session.getTag.return_value = None

        expected = self.format_error_message(
            "You must specify a tag name and group name")
        # Run it and check immediate output
        self.assert_system_exit(
            handle_unblock_group,
            self.options, self.session, arguments,
            stderr=expected,
            stdout='',
            activate_session=None,
            exit_code=2)

        # Finally, assert that things were called as we expected.
        self.activate_session_mock.assert_not_called()
        self.session.groupListUnblock.assert_not_called()

    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_unblock_group(self, stdout):
        tag = 'tag'
        group = 'group'
        arguments = [tag, group]

        # Run it and check immediate output
        rv = handle_unblock_group(self.options, self.session, arguments)
        actual = stdout.getvalue()
        expected = ''
        self.assertMultiLineEqual(actual, expected)

        # Finally, assert that things were called as we expected.
        self.activate_session_mock.assert_called_once_with(self.session, self.options)
        self.session.groupListUnblock.assert_called_once_with(tag, group)
        self.assertEqual(rv, None)


# the end
