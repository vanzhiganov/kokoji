from unittest import mock
import unittest

import koji
import kojihub


class TestSetHostPassword(unittest.TestCase):

    def setUp(self):
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context_db = mock.patch('kojihub.db.context').start()
        self.context.session.assertPerm = mock.MagicMock()
        self.exports = kojihub.RootExports()
        self.get_host = mock.patch('kojihub.kojihub.get_host').start()
        self.hostinfo = {
            'id': 123,
            'user_id': 234,
            'name': 'builder1.example.com',
            'arches': 'x86_64',
            'enabled': True,
        }

    def tearDown(self):
        mock.patch.stopall()

    def test_set_host_password(self):
        self.get_host.return_value = self.hostinfo

        self.exports.setHostPassword('builder1.example.com', 's3cr3t')

        self.context.session.assertPerm.assert_called_once_with('admin')
        self.get_host.assert_called_once_with('builder1.example.com', strict=True)
        self.context.session.setPassword.assert_called_once_with(
            'builder1.example.com', 's3cr3t')

    def test_set_host_password_by_id(self):
        # the host may be looked up by id, but the credential belongs to the
        # host's user, i.e. its name
        self.get_host.return_value = self.hostinfo

        self.exports.setHostPassword(123, 's3cr3t')

        self.context.session.assertPerm.assert_called_once_with('admin')
        self.get_host.assert_called_once_with(123, strict=True)
        self.context.session.setPassword.assert_called_once_with(
            'builder1.example.com', 's3cr3t')

    def test_set_host_password_unknown_host(self):
        # get_host(strict=True) rejects anything that is not a registered host,
        # so this cannot be used to reset an arbitrary account
        self.get_host.side_effect = koji.GenericError('Invalid hostInfo: nope.example.com')

        with self.assertRaises(koji.GenericError):
            self.exports.setHostPassword('nope.example.com', 's3cr3t')

        self.context.session.assertPerm.assert_called_once_with('admin')
        self.context.session.setPassword.assert_not_called()

    def test_set_host_password_not_admin(self):
        self.context.session.assertPerm.side_effect = koji.GenericError(
            'You must have the "admin" permission to perform this action')
        self.get_host.return_value = self.hostinfo

        with self.assertRaises(koji.GenericError):
            self.exports.setHostPassword('builder1.example.com', 's3cr3t')

        # permission is checked before we look anything up or write anything
        self.get_host.assert_not_called()
        self.context.session.setPassword.assert_not_called()

    def test_set_host_password_empty(self):
        # validation lives in Session.setPassword; make sure we reach it and
        # that an empty password never turns into a usable credential
        self.get_host.return_value = self.hostinfo
        self.context.session.setPassword.side_effect = koji.GenericError(
            'password must be a non-empty string')

        with self.assertRaises(koji.GenericError):
            self.exports.setHostPassword('builder1.example.com', '')

        self.context.session.setPassword.assert_called_once_with('builder1.example.com', '')


if __name__ == '__main__':
    unittest.main()