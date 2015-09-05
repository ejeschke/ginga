#
# Overlays.py -- Overlays plugin for Ginga FITS viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga import GingaPlugin, RGBImage, colors
from ginga.gw import Widgets

class Overlays(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Overlays, self).__init__(fv, fitsimage)

        self.layertag = 'overlays-canvas'

        self.dc = fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.colornames = colors.get_colors()
        # TODO: there is some problem with basic "red", at least on Linux
        #self.hi_color = 'red'
        self.hi_color = 'palevioletred'
        self.hi_value = None
        self.lo_color = 'blue'
        self.lo_value = None
        self.opacity = 0.5
        self.arrsize = None
        self.rgbarr = numpy.zeros((1, 1, 4), dtype=numpy.uint8)
        self.rgbobj = RGBImage.RGBImage(self.rgbarr, logger=self.logger)
        self.canvas_img = None

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

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
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def instructions(self):
        self.tw.set_text("""Enter a limit for saturation.""")

    def start(self):
        self.instructions()
        # start ruler drawing operation
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()
        if not (self.hi_value is None):
            self.redo()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Enter a value for saturation limit")

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.deleteObjectByTag(self.layertag)
        except:
            pass
        #self.canvas.ui_setActive(False)
        self.fv.showStatus("")

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

        image = self.fitsimage.get_image()
        if image is None:
            return

        self.logger.debug("preparing RGB image")
        wd, ht = image.get_size()
        if (wd, ht) != self.arrsize:
            rgbarr = numpy.zeros((ht, wd, 4), dtype=numpy.uint8)
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
            data = image.get_data()
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
            self.canvas_img = self.dc.Image(0, 0, self.rgbobj)
            self.canvas.add(self.canvas_img)
        else:
            self.logger.debug("Updating canvas image")
            self.canvas_img.set_image(self.rgbobj)

        self.logger.debug("redrawing canvas")
        self.canvas.update_canvas()

        self.logger.debug("redo completed")

    def clear(self, canvas, button, data_x, data_y):
        self.canvas_img = None
        self.canvas.deleteAllObjects()
        return False

    def __str__(self):
        return 'overlays'

#END
