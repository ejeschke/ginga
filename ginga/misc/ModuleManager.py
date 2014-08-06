#
# ModuleManager.py -- Simple class to dynamically manage module imports.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
def my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


class ModuleManagerError(Exception):
    pass

class ModuleManager(object):

    def __init__(self, logger):
        self.logger = logger
        
        self.module = {}

    def loadModule(self, moduleName, pfx=None):
        try:
            if moduleName in self.module:
                self.logger.info("Reloading module '%s'..." % moduleName)
                module = reload(self.module[moduleName])

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
        return self.module[moduleName]

    
            
#END
