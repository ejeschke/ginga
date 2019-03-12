# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
See the logging output of the reference viewer.

**Plugin Type: Global**

``Log`` is a global plugin.  Only one instance can be opened.

**Usage**

The ``Log`` plugin builds a UI that includes a large scrolling text widget
showing the active output of the logger.  The latest output shows up at
the bottom.  This can be useful for troubleshooting problems.

There are four controls:

* The combo box on the lower left allows you to choose the level of
  logging desired.  The four levels, in order of verbosity are: "debug",
  "info", "warn", and "error".
* The box with the number on the lower right allows you to set how many
  lines of input to keep in the display buffer (e.g., keep only the last
  1000 lines).
* The checkbox "Auto scroll", if checked, will cause the large text
  widget to scroll to the end as new log messages are added.  Uncheck
  this if you want to peruse the older messages and study them.
* The "Clear" button is used to clear the text widget, so that only new
  logging shows up.

"""
import logging
from collections import deque

from ginga import GingaPlugin
from ginga.gw import Widgets

__all__ = ['Log']


class Log(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Log, self).__init__(fv)

        self.histlimit = 1000
        self.histmax = 10000
        self.levels = (('Error', logging.ERROR),
                       ('Warn', logging.WARN),
                       ('Info', logging.INFO),
                       ('Debug', logging.DEBUG))
        self.autoscroll = True
        self.tw = None
        self._lines = deque([], self.histlimit)
        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()

        self.msg_font = self.fv.get_font('fixed', 12)
        tw = Widgets.TextArea(wrap=False, editable=False)
        tw.set_font(self.msg_font)
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
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)
        self.gui_up = True

    def set_history(self, histlimit):
        if histlimit > self.histmax:
            raise Exception(
                "Limit exceeds maximum value of %d" % (self.histmax))
        self.histlimit = histlimit
        self._lines = deque(self._lines, histlimit)
        self.logger.debug("Logging history limit set to %d" % (
            histlimit))
        if self.tw is not None:
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
        if self.gui_up:
            self.tw.append_text(text + '\n',
                                autoscroll=self.autoscroll)
        else:
            self._lines.append(text)

    def clear(self):
        if self.gui_up:
            self.tw.clear()
        self._lines.clear()
        return True

    def start(self):
        self.tw.set_text('\n'.join(self._lines))
        self._lines.clear()

    def stop(self):
        self.tw = None
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'log'

# END
