# Repos and external repos

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Text,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from .base import Base, TIMESTAMPTZ, Versioned, versioned_checks


class Repo(Base):
    __tablename__ = 'repo'

    id = mapped_column(Integer, primary_key=True)
    # creation_time is the time that the repo entry was created;
    # create_event is the event that the repo was created *from*
    creation_time = mapped_column(TIMESTAMPTZ, server_default=text('now()'))
    create_event = mapped_column(Integer, ForeignKey('events.id'),
                                 nullable=False, server_default=text('get_event()'))
    # state_time is changed when the repo changes state
    state_time = mapped_column(TIMESTAMPTZ, server_default=text('now()'))
    # begin_event/end_event are the event boundaries where the repo
    # matches its tag
    begin_event = mapped_column(Integer, ForeignKey('events.id'))
    end_event = mapped_column(Integer, ForeignKey('events.id'))
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    state = mapped_column(Integer)
    dist = mapped_column(Boolean, server_default=text('false'))
    opts = mapped_column(JSONB)
    custom_opts = mapped_column(JSONB)
    task_id = mapped_column(Integer, ForeignKey('task.id'))


class RepoQueue(Base):
    __tablename__ = 'repo_queue'
    __table_args__ = (
        CheckConstraint('at_event IS NULL OR min_event IS NULL',
                        name='only_one_event'),
        # active requests shouldn't already have a repo_id
        CheckConstraint('NOT active OR repo_id IS NULL', name='active_sane'),
    )

    id = mapped_column(Integer, primary_key=True)
    create_time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))
    owner = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    priority = mapped_column(Integer, nullable=False)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    at_event = mapped_column(Integer, ForeignKey('events.id'))
    min_event = mapped_column(Integer, ForeignKey('events.id'))
    opts = mapped_column(JSONB, nullable=False)
    update_time = mapped_column(TIMESTAMPTZ, nullable=False, server_default=text('now()'))
    active = mapped_column(Boolean, nullable=False, server_default=text('true'))
    task_id = mapped_column(Integer, ForeignKey('task.id'))
    tries = mapped_column(Integer, nullable=False, server_default=text('0'))
    repo_id = mapped_column(Integer, ForeignKey('repo.id'))


class ExternalRepo(Base):
    __tablename__ = 'external_repo'

    # external yum repos
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)


class ExternalRepoConfig(Versioned, Base):
    __tablename__ = 'external_repo_config'
    __table_args__ = versioned_checks('external_repo_config') + (
        PrimaryKeyConstraint('create_event', 'external_repo_id'),
        UniqueConstraint('external_repo_id', 'active'),
    )

    external_repo_id = mapped_column(Integer, ForeignKey('external_repo.id'),
                                     nullable=False)
    url = mapped_column(Text, nullable=False)


class ExternalRepoData(Versioned, Base):
    __tablename__ = 'external_repo_data'
    __table_args__ = versioned_checks('external_repo_data') + (
        PrimaryKeyConstraint('create_event', 'external_repo_id'),
        UniqueConstraint('external_repo_id', 'active'),
    )

    # kojira uses this table to record info about external repos
    external_repo_id = mapped_column(Integer, ForeignKey('external_repo.id'),
                                     nullable=False)
    data = mapped_column(JSONB)
