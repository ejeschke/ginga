#
# Histogram.py -- Histogram plugin for Ginga fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Nov 16 13:11:05 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from QtHelp import QtGui, QtCore
import QtHelp

import FitsImageCanvasTypesQt as CanvasTypes
import Plot
import GingaPlugin

class Histogram(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Histogram, self).__init__(fv, fitsimage)

        self.layertag = 'histogram-canvas'
        self.histtag = None
        self.histcolor = 'aquamarine'

        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('rectangle', color='cyan', linestyle='dash',
                            drawdims=True)
        canvas.set_callback('draw-event', self.histogram)
        canvas.set_callback('button-press', self.drag)
        canvas.set_callback('motion', self.drag)
        canvas.set_callback('button-release', self.update)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

    def build_gui(self, container):
        # Splitter is just to provide a way to size the graph
        # to a reasonable size
        vpaned = QtGui.QSplitter()
        vpaned.setOrientation(QtCore.Qt.Vertical)
        
        # Make the cuts plot
        twidget = QtHelp.VBox()
        vbox1 = twidget.layout()
        vbox1.setContentsMargins(4, 4, 4, 4)
        vbox1.setSpacing(2)

        msgFont = QtGui.QFont("Sans", 14)
        tw = QtGui.QLabel()
        tw.setFont(msgFont)
        tw.setWordWrap(True)
        self.tw = tw

        fr = QtHelp.Frame("Instructions")
        fr.layout().addWidget(tw, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)
        
        self.plot = Plot.Plot(self.logger)
        w = self.plot.get_widget()
        vbox1.addWidget(w, stretch=1, alignment=QtCore.Qt.AlignTop)

        btns = QtHelp.HBox()
        layout= btns.layout()
        layout.setSpacing(3)
        #btns.set_child_size(15, -1)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(lambda w: self.close())

        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vpaned.addWidget(twidget)
        vpaned.addWidget(QtGui.QLabel(''))

        container.addWidget(vpaned, stretch=1)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def instructions(self):
        self.tw.setText("""Draw (or redraw) a region with the right mouse button.  Click or drag left mouse button to reposition region.""")
            
    def start(self):
        self.instructions()
        self.plot.set_titles(rtitle="Histogram")

        # insert canvas, if not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        #self.canvas.deleteAllObjects()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a rectangle with the right mouse button")
        if self.histtag:
            self.redo()
        
    def stop(self):
        # remove the rect from the canvas
        ## try:
        ##     self.canvas.deleteObjectByTag(self.histtag, redraw=False)
        ## except:
        ##     pass
        ##self.histtag = None
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.fv.showStatus("")
        
    def redo(self):
        obj = self.canvas.getObjectByTag(self.histtag)
        if obj.kind != 'compound':
            return True
        bbox = obj.objects[0]
        
        # Do histogram on the points within the rect
        y, x = self.fitsimage.histogram(int(bbox.x1), int(bbox.y1),
                                        int(bbox.x2), int(bbox.y2))
        x = x[:-1]
        self.plot.clear()
        self.plot.plot(x, y, xtitle="Pixel value", ytitle="Number",
                           title="Pixel Value Distribution")
        self.fv.showStatus("Click or drag left mouse button to move region")
        return True
    
    def update(self, canvas, button, data_x, data_y):
        if not (button == 0x1):
            return
        
        obj = self.canvas.getObjectByTag(self.histtag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = bbox.x1+dx, bbox.y1+dy, bbox.x2+dx, bbox.y2+dy
        
        try:
            canvas.deleteObjectByTag(self.histtag, redraw=False)
        except:
            pass

        tag = canvas.add(CanvasTypes.Rectangle(x1, y1, x2, y2,
                                               color='cyan',
                                               linestyle='dash'))

        self.histogram(canvas, tag)

    def drag(self, canvas, button, data_x, data_y):
        if not (button == 0x1):
            return
        
        obj = self.canvas.getObjectByTag(self.histtag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = bbox.x1+dx, bbox.y1+dy, bbox.x2+dx, bbox.y2+dy

        if obj.kind == 'compound':
            try:
                canvas.deleteObjectByTag(self.histtag, redraw=False)
            except:
                pass

            self.histtag = canvas.add(CanvasTypes.Rectangle(x1, y1, x2, y2,
                                                            color='cyan',
                                                            linestyle='dash'))
        else:
            bbox.x1, bbox.y1, bbox.x2, bbox.y2 = x1, y1, x2, y2
            canvas.redraw(whence=3)

    
    def histogram(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if obj.kind != 'rectangle':
            return True
        canvas.deleteObjectByTag(tag, redraw=False)

        if self.histtag:
            try:
                canvas.deleteObjectByTag(self.histtag, redraw=False)
            except:
                pass

        tag = canvas.add(CanvasTypes.CompoundObject(
            CanvasTypes.Rectangle(obj.x1, obj.y1, obj.x2, obj.y2,
                                  color=self.histcolor),
            CanvasTypes.Text(obj.x1, obj.y2+4, "Histogram",
                             color=self.histcolor)))
        self.histtag = tag

        return self.redo()
    
    def __str__(self):
        return 'histogram'
    
# END
