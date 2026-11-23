# Scheduler tables

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from .base import Base, TIMESTAMPTZ


class SchedulerTaskRun(Base):
    __tablename__ = 'scheduler_task_runs'
    __table_args__ = (
        Index('scheduler_task_runs_task', 'task_id'),
        Index('scheduler_task_runs_host', 'host_id'),
        Index('scheduler_task_runs_create_time', 'create_time'),
    )

    id = mapped_column(Integer, primary_key=True)
    task_id = mapped_column(Integer, ForeignKey('task.id'), nullable=False)
    host_id = mapped_column(Integer, ForeignKey('host.id'), nullable=False)
    active = mapped_column(Boolean, nullable=False, server_default=text('true'))
    create_time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))


class SchedulerHostData(Base):
    __tablename__ = 'scheduler_host_data'

    host_id = mapped_column(Integer, ForeignKey('host.id'),
                            primary_key=True, nullable=False)
    data = mapped_column(JSONB)


class SchedulerSysData(Base):
    __tablename__ = 'scheduler_sys_data'

    name = mapped_column(Text, primary_key=True, nullable=False)
    data = mapped_column(JSONB)


class SchedulerTaskRefusal(Base):
    __tablename__ = 'scheduler_task_refusals'
    __table_args__ = (
        UniqueConstraint('task_id', 'host_id'),
    )

    id = mapped_column(Integer, primary_key=True)
    task_id = mapped_column(Integer, ForeignKey('task.id'), nullable=False)
    host_id = mapped_column(Integer, ForeignKey('host.id'), nullable=False)
    by_host = mapped_column(Boolean, nullable=False)
    soft = mapped_column(Boolean, nullable=False, server_default=text('false'))
    msg = mapped_column(Text)
    time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))


class SchedulerLogMessage(Base):
    __tablename__ = 'scheduler_log_messages'

    id = mapped_column(Integer, primary_key=True)
    task_id = mapped_column(Integer, ForeignKey('task.id'))
    host_id = mapped_column(Integer, ForeignKey('host.id'))
    msg_time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))
    msg = mapped_column(Text, nullable=False)
