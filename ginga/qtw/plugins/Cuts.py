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

from ginga.qtw import Plot
from ginga.misc.plugins import CutsBase


class Cuts(CutsBase.CutsBase):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Cuts, self).__init__(fv, fitsimage)

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

        msgFont = self.fv.getFont("sansFont", 14)
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
        
        combobox = QtHelp.ComboBox()
        for cuttype in self.cuttypes:
            combobox.append_text(cuttype)
        self.w.cuts_type = combobox
        index = self.cuttypes.index(self.cuttype)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_cutsdrawtype_cb)
        combobox.setToolTip("Choose the cut type")
        hbox.addWidget(combobox)

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

    def instructions(self):
        self.tw.setText("""Draw (or redraw) a line with the right mouse button.  Click or drag left button to reposition line.""")
            
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
        
    def set_cutsdrawtype_cb(self, index):
        self.cuttype = self.cuttypes[index]
        if self.cuttype in ('free', ):
            self.canvas.set_drawtype('line', color='cyan', linestyle='dash')
        else:
            self.canvas.set_drawtype('rectangle', color='cyan',
                                     linestyle='dash')

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
        if tag == 'None':
            tag = None
        self.select_cut(tag)
        if tag != None:
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
        
    def __str__(self):
        return 'cuts'
    
#END
