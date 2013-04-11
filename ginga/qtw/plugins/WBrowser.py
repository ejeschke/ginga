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

has_webkit = False
try:
    from ginga.qtw.QtHelp import QtWebKit as webkit
    has_webkit = True
except ImportError:
    pass

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
        
class WBrowser(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(WBrowser, self).__init__(fv)

        self.browser = None

    def build_gui(self, container):
        rvbox = container

        if not has_webkit:
            self.browser = QtGui.QLabel("Please install the python-webkit package to enable this plugin")
        else:
            self.browser = webkit.QWebView()
        
        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(True)
        #sw.set_border_width(2)
        sw.setWidget(self.browser)

        rvbox.addWidget(sw, stretch=1)
        sw.show()

        self.entry = QtGui.QLineEdit()
        rvbox.addWidget(self.entry, stretch=0)
        self.entry.returnPressed.connect(self.browse_cb)

        if has_webkit:
            helpfile = os.path.abspath(os.path.join(moduleHome, "..",
                                                    "..", "doc", "manual",
                                                    "quickref.html"))
            helpurl = "file://%s" % (helpfile)
            self.entry.setText(helpurl)
            self.browse(helpurl)

    def browse(self, url):
        self.logger.debug("Browsing '%s'" % (url))
        self.browser.load(QtCore.QUrl(url))
        self.browser.show()
        
    def browse_cb(self):
        url = str(self.entry.text()).strip()
        self.browse(url)
        
    def __str__(self):
        return 'wbrowser'
    
#END
