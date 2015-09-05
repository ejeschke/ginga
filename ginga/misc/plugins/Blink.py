#
# Blink.py -- Blink plugin for Ginga reference viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.gw import Widgets

class Blink(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Blink, self).__init__(fv, fitsimage)

        self.interval = 1.0
        self.blink_timer = fv.get_timer()
        self.blink_timer.set_callback('expired', self._blink_timer_cb)

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Blink")

        captions = (("Interval:", 'label', 'Interval', 'entry',
                     "Start Blink", 'button', "Stop Blink", 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        b.interval.set_text(str(self.interval))
        b.interval.add_callback('activated', lambda w: self._set_interval_cb())
        b.interval.set_tooltip("Interval in seconds between changing images")

        b.start_blink.add_callback('activated',
                                   lambda w: self._start_blink_cb())
        b.stop_blink.add_callback('activated',
                                  lambda w: self._stop_blink_cb())

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def instructions(self):
        self.tw.set_text("""Blink the images in this channel.

Only images loaded in memory will be cycled.""")

    def start(self):
        self.instructions()
        self.resume()

    def pause(self):
        self.stop_blinking()

    def resume(self):
        self.start_blinking()

    def stop(self):
        self.stop_blinking()

    def redo(self):
        pass

    def _blink_timer_cb(self, timer):
        # set timer
        self.fv.gui_do(self.fv.next_img, loop=True)
        timer.set(self.interval)

    def start_blinking(self):
        self.blink_timer.set(self.interval)

    def stop_blinking(self):
        self.blink_timer.clear()

    def _start_blink_cb(self):
        self._set_interval_cb()
        self.start_blinking()

    def _stop_blink_cb(self):
        self.stop_blinking()

    def _set_interval_cb(self):
        interval = float(self.w.interval.get_text())
        self.interval = max(min(interval, 30.0), 0.25)
        self.stop_blinking()
        self.start_blinking()

    def __str__(self):
        return 'blink'

#END
