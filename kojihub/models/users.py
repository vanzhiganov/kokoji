# Events, users, permissions and sessions

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.orm import mapped_column

from .base import Base, TIMESTAMPTZ, Versioned, versioned_checks


class Event(Base):
    __tablename__ = 'events'

    # We use the events table to sequence time in the event that the system
    # clock rolls back; event_ids will retain proper sequencing.
    id = mapped_column(Integer, primary_key=True)
    time = mapped_column(TIMESTAMPTZ, nullable=False,
                         server_default=text('clock_timestamp()'))


class EventLabel(Base):
    __tablename__ = 'event_labels'
    # the table has no primary key in the schema; use the unique label
    # as the ORM identity
    __mapper_args__ = {'primary_key': ['event_id', 'label']}

    # most events will be unlabeled, so keeping this separate saves space
    event_id = mapped_column(Integer, ForeignKey('events.id'), nullable=False)
    label = mapped_column(String(255), unique=True, nullable=False)


class User(Base):
    __tablename__ = 'users'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(255), unique=True, nullable=False)
    password = mapped_column(String(255))
    status = mapped_column(Integer, nullable=False)
    usertype = mapped_column(Integer, nullable=False)


class Permission(Base):
    __tablename__ = 'permissions'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(50), unique=True, nullable=False)
    description = mapped_column(Text)


class UserPerm(Versioned, Base):
    __tablename__ = 'user_perms'
    __table_args__ = versioned_checks('user_perms') + (
        PrimaryKeyConstraint('create_event', 'user_id', 'perm_id'),
        UniqueConstraint('user_id', 'perm_id', 'active'),
    )

    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    perm_id = mapped_column(Integer, ForeignKey('permissions.id'), nullable=False)


class UserGroup(Versioned, Base):
    __tablename__ = 'user_groups'
    __table_args__ = versioned_checks('user_groups') + (
        PrimaryKeyConstraint('create_event', 'user_id', 'group_id'),
        UniqueConstraint('user_id', 'group_id', 'active'),
    )

    # groups are represented as users w/ usertype=2
    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    group_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)


class Session(Base):
    __tablename__ = 'sessions'
    __table_args__ = (
        CheckConstraint('exclusive', name='sessions_exclusive_check'),
        CheckConstraint('master IS NULL OR "exclusive" IS NULL',
                        name='no_exclusive_subsessions'),
        CheckConstraint('closed IS FALSE OR "exclusive" IS NULL',
                        name='no_closed_exclusive'),
        UniqueConstraint('user_id', 'exclusive'),
        Index('sessions_master', 'master'),
        Index('sessions_active_and_recent', 'expired', 'master', 'update_time',
              postgresql_where=text('expired = FALSE AND master IS NULL')),
        Index('sessions_expired', 'expired'),
    )

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    expired = mapped_column(Boolean, nullable=False, server_default=text('false'))
    # a subsession's master always points to the top session
    master = mapped_column(Integer, ForeignKey('sessions.id'))
    key = mapped_column(String(255))
    authtype = mapped_column(Integer)
    hostip = mapped_column(String(255))
    callnum = mapped_column(Integer)
    start_time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))
    update_time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))
    # exclusive is either NULL or TRUE, never FALSE, so that exclusivity
    # can be enforced with a unique condition
    exclusive = mapped_column(Boolean)
    closed = mapped_column(Boolean, nullable=False, server_default=text('false'))
    renew_time = mapped_column(TIMESTAMPTZ)
