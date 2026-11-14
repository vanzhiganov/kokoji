from __future__ import absolute_import
import importlib.machinery
import importlib.util
import os

# http://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
KOJID_FILENAME = os.path.dirname(__file__) + "/../../builder/kojid"
loader = importlib.machinery.SourceFileLoader('koji_kojid', KOJID_FILENAME)
spec = importlib.util.spec_from_file_location("koji_kojid", loader=loader)
kojid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kojid)
