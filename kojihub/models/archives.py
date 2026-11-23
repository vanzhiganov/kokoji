# Archives and archive types

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import mapped_column

from .base import Base


class ArchiveType(Base):
    __tablename__ = 'archivetypes'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)
    description = mapped_column(Text, nullable=False)
    extensions = mapped_column(Text, nullable=False)
    compression_type = mapped_column(Text)


class ArchiveInfo(Base):
    __tablename__ = 'archiveinfo'
    __table_args__ = (
        Index('archiveinfo_build_idx', 'build_id'),
        Index('archiveinfo_buildroot_idx', 'buildroot_id'),
        Index('archiveinfo_type_idx', 'type_id'),
        Index('archiveinfo_filename_idx', 'filename'),
    )

    # despite the name, this can be used for any filetype output by a
    # build process (archives, installer executables, ...)
    id = mapped_column(Integer, primary_key=True)
    type_id = mapped_column(Integer, ForeignKey('archivetypes.id'), nullable=False)
    btype_id = mapped_column(Integer, ForeignKey('btype.id'))
    build_id = mapped_column(Integer, ForeignKey('build.id'), nullable=False)
    buildroot_id = mapped_column(Integer, ForeignKey('buildroot.id'))
    filename = mapped_column(Text, nullable=False)
    size = mapped_column(BigInteger, nullable=False)
    checksum = mapped_column(Text, nullable=False)
    checksum_type = mapped_column(Integer, nullable=False)
    metadata_only = mapped_column(Boolean, nullable=False, server_default=text('false'))
    extra = mapped_column(Text)


class MavenArchive(Base):
    __tablename__ = 'maven_archives'

    archive_id = mapped_column(Integer, ForeignKey('archiveinfo.id'),
                               primary_key=True, nullable=False)
    group_id = mapped_column(Text, nullable=False)
    artifact_id = mapped_column(Text, nullable=False)
    version = mapped_column(Text, nullable=False)


class ImageArchive(Base):
    __tablename__ = 'image_archives'

    archive_id = mapped_column(Integer, ForeignKey('archiveinfo.id'),
                               primary_key=True, nullable=False)
    arch = mapped_column(String(16), nullable=False)


class ArchiveRpmComponent(Base):
    __tablename__ = 'archive_rpm_components'
    # the table has no primary key in the schema; use the unique
    # (archive_id, rpm_id) pair as the ORM identity
    __mapper_args__ = {'primary_key': ['archive_id', 'rpm_id']}
    __table_args__ = (
        UniqueConstraint('archive_id', 'rpm_id'),
        Index('rpm_components_idx', 'rpm_id'),
    )

    # tracks the rpm contents of an image or other archive
    archive_id = mapped_column(Integer, ForeignKey('archiveinfo.id'), nullable=False)
    rpm_id = mapped_column(Integer, ForeignKey('rpminfo.id'), nullable=False)


class ArchiveComponent(Base):
    __tablename__ = 'archive_components'
    # the table has no primary key in the schema; use the unique
    # (archive_id, component_id) pair as the ORM identity
    __mapper_args__ = {'primary_key': ['archive_id', 'component_id']}
    __table_args__ = (
        UniqueConstraint('archive_id', 'component_id'),
        Index('archive_components_idx', 'component_id'),
    )

    # tracks the archive contents of an image or other archive
    archive_id = mapped_column(Integer, ForeignKey('archiveinfo.id'), nullable=False)
    component_id = mapped_column(Integer, ForeignKey('archiveinfo.id'), nullable=False)


class BuildrootArchive(Base):
    __tablename__ = 'buildroot_archives'
    __table_args__ = (
        PrimaryKeyConstraint('buildroot_id', 'archive_id'),
        Index('buildroot_archives_archive_idx', 'archive_id'),
    )

    buildroot_id = mapped_column(Integer, ForeignKey('buildroot.id'), nullable=False)
    archive_id = mapped_column(Integer, ForeignKey('archiveinfo.id'), nullable=False)
    project_dep = mapped_column(Boolean, nullable=False)


class WinArchive(Base):
    __tablename__ = 'win_archives'

    # extended information about files built in Windows VMs
    archive_id = mapped_column(Integer, ForeignKey('archiveinfo.id'),
                               primary_key=True, nullable=False)
    relpath = mapped_column(Text, nullable=False)
    platforms = mapped_column(Text, nullable=False)
    flags = mapped_column(Text)
