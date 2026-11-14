import unittest
from unittest import mock

import koji
import kojiweb
import kojiweb.errors
import kojiweb.util


# markers we plant in the values dict, so we can look for them in the output
EXCEPTION_LINE = 'EXCEPTION_LINE_MARKER'
TRACEBACK = 'FULL_TRACEBACK_MARKER'


def make_environ(options=None):
    opts = {
        'LoginDisabled': False,
        'SiteName': 'test',
        'LiteralFooter': True,
        'AllowRegistration': False,
    }
    if options:
        opts.update(options)
    return {'koji.options': opts}


class ErrorTemplateTestCase(unittest.TestCase):
    """Render error.html and check what actually reaches the browser."""

    def render(self, debug_level, tb_long):
        environ = make_environ()
        kojiweb.util._initValues(environ, 'Error', 'error')
        values = environ['koji.values']
        values.update({
            'explanation': 'an error occurred',
            'debug_level': debug_level,
            'tb_short': EXCEPTION_LINE,
            'tb_long': tb_long,
            'etype': None,
        })
        return kojiweb.util._genHTML(environ, 'error.chtml')


class TestTracebackNotRendered(ErrorTemplateTestCase):
    """An empty tb_long must mean the traceback block is not emitted at all.

    Regression guard: the block used to be wrapped in a
    "<div style=visibility: hidden>" whenever debug_level was below 2, which
    left the text in the page source for anyone to read.
    """

    def test_absent_when_tb_long_is_empty(self):
        for level in (0, 1, 2):
            out = self.render(level, '')
            self.assertNotIn(TRACEBACK, out)
            self.assertNotIn('<pre', out)

    def test_present_when_tb_long_has_content(self):
        # this is the PythonDebug case -- opt in and you get the traceback
        for level in (0, 1, 2):
            out = self.render(level, TRACEBACK)
            self.assertIn(TRACEBACK, out)
            self.assertIn('<pre', out)

    def test_no_css_hiding(self):
        # nothing should be hidden-but-present anywhere in the output
        for level in (0, 1, 2):
            for tb_long in ('', TRACEBACK):
                out = self.render(level, tb_long)
                self.assertNotIn('visibility: hidden', out)
                self.assertNotIn('display: none', out)


class TestExceptionLine(ErrorTemplateTestCase):
    """debug_level still controls the single-line exception text.

    Unlike the traceback this stays user-visible, since "No such task ID: 5"
    tells the user what went wrong. But when the level says hide it, it must
    be absent from the markup rather than merely concealed.
    """

    def test_shown_at_level_one_and_above(self):
        for level in (1, 2):
            out = self.render(level, '')
            self.assertIn(EXCEPTION_LINE, out)

    def test_absent_at_level_zero(self):
        out = self.render(0, '')
        self.assertNotIn(EXCEPTION_LINE, out)

    def test_level_zero_still_hides_traceback_text(self):
        # ServerOffline reports level 0, and a traceback must not ride along
        # even if PythonDebug is on
        out = self.render(0, TRACEBACK)
        self.assertNotIn(EXCEPTION_LINE, out)
        self.assertIn(TRACEBACK, out)


class ErrorPageTestCase(unittest.TestCase):
    """error_page checks: what it puts in the values dict."""

    def setUp(self):
        self.environ = {'koji.values': {}}
        self.captured = {}

        def fake_initValues(environ, *desc):
            environ['koji.values'] = {}
            return environ['koji.values']

        def fake_genHTML(environ, fileName):
            self.captured['file'] = fileName
            self.captured['values'] = environ['koji.values']
            return 'PAGE'

        self._patchers = [
            mock.patch.object(kojiweb.util, '_initValues', fake_initValues),
            mock.patch.object(kojiweb.util, '_genHTML', fake_genHTML),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self._patchers):
            patcher.stop()

    def raise_and_render(self, error, python_debug=False):
        """Render the error page for `error` and return the values dict"""
        try:
            raise error
        except type(error):
            kojiweb.errors.error_page(self.environ, {'PythonDebug': python_debug})
        return self.captured['values']

    def render_startup_error(self):
        kojiweb.errors.error_page(
            self.environ, {},
            message='the web interface failed to start up', err=False)
        return self.captured['values']


