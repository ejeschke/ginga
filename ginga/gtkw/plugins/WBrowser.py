#
# WBrowser.py -- Web Browser plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
from ginga import GingaPlugin

import gtk

has_webkit = False
try:
    import webkit
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
        if not has_webkit:
            self.browser = gtk.Label("Please install the python-webkit package to enable this plugin")
        else:
            self.browser = webkit.WebView()
        
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)
        sw.add(self.browser)

        container.pack_start(sw, fill=True, expand=True)

        self.entry = gtk.Entry()
        container.pack_start(self.entry, fill=True, expand=False)
        self.entry.connect('activate', self.browse_cb)
         
        if has_webkit:
            helpfile = os.path.abspath(os.path.join(moduleHome, "..",
                                                    "..", "doc", "manual",
                                                    "quickref.html"))
            helpurl = "file://%s" % (helpfile)
            self.entry.set_text(helpurl)
            self.browse(helpurl)

    def browse(self, url):
        self.logger.debug("Browsing '%s'" % (url))
        self.browser.open(url)
        
    def browse_cb(self, w):
        url = w.get_text().strip()
        self.browse(url)
        
    def __str__(self):
        return 'wbrowser'
    
#END
