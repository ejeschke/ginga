#
# Errors.py -- Error reporting plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

from ginga import GingaPlugin

import gtk

class Errors(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Errors, self).__init__(fv)


    def build_gui(self, container):
        self.msgFont = self.fv.getFont("fixedFont", 12)

        self.msgList = gtk.VBox(spacing=2)
        
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(self.msgList)

        container.pack_start(sw, fill=True, expand=True)

        hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_END)
        btn = gtk.Button("Remove All")
        btn.connect('clicked', lambda w: self.remove_all())
        hbox.add(btn)
        container.pack_end(hbox, fill=False, expand=False)


    def add_error(self, errmsg):
        vbox = gtk.VBox()
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_NONE)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.modify_font(self.msgFont)

        buf = tw.get_buffer()
        buf.set_text(errmsg)
        vbox.pack_start(tw, fill=True, expand=False)

        hbox = gtk.HBox(spacing=4)
        btn = gtk.Button("Remove")
        btn.connect('clicked', lambda w: self.remove_error(vbox))
        hbox.pack_start(btn, fill=False, expand=False)
        # Add the time the error occurred
        ts = time.strftime("%m/%d %H:%M:%S", time.localtime())
        lbl = gtk.Label(ts)
        lbl.set_alignment(0.0, 0.5)
        hbox.pack_start(lbl, fill=True, expand=True)
        vbox.pack_start(hbox, fill=True, expand=False)
        
        self.msgList.pack_start(vbox, fill=False, expand=False)
        vbox.show_all()
        # TODO: force scroll to bottom 

    def remove_error(self, vbox):
        self.msgList.remove(vbox)
        
    def remove_all(self):
        for child in self.msgList.children():
            self.msgList.remove(child)
        
    def __str__(self):
        return 'errors'
    
#END
