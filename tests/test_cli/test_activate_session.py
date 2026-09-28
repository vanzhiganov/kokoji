from __future__ import absolute_import
try:
    from unittest import mock
except ImportError:
    import mock
import shutil
import tempfile
import unittest

from koji_cli.lib import activate_session


class TestActivateSession(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.warn = mock.patch('koji_cli.lib.warn').start()
        self.error = mock.patch('koji_cli.lib.error').start()
        self.session = mock.MagicMock()

    def tearDown(self):
        mock.patch.stopall()
        shutil.rmtree(self.tempdir)

    def test_activate_session_noauth(self):
        self.session.logged_in = False
        options = {'authtype': 'noauth', 'debug': False}
        activate_session(self.session, options)
        options = {'authtype': None, 'noauth': True, 'debug': False}
        activate_session(self.session, options)
        self.session.login.assert_not_called()
        self.session.ssl_login.assert_not_called()

    def test_activate_session_ssl(self):
        self.session.logged_in = False
        certfile = '%s/CERT' % self.tempdir
        options = {'authtype': 'ssl', 'debug': False, 'cert': certfile, 'serverca': 'SERVERCA'}
        activate_session(self.session, options)
        self.session.ssl_login.assert_called_once_with(certfile, None, 'SERVERCA', proxyuser=None)
        self.session.login.assert_not_called()

    def test_activate_session_ssl_logged(self):
        self.session.logged_in = True
        certfile = '%s/CERT' % self.tempdir
        options = {'authtype': 'ssl', 'debug': False, 'cert': certfile, 'serverca': 'SERVERCA'}
        activate_session(self.session, options)
        self.session.ssl_login.assert_not_called()
        self.session.login.assert_not_called()

    def test_activate_session_ssl_implicit_logged(self):
        self.session.logged_in = True
        certfile = '%s/CERT' % self.tempdir
        open(certfile, 'w').close()
        options = {'authtype': None, 'debug': False, 'cert': certfile, 'serverca': 'SERVERCA'}
        activate_session(self.session, options)
        self.session.ssl_login.assert_not_called()
        self.session.login.assert_not_called()

    def test_activate_session_ssl_implicit(self):
        self.session.logged_in = False
        certfile = '%s/CERT' % self.tempdir
        open(certfile, 'w').close()
        options = {'authtype': None, 'debug': False, 'cert': certfile, 'serverca': 'SERVERCA'}
        activate_session(self.session, options)
        self.session.ssl_login.assert_called_once_with(certfile, None, 'SERVERCA', proxyuser=None)
        self.session.login.assert_not_called()

    def test_activate_session_pw_logged(self):
        self.session.logged_in = True
        options = {'authtype': 'password', 'debug': False, 'cert': ''}
        activate_session(self.session, options)
        self.session.login.assert_not_called()
        self.session.ssl_login.assert_not_called()

    def test_activate_session_pw(self):
        self.session.logged_in = False
        options = {'authtype': 'password', 'debug': False, 'cert': ''}
        activate_session(self.session, options)
        self.session.login.assert_called_once_with()
        self.session.ssl_login.assert_not_called()

    def test_activate_session_pw_implicit_logged(self):
        self.session.logged_in = True
        options = {'authtype': None, 'debug': False, 'cert': '', 'user': 'USER'}
        activate_session(self.session, options)
        self.session.login.assert_not_called()
        self.session.ssl_login.assert_not_called()

    def test_activate_session_pw_implicit(self):
        self.session.logged_in = False
        options = {'authtype': None, 'debug': False, 'cert': '', 'user': 'USER'}
        activate_session(self.session, options)
        self.session.login.assert_called_once_with()
        self.session.ssl_login.assert_not_called()

    def test_activate_session_krb_logged(self):
        self.session.logged_in = True
        options = {'authtype': 'kerberos', 'debug': False, 'cert': ''}
        activate_session(self.session, options)
        self.session.login.assert_not_called()
        self.session.ssl_login.assert_not_called()

    def test_activate_session_krb_rejected(self):
        # error() is mocked out, so unlike in production the rejected authtype
        # falls through to the generic "unable to log in" error as well
        self.session.logged_in = False
        options = {'authtype': 'kerberos', 'debug': False, 'cert': ''}
        activate_session(self.session, options)
        self.session.login.assert_not_called()
        self.session.ssl_login.assert_not_called()
        self.error.assert_any_call(
            'Kerberos authentication is no longer supported; use --authtype ssl '
            'or --authtype password')

    def test_activate_session_no_method(self):
        # nothing configured: neither a cert file nor a user, so no auth method
        # is attempted and the user is told why
        self.session.logged_in = False
        options = {'authtype': None, 'debug': False, 'cert': ''}
        activate_session(self.session, options)
        self.session.login.assert_not_called()
        self.session.ssl_login.assert_not_called()
        self.error.assert_called_once()
