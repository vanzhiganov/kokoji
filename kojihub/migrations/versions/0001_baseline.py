"""Baseline: Koji hub schema version 1.36

Creates the full Koji hub schema, equivalent to schemas/schema.sql
(including the get_event()/get_event_time() functions, initial data
and public read grants).

Databases that were already created from schemas/schema.sql must NOT
run this migration; mark them as up-to-date instead:

    koji-hub-migrate stamp head

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-23

"""
from alembic import op
from sqlalchemy.schema import CreateIndex, CreateTable, DropTable

from kojihub.migrations import seed_data
from kojihub.models import metadata

# revision identifiers, used by Alembic.
revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None

# Functions used as column defaults and for event/time conversion.
# Kept as raw SQL: they are PostgreSQL-specific and not part of the
# table metadata.
FUNCTIONS_SQL = """
CREATE FUNCTION get_event() RETURNS INTEGER AS '
    INSERT INTO events (time) VALUES (clock_timestamp());
    SELECT currval(''events_id_seq'')::INTEGER;
' LANGUAGE SQL;

CREATE FUNCTION get_event_time(INTEGER) RETURNS TIMESTAMPTZ AS '
    SELECT time FROM events WHERE id=$1;
' LANGUAGE SQL;
"""

GRANTS_SQL = (
    "GRANT SELECT ON build, package, task, tag, "
    "tag_listing, tag_config, tag_inheritance, tag_packages, "
    "rpminfo TO PUBLIC"
)


def upgrade():
    # mirrors schemas/schema.sql: the events table comes first, then the
    # functions (whose SQL bodies reference events), then the remaining
    # tables (whose defaults reference get_event())
    op.execute(CreateTable(metadata.tables['events']))
    op.execute(FUNCTIONS_SQL)
    for table in metadata.sorted_tables:
        if table.name != 'events':
            op.execute(CreateTable(table))
    for table in metadata.sorted_tables:
        for index in sorted(table.indexes, key=lambda i: i.name):
            op.execute(CreateIndex(index))
    seed_data.insert_all()
    op.execute(GRANTS_SQL)


def downgrade():
    for table in reversed(metadata.sorted_tables):
        op.execute(DropTable(table))
    op.execute('DROP FUNCTION IF EXISTS get_event_time(integer)')
    op.execute('DROP FUNCTION IF EXISTS get_event()')
