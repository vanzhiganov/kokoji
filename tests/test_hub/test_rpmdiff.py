import copy
from unittest import mock
import os
import unittest

import koji
from kojihub import kojihub


class TestRPMDiff(unittest.TestCase):

    @mock.patch('koji.rpmdiff.Rpmdiff')
    def test_rpmdiff_empty_invocation(self, Rpmdiff):
        kojihub.rpmdiff('basepath', [], hashes={})
        Rpmdiff.assert_not_called()
        kojihub.rpmdiff('basepath', ['tasks/12/1234/foo'], hashes={})
        Rpmdiff.assert_not_called()

    @mock.patch('koji.rpmdiff.Rpmdiff')
    def test_rpmdiff_simple_success(self, Rpmdiff):
        d = mock.MagicMock()
        d.differs.return_value = False
        Rpmdiff.return_value = d
        self.assertFalse(kojihub.rpmdiff('basepath',
                                         ['tasks/12/1234/foo', 'tasks/23/2345/bar'], hashes={}))
        Rpmdiff.assert_called_once_with(
            'basepath/tasks/12/1234/foo', 'basepath/tasks/23/2345/bar', ignore='S5TN')

    @mock.patch('koji.rpmdiff.Rpmdiff')
    def test_rpmdiff_simple_failure(self, Rpmdiff):
        d = mock.MagicMock()
        d.differs.return_value = True
        Rpmdiff.return_value = d
        with self.assertRaises(koji.BuildError):
            kojihub.rpmdiff('basepath', ['tasks/12/1234/foo', 'tasks/13/1345/bar'], hashes={})
        Rpmdiff.assert_called_once_with(
            'basepath/tasks/12/1234/foo', 'basepath/tasks/13/1345/bar', ignore='S5TN')
        d.textdiff.assert_called_once_with()

    def test_rpmdiff_real_target(self):
        data_path = os.path.abspath("tests/test_hub/data/rpms")

        # the only differences between rpm1 and rpm2 are 1) create time 2) file name
        rpm1 = os.path.join(data_path, 'test-pkg-1.0.0-1.el7.noarch.rpm')
        rpm2 = os.path.join(data_path, 'test-pkg-1.0.0-1.fc24.noarch.rpm')

        diff_output = "..........T /usr/share/test-pkg/test-doc01.txt\n" + \
                      "..........T /usr/share/test-pkg/test-doc02.txt\n" + \
                      "..........T /usr/share/test-pkg/test-doc03.txt\n" + \
                      "..........T /usr/share/test-pkg/test-doc04.txt"

        # case 1. no ignore option, timestamp is different
        # perform twice check to verify issue: #994
        for _ in range(0, 2):
            d = koji.rpmdiff.Rpmdiff(rpm1, rpm2)
            self.assertEqual(d.textdiff(), diff_output)

        # case 2. ignore timestamp, two rpms should be the same
        # perform twice check to verify issue: #994
        for r in range(0, 2):
            d = koji.rpmdiff.Rpmdiff(rpm1, rpm2, ignore='S5TN')
            self.assertEqual(d.textdiff(), '')

    def test_rpmdiff_size(self):
        data_path = os.path.abspath("tests/test_hub/data/rpms")

        # the only differences between rpm1 and rpm2 are 1) create time 2) file name
        rpm1 = os.path.join(data_path, 'different_size_a.noarch.rpm')
        rpm2 = os.path.join(data_path, 'different_size_b.noarch.rpm')

        diff_output = "S.5.......T /bin/test"

        # case 1. no ignore option, timestamp is different
        # perform twice check to verify issue: #994
        for _ in range(0, 2):
            d = koji.rpmdiff.Rpmdiff(rpm1, rpm2)
            self.assertEqual(d.textdiff(), diff_output)

        # case 2. ignore timestamp, two rpms should be the same
        # perform twice check to verify issue: #994
        for r in range(0, 2):
            d = koji.rpmdiff.Rpmdiff(rpm1, rpm2, ignore='S5TN')
            self.assertEqual(d.textdiff(), '')

    def test_rpmdiff_kojihash(self):
        data_path = os.path.abspath("tests/test_hub/data/rpms")

        # the only differences between rpm1 and rpm2 are 1) create time 2) file name
        rpm1 = os.path.join(data_path, 'different_size_a.noarch.rpm')
        rpm2 = os.path.join(data_path, 'different_size_b.noarch.rpm')

        hash1 = '38e6838cfc14ae00265b0134ebb2e9c31f014b3e96b044173787e773e91c86bf'
        hash2 = '8d55616a6ca4c270f9adf76eba0a352c26c6c91d016735d2f5a3b880ad21a0ed'
        for _ in range(2):
            # double check that kojihash is deterministic
            d = koji.rpmdiff.Rpmdiff(rpm1, rpm2)
            self.assertEqual(d.kojihash(), hash1)
            self.assertEqual(d.kojihash(new=True), hash2)

    def test_rpmdiff_ignore_test(self):
        data_path = os.path.abspath("tests/test_hub/data/rpms")

        # a template file for parsing rpm header
        rpm = os.path.join(data_path, 'test-pkg-1.0.0-1.el7.noarch.rpm')

        # dummy file info
        defattr = [19, 33188, 1531970408, 0, 0, 2, 1, -1, -1, 'root', 'root', '02d2c91b']

        rpm_dict_old = {'a_file': defattr}

        def check_diff_result(opt, idx, value, textdiff):
            orig_init = koji.rpmdiff.Rpmdiff.__init__

            def init_mock(*args, **kwargs):
                # need to init rpm_dict every time
                attr = defattr[:]
                attr[idx] = value
                rpm_dict_new = {'a_file': attr}

                args[0]._getFilesDict = mock.MagicMock()
                args[0]._getFilesDict.side_effect = [rpm_dict_old, rpm_dict_new]
                orig_init(*args, **kwargs)

            # compare with every option
            with mock.patch('koji.rpmdiff.Rpmdiff.__init__', new=init_mock):
                for token in 'SM5DNLVUGFT':
                    diff = koji.rpmdiff.Rpmdiff(rpm, rpm, ignore=token)
                    self.assertEqual(diff.textdiff(), textdiff if token not in opt else '')

        # case 1 size diffrerent
        check_diff_result('S', 0, 99, "S.......... a_file")

        # case 2 mode different
        check_diff_result('M', 1, 22188, ".M......... a_file")

        # case 3 time different
        check_diff_result('T', 2, 1531976666, "..........T a_file")

        # case 4 flag different
        check_diff_result('F', 3, 3, ".........F. a_file")

        # case 5 device different
        check_diff_result('D', 4, 4, "...D....... a_file")

        # case 6 inode different
        check_diff_result('N', 5, 5, "....N...... a_file")

        # case 7 number of links different
        check_diff_result('L', 6, 6, ".....L..... a_file")

        # case 8 vflag different
        check_diff_result('V', 8, 8, "......V.... a_file")

        # case 9 user different
        check_diff_result('U', 9, 'tester', ".......U... a_file")

        # case 10 group different
        check_diff_result('G', 10, 'tester', "........G.. a_file")

        # case 11 checksum different
        check_diff_result('5', 11, 'aabbccdd', "..5........ a_file")


