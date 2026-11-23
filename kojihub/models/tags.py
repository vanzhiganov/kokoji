# Tags, targets, package lists and groups

from sqlalchemy import (
    Boolean,
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

from .base import Base, Versioned, versioned_checks


class Tag(Base):
    __tablename__ = 'tag'

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)


class TagInheritance(Versioned, Base):
    __tablename__ = 'tag_inheritance'
    __table_args__ = versioned_checks('tag_inheritance') + (
        PrimaryKeyConstraint('create_event', 'tag_id', 'priority'),
        UniqueConstraint('tag_id', 'priority', 'active'),
        UniqueConstraint('tag_id', 'parent_id', 'active'),
        Index('tag_inheritance_by_parent', 'parent_id'),
    )

    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    parent_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    priority = mapped_column(Integer, nullable=False)
    maxdepth = mapped_column(Integer)
    intransitive = mapped_column(Boolean, nullable=False, server_default=text('false'))
    noconfig = mapped_column(Boolean, nullable=False, server_default=text('false'))
    pkg_filter = mapped_column(Text)


class TagConfig(Versioned, Base):
    __tablename__ = 'tag_config'
    __table_args__ = versioned_checks('tag_config') + (
        PrimaryKeyConstraint('create_event', 'tag_id'),
        UniqueConstraint('tag_id', 'active'),
    )

    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    arches = mapped_column(Text)
    # the permission required to apply the tag; can be NULL
    perm_id = mapped_column(Integer, ForeignKey('permissions.id'))
    locked = mapped_column(Boolean, nullable=False, server_default=text('false'))
    maven_support = mapped_column(Boolean, nullable=False, server_default=text('false'))
    maven_include_all = mapped_column(Boolean, nullable=False, server_default=text('false'))


class TagExtra(Versioned, Base):
    __tablename__ = 'tag_extra'
    __table_args__ = versioned_checks('tag_extra') + (
        PrimaryKeyConstraint('create_event', 'tag_id', 'key'),
        UniqueConstraint('tag_id', 'key', 'active'),
    )

    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    key = mapped_column(Text, nullable=False)
    value = mapped_column(Text)


class TagUpdate(Base):
    __tablename__ = 'tag_updates'
    __table_args__ = (
        Index('tag_updates_by_tag', 'tag_id'),
        Index('tag_updates_by_event', 'update_event'),
    )

    # indicates changes relevant to a tag that are not reflected in a
    # versioned table (e.g. builds changing volumes, external repo content)
    id = mapped_column(Integer, primary_key=True)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    update_event = mapped_column(Integer, ForeignKey('events.id'),
                                 nullable=False, server_default=text('get_event()'))
    updater_id = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    update_type = mapped_column(Integer, nullable=False)


class BuildTarget(Base):
    __tablename__ = 'build_target'

    # a build target tells the system where to build the package
    # and how to tag it afterwards
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, unique=True, nullable=False)


class BuildTargetConfig(Versioned, Base):
    __tablename__ = 'build_target_config'
    __table_args__ = versioned_checks('build_target_config') + (
        PrimaryKeyConstraint('create_event', 'build_target_id'),
        UniqueConstraint('build_target_id', 'active'),
    )

    build_target_id = mapped_column(Integer, ForeignKey('build_target.id'),
                                    nullable=False)
    build_tag = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    dest_tag = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)


class TagListing(Versioned, Base):
    __tablename__ = 'tag_listing'
    __table_args__ = versioned_checks('tag_listing') + (
        PrimaryKeyConstraint('create_event', 'build_id', 'tag_id'),
        UniqueConstraint('build_id', 'tag_id', 'active'),
        Index('tag_listing_tag_id_key', 'tag_id'),
    )

    # an entry here tags a build
    build_id = mapped_column(Integer, ForeignKey('build.id'), nullable=False)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)


