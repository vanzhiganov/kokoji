from unittest import mock
import unittest

import koji
from kojihub import kojihub

QP = kojihub.QueryProcessor
UP = kojihub.UpdateProcessor
DP = kojihub.DeleteProcessor


class TestRecycleBuild(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.QueryProcessor = mock.patch('kojihub.kojihub.QueryProcessor',
                                         side_effect=self.getQuery).start()
        self.queries = []
        self.query_execute = mock.MagicMock()
        self.UpdateProcessor = mock.patch('kojihub.kojihub.UpdateProcessor',
                                          side_effect=self.getUpdate).start()
        self.run_callbacks = mock.patch('koji.plugin.run_callbacks').start()
        self.rmtree = mock.patch('koji.util.rmtree').start()
        self.unlink = mock.patch('os.unlink').start()
        self.islink = mock.patch('os.path.islink', return_value=False).start()
        self.exists = mock.patch('os.path.exists', return_value=False).start()
        self.updates = []
        self.DeleteProcessor = mock.patch('kojihub.kojihub.DeleteProcessor',
                                          side_effect=self.getDelete).start()
        self.deletes = []
        self.get_build = mock.patch('kojihub.kojihub.get_build').start()
        self.list_volumes = mock.patch('kojihub.kojihub.list_volumes').start()
        self.list_volumes.return_value = [{'id': 0, 'name': 'DEFAULT'}]
        self._recycle_lock = mock.patch('kojihub.kojihub._recycle_lock').start()

        # base data
        self.new = self.new_base.copy()
        self.old = self.old_base.copy()
        self._recycle_lock.return_value = self.old

    def tearDown(self):
        mock.patch.stopall()

    def getUpdate(self, *args, **kwargs):
        update = UP(*args, **kwargs)
        update.execute = mock.MagicMock()
        self.updates.append(update)
        return update

    def getQuery(self, *args, **kwargs):
        query = QP(*args, **kwargs)
        query.execute = self.query_execute
        self.queries.append(query)
        return query

    def getDelete(self, *args, **kwargs):
        delete = DP(*args, **kwargs)
        delete.execute = mock.MagicMock()
        self.deletes.append(delete)
        return delete

    # Basic old and new build infos
    old_base = {
           'id': 2,
           'state': 3,
           'task_id': None,
           'epoch': None,
           'name': 'GConf2',
           'nvr': 'GConf2-3.2.6-15.fc23',
           'package_id': 2,
           'package_name': 'GConf2',
           'release': '15.fc23',
           'version': '3.2.6',
           'source': None,
           'extra': None,
           'cg_id': None,
           'volume_id': 0,
           'volume_name': 'DEFAULT'}
    new_base = {
           'state': 3,
           'name': 'GConf2',
           'version': '3.2.6',
           'release': '15.fc23',
           'epoch': None,
           'nvr': 'GConf2-3.2.6-15.fc23',
           'completion_time': '2016-09-16',
           'start_time': '2016-09-16',
           'owner': 2,
           'source': None,
           'extra': None,
           'cg_id': None,
           'volume_id': 0}

    def test_build_already_in_progress(self):
        self.old['state'] = self.new['state'] = koji.BUILD_STATES['BUILDING']
        self.old['task_id'] = 137
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.recycle_build(self.old, self.new)
        self.assertEqual(f"Build already in progress (task {self.old['task_id']})", str(ex.exception))
        self.assertEqual(len(self.queries), 0)
        self.assertEqual(len(self.updates), 0)
        self.assertEqual(len(self.deletes), 0)

        self.get_build.assert_not_called()
        self.run_callbacks.assert_not_called()

    def test_build_already_in_progress_same_task_id(self):
        self.old['state'] = self.new['state'] = koji.BUILD_STATES['BUILDING']
        self.old['task_id'] = self.new['task_id'] = 137
        result = kojihub.recycle_build(self.old, self.new)
        self.assertEqual(result, None)
        self.assertEqual(len(self.queries), 0)
        self.assertEqual(len(self.updates), 0)
        self.assertEqual(len(self.deletes), 0)

        self.get_build.assert_not_called()
        self.run_callbacks.assert_not_called()

    def test_not_in_failed_or_canceled_state(self):
        self.old['state'] = koji.BUILD_STATES['COMPLETE']
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.recycle_build(self.old, self.new)
        self.assertEqual(f"Build already exists (id={self.old['id']}, state=COMPLETE): {self.new}",
                         str(ex.exception))
        self.assertEqual(len(self.queries), 0)
        self.assertEqual(len(self.updates), 0)
        self.assertEqual(len(self.deletes), 0)

        self.get_build.assert_not_called()
        self.run_callbacks.assert_not_called()

    def test_tag_activity_already_exists(self):
        self.old['task_id'] = 137
        self.query_execute.return_value = [{'tag_id': 123}]
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.recycle_build(self.old, self.new)
        self.assertEqual("Build already exists. Unable to recycle, has tag history",
                         str(ex.exception))
        self.assertEqual(len(self.queries), 1)
        self.assertEqual(len(self.updates), 0)
        self.assertEqual(len(self.deletes), 0)

        query = self.queries[0]
        self.assertEqual(query.tables, ['tag_listing'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['tag_id'])

        self.get_build.assert_not_called()
        self.run_callbacks.assert_not_called()

    def test_rpm_activity_already_exists(self):
        self.old['task_id'] = 137
        self.query_execute.side_effect = [[], [{'id': 1}]]
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.recycle_build(self.old, self.new)
        self.assertEqual("Build already exists. Unable to recycle, has rpm data",
                         str(ex.exception))

        self.assertEqual(len(self.queries), 2)
        self.assertEqual(len(self.updates), 0)
        self.assertEqual(len(self.deletes), 0)

        query = self.queries[0]
        self.assertEqual(query.tables, ['tag_listing'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['tag_id'])

        query = self.queries[1]
        self.assertEqual(query.tables, ['rpminfo'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['id'])

        self.get_build.assert_not_called()
        self.run_callbacks.assert_not_called()

    def test_archive_activity_already_exists(self):
        self.old['task_id'] = 137
        self.query_execute.side_effect = [[], [], [{'id': 11}]]
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.recycle_build(self.old, self.new)
        self.assertEqual("Build already exists. Unable to recycle, has archive data",
                         str(ex.exception))

        self.assertEqual(len(self.queries), 3)
        self.assertEqual(len(self.updates), 0)
        self.assertEqual(len(self.deletes), 0)

        query = self.queries[0]
        self.assertEqual(query.tables, ['tag_listing'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['tag_id'])

        query = self.queries[1]
        self.assertEqual(query.tables, ['rpminfo'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['id'])

        query = self.queries[2]
        self.assertEqual(query.tables, ['archiveinfo'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['id'])

        self.get_build.assert_not_called()
        self.run_callbacks.assert_not_called()

    def test_valid(self):
        self.old['task_id'] = self.new['task_id'] = 137
        self.query_execute.side_effect = [[], [], []]
        self.get_build.return_value = {'build_id': 2, 'name': 'GConf2', 'version': '3.2.6',
                                       'release': '15.fc23'}

        kojihub.recycle_build(self.old, self.new)

        self.assertEqual(len(self.queries), 3)
        self.assertEqual(len(self.updates), 1)
        self.assertEqual(len(self.deletes), 4)

        query = self.queries[0]
        self.assertEqual(query.tables, ['tag_listing'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['tag_id'])

        query = self.queries[1]
        self.assertEqual(query.tables, ['rpminfo'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['id'])

        query = self.queries[2]
        self.assertEqual(query.tables, ['archiveinfo'])
        self.assertEqual(query.joins, None)
        self.assertEqual(query.clauses, ['build_id = %(id)s'])
        self.assertEqual(query.values, self.old)
        self.assertEqual(query.columns, ['id'])

        delete = self.deletes[0]
        self.assertEqual(delete.table, 'maven_builds')
        self.assertEqual(delete.clauses, ['build_id = %(id)i'])
        self.assertEqual(delete.values, self.old)

        delete = self.deletes[1]
        self.assertEqual(delete.table, 'win_builds')
        self.assertEqual(delete.clauses, ['build_id = %(id)i'])
        self.assertEqual(delete.values, self.old)

        delete = self.deletes[2]
        self.assertEqual(delete.table, 'image_builds')
        self.assertEqual(delete.clauses, ['build_id = %(id)i'])
        self.assertEqual(delete.values, self.old)

        delete = self.deletes[3]
        self.assertEqual(delete.table, 'build_types')
        self.assertEqual(delete.clauses, ['build_id = %(id)i'])
        self.assertEqual(delete.values, self.old)

        update = self.updates[0]
        self.assertEqual(update.table, 'build')
        self.assertEqual(update.values, self.new)
        for key in ['state', 'task_id', 'owner', 'start_time',
                    'completion_time', 'epoch']:
            assert update.data[key] == self.new[key]
        self.assertEqual(update.rawdata, {'create_event': 'get_event()'})
        self.assertEqual(update.clauses, ['id=%(id)s'])

        self.get_build.assert_called_once_with(self.new['id'], strict=True)
        self.assertEqual(self.run_callbacks.call_count, 2)

        # our default data does not include stray files
        self.rmtree.assert_not_called()
        self.unlink.assert_not_called()

    def test_stray_link(self):
        self.old['task_id'] = self.new['task_id'] = 137
        self.query_execute.side_effect = [[], [], []]
        self.get_build.return_value = {'build_id': 2, 'name': 'GConf2', 'version': '3.2.6',
                                       'release': '15.fc23'}

        self.islink.return_value = True
        kojihub.recycle_build(self.old, self.new)
        self.rmtree.assert_not_called()
        self.unlink.assert_called_once_with('/mnt/koji/packages/GConf2/3.2.6/15.fc23')

    def test_stray_dir(self):
        self.old['task_id'] = self.new['task_id'] = 137
        self.query_execute.side_effect = [[], [], []]
        self.get_build.return_value = {'build_id': 2, 'name': 'GConf2', 'version': '3.2.6',
                                       'release': '15.fc23'}

        self.exists.return_value = True
        kojihub.recycle_build(self.old, self.new)
        self.unlink.assert_not_called()
        self.rmtree.assert_called_once_with('/mnt/koji/packages/GConf2/3.2.6/15.fc23')


class TestRecycleLock(unittest.TestCase):

    def setUp(self):
        self.QP = mock.patch('kojihub.kojihub.QueryProcessor').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_recycle_lock(self):
        old = {'id': 12345}
        self.QP().executeOne.return_value = mock.sentinel.lock
        result = kojihub._recycle_lock(old)

        self.assertEqual(result, mock.sentinel.lock)


# the end
