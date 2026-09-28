#!/bin/bash
set -e

# Substitute database connection settings from environment variables.
#
# This uses configparser rather than sed so that it works regardless of whether
# an option is already set, commented out, or absent. A plain `sed -i
# 's/^DBName = .../'` silently does nothing when the line is commented, which
# leaves the container pointed at the wrong database.

python3 - "$@" <<'PYEOF'
import configparser
import os

CONF = '/etc/koji-hub/hub.conf'

parser = configparser.ConfigParser(interpolation=None)
# preserve key case; the hub does case-insensitive lookups but a rewritten
# config should stay readable
parser.optionxform = str
parser.read(CONF)

if not parser.has_section('hub'):
    parser.add_section('hub')


def env(name, default):
    return os.environ.get(name, default)


opts = {
    'DBName': env('DB_NAME', 'koji'),
    'DBUser': env('DB_USER', 'koji'),
    'DBHost': env('DB_HOST', 'db'),
    'DBPort': env('DB_PORT', '5432'),
    'DBPass': env('DB_PASS', 'koji'),
}

for key, value in opts.items():
    parser.set('hub', key, value)

with open(CONF, 'w') as f:
    parser.write(f)

print('koji-hub config:')
for key, value in opts.items():
    print('  %s = %s' % (key, value))
PYEOF

# Ensure the koji top directory exists and is writable by the web server user
mkdir -p /mnt/koji
chown -R apache:apache /mnt/koji || true

echo "Starting koji-hub..."
exec httpd -DFOREGROUND
