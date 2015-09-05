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
from ginga.gw import Widgets

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
        self.autoscroll = True
        self.tw = None

    def build_gui(self, container):
        vbox = Widgets.VBox()

        self.msgFont = self.fv.getFont("fixedFont", 12)
        tw = Widgets.TextArea(wrap=False, editable=False)
        tw.set_font(self.msgFont)
        tw.set_limit(self.histlimit)
        self.tw = tw

        sw = Widgets.ScrollArea()
        sw.set_widget(self.tw)

        vbox.add_widget(sw, stretch=1)

        captions = (('Level', 'combobox', 'History', 'spinbutton'),
                    ('Auto scroll', 'checkbutton', 'Clear', 'button')
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        combobox = b.level
        for (name, level) in self.levels:
            combobox.append_text(name)
        combobox.set_index(1)
        combobox.add_callback('activated', self.set_loglevel_cb)
        combobox.set_tooltip("Set the logging level")

        spinbox = b.history
        spinbox.set_limits(100, self.histmax, incr_value=10)
        spinbox.set_value(self.histlimit)
        spinbox.add_callback('value-changed', self.set_history_cb)
        spinbox.set_tooltip("Set the logging history line limit")

        btn = b.auto_scroll
        btn.set_state(self.autoscroll)
        btn.set_tooltip("Scroll the log window automatically")
        btn.add_callback('activated', self.set_autoscroll_cb)

        btn = b.clear
        btn.add_callback('activated', lambda w: self.clear())
        btn.set_tooltip("Clear the log history")
        vbox.add_widget(w, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

    def set_history(self, histlimit):
        assert histlimit <= self.histmax, \
               Exception("Limit exceeds maximum value of %d" % (self.histmax))
        self.histlimit = histlimit
        self.logger.debug("Logging history limit set to %d" % (
            histlimit))
        self.tw.set_limit(histlimit)

    def set_history_cb(self, w, val):
        self.set_history(val)

    def set_loglevel_cb(self, w, index):
        name, level = self.levels[index]
        self.fv.set_loglevel(level)
        self.logger.info("GUI log level changed to '%s'" % (
            name))

    def set_autoscroll_cb(self, w, val):
        self.autoscroll = val

    def log(self, text):
        if self.tw is not None:
            self.tw.append_text(text + '\n',
                                autoscroll=self.autoscroll)

    def clear(self):
        self.tw.clear()
        return True

    def close(self):
        self.fv.stop_global_plugin(str(self))
        self.tw = None
        return True

    def __str__(self):
        return 'log'

#END
