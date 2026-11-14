import unittest

try:
    from unittest import mock
except ImportError:
    import mock

import koji
from koji.util import HiddenValue

from .loadwebindex import webidx
import kojiweb


class TestLoginCookie(unittest.TestCase):

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
        }
        self.app = kojiweb.create_app(options=options)
        self.app.config['TESTING'] = True

    def test_successful_login_sets_user_cookie_on_redirect(self):
        session = mock.MagicMock()
        session.login.return_value = True

        def fake_get_server(environ):
            environ['koji.session'] = session
            return session

        with mock.patch.object(webidx, '_getServer', side_effect=fake_get_server):
            resp = self.app.test_client().post(
                '/login',
                data={'username': 'alice', 'password': 'pw', 'page': ''},
                environ_overrides={'REQUEST_SCHEME': 'http'})

        self.assertEqual(resp.status_code, 302)
        cookies = resp.headers.getlist('Set-Cookie')
        self.assertTrue(any(c.startswith('user=') and ':alice:' in c for c in cookies),
                        cookies)


if __name__ == '__main__':
    unittest.main()
