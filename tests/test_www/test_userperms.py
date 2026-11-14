import unittest

try:
    from unittest import mock
except ImportError:
    import mock

import koji
from koji.server import ServerRedirect

from .loadwebindex import webidx


class TestUserPerms(unittest.TestCase):

    def setUp(self):
        self.server = mock.MagicMock()
        self.server.getUser.return_value = {'id': 5, 'name': 'alice'}
        self.server.getUserPerms.return_value = ['admin']
        self.environ = {
            'koji.currentUser': {'id': 1, 'name': 'admin'},
        }
        patches = [
            mock.patch.object(webidx, '_getServer', return_value=self.server),
            mock.patch.object(webidx, '_assertLogin'),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_grant_calls_hub_and_redirects_to_user(self):
        with self.assertRaises(ServerRedirect):
            webidx.userperms(self.environ, '5', 'tag', 'grant')
        self.server.grantPermission.assert_called_once_with(5, 'tag')
        self.assertIn('userinfo?userID=5', self.environ['koji.redirect'])

    def test_revoke_calls_hub(self):
        with self.assertRaises(ServerRedirect):
            webidx.userperms(self.environ, '5', 'tag', 'revoke')
        self.server.revokePermission.assert_called_once_with(5, 'tag')

    def test_non_admin_is_refused(self):
        self.server.getUserPerms.return_value = ['tag']
        with self.assertRaises(koji.ActionNotAllowed):
            webidx.userperms(self.environ, '5', 'tag', 'grant')
        self.server.grantPermission.assert_not_called()

    def test_admin_cannot_revoke_own_admin(self):
        self.server.getUser.return_value = {'id': 1, 'name': 'admin'}
        with self.assertRaises(koji.ActionNotAllowed):
            webidx.userperms(self.environ, '1', 'admin', 'revoke')
        self.server.revokePermission.assert_not_called()

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(koji.GenericError):
            webidx.userperms(self.environ, '5', 'tag', 'delete')
        self.server.grantPermission.assert_not_called()
        self.server.revokePermission.assert_not_called()


if __name__ == '__main__':
    unittest.main()
