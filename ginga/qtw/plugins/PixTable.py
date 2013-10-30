#
# PixTable.py -- Pixel Table plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

from ginga.qtw import ImageViewCanvasTypesQt as CanvasTypes
from ginga import GingaPlugin


class PixTable(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(PixTable, self).__init__(fv, fitsimage)

        self.layertag = 'pixtable-canvas'
        self.pan2mark = False

        canvas = CanvasTypes.DrawingCanvas()
        ## canvas.enable_draw(True)
        ## canvas.set_drawtype('point', color='pink')
        ## canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('cursor-down', self.btndown_cb)
        canvas.set_callback('none-move', self.motion_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        # For pixel table
        self.pixtbl_radius = 2
        self.sizes = [ 1, 2, 3, 4 ]
        self.lastx = 0
        self.lasty = 0

        # For "marks" feature
        self.mark_radius = 10
        self.mark_style = 'cross'
        self.mark_color = 'purple'
        self.select_color = 'cyan'
        self.marks = ['None']
        self.mark_index = 0
        self.mark_selected = None

    def build_gui(self, container):
        # Splitter is just to provide a way to size the graph
        # to a reasonable size
        vpaned = QtGui.QSplitter()
        vpaned.setOrientation(QtCore.Qt.Vertical)
        
        # Make the PixTable plot
        twidget = QtHelp.VBox()
        vbox1 = twidget.layout()
        vbox1.setContentsMargins(4, 4, 4, 4)
        vbox1.setSpacing(2)

        fr = QtHelp.Frame("Pixel Values")
        
        # Make the cuts plot
        msgFont = self.fv.getFont('fixedFont', 10)
        tw = QtGui.QLabel()
        tw.setFont(msgFont)
        tw.setWordWrap(False)
        self.tw = tw
        fr.layout().addWidget(tw, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox1.addWidget(fr, stretch=1, alignment=QtCore.Qt.AlignTop)

        hbox = QtHelp.HBox()
        layout = hbox.layout()
        layout.setSpacing(4)

        cbox1 = QtHelp.ComboBox()
        index = 0
        for i in self.sizes:
            j = 1 + i*2
            name = "%dx%d" % (j, j)
            cbox1.addItem(name)
            index += 1
        index = self.sizes.index(self.pixtbl_radius)
        cbox1.setCurrentIndex(index)
        cbox1.activated.connect(lambda val: self.set_cutout_size(cbox1))
        cbox1.setToolTip("Select size of pixel table")
        layout.addWidget(cbox1, stretch=0, alignment=QtCore.Qt.AlignLeft)

        # control for selecting a mark
        cbox2 = QtHelp.ComboBox()
        for tag in self.marks:
            cbox2.addItem(tag)
        if self.mark_selected == None:
            cbox2.setCurrentIndex(0)
        else:
            cbox2.show_text(lambda n: self.mark_selected(cbox2))
        cbox2.activated.connect(lambda n: self.mark_select_cb(cbox2))
        self.w.marks = cbox2
        cbox2.setToolTip("Select a mark")
        cbox2.setMinimumContentsLength(8)
        layout.addWidget(cbox2, stretch=0, alignment=QtCore.Qt.AlignLeft)

        btn1 = QtGui.QPushButton("Delete")
        btn1.clicked.connect(self.clear_mark_cb)
        btn1.setToolTip("Delete selected mark")
        layout.addWidget(btn1, stretch=0, alignment=QtCore.Qt.AlignLeft)
        
        btn2 = QtGui.QPushButton("Delete All")
        btn2.clicked.connect(self.clear_all)
        btn2.setToolTip("Clear all marks")
        layout.addWidget(btn2, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vbox1.addWidget(hbox, stretch=0, alignment=QtCore.Qt.AlignLeft)
        
        hbox = QtHelp.HBox()
        layout = hbox.layout()
        layout.setSpacing(4)

        btn3 = QtGui.QCheckBox("Pan to mark")
        btn3.setChecked(self.pan2mark)
        btn3.stateChanged.connect(lambda w: self.pan2mark_cb(btn3))
        btn3.setToolTip("Pan follows selected mark")
        layout.addWidget(btn3, stretch=0, alignment=QtCore.Qt.AlignLeft)
        
        vbox1.addWidget(hbox, stretch=0, alignment=QtCore.Qt.AlignLeft)
        
        hbox = QtHelp.HBox()
        layout = hbox.layout()
        layout.setSpacing(3)
        #btns.set_child_size(15, -1)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(hbox, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vpaned.addWidget(twidget)
        vpaned.addWidget(QtGui.QLabel(''))

        container.addWidget(vpaned, stretch=1)

    def select_mark(self, tag, pan=True):
        # deselect the current selected mark, if there is one
        if self.mark_selected != None:
            try:
                obj = self.canvas.getObjectByTag(self.mark_selected)
                obj.setAttrAll(color=self.mark_color)
            except:
                # old object may have been deleted
                pass
            
        self.mark_selected = tag
        if tag == None:
            self.w.marks.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.marks.show_text(tag)
        obj = self.canvas.getObjectByTag(tag)
        obj.setAttrAll(color=self.select_color)
        self.lastx = obj.objects[0].x
        self.lasty = obj.objects[0].y
        if self.pan2mark and pan:
            self.fitsimage.panset_xy(self.lastx, self.lasty, redraw=True)
        self.canvas.redraw(whence=3)

        self.redo()
        
    def mark_select_cb(self, w):
        index = w.currentIndex()
        tag = self.marks[index]
        if index == 0:
            tag = None
        self.select_mark(tag)

    def pan2mark_cb(self, w):
        self.pan2mark = w.checkState()
        
    def clear_mark_cb(self):
        tag = self.mark_selected
        if tag == None:
            return
        index = self.marks.index(tag)
        self.canvas.deleteObjectByTag(tag)
        self.w.marks.removeItem(index)
        self.marks.remove(tag)
        self.w.marks.setCurrentIndex(0)
        self.mark_selected = None
        
    def clear_all(self):
        self.canvas.deleteAllObjects()
        for index in len(self.marks):
            self.w.marks.removeItem(index)
        self.marks = ['None']
        self.w.marks.append_text('None')
        self.w.marks.setCurrentIndex(0)
        self.mark_selected = None
        
    def plot(self, data, x1, y1, x2, y2, data_x, data_y, radius,
             maxv=9):
        
        width, height = self.fitsimage.get_dims(data)

        maxval = numpy.nanmax(data)
        minval = numpy.nanmin(data)
        avgval = numpy.average(data)
        
        maxdigits = 9
        sep = '  '
        # make format string for a row
        fmt_cell = '%%%d.2f' % maxdigits
        fmt_r = (fmt_cell + sep) * width
        fmt_r = '%6d | ' + fmt_r

        fmt_h = (('%%%dd' % maxdigits) + sep) * width
        fmt_h = ('%6s | ') % '' + fmt_h
        t = tuple([i + x1 + 1 for i in xrange(width)])

        # format the buffer and insert into the tw
        l = [fmt_h % t]
        for i in xrange(height):
            t = tuple([y1 + i + 1] + list(data[i]))
            l.append(fmt_r % t)
        l.append('')

        # append statistics line
        fmt_stat = "  Min: %s  Max: %s  Avg: %s" % (fmt_cell, fmt_cell,
                                                  fmt_cell)
        l.append(fmt_stat % (minval, maxval, avgval))

        # update the text widget
        self.tw.setText('\n'.join(l))
    
    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def start(self):
        #self.plot.set_titles(rtitle="Pixel Values")

        # insert layer if it is not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)
        self.resume()

    def stop(self):
        # remove the canvas from the image
        self.canvas.ui_setActive(False)
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.plot = None
        
    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        self.canvas.ui_setActive(True)
        self.redo()
        
    def redo(self):
        if self.plot == None:
            return
        # cut out and set the pixel table data
        image = self.fitsimage.get_image()
        data, x1, y1, x2, y2 = image.cutout_radius(self.lastx, self.lasty,
                                                   self.pixtbl_radius)
        self.plot(data, x1, y1, x2, y2, self.lastx, self.lasty,
                  self.pixtbl_radius, maxv=9)

    def set_cutout_size(self, w):
        index = w.currentIndex()
        self.pixtbl_radius = self.sizes[index]
        
    def motion_cb(self, canvas, button, data_x, data_y):
        if self.mark_selected != None:
            return False
        if self.plot == None:
            return
        self.lastx, self.lasty = data_x, data_y
        self.redo()
        return False
        
    def btndown_cb(self, canvas, button, data_x, data_y):
        self.add_mark(data_x, data_y)
        return True

    def add_mark(self, data_x, data_y, radius=None, color=None, style=None):
        if not radius:
            radius = self.mark_radius
        if not color:
            color = self.mark_color
        if not style:
            style = self.mark_style

        self.logger.debug("Setting mark at %d,%d" % (data_x, data_y))
        self.mark_index += 1
        tag = 'mark%d' % (self.mark_index)
        tag = self.canvas.add(CanvasTypes.CompoundObject(
            CanvasTypes.Point(data_x, data_y, self.mark_radius,
                              style=style, color=color,
                              linestyle='solid'),
            CanvasTypes.Text(data_x + 10, data_y, "%d" % (self.mark_index),
                             color=color)),
                              tag=tag)
        self.marks.append(tag)
        self.w.marks.append_text(tag)
        self.select_mark(tag, pan=False)
        
        
    def __str__(self):
        return 'pixtable'
    
#END
        
