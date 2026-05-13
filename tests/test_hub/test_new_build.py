from unittest import mock
import unittest

import koji
from kojihub import kojihub

IP = kojihub.InsertProcessor


class TestNewBuild(unittest.TestCase):
    def setUp(self):
        self.get_rpm = mock.patch("kojihub.kojihub.get_rpm").start()
        self.get_external_repo_id = mock.patch(
            "kojihub.kojihub.get_external_repo_id"
        ).start()
        self.nextval = mock.patch("kojihub.kojihub.nextval").start()
        self.Savepoint = mock.patch("kojihub.kojihub.Savepoint").start()
        self.InsertProcessor = mock.patch(
            "kojihub.kojihub.InsertProcessor", side_effect=self.getInsert
        ).start()
        self.inserts = []
        self.insert_execute = mock.MagicMock()
        self.lookup_package = mock.patch("kojihub.kojihub.lookup_package").start()
        self.new_package = mock.patch("kojihub.kojihub.new_package").start()
        self.get_user = mock.patch("kojihub.kojihub.get_user").start()
        self.get_build = mock.patch("kojihub.kojihub.get_build").start()
        self.recycle_build = mock.patch("kojihub.kojihub.recycle_build").start()
        self.context = mock.patch("kojihub.kojihub.context").start()
        self.find_build_id = mock.patch("kojihub.kojihub.find_build_id").start()
        self.get_old_draft_build = mock.patch("kojihub.kojihub._get_old_draft_build").start()

    def tearDown(self):
        mock.patch.stopall()

    def getInsert(self, *args, **kwargs):
        insert = IP(*args, **kwargs)
        insert.execute = self.insert_execute
        self.inserts.append(insert)
        return insert

    def test_valid(self):
        self.get_build.return_value = None
        self.nextval.return_value = 65  # free build id
        self.new_package.return_value = 54
        self.get_user.return_value = {"id": 123}
        data = {
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "owner": "test_owner",
            "extra": {"extra_key": "extra_value"},
        }

        kojihub.new_build(data)

        self.assertEqual(len(self.inserts), 1)
        insert = self.inserts[0]
        self.assertEqual(insert.table, "build")
        self.assertEqual(
            insert.data,
            {
                "completion_time": "NOW",
                "epoch": "test_epoch",
                "extra": '{"extra_key": "extra_value"}',
                "id": 65,
                "owner": 123,
                "pkg_id": 54,
                "release": "test_release",
                "source": None,
                "start_time": "NOW",
                "state": 1,
                "task_id": None,
                "draft": False,
                "version": "test_version",
                "volume_id": 0,
            },
        )

    def test_empty_data(self):
        with self.assertRaises(koji.GenericError):
            kojihub.new_build({})
        self.assertEqual(len(self.inserts), 0)

    def test_wrong_pkg_id(self):
        self.lookup_package.side_effect = koji.GenericError
        data = {
            "pkg_id": 444,
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "owner": "test_owner",
            "extra": {"extra_key": "extra_value"},
        }

        with self.assertRaises(koji.GenericError):
            kojihub.new_build(data)

        self.assertEqual(len(self.inserts), 0)

    def test_missing_pkg_id_name(self):
        data = {
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "owner": "test_owner",
            "extra": {"extra_key": "extra_value"},
        }

        with self.assertRaises(koji.GenericError) as cm:
            kojihub.new_build(data)

        self.assertEqual(len(self.inserts), 0)
        self.assertEqual("No name or package id provided for build", str(cm.exception))

    def test_wrong_owner(self):
        self.get_user.side_effect = koji.GenericError
        data = {
            "owner": 123456,
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "extra": {"extra_key": "extra_value"},
        }

        with self.assertRaises(koji.GenericError):
            kojihub.new_build(data)

        self.assertEqual(len(self.inserts), 0)

    def test_missing_vre(self):
        data = {
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
        }

        for item in ("version", "release", "epoch"):
            d = data.copy()
            del d[item]
            with self.assertRaises(koji.GenericError):
                kojihub.new_build(d)

        self.assertEqual(len(self.inserts), 0)

    def test_wrong_extra(self):
        # extra dict contains unserializable data
        class CantDoJSON(object):
            pass

        data = {
            "owner": 123456,
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "extra": {"extra_key": CantDoJSON()},
        }

        with self.assertRaises(koji.GenericError) as cm:
            kojihub.new_build(data)

        self.assertEqual(len(self.inserts), 0)
        self.assertEqual(
            "No such build extra data: %(extra)r" % data, str(cm.exception)
        )

    def test_draft(self):
        data = {
            "owner": 123456,
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "draft": True,
        }
        insert_data = {
            "completion_time": "NOW",
            "epoch": "test_epoch",
            "id": 108,
            "extra": None,
            "owner": 123,
            "pkg_id": 54,
            "release": "test_release,draft_108",
            "source": None,
            "start_time": "NOW",
            "state": 1,
            "task_id": None,
            "draft": True,
            "version": "test_version",
            "volume_id": 0,
        }
        self.nextval.return_value = 108
        self.new_package.return_value = 54
        self.get_user.return_value = {"id": 123}
        self.get_build.side_effect = [None, mock.ANY]
        self.find_build_id.return_value = None
        self.get_old_draft_build.return_value = None

        kojihub.new_build(data)

        self.assertEqual(len(self.inserts), 1)
        insert = self.inserts[0]
        self.assertEqual(insert.table, "build")
        self.assertEqual(insert.data, insert_data)
        self.get_build.assert_has_calls(
            [
                mock.call(
                    # it looks like a "draft build" because we use the "data" reference
                    {
                        "owner": 123,
                        "name": "test_name",
                        "version": "test_version",
                        "release": "test_release,draft_108",
                        "epoch": "test_epoch",
                        "draft": True,
                        "pkg_id": 54,
                        "extra": None,
                        "state": 1,
                        "start_time": "NOW",
                        "completion_time": "NOW",
                        "source": None,
                        "task_id": None,
                        "volume_id": 0,
                        "id": 108,
                    }
                ),
                mock.call(108, strict=True),
            ]
        )
        self.find_build_id.assert_called_once_with(
            {
                "name": "test_name",
                "version": "test_version",
                "release": "test_release,draft_108",
            }
        )

    def test_draft_exists(self):
        data = {
            "owner": 123456,
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "draft": True,
        }
        self.new_package.return_value = 54
        self.get_user.return_value = {"id": 123}
        self.get_build.side_effect = [None, mock.ANY]
        self.find_build_id.return_value = 101010
        self.get_old_draft_build.return_value = None
        self.nextval.return_value = 108

        with self.assertRaises(koji.GenericError) as ex:
            kojihub.new_build(data)

        assert str(ex.exception).startswith('The build already exists')
        self.assertEqual(len(self.inserts), 0)
        self.find_build_id.assert_called_once_with(
            {
                "name": "test_name",
                "version": "test_version",
                "release": "test_release,draft_108",
            }
        )

    def test_recycle(self):
        self.get_build.return_value = {'id': 456, 'nvr': 'N-V-R'}
        self.get_user.return_value = {"id": 123}
        data = {
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "owner": "test_owner",
            "extra": {"extra_key": "extra_value"},
        }

        # shouldn't recycle if strict is True
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.new_build(data, strict=True)
        assert str(ex.exception).startswith('Existing build found')
        self.assertEqual(len(self.inserts), 0)

        # but should work if not
        result = kojihub.new_build(data)  # strict is off by default
        self.assertEqual(len(self.inserts), 0)
        self.assertEqual(result, 456)

    def test_recycle_draft(self):
        self.get_user.return_value = {"id": 123}
        data = {
            "name": "test_name",
            "version": "test_version",
            "release": "test_release",
            "epoch": "test_epoch",
            "owner": "test_owner",
            "draft": True,
            "extra": {"extra_key": "extra_value"},
        }

        # shouldn't recycle if non-draft build exists
        self.get_build.return_value = {'id': 456, 'nvr': 'N-V-R'}
        with self.assertRaises(koji.GenericError) as ex:
            kojihub.new_build(data, strict=True)
        assert str(ex.exception).startswith('Target build already exists')
        self.recycle_build.assert_not_called()
        self.assertEqual(len(self.inserts), 0)

        # but should work if not
        self.get_build.return_value = None
        self.get_old_draft_build.return_value = {'id': 455, 'nvr': 'N-V-R,draft_455'}
        result = kojihub.new_build(data)
        self.assertEqual(len(self.inserts), 0)
        self.recycle_build.assert_called_once()
        self.assertEqual(result, 455)


