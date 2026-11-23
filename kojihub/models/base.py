# Declarative base and shared helpers for the Koji hub database models.
#
# The models mirror schemas/schema.sql exactly, so that Alembic autogenerate
# produces no spurious diffs against a database created from that schema.
# Constraint names follow PostgreSQL's default naming rules (see the
# naming convention below), which keeps reflected and model metadata aligned.

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, MetaData, text
from sqlalchemy.orm import DeclarativeBase, declared_attr, mapped_column

# PostgreSQL TIMESTAMP WITH TIME ZONE
TIMESTAMPTZ = DateTime(timezone=True)

# PostgreSQL default constraint naming:
#   PRIMARY KEY  -> <table>_pkey
#   UNIQUE       -> <table>_<col1>_<col2>..._key
#   FOREIGN KEY  -> <table>_<col1>_<col2>..._fkey
#   CHECK        -> <table>_<col>_check
#   INDEX        -> <table>_<col>_idx
NAMING_CONVENTION = {
    'ix': '%(table_name)s_%(column_0_name)s_idx',
    'uq': '%(table_name)s_%(column_0_N_name)s_key',
    'ck': '%(table_name)s_%(column_0_name)s_check',
    'fk': '%(table_name)s_%(column_0_N_name)s_fkey',
    'pk': '%(table_name)s_pkey',
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# The versioning scheme used by many Koji tables (see VERSIONING in
# schemas/schema.sql).  The active field is either True or NULL, never False.
ACTIVE_REVOKE_SANE = (
    '(active IS NULL AND revoke_event IS NOT NULL AND revoker_id IS NOT NULL) '
    'OR (active IS NOT NULL AND revoke_event IS NULL AND revoker_id IS NULL)'
)


def versioned_checks(table_name):
    """Common CHECK constraints for versioned tables"""
    return (
        CheckConstraint('active', name=f'{table_name}_active_check'),
        CheckConstraint(ACTIVE_REVOKE_SANE, name='active_revoke_sane'),
    )


class Versioned:
    """Mixin providing the standard versioning columns"""

    @declared_attr
    def create_event(cls):
        return mapped_column(Integer, ForeignKey('events.id'),
                             nullable=False, server_default=text('get_event()'))

    @declared_attr
    def revoke_event(cls):
        return mapped_column(Integer, ForeignKey('events.id'))

    @declared_attr
    def creator_id(cls):
        return mapped_column(Integer, ForeignKey('users.id'), nullable=False)

    @declared_attr
    def revoker_id(cls):
        return mapped_column(Integer, ForeignKey('users.id'))

    @declared_attr
    def active(cls):
        return mapped_column(Boolean, server_default=text('true'))
