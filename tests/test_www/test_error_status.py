import unittest

try:
    from unittest import mock
except ImportError:
    import mock

import koji
from koji.util import HiddenValue

from .loadwebindex import webidx
import kojiweb


class TestErrorStatus(unittest.TestCase):

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
            'PythonDebug': False,
        }
        self.app = kojiweb.create_app(options=options)
        self.app.config['TESTING'] = True

    def _get(self, error):
        env = {'REQUEST_SCHEME': 'http'}
        with mock.patch.object(webidx, '_getServer', side_effect=error), \
                self.assertLogs('koji.web', level='ERROR'):
            return self.app.test_client().get('/userperms?userID=1&permission=tag&action=grant',
                                              environ_overrides=env)

    def test_action_not_allowed_is_forbidden(self):
        resp = self._get(koji.ActionNotAllowed('admin permission required'))
        self.assertEqual(resp.status_code, 403)

    def test_other_errors_stay_server_errors(self):
        resp = self._get(koji.GenericError('boom'))
        self.assertEqual(resp.status_code, 500)


if __name__ == '__main__':
    unittest.main()
