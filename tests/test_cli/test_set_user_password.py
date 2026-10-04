from __future__ import absolute_import
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import six

import koji
from koji_cli.commands import handle_set_user_password
from . import utils


class TestSetUserPassword(utils.CliTestCase):
    def setUp(self):
        self.options = mock.MagicMock()
        self.options.debug = False
        self.session = mock.MagicMock()
        self.session.getAPIVersion.return_value = koji.API_VERSION
        self.activate_session_mock = mock.patch('koji_cli.commands.activate_session').start()
        self.error_format = """Usage: %s set-user-password [options] <username>
(Specify the --help global option for a list of other help options)

%s: error: {message}
""" % (self.progname, self.progname)
        self.user = 'someuser'
        self.password = 's3cr3t'

    def tearDown(self):
        mock.patch.stopall()

    @mock.patch('getpass.getpass')
    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_set_user_password(self, stdout, getpass_mock):
        getpass_mock.side_effect = [self.password, self.password]
        args = [self.user]

        handle_set_user_password(self.options, self.session, args)

        self.assertMultiLineEqual(stdout.getvalue(),
                                 'Password set for user %s\n' % self.user)
        self.activate_session_mock.assert_called_once_with(self.session, self.options)
        self.session.setUserPassword.assert_called_once_with(self.user, self.password)

    @mock.patch('getpass.getpass')
    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_set_user_password_stdin(self, stdout, getpass_mock):
        args = [self.user, '--password-stdin']

        with mock.patch('sys.stdin', new_callable=six.StringIO) as stdin:
            stdin.write(self.password + '\n')
            stdin.seek(0)
            handle_set_user_password(self.options, self.session, args)

        self.assertMultiLineEqual(stdout.getvalue(),
                                 'Password set for user %s\n' % self.user)
        self.session.setUserPassword.assert_called_once_with(self.user, self.password)
        getpass_mock.assert_not_called()

    @mock.patch('getpass.getpass')
    def test_handle_set_user_password_empty(self, getpass_mock):
        getpass_mock.return_value = ''
        args = [self.user]

        self.assert_system_exit(
            handle_set_user_password,
            self.options,
            self.session,
            args,
            stdout='',
            stderr='Password must not be empty\n',
            activate_session=None,
            exit_code=1
        )

        self.session.setUserPassword.assert_not_called()

    def test_handle_set_user_password_no_arg(self):
        expected = self.format_error_message("Please specify the username of the user")
        self.assert_system_exit(
            handle_set_user_password,
            self.options,
            self.session,
            [],
            stdout='',
            stderr=expected,
            activate_session=None,
            exit_code=2
        )

        self.activate_session_mock.assert_not_called()
        self.session.setUserPassword.assert_not_called()

    def test_handle_set_user_password_too_many_args(self):
        expected = self.format_error_message(
            "This command only accepts one argument (username)")
        self.assert_system_exit(
            handle_set_user_password,
            self.options,
            self.session,
            [self.user, 'extra'],
            stdout='',
            stderr=expected,
            activate_session=None,
            exit_code=2
        )

        self.activate_session_mock.assert_not_called()
        self.session.setUserPassword.assert_not_called()

    def test_handle_set_user_password_help(self):
        self.assert_help(
            handle_set_user_password,
            """Usage: %s set-user-password [options] <username>
(Specify the --help global option for a list of other help options)

Options:
  -h, --help        show this help message and exit
  --password-stdin  read the password from stdin instead of prompting for it
""" % self.progname)


if __name__ == '__main__':
    unittest.main()