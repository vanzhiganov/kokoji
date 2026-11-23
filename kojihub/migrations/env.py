# Alembic environment for the Koji hub database.
#
# The database URL is taken from the hub configuration files (the same
# ones kojihub itself uses), unless overridden with -x url=... or set
# explicitly as sqlalchemy.url in alembic.ini.

from alembic import context
from sqlalchemy import create_engine

from kojihub.migrations.config import get_db_url
from kojihub.models import metadata

config = context.config

if not config.get_main_option('sqlalchemy.url'):
    x_args = context.get_x_argument(as_dictionary=True)
    url = x_args.get('url')
    if not url:
        url = get_db_url(config_file=x_args.get('config'),
                         config_dir=x_args.get('config_dir'))
    # escape percent signs for configparser interpolation
    config.set_main_option('sqlalchemy.url', url.replace('%', '%%'))

target_metadata = metadata


def include_object(obj, name, type_, reflected, compare_to):
    # never consider alembic's own version table
    if type_ == 'table' and name == 'alembic_version':
        return False
    # Alembic cannot compare text-based expression indexes reliably:
    # PostgreSQL reflects the expression with casts and extra parentheses
    # while the model uses the original text, which produces a spurious
    # remove/add diff.  Changes to this index must be written by hand.
    if type_ == 'index' and name == 'rpminfo_filename':
        return False
    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode (--sql): emit SQL to stdout"""
    context.configure(
        url=config.get_main_option('sqlalchemy.url'),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode: against a live database"""
    connectable = create_engine(config.get_main_option('sqlalchemy.url'))

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