class TagPackage(Versioned, Base):
    __tablename__ = 'tag_packages'
    __table_args__ = versioned_checks('tag_packages') + (
        PrimaryKeyConstraint('create_event', 'package_id', 'tag_id'),
        UniqueConstraint('package_id', 'tag_id', 'active'),
        Index('tag_packages_active_tag_id', 'active', 'tag_id'),
        Index('tag_packages_create_event', 'create_event'),
        Index('tag_packages_revoke_event', 'revoke_event'),
    )

    # per-tag list of packages; if blocked is true, the package is
    # specifically not included (also prevents inclusion via inheritance)
    package_id = mapped_column(Integer, ForeignKey('package.id'), nullable=False)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    blocked = mapped_column(Boolean, nullable=False, server_default=text('false'))
    extra_arches = mapped_column(Text)


class TagPackageOwner(Versioned, Base):
    __tablename__ = 'tag_package_owners'
    __table_args__ = versioned_checks('tag_package_owners') + (
        PrimaryKeyConstraint('create_event', 'package_id', 'tag_id'),
        UniqueConstraint('package_id', 'tag_id', 'active'),
    )

    package_id = mapped_column(Integer, ForeignKey('package.id'), nullable=False)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    owner = mapped_column(Integer, ForeignKey('users.id'), nullable=False)


class Group(Base):
    __tablename__ = 'groups'

    # package groups (per tag), used for generating comps for the tag repos;
    # name corresponds to the id field in a comps group
    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(String(50), unique=True, nullable=False)


class GroupConfig(Versioned, Base):
    __tablename__ = 'group_config'
    __table_args__ = versioned_checks('group_config') + (
        PrimaryKeyConstraint('create_event', 'group_id', 'tag_id'),
        UniqueConstraint('group_id', 'tag_id', 'active'),
    )

    group_id = mapped_column(Integer, ForeignKey('groups.id'), nullable=False)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    blocked = mapped_column(Boolean, nullable=False, server_default=text('false'))
    exported = mapped_column(Boolean, server_default=text('true'))
    display_name = mapped_column(Text, nullable=False)
    is_default = mapped_column(Boolean)
    uservisible = mapped_column(Boolean)
    description = mapped_column(Text)
    langonly = mapped_column(Text)
    biarchonly = mapped_column(Boolean)


class GroupReqListing(Versioned, Base):
    __tablename__ = 'group_req_listing'
    __table_args__ = versioned_checks('group_req_listing') + (
        PrimaryKeyConstraint('create_event', 'group_id', 'tag_id', 'req_id'),
        UniqueConstraint('group_id', 'tag_id', 'req_id', 'active'),
    )

    group_id = mapped_column(Integer, ForeignKey('groups.id'), nullable=False)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    req_id = mapped_column(Integer, ForeignKey('groups.id'), nullable=False)
    blocked = mapped_column(Boolean, nullable=False, server_default=text('false'))
    type = mapped_column(String(25))
    is_metapkg = mapped_column(Boolean, nullable=False, server_default=text('false'))


class GroupPackageListing(Versioned, Base):
    __tablename__ = 'group_package_listing'
    __table_args__ = versioned_checks('group_package_listing') + (
        PrimaryKeyConstraint('create_event', 'group_id', 'tag_id', 'package'),
        UniqueConstraint('group_id', 'tag_id', 'package', 'active'),
    )

    group_id = mapped_column(Integer, ForeignKey('groups.id'), nullable=False)
    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    # package refers to an rpm name, not necessarily an srpm name
    # (so it does not reference the package table)
    package = mapped_column(Text, nullable=False)
    blocked = mapped_column(Boolean, nullable=False, server_default=text('false'))
    type = mapped_column(String(25), nullable=False)
    basearchonly = mapped_column(Boolean)
    requires = mapped_column(Text)


class TagExternalRepo(Versioned, Base):
    __tablename__ = 'tag_external_repos'
    __table_args__ = versioned_checks('tag_external_repos') + (
        PrimaryKeyConstraint('create_event', 'tag_id', 'priority'),
        UniqueConstraint('tag_id', 'priority', 'active'),
        UniqueConstraint('tag_id', 'external_repo_id', 'active'),
    )

    tag_id = mapped_column(Integer, ForeignKey('tag.id'), nullable=False)
    external_repo_id = mapped_column(Integer, ForeignKey('external_repo.id'),
                                     nullable=False)
    priority = mapped_column(Integer, nullable=False)
    merge_mode = mapped_column(Text, nullable=False, server_default=text("'koji'"))
    arches = mapped_column(Text)
