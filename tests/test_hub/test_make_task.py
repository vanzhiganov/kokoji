import unittest

from unittest import mock

import koji
import koji.xmlrpcplus
from kojihub import kojihub, kojixmlrpc

QP = kojihub.QueryProcessor
IP = kojihub.InsertProcessor


class TestMakeTask(unittest.TestCase):
    def getQuery(self, *args, **kwargs):
        query = QP(*args, **kwargs)
        query.execute = mock.MagicMock()
        query.executeOne = mock.MagicMock()
        self.queries.append(query)
        return query

    def getInsert(self, *args, **kwargs):
        insert = IP(*args, **kwargs)
        insert.execute = mock.MagicMock()
        self.inserts.append(insert)
        return insert

    def setUp(self):
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context_db = mock.patch('kojihub.db.context').start()
        # self.get_user = mock.patch('kojihub.kojihub.get_user').start()
        self.opts = {
            'DefaultChannelCompat': True,
            'policy': {
                'channel': kojixmlrpc._default_policies['channel'],
                'priority': kojixmlrpc._default_policies['priority'],
            }
        }
        self.context.opts = self.opts

        self._dml = mock.patch('kojihub.db._dml').start()
        self.QueryProcessor = mock.patch('kojihub.kojihub.QueryProcessor',
                                         side_effect=self.getQuery).start()
        self.queries = []
        self.InsertProcessor = mock.patch('kojihub.kojihub.InsertProcessor',
                                          side_effect=self.getInsert).start()
        self.inserts = []

        self.get_channel = mock.patch('kojihub.kojihub.get_channel').start()
        self.get_channel_id = mock.patch('kojihub.kojihub.get_channel_id').start()
        self.currval = mock.patch('kojihub.kojihub.currval').start()
        self.auto_arch_refuse = mock.patch('kojihub.scheduler.auto_arch_refuse').start()
        self.Task = mock.patch('kojihub.kojihub.Task').start()

        self.set_policy()

    def tearDown(self):
        mock.patch.stopall()

    def set_policy(self, opts=None):
        # set policy from options
        if opts is None:
            opts = self.context.opts
        plugins = {}
        policy = kojixmlrpc.get_policy(opts, plugins)
        self.context.policy = policy or {}

    def test_make_task_simple(self):
        self.get_channel_id.return_value = 1

        kojihub.make_task('something', [1, 2, 3])

        self.get_channel_id.assert_called_once_with('default', strict=True)
        self.assertEqual(len(self.inserts), 1)
        expected = {'state': 0, 'method': 'something', 'parent': None, 'arch': 'noarch',
                    'channel_id': 1}
        for key in expected:
            self.assertEqual(self.inserts[0].data[key], expected[key])

    def test_make_task_default_channel_compat(self):
        self.get_channel.return_value = {'name': 'testing', 'id': 23, 'enabled': True}
        self.opts['DefaultChannelCompat'] = True
        self.opts['policy']['channel'] = '''
            has req_channel :: req
            all :: use bad
        '''
        self.set_policy()

        kojihub.make_task('something', [1, 2, 3], default_channel='testing')

        # in compat mode we expect to hit the "req" policy result
        self.get_channel.assert_called_once_with('testing')
        self.get_channel_id.assert_not_called()
        self.assertEqual(len(self.inserts), 1)
        expected = {'state': 0, 'method': 'something', 'parent': None, 'arch': 'noarch',
                    'channel_id': 23}
        for key in expected:
            self.assertEqual(self.inserts[0].data[key], expected[key])

    def test_make_task_default_channel_nocompat(self):
        self.get_channel_id.return_value = 23
        self.opts['DefaultChannelCompat'] = False
        self.opts['policy']['channel'] = '''
            has req_channel :: use bad
            all :: default
        '''
        self.set_policy()

        kojihub.make_task('something', [1, 2, 3], default_channel='testing')

        # without compat mode we expect to hit the "default" policy result
        self.get_channel_id.assert_called_once_with('testing', strict=True)
        self.get_channel.assert_not_called()
        self.assertEqual(len(self.inserts), 1)
        expected = {'state': 0, 'method': 'something', 'parent': None, 'arch': 'noarch',
                    'channel_id': 23}
        for key in expected:
            self.assertEqual(self.inserts[0].data[key], expected[key])

    def test_make_task_no_policy_result(self):
        # if channel policy does not match, we should use the default
        self.get_channel.return_value = {'name': 'testing', 'id': 23, 'enabled': True}
        self.get_channel_id.return_value = 23
        self.opts['policy']['channel'] = ''
        self.set_policy()

        kojihub.make_task('something', [1, 2, 3], default_channel='testing')

        self.get_channel_id.assert_called_once_with('testing', strict=True)
        self.get_channel.assert_called_once_with('testing')
        self.assertEqual(len(self.inserts), 1)
        expected = {'state': 0, 'method': 'something', 'parent': None, 'arch': 'noarch',
                    'channel_id': 23}
        for key in expected:
            self.assertEqual(self.inserts[0].data[key], expected[key])

    @mock.patch('kojihub.kojihub._get_task_parent')
    def test_make_task_with_parent(self, _get_task_parent):
        self.get_channel.return_value = {'name': 'testing', 'id': 23, 'enabled': True}
        self.opts['DefaultChannelCompat'] = True
        self.opts['policy']['channel'] = '''
            has req_channel :: req
            all :: use bad
        '''
        self.set_policy()
        # mock parent data
        kwargs = {'srpm': 'SRPM', 'build_tag': 100}
        arglist = koji.encode_args(**kwargs)
        request = koji.xmlrpcplus.dumps(tuple(arglist), methodname='parent_method')
        pdata = {
                'state': koji.TASK_STATES['OPEN'],
                'owner': 1,
                'channel_id':23,
                'priority': 20,
                'arch': 'noarch',
                'parent': None,
                'method': 'parent_method',
                'request': request,
        }
        _get_task_parent.return_value = pdata
        self.Task.return_value.getInfo.return_value = pdata

        kojihub.make_task('something', [1, 2, 3], default_channel='testing', parent=5678)

        # in compat mode we expect to hit the "req" policy result
        self.get_channel.assert_called_once_with('testing')
        self.get_channel_id.assert_not_called()
        self.assertEqual(len(self.inserts), 1)
        expected = {'state': 0, 'method': 'something', 'parent': 5678, 'arch': 'noarch',
                    'channel_id': 23}
        for key in expected:
            self.assertEqual(self.inserts[0].data[key], expected[key])

    @mock.patch('kojihub.kojihub._get_task_parent')
    def test_make_task_with_invalid_parent(self, _get_task_parent):
        _get_task_parent.return_value = None

        with self.assertRaises(koji.GenericError) as ex:
            kojihub.make_task('something', [1, 2, 3], default_channel='testing', parent=5678)

        self.assertEqual('Invalid parent task: 5678', str(ex.exception))

    @mock.patch('kojihub.kojihub._get_task_parent')
    def test_make_task_with_nonopen_parent(self, _get_task_parent):
        # mock parent data
        pdata = {
                'state': koji.TASK_STATES['FAILED'],
                'owner': 1,
                'channel_id':23,
                'priority': 20,
                'arch': 'noarch',
                'parent': None,
        }
        _get_task_parent.return_value = pdata

        with self.assertRaises(koji.GenericError) as ex:
            kojihub.make_task('something', [1, 2, 3], default_channel='testing', parent=5678)

        self.assertEqual('Parent task (id 5678) is not open', str(ex.exception))


# the end
