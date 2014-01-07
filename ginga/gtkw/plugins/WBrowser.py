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

import gtk

has_webkit = False
try:
    import webkit
    has_webkit = True
except ImportError:
    pass

from ginga import GingaPlugin
from ginga.Control import packageHome

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

        cw = container.get_widget()
        cw.pack_start(sw, fill=True, expand=True)

        self.entry = gtk.Entry()
        cw.pack_start(self.entry, fill=True, expand=False)
        self.entry.connect('activate', self.browse_cb)
         
        if has_webkit:
            helpfile = os.path.abspath(os.path.join(packageHome,
                                                    "doc", "help.html"))
            helpurl = "file:%s" % (helpfile)
            self.browse(helpurl)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)
        btns.set_child_size(15, -1)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        cw.pack_start(btns, padding=4, fill=True, expand=False)


    def browse(self, url):
        self.logger.debug("Browsing '%s'" % (url))
        try:
            self.browser.open(url)
            self.entry.set_text(url)
        except Exception as e:
            self.fv.show_error("Couldn't load web page: %s" % (str(e)))
        
    def browse_cb(self, w):
        url = w.get_text().strip()
        self.browse(url)
        
    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'wbrowser'
    
#END
