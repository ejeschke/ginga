# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
A plugin for generating color overlays representing under- and
over-exposure in the loaded image.

**Plugin Type: Local**

``Overlays`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

Choose colors from the drop-down menus for the low-limit and/or
high-limit ("Lo color" and "Hi color", respectively).  Specify the limits
for low and high values in the limit boxes ("Lo limit" and "Hi limit",
respectively).  Set the opacity of the overlays with a value between
0 and 1 in the "Opacity" box.  Finally, press the "Redo" button.

The color overlay should show areas below the low limit with a low color
and the areas above the high limit in the high color.
If you omit a limit (leave the box blank), that color won't be shown in
the overlay.

If a new image is selected for the channel, the overlays image will be
recalculated based on the current parameters with the new data.

"""
import numpy as np

from ginga import GingaPlugin, RGBImage, colors
from ginga.gw import Widgets

__all__ = ['Overlays']


class Overlays(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Overlays, self).__init__(fv, fitsimage)

        self.layertag = 'overlays-canvas'

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        # get Overlays preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Overlays')
        self.settings.add_defaults(hi_color='palevioletred', hi_value=None,
                                   lo_color='blue', lo_value=None,
                                   opacity=0.5, orientation=None)
        self.settings.load(onError='silent')

        self.colornames = colors.get_colors()
        self.hi_color = self.settings.get('hi_color', 'palevioletred')
        self.hi_value = self.settings.get('hi_value', None)
        self.lo_color = self.settings.get('lo_color', 'blue')
        self.lo_value = self.settings.get('lo_value', None)
        self.opacity = self.settings.get('opacity', 0.5)
        self.arrsize = None
        self.rgbarr = np.zeros((1, 1, 4), dtype=np.uint8)
        self.rgbobj = RGBImage.RGBImage(logger=self.logger, data_np=self.rgbarr)
        self.canvas_img = None

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("Limits")

        captions = (('Opacity:', 'label', 'Opacity', 'spinfloat'),
                    ('Hi color:', 'label', 'Hi color', 'combobox'),
                    ('Hi limit:', 'label', 'Hi value', 'entry'),
                    ('Lo color:', 'label', 'Lo color', 'combobox'),
                    ('Lo limit:', 'label', 'Lo value', 'entry'),
                    ('Redo', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.opacity.set_decimals(2)
        b.opacity.set_limits(0.0, 1.0, incr_value=0.1)
        b.opacity.set_value(self.opacity)
        b.opacity.add_callback('value-changed', lambda *args: self.redo())

        combobox = b.hi_color
        for name in self.colornames:
            combobox.append_text(name)
        index = self.colornames.index(self.hi_color)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda *args: self.redo())

        b.hi_value.set_length(22)
        if self.hi_value is not None:
            b.hi_value.set_text(str(self.hi_value))
        b.hi_value.add_callback('activated', lambda *args: self.redo())

        combobox = b.lo_color
        for name in self.colornames:
            combobox.append_text(name)
        index = self.colornames.index(self.lo_color)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda *args: self.redo())

        b.lo_value.set_length(22)
        if self.lo_value is not None:
            b.lo_value.set_text(str(self.lo_value))
        b.lo_value.add_callback('activated', lambda *args: self.redo())

        b.redo.add_callback('activated', lambda *args: self.redo())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # start ruler drawing operation
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()
        if not (self.hi_value is None):
            self.redo()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.fv.show_status("Enter a value for saturation limit")

    def stop(self):
        self.arrsize = None
        self.rgbobj.set_data(self.rgbarr)

        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        self.canvas.update_canvas(whence=0)  # Force redraw
        #self.canvas.ui_set_active(False)
        self.fv.show_status("")

    def redo(self):
        hi_value_s = self.w.hi_value.get_text().strip()
        if len(hi_value_s) > 0:
            self.hi_value = float(hi_value_s)
        else:
            self.hi_value = None

        lo_value_s = self.w.lo_value.get_text().strip()
        if len(lo_value_s) > 0:
            self.lo_value = float(lo_value_s)
        else:
            self.lo_value = None
        self.logger.debug("set lo=%s hi=%s" % (self.lo_value, self.hi_value))

        self.opacity = self.w.opacity.get_value()
        self.logger.debug("set alpha to %f" % (self.opacity))

        # look up the colors
        self.hi_color = self.colornames[self.w.hi_color.get_index()]
        try:
            rh, gh, bh = colors.lookup_color(self.hi_color)
        except KeyError:
            self.fv.show_error("No such color found: '%s'" % (self.hi_color))

        self.lo_color = self.colornames[self.w.lo_color.get_index()]
        try:
            rl, gl, bl = colors.lookup_color(self.lo_color)
        except KeyError:
            self.fv.show_error("No such color found: '%s'" % (self.lo_color))

        image = self.fitsimage.get_vip()
        if image is None:
            return

        (x1, y1), (x2, y2) = self.fitsimage.get_limits()
        data = image.cutout_data(x1, y1, x2, y2)

        self.logger.debug("preparing RGB image")
        #wd, ht = image.get_size()
        ht, wd = data.shape[:2]
        if (wd, ht) != self.arrsize:
            rgbarr = np.zeros((ht, wd, 4), dtype=np.uint8)
            self.arrsize = (wd, ht)
            self.rgbobj.set_data(rgbarr)

        else:
            rgbarr = self.rgbobj.get_data()

        # Set array to the desired saturation color
        rc = self.rgbobj.get_slice('R')
        gc = self.rgbobj.get_slice('G')
        bc = self.rgbobj.get_slice('B')
        ac = self.rgbobj.get_slice('A')

        self.logger.debug("Calculating alpha channel")
        # set alpha channel according to saturation limit
        try:
            #data = image.get_data()
            ac[:] = 0
            if self.hi_value is not None:
                idx = data >= self.hi_value
                rc[idx] = int(rh * 255)
                gc[idx] = int(gh * 255)
                bc[idx] = int(bh * 255)
                ac[idx] = int(self.opacity * 255)
            if self.lo_value is not None:
                idx = data <= self.lo_value
                rc[idx] = int(rl * 255)
                gc[idx] = int(gl * 255)
                bc[idx] = int(bl * 255)
                ac[idx] = int(self.opacity * 255)
        except Exception as e:
            self.logger.error("Error setting alpha channel: %s" % (str(e)))

        if self.canvas_img is None:
            self.logger.debug("Adding image to canvas")
            self.canvas_img = self.dc.Image(x1, y1, self.rgbobj)
            self.canvas.add(self.canvas_img)
        else:
            self.logger.debug("Updating canvas image")
            self.canvas_img.set_image(self.rgbobj)

        self.logger.debug("redrawing canvas")
        self.canvas.update_canvas(whence=0)

        self.logger.debug("redo completed")

    def clear(self, canvas, button, data_x, data_y):
        self.canvas_img = None
        self.canvas.delete_all_objects()
        return False

    def __str__(self):
        return 'overlays'

# END
