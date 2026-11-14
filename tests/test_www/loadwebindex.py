import os
import sys

# The web handlers now live in the kojiweb package (kojiweb.views). Expose
# that module as "webidx" so the existing tests keep working unchanged.
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'www', 'lib')))

import kojiweb.views  # noqa: E402

webidx = kojiweb.views
