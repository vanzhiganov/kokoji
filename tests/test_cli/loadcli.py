from __future__ import absolute_import
import importlib
import importlib.machinery
import importlib.util
import os
import sys

CLI_MOD = "koji_cli_fake"

# We have to do this craziness because 'import koji' is ambiguous.  Is it the
# koji module, or the koji cli module.  Jump through hoops accordingly.
# https://stackoverflow.com/questions/67631/how-to-import-a-module-given-the-full-path
CLI_FILENAME = os.path.dirname(__file__) + "/../../cli/koji"
importlib.machinery.SOURCE_SUFFIXES.append('')
spec = importlib.util.spec_from_file_location(CLI_MOD, CLI_FILENAME)
cli = importlib.util.module_from_spec(spec)
sys.modules[CLI_MOD] = cli
spec.loader.exec_module(cli)
importlib.machinery.SOURCE_SUFFIXES.pop()
