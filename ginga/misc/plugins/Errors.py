#
# Errors.py -- Error reporting plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
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

    def build_gui(self, container):
        self.msgFont = self.fv.getFont("fixedFont", 10)

        vbox = Widgets.VBox()

        mlst = Widgets.VBox()
        mlst.set_spacing(2)
        self.msgList = mlst

        sw = Widgets.ScrollArea()
        sw.set_widget(self.msgList)

        vbox.add_widget(sw, stretch=1)

        hbox = Widgets.HBox()
        btn = Widgets.Button("Remove All")
        btn.add_callback('activated', lambda w: self.remove_all())
        hbox.add_widget(btn, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        vbox.add_widget(hbox, stretch=0)
        container.add_widget(vbox, stretch=1)

    def add_error(self, errmsg):
        vbox = Widgets.VBox()

        hbox = Widgets.HBox()
        # Add the time the error occurred
        ts = time.strftime("%m/%d %H:%M:%S", time.localtime())
        lbl = Widgets.Label(ts)
        hbox.add_widget(lbl, stretch=1)
        vbox.add_widget(hbox, stretch=0)

        tw = Widgets.TextArea(editable=False, wrap=False)
        tw.set_font(self.msgFont)

        tw.set_text(errmsg)
        vbox.add_widget(tw, stretch=0)

        hbox = Widgets.HBox()
        btn = Widgets.Button("Remove")
        btn.add_callback('activated', lambda w: self.remove_error(vbox))
        hbox.add_widget(btn)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        self.msgList.add_widget(vbox, stretch=0)
        # TODO: force scroll to bottom

    def remove_error(self, child):
        self.msgList.remove(child)

    def remove_all(self):
        for child in list(self.msgList.get_children()):
            self.remove_error(child)

    def __str__(self):
        return 'errors'

#END
