#
# Ruler.py -- Ruler plugin for Ginga FITS viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk
from ginga.gtkw import GtkHelp
from ginga import GingaPlugin

class Ruler(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Ruler, self).__init__(fv, fitsimage)

        self.rulecolor = 'green'
        self.layertag = 'ruler-canvas'
        self.ruletag = None

        self.dc = fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('ruler', color='cyan')
        canvas.set_callback('draw-event', self.wcsruler)
        canvas.set_callback('draw-down', self.clear)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.w = None
        self.unittypes = ('arcmin', 'pixels')
        self.units = 'arcmin'

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
        fr.show_all()
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)
        
        fr = gtk.Frame(label="Ruler")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Units', 'combobox'),)
        w, b = GtkHelp.build_info(captions)
        self.w = b

        combobox = b.units
        index = 0
        for name in self.unittypes:
            combobox.insert_text(index, name)
            index += 1
        index = self.unittypes.index(self.units)
        combobox.set_active(index)
        combobox.sconnect('changed', lambda w: self.set_units())

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

    def set_units(self):
        index = self.w.units.get_active()
        units = self.unittypes[index]
        self.canvas.set_drawtype('ruler', color='cyan', units=units)
        self.redo()
        return True

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def instructions(self):
        buf = self.tw.get_buffer()
        buf.set_text("""Draw (or redraw) a line with the right mouse button.  Display the Zoom tab to precisely see detail.""")
        self.tw.modify_font(self.msgFont)
            
    def start(self):
        self.instructions()
        # start ruler drawing operation
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        self.canvas.deleteAllObjects()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a ruler with the right mouse button")
        
    def stop(self):
        ## # remove the ruler from the canvas
        ## try:
        ##     self.canvas.deleteObjectByTag(self.ruletag, redraw=False)
        ## except:
        ##     pass
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        #self.canvas.ui_setActive(False)
        self.fv.showStatus("")
        
    def redo(self):
        obj = self.canvas.getObjectByTag(self.ruletag)
        if obj.kind != 'ruler':
            return True
        text_x, text_y, text_h = self.canvas.get_ruler_distances(obj.x1, obj.y1,
                                                                 obj.x2, obj.y2)
        obj.text_x = text_x
        obj.text_y = text_y
        obj.text_h = text_h
        self.canvas.redraw(whence=3)

    def clear(self, canvas, button, data_x, data_y):
        self.canvas.deleteAllObjects()
        return False

    def wcsruler(self, surface, tag):
        obj = self.canvas.getObjectByTag(tag)
        if obj.kind != 'ruler':
            return True
        # remove the old ruler
        try:
            self.canvas.deleteObjectByTag(self.ruletag, redraw=False)
        except:
            pass

        # change some characteristics of the drawn image and
        # save as the new ruler
        self.ruletag = tag
        obj.color = self.rulecolor
        obj.cap = 'ball'
        self.canvas.redraw(whence=3)
        
    def __str__(self):
        return 'ruler'
    
#END