class TestCheckNoarchRpms(unittest.TestCase):
    @mock.patch('kojihub.kojihub.rpmdiff')
    def test_check_noarch_rpms_empty_invocation(self, rpmdiff):
        originals = ['foo', 'bar']
        result = kojihub.check_noarch_rpms('basepath', copy.copy(originals))
        self.assertEqual(result, originals)

    @mock.patch('kojihub.kojihub.rpmdiff')
    def test_check_noarch_rpms_simple_invocation(self, rpmdiff):
        originals = ['tasks/12/1234/foo.noarch.rpm', 'tasks/23/2345/foo.noarch.rpm']
        result = kojihub.check_noarch_rpms('basepath', copy.copy(originals))
        self.assertEqual(result, originals[0:1])
        self.assertEqual(len(rpmdiff.mock_calls), 1)

    @mock.patch('kojihub.kojihub.rpmdiff')
    def test_check_noarch_rpms_with_duplicates(self, rpmdiff):
        originals = [
            'tasks/34/1234/bar.noarch.rpm',
            'tasks/45/2345/bar.noarch.rpm',
            'tasks/55/5555/bar.noarch.rpm',
        ]
        result = kojihub.check_noarch_rpms('basepath', copy.copy(originals))
        # pick the first one
        self.assertEqual(result, ['tasks/34/1234/bar.noarch.rpm'])
        rpmdiff.assert_called_once_with('basepath', originals, hashes={})

    @mock.patch('kojihub.kojihub.rpmdiff')
    def test_check_noarch_rpms_with_mixed(self, rpmdiff):
        originals = [
            'tasks/34/1234/foo.x86_64.rpm',
            'tasks/34/2234/bar.x86_64.rpm',
            'tasks/12/1212/bar.noarch.rpm',
            'tasks/23/2323/bar.noarch.rpm',
        ]
        result = kojihub.check_noarch_rpms('basepath', copy.copy(originals))
        self.assertEqual(result, [
            'tasks/34/1234/foo.x86_64.rpm',
            'tasks/34/2234/bar.x86_64.rpm',
            'tasks/12/1212/bar.noarch.rpm'
        ])
        rpmdiff.assert_called_once_with(
            'basepath',
            ['tasks/12/1212/bar.noarch.rpm', 'tasks/23/2323/bar.noarch.rpm'],
            hashes={}
        )


