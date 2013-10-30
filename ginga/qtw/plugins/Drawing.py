#
# Drawing.py -- Drawing plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

from ginga.qtw import ImageViewCanvasTypesQt as CanvasTypes
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
        sw = QtGui.QScrollArea()

        twidget = QtHelp.VBox()
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                               QtGui.QSizePolicy.Fixed)
        twidget.setSizePolicy(sp)
        vbox1 = twidget.layout()
        vbox1.setContentsMargins(4, 4, 4, 4)
        vbox1.setSpacing(2)
        sw.setWidgetResizable(True)
        sw.setWidget(twidget)

        msgFont = self.fv.getFont("sansFont", 14)
        tw = QtGui.QLabel()
        tw.setFont(msgFont)
        tw.setWordWrap(True)
        self.tw = tw

        fr = QtHelp.Frame("Instructions")
        fr.layout().addWidget(tw, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)
        
        fr = QtHelp.Frame("Drawing")

        captions = (('Draw type', 'combobox'), ('Draw color', 'combobox'),
                    ('Clear canvas', 'button'))
        w, b = QtHelp.build_info(captions)
        self.w = b

        combobox = b.draw_type
        options = []
        index = 0
        for name in self.drawtypes:
            options.append(name)
            combobox.addItem(name)
            index += 1
        index = self.drawtypes.index(default_drawtype)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_drawparams)

        self.w.draw_color = b.draw_color
        combobox = b.draw_color
        options = []
        index = 0
        self.drawcolors = draw_colors
        for name in self.drawcolors:
            options.append(name)
            combobox.addItem(name)
            index += 1
        index = self.drawcolors.index(default_drawcolor)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_drawparams)

        b.clear_canvas.clicked.connect(self.clear_canvas)

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        container.addWidget(sw, stretch=1)


    def set_drawparams(self):
        index = self.w.draw_type.currentIndex()
        kind = self.drawtypes[index]
        index = self.w.draw_color.currentIndex()
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
        self.tw.setText("""Draw a figure with the right mouse button.""")
            
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