class TestGetOldDraft(unittest.TestCase):

    def setUp(self):
        self.QueryProcessor = mock.patch("kojihub.kojihub.QueryProcessor").start()
        self.get_build = mock.patch("kojihub.kojihub.get_build").start()

    def tearDown(self):
        mock.patch.stopall()

    def test_query_skipped(self):
        # cases where the function doesn't even query

        # not a draft
        data = {'draft': False, 'task_id': 1234, 'state': koji.BUILD_STATES['BUILDING']}
        result = kojihub._get_old_draft_build(data)
        self.assertEqual(result, None)

        # no task id
        data = {'draft': True, 'task_id': None, 'state': koji.BUILD_STATES['BUILDING']}
        result = kojihub._get_old_draft_build(data)
        self.assertEqual(result, None)

        # wrong state
        data = {'draft': True, 'task_id': 1234, 'state': koji.BUILD_STATES['COMPLETE']}
        result = kojihub._get_old_draft_build(data)
        self.assertEqual(result, None)

        # none of these should have resulted in a query
        self.QueryProcessor.assert_not_called()

    def test_no_match(self):
        # the function queries and gets no match

        data = {
            'name': 'foo', 'version': '1.2', 'release': '55',
            'draft': True, 'task_id': 1234, 'state': koji.BUILD_STATES['BUILDING']}
        self.QueryProcessor.return_value.execute.return_value = []  # no match
        result = kojihub._get_old_draft_build(data)
        self.assertEqual(result, None)

    def test_match(self):
        # the function queries and gets no match

        data = {
            'name': 'foo', 'version': '1.2', 'release': '55',
            'draft': True, 'task_id': 1234, 'state': koji.BUILD_STATES['BUILDING']}
        row = {'build.id': 5678}
        self.QueryProcessor.return_value.execute.return_value = [row]
        self.get_build.return_value = mock.sentinel.binfo
        result = kojihub._get_old_draft_build(data)
        self.assertEqual(result, mock.sentinel.binfo)
        self.get_build.assert_called_with(5678)


# the end
