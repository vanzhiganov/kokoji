# Builds, buildroots and related tables

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


class Package(Base):
    __tablename__ = 'package'

    # by package, we mean srpm: the package in general, not an individual build
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)


class Volume(Base):
    __tablename__ = 'volume'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)


class ContentGenerator(Base):
    __tablename__ = 'content_generator'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)


class Build(Base):
    __tablename__ = 'build'
    __table_args__ = (
        UniqueConstraint('pkg_id', 'version', 'release', name='build_pkg_ver_rel'),
        # required by constraint rpminfo_build_id_draft_fkey on table rpminfo
        UniqueConstraint('id', 'draft', name='draft_for_rpminfo'),
        CheckConstraint('(state = 0 AND completion_time IS NULL) OR '
                        '(state <> 0 AND completion_time IS NOT NULL)',
                        name='completion_sane'),
        CheckConstraint('NOT draft OR (promotion_time IS NULL AND promoter IS NULL)',
                        name='promotion_sane'),
        CheckConstraint("NOT draft OR release ~ ('^.*,draft_' || id::TEXT || '$')",
                        name='draft_release_sane'),
        Index('build_by_pkg_id', 'pkg_id'),
        Index('build_completion', 'completion_time'),
    )

    # builds are tracked at the srpm level; even though we track epoch,
    # we demand that N-V-R be unique
    id = mapped_column(Integer, primary_key=True)
    volume_id = mapped_column(Integer, ForeignKey('volume.id'), nullable=False)
    pkg_id = mapped_column(Integer, ForeignKey('package.id', deferrable=True),
                           nullable=False)
    version = mapped_column(Text, nullable=False)
    release = mapped_column(Text, nullable=False)
    epoch = mapped_column(Integer)
    draft = mapped_column(Boolean, nullable=False, server_default=text('false'))
    source = mapped_column(Text)
    create_event = mapped_column(Integer, ForeignKey('events.id'),
                                 nullable=False, server_default=text('get_event()'))
    start_time = mapped_column(TIMESTAMPTZ)
    completion_time = mapped_column(TIMESTAMPTZ)
    promotion_time = mapped_column(TIMESTAMPTZ)
    state = mapped_column(Integer, nullable=False)
    # may be null, or may point to a deleted task
    task_id = mapped_column(Integer, ForeignKey('task.id'))
    owner = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    promoter = mapped_column(Integer, ForeignKey('users.id'))
    cg_id = mapped_column(Integer, ForeignKey('content_generator.id'))
    extra = mapped_column(Text)


class Btype(Base):
    __tablename__ = 'btype'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)


class BuildType(Base):
    __tablename__ = 'build_types'
    __table_args__ = (
        PrimaryKeyConstraint('build_id', 'btype_id'),
    )

    build_id = mapped_column(Integer, ForeignKey('build.id'), nullable=False)
    btype_id = mapped_column(Integer, ForeignKey('btype.id'), nullable=False)


class CgUser(Versioned, Base):
    __tablename__ = 'cg_users'
    __table_args__ = versioned_checks('cg_users') + (
        PrimaryKeyConstraint('create_event', 'cg_id', 'user_id'),
        UniqueConstraint('cg_id', 'user_id', 'active'),
    )

    cg_id = mapped_column(Integer, ForeignKey('content_generator.id'), nullable=False)
    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)


class BuildReservation(Base):
    __tablename__ = 'build_reservations'
    __table_args__ = (
        PrimaryKeyConstraint('build_id'),
        Index('build_reservations_created', 'created'),
    )

    build_id = mapped_column(Integer, ForeignKey('build.id'), nullable=False)
    token = mapped_column(String(64))
    created = mapped_column(TIMESTAMPTZ, nullable=False)


class Buildroot(Base):
    __tablename__ = 'buildroot'
    __table_args__ = (
        CheckConstraint('(cg_id IS NULL AND cg_version IS NULL) OR '
                        '(cg_id IS NOT NULL AND cg_version IS NOT NULL)',
                        name='cg_sane'),
        CheckConstraint('(container_type IS NULL AND container_arch IS NULL) OR '
                        '(container_type IS NOT NULL AND container_arch IS NOT NULL)',
                        name='container_sane'),
    )

    id = mapped_column(Integer, primary_key=True)
    br_type = mapped_column(Integer, nullable=False)
    cg_id = mapped_column(Integer, ForeignKey('content_generator.id'))
    cg_version = mapped_column(Text)
    container_type = mapped_column(Text)
    container_arch = mapped_column(Text)
    host_os = mapped_column(Text)
    host_arch = mapped_column(Text)
    extra = mapped_column(Text)


class StandardBuildroot(Base):
    __tablename__ = 'standard_buildroot'

    buildroot_id = mapped_column(Integer, ForeignKey('buildroot.id'),
                                 primary_key=True, nullable=False)
    host_id = mapped_column(Integer, ForeignKey('host.id'), nullable=False)
    repo_id = mapped_column(Integer, ForeignKey('repo.id'), nullable=False)
    task_id = mapped_column(Integer, ForeignKey('task.id'), nullable=False)
    create_event = mapped_column(Integer, ForeignKey('events.id'),
                                 nullable=False, server_default=text('get_event()'))
    retire_event = mapped_column(Integer)
    state = mapped_column(Integer)


class BuildrootToolsInfo(Base):
    __tablename__ = 'buildroot_tools_info'
    __table_args__ = (
        PrimaryKeyConstraint('buildroot_id', 'tool'),
    )

    buildroot_id = mapped_column(Integer, ForeignKey('buildroot.id'), nullable=False)
    tool = mapped_column(Text, nullable=False)
    version = mapped_column(Text, nullable=False)


class ImageBuild(Base):
    __tablename__ = 'image_builds'

    # tracks spun images (livecds, installation, VMs...)
    build_id = mapped_column(Integer, ForeignKey('build.id'),
                             primary_key=True, nullable=False)


class MavenBuild(Base):
    __tablename__ = 'maven_builds'

    build_id = mapped_column(Integer, ForeignKey('build.id'),
                             primary_key=True, nullable=False)
    group_id = mapped_column(Text, nullable=False)
    artifact_id = mapped_column(Text, nullable=False)
    version = mapped_column(Text, nullable=False)


class WinBuild(Base):
    __tablename__ = 'win_builds'

    build_id = mapped_column(Integer, ForeignKey('build.id'),
                             primary_key=True, nullable=False)
    platform = mapped_column(Text, nullable=False)


class BuildNotification(Base):
    __tablename__ = 'build_notifications'

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    package_id = mapped_column(Integer, ForeignKey('package.id'))
    tag_id = mapped_column(Integer, ForeignKey('tag.id'))
    success_only = mapped_column(Boolean, nullable=False, server_default=text('false'))
    email = mapped_column(Text, nullable=False)


class BuildNotificationBlock(Base):
    __tablename__ = 'build_notifications_block'

    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    package_id = mapped_column(Integer, ForeignKey('package.id'))
    tag_id = mapped_column(Integer, ForeignKey('tag.id'))
