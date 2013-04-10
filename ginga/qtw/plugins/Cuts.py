#
# Cuts.py -- Cuts plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

from ginga.qtw import FitsImageCanvasTypesQt as CanvasTypes
from ginga.qtw import Plot
from ginga import GingaPlugin

import numpy

class Cuts(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Cuts, self).__init__(fv, fitsimage)

        self.cutscolor = 'limegreen'
        self.layertag = 'cuts-canvas'
        self.cutstag = None
        self.tags = ['None']
        self.count = 0
        self.colors = ['green', 'red', 'blue', 'cyan', 'pink', 'magenta']
        #self.move_together = True

        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('line', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('button-press', self.buttondown_cb)
        canvas.set_callback('motion', self.motion_cb)
        canvas.set_callback('button-release', self.buttonup_cb)
        canvas.set_callback('key-press', self.keydown)
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
        
        self.plot = Plot.Cuts(self.logger)
        w = self.plot.get_widget()
        vbox1.addWidget(w, stretch=1, alignment=QtCore.Qt.AlignTop)

        hbox = QtHelp.HBox()
        hbox.setSpacing(4)

        # control for selecting a cut
        combobox = QtHelp.ComboBox()
        for tag in self.tags:
            combobox.append_text(tag)
        if self.cutstag == None:
            combobox.setCurrentIndex(0)
        else:
            combobox.show_text(self.cutstag)
        combobox.activated.connect(self.cut_select_cb)
        self.w.cuts = combobox
        combobox.setToolTip("Select a cut")
        hbox.addWidget(combobox)

        btn = QtGui.QPushButton("Delete")
        btn.clicked.connect(self.delete_cut_cb)
        btn.setToolTip("Delete selected cut")
        hbox.addWidget(btn)
        
        btn = QtGui.QPushButton("Delete All")
        btn.clicked.connect(self.delete_all)
        btn.setToolTip("Clear all cuts")
        hbox.addWidget(btn)
        
        ## btn = QtGui.CheckBox("Move together")
        ## #btn.stateChanged.connect(self.movetogether_cb)
        ## btn.setChecked(self.move_together)
        ## btn.setToolTip("Move cuts as a group")
        ## hbox.addWidget(btn)
        
        vbox1.addWidget(hbox, stretch=0, alignment=QtCore.Qt.AlignLeft)
 
        btns = QtHelp.HBox()
        layout= btns.layout()
        layout.setSpacing(3)
        #btns.set_child_size(15, -1)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)

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
        self.tw.setText("""Draw (or redraw) a line with the right mouse button.  Click or drag left button to reposition line.""")
            
    def start(self):
        # start line cuts operation
        self.instructions()
        self.plot.set_titles(rtitle="Cuts")

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
        self.fv.showStatus("Draw a line with the right mouse button")
        self.redo()

    def stop(self):
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.fv.showStatus("")

    def select_cut(self, tag):
        # deselect the current selected cut, if there is one
        if self.cutstag != None:
            try:
                obj = self.canvas.getObjectByTag(self.cutstag)
                #obj.setAttrAll(color=self.mark_color)
            except:
                # old object may have been deleted
                pass
            
        self.cutstag = tag
        if tag == None:
            self.w.cuts.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.cuts.show_text(tag)
        obj = self.canvas.getObjectByTag(tag)
        #obj.setAttrAll(color=self.select_color)

        #self.redo()
        
    def cut_select_cb(self, index):
        tag = self.tags[index]
        if index == 0:
            tag = None
        self.select_cut(tag)

    def pan2mark_cb(self, w):
        self.pan2mark = w.get_active()
        
    def delete_cut_cb(self):
        tag = self.cutstag
        if tag == None:
            return
        index = self.tags.index(tag)
        self.canvas.deleteObjectByTag(tag)
        self.w.cuts.removeItem(index)
        self.tags.remove(tag)
        idx = len(self.tags) - 1
        tag = self.tags[idx]
        self.select_cut(tag)
        self.redo()
        
    def delete_all(self):
        self.canvas.deleteAllObjects()
        self.w.cuts.clear()
        self.tags = ['None']
        self.w.cuts.append_text('None')
        self.w.cuts.setCurrentIndex(0)
        self.cutstag = None
        self.redo()
        
    def deleteCutsTag(self, tag, redraw=False):
        try:
            self.canvas.deleteObjectByTag(tag, redraw=redraw)
        except:
            pass
        try:
            self.tags.remove(tag)
        except:
            pass
        if tag == self.cutstag:
            #self.unhighlightTag(tag)
            if len(self.tags) == 0:
                self.cutstag = None
            else:
                self.cutstag = self.tags[0]
                #self.highlightTag(self.cutstag)
        
    def addCutsTag(self, tag, select=False):
        if not tag in self.tags:
            self.tags.append(tag)
            self.w.cuts.append_text(tag)

        if select:
            if self.cutstag != None:
                #self.unhighlightTag(self.cutstag)
                pass
            self.cutstag = tag
            self.w.cuts.show_text(tag)
            #self.highlightTag(self.cutstag)
        
    def replaceCutsTag(self, oldtag, newtag, select=False):
        self.addCutsTag(newtag, select=select)
        self.deleteCutsTag(oldtag)
        
    def _redo(self, cutstag, color):
        obj = self.canvas.getObjectByTag(cutstag)
        if obj.kind != 'compound':
            return True
        line = obj.objects[0]
        line.color = color
        text = obj.objects[1]
        text.color = color
        
        # Get points on the line
        points = self.fitsimage.get_pixels_on_line(int(line.x1), int(line.y1),
                                                   int(line.x2), int(line.y2))
        points = numpy.array(points)
        self.plot.cuts(points, xtitle="Line Index", ytitle="Pixel Value",
                       color=color)
        return True
    
    def redo(self):
        self.plot.clear()
        idx = 0
        for cutstag in self.tags:
            if cutstag != 'None':
                color = self.colors[idx]
                self._redo(cutstag, color)
            idx = (idx+1) % len(self.colors)

        self.canvas.redraw(whence=3)
        self.fv.showStatus("Click or drag left mouse button to reposition cuts")
        return True

    def _movecut(self, obj, data_x, data_y):
        if obj.kind == 'compound':
            line = obj.objects[0]
            lbl  = obj.objects[1]
        elif obj.kind == 'line':
            line = obj
            lbl = None
        else:
            return True
        
        # calculate center of line
        wd = line.x2 - line.x1
        dw = wd // 2
        ht = line.y2 - line.y1
        dh = ht // 2
        x, y = line.x1 + dw, line.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        x1, y1, x2, y2 = line.x1 + dx, line.y1 + dy, line.x2 + dx, line.y2 + dy

        line.x1, line.y1, line.x2, line.y2 = x1, y1, x2, y2
        if lbl:
            lbl.x += dx
            lbl.y += dy
            
    def buttondown_cb(self, canvas, button, data_x, data_y):
        return self.motion_cb(canvas, button, data_x, data_y)
    
    def motion_cb(self, canvas, button, data_x, data_y):
        if not (button == 0x1):
            return

        obj = self.canvas.getObjectByTag(self.cutstag)
        if obj.kind == 'compound':
            line = obj.objects[0]
            lbl  = obj.objects[1]
        elif obj.kind == 'line':
            line = obj
            lbl = None
        else:
            return

        line.linestyle = 'dash'
        self._movecut(obj, data_x, data_y)

        canvas.redraw(whence=3)
    
    def buttonup_cb(self, canvas, button, data_x, data_y):
        if not (button == 0x1):
            return
        
        obj = self.canvas.getObjectByTag(self.cutstag)
        if obj.kind == 'compound':
            line = obj.objects[0]
        elif obj.kind == 'line':
            line = obj
        else:
            return

        line.linestyle = 'solid'
        self._movecut(obj, data_x, data_y)
        
        self.redo()
    
    def keydown(self, canvas, keyname):
        if keyname == 'space':
            self.select_cut(None)
            
    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if obj.kind != 'line':
            return True
        canvas.deleteObjectByTag(tag, redraw=False)

        # calculate center of line
        wd = obj.x2 - obj.x1
        dw = wd // 2
        ht = obj.y2 - obj.y1
        dh = ht // 2
        x, y = obj.x1 + dw + 4, obj.y1 + dh + 4

        if self.cutstag:
            # Replacing a cut
            print "replacing cut position"
            cutobj = canvas.getObjectByTag(self.cutstag)
            line = cutobj.objects[0]
            line.x1, line.y1, line.x2, line.y2 = obj.x1, obj.y1, obj.x2, obj.y2
            text = cutobj.objects[1]
            text.x, text.y = x, y

        else:
            # Adding new cut
            print "adding cut position"
            self.count += 1
            tag = "cuts%d" % (self.count)
            canvas.add(CanvasTypes.CompoundObject(
                CanvasTypes.Line(obj.x1, obj.y1, obj.x2, obj.y2,
                                 color='cyan',
                                 cap='ball'),
                CanvasTypes.Text(x, y, "cuts%d" % self.count,
                                 color='cyan')),
                       tag=tag)

            self.addCutsTag(tag, select=True)

        print "redoing cut plots"
        return self.redo()
  
    def __str__(self):
        return 'cuts'
    
#END
