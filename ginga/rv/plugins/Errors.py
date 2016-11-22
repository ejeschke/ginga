#
# Errors.py -- Error reporting plugin for fits viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

from ginga import GingaPlugin
from ginga.gw import Widgets

class Errors(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Errors, self).__init__(fv)

        self.pending_errors = []
        self.gui_up = False

    def build_gui(self, container):
        self.msg_font = self.fv.get_font("fixedFont", 10)

        vbox = Widgets.VBox()

        mlst = Widgets.VBox()
        mlst.set_spacing(2)
        self.msg_list = mlst

        sw = Widgets.ScrollArea()
        sw.set_widget(self.msg_list)

        vbox.add_widget(sw, stretch=1)

        hbox = Widgets.HBox()
        btn = Widgets.Button("Remove All")
        btn.add_callback('activated', lambda w: self.remove_all())
        hbox.add_widget(btn, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        vbox.add_widget(hbox, stretch=0)
        container.add_widget(vbox, stretch=1)

        self.gui_up = True

        pending = self.pending_errors
        self.pending_errors = []

        for errmsg, ts in pending:
            self.add_error(errmsg, ts=ts)

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
        vbox.cfg_expand(horizontal=1)

        self.msg_list.add_widget(vbox, stretch=0)
        # TODO: force scroll to bottom

    def remove_error(self, child):
        self.msg_list.remove(child)

    def remove_all(self):
        for child in list(self.msg_list.get_children()):
            self.remove_error(child)

    def __str__(self):
        return 'errors'

#END
