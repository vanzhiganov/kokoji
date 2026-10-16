# Configuration and logging for the koji web interface
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

import logging

import koji
import koji.util

# option, type, default
CFGMAP = [
    ['SiteName', 'string', None],
    ['KojiHubURL', 'string', 'http://localhost/kojihub'],
    ['KojiFilesURL', 'string', 'http://localhost/kojifiles'],
    ['KojiTheme', 'string', None],
    ['KojiGreeting', 'string', 'Welcome to Koji Web'],
    ['LiteralFooter', 'boolean', True],

    ['WebAuthType', 'string', None],

    ['WebCert', 'string', None],
    ['KojiHubCA', 'string', '/etc/kojiweb/kojihubca.crt'],

    ['PythonDebug', 'boolean', False],

    ['LoginTimeout', 'integer', 72],

    ['ForceSSL', 'boolean', True],

    ['Secret', 'string', None],

    ['LoginDisabled', 'boolean', False],

    ['AllowRegistration', 'boolean', False],

    ['LibPath', 'string', '/usr/share/koji-web/lib'],

    ['LogLevel', 'string', 'WARNING'],
    ['LogFormat', 'string',
     '%(msecs)d [%(levelname)s] m=%(method)s u=%(user_name)s p=%(process)s r=%(remoteaddr)s '
     '%(name)s: %(message)s'],

    ['Tasks', 'list', []],
    ['ToplevelTasks', 'list', []],
    ['ParentTasks', 'list', []],

    ['MBS_WEB_URL', 'string', None],

    ['RLIMIT_AS', 'string', None],
    ['RLIMIT_CORE', 'string', None],
    ['RLIMIT_CPU', 'string', None],
    ['RLIMIT_DATA', 'string', None],
    ['RLIMIT_FSIZE', 'string', None],
    ['RLIMIT_MEMLOCK', 'string', None],
    ['RLIMIT_NOFILE', 'string', None],
    ['RLIMIT_NPROC', 'string', None],
    ['RLIMIT_OFILE', 'string', None],
    ['RLIMIT_RSS', 'string', None],
    ['RLIMIT_STACK', 'string', None],
]


class HubFormatter(logging.Formatter):
    """Support some koji specific fields in the format string"""

    environ = {}

    def format(self, record):
        environ = self.environ
        record.method = environ.get('koji.method')
        record.remoteaddr = "%s:%s" % (
            environ.get('REMOTE_ADDR', '?'),
            environ.get('REMOTE_PORT', '?'))
        record.user_name = environ.get('koji.currentLogin')
        user = environ.get('koji.currentUser')
        if user:
            record.user_id = user['id']
        else:
            record.user_id = None
        session = environ.get('koji.session')
        record.session_id = None
        if session:
            record.callnum = session.callnum
            if session.sinfo:
                record.session_id = session.sinfo.get('session.id')
        else:
            record.callnum = None
        return logging.Formatter.format(self, record)


def load_config(environ):
    """Load configuration options.

    Options are read from a kojiweb config file. To override the
    configuration file location, use the SetEnv Apache directive. For
    example:

      SetEnv koji.web.ConfigFile /home/developer/koji/www/conf/web.conf

    Backwards compatibility:
        - if ConfigFile is not set, opts are loaded from http config
        - if ConfigFile is set, then the http config must not provide Koji options
        - In a future version we will load the default hub config regardless
        - all PythonOptions (except koji.web.ConfigFile) are now deprecated and
          support for them will disappear in a future version of Koji
    """
    cf = environ.get('koji.web.ConfigFile', '/etc/kojiweb/web.conf')
    cfdir = environ.get('koji.web.ConfigDir', '/etc/kojiweb/web.conf.d')
    # raw=True: the hub does the same (see kojixmlrpc.py). Without it,
    # configparser applies %-interpolation and any LogFormat containing
    # %(asctime)s-style fields raises InterpolationMissingOptionError.
    config = koji.read_config_files([cfdir, (cf, True)], raw=True)

    opts = {}
    for name, dtype, default in CFGMAP:
        key = ('web', name)
        if config.has_option(*key):
            if dtype == 'integer':
                opts[name] = config.getint(*key)
            elif dtype == 'boolean':
                opts[name] = config.getboolean(*key)
            elif dtype == 'list':
                opts[name] = [x.strip() for x in config.get(*key).split(',')]
            else:
                opts[name] = config.get(*key)
        else:
            opts[name] = default
    opts['Secret'] = koji.util.HiddenValue(opts['Secret'])

    if opts['WebAuthType'] not in (None, 'password', 'ssl'):
        raise koji.ConfigurationError(f"Invalid value {opts['WebAuthType']} for "
                                      "WebAuthType (password/ssl)")
    if opts['WebAuthType'] == 'ssl':
        opts['WebAuthType'] = koji.AUTHTYPES['SSL']
    elif opts['WebAuthType'] == 'password':
        opts['WebAuthType'] = koji.AUTHTYPES['NORMAL']
    # if there is no explicit request, use same authtype as web has
    elif opts['WebCert']:
        opts['WebAuthType'] = koji.AUTHTYPES['SSL']

    return opts


_log_handler = None


def setup_basic_logging():
    """Set up a basic stderr log handler for the koji logger (once)."""
    global _log_handler
    logger = logging.getLogger("koji")
    logger.setLevel(logging.WARNING)
    if _log_handler is None:
        _log_handler = logging.StreamHandler()
        log_format = '%(msecs)d [%(levelname)s] SETUP p=%(process)s %(name)s: %(message)s'
        _log_handler.setFormatter(logging.Formatter(log_format))
        _log_handler.setLevel(logging.DEBUG)
        logger.addHandler(_log_handler)
    return _log_handler


def setup_logging(opts, environ):
    """Adjust logging based on configuration options"""
    level = opts['LogLevel']
    valid_levels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    # the config value can be a single level name or a series of
    # logger:level names pairs. processed in order found
    default = None
    for part in level.split():
        pair = part.split(':', 1)
        if len(pair) == 2:
            name, level = pair
        else:
            name = 'koji'
            level = part
            default = level
        if level not in valid_levels:
            raise koji.GenericError("Invalid log level: %s" % level)
        # all our loggers start with koji
        if name == '':
            name = 'koji'
            default = level
        elif name.startswith('.'):
            name = 'koji' + name
        elif not name.startswith('koji'):
            name = 'koji.' + name
        level_code = logging.getLevelName(level)
        logging.getLogger(name).setLevel(level_code)
    logger = logging.getLogger("koji")
    # if KojiDebug is set, force main log level to DEBUG
    if opts.get('KojiDebug'):
        logger.setLevel(logging.DEBUG)
    elif default is None:
        # LogLevel did not configure a default level
        logger.setLevel(logging.WARNING)
    return HubFormatter(opts['LogFormat'])
