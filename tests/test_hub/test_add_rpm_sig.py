import base64
from unittest import mock
import os
import unittest

import koji
from kojihub import kojihub

IP = kojihub.InsertProcessor
QP = kojihub.QueryProcessor


DATADIR = os.path.dirname(__file__) + '/data'


class TestAddRPMSigWrapper(unittest.TestCase):
    def setUp(self):
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context.session.assertPerm = mock.MagicMock()
        self.add_rpm_sig = mock.patch('kojihub.kojihub.add_rpm_sig').start()
        self.exports = kojihub.RootExports()

    def tearDown(self):
        mock.patch.stopall()

    def test_wrapper1(self):
        # the wrapper should enforce acl, convert base64, and otherwise pass through the args
        sighdr = b'SIGHEADER 429'
        self.exports.addRPMSig(1, base64.b64encode(sighdr))

        self.context.session.assertPerm.assert_called_once_with('sign')
        self.add_rpm_sig.assert_called_once_with(1, sighdr, sigkey=None)

    def test_wrapper2(self):
        # the wrapper should enforce acl, convert base64, and otherwise pass through the args
        sighdr = b'SIGHEADER 429'
        self.exports.addRPMSig(1, base64.b64encode(sighdr), 'KEY')

        self.context.session.assertPerm.assert_called_once_with('sign')
        self.add_rpm_sig.assert_called_once_with(1, sighdr, sigkey='KEY')


class TestAddRPMSig(unittest.TestCase):
    def getInsert(self, *args, **kwargs):
        insert = IP(*args, **kwargs)
        insert.execute = mock.MagicMock()
        self.inserts.append(insert)
        return insert

    def getQuery(self, *args, **kwargs):
        query = QP(*args, **kwargs)
        query.execute = self.query_execute
        self.queries.append(query)
        return query

    def setUp(self):
        self.InsertProcessor = mock.patch('kojihub.kojihub.InsertProcessor',
                                          side_effect=self.getInsert).start()
        self.inserts = []
        self.QueryProcessor = mock.patch('kojihub.kojihub.QueryProcessor',
                                         side_effect=self.getQuery).start()
        self.queries = []
        self.query_execute = mock.MagicMock()
        self.context = mock.patch('kojihub.kojihub.context').start()
        # It seems MagicMock will not automatically handle attributes that
        # start with "assert"
        self.context.session.assertLogin = mock.MagicMock()
        self.context.opts = {
            'HostPrincipalFormat': '-%s-',
            'MaxNameLengthInternal': 99,
        }
        self.get_rpm = mock.patch('kojihub.kojihub.get_rpm').start()
        self.get_build = mock.patch('kojihub.kojihub.get_build').start()
        self.isdir = mock.patch('os.path.isdir').start()
        self.ensuredir = mock.patch('koji.ensuredir').start()
        self.open = mock.patch('kojihub.kojihub.open').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_add_rpm_sig_header_signed(self):
        """Test addRPMSig with header-only signed RPM"""
        self.query_execute.side_effect = [[]]
        self.isdir.side_effect = [True]
        self.get_rpm.side_effect = [{
            'id': 1,
            'name': 'testpkg',
            'version': '1.0.0',
            'release': '1',
            'arch': 'noarch',
            'epoch': None,
            'payloadhash': '1706d0174aa29a5a3e5c60855a778c35',
            'size': 123,
            'external_repo_id': None,
            'build_id': 1,
        }]
        self.open.side_effect = [mock.MagicMock()]

        rpm_path = DATADIR + '/rpms/header-signed.rpm'
        sighdr = koji.rip_rpm_sighdr(rpm_path)

        kojihub.add_rpm_sig(1, sighdr)
        self.assertEqual(len(self.inserts), 1)
        insert = self.inserts[0]
        self.assertEqual(insert.data['rpm_id'], 1)
        self.assertEqual(insert.data['sigkey'], '15f712be')

    def test_add_rpm_sig_external(self):
        """external rpm failure case"""
        self.get_rpm.side_effect = [{
            'id': 1,
            'name': 'testpkg',
            'version': '1.0.0',
            'release': '1',
            'arch': 'noarch',
            'epoch': None,
            'payloadhash': '1706d0174aa29a5a3e5c60855a778c35',
            'size': 123,
            'external_repo_id': 10,
            'external_repo_name': 'EXTREPO',
            'build_id': 1,
        }]

        sighdr = 'SIG HEADER 99'

        with self.assertRaises(koji.GenericError):
            kojihub.add_rpm_sig(1, sighdr)

        self.assertEqual(len(self.inserts), 0)
        self.open.assert_not_called()
        self.isdir.assert_not_called()

    def test_add_rpm_sig_no_dir(self):
        """missing build dir failure case"""
        sighdr = 'SIG HEADER 99'
        self.isdir.side_effect = [False]
        self.get_rpm.side_effect = [{'build_id': 100, 'external_repo_id': None}]

        with self.assertRaises(koji.GenericError):
            kojihub.add_rpm_sig(1, sighdr)

        self.assertEqual(len(self.inserts), 0)
        self.open.assert_not_called()
        self.isdir.assert_called_once()

    def test_add_rpm_sig_bad_sigkey(self):
        """bad sigkey failure case"""
        sighdr = 'SIG HEADER 99'
        self.isdir.side_effect = [True]
        self.get_rpm.side_effect = [{'build_id': 100, 'external_repo_id': None}]

        with self.assertRaises(koji.GenericError):
            kojihub.add_rpm_sig(1, sighdr, sigkey='foo/bar !')

        self.assertEqual(len(self.inserts), 0)
        self.open.assert_not_called()
        self.isdir.assert_called_once()


class TestScanHeaderOnly(unittest.TestCase):

    def test_scan_sighdr_header_signed(self):
        """Test _scan_sighdr on a header-only signed package"""
        rpm_path = DATADIR + '/rpms/header-signed.rpm'
        sighdr = koji.rip_rpm_sighdr(rpm_path)

        sigmd5, sig = kojihub._scan_sighdr(sighdr, rpm_path)
        self.assertEqual(koji.hex_string(sigmd5), '1706d0174aa29a5a3e5c60855a778c35')
        sigkey = koji.get_sigpacket_key_id(sig)
        self.assertEqual(sigkey, '15f712be')


# the end
