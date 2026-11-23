# Alembic migrations for the Koji hub database.
#
# Usage (see also util/koji-hub-migrate):
#   alembic -c kojihub/migrations/alembic.ini upgrade head
#
# The database connection is read from the hub configuration
# (/etc/koji-hub/hub.conf by default, override with KOJI_HUB_CONFIG
# or -x config=...).  An explicit URL can be passed with -x url=...

import os

ALEMBIC_INI = os.path.join(os.path.dirname(__file__), 'alembic.ini')
