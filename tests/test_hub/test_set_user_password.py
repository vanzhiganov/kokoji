from unittest import mock
import unittest

import koji
import kojihub


class TestSetUserPassword(unittest.TestCase):

    def setUp(self):
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context_db = mock.patch('kojihub.db.context').start()
        self.context.session.assertPerm = mock.MagicMock()
        self.exports = kojihub.RootExports()
        self.get_user = mock.patch('kojihub.kojihub.get_user').start()
        self.userinfo = {
            'id': 42,
            'name': 'someuser',
            'status': koji.USER_STATUS['NORMAL'],
            'usertype': koji.USERTYPES['NORMAL'],
        }

    def tearDown(self):
        mock.patch.stopall()

    def test_set_user_password(self):
        self.get_user.return_value = self.userinfo

        self.exports.setUserPassword('someuser', 's3cr3t')

        self.context.session.assertPerm.assert_called_once_with('admin')
        self.get_user.assert_called_once_with(userInfo={'name': 'someuser'}, strict=True)
        self.context.session.setPassword.assert_called_once_with('someuser', 's3cr3t')

    def test_set_user_password_host(self):
        # a builder account is a user too, so this covers hosts as well
        self.get_user.return_value = dict(self.userinfo,
                                          name='builder1.example.com',
                                          usertype=koji.USERTYPES['HOST'])

        self.exports.setUserPassword('builder1.example.com', 's3cr3t')

        self.context.session.assertPerm.assert_called_once_with('admin')
        self.context.session.setPassword.assert_called_once_with(
            'builder1.example.com', 's3cr3t')

    def test_set_user_password_group(self):
        # groups are modelled as users but cannot log in
        self.get_user.return_value = dict(self.userinfo,
                                          name='somegroup',
                                          usertype=koji.USERTYPES['GROUP'])

        with self.assertRaises(koji.GenericError) as ex:
            self.exports.setUserPassword('somegroup', 's3cr3t')

        self.assertEqual(
            'groups cannot log in, so they have no password: somegroup',
            str(ex.exception))
        self.context.session.setPassword.assert_not_called()

    def test_set_user_password_unknown_user(self):
        self.get_user.side_effect = koji.GenericError('Invalid userInfo: nobody')

        with self.assertRaises(koji.GenericError):
            self.exports.setUserPassword('nobody', 's3cr3t')

        self.context.session.assertPerm.assert_called_once_with('admin')
        self.context.session.setPassword.assert_not_called()

    def test_set_user_password_not_admin(self):
        self.context.session.assertPerm.side_effect = koji.GenericError(
            'You must have the "admin" permission to perform this action')
        self.get_user.return_value = self.userinfo

        with self.assertRaises(koji.GenericError):
            self.exports.setUserPassword('someuser', 's3cr3t')

        self.get_user.assert_not_called()
        self.context.session.setPassword.assert_not_called()


if __name__ == '__main__':
    unittest.main()