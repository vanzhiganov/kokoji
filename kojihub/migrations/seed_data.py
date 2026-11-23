# Initial data for the Koji hub database, mirroring the INSERT
# statements in schemas/schema.sql.  Used by the baseline migration.

PERMISSIONS = [
    {'name': 'admin', 'description': 'Full administrator access. Perform all actions.'},
    {'name': 'appliance', 'description': 'Create appliance builds - deprecated.'},
    {'name': 'dist-repo', 'description': 'Create a dist-repo.'},
    {'name': 'host', 'description': 'Add, remove, enable, disable hosts and channels.'},
    {'name': 'image', 'description': 'Start image tasks.'},
    {'name': 'image-import', 'description': 'Import image archives.'},
    {'name': 'livecd', 'description': 'Start livecd tasks.'},
    {'name': 'maven-import', 'description': 'Import maven archives.'},
    {'name': 'repo', 'description': 'Manage repos: newRepo, repoExpire, repoDelete, repoProblem.'},
    {'name': 'sign', 'description': 'Import RPM signatures and write signed RPMs.'},
    {'name': 'tag', 'description': 'Manage packages in tags: add, block, remove, and clone tags.'},
    {'name': 'target', 'description': 'Add, edit, and remove targets.'},
    {'name': 'win-admin',
     'description': 'The default hub policy rule for "vm" requires this permission to trigger '
                    'Windows builds.'},
    {'name': 'win-import', 'description': 'Import win archives.'},
    {'name': 'draft-promoter',
     'description': 'The permission required in the default "draft_promotion" hub policy rule to '
                    'promote draft build.'},
]

CHANNELS = [
    {'name': 'default'},
    {'name': 'createrepo'},
    {'name': 'maven'},
    {'name': 'livecd'},
    {'name': 'appliance'},
    {'name': 'vm'},
    {'name': 'image'},
    {'name': 'livemedia'},
]

VOLUMES = [
    {'id': 0, 'name': 'DEFAULT'},
]

BTYPES = [
    {'name': 'rpm'},
    {'name': 'maven'},
    {'name': 'win'},
    {'name': 'image'},
]

EXTERNAL_REPOS = [
    {'id': 0, 'name': 'INTERNAL'},
]

