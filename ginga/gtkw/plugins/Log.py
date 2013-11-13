#
# Log.py -- Logging plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import logging

from ginga import GingaPlugin
from ginga.gtkw import GtkHelp
import gtk

class Log(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Log, self).__init__(fv)

        self.histlimit = 1000
        self.histmax = 10000
        self.levels = (('Error', logging.ERROR),
                       ('Warn',  logging.WARN),
                       ('Info',  logging.INFO),
                       ('Debug', logging.DEBUG))

        
    def build_gui(self, container):
        self.msgFont = self.fv.getFont("fixedFont", 10)
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_NONE)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.modify_font(self.msgFont)
        self.tw = tw
        self.buf = self.tw.get_buffer()
         
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)
        sw.add(self.tw)

        container.pack_start(sw, fill=True, expand=True)

        hbox = gtk.HBox()

        lbl = gtk.Label('Level:')
        hbox.pack_start(lbl, fill=False, expand=False)
        combobox = GtkHelp.combo_box_new_text()
        for (name, level) in self.levels:
            combobox.append_text(name)
        combobox.set_active(1)
        combobox.sconnect('changed', self.set_loglevel_cb)
        hbox.pack_start(combobox, fill=False, expand=False,
                        padding=4)
        
        lbl = gtk.Label('History:')
        hbox.pack_start(lbl, fill=False, expand=False)
        spinbox = GtkHelp.SpinButton()
        adj = spinbox.get_adjustment()
        adj.configure(self.histlimit, 100, self.histmax, 10, 100, 0)
        spinbox.sconnect('value-changed', self.set_history_cb)
        hbox.pack_start(spinbox, fill=False, expand=False,
                        padding=4)
        
        btn = gtk.Button("Clear")
        btn.connect('clicked', lambda w: self.clear())
        hbox.pack_end(btn, fill=False, expand=False)
        container.pack_end(hbox, fill=False, expand=False)

    def set_history(self, histlimit):
        assert histlimit <= self.histmax, \
               Exception("Limit exceeds maximum value of %d" % (self.histmax))
        self.histlimit = histlimit
        self.logger.debug("Logging history limit set to %d" % (
            histlimit))
        self.history_housekeeping()
        
    def set_history_cb(self, rng):
        histlimit = rng.get_value()
        self.set_history(histlimit)
        
    def history_housekeeping(self):
        # remove some lines to keep us within our history limit
        numlines = self.buf.get_line_count()
        if numlines > self.histlimit:
            rmcount = int(numlines - self.histlimit)
            start = self.buf.get_iter_at_line(0)
            end   = self.buf.get_iter_at_line(rmcount)
            self.buf.delete(start, end)

    def set_loglevel_cb(self, w):
        index = w.get_active()
        name, level = self.levels[index]
        self.fv.set_loglevel(level)
        self.logger.info("GUI log level changed to '%s'" % (
            name))

    def log(self, text):
        end = self.buf.get_end_iter()
        self.buf.insert(end, text + '\n')

        self.history_housekeeping()
        
        # scroll window to end of buffer
        end = self.buf.get_end_iter()
        mark = self.buf.get_insert()
        #self.tw.scroll_to_iter(end, 0.5)
        # TODO: this is causing a segfault if the text widget is
        # not mapped yet!
        #self.buf.move_mark(mark, end)
        #res = self.tw.scroll_to_mark(mark, 0.2, True)

    def clear(self):
        start = self.buf.get_start_iter()
        end = self.buf.get_end_iter()
        self.buf.delete(start, end)
        return True
        
    def __str__(self):
        return 'log'
    
#END
