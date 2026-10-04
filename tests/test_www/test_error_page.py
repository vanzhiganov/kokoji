import importlib.util
import os
import os.path
import shutil
import sys
import tempfile
import unittest
import warnings
from unittest import mock

import Cheetah.Template

import koji
import kojiweb
import kojiweb.util


WSP_FILENAME = os.path.join(os.path.dirname(__file__), '../../www/kojiweb/wsgi_publisher.py')
ERROR_TMPL = os.path.join(os.path.dirname(__file__), '../../www/kojiweb/error.chtml')

# markers we plant in the values dict, so we can look for them in the output
EXCEPTION_LINE = 'EXCEPTION_LINE_MARKER'
TRACEBACK = 'FULL_TRACEBACK_MARKER'


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# load wsgi_publisher by path, the same way loadwebindex.py loads index.py
wsp = load_module('wsgi_publisher_test', WSP_FILENAME)


class ErrorTemplateTestCase(unittest.TestCase):
    """Render error.chtml and check what actually reaches the browser.

    Cheetah resolves a relative #include against the cwd (not the template's
    own directory) and error.chtml starts with "#from kojiweb import util", so
    we render a copy out of a temp dir alongside stub includes.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.origdir = os.getcwd()
        os.mkdir(os.path.join(self.tmpdir, 'includes'))
        for name in ('header.chtml', 'footer.chtml'):
            with open(os.path.join(self.tmpdir, 'includes', name), 'w') as f:
                f.write('stub\n')
        shutil.copy(ERROR_TMPL, os.path.join(self.tmpdir, 'error.chtml'))
        os.chdir(self.tmpdir)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.template = Cheetah.Template.Template.compile(file='error.chtml')

    def tearDown(self):
        os.chdir(self.origdir)
        shutil.rmtree(self.tmpdir)

    def render(self, debug_level, tb_long):
        values = {
            'explanation': 'an error occurred',
            'debug_level': debug_level,
            'tb_short': EXCEPTION_LINE,
            'tb_long': tb_long,
        }
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            return str(self.template(namespaces=[values]).respond())


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
            self.assertNotIn('<pre>', out)

    def test_present_when_tb_long_has_content(self):
        # this is the PythonDebug case -- opt in and you get the traceback
        for level in (0, 1, 2):
            out = self.render(level, TRACEBACK)
            self.assertIn(TRACEBACK, out)
            self.assertIn('<pre>', out)

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
    """Publisher-level checks: what error_page puts in the values dict."""

    def setUp(self):
        self.dispatcher = wsp.Dispatcher()
        self.environ = {'koji.values': {}}
        self.captured = {}

        def fake_initValues(environ, *desc):
            environ['koji.values'] = {}
            return environ['koji.values']

        def fake_genHTML(environ, fileName):
            self.captured['file'] = fileName
            self.captured['values'] = environ['koji.values']
            return 'PAGE'

        # error_page looks up the global "kojiweb", which _setup would have
        # imported; we skip _setup so bind it ourselves
        self._patchers = [
            mock.patch.object(kojiweb.util, '_initValues', fake_initValues),
            mock.patch.object(kojiweb.util, '_genHTML', fake_genHTML),
            mock.patch.object(wsp, 'kojiweb', kojiweb, create=True),
        ]
        for patcher in self._patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self._patchers):
            patcher.stop()

    def raise_and_render(self, error, python_debug=False):
        """Render the error page for `error` and return the values dict"""
        self.dispatcher.options = {'PythonDebug': python_debug}
        try:
            raise error
        except type(error):
            self.dispatcher.error_page(self.environ)
        return self.captured['values']

    def render_startup_error(self):
        self.dispatcher.options = {}
        statuses = []
        self.dispatcher.handle_request(
            {'REQUEST_METHOD': 'GET', 'koji.values': {}},
            lambda status, headers: statuses.append(status))
        return statuses, self.captured['values']


class TestPythonDebugGate(ErrorPageTestCase):

    def test_no_traceback_by_default(self):
        # PythonDebug is off in every shipped config
        self.dispatcher.options = {}
        try:
            raise koji.GenericError('SUPER_SECRET_TOKEN')
        except koji.GenericError:
            self.dispatcher.error_page(self.environ)
        values = self.captured['values']
        self.assertEqual(values['tb_long'], '')
        self.assertNotIn('SUPER_SECRET_TOKEN', values['tb_long'])

    def test_no_placeholder_substituted(self):
        # we used to put "Full tracebacks disabled" here, which then rendered
        # as visible page content because explainError defaults to level 2
        self.dispatcher.options = {}
        try:
            raise koji.GenericError('boom')
        except koji.GenericError:
            self.dispatcher.error_page(self.environ)
        self.assertNotIn('traceback', self.captured['values']['tb_long'].lower())

    def test_traceback_only_with_pythondebug(self):
        values = self.raise_and_render(koji.GenericError('boom'), python_debug=True)
        self.assertIn('Traceback (most recent call last)', values['tb_long'])
        self.assertIn('GenericError', values['tb_long'])

    def test_pythondebug_off_gives_empty_string_not_none(self):
        # error.chtml tests #if $tb_long, so it has to be falsy, not missing
        self.dispatcher.options = {'PythonDebug': False}
        try:
            raise koji.GenericError('boom')
        except koji.GenericError:
            self.dispatcher.error_page(self.environ)
        self.assertEqual(self.captured['values']['tb_long'], '')

    def test_exception_line_still_available(self):
        # the single-line text is a deliberate feature, keep it
        values = self.raise_and_render(koji.GenericError('no such task'))
        self.assertIn('no such task', values['tb_short'])
        self.assertIn('koji.GenericError', values['tb_short'])


class TestStartupError(ErrorPageTestCase):

    def test_exception_detail_not_in_message(self):
        secret = 'No module named super_secret_module'
        with mock.patch.object(self.dispatcher, '_setup', side_effect=RuntimeError(secret)):
            with mock.patch.object(self.dispatcher.logger, 'error'):
                self.dispatcher.setup({})
        self.assertIsNotNone(self.dispatcher.startup_error)
        self.assertNotIn(secret, self.dispatcher.startup_error)
        self.assertNotIn('super_secret_module', self.dispatcher.startup_error)

    def test_exception_detail_goes_to_the_log(self):
        secret = 'super_secret_module'
        with mock.patch.object(self.dispatcher, '_setup', side_effect=RuntimeError(secret)):
            with mock.patch.object(self.dispatcher.logger, 'error') as logged:
                self.dispatcher.setup({})
        logged.assert_called_once()
        logged_text = ''.join([str(x) for x in logged.call_args[0]])
        self.assertIn(secret, logged_text)
        self.assertIn('Traceback', logged_text)

    def test_startup_error_is_a_500(self):
        # it used to report 200 OK, which made monitors think all was well
        self.dispatcher.startup_error = 'the web interface failed to start up'
        statuses, values = self.render_startup_error()
        self.assertEqual(statuses, ['500 Internal Server Error'])
        self.assertEqual(values['explanation'], self.dispatcher.startup_error)

    def test_startup_error_renders_no_exception_text(self):
        # err=False keeps error_page from describing a nonexistent exception,
        # which otherwise rendered a stray "NoneType: None"
        self.dispatcher.startup_error = 'the web interface failed to start up'
        statuses, values = self.render_startup_error()
        self.assertEqual(values['tb_short'], '')
        self.assertEqual(values['tb_long'], '')
        self.assertEqual(values['debug_level'], 0)
        self.assertIsNone(values['etype'])
        self.assertNotIn('NoneType', str(values['explanation']))


if __name__ == '__main__':
    unittest.main()
