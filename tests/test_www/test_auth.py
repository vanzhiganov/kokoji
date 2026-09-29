from __future__ import absolute_import

import unittest

try:
    from unittest import mock
except ImportError:
    import mock

import koji

from .loadwebindex import webidx


class TestForceSSL(unittest.TestCase):

    def test_password_login_redirect_uses_config(self):
        for force_ssl in (False, True):
            with self.subTest(force_ssl=force_ssl):
                session = mock.MagicMock()
                form = mock.MagicMock()
                form.getfirst.side_effect = lambda key, default=None: {
                    'username': 'alice', 'password': 'pw',
                }.get(key, default)
                environ = {
                    'koji.session': session,
                    'koji.options': {'ForceSSL': force_ssl},
                    'koji.form': form,
                }

                with mock.patch.object(webidx, '_initValues', return_value={}), \
                        mock.patch.object(webidx, '_setUserCookie'), \
                        mock.patch.object(webidx, '_redirectBack') as redirect_back:
                    webidx._password_login(environ)

                redirect_back.assert_called_once_with(environ, None, forceSSL=force_ssl)

    def test_force_ssl_controls_password_cookie_only(self):
        for auth_type, secure in (
                (koji.AUTHTYPES['NORMAL'], False),
                (koji.AUTHTYPES['SSL'], True)):
            environ = {
                'koji.options': {
                    'ForceSSL': False,
                    'WebAuthType': auth_type,
                    'Secret': mock.Mock(value='secret'),
                    'LoginTimeout': 72,
                },
                'SCRIPT_NAME': '/koji',
                'koji.headers': [],
            }

            webidx._setUserCookie(environ, 'alice')

            self.assertEqual('Secure' in environ['koji.headers'][0][1], secure)


if __name__ == '__main__':
    unittest.main()
