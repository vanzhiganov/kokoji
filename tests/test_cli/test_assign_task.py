from __future__ import absolute_import
try:
    from unittest import mock
except ImportError:
    import mock
import six
import unittest

import koji
from koji_cli.commands import handle_assign_task
from . import utils


class TestAssignTask(utils.CliTestCase):

    def setUp(self):
        # Show long diffs in error output...
        self.maxDiff = None
        self.options = mock.MagicMock()
        self.options.debug = False
        self.session = mock.MagicMock()
        self.session.getAPIVersion.return_value = koji.API_VERSION
        self.activate_session_mock = mock.patch('koji_cli.commands.activate_session').start()
        self.error_format = """Usage: %s assign-task <task_id> <hostname>
(Specify the --help global option for a list of other help options)

%s: error: {message}
""" % (self.progname, self.progname)
        self.hostname = "host"
        self.task_id = "1"

    def tearDown(self):
        mock.patch.stopall()

    def test_handle_assign_task_no_such_task(self):
        arguments = [self.task_id, self.hostname]

        self.session.getTaskInfo.return_value = None
        with six.assertRaisesRegex(self, koji.GenericError,
                                   "No such task: %s" % self.task_id):
            handle_assign_task(self.options, self.session, arguments)
        self.session.getTaskInfo.assert_called_with(int(self.task_id), request=False)
        self.session.getHost.assert_not_called()
        self.session.hasPerm.assert_not_called()
        self.session.assignTask.assert_not_called()

    def test_handle_assign_task_no_such_host(self):
        arguments = [self.task_id, self.hostname]
        self.session.getTaskInfo.return_value = "task_info"
        self.session.getHost.return_value = None
        with six.assertRaisesRegex(self, koji.GenericError,
                                   "No such host: %s" % self.hostname):
            handle_assign_task(self.options, self.session, arguments)
        self.session.getTaskInfo.assert_called_with(int(self.task_id), request=False)
        self.session.getHost.assert_called_with(self.hostname)
        self.session.hasPerm.assert_not_called()
        self.session.assignTask.assert_not_called()

    def test_handle_assign_task_without_perm(self):
        arguments = [self.task_id, self.hostname]
        self.session.getHost.return_value = self.hostname
        self.session.hasPerm.return_value = False
        self.assert_system_exit(
            handle_assign_task,
            self.options, self.session, arguments,
            stdout='',
            stderr=self.format_error_message("This action requires admin privileges"),
            exit_code=2
        )
        self.session.getTaskInfo.assert_called_with(int(self.task_id), request=False)
        self.session.getHost.assert_called_with(self.hostname)
        self.session.hasPerm.assert_called_with('admin')
        self.session.assignTask.assert_not_called()

    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_assign_task_with_force_with_perm(self, stdout):
        arguments = [self.task_id, self.hostname]
        arguments.append("--force")
        self.session.hasPerm.return_value = True
        self.session.assignTask.return_value = True
        handle_assign_task(self.options, self.session, arguments)
        actual = stdout.getvalue()
        expected = 'assigned task %s to host %s\n' % (self.task_id, self.hostname)
        self.assertMultiLineEqual(actual, expected)
        self.session.getTaskInfo.assert_called_with(int(self.task_id), request=False)
        self.session.getHost.assert_called_with(self.hostname)
        self.session.hasPerm.assert_called_with('admin')
        self.session.assignTask.assert_called_with(int(self.task_id), self.hostname, True)

    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_assign_task_failed_assign(self, stdout):
        arguments = [self.task_id, self.hostname]
        self.session.hasPerm.return_value = True
        self.session.assignTask.return_value = False
        handle_assign_task(self.options, self.session, arguments)
        actual = stdout.getvalue()
        expected = 'failed to assign task %s to host %s\n' % (self.task_id, self.hostname)
        self.assertMultiLineEqual(actual, expected)
        self.activate_session_mock.assert_called_with(self.session, self.options)
        self.session.getTaskInfo.assert_called_with(int(self.task_id), request=False)
        self.session.getHost.assert_called_with(self.hostname)
        self.session.hasPerm.assert_called_with('admin')
        self.session.assignTask.assert_called_with(int(self.task_id), self.hostname, False)

    @mock.patch('sys.stdout', new_callable=six.StringIO)
    def test_handle_assign_task_override(self, stdout):
        arguments = [self.task_id, self.hostname]
        arguments.append("--override")
        self.session.hasPerm.return_value = True
        self.session.assignTask.return_value = True
        handle_assign_task(self.options, self.session, arguments)
        actual = stdout.getvalue()
        expected = 'assigned task %s to host %s\n' % (self.task_id, self.hostname)
        self.assertMultiLineEqual(actual, expected)
        self.activate_session_mock.assert_called_with(self.session, self.options)
        self.session.getTaskInfo.assert_called_with(int(self.task_id), request=False)
        self.session.getHost.assert_called_with(self.hostname)
        self.session.hasPerm.assert_called_with('admin')
        self.session.assignTask.assert_called_with(
            int(self.task_id), self.hostname, False, override=True)

    def test_handle_assign_task_no_args(self):
        arguments = []
        # Run it and check immediate output
        self.assert_system_exit(
            handle_assign_task,
            self.options, self.session, arguments,
            stdout='',
            stderr=self.format_error_message('please specify a task id and a hostname'),
            activate_session=None,
            exit_code=2
        )

        # Finally, assert that things were called as we expected.
        self.activate_session_mock.assert_not_called()
        self.session.hasHost.assert_not_called()
        self.session.addHost.assert_not_called()

    def test_assign_task_help(self):
        self.assert_help(
            handle_assign_task,
            """Usage: %s assign-task <task_id> <hostname>
(Specify the --help global option for a list of other help options)

Options:
  -h, --help   show this help message and exit
  -f, --force  force to assign a non-free task
  --override   prevent the scheduler from reassigning later
""" % self.progname)


if __name__ == '__main__':
    unittest.main()
