# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Errors`` plugin reports error messages on the viewer.

**Plugin Type: Global**

``Errors`` is a global plugin.  Only one instance can be opened.

**Usage**

When an error occurs in Ginga, its message may be reported here.

This plugin is not usually configured to be closeable, but the user can
make it so by setting the "closeable" setting to True in the configuration
file--then Close and Help buttons will be added to the bottom of the UI.

"""
import time
from collections import deque

from ginga import GingaPlugin
from ginga.gw import Widgets

__all__ = ['Errors']


class Errors(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Errors, self).__init__(fv)

        spec = self.fv.get_plugin_spec(str(self))

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Errors')
        self.settings.add_defaults(closeable=not spec.get('hidden', False),
                                   max_errors=100)
        self.settings.load(onError='silent')

        max_errors = self.settings.get('max_errors', 100)
        self.pending_errors = deque([], max_errors)
        self.gui_up = False

    def build_gui(self, container):
        self.msg_font = self.fv.get_font('fixed', 10)

        vbox = Widgets.VBox()

        mlst = Widgets.VBox()
        mlst.set_spacing(2)
        self.msg_list = mlst

        sw = Widgets.ScrollArea()
        sw.set_widget(self.msg_list)

        vbox.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        if self.settings.get('closeable', False):
            btn = Widgets.Button("Close")
            btn.add_callback('activated', lambda w: self.close())
            btns.add_widget(btn)
            btn = Widgets.Button("Help")
            btn.add_callback('activated', lambda w: self.help())
            btns.add_widget(btn, stretch=0)

        btn = Widgets.Button("Remove All")
        btn.add_callback('activated', lambda w: self.remove_all())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vbox.add_widget(btns, stretch=0)
        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def add_error(self, errmsg, ts=None):
        if ts is None:
            # Add the time the error occurred
            ts = time.strftime("%m/%d %H:%M:%S", time.localtime())

        if not self.gui_up:
            self.pending_errors.append((errmsg, ts))
            return

        vbox = Widgets.VBox()

        hbox = Widgets.HBox()
        # Add the time the error occurred
        ts = time.strftime("%m/%d %H:%M:%S", time.localtime())
        lbl = Widgets.Label(ts, halign='left')
        hbox.add_widget(lbl, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        tw = Widgets.TextArea(editable=False, wrap=False)
        tw.set_font(self.msg_font)

        tw.set_text(errmsg)
        vbox.add_widget(tw, stretch=1)

        hbox = Widgets.HBox()
        btn = Widgets.Button("Remove")
        btn.add_callback('activated', lambda w: self.remove_error(vbox))
        hbox.add_widget(btn)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)
        # special hack for Qt
        vbox.cfg_expand(horizontal='minimum')

        self.msg_list.add_widget(vbox, stretch=0)
        # TODO: force scroll to bottom

    def remove_error(self, child):
        self.msg_list.remove(child)

    def remove_all(self):
        self.pending_errors.clear()
        for child in list(self.msg_list.get_children()):
            self.remove_error(child)

    def start(self):
        pending = self.pending_errors
        self.pending_errors = []

        for errmsg, ts in pending:
            self.add_error(errmsg, ts=ts)

    def stop(self):
        self.pending_errors = []
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'errors'

# END
