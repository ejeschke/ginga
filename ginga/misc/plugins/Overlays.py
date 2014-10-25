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
from ginga.misc import Widgets, CanvasTypes

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
        self.sat_color = 'red'
        self.sat_value = None
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

        fr = Widgets.Frame("Instructions")
        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=0)
        
        fr = Widgets.Frame("Overlays")

        captions = (('Sat color:', 'label', 'Sat color', 'combobox'),
                    ('Saturation:', 'label', 'Sat value', 'entry'),
                    ('Redo', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        combobox = b.sat_color
        for name in self.colornames:
            combobox.append_text(name)
        index = self.colornames.index(self.sat_color)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda *args: self.redo())

        b.sat_value.set_length(22)
        if self.sat_value != None:
            b.sat_value.set_text(str(self.sat_value))
        b.sat_value.add_callback('activated', lambda *args: self.redo())

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
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        self.resume()
        if self.sat_value != None:
            self.redo()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        #self.canvas.ui_setActive(True)
        self.fv.showStatus("Enter a value for saturation limit")
        
    def stop(self):
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        #self.canvas.ui_setActive(False)
        self.fv.showStatus("")
        
    def redo(self):
        self.sat_value = float(self.w.sat_value.get_text())
        self.logger.debug("set max to %f" % (self.sat_value))

        # look up the color
        self.sat_color = self.colornames[self.w.sat_color.get_index()]
        try:
            r, g, b = colors.lookup_color(self.sat_color)
        except KeyError:
            self.fv.show_error("No such color found: '%s'" % (self.sat_color))
        
        image = self.fitsimage.get_image()
        if image == None:
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
        self.rgbobj.set_color(r, g, b)

        self.logger.debug("Calculating alpha channel")
        # set alpha channel according to saturation limit
        try:
            data = image.get_data()
            alpha = self.rgbobj.get_slice('A')
            alpha[:] = 0
            alpha[data >= self.sat_value] = 255
        except Exception as e:
            self.logger.error("Error setting alpha channel: %s" % (str(e)))
            
        if self.canvas_img == None:
            self.logger.debug("Adding image to canvas")
            self.canvas_img = CanvasTypes.Image(0, 0, self.rgbobj)
            self.canvas.add(self.canvas_img, redraw=False)
        self.logger.debug("redrawing canvas")
        self.fitsimage.redraw(whence=0)

        self.logger.debug("redo completed")

    def clear(self, canvas, button, data_x, data_y):
        self.canvas.deleteAllObjects()
        return False

    def __str__(self):
        return 'overlays'
    
#END
