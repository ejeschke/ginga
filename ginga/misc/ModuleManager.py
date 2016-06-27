"""Dynamically manage module imports."""
#
# ModuleManager.py -- Simple class to dynamically manage module imports.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import absolute_import

from ..util.six.moves import reload_module

__all__ = ['ModuleManager']


def my_import(name):
    """Return imported module for the given name."""
    mod = __import__(name)
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

    def loadModule(self, moduleName, pfx=None):
        """Load module from the given name."""
        try:
            if moduleName in self.module:
                self.logger.info("Reloading module '%s'..." % moduleName)
                module = reload_module(self.module[moduleName])

            else:
                if pfx:
                    name = pfx + '.' + moduleName
                else:
                    name = moduleName

                self.logger.info("Loading module '%s'..." % moduleName)
                module = my_import(name)

            self.module[moduleName] = module

        except Exception as e:
            self.logger.error("Failed to load module '%s': %s" % (
                moduleName, str(e)))
            raise ModuleManagerError(e)

    def getModule(self, moduleName):
        """Return loaded module from the given name."""
        return self.module[moduleName]

#END
