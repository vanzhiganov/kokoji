from __future__ import absolute_import

import io
import logging
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

import koji
from kojiweb.util import FieldStorageCompat

from .loadwebindex import webidx


class TestRegisterLogging(unittest.TestCase):
    """Every registration outcome must reach the log.

    Previously only the success path logged anything, so rejected and
    malformed attempts were invisible server-side. These cover all six
    outcomes plus the plain GET of the form, which deliberately does not log.
    """

    def setUp(self):
        self.records = []

        handler = logging.Handler()
        handler.emit = self.records.append
        self.handler = handler
        self.logger = webidx.authlogger
        self.old_level = self.logger.level
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

        self.session = mock.MagicMock()
        self.values = {}

    def tearDown(self):
        self.logger.removeHandler(self.handler)
        self.logger.setLevel(self.old_level)
        mock.patch.stopall()

    def call_register(self, form, allow=True, side_effect=None, field_storage=None):
        environ = {
            'koji.options': {'AllowRegistration': allow},
            'koji.form': field_storage if field_storage is not None else mock.MagicMock(
                **{'getfirst.side_effect': lambda k, d='': form.get(k, d)}),
            'koji.values': self.values,
        }
        if side_effect is not None:
            self.session.registerUser.side_effect = side_effect

        with mock.patch.object(webidx, '_getServer', return_value=self.session), \
                mock.patch.object(webidx, '_initValues', return_value=self.values), \
                mock.patch.object(webidx, '_genHTML', return_value='<html/>'):
            webidx.register(environ)

    def messages(self):
        return [r.getMessage() for r in self.records]

    def test_success_logged(self):
        self.call_register({'username': 'bob', 'password': 'pw',
                            'confirm_password': 'pw'})
        self.assertEqual(self.messages(), ['New user registered: bob'])
        self.assertEqual(self.records[0].levelno, logging.INFO)

    def test_post_body_is_sent_to_hub(self):
        body = b'username=bob&password=pw&confirm_password=pw'
        environ = {
            'REQUEST_METHOD': 'POST',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': str(len(body)),
            'QUERY_STRING': '',
            'wsgi.input': io.BytesIO(body),
        }
        form = FieldStorageCompat(environ)

        self.call_register({}, field_storage=form)

        self.session.registerUser.assert_called_once_with('bob', 'pw')

    def test_hub_rejection_logged(self):
        self.call_register({'username': 'bob', 'password': 'pw',
                            'confirm_password': 'pw'},
                           side_effect=koji.GenericError('user already exists: bob'))
        self.assertEqual(self.messages(),
                         ['Registration failed for bob: user already exists: bob'])
        self.assertEqual(self.records[0].levelno, logging.WARNING)

    def test_missing_username_logged(self):
        self.call_register({'password': 'pw', 'confirm_password': 'pw'})
        self.assertEqual(self.messages(), ['Registration failed: no username submitted'])
        self.assertEqual(self.records[0].levelno, logging.WARNING)

    def test_missing_password_logged(self):
        self.call_register({'username': 'bob', 'confirm_password': 'pw'})
        self.assertEqual(self.messages(),
                         ['Registration failed: no password submitted for user bob'])
        self.assertEqual(self.records[0].levelno, logging.WARNING)

    def test_password_mismatch_logged(self):
        self.call_register({'username': 'bob', 'password': 'a',
                            'confirm_password': 'b'})
        self.assertEqual(self.messages(),
                         ['Registration failed: password mismatch for user bob'])
        self.assertEqual(self.records[0].levelno, logging.WARNING)

    def test_disabled_logged_and_raises(self):
        with self.assertRaises(koji.ActionNotAllowed):
            self.call_register({'username': 'bob', 'password': 'pw',
                                'confirm_password': 'pw'}, allow=False)
        self.assertEqual(self.messages(),
                         ['Registration refused: registration is disabled on this server'])
        self.assertEqual(self.records[0].levelno, logging.WARNING)

    def test_form_view_not_logged(self):
        # a plain GET is not a registration action; logging it would let anyone
        # flood the log by reloading the page
        self.call_register({})
        self.assertEqual(self.messages(), [])

    def test_password_never_logged(self):
        secret = 'sup3rs3cret'
        for form in (
                {'username': 'bob', 'password': secret, 'confirm_password': 'other'},
                {'username': 'bob', 'password': secret, 'confirm_password': secret},
                {'username': 'bob'},
                {}):
            self.records = []
            self.call_register(form)
            for msg in self.messages():
                self.assertNotIn(secret, msg)


if __name__ == '__main__':
    unittest.main()
