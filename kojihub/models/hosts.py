# Builder channels and hosts

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
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


class Channel(Base):
    __tablename__ = 'channels'

    # Channels are used to limit which tasks are run on which machines.
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(128), unique=True, nullable=False)
    description = mapped_column(Text)
    enabled = mapped_column(Boolean, nullable=False, server_default=text('true'))
    comment = mapped_column(Text)


class Host(Base):
    __tablename__ = 'host'
    __table_args__ = (
        CheckConstraint('NOT task_load < 0', name='host_task_load_check'),
    )

    # each host has an entry in the users table also
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    name = mapped_column(String(128), unique=True, nullable=False)
    update_time = mapped_column(TIMESTAMPTZ)
    task_load = mapped_column(Float, nullable=False, server_default=text('0.0'))
    ready = mapped_column(Boolean, nullable=False, server_default=text('false'))


class HostConfig(Versioned, Base):
    __tablename__ = 'host_config'
    __table_args__ = versioned_checks('host_config') + (
        CheckConstraint('capacity > 1', name='host_config_capacity_check'),
        PrimaryKeyConstraint('create_event', 'host_id'),
        UniqueConstraint('host_id', 'active'),
        Index('host_config_by_active_and_enabled', 'active', 'enabled'),
    )

    host_id = mapped_column(Integer, ForeignKey('host.id'), nullable=False)
    arches = mapped_column(Text)
    # capacity: the host's weighted task capacity
    capacity = mapped_column(Float, nullable=False, server_default=text('2.0'))
    description = mapped_column(Text)
    comment = mapped_column(Text)
    enabled = mapped_column(Boolean, nullable=False, server_default=text('true'))


class HostChannel(Versioned, Base):
    __tablename__ = 'host_channels'
    __table_args__ = versioned_checks('host_channels') + (
        PrimaryKeyConstraint('create_event', 'host_id', 'channel_id'),
        UniqueConstraint('host_id', 'channel_id', 'active'),
    )

    host_id = mapped_column(Integer, ForeignKey('host.id'), nullable=False)
    channel_id = mapped_column(Integer, ForeignKey('channels.id'), nullable=False)
