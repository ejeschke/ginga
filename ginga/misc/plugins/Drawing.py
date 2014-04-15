#
# Drawing.py -- Drawing plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga import colors
from ginga.misc import Widgets, CanvasTypes

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
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(msgFont)
        self.tw = tw

        fr = Widgets.Frame("Instructions")
        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=0)
        
        fr = Widgets.Frame("Drawing")

        captions = (('Draw type:', 'label', 'Draw type', 'combobox'),
                    ('Draw color:', 'label', 'Draw color', 'combobox'),
                    ('Clear canvas', 'button'))
        w, b = Widgets.build_info(captions)
        self.w = b

        combobox = b.draw_type
        options = []
        index = 0
        for name in self.drawtypes:
            options.append(name)
            combobox.append_text(name)
            index += 1
        index = self.drawtypes.index(default_drawtype)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams())

        self.w.draw_color = b.draw_color
        combobox = b.draw_color
        options = []
        index = 0
        self.drawcolors = draw_colors
        for name in self.drawcolors:
            options.append(name)
            combobox.append_text(name)
            index += 1
        index = self.drawcolors.index(default_drawcolor)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams())

        b.clear_canvas.add_callback('activated', lambda w: self.clear_canvas())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)
        
        top.add_widget(sw, stretch=1)
        
        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)


    def set_drawparams(self):
        index = self.w.draw_type.get_index()
        kind = self.drawtypes[index]
        index = self.w.draw_color.get_index()
        drawparams = { 'color': self.drawcolors[index],
                       }
        self.canvas.set_drawtype(kind, **drawparams)

    def clear_canvas(self):
        self.canvas.deleteAllObjects()
        
    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        
    def instructions(self):
        self.tw.set_text("""Draw a figure with the right mouse button.""")
            
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
