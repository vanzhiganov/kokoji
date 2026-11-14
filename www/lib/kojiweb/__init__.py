# Koji web interface (Flask application)
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
#
# Authors:
#       Mike Bonnet <mikeb@redhat.com>
#       Mike McLean <mikem@redhat.com>

import inspect
import logging
import os
import sys
import traceback

from flask import Flask, Response, make_response, redirect, request

import koji
import koji.util
from koji.server import ServerRedirect
from koji.util import dslice

from . import errors
from . import util
from . import views
from .config import load_config, setup_basic_logging, setup_logging


# static files are served under this url prefix; in production Apache serves
# the directory directly, but Flask can serve it in development.
STATIC_URL_PATH = '/koji-static'

# location of the static files relative to this package
_DEFAULT_STATIC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, 'static'))

# handlers that are registered as url rules, keyed by method name
_HANDLERS = {}


def _find_handlers():
    """Discover the environ-style handlers in the views module."""
    handlers = {}
    for name in dir(views):
        if name.startswith('_'):
            continue
        val = getattr(views, name, None)
        if not inspect.isfunction(val):
            continue
        try:
            args = inspect.getfullargspec(val).args
        except TypeError:  # pragma: no cover
            continue
        if not args or args[0] != 'environ':
            continue
        handlers[name] = val
    return handlers


def _get_handler(name):
    global _HANDLERS
    if not _HANDLERS:
        _HANDLERS = _find_handlers()
    return _HANDLERS.get(name)


def _dispatch(name):
    """Run the environ-style handler named ``name`` and build a response.

    This mirrors the old wsgi_publisher.Dispatcher.handle_request, but the
    result is returned as a Flask Response.
    """
    from flask import current_app

    app = current_app
    environ = request.environ
    environ.setdefault('koji.method', name)

    state = app.extensions['kojiweb']

    if state.get('startup_error'):
        body, status = _render_error(environ, state, message=state['startup_error'], err=False)
        return Response(body, status=status, mimetype='text/html')

    if request.method not in ('GET', 'POST', 'HEAD'):
        body, status = _render_error(environ, state, message="Method Not Allowed", err=False)
        return Response(body, status=405, mimetype='text/html')

    options = state.get('options')
    if options is None:
        options = load_config(environ)
        state['options'] = options
        state['formatter'] = setup_logging(options, environ)
    environ['koji.options'] = options
    environ['koji.headers'] = []
    formatter = state.get('formatter')
    if formatter is not None:
        formatter.environ = environ

    func = _get_handler(name)
    if func is None:
        msg = "Not found: %s" % environ.get('REQUEST_URI', name)
        body, status = _render_error(environ, state, message=msg, err=False)
        return Response(body, status=404, mimetype='text/html')

    # parse url/form args
    fs = util.FieldStorageCompat(environ)
    environ['koji.form'] = fs
    args = inspect.getfullargspec(func).args
    data = dslice(fs.data, args, strict=False)

    try:
        result = func(environ, **data)
        status = 200
    except ServerRedirect:
        location = environ.get('koji.redirect', '/')
        resp = redirect(location, code=302)
        views._persistHubSession(environ)
        # keep the Set-Cookie headers (e.g. the user cookie set on login)
        _apply_headers(resp, environ.get('koji.headers', []))
        return resp
    except Exception as exc:
        tb_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger("koji.web").error(tb_str)
        views._persistHubSession(environ)
        body, status = _render_error(environ, state)
        if isinstance(exc, koji.ActionNotAllowed):
            # the user is logged in but lacks the permission for this action
            status = 403
        resp = Response(body, status=status, mimetype='text/html')
        _apply_headers(resp, environ.get('koji.headers', []))
        return resp

    views._persistHubSession(environ)

    if result is None:
        result = ''
    resp = make_response(result, status)
    resp.headers.setdefault('Content-Type', 'text/html')
    _apply_headers(resp, environ.get('koji.headers', []))
    return resp


def _render_error(environ, state, message=None, err=True):
    """Render the error page, falling back to a simple page on failure."""
    options = state.get('options') or {}
    try:
        body = errors.error_page(environ, options, message=message, err=err)
    except Exception:  # pragma: no cover - defensive
        logging.getLogger("koji.web").exception('error rendering failed')
        body = errors.simple_error_page(message, err='Internal Server Error')
        return body, 500
    status = 200
    if err or message == state.get('startup_error'):
        status = 500
    elif message and message.startswith('Not found'):
        status = 404
    elif message == 'Method Not Allowed':
        status = 405
    return body, status


def _apply_headers(response, headers):
    """Apply headers accumulated in environ['koji.headers'].

    Multiple Set-Cookie headers are preserved; for any other header the last
    value wins (matching the old dispatcher behavior).
    """
    simple = {}
    set_cookies = []
    for name, value in headers:
        key = name.lower()
        if key == 'set-cookie':
            set_cookies.append((name, value))
        else:
            simple[key] = (name, value)
    for name, value in simple.values():
        response.headers[name] = value
    for name, value in set_cookies:
        response.headers.add(name, value)


def create_app(config=None, options=None):
    """Create and configure the kojiweb Flask application.

    :param dict config: optional Flask configuration overrides
    :param dict options: pre-loaded koji web options (mainly for testing)
    """
    setup_basic_logging()

    app = Flask(
        __name__,
        template_folder='templates',
        static_url_path=STATIC_URL_PATH,
        static_folder=_DEFAULT_STATIC_DIR,
    )
    if config:
        app.config.update(config)
    # testing uses raise-on-error semantics elsewhere; keep exceptions from
    # being swallowed by surprise
    app.config.setdefault('PROPAGATE_EXCEPTIONS', None)

    util.setup_jinja_env(app.jinja_env)
    # make the templates directory configurable (used by tests)
    if app.config.get('TEMPLATE_DIR'):
        app.jinja_loader = util.jinja2.FileSystemLoader(app.config['TEMPLATE_DIR'])

    app.extensions['kojiweb'] = {
        'options': options,
        'formatter': None,
        'startup_error': None,
    }

    @app.before_request
    def _before_request():
        # A request like /koji (no trailing slash) leaves PATH_INFO empty,
        # which breaks the relative urls used throughout the interface.
        if not request.environ.get('PATH_INFO'):
            target = request.environ.get('REQUEST_URI') or (request.script_root + '/')
            return redirect(target + '/', code=302)
        state = app.extensions['kojiweb']
        if state.get('options') is None and not state.get('startup_error'):
            try:
                state['options'] = load_config(request.environ)
                state['formatter'] = setup_logging(state['options'], request.environ)
                koji.util.setup_rlimits(state['options'])
            except Exception:
                etype, e = sys.exc_info()[:2]
                tb_short = ''.join(traceback.format_exception_only(etype, e))
                tb_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger("koji.web").error(
                    "Startup failed: %s\n%s", tb_short, tb_str)
                state['startup_error'] = ("The web interface failed to start up. "
                                          "Please check the server log for details.")
        return None

    @app.route('/', methods=['GET', 'POST', 'HEAD'], endpoint='index')
    @app.route('/<name>', methods=['GET', 'POST', 'HEAD'], endpoint='handler',
               strict_slashes=False)
    def dispatch(name='index'):
        return _dispatch(name)

    return app