class TestPythonDebugGate(ErrorPageTestCase):

    def test_no_traceback_by_default(self):
        # PythonDebug is off in every shipped config
        values = self.raise_and_render(koji.GenericError('SUPER_SECRET_TOKEN'))
        self.assertEqual(values['tb_long'], '')
        self.assertNotIn('SUPER_SECRET_TOKEN', values['tb_long'])

    def test_no_placeholder_substituted(self):
        # we used to put "Full tracebacks disabled" here, which then rendered
        # as visible page content because explainError defaults to level 2
        values = self.raise_and_render(koji.GenericError('boom'))
        self.assertNotIn('traceback', values['tb_long'].lower())

    def test_traceback_only_with_pythondebug(self):
        values = self.raise_and_render(koji.GenericError('boom'), python_debug=True)
        self.assertIn('Traceback (most recent call last)', values['tb_long'])
        self.assertIn('GenericError', values['tb_long'])

    def test_pythondebug_off_gives_empty_string_not_none(self):
        # error.html tests {% if tb_long %}, so it has to be falsy, not missing
        values = self.raise_and_render(koji.GenericError('boom'), python_debug=False)
        self.assertEqual(values['tb_long'], '')

    def test_exception_line_still_available(self):
        # the single-line text is a deliberate feature, keep it
        values = self.raise_and_render(koji.GenericError('no such task'))
        self.assertIn('no such task', values['tb_short'])
        self.assertIn('koji.GenericError', values['tb_short'])


class TestStartupError(ErrorPageTestCase):
    """Startup failures must not leak exception detail into the page."""

    def test_startup_error_renders_no_exception_text(self):
        # err=False keeps error_page from describing a nonexistent exception,
        # which otherwise rendered a stray "NoneType: None"
        values = self.render_startup_error()
        self.assertEqual(values['tb_short'], '')
        self.assertEqual(values['tb_long'], '')
        self.assertEqual(values['debug_level'], 0)
        self.assertIsNone(values['etype'])
        self.assertNotIn('NoneType', str(values['explanation']))


class TestStartupErrorClient(unittest.TestCase):
    """End-to-end startup failure checks through the Flask app."""

    def test_exception_detail_not_in_message(self):
        secret = 'No module named super_secret_module'
        with mock.patch.object(kojiweb, 'load_config',
                               side_effect=RuntimeError(secret)):
            app = kojiweb.create_app()
            client = app.test_client()
            with self.assertLogs('koji.web', level='ERROR'):
                resp = client.get('/')
        self.assertEqual(resp.status_code, 500)
        body = resp.get_data(as_text=True)
        self.assertNotIn(secret, body)
        self.assertNotIn('super_secret_module', body)
        self.assertIn(app.extensions['kojiweb']['startup_error'], body)

    def test_exception_detail_goes_to_the_log(self):
        secret = 'super_secret_module'
        with mock.patch.object(kojiweb, 'load_config',
                               side_effect=RuntimeError(secret)):
            app = kojiweb.create_app()
            client = app.test_client()
            with self.assertLogs('koji.web', level='ERROR') as logs:
                client.get('/')
        logged_text = '\n'.join(logs.output)
        self.assertIn(secret, logged_text)
        self.assertIn('Traceback', logged_text)

    def test_startup_error_is_a_500(self):
        # it used to report 200 OK, which made monitors think all was well
        app = kojiweb.create_app(options={})
        app.extensions['kojiweb']['startup_error'] = 'the web interface failed to start up'
        client = app.test_client()
        resp = client.get('/')
        self.assertEqual(resp.status_code, 500)
        body = resp.get_data(as_text=True)
        self.assertIn('the web interface failed to start up', body)


if __name__ == '__main__':
    unittest.main()
