import ssl
import unittest
from xml.parsers.expat import ExpatError

import koji
from koji.xmlrpcplus import xmlrpc_client
from kojiweb.util import explainError, formatMode, formatLink, escapeHTML

class TestFormatMode(unittest.TestCase):
    def test_format_mode(self):
        formats = (
            ('drwxrwxr-x', 0x41fd), # dir
            ('-rw-------', 0x8180), # reg. file
            ('crw--w----', 0x2190), # /dev/tty0
            ('brw-rw----', 0x61b0), # /dev/sda
            ('lrwxrwxrwx', 0xa1ff), # symlink
            ('srwxr-xr-x', 0xc1ed), # socket
            ('-rwsrwsr--', 0x8db4), # suid
        )

        for s, mode in formats:
            self.assertEqual(formatMode(mode), s)

    def test_format_link(self):
        formats = (
            ('test me', 'test me'),
            ('  test ', 'test'),
            ('<script>hack</script>', '&lt;script&gt;hack&lt;/script&gt;'),
            ('not://valid', 'not://valid'),
            ('https://foo.com', '<a href="https://foo.com">https://foo.com</a>'),
            ('http://bar.com/', '<a href="http://bar.com/">http://bar.com/</a>'),
            ('HTtP://BaR.CoM/', '<a href="HTtP://BaR.CoM/">HTtP://BaR.CoM/</a>'),
            ('https://baz.com/baz&t=1', '<a href="https://baz.com/baz&amp;t=1">https://baz.com/baz&amp;t=1</a>'),
            ('ssh://git@pagure.io/foo', '<a href="ssh://git@pagure.io/foo">ssh://git@pagure.io/foo</a>'),
            ('git://git@pagure.io/foo', '<a href="git://git@pagure.io/foo">git://git@pagure.io/foo</a>'),
            ('obs://build.opensuse.org/foo', '<a href="obs://build.opensuse.org/foo">obs://build.opensuse.org/foo</a>'),
        )

        for input, output in formats:
            self.assertEqual(str(formatLink(input)), output)

    def test_escape_html(self):
        tests = (
            ('test me', 'test me'),
            ('test <danger>', 'test &lt;danger&gt;'),
            ('test <danger="true">', 'test &lt;danger=&quot;true&quot;&gt;'),
            ("test <danger='true'>", 'test &lt;danger=&#x27;true&#x27;&gt;'),
            ('test&test', 'test&amp;test'),
            ('test&amp;test', 'test&amp;test'),
        )

        for input, output in tests:
            self.assertEqual(escapeHTML(input), output)


class TestExplainError(unittest.TestCase):
    """explainError returns (prose, level).

    level only decides whether the single-line exception text is shown to the
    user; it no longer has any bearing on whether a traceback is rendered.
    That is gated solely on PythonDebug at the publisher. These tests pin the
    levels so a change here cannot silently start exposing exception text.
    """

    def test_no_traceback_level(self):
        # ServerOffline is the only error that suppresses the exception line
        str_, level = explainError(koji.ServerOffline('hub is down'))
        self.assertEqual(level, 0)
        self.assertIn('offline', str_.lower())

    def test_exception_only_levels(self):
        # these show the exception line but the prose is generic
        tests = [
            koji.RetryError('gave up'),
            ssl.SSLError('bad handshake'),
            ExpatError('malformed xml'),
            xmlrpc_client.ProtocolError('http://hub', 500, 'err', {}),
        ]
        for error in tests:
            str_, level = explainError(error)
            self.assertEqual(level, 1, '%r should be level 1' % (error,))
            self.assertTrue(str_)

    def test_default_levels(self):
        # these fall through to the generic branches and keep level 2
        fault = koji.GenericError('boom')
        fault.fromFault = True
        tests = [
            koji.GenericError('no such task'),
            fault,
            koji.ActionNotAllowed('nope'),
            koji.FunctionDeprecated('gone'),
            koji.AuthError('bad password'),
            RuntimeError('something else entirely'),
        ]
        for error in tests:
            str_, level = explainError(error)
            self.assertEqual(level, 2, '%r should be level 2' % (error,))
            self.assertTrue(str_)

    def test_generic_error_from_fault_differs(self):
        # a fault came from the hub, so the wording points at the server
        fault = koji.GenericError('boom')
        fault.fromFault = True
        local, _ = explainError(koji.GenericError('boom'))
        remote, _ = explainError(fault)
        self.assertNotEqual(local, remote)
        self.assertIn('main server', remote)
        self.assertIn('web interface code', local)

    def test_explanation_never_contains_exception_detail(self):
        # the prose must not echo the exception message back to the browser
        secret = 'SUPER_SECRET_TOKEN'
        for error in (koji.GenericError(secret), koji.ServerOffline(secret),
                      koji.ActionNotAllowed(secret), RuntimeError(secret)):
            str_, _ = explainError(error)
            self.assertNotIn(secret, str_)
