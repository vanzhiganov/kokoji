from __future__ import absolute_import
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

import six

import koji
from koji_cli.commands import handle_set_host_password
from . import utils


class TestSetHostPassword(utils.CliTestCase):
    def setUp(self):
        self.options = mock.MagicMock()
        self.options.debug = False
        self.session = mock.MagicMock()
        self.session.getAPIVersion.return_value = koji.API_VERSION
        self.activate_session_mock = mock.patch('koji_cli.commands.activate_session').start()
        self.error_format = """Usage: %s set-host-password [options] <hostname>
(Specify the --help global option for a list of other help options)

%s: error: {message}
""" % (self.progname, self.progname)
        self.host = 'builder1.example.com'
        self.password = 's3cr3t'

    def tearDown(self):
        mock.patch.stopall()

    @mock.patch('getpass.getpass')
    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_set_host_password(self, stdout, getpass_mock):
        # prompted twice for confirmation
        getpass_mock.side_effect = [self.password, self.password]
        args = [self.host]

        handle_set_host_password(self.options, self.session, args)

        self.assertMultiLineEqual(stdout.getvalue(),
                                 'Password set for host %s\n' % self.host)
        self.activate_session_mock.assert_called_once_with(self.session, self.options)
        self.session.setHostPassword.assert_called_once_with(self.host, self.password)

    @mock.patch('getpass.getpass')
    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_set_host_password_arg(self, stdout, getpass_mock):
        args = [self.host, '--password=' + self.password]

        handle_set_host_password(self.options, self.session, args)

        self.assertMultiLineEqual(stdout.getvalue(),
                                 'Password set for host %s\n' % self.host)
        self.session.setHostPassword.assert_called_once_with(self.host, self.password)
        # no prompt when the password came from the command line
        getpass_mock.assert_not_called()

    @mock.patch('getpass.getpass')
    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_set_host_password_arg_separate(self, stdout, getpass_mock):
        # optparse also accepts the value as a following argument
        args = [self.host, '--password', self.password]

        handle_set_host_password(self.options, self.session, args)

        self.session.setHostPassword.assert_called_once_with(self.host, self.password)
        getpass_mock.assert_not_called()

    @mock.patch('getpass.getpass')
    def test_handle_set_host_password_arg_empty(self, getpass_mock):
        args = [self.host, '--password=']

        self.assert_system_exit(
            handle_set_host_password,
            self.options,
            self.session,
            args,
            stdout='',
            stderr='Password must not be empty\n',
            activate_session=None,
            exit_code=1
        )

        self.session.setHostPassword.assert_not_called()
        getpass_mock.assert_not_called()

    @mock.patch('getpass.getpass')
    def test_handle_set_host_password_arg_and_stdin(self, getpass_mock):
        # ambiguous: refuse rather than silently pick one
        args = [self.host, '--password=' + self.password, '--password-stdin']

        self.assert_system_exit(
            handle_set_host_password,
            self.options,
            self.session,
            args,
            stdout='',
            stderr='--password and --password-stdin are mutually exclusive\n',
            activate_session=None,
            exit_code=1
        )

        self.session.setHostPassword.assert_not_called()

    @mock.patch('getpass.getpass')
    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_set_host_password_stdin(self, stdout, getpass_mock):
        args = [self.host, '--password-stdin']

        with mock.patch('sys.stdin', new_callable=six.StringIO) as stdin:
            stdin.write(self.password + '\n')
            stdin.seek(0)
            handle_set_host_password(self.options, self.session, args)

        self.assertMultiLineEqual(stdout.getvalue(),
                                 'Password set for host %s\n' % self.host)
        self.session.setHostPassword.assert_called_once_with(self.host, self.password)
        # no interactive prompt when reading from stdin
        getpass_mock.assert_not_called()

    @mock.patch('getpass.getpass')
    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_set_host_password_mismatch(self, stdout, getpass_mock):
        getpass_mock.side_effect = ['first', 'second', 'third', 'third']
        args = [self.host]

        handle_set_host_password(self.options, self.session, args)

        actual = stdout.getvalue()
        # the user is told to retry, and the accepted value is the third/fourth
        self.assertIn('Passwords do not match, please try again\n', actual)
        self.assertEqual(actual.count('Passwords do not match'), 1)
        self.session.setHostPassword.assert_called_once_with(self.host, 'third')

    @mock.patch('getpass.getpass')
    def test_handle_set_host_password_empty(self, getpass_mock):
        getpass_mock.return_value = ''
        args = [self.host]

        expected = 'Password must not be empty\n'
        self.assert_system_exit(
            handle_set_host_password,
            self.options,
            self.session,
            args,
            stdout='',
            stderr=expected,
            activate_session=None,
            exit_code=1
        )

        self.session.setHostPassword.assert_not_called()

    def test_handle_set_host_password_empty_stdin(self):
        args = [self.host, '--password-stdin']

        with mock.patch('sys.stdin', new_callable=six.StringIO) as stdin:
            stdin.seek(0)
            self.assert_system_exit(
                handle_set_host_password,
                self.options,
                self.session,
                args,
                stdout='',
                stderr='No password was read from stdin\n',
                activate_session=None,
                exit_code=1
            )

        self.session.setHostPassword.assert_not_called()

    def test_handle_set_host_password_no_arg(self):
        expected = self.format_error_message("Please specify the hostname of the host")
        self.assert_system_exit(
            handle_set_host_password,
            self.options,
            self.session,
            [],
            stdout='',
            stderr=expected,
            activate_session=None,
            exit_code=2
        )

        self.activate_session_mock.assert_not_called()
        self.session.setHostPassword.assert_not_called()

    def test_handle_set_host_password_too_many_args(self):
        expected = self.format_error_message(
            "This command only accepts one argument (hostname)")
        self.assert_system_exit(
            handle_set_host_password,
            self.options,
            self.session,
            [self.host, 'extra'],
            stdout='',
            stderr=expected,
            activate_session=None,
            exit_code=2
        )

        self.activate_session_mock.assert_not_called()
        self.session.setHostPassword.assert_not_called()

    def test_handle_set_host_password_help(self):
        self.assert_help(
            handle_set_host_password,
            """Usage: %s set-host-password [options] <hostname>
(Specify the --help global option for a list of other help options)

Options:
  -h, --help           show this help message and exit
  --password=PASSWORD  use this password instead of prompting for one. Visible
                       to other users through ps, so prefer --password-stdin
                       where you can
  --password-stdin     read the password from stdin instead of prompting for
                       it
""" % self.progname)


if __name__ == '__main__':
    unittest.main()