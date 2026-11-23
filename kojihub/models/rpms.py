# RPM tracking

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import mapped_column

from .base import Base


class RpmInfo(Base):
    __tablename__ = 'rpminfo'
    __table_args__ = (
        # ensures the draft field is consistent with the build entry
        ForeignKeyConstraint(['build_id', 'draft'], ['build.id', 'build.draft'],
                             onupdate='CASCADE'),
        CheckConstraint('(draft IS NULL AND build_id IS NULL AND external_repo_id <> 0) '
                        'OR (draft IS NOT NULL AND build_id IS NOT NULL '
                        'AND external_repo_id = 0)',
                        name='build_id_draft_external_repo_id_sane'),
        Index('rpminfo_build', 'build_id'),
        Index('rpminfo_unique_nvra_not_draft',
              'name', 'version', 'release', 'arch', 'external_repo_id',
              unique=True, postgresql_where=text('draft IS NOT TRUE')),
        Index('rpminfo_nvra', 'name', 'version', 'release', 'arch', 'external_repo_id'),
        # index for the default search method for rpms
        Index('rpminfo_filename',
              text("(name || '-' || version || '-' || release || '.' || arch || '.rpm')"),
              postgresql_include=['id']),
    )

    # tracks individual rpms (incl srpms); buildroot_id can be NULL for
    # externally built packages.  We demand that N-V-R.A be unique for
    # non-draft builds.  Filename is not stored: it should be N-V-R.A.rpm.
    id = mapped_column(Integer, primary_key=True)
    build_id = mapped_column(Integer)
    buildroot_id = mapped_column(Integer, ForeignKey('buildroot.id'))
    name = mapped_column(Text, nullable=False)
    version = mapped_column(Text, nullable=False)
    release = mapped_column(Text, nullable=False)
    epoch = mapped_column(Integer)
    arch = mapped_column(String(16), nullable=False)
    draft = mapped_column(Boolean)
    external_repo_id = mapped_column(Integer, ForeignKey('external_repo.id'),
                                     nullable=False)
    payloadhash = mapped_column(Text, nullable=False)
    size = mapped_column(BigInteger, nullable=False)
    buildtime = mapped_column(BigInteger, nullable=False)
    metadata_only = mapped_column(Boolean, nullable=False, server_default=text('false'))
    extra = mapped_column(Text)


class RpmSig(Base):
    __tablename__ = 'rpmsigs'
    # the table has no primary key in the schema; use the unique
    # (rpm_id, sigkey) pair as the ORM identity
    __mapper_args__ = {'primary_key': ['rpm_id', 'sigkey']}
    __table_args__ = (
        UniqueConstraint('rpm_id', 'sigkey', name='rpmsigs_no_resign'),
    )

    # sighash is the checksum of the signature header
    rpm_id = mapped_column(Integer, ForeignKey('rpminfo.id'), nullable=False)
    sigkey = mapped_column(Text, nullable=False)
    sighash = mapped_column(Text, nullable=False)


class BuildrootListing(Base):
    __tablename__ = 'buildroot_listing'
    # the table has no primary key in the schema; use the unique
    # (buildroot_id, rpm_id) pair as the ORM identity
    __mapper_args__ = {'primary_key': ['buildroot_id', 'rpm_id']}
    __table_args__ = (
        UniqueConstraint('buildroot_id', 'rpm_id'),
        Index('buildroot_listing_rpms', 'rpm_id'),
    )

    buildroot_id = mapped_column(Integer, ForeignKey('buildroot.id'), nullable=False)
    rpm_id = mapped_column(Integer, ForeignKey('rpminfo.id'), nullable=False)
    is_update = mapped_column(Boolean, nullable=False, server_default=text('false'))


class RpmChecksum(Base):
    __tablename__ = 'rpm_checksum'
    __table_args__ = (
        Index('rpm_checksum_rpm_id', 'rpm_id'),
    )

    rpm_id = mapped_column(Integer, ForeignKey('rpminfo.id'),
                           primary_key=True, nullable=False)
    sigkey = mapped_column(Text, primary_key=True, nullable=False)
    checksum = mapped_column(Text, unique=True, nullable=False)
    checksum_type = mapped_column(SmallInteger, primary_key=True, nullable=False)
