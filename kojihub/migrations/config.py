# Database configuration helpers for Koji hub schema migrations.
#
# The database settings are read from the same hub configuration files
# used by kojihub (see kojihub.kojixmlrpc.load_config), so migrations
# always target the database the hub itself uses.

import os

import psycopg2.extensions
from sqlalchemy.engine import URL

import koji

DEFAULT_CONFIG_FILE = '/etc/koji-hub/hub.conf'
DEFAULT_CONFIG_DIR = '/etc/koji-hub/hub.conf.d'

DB_OPTIONS = ('DBName', 'DBUser', 'DBHost', 'DBPort', 'DBPass', 'DBConnectionString')


def load_db_opts(config_file=None, config_dir=None):
    """Read database options from the hub configuration file(s)

    :param str config_file: hub config file (default: $KOJI_HUB_CONFIG
        or /etc/koji-hub/hub.conf)
    :param str config_dir: hub config directory (default: $KOJI_HUB_CONFIG_DIR
        or /etc/koji-hub/hub.conf.d)
    :returns dict: options with None values omitted
    """
    cf = config_file or os.environ.get('KOJI_HUB_CONFIG', DEFAULT_CONFIG_FILE)
    cfdir = config_dir or os.environ.get('KOJI_HUB_CONFIG_DIR', DEFAULT_CONFIG_DIR)
    config = koji.read_config_files([cfdir, (cf, True)], raw=True)
    opts = {}
    for name in DB_OPTIONS:
        if config.has_option('hub', name):
            value = config.get('hub', name)
            if value is not None and value != '':
                opts[name] = value
    # note: option names are case insensitive, so the legacy DBhost
    # spelling is covered by DBHost above
    return opts


def _url_from_dsn(dsn):
    """Normalize a DBConnectionString value to a SQLAlchemy URL"""
    if dsn.startswith('postgres://'):
        return 'postgresql+psycopg2://' + dsn[len('postgres://'):]
    if dsn.startswith('postgresql://'):
        return 'postgresql+psycopg2://' + dsn[len('postgresql://'):]
    if dsn.startswith('postgresql+'):
        # already carries a driver specification
        return dsn
    # key=value connection string
    params = psycopg2.extensions.parse_dsn(dsn)
    return URL.create(
        'postgresql+psycopg2',
        username=params.get('user'),
        password=params.get('password'),
        host=params.get('host'),
        port=int(params['port']) if params.get('port') else None,
        database=params.get('dbname'),
    ).render_as_string(hide_password=False)


def get_db_url(opts=None, config_file=None, config_dir=None):
    """Build a SQLAlchemy database URL from the hub database options

    DBConnectionString takes precedence over the individual DB* options,
    mirroring the behavior of kojihub.db.connect().

    :param dict opts: preloaded options (as returned by load_db_opts);
        if omitted, the options are read from the hub configuration
    :returns str: the database URL
    """
    if opts is None:
        opts = load_db_opts(config_file, config_dir)
    if opts.get('DBConnectionString'):
        return _url_from_dsn(opts['DBConnectionString'])
    port = opts.get('DBPort')
    return URL.create(
        'postgresql+psycopg2',
        username=opts.get('DBUser'),
        password=opts.get('DBPass'),
        host=opts.get('DBHost'),
        port=int(port) if port else None,
        database=opts.get('DBName'),
    ).render_as_string(hide_password=False)
