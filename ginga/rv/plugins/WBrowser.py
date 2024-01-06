# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Web browser plugin for Ginga.

**Plugin Type: Global**

``WBrowser`` is a global plugin. Only one instance can be opened.

**Usage**

This global plugin is used to browse help pages for Ginga.

When a "Help" button is pressed from a plugin (e.g., ``Pick``),
Ginga will attempt to download an existing documentation build
from *ReadTheDocs* for the matching version. If successful,
plugin documentation from that download is displayed.
If not successful or deliberately disabled in "plugin_WBrowser.cfg",
Ginga will offer choices as to how to render the plugin's docstring:
either showing the RST text in a plain text widget or attempting
to view the documentation from the RTD web site using an external
browser.
"""

import os.path
import webbrowser

# GINGA
from ginga.GingaPlugin import GlobalPlugin
from ginga.doc import download_doc
from ginga.gw import Widgets

__all__ = ['WBrowser']

WAIT_HTML = """<html><title>Downloading documentation</title>
<body>
<p>Downloading and unpacking Ginga documentation from ReadTheDocs.
This may take several seconds (or longer, depending on your connection).</p>
<p>Please wait...</p>
</body>
</html>
"""

WAIT_PLAIN = """
Opening documentation from ReadTheDocs in external web browser using
Python `webbrowser` module ...

If this fails, please visit:
    %(url)s
