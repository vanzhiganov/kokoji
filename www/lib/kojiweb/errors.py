# Error handling for the koji web interface
#
# Copyright (c) 2005-2024 Red Hat, Inc.
#
#    Koji is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation;
#    version 2.1 of the License.
#
#    This software is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this software; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import sys
import traceback

import koji

from . import util


class URLNotFound(Exception):
    """Used to generate a 404 response"""


def simple_error_page(message=None, err=None):
    """Return a minimal standalone error page (used if templating fails)."""
    result = []
    result.append("""\
<!DOCTYPE html>
<html><head><title>Error</title></head>
<body>
""")
    if message:
        result.append("<p>%s</p>\n" % message)
    if err:
        result.append("<p>%s</p>\n" % err)
    result.append("</body></html>\n")
    return ''.join(result)


def error_page(environ, options, message=None, err=True):
    """Render the error template and return the resulting HTML.

    ``err`` indicates whether there is a live exception to describe. When it
    is False (e.g. a startup failure) no exception detail is emitted, which
    avoids rendering a stray "NoneType: None".
    """
    if err:
        etype, e = sys.exc_info()[:2]
        tb_short = ''.join(traceback.format_exception_only(etype, e))
        tb_long = ''.join(traceback.format_exception(*sys.exc_info()))
        if isinstance(e, koji.ServerOffline):
            desc = ('Outage', 'outage')
        else:
            desc = ('Error', 'error')
    else:
        etype = None
        e = None
        tb_short = ''
        tb_long = ''
        desc = ('Error', 'error')

    values = util._initValues(environ, *desc)
    values['etype'] = etype
    values['exception'] = e
    if err:
        values['explanation'], values['debug_level'] = util.explainError(e)
        if message:
            values['explanation'] = message
    else:
        values['explanation'] = message or "Unknown error"
        values['debug_level'] = 0
    values['tb_short'] = tb_short
    # PythonDebug is the only thing that may put a real traceback in the
    # response. error.html keys off tb_long having content, so an empty
    # string means the block is not rendered at all -- we must not fall
    # back to substituting placeholder text here.
    if int(options.get("PythonDebug", 0)):
        values['tb_long'] = tb_long
    else:
        values['tb_long'] = ''
    # default these koji values to false so _genHTML doesn't try to look
    # them up (which will fail badly if the hub is offline)
    environ['koji.values'].setdefault('mavenEnabled', False)
    environ['koji.values'].setdefault('winEnabled', False)
    return util._genHTML(environ, 'error.chtml')
