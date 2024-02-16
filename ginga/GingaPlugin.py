#
# GingaPlugin.py -- Base classes for plugins in Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch

__all__ = ['PluginError', 'GlobalPlugin', 'LocalPlugin']


class PluginError(Exception):
    """Plugin related error."""
    pass


class BasePlugin(object):
    """Base class for all plugins."""
    def __init__(self, fv):
        super(BasePlugin, self).__init__()
        self.fv = fv
        self.logger = fv.logger

        # Holds GUI widgets
        self.w = Bunch.Bunch()

    # def build_gui(self, container):
    #     """
    #     If a plugin defines this method, it will be called with a
    #     container object in which to build its GUI. It should finish
    #     by packing into this container.  This will be called every
    #     time the plugin is activated.
    #     """
    #     pass

    def start(self):
        """
        This method is called to start the plugin.
        It is called after build_gui().
        """
        pass

    def stop(self):
        """This method is called to stop the plugin."""
        pass

    def _get_docstring(self):
        import inspect

        # Insert section title at the beginning
        plg_name = self.__class__.__name__
        plg_mod = inspect.getmodule(self)
        plg_doc = ('{}\n{}\n'.format(plg_name, '=' * len(plg_name)) +
                   plg_mod.__doc__)
        return plg_name, plg_doc

    def _help_docstring(self):
        plg_name, plg_doc = self._get_docstring()
        self.fv.help_text(plg_name, plg_doc, text_kind='rst', trim_pfx=4)

    def help(self, text_kind='rst'):
        """Display help for the plugin."""
        self.fv.help_plugin(self, text_kind=text_kind)


class GlobalPlugin(BasePlugin):
    """Class to handle a global plugin."""
    def __init__(self, fv):
        super(GlobalPlugin, self).__init__(fv)

    def redo(self, channel, image):
        """This method is called when an image is set in a channel."""
        pass

    def blank(self, channel):
        """This method is called when a channel is no longer displaying any object."""
        pass


class LocalPlugin(BasePlugin):
    """Class to handle a local plugin."""
    def __init__(self, fv, fitsimage):
        super(LocalPlugin, self).__init__(fv)
        self.fitsimage = fitsimage

        # find our channel info
        if self.fitsimage is not None:
            self.chname = self.fv.get_channel_name(self.fitsimage)
            self.channel = self.fv.get_channel(self.chname)
            # TO BE DEPRECATED
            self.chinfo = self.channel

    def modes_off(self):
        """Turn off any mode user may be in."""
        bm = self.fitsimage.get_bindmap()
        bm.reset_mode(self.fitsimage)

    def pause(self):
        """
        This method is called when the plugin is defocused.
        The plugin should disable any user input that it responds to.
        """
        pass

    def resume(self):
        """
        This method is called when the plugin is focused.
        The plugin should enable any user input that it responds to.
        """
        pass

    def redo(self):
        """
        This method is called when a new image arrives in the channel
        associated with the plugin.  It can optionally redo whatever operation
        it is doing.
        """
        pass

    def blank(self):
        """
        This method is called when no object is displayed in the channel
        associated with the plugin.  It can optionally clear whatever operation
        it is doing.
        """
        pass

# END
