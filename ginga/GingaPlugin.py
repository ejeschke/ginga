#
# GingaPlugin.py -- Base classes for plugins in Ginga FITS viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch

class PluginError(Exception):
    pass

class GlobalPlugin(object):

    def __init__(self, fv):
        super(GlobalPlugin, self).__init__()
        self.fv = fv
        self.logger = fv.logger

        # Holds GUI widgets
        self.w = Bunch.Bunch()

    def initialize(self, container):
        """This method will be called with a container widget if the global
        plugin was requested to be loaded into a workspace.  The plugin should
        construct its GUI and pack it into the container.
        """
        pass

    def start(self):
        """This method is called to start the plugin.  It is called after
        build_gui().
        """
        pass
        
    def stop(self):
        """This method is called to stop the plugin.
        """
        pass


class LocalPlugin(object):

    def __init__(self, fv, fitsimage):
        super(LocalPlugin, self).__init__()
        self.fv = fv
        self.logger = fv.logger
        self.fitsimage = fitsimage

        # Holds GUI widgets
        self.w = Bunch.Bunch()

    def modes_off(self):
        # turn off any mode user may be in
        bm = self.fitsimage.get_bindmap()
        bm.reset_mode(self.fitsimage)
        
    # def build_gui(self, container):
    #     """If a plugin defines this method, it will be called with a
    #     container object in which to build its GUI. It should finish
    #     by packing into this container.  This will be called every
    #     time the local plugin is activated.
    #     """
    #     pass

    def start(self):
        """This method is called just after build_gui() when the plugin is
        activated.
        """
        pass
        
    def stop(self):
        """This method is called when the plugin is deactivated.
        """
        pass

    def pause(self):
        """This method is called when the plugin is defocused.  The plugin
        should disable any user input that it responds to.
        """
        pass

    def resume(self):
        """This method is called when the plugin is focused.  The plugin
        should enable any user input that it responds to.
        """
        pass

    def redo(self):
        """This method is called when a new image arrives in the channel
        associated with the plugin.  It can optionally redo whatever operation
        it is doing.
        """
        pass


#END
