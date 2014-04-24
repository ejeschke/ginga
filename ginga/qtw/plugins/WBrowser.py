#
# WBrowser.py -- Web Browser plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
from ginga import GingaPlugin

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.Control import packageHome

has_webkit = False
try:
    from ginga.qtw.QtHelp import QWebView
    has_webkit = True
except ImportError:
    pass

class WBrowser(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(WBrowser, self).__init__(fv)

        self.browser = None

    def build_gui(self, container):
        if not has_webkit:
            self.browser = QtGui.QLabel("Please install the python-webkit package to enable this plugin")
        else:
            self.browser = QWebView()
        
        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(True)
        #sw.set_border_width(2)
        sw.setWidget(self.browser)

        cw = container.get_widget()
        cw.addWidget(sw, stretch=1)
        sw.show()

        self.entry = QtGui.QLineEdit()
        cw.addWidget(self.entry, stretch=0)
        self.entry.returnPressed.connect(self.browse_cb)

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        cw.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        if has_webkit:
            helpfile = os.path.abspath(os.path.join(packageHome,
                                                    "doc", "help.html"))
            helpurl = "file://%s" % (helpfile)
            self.browse(helpurl)

    def browse(self, url):
        self.logger.debug("Browsing '%s'" % (url))
        try:
            self.browser.load(QtCore.QUrl(url))
            self.entry.setText(url)
            self.browser.show()
        except Exception as e:
            self.fv.show_error("Couldn't load web page: %s" % (str(e)))
        
    def browse_cb(self):
        url = str(self.entry.text()).strip()
        self.browse(url)
        
    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'wbrowser'
    
#END