class TestRPMDiffHub(unittest.TestCase):
    @mock.patch('koji.rpmdiff.Rpmdiff')
    def test_rpmdiff_differing_hashes_fails(self, Rpmdiff):
        """When different archs have different pre-computed hashes, task must fail."""
        d = mock.MagicMock()
        d.textdiff.return_value = 'mock diff'
        Rpmdiff.return_value = d
        # Paths: tasks/2345/12345/pkg.noarch.rpm and tasks/6789/56789/pkg.noarch.rpm
        rpmlist = ['tasks/2345/12345/pkg.noarch.rpm', 'tasks/6789/56789/pkg.noarch.rpm']
        hashes = {
            12345: {'pkg.noarch.rpm': 'hash_from_arch1'},
            56789: {'pkg.noarch.rpm': 'hash_from_arch2'},
        }
        with self.assertRaises(koji.BuildError) as cm:
            kojihub.rpmdiff('basepath', rpmlist, hashes=hashes)
        self.assertIn('built differently on different architectures', str(cm.exception))
        Rpmdiff.assert_called_once_with(
            'basepath/tasks/2345/12345/pkg.noarch.rpm',
            'basepath/tasks/6789/56789/pkg.noarch.rpm',
            ignore='S5TN')

    @mock.patch('koji.rpmdiff.Rpmdiff')
    def test_rpmdiff_same_hash_skips(self, Rpmdiff):
        """When pre-computed hashes are equal, skip Rpmdiff (optimization)."""
        rpmlist = ['tasks/2345/12345/pkg.noarch.rpm', 'tasks/6789/56789/pkg.noarch.rpm']
        hashes = {
            "12345": {'pkg.noarch.rpm': "same_hash"},
            "56789": {'pkg.noarch.rpm': "same_hash"},
        }
        kojihub.rpmdiff('basepath', rpmlist, hashes=hashes)
        Rpmdiff.assert_not_called()


