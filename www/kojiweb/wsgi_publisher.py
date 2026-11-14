# mod_wsgi entry point for the koji web interface
#
# Copyright (c) 2012-2024 Red Hat, Inc.
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
#
# This file is loaded by mod_wsgi (see the "Alias /koji" directive in
# conf/kojiweb.conf). The application itself now lives in the kojiweb
# package; this module only has to make that package importable and expose
# its WSGI application.

import os
import sys

# Make sure the kojiweb package can be found. The Apache configuration should
# normally add this via WSGIDaemonProcess python-path, but keep a fallback so
# the entry point works when run directly as well.
_LIBPATH = os.environ.get('KOJIWEB_LIBPATH', '/usr/share/koji-web/lib')
if os.path.isdir(_LIBPATH) and _LIBPATH not in sys.path:
    sys.path.insert(0, _LIBPATH)

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from kojiweb.wsgi import application  # noqa: E402,F401
