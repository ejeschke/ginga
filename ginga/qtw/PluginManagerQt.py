#
# PluginManagerQt.py -- Simple class to manage plugins.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.misc.PluginManager import PluginManagerBase, PluginManagerError

class PluginManager(PluginManagerBase):
    """
    This provides the GUI support methods for the PluginManager.
    See PluginManagerBase for the general logic of this class.
    """

    def set_widget(self, hbox):
        self.hbox = hbox
        
    def update_taskbar(self, localmode=True):
        ## with self.lock:
        if localmode:
            for child in self.hbox.get_children():
                #self.hbox.remove(child)
                child.hide()
        for name in self.active.keys():
            bnch = self.active[name]
            #self.hbox.pack_start(bnch.widget, expand=False, fill=False)
            bnch.widget.show()

    def add_taskbar(self, bnch):
        lblname = bnch.lblname
        lbl = QtGui.QLabel(lblname)
        lbl.setAlignment(QtCore.Qt.AlignHCenter)
        lbl.setToolTip("Right click for menu")
        lbl.setSizePolicy(QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Minimum)
        lbl.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        self.hbox.addWidget(lbl, stretch=0,
                            alignment=QtCore.Qt.AlignLeft)

        lbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

        lname = bnch.pInfo.name.lower()
        menu = QtGui.QMenu()
        item = QtGui.QAction("Focus", menu)
        item.triggered.connect(lambda: self.set_focus(lname))
        menu.addAction(item)
        item = QtGui.QAction("Unfocus", menu)
        item.triggered.connect(lambda: self.clear_focus(lname))
        menu.addAction(item)
        item = QtGui.QAction("Stop", menu)
        item.triggered.connect(lambda: self.deactivate(lname))
        menu.addAction(item)

        def on_context_menu(point):
            menu.exec_(lbl.mapToGlobal(point))

        lbl.customContextMenuRequested.connect(on_context_menu)
        # better than making a whole new subclass just to get a label to
        # respond to a mouse click
        lbl.mousePressEvent = lambda event: self.set_focus_cb(event, lname)

        bnch.setvals(widget=lbl, label=lbl, menu=menu)

    def set_focus_cb(self, event, lname):
        if event.button() == 1:
            event.accept()
            self.set_focus(lname)
    
    def remove_taskbar(self, bnch):
        self.logger.debug("removing widget from taskbar")
        QtHelp.removeWidget(self.hbox, bnch.widget)
        bnch.widget = None
        bnch.label = None

    def highlight_taskbar(self, bnch):
        self.logger.debug("highlighting widget")
        bnch.label.setStyleSheet("QLabel { background-color: %s; }" % (
            self.focuscolor))

    def unhighlight_taskbar(self, bnch):
        self.logger.debug("unhighlighting widget")
        bnch.label.setStyleSheet("QLabel { background-color: grey; }")

    def finish_gui(self, pInfo, vbox):
        pass
        
    def dispose_gui(self, pInfo):
        vbox = pInfo.widget
        pInfo.widget = None
        #vbox.get_widget().destroyLater()

#END
