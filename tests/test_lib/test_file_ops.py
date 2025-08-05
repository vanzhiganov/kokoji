from __future__ import absolute_import

import shutil
import tempfile
import unittest

try:
    from unittest import mock
except ImportError:
    import mock
import errno

from koji import ensuredir, _listdir


class TestEnsureDir(unittest.TestCase):

    def setUp(self):
        self.mkdir = mock.patch('os.mkdir').start()
        self.exists = mock.patch('os.path.exists').start()
        self.isdir = mock.patch('os.path.isdir').start()
        self._listdir = mock.patch('koji._listdir').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_ensuredir_errors(self):
        self.exists.return_value = False
        with self.assertRaises(OSError) as cm:
            ensuredir('/')
        self.assertEqual(cm.exception.args[0], 'root directory missing? /')
        self.mkdir.assert_not_called()

        self.exists.return_value = True
        self.isdir.return_value = False
        with self.assertRaises(OSError) as cm:
            ensuredir('/path/foo/bar')
        self.assertEqual(cm.exception.args[0],
                         'Not a directory: /path/foo/bar')
        self.mkdir.assert_not_called()

        self.exists.return_value = False
        self.isdir.return_value = False
        self.mkdir.side_effect = OSError(errno.EEXIST, 'error msg')
        with self.assertRaises(OSError) as cm:
            ensuredir('path')
        self.assertEqual(cm.exception.args[0], errno.EEXIST)
        self.mkdir.assert_called_once_with('path')

        self.mkdir.reset_mock()
        self.mkdir.side_effect = OSError(errno.EEXIST, 'error msg')
        self.isdir.return_value = True
        ensuredir('path')
        self.mkdir.assert_called_once_with('path')

    def test_ensuredir(self):
        self.exists.side_effect = [False, False, True]
        self.isdir.return_value = True
        ensuredir('/path/foo/bar/')
        self.assertEqual(self.exists.call_count, 3)
        self.assertEqual(self.isdir.call_count, 1)
        self.mkdir.assert_has_calls([mock.call('/path/foo'),
                                     mock.call('/path/foo/bar')])

    def test_ensuredir_error_is_dir(self):
        # mkdir errors with EEXIST, and directory does exist
        self.exists.return_value = False
        self.isdir.return_value = True
        self.mkdir.side_effect = OSError(errno.EEXIST, 'error msg')
        ensuredir('path')
        self._listdir.assert_called_once()
        self.isdir.assert_called_once()

    def test_ensuredir_wrong_errno(self):
        self.exists.return_value = False
        self.isdir.return_value = True
        # if mkdir fails with a different error, this should not be trapped
        self.mkdir.side_effect = OSError(errno.ENOENT, 'error msg')
        with self.assertRaises(OSError) as cm:
            ensuredir('path')
        self.assertEqual(cm.exception.args[0], errno.ENOENT)
        self._listdir.assert_not_called()
        self.isdir.assert_not_called()


class TestListDir(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        mock.patch.stopall()
        shutil.rmtree(self.tempdir)

    def test_listdir_success(self):
        # make some files in tempdir
        names = ['abc', 'def', 'ghi']
        for fn in names:
            path = '%s/%s' % (self.tempdir, fn)
            with open(path, 'wt') as fp:
                fp.write('hello world')

        contents = _listdir(self.tempdir)
        contents.sort()
        self.assertEqual(contents, names)

    def test_listdir_missing(self):
        missing = '%s/no-such-file' % self.tempdir
        contents = _listdir(missing)
        self.assertIsNone(contents)


# the end
