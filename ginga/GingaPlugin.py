#
# GingaPlugin.py -- Base classes for plugins in Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch
from ginga.gw import Widgets

__all__ = ['PluginError', 'GlobalPlugin', 'LocalPlugin',
           'ParentPlugin', 'ChildPlugin']


class PluginError(Exception):
    """Plugin related error."""
    pass


class BasePlugin(object):
    """Base class for all plugins."""
    def __init__(self, fv, ident=None):
        super().__init__()
        self.fv = fv
        self.logger = fv.logger
        self.ident = ident

        # Holds GUI widgets
        self.w = Bunch.Bunch()

    def __str__(self):
        if self.ident is not None:
            return self.ident
        return super().__str__()

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
    def __init__(self, fv, ident=None):
        super().__init__(fv, ident=ident)

    def handleable(self, dataobj):
        """Test whether `dataobj` can be handled by this plugin."""
        # should ideally be overridden by subclass
        return True

    # def redo(self, channel, dataobj):
    #     """If defined, this method is called when a data object is switched to
    #     in a channel."""
    #     pass

    # def blank(self, channel):
    #     """If defined, this method is called when a channel is no longer
    #     displaying any object."""
    #     pass


class LocalPlugin(BasePlugin):
    """Class to handle a local plugin."""
    def __init__(self, fv, fitsimage, ident=None):
        super().__init__(fv, ident=ident)
        self.fitsimage = fitsimage

        # find our channel info
        if self.fitsimage is not None:
            self.chname = self.fv.get_channel_name(self.fitsimage)
            self.channel = self.fv.get_channel(self.chname)
            # TO BE DEPRECATED
            self.chinfo = self.channel

    def handleable(self, dataobj):
        """Test whether `dataobj` can be handled by this plugin."""
        # should ideally be overridden by subclass
        return True

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

    # def redo(self):
    #     """
    #     If defined, this method is called when a data object is switched
    #     to in the channel associated with the plugin.  It can optionally
    #     redo whatever operation it is doing.
    #     """
    #     pass

    # def blank(self):
    #     """
    #     If defined, this method is called when no object is displayed in the
    #     channel associated with the plugin.  It can optionally clear whatever
    #     operation it is doing.
    #     """
    #     pass


class ParentPlugin(GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super().__init__(fv, ident=None)

        self.plugin_dct = dict()
        self.class_childplugin = None

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.add_callback('channel-change', self.focus_cb)
        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(1)
        vbox.set_spacing(1)
        self.w.top_w = vbox

        nb = Widgets.StackWidget()
        vbox.add_widget(nb, stretch=1)
        self.w.nb = nb

        container.add_widget(vbox, stretch=1)
        self.gui_up = True

    def add_channel(self, viewer, channel):
        if not self.gui_up:
            return

        # create child plugin
        plugin = self.class_childplugin(self.fv, channel.fitsimage, self)

        if hasattr(plugin, 'build_gui'):
            # build it's gui
            vbox = Widgets.VBox()
            vbox.set_border_width(1)
            vbox.set_spacing(1)

            plugin.build_gui(vbox)

            self.w.nb.add_widget(vbox, title=channel.name)
        else:
            vbox = None

        self.plugin_dct[channel.name] = Bunch.Bunch(plugin=plugin,
                                                    widget=vbox)

    def delete_channel(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        bnch = self.plugin_dct[chname]
        del self.plugin_dct[chname]
        widget = bnch.widget
        try:
            bnch.plugin.stop()
        except Exception as e:
            self.logger.error(f"error closing plugin: {e}")
        if widget is not None:
            self.w.nb.remove(widget, delete=True)

    def focus_cb(self, viewer, channel):
        if not self.gui_up:
            return
        bnch = self.plugin_dct[channel.name]
        if bnch.widget is not None:
            index = self.w.nb.index_of(bnch.widget)
            self.w.nb.set_index(index)

    def start(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            self.add_channel(self.fv, channel)

        channel = self.fv.get_channel_info()
        if channel is not None:
            viewer = channel.fitsimage

            image = viewer.get_image()
            if image is not None:
                self.redo(channel, image)

            self.focus_cb(viewer, channel)

    def stop(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            self.delete_channel(self.fv, channel)

        self.gui_up = False
        # dereference gui widgets
        self.w = Bunch.Bunch()
        return True

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def redo(self, channel, image):
        bnch = self.plugin_dct[channel.name]
        bnch.plugin.redo()


class ChildPlugin(LocalPlugin):

    def __init__(self, fv, image_viewer, parent_plugin):
        super().__init__(fv, image_viewer)

        self.pp = parent_plugin
        self.gui_up = False


# END
