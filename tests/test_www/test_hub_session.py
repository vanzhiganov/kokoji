import gc
import re
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

import koji
from koji.util import HiddenValue

from .loadwebindex import webidx
import kojiweb


class FakeHubSession(object):
    """Minimal stand-in for koji.ClientSession, enough for the web views."""

    hub_logouts = []

    def __init__(self):
        self.opts = {}
        self.logged_in = False
        self.sinfo = None
        self.callnum = None
        self.seen_sinfo = None
        self.seen_callnum = None

    def __del__(self):
        # like koji.ClientSession: a logged-in session is logged out when collected
        if self.logged_in:
            FakeHubSession.hub_logouts.append(self.sinfo['session-id'])

    def _forget(self):
        self.setSession(None)

    def setSession(self, sinfo):
        self.sinfo = sinfo
        self.logged_in = sinfo is not None
        self.callnum = 0

    def login(self):
        self.setSession({'session-id': 7, 'session-key': 'key-abc', 'header-auth': True})
        return True

    def logout(self):
        self.logged_in = False

    def getUser(self, name):
        return {'id': 1, 'name': name}

    def mavenEnabled(self):
        return False

    def winEnabled(self):
        return False

    def listUsers(self, **kwargs):
        return []

    def listTasks(self, **kwargs):
        # record what the hub call saw, then advance the callnum like a real call
        self.seen_sinfo = dict(self.sinfo) if self.sinfo else None
        self.seen_callnum = self.callnum
        self.callnum += 3
        return []

    def __getattr__(self, name):
        # other hub methods are not needed by these tests
        return lambda *args, **kwargs: []


class TestHubSession(unittest.TestCase):

    def setUp(self):
        options = {
            'WebAuthType': koji.AUTHTYPES['NORMAL'],
            'WebCert': None,
            'ForceSSL': False,
            'Secret': HiddenValue('secret'),
            'LoginTimeout': 72,
            'AllowRegistration': False,
            'LoginDisabled': False,
            'KojiHubCA': '/nonexistent',
            'KojiHubURL': 'http://hub/kojihub',
            'SiteName': 'koji',
            'LogLevel': 'WARNING',
            'LiteralFooter': True,
            'KojiTheme': None,
            'Tasks': [],
            'ToplevelTasks': [],
            'ParentTasks': [],
            'HiddenUsers': None,
            'LibPath': '/nonexistent',
            'PythonDebug': True,
        }
        self.app = kojiweb.create_app(options=options)
        self.app.config['TESTING'] = True
        self.sessions = []
        FakeHubSession.hub_logouts = []

    def _make_session(self, options):
        session = FakeHubSession()
        self.sessions.append(session)
        return session

    def _cookie_header(self, response):
        cookies = []
        for header in response.headers.getlist('Set-Cookie'):
            name, value = header.split(';', 1)[0].split('=', 1)
            if value:
                cookies.append('%s=%s' % (name, value))
        return '; '.join(cookies)

    def test_password_login_keeps_hub_session_for_next_request(self):
        env = {'REQUEST_SCHEME': 'http'}
        with mock.patch.object(webidx, '_makeClientSession', side_effect=self._make_session):
            client = self.app.test_client()
            resp = client.post('/login', data={'username': 'alice', 'password': 'pw',
                                               'page': ''}, environ_overrides=env)
            self.assertEqual(resp.status_code, 302)
            cookie = self._cookie_header(resp)
            self.assertIn('hubsession=', cookie)

            # the next request must authenticate to the hub as the same session
            self.sessions.clear()
            resp = client.get('/tasks', headers={'Cookie': cookie},
                              environ_overrides=env)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(self.sessions), 1)
            first = self.sessions[0]
            self.assertEqual(first.seen_sinfo['session-id'], 7)
            self.assertEqual(first.seen_sinfo['session-key'], 'key-abc')
            # the first request starts at the stored callnum (0 after login)
            self.assertEqual(first.seen_callnum, 0)
            cookie = self._cookie_header(resp)
            # the callnum advanced by the hub call is stored for the next request
            self.assertTrue(cookie.split('hubsession=')[1].endswith(':3'), cookie)

            # the next request must continue from 3, not restart the sequence
            self.sessions.clear()
            resp = client.get('/tasks', headers={'Cookie': cookie},
                              environ_overrides=env)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(self.sessions[0].seen_callnum, 3)

            # the hub session must not be logged out when the request objects are collected
            first = None
            self.sessions.clear()
            gc.collect()
            self.assertEqual(FakeHubSession.hub_logouts, [])

    def test_tampered_hub_session_cookie_is_ignored(self):
        env = {'REQUEST_SCHEME': 'http'}
        with mock.patch.object(webidx, '_makeClientSession', side_effect=self._make_session):
            client = self.app.test_client()
            resp = client.post('/login', data={'username': 'alice', 'password': 'pw',
                                               'page': ''}, environ_overrides=env)
            cookie = self._cookie_header(resp)
            tampered = re.sub(r'hubsession=[^:]*:', 'hubsession=0000:', cookie)
            self.sessions.clear()
            # a fresh client, so the test client's own cookie jar does not add the valid cookie
            self.app.test_client().get('/tasks', headers={'Cookie': tampered},
                                       environ_overrides=env)
            self.assertEqual(len(self.sessions), 1)
            self.assertIsNone(self.sessions[0].seen_sinfo)


if __name__ == '__main__':
    unittest.main()
