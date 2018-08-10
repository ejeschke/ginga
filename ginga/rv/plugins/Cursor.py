# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Cursor`` plugin displays a summary line of text that changes as the
user moves the cursor around an image.  In the standard reference viewer
configuration, it appears as a line containing green text just below the
``Colorbar`` plugin.

**Plugin Type: Global**

``Cursor`` is a global plugin.  Only one instance can be opened.

**Usage**

``Cursor`` simply tracks the cursor as it moves around an image and displays
information about the pixel coordinates, WCS coordinates (if available)
and the value of the pixel under the cursor.

There is no associated configuration GUI.

.. note:: Pixel coordinates are affected by the general setting
          "pixel_coords_offset" which can be set in the "general.cfg"
          configuration file for ginga.  The default is value for this
          setting is 1.0, which means pixel coordinates are reported
          from an origin of 1, as per the FITS standard.

"""
import platform

import numpy as np

from ginga import GingaPlugin, toolkit
from ginga.gw import Readout
from ginga.ImageView import ImageViewNoDataError
from ginga.fonts import font_asst

__all__ = ['Cursor']


class Cursor(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Cursor, self).__init__(fv)

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Cursor')
        self.settings.add_defaults(share_readout=True)
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('field-info', self.field_info_cb)
        fv.set_callback('channel-change', self.focus_cb)

        # TODO: let this become OUR setting
        self.share_readout = self.fv.settings.get('share_readout', True)
        self.readout = None

    def _build_readout(self):
        readout = Readout.Readout(-1, 24)

        font_name = font_asst.resolve_alias('fixed', 'Courier')

        # NOTE: Special hack for certain platforms, otherwise the font
        # on the readout is too small
        macos_ver = platform.mac_ver()[0]
        if len(macos_ver) > 0:
            # Mac OS X
            readout.set_font('monaco', 16)
        elif toolkit.get_family().startswith('gtk'):
            # Gtk
            readout.set_font(font_name, 14)
        else:
            readout.set_font(font_name, 11)
        return readout

    def build_gui(self, container):

        if self.share_readout:
            self.readout = self._build_readout()
            rw = self.readout.get_widget()
            container.add_widget(rw, stretch=0)

            channel = self.fv.get_channel_info()
            if channel is not None:
                self.focus_cb(self.fv, channel)

    def add_channel_cb(self, viewer, channel):
        fi = channel.fitsimage

        if not self.share_readout:
            readout = self._build_readout()
            readout.fitsimage = fi

            rw = readout.get_widget()
            channel.container.add_widget(rw, stretch=0)

        else:
            # shared readout
            readout = self.readout

        channel.extdata.readout = readout

    def delete_channel_cb(self, viewer, channel):
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))

    def start(self):
        ## names = self.fv.get_channel_names()
        ## for name in names:
        ##     channel = self.fv.get_channel_info(name)
        ##     self.add_channel_cb(self.fv, channel)
        pass

    def readout_config(self, fitsimage, image, readout):
        if (readout is None) or (image is None):
            return True
        self.logger.debug("configuring readout (%s)" % (str(readout)))
        # Configure readout for this image.
        # Get and store the sizes of the fields necessary to display
        # all X, Y coords as well as values.

        try:
            width, height = fitsimage.get_data_size()
        except ImageViewNoDataError as exc:  # table
            self.logger.debug(str(exc))
            return

        # Set size of coordinate areas (4 is "." + precision 3)
        readout.maxx = len(str(width)) + 4
        readout.maxy = len(str(height)) + 4
        minval, maxval = image.get_minmax()
        readout.maxv = max(len(str(minval)), len(str(maxval)))
        return True

    def redo(self, channel, image):
        readout = channel.extdata.readout
        self.readout_config(channel.fitsimage, image, readout)
        self._set_readout_text(
            readout, channel.get_image_info(image.get('name', 'none')))

    def change_readout(self, channel, fitsimage):
        if (self.share_readout) and (self.readout is not None):
            self.logger.debug("configuring readout")

            self.readout.fitsimage = fitsimage

            image = fitsimage.get_image()
            if image is not None:
                self.readout_config(fitsimage, image, self.readout)
                self.logger.debug("configured readout")

        else:
            # Get this channel's readout (if any)
            self.readout = channel.extdata.get('readout', None)

    def focus_cb(self, viewer, channel):
        if channel is not None:
            self.change_readout(channel, channel.fitsimage)

    def field_info_cb(self, viewer, channel, info):
        readout = self.readout
        if readout is None:
            return

        fitsimage = channel.fitsimage
        ## self.logger.debug("fitsimage: %s readout.fitsimage: %s" % (
        ##     str(fitsimage), str(readout.fitsimage)))
        if readout.fitsimage != fitsimage:
            self.change_readout(channel, fitsimage)
            if self.readout is None:
                return
            readout = self.readout

        self._set_readout_text(readout, info)

    @staticmethod
    def _set_readout_text(readout, info):
        if 'value' not in info:
            return  # no-op

        # If this is a multiband image, then average the values
        # for the readout
        value = info.value
        if isinstance(value, np.ndarray):
            avg = np.average(value)
            value = avg

        # Update the readout
        px_x = "%.3f" % info.x
        px_y = "%.3f" % info.y
        maxx = max(readout.maxx, len(str(px_x)))
        if maxx > readout.maxx:
            readout.maxx = maxx
        maxy = max(readout.maxy, len(str(px_y)))
        if maxy > readout.maxy:
            readout.maxy = maxy
        maxv = max(readout.maxv, len(str(value)))
        if maxv > readout.maxv:
            readout.maxv = maxv

        if 'ra_txt' in info:
            text = "%1.1s: %-14.14s  %1.1s: %-14.14s  X: %-*.*s  Y: %-*.*s  Value: %-*.*s" % (
                info.ra_lbl, info.ra_txt, info.dec_lbl, info.dec_txt,
                maxx, maxx, px_x, maxy, maxy, px_y, maxv, maxv, value)
        else:
            text = "%1.1s: %-14.14s  %1.1s: %-14.14s  X: %-*.*s  Y: %-*.*s  Value: %-*.*s" % (
                '', '', '', '',
                maxx, maxx, px_x, maxy, maxy, px_y, maxv, maxv, value)
        readout.set_text(text)

    def __str__(self):
        return 'cursor'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Cursor', package='ginga')

# END