"""


class WBrowser(GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(WBrowser, self).__init__(fv)

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_WBrowser')
        self.settings.add_defaults(offline_doc_only=False)
        self.settings.load(onError='silent')

        self.browser = None
        self._do_remember = False
        self._no_browser_choice = 0
        self._plugin = None
        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        self.browser = None
        self.w.tw = None

        if Widgets.has_webkit:
            try:
                self.browser = Widgets.WebView()
            except Exception as e:
                self.logger.error(f"can't create browser widget: {e}",
                                  exc_info=True)

        # Create troubleshooting dialog if downloading cannot be done
        self.w.dialog = Widgets.Dialog(title="Problem loading documentation",
                                       parent=container,
                                       modal=False,
                                       buttons=[("Cancel", 0),
                                                ("Show RST text", 1),
                                                ("Use external browser", 2),
                                                ])
        self.w.dialog.buttons[0].set_tooltip("Skip help")
        self.w.dialog.buttons[1].set_tooltip("Show local docstring for plugin help")
        self.w.dialog.buttons[2].set_tooltip("Show online web documentation in external browser")
        vbox2 = self.w.dialog.get_content_area()
        self.w.error_text = Widgets.TextArea(wrap=True, editable=False)
        vbox2.add_widget(self.w.error_text, stretch=1)
        cb = Widgets.CheckBox("Remember my choice for session")
        cb.set_state(False)
        vbox2.add_widget(cb, stretch=0)
        self.w.cb_remember = cb
        cb.add_callback('activated', self._remember_cb)
        self.w.dialog.add_callback('activated', self._handle_alternate_cb)

        if self.browser is None:
            self.w.error_text.set_text("The built-in browser could not "
                                       "be created.\nHere are your options:")
            msg_font = self.fv.get_font('fixed', 12)
            self.w.tw = Widgets.TextArea(wrap=False, editable=False)
            self.w.tw.set_font(msg_font)
            vbox.add_widget(self.w.tw, stretch=1)
            self.w.tw.set_text("Please install the pyqtwebengine (Qt) or \n"
                               "webkit2 (Gtk) package to fully enable \n"
                               "this plugin\n")

        else:
            sw = Widgets.ScrollArea()
            sw.set_widget(self.browser)

            vbox.add_widget(sw, stretch=1)

            self.w.entry = Widgets.TextEntrySet()
            vbox.add_widget(self.w.entry, stretch=0)
            self.w.entry.add_callback('activated', lambda w: self.browse_cb())

            tbar = Widgets.Toolbar(orientation='horizontal')
            for tt, cb, ico in (
                    ('Go back', lambda w: self.back_cb(), 'prev.svg'),
                    ('Go forward', lambda w: self.forward_cb(), 'next.svg'),
                    ('Reload page', lambda w: self.reload_cb(), 'rotate.svg'),
                    ('Stop loading', lambda w: self.stop_cb(), 'stop.svg'),
                    ('Go to top of documentation', lambda w: self.show_help(),
                     'file.svg')):
                btn = tbar.add_action(
                    None, iconpath=os.path.join(self.fv.iconpath, ico))
                btn.add_callback('activated', cb)
                btn.set_tooltip(tt)

            vbox.add_widget(tbar, stretch=0)

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
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def has_browser(self):
        return self.browser is not None

    def _download_error(self, errmsg):
        # called when failed to download in _download_doc()
        self.fv.assert_gui_thread()
        self.w.error_text.set_text(errmsg)
        self.w.dialog.show()

    def _download_doc(self, plugin=None, no_url_callback=None):
        self.fv.assert_nongui_thread()

        self.fv.gui_do(self._load_doc, WAIT_HTML, url_is_content=True)

        def _dl_indicator(count, blksize, totalsize):
            pct = (count * blksize) / totalsize
            msg = 'Downloading: {:.1%} complete'.format(pct)
            self.fv.gui_do(self.w.entry.set_text, msg)

        # This can block as long as it takes without blocking the UI.
        if self.settings.get('offline_doc_only', False):
            url = None  # DEBUG: Use this to force offline mode.
        else:
            try:
                url = download_doc.get_doc(logger=self.logger, plugin=plugin,
                                           reporthook=_dl_indicator)
                self.fv.gui_do(self._load_doc, url,
                               no_url_callback=no_url_callback)

            except Exception as e:
                # we can get HTTP 403 ("Forbidden") errors and so forth
                errmsg = f"Error downloading documentation: {e}"
                self.logger.error(errmsg, exc_info=True)
                self.fv.gui_do(self._download_error, errmsg)

    def _load_doc(self, url, no_url_callback=None, url_is_content=False):
        self.fv.assert_gui_thread()
        if url is None:
            self.w.entry.set_text('')
            if no_url_callback is None:
                self.fv.show_error("Couldn't load web page")
            else:
                no_url_callback()
        else:
            self.browse(url, url_is_content=url_is_content)

    def show_help(self, plugin=None, no_url_callback=None):
        """See `~ginga.GingaPlugin` for usage of optional keywords."""
        # record plugin choice
        self._plugin = plugin

        if not self.has_browser():
            if self._no_browser_choice == 0:
                self.w.dialog.show()
            else:
                self._handle_alternate_cb(self.w.dialog, self._no_browser_choice)
            return

        self.fv.nongui_do(self._download_doc, plugin=plugin,
                          no_url_callback=no_url_callback)

    def _display_externally(self, url):
        self.w.tw.append_text("\n---------\n")
        self.w.tw.append_text(WAIT_PLAIN % dict(url=url))
        webbrowser.open(url)

    def _handle_alternate_cb(self, dialog_w, val):
        dialog_w.hide()
        if self._do_remember:
            self._no_browser_choice = val
        plugin = self._plugin
        if val == 1:
            if plugin is not None:
                name, doc = plugin._help_docstring()
                self.fv.show_help_text(name, doc)
            self.close()
        elif val == 2:
            url = download_doc.get_online_docs_url(plugin=plugin)
            self._display_externally(url)
        self.close()

    def _remember_cb(self, cb_w, tf):
        self._do_remember = tf

    def browse(self, url, url_is_content=False):
        if not self.has_browser():
            self._display_externally(url, not url_is_content)
            return

        try:
            if url_is_content:  # This was load_html()
                self.browser.load_html_string(url)
                self.w.entry.set_text('')
            else:
                self.logger.debug("Browsing '{}'".format(url))
                self.browser.load_url(url)
                self.w.entry.set_text(url)
        except Exception as e:
            self.fv.show_error("Couldn't load web page: {}".format(str(e)))
        else:
            self.browser.show()

    def browse_cb(self):
        url = str(self.w.entry.get_text()).strip()
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

    def stop(self):
        self.browser = None
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'wbrowser'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_WBrowser', package='ginga')

# END
