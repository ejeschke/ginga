#
# Ruler.py -- Ruler plugin for Ginga FITS viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.misc import Widgets, CanvasTypes

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
        
        fr = Widgets.Frame("Ruler")

        captions = (('Units:', 'label', 'Units', 'combobox'),)
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        combobox = b.units
        for name in self.unittypes:
            combobox.append_text(name)
        index = self.unittypes.index(self.units)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_units())

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

    def set_units(self):
        index = self.w.units.get_index()
        units = self.unittypes[index]
        self.canvas.set_drawtype('ruler', color='cyan', units=units)
        self.redo()
        return True

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True
        
    def instructions(self):
        self.tw.set_text("""Draw (or redraw) a line with the right mouse button.  Display the Zoom tab to precisely see detail.""")
            
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
