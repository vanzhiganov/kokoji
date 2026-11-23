# SQLAlchemy models for the Koji hub database schema.
#
# These models mirror schemas/schema.sql (schema version 1.36) and are used
# by Alembic (kojihub.migrations) to manage schema migrations.  The runtime
# hub code still uses raw SQL via kojihub.db; these models are for schema
# management only.

from . import (  # noqa: F401
    archives,
    builds,
    hosts,
    misc,
    repos,
    rpms,
    scheduler,
    tags,
    tasks,
    users,
)
from .archives import (  # noqa: F401
    ArchiveComponent,
    ArchiveInfo,
    ArchiveRpmComponent,
    ArchiveType,
    BuildrootArchive,
    ImageArchive,
    MavenArchive,
    WinArchive,
)
from .base import Base  # noqa: F401
from .builds import (  # noqa: F401
    Btype,
    Build,
    BuildNotification,
    BuildNotificationBlock,
    BuildReservation,
    Buildroot,
    BuildrootToolsInfo,
    BuildType,
    CgUser,
    ContentGenerator,
    ImageBuild,
    MavenBuild,
    Package,
    StandardBuildroot,
    Volume,
    WinBuild,
)
from .hosts import Channel, Host, HostChannel, HostConfig  # noqa: F401
from .misc import Lock, ProtonQueue  # noqa: F401
from .repos import (  # noqa: F401
    ExternalRepo,
    ExternalRepoConfig,
    ExternalRepoData,
    Repo,
    RepoQueue,
)
from .rpms import (  # noqa: F401
    BuildrootListing,
    RpmChecksum,
    RpmInfo,
    RpmSig,
)
from .scheduler import (  # noqa: F401
    SchedulerHostData,
    SchedulerLogMessage,
    SchedulerSysData,
    SchedulerTaskRefusal,
    SchedulerTaskRun,
)
from .tags import (  # noqa: F401
    BuildTarget,
    BuildTargetConfig,
    Group,
    GroupConfig,
    GroupPackageListing,
    GroupReqListing,
    Tag,
    TagConfig,
    TagExternalRepo,
    TagExtra,
    TagInheritance,
    TagListing,
    TagPackage,
    TagPackageOwner,
    TagUpdate,
)
from .tasks import Task  # noqa: F401
from .users import (  # noqa: F401
    Event,
    EventLabel,
    Permission,
    Session,
    User,
    UserGroup,
    UserPerm,
)

metadata = Base.metadata
