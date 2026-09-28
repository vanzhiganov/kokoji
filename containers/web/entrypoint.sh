#!/bin/bash
set -e

# Substitute configuration from environment variables.
#
# This uses configparser rather than sed so that it works regardless of whether
# the option is already set, commented out, or absent from the file. A plain
# `sed -i 's/^AllowRegistration = .../'` silently does nothing when the line is
# commented, which leaves registration off no matter what the env var says.

python3 - "$@" <<'PYEOF'
import configparser
import os

CONF = '/etc/kojiweb/web.conf'

parser = configparser.ConfigParser(interpolation=None)
# preserve key case; kojiweb does case-insensitive lookups but a rewritten
# config should stay readable
parser.optionxform = str
parser.read(CONF)

if not parser.has_section('web'):
    parser.add_section('web')


def set_opt(name, value):
    parser.set('web', name, value)


set_opt('KojiHubURL', os.environ.get('HUB_URL', 'http://hub/kojihub'))
set_opt('KojiFilesURL', os.environ.get('FILES_URL', 'http://hub/kojifiles'))
set_opt('Secret', os.environ.get('WEB_SECRET', 'change-me-secret'))

# Allow toggling self-registration
allow_reg = os.environ.get('ALLOW_REGISTRATION', 'On')
set_opt('AllowRegistration', 'On' if allow_reg == 'On' else 'Off')

with open(CONF, 'w') as f:
    parser.write(f)

print('kojiweb config:')
for key in ('KojiHubURL', 'KojiFilesURL', 'AllowRegistration'):
    print('  %s = %s' % (key, parser.get('web', key)))
PYEOF

echo "Starting koji-web..."
exec httpd -DFOREGROUND
