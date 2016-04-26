#
# Colorbar.py -- Color bar plugin for Ginga viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.misc import Bunch
from ginga.gw import Widgets, ColorBar


class Colorbar(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Colorbar, self).__init__(fv)

        self._image = None
        self.channel = {}
        self.active = None
        self.info = None

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_ColorBar')
        #self.settings.addDefaults()
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)

    def build_gui(self, container):
        cbar = ColorBar.ColorBar(self.logger)
        cbar.set_cmap(self.fv.cm)
        cbar.set_imap(self.fv.im)
        if hasattr(cbar, 'get_widget'):
            # generic version based on a ginga widget
            cbar_w = cbar.get_widget()
            # TEMP
            #cbar_w.resize(600, 16)
            fr = cbar_w
        else:
            # dedicated widget version
            cbar_w = Widgets.wrap(cbar)

            fr = Widgets.Frame()
            fr.set_border_width(0)
            fr.set_widget(cbar_w)

        self.colorbar = cbar
        self.fv.add_callback('channel-change', self.change_cbar, cbar)
        cbar.add_callback('motion', self.cbar_value_cb)

        container.add_widget(fr, stretch=0)

    def add_channel_cb(self, viewer, channel):
        settings = channel.settings
        settings.getSetting('cuts').add_callback('set',
                              self.change_range_cb, channel.fitsimage, self.colorbar)

        chname = channel.name
        info = Bunch.Bunch(chname=chname, channel=channel)
        self.channel[chname] = info

        fi = channel.fitsimage
        rgbmap = fi.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, channel)

    def delete_channel_cb(self, viewer, channel):
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        self.active = None
        self.info = None
        del self.channel[chname]

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
    #         self.info = self.channel[self.active]

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
        if fitsimage != self.fv.getfocus_fitsimage():
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
        channel = self.fv.get_channelInfo()
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
        ## names = self.fv.get_channelNames()
        ## for name in names:
        ##     channel = self.fv.get_channelInfo(name)
        ##     self.add_channel_cb(self.fv, channel)
        pass

    def __str__(self):
        return 'colorbar'

#END
