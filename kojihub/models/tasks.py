# Tasks

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.orm import mapped_column

from .base import Base, TIMESTAMPTZ


class Task(Base):
    __tablename__ = 'task'
    __table_args__ = (
        CheckConstraint('NOT weight < 0', name='task_weight_check'),
        CheckConstraint('parent IS NOT NULL OR label IS NULL',
                        name='parent_label_sane'),
        UniqueConstraint('parent', 'label'),
        Index('task_by_state', 'state'),
        Index('task_by_host', 'host_id'),
        Index('task_by_no_parent_state_method', 'parent', 'state', 'method',
              postgresql_where=text('parent IS NULL')),
    )

    # tasks may spawn subtasks (hence the parent field); top-level tasks
    # have NULL parent.  The request and result fields are xmlrpc data.
    id = mapped_column(Integer, primary_key=True)
    state = mapped_column(Integer)
    create_time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))
    start_time = mapped_column(TIMESTAMPTZ)
    completion_time = mapped_column(TIMESTAMPTZ)
    channel_id = mapped_column(Integer, ForeignKey('channels.id'), nullable=False)
    # the host running the task; used to lock the task
    host_id = mapped_column(Integer, ForeignKey('host.id'))
    parent = mapped_column(Integer, ForeignKey('task.id'))
    # labels are used in task failover to prevent duplication of work
    label = mapped_column(String(255))
    waiting = mapped_column(Boolean)
    awaited = mapped_column(Boolean)
    owner = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    method = mapped_column(Text)
    request = mapped_column(Text)
    result = mapped_column(Text)
    eta = mapped_column(Integer)
    arch = mapped_column(String(16), nullable=False)
    priority = mapped_column(Integer)
    weight = mapped_column(Float, nullable=False, server_default=text('1.0'))
