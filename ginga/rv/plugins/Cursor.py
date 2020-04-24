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
        self.settings.add_defaults(font_name=None, font_size=None)
        self.settings.load(onError='silent')

        fv.add_callback('field-info', self.field_info_cb)
        fv.set_callback('channel-change', self.focus_cb)

        self.readout = None
        self.gui_up = False

    def build_gui(self, container):
        readout = Readout.Readout(-1, 24)

        # NOTE: Special hack for certain platforms, otherwise the font
        # on the readout is too small
        macos_ver = platform.mac_ver()[0]

        font_size = self.settings.get('font_size', None)
        if font_size is None:
            if len(macos_ver) > 0:
                # Mac OS X
                font_size = 16
            elif toolkit.get_family().startswith('gtk'):
                # Gtk
                font_size = 11
            else:
                font_size = 11

        font_name = self.settings.get('font_name', None)
        if font_name is None:
            font_name = font_asst.resolve_alias('fixed', 'Courier')
            if len(macos_ver) > 0:
                # Mac OS X
                font_name = 'monaco'

        readout.set_font(font_name, font_size)

        self.readout = readout
        rw = self.readout.get_widget()

        container.add_widget(rw, stretch=0)
        self.gui_up = True

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

    def force_update(self, channel):
        viewer = channel.fitsimage
        data_x, data_y = viewer.get_last_data_xy()
        self.fv.showxy(viewer, data_x, data_y)

    def redo(self, channel, image):
        if not self.gui_up or channel is None:
            return
        self.readout_config(channel.fitsimage, image, self.readout)

        # force an update on an image change, because the WCS
        # may be different, even if the data coords are the same
        self.force_update(channel)

    def change_readout(self, channel, fitsimage):
        self.readout.fitsimage = fitsimage

        image = fitsimage.get_image()
        if image is not None:
            self.readout_config(fitsimage, image, self.readout)
            self.logger.debug("configured readout")

    def focus_cb(self, viewer, channel):
        if not self.gui_up or channel is None:
            return

        self.change_readout(channel, channel.fitsimage)

        # force an update on a channel change, because the WCS
        # may be different, even if the data coords are the same
        self.force_update(channel)

    def start(self):
        channel = self.fv.get_channel_info()
        self.focus_cb(self.fv, channel)

    def stop(self):
        self.readout = None
        self.gui_up = False
        return True

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def field_info_cb(self, viewer, channel, info):
        if not self.gui_up or channel is None:
            return
        readout = self.readout
        fitsimage = channel.fitsimage

        if readout.fitsimage != fitsimage:
            self.change_readout(channel, fitsimage)

        value = info.value

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
