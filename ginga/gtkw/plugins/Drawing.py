#
# Drawing.py -- Drawing plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk
from ginga.gtkw import GtkHelp

from ginga.gtkw import ImageViewCanvasTypesGtk as CanvasTypes
from ginga import GingaPlugin
from ginga import colors

draw_colors = colors.get_colors()

default_drawtype = 'point'
default_drawcolor = 'blue'

class Drawing(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Drawing, self).__init__(fv, fitsimage)

        self.layertag = 'drawing-canvas'

        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('point', color='cyan')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.w = None
        self.drawtypes = canvas.get_drawtypes()
        self.drawcolors = draw_colors


    def build_gui(self, container):
        vbox1 = gtk.VBox()

        self.msgFont = self.fv.getFont("sansFont", 14)
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_WORD)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.modify_font(self.msgFont)
        self.tw = tw

        fr = gtk.Frame(label=" Instructions ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.set_label_align(0.1, 0.5)
        fr.add(tw)
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)
        
        fr = gtk.Frame(label="Drawing")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Draw type', 'combobox'), ('Draw color', 'combobox'),
                    ('Clear canvas', 'button'))
        w, b = GtkHelp.build_info(captions)
        self.w = b

        combobox = b.draw_type
        options = []
        index = 0
        for name in self.drawtypes:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        index = self.drawtypes.index(default_drawtype)
        combobox.set_active(index)
        combobox.sconnect('changed', lambda w: self.set_drawparams())

        self.w.draw_color = b.draw_color
        combobox = b.draw_color
        options = []
        index = 0
        self.drawcolors = draw_colors
        for name in self.drawcolors:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        index = self.drawcolors.index(default_drawcolor)
        combobox.set_active(index)
        combobox.sconnect('changed', lambda w: self.set_drawparams())

        b.clear_canvas.connect('clicked', lambda w: self.clear_canvas())
        fr.add(w)
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        vbox1.pack_start(btns, padding=4, fill=True, expand=False)

        vbox1.show_all()
        container.pack_start(vbox1, padding=0, fill=True, expand=False)


    def set_drawparams(self):
        index = self.w.draw_type.get_active()
        kind = self.drawtypes[index]
        index = self.w.draw_color.get_active()
        drawparams = { 'color': self.drawcolors[index],
                       }
        self.canvas.set_drawtype(kind, **drawparams)

    def clear_canvas(self):
        self.canvas.deleteAllObjects()
        
    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def instructions(self):
        buf = self.tw.get_buffer()
        buf.set_text("""Draw a figure with the right mouse button.""")
        self.tw.modify_font(self.msgFont)
            
    def start(self):
        self.instructions()
        self.set_drawparams()

        # insert layer if it is not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)
            
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a figure with the right mouse button")
        
    def stop(self):
        # remove the canvas from the image
        ## try:
        ##     self.fitsimage.deleteObjectByTag(self.layertag)
        ## except:
        ##     pass
        self.canvas.ui_setActive(False)
        self.fv.showStatus("")

    def redo(self):
        pass

    def draw_cb(self, fitsimage, tag):
        # TODO: record information about objects drawn?
        pass

    def __str__(self):
        return 'drawing'
    
#END
