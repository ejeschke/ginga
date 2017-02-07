#
# ModuleManager.py -- Simple class to dynamically manage module imports.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Dynamically manage module imports."""

from __future__ import absolute_import

from ..util.six.moves import reload_module
import imp

__all__ = ['ModuleManager']


def my_import(name, path=None):
    """Return imported module for the given name."""
    #mod = __import__(name)
    if path is None:
        fp, path, description = imp.find_module(name)

    else:
        fp = open(path, 'r')
        description = ('.py', 'r', imp.PY_SOURCE)

    try:
        mod = imp.load_module(name, fp, path, description)

    finally:
        fp.close()

    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
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
        """Load module from the given name."""
        try:
            if module_name in self.module:
                self.logger.info("Reloading module '%s'..." % module_name)
                module = reload_module(self.module[module_name])

            else:
                if pfx:
                    name = pfx + '.' + module_name
                else:
                    name = module_name

                self.logger.info("Loading module '%s'..." % module_name)
                module = my_import(name, path=path)

            self.module[module_name] = module

        except Exception as e:
            self.logger.error("Failed to load module '%s': %s" % (
                module_name, str(e)))
            raise ModuleManagerError(e)

    def get_module(self, module_name):
        """Return loaded module from the given name."""
        return self.module[module_name]

    ########################################################
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    loadModule = load_module
    getModule = get_module

#END
