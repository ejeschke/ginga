#
# WBrowser.py -- Web Browser plugin for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Browse help for Ginga."""
from __future__ import absolute_import, division, print_function

# GINGA
from ginga.GingaPlugin import GlobalPlugin
from ginga.gw import Widgets

__all__ = []


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

        self.entry = Widgets.TextEntry()
        container.add_widget(self.entry, stretch=0)
        self.entry.add_callback('activated', lambda w: self.browse_cb())

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        container.add_widget(btns, stretch=0)

        self.show_help()
        self.gui_up = True

    def show_help(self, plugin=None, no_url_callback=None):
        """See `~ginga.GingaPlugin` for usage of optional keywords."""
        if not Widgets.has_webkit:
            return

        from ginga.doc.download_doc import get_doc
        self.fv.assert_gui_thread()

        def _dl_indicator(count, blksize, totalsize):
            pct = (count * blksize) / totalsize
            msg = 'Downloading: {:.2%} complete'.format(pct)
            self.fv.gui_do(self.entry.set_text, msg)

        helpurl = get_doc(logger=self.logger, plugin=plugin,
                          reporthook=_dl_indicator)
        if helpurl is None:
            self.entry.set_text('')
            if no_url_callback is None:
                self.fv.show_error("Couldn't load web page")
            else:
                no_url_callback()
        else:
            self.browse(helpurl)

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

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'wbrowser'

# END
