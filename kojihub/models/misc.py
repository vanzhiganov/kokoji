# Miscellaneous tables

from sqlalchemy import Integer, Text, text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import mapped_column

from .base import Base, TIMESTAMPTZ


class ProtonQueue(Base):
    __tablename__ = 'proton_queue'

    # message queue for the protonmsg plugin
    id = mapped_column(Integer, primary_key=True)
    created_ts = mapped_column(TIMESTAMPTZ, server_default=text('now()'))
    address = mapped_column(Text, nullable=False)
    props = mapped_column(JSON, nullable=False)
    body = mapped_column(JSON, nullable=False)


class Lock(Base):
    __tablename__ = 'locks'

    # this table is used for locking, see kojihub.db.db_lock()
    name = mapped_column(Text, primary_key=True, nullable=False)