ARCHIVETYPES = [
    {'name': 'jar',
     'description': 'Jar file',
     'extensions': 'jar war rar ear sar jdocbook jdocbook-style',
     'compression_type': 'zip'},
    {'name': 'zip', 'description': 'Zip file', 'extensions': 'zip', 'compression_type': 'zip'},
    {'name': 'pom', 'description': 'Maven Project Object Management file', 'extensions': 'pom'},
    {'name': 'tar',
     'description': 'Tar file',
     'extensions': 'tar tar.gz tar.bz2 tar.xz tgz',
     'compression_type': 'tar'},
    {'name': 'xml', 'description': 'XML file', 'extensions': 'xml'},
    {'name': 'xmlcompressed',
     'description': 'Compressed XML file',
     'extensions': 'xml.gz xml.bz2 xml.xz'},
    {'name': 'xsd', 'description': 'XML Schema Definition', 'extensions': 'xsd'},
    {'name': 'spec', 'description': 'RPM spec file', 'extensions': 'spec'},
    {'name': 'exe', 'description': 'Windows executable', 'extensions': 'exe'},
    {'name': 'dll', 'description': 'Windows dynamic link library', 'extensions': 'dll'},
    {'name': 'lib', 'description': 'Windows import library', 'extensions': 'lib'},
    {'name': 'sys', 'description': 'Windows device driver', 'extensions': 'sys'},
    {'name': 'inf', 'description': 'Windows driver information file', 'extensions': 'inf'},
    {'name': 'cat', 'description': 'Windows catalog file', 'extensions': 'cat'},
    {'name': 'msi', 'description': 'Windows Installer package', 'extensions': 'msi'},
    {'name': 'pdb', 'description': 'Windows debug information', 'extensions': 'pdb'},
    {'name': 'oem', 'description': 'Windows driver oem file', 'extensions': 'oem'},
    {'name': 'iso', 'description': 'CD/DVD Image', 'extensions': 'iso'},
    {'name': 'raw', 'description': 'Raw disk image', 'extensions': 'raw'},
    {'name': 'qcow', 'description': 'QCOW image', 'extensions': 'qcow'},
    {'name': 'qcow2', 'description': 'QCOW2 image', 'extensions': 'qcow2'},
    {'name': 'vmdk', 'description': 'vSphere image', 'extensions': 'vmdk'},
    {'name': 'ova', 'description': 'Open Virtualization Archive', 'extensions': 'ova'},
    {'name': 'ks', 'description': 'Kickstart', 'extensions': 'ks'},
    {'name': 'cfg', 'description': 'Configuration file', 'extensions': 'cfg'},
    {'name': 'vdi', 'description': 'VirtualBox Virtual Disk Image', 'extensions': 'vdi'},
    {'name': 'aar',
     'description': 'Binary distribution of an Android Library project',
     'extensions': 'aar'},
    {'name': 'apklib',
     'description': 'Source distribution of an Android Library project',
     'extensions': 'apklib'},
    {'name': 'cab', 'description': 'Windows cabinet file', 'extensions': 'cab'},
    {'name': 'dylib', 'description': 'OS X dynamic library', 'extensions': 'dylib'},
    {'name': 'gem', 'description': 'Ruby gem', 'extensions': 'gem'},
    {'name': 'ini', 'description': 'INI config file', 'extensions': 'ini'},
    {'name': 'js', 'description': 'Javascript file', 'extensions': 'js'},
    {'name': 'ldif', 'description': 'LDAP Data Interchange Format file', 'extensions': 'ldif'},
    {'name': 'manifest',
     'description': 'Runtime environment for .NET applications',
     'extensions': 'manifest'},
    {'name': 'msm', 'description': 'Windows merge module', 'extensions': 'msm'},
    {'name': 'properties', 'description': 'Properties file', 'extensions': 'properties'},
    {'name': 'sig', 'description': 'Signature file', 'extensions': 'sig signature'},
    {'name': 'so', 'description': 'Shared library', 'extensions': 'so'},
    {'name': 'txt', 'description': 'Text file', 'extensions': 'txt'},
    {'name': 'vhd', 'description': 'Hyper-V image', 'extensions': 'vhd'},
    {'name': 'vhdx', 'description': 'Hyper-V Virtual Hard Disk v2 image', 'extensions': 'vhdx'},
    {'name': 'wsf', 'description': 'Windows script file', 'extensions': 'wsf'},
    {'name': 'box', 'description': 'Vagrant Box Image', 'extensions': 'box'},
    {'name': 'raw-xz', 'description': 'xz compressed raw disk image', 'extensions': 'raw.xz'},
    {'name': 'json', 'description': 'JSON data', 'extensions': 'json'},
    {'name': 'key', 'description': 'Key file', 'extensions': 'key'},
    {'name': 'dot', 'description': 'DOT graph description', 'extensions': 'dot gv'},
    {'name': 'groovy', 'description': 'Groovy script file', 'extensions': 'groovy gvy'},
    {'name': 'batch', 'description': 'Batch file', 'extensions': 'bat'},
    {'name': 'shell', 'description': 'Shell script', 'extensions': 'sh'},
    {'name': 'rc', 'description': 'Resource file', 'extensions': 'rc'},
    {'name': 'wsdl', 'description': 'Web Services Description Language', 'extensions': 'wsdl'},
    {'name': 'obr', 'description': 'OSGi Bundle Repository', 'extensions': 'obr'},
    {'name': 'liveimg-squashfs',
     'description': 'liveimg compatible squashfs image',
     'extensions': 'liveimg.squashfs'},
    {'name': 'tlb', 'description': 'OLE type library file', 'extensions': 'tlb'},
    {'name': 'jnilib', 'description': 'Java Native Interface library', 'extensions': 'jnilib'},
    {'name': 'yaml', 'description': "YAML Ain't Markup Language", 'extensions': 'yaml yml'},
    {'name': 'xjb',
     'description': 'JAXB(Java Architecture for XML Binding) Binding Customization File',
     'extensions': 'xjb'},
    {'name': 'raw-gz', 'description': 'GZIP compressed raw disk image', 'extensions': 'raw.gz'},
    {'name': 'qcow2-compressed',
     'description': 'Compressed QCOW2 image',
     'extensions': 'qcow2.gz qcow2.xz'},
    {'name': 'iso-compressed',
     'description': 'Compressed iso image',
     'extensions': 'iso.gz iso.xz'},
    {'name': 'vhd-compressed',
     'description': 'Compressed VHD image',
     'extensions': 'vhd.gz vhd.xz'},
    {'name': 'vhdx-compressed',
     'description': 'Compressed VHDx image',
     'extensions': 'vhdx.gz vhdx.xz'},
    {'name': 'vmdk-compressed',
     'description': 'Compressed VMDK image',
     'extensions': 'vmdk.gz vmdk.xz'},
    {'name': 'kernel-image',
     'description': 'Kernel BZ2 Image',
     'extensions': 'vmlinuz vmlinuz.gz vmlinuz.xz'},
    {'name': 'initramfs', 'description': 'Compressed Initramfs Image', 'extensions': 'img'},
    {'name': 'checksum', 'description': 'Checksum file', 'extensions': 'sha256'},
    {'name': 'changes', 'description': 'Kiwi changes file', 'extensions': 'changes.xz changes'},
    {'name': 'packages', 'description': 'Kiwi packages listing', 'extensions': 'packages'},
    {'name': 'verified', 'description': 'Kiwi verified package list', 'extensions': 'verified'},
]

LOCKS = [
    {'name': 'protonmsg-plugin'},
    {'name': 'scheduler'},
    {'name': 'repo-queue'},
]


def insert_all():
    """Insert the initial data (called from the baseline migration)"""
    from alembic import op

    from kojihub.models import metadata

    for table_name, rows in [
        ('permissions', PERMISSIONS),
        ('channels', CHANNELS),
        ('volume', VOLUMES),
        ('btype', BTYPES),
        ('external_repo', EXTERNAL_REPOS),
        ('archivetypes', ARCHIVETYPES),
        ('locks', LOCKS),
    ]:
        # bulk_insert requires a uniform set of keys across all rows;
        # columns omitted in schema.sql inserts default to NULL
        keys = set()
        for row in rows:
            keys.update(row)
        rows = [{key: row.get(key) for key in keys} for row in rows]
        op.bulk_insert(metadata.tables[table_name], rows)
