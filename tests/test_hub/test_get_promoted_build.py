import unittest
from unittest import mock

import koji
from kojihub import kojihub


class TestGetPromotedBuild(unittest.TestCase):

    def setUp(self):
        self.get_build = mock.patch('kojihub.kojihub.get_build').start()

    def tearDown(self):
        mock.patch.stopall()

    def mkbuild(self, **kwargs):
        binfo = kwargs
        binfo.setdefault('draft', False)
        binfo.setdefault('id', 100)
        binfo.setdefault('name', 'test-package')
        binfo.setdefault('version', '10.0.1')
        if 'release' not in binfo:
            rel = '1.fc99'
            if binfo['draft']:
                rel += f',draft_{binfo["id"]}'
            binfo['release'] = rel
        binfo.setdefault('nvr', 'NVR')
        binfo.setdefault('epoch', None)
        return binfo

    def test_is_promoted(self):
        binfo1 = self.mkbuild(draft=True)
        binfo2 = self.mkbuild(draft=False, id=101)
        self.get_build.side_effect = [binfo1, binfo2]

        result = kojihub.get_promoted_build(binfo1['id'])

        self.assertEqual(result, binfo2)

    def test_not_promoted(self):
        binfo = self.mkbuild(draft=True)
        self.get_build.side_effect = [binfo, None]

        result = kojihub.get_promoted_build(binfo['id'])

        self.assertEqual(result, None)

    def test_not_draft(self):
        binfo = self.mkbuild(draft=False)
        self.get_build.side_effect = [binfo]

        result = kojihub.get_promoted_build(binfo['id'])

        self.assertEqual(result, None)

    def test_bad_release(self):
        binfo = self.mkbuild(draft=True, release='BAD')

        # no error with safe=True
        self.get_build.side_effect = [binfo]
        result = kojihub.get_promoted_build(binfo['id'], safe=True)
        self.assertEqual(result, None)

        # otherwise error
        self.get_build.side_effect = [binfo]
        with self.assertRaises(koji.GenericError):
            kojihub.get_promoted_build(binfo['id'], safe=False)

    def test_bad_promotion(self):
        # not a case that should be possible
        binfo1 = self.mkbuild(draft=True)
        binfo2 = self.mkbuild(draft=False, id=101)
        binfo2['draft'] = True

        # no error with safe=True
        self.get_build.side_effect = [binfo1, binfo2]
        result = kojihub.get_promoted_build(binfo1['id'], safe=True)
        self.assertEqual(result, None)

        # otherwise error
        self.get_build.side_effect = [binfo1, binfo2]
        with self.assertRaises(koji.GenericError):
            kojihub.get_promoted_build(binfo1['id'], safe=False)


# the end
