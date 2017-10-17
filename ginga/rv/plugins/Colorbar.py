# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Colorbar`` plugin shows a colorbar indicating the colormap applied
to the image and showing the example values along the range.

**Plugin Type: Global**

``Colorbar`` is a global plugin.  Only one instance can be opened.

**Usage**

Clicking and dragging in the ``Colorbar`` window will shift the colormap
left or right.  Scrolling will stretch or shrink the colormap at the
cursor position.  Right-clicking will restore the colormap from any
shift or stretch.

If the focus shifts to another channel, the colorbar will be updated
to reflect that channel's colormap and value information.

"""
from ginga import GingaPlugin
from ginga.misc import Bunch
from ginga.gw import ColorBar

__all__ = ['Colorbar']


class Colorbar(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Colorbar, self).__init__(fv)

        self._image = None
        self.active = None
        self.info = None

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Colorbar')
        self.settings.add_defaults(cbar_height=36, fontsize=12)
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)

    def build_gui(self, container):
        cbar = ColorBar.ColorBar(self.logger, settings=self.settings)
        cbar.set_cmap(self.fv.cm)
        cbar.set_imap(self.fv.im)
        cbar_w = cbar.get_widget()
        cbar_ht = self.settings.get('cbar_height', 36)
        cbar_w.resize(-1, cbar_ht)

        self.colorbar = cbar
        self.fv.add_callback('channel-change', self.change_cbar, cbar)
        cbar.add_callback('motion', self.cbar_value_cb)

        container.add_widget(cbar_w, stretch=0)

    def add_channel_cb(self, viewer, channel):
        settings = channel.settings
        settings.get_setting('cuts').add_callback(
            'set', self.change_range_cb, channel.fitsimage, self.colorbar)

        chname = channel.name
        info = Bunch.Bunch(chname=chname, channel=channel)
        channel.extdata._colorbar_info = info

        fi = channel.fitsimage
        rgbmap = fi.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, channel)

    def delete_channel_cb(self, viewer, channel):
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        self.active = None
        self.info = None

    def _match_cmap(self, fitsimage, colorbar):
        """
        Help method to change the ColorBar to match the cut levels or
        colormap used in a ginga ImageView.
        """
        rgbmap = fitsimage.get_rgbmap()
        loval, hival = fitsimage.get_cut_levels()
        colorbar.set_range(loval, hival)
        # If we are sharing a ColorBar for all channels, then store
        # to change the ColorBar's rgbmap to match our
        colorbar.set_rgbmap(rgbmap)

    def change_cbar(self, viewer, channel, cbar):
        self._match_cmap(channel.fitsimage, cbar)

    # def focus_cb(self, viewer, channel):
    #     chname = channel.name

    #     if self.active != chname:
    #         self.active = chname
    #         self.info = channel.extdata._colorbar_info

    #     image = channel.fitsimage.get_image()
    #     if image is None:
    #         return
    #     # install rgbmap

    def change_range_cb(self, setting, value, fitsimage, cbar):
        """
        This method is called when the cut level values (lo/hi) have
        changed in a channel.  We adjust them in the ColorBar to match.
        """
        if cbar is None:
            return
        if fitsimage != self.fv.getfocus_viewer():
            # values have changed in a channel that doesn't have the focus
            return False
        loval, hival = value
        cbar.set_range(loval, hival)

    def cbar_value_cb(self, cbar, value, event):
        """
        This method is called when the user moves the mouse over the
        ColorBar.  It displays the value of the mouse position in the
        ColorBar in the Readout (if any).
        """
        channel = self.fv.get_channel_info()
        if channel is None:
            return
        readout = channel.extdata.get('readout', None)
        if readout is not None:
            maxv = readout.maxv
            text = "Value: %-*.*s" % (maxv, maxv, value)
            readout.set_text(text)

    def rgbmap_cb(self, rgbmap, channel):
        """
        This method is called when the RGBMap is changed.  We update
        the ColorBar to match.
        """
        fitsimage = channel.fitsimage
        if fitsimage != self.fv.getfocus_fitsimage():
            return False
        if self.colorbar is not None:
            self.change_cbar(self.fv, channel, self.colorbar)

    def start(self):
        ## names = self.fv.get_channel_names()
        ## for name in names:
        ##     channel = self.fv.get_channel(name)
        ##     self.add_channel_cb(self.fv, channel)
        pass

    def __str__(self):
        return 'colorbar'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Colorbar', package='ginga')

# END
