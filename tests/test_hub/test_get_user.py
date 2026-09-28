from unittest import mock

import koji
import kojihub
from .utils import DBQueryTestCase


class TestGetUser(DBQueryTestCase):

    def setUp(self):
        super(TestGetUser, self).setUp()
        self.exports = kojihub.RootExports()
        self.context = mock.patch('kojihub.kojihub.context').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_wrong_format_user_info(self):
        userinfo = ['test-user']
        with self.assertRaises(koji.GenericError) as cm:
            self.exports.getUser(userinfo)
        self.assertEqual(f"Invalid type for userInfo: {type(userinfo)}", str(cm.exception))

    def test_wrong_format_userid(self):
        userinfo = {'id': '123456'}
        with self.assertRaises(koji.GenericError) as cm:
            self.exports.getUser(userinfo)
        self.assertEqual(f"Invalid type for userid: {type(userinfo['id'])}", str(cm.exception))

    def test_wrong_format_username(self):
        userinfo = {'name': 57896}
        with self.assertRaises(koji.GenericError) as cm:
            self.exports.getUser(userinfo)
        self.assertEqual(f"Invalid type for username: {type(userinfo['name'])}", str(cm.exception))

    def test_not_logged_user(self):
        self.context.session.user_id = None
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.get_user(userInfo=None)
        self.assertEqual("No user provided", str(cm.exception))

    def test_userinfo_string(self):
        userinfo = 'test-user'
        kojihub.get_user(userinfo)
        self.assertEqual(len(self.queries), 1)
        query = self.queries[0]
        str(query)
        self.assertEqual(query.tables, ['users'])
        columns = ['id', 'name', 'status', 'usertype']
        self.assertEqual(set(query.columns), set(columns))
        self.assertEqual(query.clauses, ['name = %(info)s'])
        self.assertIsNone(query.joins)
        self.assertEqual(query.values, {'info': userinfo})

    def test_userinfo_dict(self):
        userinfo = {'id': 123456, 'name': 'test-user'}
        self.qp_execute_one_return_value = {'id': 123456, 'name': 'test-user',
                                            'status': 1, 'usertype': 1}
        result = kojihub.get_user(userinfo)
        self.assertEqual(result, {'id': 123456, 'name': 'test-user',
                                  'status': 1, 'usertype': 1})
        self.assertEqual(len(self.queries), 1)
        query = self.queries[0]
        str(query)
        self.assertEqual(query.tables, ['users'])
        columns = ['id', 'name', 'status', 'usertype']
        self.assertEqual(set(query.columns), set(columns))
        self.assertEqual(query.clauses, ['users.id = %(id)i', 'users.name = %(name)s'])
        self.assertIsNone(query.joins)
        self.assertEqual(query.values, userinfo)

    def test_userinfo_int_user_not_exist_and_strict(self):
        userinfo = {'id': 123456}
        self.qp_execute_one_return_value = {}
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.get_user(userinfo['id'], strict=True)
        self.assertEqual(f"No such user: {userinfo['id']}", str(cm.exception))
        self.assertEqual(len(self.queries), 1)
        query = self.queries[0]
        str(query)
        self.assertEqual(query.tables, ['users'])
        columns = ['id', 'name', 'status', 'usertype']
        self.assertEqual(set(query.columns), set(columns))
        self.assertEqual(query.clauses, ['users.id = %(id)i'])
        self.assertIsNone(query.joins)
        self.assertEqual(query.values, userinfo)
