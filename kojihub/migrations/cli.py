# Command line interface for Koji hub database migrations.
#
# Wraps Alembic commands, resolving the database connection from the hub
# configuration the same way env.py does.

import argparse

from alembic import command
from alembic.config import Config

from kojihub.migrations import ALEMBIC_INI


def get_config(args):
    """Build an Alembic Config from parsed command line arguments"""
    x_args = []
    if args.config:
        x_args.append('config=' + args.config)
    if args.config_dir:
        x_args.append('config_dir=' + args.config_dir)
    cfg = Config(ALEMBIC_INI, cmd_opts=argparse.Namespace(x=x_args))
    if args.url:
        # escape percent signs for configparser interpolation
        cfg.set_main_option('sqlalchemy.url', args.url.replace('%', '%%'))
    return cfg


def get_parser():
    parser = argparse.ArgumentParser(
        prog='koji-hub-migrate',
        description='Manage Koji hub database schema migrations (Alembic). '
                    'The database connection is read from the hub config '
                    '(/etc/koji-hub/hub.conf by default).')
    parser.add_argument('--config', metavar='FILE',
                        help='hub config file (default: $KOJI_HUB_CONFIG '
                             'or /etc/koji-hub/hub.conf)')
    parser.add_argument('--config-dir', metavar='DIR',
                        help='hub config directory (default: $KOJI_HUB_CONFIG_DIR '
                             'or /etc/koji-hub/hub.conf.d)')
    parser.add_argument('--url', metavar='URL',
                        help='explicit SQLAlchemy database URL, e.g. '
                             'postgresql+psycopg2://user:pass@host/dbname '
                             '(overrides the hub config)')
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('upgrade', help='apply migrations (default: up to head)')
    p.add_argument('revision', nargs='?', default='head')
    p.add_argument('--sql', action='store_true',
                   help='emit SQL to stdout instead of running it')

    p = sub.add_parser('downgrade', help='revert migrations')
    p.add_argument('revision')
    p.add_argument('--sql', action='store_true',
                   help='emit SQL to stdout instead of running it')

    p = sub.add_parser('stamp', help='mark the database as being at a revision '
                       'without running migrations (e.g. "stamp head" for a '
                       'database already created from schemas/schema.sql)')
    p.add_argument('revision')

    sub.add_parser('current', help='show the current revision of the database')
    sub.add_parser('history', help='list available migrations')
    sub.add_parser('heads', help='show the latest available revisions')
    sub.add_parser('check', help='check if there are pending migrations')
    return parser


def main(argv=None):
    parser = get_parser()
    args = parser.parse_args(argv)
    cfg = get_config(args)

    if args.command == 'upgrade':
        command.upgrade(cfg, args.revision, sql=args.sql)
    elif args.command == 'downgrade':
        command.downgrade(cfg, args.revision, sql=args.sql)
    elif args.command == 'stamp':
        command.stamp(cfg, args.revision)
    elif args.command == 'current':
        command.current(cfg, verbose=True)
    elif args.command == 'history':
        command.history(cfg, verbose=True)
    elif args.command == 'heads':
        command.heads(cfg, verbose=True)
    elif args.command == 'check':
        command.check(cfg)
    return 0
