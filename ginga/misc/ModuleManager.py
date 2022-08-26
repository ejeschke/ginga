#
# ModuleManager.py -- Simple class to dynamically manage module imports.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Dynamically manage module imports.

The ModuleManager class
"""
import sys
import os
import importlib

__all__ = ['ModuleManager']


def my_import(name, path=None):
    """Return imported module for the given name."""

    # Documentation for importlib says this may be needed to pick up
    # modules created after the program has started
    importlib.invalidate_caches()

    if path is not None:
        directory, src_file = os.path.split(path)

        # TODO: use the importlib.util machinery
        sys.path.insert(0, directory)
        try:
            mod = importlib.import_module(name)
        finally:
            sys.path.pop(0)

    else:
        mod = importlib.import_module(name)

    return mod


class ModuleManagerError(Exception):
    """Exception related to module manager."""
    pass


class ModuleManager(object):
    """Simple class to dynamically manage module imports."""

    def __init__(self, logger):
        self.logger = logger

        self.module = {}

    def load_module(self, module_name, pfx=None, path=None):
        """Load/reload module from the given name."""
        try:
            if pfx:
                name = pfx + '.' + module_name
            else:
                name = module_name

            if name in sys.modules:
                module = sys.modules[name]
                self.logger.info("Reloading module '%s'..." % module_name)
                module = importlib.reload(module)

            else:
                self.logger.info("Loading module '%s'..." % module_name)
                module = my_import(name, path=path)

            self.module[module_name] = module
            return module

        except Exception as e:
            self.logger.error("Failed to load module '%s': %s" % (
                module_name, str(e)), exc_info=True)
            raise ModuleManagerError(e)

    def get_module(self, module_name):
        """Return loaded module from the given name."""
        try:
            return self.module[module_name]

        except KeyError:
            return sys.modules[module_name]