class TestRealBuild(unittest.TestCase):
    # https://kojihub.stream.rdu2.redhat.com/koji/taskinfo?taskID=6138158

    @mock.patch('koji.rpmdiff.Rpmdiff')
    @mock.patch('koji.load_json')
    def test_real_build(self, load_json, rpmdiff):
        # workdir /volume/work
        # taskrelpath = tasks/34/1234
        uploadpath = '/mnt/koji/work'
        results = {
            6138160: {
                "rpms": [
                    "tasks/8160/6138160/golang-src-1.25.3-7.el10.noarch.rpm",
                    "tasks/8160/6138160/golang-tests-1.25.3-7.el10.noarch.rpm",
                    "tasks/8160/6138160/go-toolset-1.25.3-7.el10.aarch64.rpm",
                    "tasks/8160/6138160/golang-bin-1.25.3-7.el10.aarch64.rpm",
                    "tasks/8160/6138160/golang-1.25.3-7.el10.aarch64.rpm",
                    "tasks/8160/6138160/golang-race-1.25.3-7.el10.aarch64.rpm",
                    "tasks/8160/6138160/golang-docs-1.25.3-7.el10.noarch.rpm",
                    "tasks/8160/6138160/golang-misc-1.25.3-7.el10.noarch.rpm"
                ],
                "srpms": [
                    "tasks/8160/6138160/golang-1.25.3-7.el10.src.rpm"
                ],
                "logs": [
                    "tasks/8160/6138160/state.log",
                    "tasks/8160/6138160/build.log",
                    "tasks/8160/6138160/root.log",
                    "tasks/8160/6138160/dnf.librepo.log",
                    "tasks/8160/6138160/hw_info.log",
                    "tasks/8160/6138160/dnf.log",
                    "tasks/8160/6138160/dnf.rpm.log",
                    "tasks/8160/6138160/installed_pkgs.log",
                    "tasks/8160/6138160/mock_output.log",
                    "tasks/8160/6138160/mock_config.log",
                    "tasks/8160/6138160/noarch_rpmdiff.json"
                ],
                "brootid": 771895
            },
            6138161: {
                "rpms": [
                    "tasks/8161/6138161/golang-docs-1.25.3-7.el10.noarch.rpm",
                    "tasks/8161/6138161/go-toolset-1.25.3-7.el10.ppc64le.rpm",
                    "tasks/8161/6138161/golang-race-1.25.3-7.el10.ppc64le.rpm",
                    "tasks/8161/6138161/golang-bin-1.25.3-7.el10.ppc64le.rpm",
                    "tasks/8161/6138161/golang-tests-1.25.3-7.el10.noarch.rpm",
                    "tasks/8161/6138161/golang-src-1.25.3-7.el10.noarch.rpm",
                    "tasks/8161/6138161/golang-1.25.3-7.el10.ppc64le.rpm",
                    "tasks/8161/6138161/golang-misc-1.25.3-7.el10.noarch.rpm"
                ],
                "srpms": [],
                "logs": [
                    "tasks/8161/6138161/mock_config.log",
                    "tasks/8161/6138161/mock_output.log",
                    "tasks/8161/6138161/build.log",
                    "tasks/8161/6138161/installed_pkgs.log",
                    "tasks/8161/6138161/hw_info.log",
                    "tasks/8161/6138161/root.log",
                    "tasks/8161/6138161/dnf.log",
                    "tasks/8161/6138161/dnf.rpm.log",
                    "tasks/8161/6138161/state.log",
                    "tasks/8161/6138161/dnf.librepo.log",
                    "tasks/8161/6138161/noarch_rpmdiff.json"
                ],
                "brootid": 771896
            },
            6138162: {
                "rpms": [
                    "tasks/8162/6138162/golang-bin-1.25.3-7.el10.s390x.rpm",
                    "tasks/8162/6138162/go-toolset-1.25.3-7.el10.s390x.rpm",
                    "tasks/8162/6138162/golang-tests-1.25.3-7.el10.noarch.rpm",
                    "tasks/8162/6138162/golang-1.25.3-7.el10.s390x.rpm",
                    "tasks/8162/6138162/golang-race-1.25.3-7.el10.s390x.rpm",
                    "tasks/8162/6138162/golang-src-1.25.3-7.el10.noarch.rpm",
                    "tasks/8162/6138162/golang-docs-1.25.3-7.el10.noarch.rpm",
                    "tasks/8162/6138162/golang-misc-1.25.3-7.el10.noarch.rpm"
                ],
                "srpms": [],
                "logs": [
                    "tasks/8162/6138162/mock_output.log",
                    "tasks/8162/6138162/dnf.librepo.log",
                    "tasks/8162/6138162/installed_pkgs.log",
                    "tasks/8162/6138162/mock_config.log",
                    "tasks/8162/6138162/hw_info.log",
                    "tasks/8162/6138162/dnf.log",
                    "tasks/8162/6138162/dnf.rpm.log",
                    "tasks/8162/6138162/state.log",
                    "tasks/8162/6138162/build.log",
                    "tasks/8162/6138162/root.log",
                    "tasks/8162/6138162/noarch_rpmdiff.json"
                ],
                "brootid": 771893
            },
            6138163: {
                "rpms": [
                    "tasks/8163/6138163/golang-src-1.25.3-7.el10.noarch.rpm",
                    "tasks/8163/6138163/golang-race-1.25.3-7.el10.x86_64.rpm",
                    "tasks/8163/6138163/golang-bin-1.25.3-7.el10.x86_64.rpm",
                    "tasks/8163/6138163/golang-docs-1.25.3-7.el10.noarch.rpm",
                    "tasks/8163/6138163/go-toolset-1.25.3-7.el10.x86_64.rpm",
                    "tasks/8163/6138163/golang-misc-1.25.3-7.el10.noarch.rpm",
                    "tasks/8163/6138163/golang-tests-1.25.3-7.el10.noarch.rpm",
                    "tasks/8163/6138163/golang-1.25.3-7.el10.x86_64.rpm"
                ],
                "srpms": [],
                "logs": [
                    "tasks/8163/6138163/dnf.log",
                    "tasks/8163/6138163/dnf.rpm.log",
                    "tasks/8163/6138163/state.log",
                    "tasks/8163/6138163/hw_info.log",
                    "tasks/8163/6138163/installed_pkgs.log",
                    "tasks/8163/6138163/build.log",
                    "tasks/8163/6138163/mock_output.log",
                    "tasks/8163/6138163/dnf.librepo.log",
                    "tasks/8163/6138163/mock_config.log",
                    "tasks/8163/6138163/root.log",
                    "tasks/8163/6138163/noarch_rpmdiff.json"
                ],
                "brootid": 771894
            }
        }
        logs = {
            'aarch64': [
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/state.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/build.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/root.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/dnf.librepo.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/hw_info.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/dnf.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/dnf.rpm.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/installed_pkgs.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/mock_output.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/mock_config.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/aarch64/noarch_rpmdiff.json",
            ],
            'ppc64le': [
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/mock_config.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/mock_output.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/build.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/installed_pkgs.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/hw_info.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/root.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/dnf.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/dnf.rpm.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/state.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/dnf.librepo.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/ppc64le/noarch_rpmdiff.json",
            ],
            's390x': [
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/mock_output.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/dnf.librepo.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/installed_pkgs.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/mock_config.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/hw_info.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/dnf.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/dnf.rpm.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/state.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/build.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/root.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/s390x/noarch_rpmdiff.json",
            ],
            'x86_64': [
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/dnf.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/dnf.rpm.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/state.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/hw_info.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/installed_pkgs.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/build.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/mock_output.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/dnf.librepo.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/mock_config.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/root.log",
                "vol/koji02/packages/golang/1.25.3/7.el10,draft_93372/data/logs/x86_64/noarch_rpmdiff.json",
            ]
        }

        hashes = {
            "6138160": {
                "golang-docs-1.25.3-7.el10.noarch.rpm": "9f7fe1181c2fe2aaf5341df4aae68008b53947fdf26fed09244849a5a3c64dd5",
                "golang-misc-1.25.3-7.el10.noarch.rpm": "b1d80aef9a7705af366c2b2a3178d8fac6dabc8b3569f1b9b65ccf719f903dbb",
                "golang-src-1.25.3-7.el10.noarch.rpm": "1ed89a428dfbbd4f32e2782bb2b2d51f7aa2ff1950c82fc97d53b591b4ae8d52",
                "golang-tests-1.25.3-7.el10.noarch.rpm": "11ca9a335851cf0ff197bb2f586de03617c30569497b196ec39c0a866f6629b3"
            },
            "6138161": {
                "golang-docs-1.25.3-7.el10.noarch.rpm": "9f7fe1181c2fe2aaf5341df4aae68008b53947fdf26fed09244849a5a3c64dd5",
                "golang-misc-1.25.3-7.el10.noarch.rpm": "b1d80aef9a7705af366c2b2a3178d8fac6dabc8b3569f1b9b65ccf719f903dbb",
                "golang-src-1.25.3-7.el10.noarch.rpm": "1ed89a428dfbbd4f32e2782bb2b2d51f7aa2ff1950c82fc97d53b591b4ae8d52",
                "golang-tests-1.25.3-7.el10.noarch.rpm": "11ca9a335851cf0ff197bb2f586de03617c30569497b196ec39c0a866f6629b3"
            },
            "6138162": {
                "golang-docs-1.25.3-7.el10.noarch.rpm": "9f7fe1181c2fe2aaf5341df4aae68008b53947fdf26fed09244849a5a3c64dd5",
                "golang-misc-1.25.3-7.el10.noarch.rpm": "b1d80aef9a7705af366c2b2a3178d8fac6dabc8b3569f1b9b65ccf719f903dbb",
                "golang-src-1.25.3-7.el10.noarch.rpm": "1ed89a428dfbbd4f32e2782bb2b2d51f7aa2ff1950c82fc97d53b591b4ae8d52",
                "golang-tests-1.25.3-7.el10.noarch.rpm": "11ca9a335851cf0ff197bb2f586de03617c30569497b196ec39c0a866f6629b3"
            },
            "6138163": {  # x86_64 differs
                "golang-docs-1.25.3-7.el10.noarch.rpm": "9f7fe1181c2fe2aaf5341df4aae68008b53947fdf26fed09244849a5a3c64dd5",
                "golang-misc-1.25.3-7.el10.noarch.rpm": "b1d80aef9a7705af366c2b2a3178d8fac6dabc8b3569f1b9b65ccf719f903dbb",
                "golang-src-1.25.3-7.el10.noarch.rpm": "0f0e890f6128e9159e6409390915bd2f1d4c1917eda722c8ea2fc066a85718de",
                "golang-tests-1.25.3-7.el10.noarch.rpm": "11ca9a335851cf0ff197bb2f586de03617c30569497b196ec39c0a866f6629b3"
            },
        }

        rpms = []
        for x in results.values():
            for y in x['rpms']:
                rpms.append(y)

        load_json.side_effect = [
            {'6138160': hashes['6138160']},
            {'6138161': hashes['6138161']},
            {'6138162': hashes['6138162']},
            {'6138163': hashes['6138163']},
        ]


        # first two diffs (60/61, 60/62) hits the hash architectures
        # third differs (because of inode changes), so rpmdiff is called 6138163
        # Anyway, in this case rpms are valid
        diff_same = mock.MagicMock(name="diff_same")
        diff_same.differs.return_value = False

        rpmdiff.return_value = diff_same

        # should pass without exceptions
        kojihub.check_noarch_rpms(uploadpath, rpms, logs=logs)

        # called just one for non-matching hashes
        rpmdiff.assert_called_once_with(
            '/mnt/koji/work/tasks/8160/6138160/golang-src-1.25.3-7.el10.noarch.rpm',
            '/mnt/koji/work/tasks/8163/6138163/golang-src-1.25.3-7.el10.noarch.rpm',
            ignore='S5TN'
        )
        self.assertEqual(diff_same.differs.call_count, 1)
