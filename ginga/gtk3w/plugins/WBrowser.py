#
# WBrowser.py -- Web Browser plugin for Ginga viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os

from gi.repository import Gtk

has_webkit = False
try:
    from gi.repository import WebKit
    has_webkit = True
except ImportError:
    pass

from ginga import GingaPlugin
from ginga.rv.Control import package_home

class WBrowser(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(WBrowser, self).__init__(fv)

        self.browser = None

    def build_gui(self, container):
        if not has_webkit:
            self.browser = Gtk.Label("Please install the python-webkit package to enable this plugin")
        else:
            self.browser = WebKit.WebView()

        sw = Gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC,
                      Gtk.PolicyType.AUTOMATIC)
        sw.add(self.browser)

        cw = container.get_widget()
        cw.pack_start(sw, True, True, 0)

        self.entry = Gtk.Entry()
        cw.pack_start(self.entry, False, True, 0)
        self.entry.connect('activate', self.browse_cb)

        if has_webkit:
            helpfile = os.path.abspath(os.path.join(package_home,
                                                    "doc", "help.html"))
            helpurl = "file:%s" % (helpfile)
            self.browse(helpurl)

        btns = Gtk.HButtonBox()
        btns.set_layout(Gtk.ButtonBoxStyle.START)
        btns.set_spacing(3)
        #btns.set_child_size(15, -1)

        btn = Gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        cw.pack_start(btns, False, True, 4)
        cw.show_all()

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
