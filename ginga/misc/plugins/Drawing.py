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
        self.drawtypes = list(canvas.get_drawtypes())
        self.drawcolors = draw_colors
        self.linestyles = ['solid', 'dash']

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

        captions = (("Draw type:", 'label', "Draw type", 'combobox'),
                    ("Draw color:", 'label', "Draw color", 'combobox'),
                    ("Line width:", 'label', "Line width", 'spinbutton'),
                    ("Line style:", 'label', "Line style", 'combobox'),
                    ("Alpha:", 'label', "Alpha", 'spinfloat'),
                    ("Fill", 'checkbutton', "Fill color", 'combobox'),
                    ("Fill Alpha:", 'label', "Fill Alpha", 'spinfloat'),
                    ("Text:", 'label', "Text", 'entry'),
                    ("Clear canvas", 'button')
                    )
        w, b = Widgets.build_info(captions)
        self.w = b

        combobox = b.draw_type
        for name in self.drawtypes:
            combobox.append_text(name)
        index = self.drawtypes.index(default_drawtype)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams())

        combobox = b.draw_color
        self.drawcolors = draw_colors
        for name in self.drawcolors:
            combobox.append_text(name)
        index = self.drawcolors.index(default_drawcolor)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams())

        combobox = b.fill_color
        for name in self.drawcolors:
            combobox.append_text(name)
        index = self.drawcolors.index(default_drawcolor)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams())

        b.line_width.set_limits(0, 10, 1)
        #b.line_width.set_decimals(0)
        b.line_width.set_value(1)
        b.line_width.add_callback('value-changed', lambda w, val: self.set_drawparams())
        
        combobox = b.line_style
        for name in self.linestyles:
            combobox.append_text(name)
        combobox.set_index(0)
        combobox.add_callback('activated', lambda w, idx: self.set_drawparams())

        b.fill.add_callback('activated', lambda w, tf: self.set_drawparams())
        b.fill.set_state(False)

        b.alpha.set_limits(0.0, 1.0, 0.1)
        b.alpha.set_decimals(2)
        b.alpha.set_value(1.0)
        b.alpha.add_callback('value-changed', lambda w, val: self.set_drawparams())
        
        b.fill_alpha.set_limits(0.0, 1.0, 0.1)
        b.fill_alpha.set_decimals(2)
        b.fill_alpha.set_value(0.3)
        b.fill_alpha.add_callback('value-changed', lambda w, val: self.set_drawparams())

        b.text.add_callback('activated', lambda w: self.set_drawparams())
        b.text.set_text('EDIT ME')
        b.text.set_length(60)
        
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
        color = self.drawcolors[index]
        fill = self.w.fill.get_state()
        index = self.w.fill_color.get_index()
        fillcolor = self.drawcolors[index]
        fillalpha = self.w.fill_alpha.get_value()
        alpha = self.w.alpha.get_value()
        index = self.w.line_style.get_index()
        linestyle = self.linestyles[index]
        linewidth = self.w.line_width.get_value()
        drawtext = self.w.text.get_text()

        params = { 'color': color,
                   'alpha': alpha,
                   }
        if not kind in ('text',):
            params['linestyle'] = linestyle
            params['linewidth'] = linewidth
        
        if kind in ('circle', 'rectangle', 'polygon', 'triangle'):
            params['fill'] = fill
            params['fillcolor'] = fillcolor
            params['fillalpha'] = fillalpha

        self.canvas.set_drawtext(drawtext)
        self.canvas.set_drawtype(kind, **params)

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
        ##     self.fitsimage.delete_object_by_tag(self.layertag)
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
