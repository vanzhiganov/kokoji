from unittest import mock
import shutil
import tempfile
import unittest
from collections import namedtuple

import koji.rpmdiff
import rpm
import six


"""
These tests exercise the rpmdiff class in the library, They are different from
similarly named hub tests that are focused mainly on the hub code.
"""


class TestRPMDiff(unittest.TestCase):

    def setUp(self):
        # mock the places in the class that read the rpm data
        self.load_pkg = mock.patch.object(koji.rpmdiff.Rpmdiff, '_load_pkg').start()
        self.getFilesDict = mock.patch.object(koji.rpmdiff.Rpmdiff, '_getFilesDict').start()

        # with the mocks, we shouldn't have file access, but we use temp paths just in case
        self.tempdir = tempfile.mkdtemp()
        self.oldfile = self.tempdir + '/old.rpm'
        self.newfile = self.tempdir + '/new.rpm'

        # simple default data
        self.oldhdr = make_fake_header()
        self.newhdr = make_fake_header()  # should be identical
        self.load_pkg.side_effect = [self.oldhdr, self.newhdr]
        self.oldfiles = make_fake_files(3)
        self.newfiles = make_fake_files(3)  # should be identical
        self.getFilesDict.side_effect = [self.oldfiles, self.newfiles]

    def tearDown(self):
        mock.patch.stopall()
        shutil.rmtree(self.tempdir)

    def test_rpmdiff_simple(self):
        # our baseline mock setup has identical files
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertFalse(d.differs())
        self.assertEqual(d.textdiff(), "")
        self.assertEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_changed_tag(self):
        self.newhdr[rpm.RPMTAG_NAME] = 'different'
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        self.assertEqual(d.textdiff(), 'S.5........ NAME')
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_dropped_tag(self):
        self.newhdr[rpm.RPMTAG_URL] = None
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        self.assertEqual(d.textdiff(), 'removed     URL')
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_added_tag(self):
        self.oldhdr[rpm.RPMTAG_URL] = None
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        self.assertEqual(d.textdiff(), 'added       URL')
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_dropped_files(self):
        self.newfiles.clear()
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        expect = '\n'.join(['removed     /usr/test_file_%i' % i for i in range(3)])
        self.assertEqual(d.textdiff(), expect)
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_added_files(self):
        self.oldfiles.clear()
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        expect = '\n'.join(['added       /usr/test_file_%i' % i for i in range(3)])
        self.assertEqual(d.textdiff(), expect)
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_changed_file(self):
        fn = '/usr/test_file_1'
        self.newfiles[fn] = self.newfiles[fn]._replace(size='different')
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        expect = 'S.......... /usr/test_file_1'
        self.assertEqual(d.textdiff(), expect)
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_ignore_changed_file(self):
        fn = '/usr/test_file_1'
        self.newfiles[fn] = self.newfiles[fn]._replace(size='different')
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile, ignore='S')
        self.assertFalse(d.differs())
        self.assertEqual(d.textdiff(), '')
        self.assertEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_bytes(self):
        # kojihash should be able to handle bytes values
        fn = '/usr/test_file_1'
        self.newfiles[fn] = self.newfiles[fn]._replace(digest=six.b('asdfjhgqkjhf'))
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        expect = '..5........ /usr/test_file_1'
        self.assertEqual(d.textdiff(), expect)
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_added_dep(self):
        self.newhdr.update(make_prcos([{'name': 'foo'}]))
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        expect = 'added       PROVIDES foo >= 0.99.1'
        self.assertEqual(d.textdiff(), expect)
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))

    def test_rpmdiff_dropped_dep(self):
        self.oldhdr.update(make_prcos([{'name': 'foo'}]))
        d = koji.rpmdiff.Rpmdiff(self.oldfile, self.newfile)
        self.assertTrue(d.differs())
        expect = 'removed     PROVIDES foo >= 0.99.1'
        self.assertEqual(d.textdiff(), expect)
        self.assertNotEqual(d.kojihash(), d.kojihash(new=True))


def make_fake_header(prcos=None):
    tags = [
        # should align with koji.rpmdiff.Rpmdiff.TAGS
        'name',
        'summary',
        'description',
        'group',
        'license',
        'url',
        'prein',
        'postin',
        'preun',
        'postun',
    ]
    extra_tags = [
        # not in TAGS, but accessed by the pcro code
        'version',
        'release',
    ]
    hdr = {}
    for tag in tags + extra_tags:
        code = getattr(rpm, "RPMTAG_" + tag.upper())
        hdr[code] = "fake_%s" % tag
        # prco code expects lowercase string keys
        hdr[tag] = "fake_%s" % tag
    prcos = prcos or []
    hdr.update(make_prcos(prcos))
    return hdr


PRCO = namedtuple('PRCO', ['dtype', 'name', 'flag', 'version'])
depmap = {
    '<': rpm.RPMSENSE_LESS,
    '>': rpm.RPMSENSE_GREATER,
    '=': rpm.RPMSENSE_EQUAL,
    '<=': rpm.RPMSENSE_LESS | rpm.RPMSENSE_EQUAL,
    '>=': rpm.RPMSENSE_GREATER | rpm.RPMSENSE_EQUAL,
}


def make_prcos(prcos):
    # prcos should be a list of dicts
    # all pcro fields have defaults
    for dep in prcos:
        dep.setdefault('dtype', 'provides')
        dep.setdefault('name', 'somepackage')
        dep.setdefault('version', '0.99.1')
        dep.setdefault('flag', '>=')
        if dep['flag'] in depmap:
            dep['flag'] = depmap[dep['flag']]
    tags = [
        'provides',
        'requires',
        'conflicts',
        'obsoletes',
    ]
    data = {}
    for tag in tags:
        # the class uses string keys here
        deps = [d for d in prcos if d['dtype'] == tag]
        tag = tag.upper()
        ftag = tag[:-1] + 'FLAGS'
        vtag = tag[:-1] + 'VERSION'
        data[tag] = [d['name'] for d in deps]
        data[ftag] = [d['flag'] for d in deps]
        data[vtag] = [d['version'] for d in deps]
    return data


filekeys = ['size', 'mode', 'mtime', 'fflags', 'rdev', 'inode', 'nlink',
            'state', 'vflags', 'user', 'group', 'digest']
fileinfo = namedtuple('fileinfo', filekeys)


def make_fake_files(count=0):
    files = {}
    for i in range(count):
        name = '/usr/test_file_%i' % i
        files[name] = fileinfo(*filekeys)
    return files


# the end
