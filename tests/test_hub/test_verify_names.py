import unittest

from unittest import mock
import re

import koji
import kojihub


class TestVerifyNameInternal(unittest.TestCase):

    def setUp(self):
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context.session.assertPerm = mock.MagicMock()
        self.context.opts = {'MaxNameLengthInternal': 15,
                             'RegexNameInternal.compiled': re.compile('^[A-Za-z0-9/_.+-]+$')}

    def tearDown(self):
        mock.patch.stopall()

    def test_verify_name_internal_integer_type(self):
        expected_error = "Name should be string"
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.verify_name_internal(1234)
        self.assertEqual(expected_error, str(cm.exception))

    def test_verify_name_internal_longer(self):
        name = 'test-name-internal-longer'
        expected_error = "Name %s is too long. Max length is 15 characters" % name
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.verify_name_internal(name)
        self.assertEqual(expected_error, str(cm.exception))

    def test_verify_name_internal_wrong_chars(self):
        name = 'test-name@#'
        expected_error = "Name %s does not match RegexNameInternal value" % name
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.verify_name_internal(name)
        self.assertEqual(expected_error, str(cm.exception))


class TestVerifyUser(unittest.TestCase):
    def setUp(self):
        self.context = mock.patch('kojihub.kojihub.context').start()
        self.context.session.assertPerm = mock.MagicMock()
        self.context.opts = {'MaxNameLengthInternal': 15,
                             'RegexUserName.compiled': re.compile('^[A-Za-z0-9/_.@-]+$')}

    def tearDown(self):
        mock.patch.stopall()

    def test_verify_user_type_name(self):
        expected_error = "Name should be string"
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.verify_name_user(name=1234)
        self.assertEqual(expected_error, str(cm.exception))

    def test_verify_user_name_longer(self):
        name = 'test-user-longer'
        expected_error = "Name %s is too long. Max length is 15 characters" % name
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.verify_name_user(name=name)
        self.assertEqual(expected_error, str(cm.exception))

    def test_verify_user_name_wrong_chars(self):
        name = 'test-name+@#'
        expected_error = "Name %s does not match RegexUserName value" % name
        with self.assertRaises(koji.GenericError) as cm:
            kojihub.verify_name_user(name=name)
        self.assertEqual(expected_error, str(cm.exception))
