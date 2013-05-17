#
# Ruler.py -- Ruler plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

from ginga import GingaPlugin

class Ruler(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Ruler, self).__init__(fv, fitsimage)

        self.rulecolor = 'lightgreen'
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
        
        fr = QtHelp.Frame("Ruler")

        captions = (('Units', 'combobox'),)
        w, b = QtHelp.build_info(captions)
        self.w = b

        combobox = b.units
        for name in self.unittypes:
            combobox.addItem(name)
        index = self.unittypes.index(self.units)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_units)

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)
        #btns.set_child_size(15, -1)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        container.addWidget(sw, stretch=1)

    def set_units(self):
        index = self.w.units.currentIndex()
        units = self.unittypes[index]
        self.canvas.set_drawtype('ruler', color='cyan', units=units)
        self.redo()
        return True

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def instructions(self):
        self.tw.setText("""Draw (or redraw) a line with the right mouse button.  Display the Zoom tab to precisely see detail.""")
        self.tw.show()
            
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
