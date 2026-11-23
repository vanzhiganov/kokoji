"""Integration tests for hub database migrations against a real PostgreSQL.

These tests are skipped unless a PostgreSQL server is available:
  * set KOJI_TEST_DB_URL to a server URL, e.g.
    postgresql+psycopg2://koji:koji@localhost/koji
    (test databases are created and dropped on that server), or
  * have podman or docker available: a disposable postgres:16-alpine
    container is started automatically.
"""

import os
import shutil
import socket
import subprocess
import time
import uuid

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from kojihub.migrations import cli
from kojihub.models import metadata

SCHEMA_SQL = os.path.join(os.path.dirname(__file__),
                          '../../../schemas/schema.sql')
BASELINE = '0001_baseline'


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == 'table' and name == 'alembic_version':
        return False
    # Alembic cannot compare this text-based expression index reliably
    # (see kojihub.migrations.env.include_object)
    if type_ == 'index' and name == 'rpminfo_filename':
        return False
    return True


def find_free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def wait_ready(url, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            engine = sa.create_engine(url)
            with engine.connect() as conn:
                conn.execute(sa.text('SELECT 1'))
            engine.dispose()
            return
        except sa.exc.OperationalError:
            time.sleep(1)
    raise RuntimeError('PostgreSQL did not become ready in time')


@pytest.fixture(scope='session')
def pg_server():
    url = os.environ.get('KOJI_TEST_DB_URL')
    if url:
        yield url
        return

    tool = None
    for cand in ('podman', 'docker'):
        if shutil.which(cand):
            proc = subprocess.run([cand, 'info'], capture_output=True, timeout=60)
            if proc.returncode == 0:
                tool = cand
                break
    if tool is None:
        pytest.skip('no PostgreSQL available: set KOJI_TEST_DB_URL '
                    'or make podman/docker usable')

    name = f'koji-migrate-test-{os.getpid()}-{uuid.uuid4().hex[:8]}'
    port = find_free_port()
    subprocess.run(
        [tool, 'run', '-d', '--name', name,
         '-e', 'POSTGRES_USER=koji', '-e', 'POSTGRES_PASSWORD=koji',
         '-e', 'POSTGRES_DB=koji',
         '-p', f'127.0.0.1:{port}:5432',
         'docker.io/library/postgres:16-alpine'],
        check=True, capture_output=True)
    url = f'postgresql+psycopg2://koji:koji@127.0.0.1:{port}/koji'
    try:
        wait_ready(url)
        yield url
    finally:
        subprocess.run([tool, 'rm', '-f', name], capture_output=True)


@pytest.fixture
def db_url(pg_server):
    admin = sa.create_engine(pg_server, isolation_level='AUTOCOMMIT')
    dbname = 'koji_test_' + uuid.uuid4().hex[:12]
    with admin.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE {dbname}'))
    url = admin.url.set(database=dbname).render_as_string(hide_password=False)
    try:
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(sa.text(f'DROP DATABASE IF EXISTS {dbname} WITH (FORCE)'))
        admin.dispose()


def migrate(db_url, *args):
    assert cli.main(['--url', db_url] + list(args)) == 0


def load_schema_sql(db_url):
    """Create the schema the legacy way, from schemas/schema.sql"""
    with open(SCHEMA_SQL) as f:
        sql = f.read()
    engine = sa.create_engine(db_url)
    raw = engine.raw_connection()
    try:
        import psycopg2.extensions
        raw.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = raw.cursor()
        cursor.execute(sql)
        cursor.close()
    finally:
        raw.close()
        engine.dispose()


def get_diff(db_url):
    """Alembic autogenerate diff between the database and the models"""
    engine = sa.create_engine(db_url)
    try:
        with engine.connect() as conn:
            mc = MigrationContext.configure(conn, opts={
                'compare_type': True,
                'include_object': include_object,
            })
            return compare_metadata(mc, metadata)
    finally:
        engine.dispose()


def table_names(db_url):
    engine = sa.create_engine(db_url)
    try:
        return set(sa.inspect(engine).get_table_names())
    finally:
        engine.dispose()


def schema_snapshot(db_url):
    """Normalized reflection of the database schema for comparison"""
    engine = sa.create_engine(db_url)
    try:
        md = sa.MetaData()
        md.reflect(engine)
    finally:
        engine.dispose()
    snap = {}
    for name, table in md.tables.items():
        if name == 'alembic_version':
            continue
        columns = {}
        for col in table.columns:
            default = col.server_default
            default = str(default.arg).strip() if default is not None else None
            columns[col.name] = (str(col.type), col.nullable, default)
        constraints = []
        for con in table.constraints:
            if isinstance(con, sa.PrimaryKeyConstraint):
                constraints.append(('pk', sorted(c.name for c in con.columns)))
            elif isinstance(con, sa.UniqueConstraint):
                constraints.append(('uq', con.name, sorted(c.name for c in con.columns)))
            elif isinstance(con, sa.ForeignKeyConstraint):
                constraints.append(('fk', con.name,
                                    sorted(e.parent.name for e in con.elements),
                                    sorted(f'{e.column.table.name}.{e.column.name}'
                                           for e in con.elements),
                                    con.onupdate, con.ondelete,
                                    con.deferrable, con.initially))
            elif isinstance(con, sa.CheckConstraint):
                constraints.append(('ck', con.name, str(con.sqltext)))
        indexes = []
        for idx in table.indexes:
            exprs = [str(c) if not hasattr(c, 'name') or c.name is None else c.name
                     for c in idx.expressions]
            where = idx.dialect_options['postgresql'].get('where')
            indexes.append((idx.name, tuple(exprs), idx.unique,
                            str(where) if where is not None else None))
        snap[name] = {
            'columns': columns,
            'constraints': sorted(constraints, key=repr),
            'indexes': sorted(indexes, key=repr),
        }
    return snap


class TestMigrations:

    def test_upgrade_head(self, db_url):
        migrate(db_url, 'upgrade', 'head')
        tables = table_names(db_url)
        assert set(metadata.tables) <= tables
        assert 'alembic_version' in tables

        engine = sa.create_engine(db_url)
        try:
            with engine.connect() as conn:
                # versioning functions
                event_id = conn.execute(sa.text('SELECT get_event()')).scalar()
                assert isinstance(event_id, int)
                ts = conn.execute(sa.text('SELECT get_event_time(:id)'),
                                  {'id': event_id}).scalar()
                assert ts is not None
                # initial data
                counts = {
                    'permissions': 15,
                    'channels': 8,
                    'btype': 4,
                    'archivetypes': 71,
                    'locks': 3,
                }
                for table, count in counts.items():
                    n = conn.execute(sa.text(f'SELECT count(*) FROM {table}')).scalar()
                    assert n == count, table
                assert conn.execute(sa.text(
                    "SELECT name FROM volume WHERE id = 0")).scalar() == 'DEFAULT'
                assert conn.execute(sa.text(
                    "SELECT name FROM external_repo WHERE id = 0")).scalar() == 'INTERNAL'
                # sequences behind SERIAL columns work
                uid = conn.execute(sa.text(
                    "INSERT INTO users (name, status, usertype) "
                    "VALUES ('testuser', 0, 0) RETURNING id")).scalar()
                assert uid >= 1
        finally:
            engine.dispose()

        # no pending migrations, and no schema drift
        migrate(db_url, 'check')
        assert get_diff(db_url) == []

    def test_stamp_existing_schema(self, db_url):
        load_schema_sql(db_url)
        migrate(db_url, 'stamp', 'head')
        migrate(db_url, 'check')
        # the models must match the legacy schema exactly
        assert get_diff(db_url) == []

    def test_migrated_matches_schema_sql(self, db_url, pg_server):
        # a second database created the legacy way
        admin = sa.create_engine(pg_server, isolation_level='AUTOCOMMIT')
        other = 'koji_test_' + uuid.uuid4().hex[:12]
        with admin.connect() as conn:
            conn.execute(sa.text(f'CREATE DATABASE {other}'))
        other_url = admin.url.set(database=other).render_as_string(hide_password=False)
        try:
            load_schema_sql(other_url)
            migrate(db_url, 'upgrade', 'head')
            assert schema_snapshot(db_url) == schema_snapshot(other_url)
        finally:
            with admin.connect() as conn:
                conn.execute(sa.text(f'DROP DATABASE IF EXISTS {other} WITH (FORCE)'))
            admin.dispose()

    def test_downgrade_base(self, db_url):
        migrate(db_url, 'upgrade', 'head')
        migrate(db_url, 'downgrade', 'base')
        assert table_names(db_url) == {'alembic_version'}
        engine = sa.create_engine(db_url)
        try:
            with engine.connect() as conn:
                n = conn.execute(sa.text(
                    "SELECT count(*) FROM pg_proc WHERE proname IN "
                    "('get_event', 'get_event_time')")).scalar()
                assert n == 0
        finally:
            engine.dispose()
        # and back up again
        migrate(db_url, 'upgrade', 'head')
        assert set(metadata.tables) <= table_names(db_url)
