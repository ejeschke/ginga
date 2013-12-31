#
# Errors.py -- Error reporting plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

from ginga import GingaPlugin

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

class Errors(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Errors, self).__init__(fv)

    def build_gui(self, container):
        self.msgFont = self.fv.getFont("fixedFont", 12)

        self.msgList = QtGui.QWidget()
        vbox = QtGui.QGridLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        self.msgList.setLayout(vbox)
        
        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(True)
        #sw.set_border_width(2)
        sw.setWidget(self.msgList)

        cw = container.get_widget()
        cw.addWidget(sw, stretch=1)

        hbox = QtHelp.HBox()
        btn = QtGui.QPushButton("Remove All")
        btn.clicked.connect(self.remove_all)
        hbox.addWidget(btn, stretch=0)
        cw.addWidget(hbox, stretch=0)

        self.widgetList = []

    def add_error(self, errmsg):
        vbox = QtHelp.VBox()
        tw = QtGui.QTextEdit()
        tw.setReadOnly(True)
        tw.setCurrentFont(self.msgFont)

        tw.setText(errmsg)
        vbox.addWidget(tw, stretch=1)

        hbox = QtHelp.HBox()
        btn = QtGui.QPushButton("Remove")
        btn.clicked.connect(lambda: self.remove_error(vbox))
        hbox.addWidget(btn, stretch=0)
        # Add the time the error occurred
        ts = time.strftime("%m/%d %H:%M:%S", time.localtime())
        lbl = QtGui.QLabel(ts)
        hbox.addWidget(lbl, stretch=0)
        vbox.addWidget(hbox, stretch=0)
        
        layout = self.msgList.layout()
        layout.addWidget(vbox, layout.rowCount(), 0,
                         alignment=QtCore.Qt.AlignTop)
        self.widgetList.append(vbox)
        # TODO: force scroll to bottom 

    def remove_error(self, child):
        layout = self.msgList.layout()
        #QtHelp.removeWidget(layout, child)
        layout.removeWidget(child)
        #child.setVisible(False)
        # This is necessary to actually delete the widget visibly
        child.setParent(None)
        try:
            self.widgetList.remove(child)
            child.delete()
        except:
            pass
        
    def remove_all(self):
        layout = self.msgList.layout()
        for child in list(self.widgetList):
            self.remove_error(child)
            
    def __str__(self):
        return 'errors'
    
#END
