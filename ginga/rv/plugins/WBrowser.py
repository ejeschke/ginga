#
# WBrowser.py -- Web Browser plugin for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Browse help for Ginga."""
from __future__ import absolute_import, division, print_function

import os

# GINGA
from ginga.GingaPlugin import GlobalPlugin
from ginga.gw import Widgets

__all__ = []

WAIT_HTML = """<html><title>Downloading documentation</title>
<body>
<p>Downloading and unpacking Ginga documentation from ReadTheDocs.
This may take several seconds (or longer, depending on your connection).</p>
<p>Please wait...</p>
</body>
</html>
"""


class WBrowser(GlobalPlugin):
    """
    WBrowser
    ========
    Web Browser plugin for Ginga.

    Plugin Type: Global
    -------------------
    WBrowser is a global plugin. Only one instance can be opened.

    This global plugin is used to browse help pages for Ginga.
    When available, a local help page is displayed.

    """
    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(WBrowser, self).__init__(fv)

    def build_gui(self, container):
        if not Widgets.has_webkit:
            self.browser = Widgets.Label(
                "Please install the python-webkit package to enable "
                "this plugin")
        else:
            self.browser = Widgets.WebView()

        sw = Widgets.ScrollArea()
        sw.set_widget(self.browser)

        container.add_widget(sw, stretch=1)
        sw.show()

        self.entry = Widgets.TextEntrySet()
        container.add_widget(self.entry, stretch=0)
        self.entry.add_callback('activated', lambda w: self.browse_cb())

        tbar = Widgets.Toolbar(orientation='horizontal')
        for tt, cb, ico in (
                ('Go back', lambda w: self.back_cb(), 'prev_48.png'),
                ('Go forward', lambda w: self.forward_cb(), 'next_48.png'),
                ('Reload page', lambda w: self.reload_cb(), 'rotate_48.png'),
                ('Stop loading', lambda w: self.stop_cb(), 'stop_48.png'),
                ('Go to top of documentation', lambda w: self.show_help(),
                 'fits.png')):
            btn = tbar.add_action(
                None, iconpath=os.path.join(self.fv.iconpath, ico))
            btn.add_callback('activated', cb)
            btn.set_tooltip(tt)
        container.add_widget(tbar, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)
        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button('Help')
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        container.add_widget(btns, stretch=0)

        self.gui_up = True

    def _download_doc(self, plugin=None, no_url_callback=None):
        from ginga.doc.download_doc import get_doc
        self.fv.assert_nongui_thread()

        self.fv.gui_do(self._load_doc, WAIT_HTML, url_is_content=True)

        def _dl_indicator(count, blksize, totalsize):
            pct = (count * blksize) / totalsize
            msg = 'Downloading: {:.1%} complete'.format(pct)
            self.fv.gui_do(self.entry.set_text, msg)

        # This can block as long as it takes without blocking the UI.
        url = get_doc(logger=self.logger, plugin=plugin,
                      reporthook=_dl_indicator)

        self.fv.gui_do(self._load_doc, url, no_url_callback=no_url_callback)

    def _load_doc(self, url, no_url_callback=None, url_is_content=False):
        self.fv.assert_gui_thread()
        if url is None:
            self.entry.set_text('')
            if no_url_callback is None:
                self.fv.show_error("Couldn't load web page")
            else:
                no_url_callback()
        else:
            self.browse(url, url_is_content=url_is_content)

    def show_help(self, plugin=None, no_url_callback=None):
        """See `~ginga.GingaPlugin` for usage of optional keywords."""
        if not Widgets.has_webkit:
            return

        self.fv.nongui_do(self._download_doc, plugin=plugin,
                          no_url_callback=no_url_callback)

    def browse(self, url, url_is_content=False):
        if not Widgets.has_webkit:
            return

        try:
            if url_is_content:  # This was load_html()
                self.browser.load_html_string(url)
                self.entry.set_text('')
            else:
                self.logger.debug("Browsing '{}'".format(url))
                self.browser.load_url(url)
                self.entry.set_text(url)
        except Exception as e:
            self.fv.show_error("Couldn't load web page: {}".format(str(e)))
        else:
            self.browser.show()

    def browse_cb(self):
        url = str(self.entry.get_text()).strip()
        if len(url) > 0:
            self.browse(url)

    def back_cb(self):
        if not Widgets.has_webkit:
            return
        self.browser.go_back()

    def forward_cb(self):
        if not Widgets.has_webkit:
            return
        self.browser.go_forward()

    def reload_cb(self):
        if not Widgets.has_webkit:
            return
        self.browser.reload_page()

    def stop_cb(self):
        if not Widgets.has_webkit:
            return
        self.browser.stop_loading()

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'wbrowser'

# END
