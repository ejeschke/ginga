#
# Blink.py -- Blink plugin for Ginga reference viewer
#
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

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Blink')
        self.settings.addDefaults(blink_channels=False)
        self.settings.load(onError='silent')

        self.blink_channels = self.settings.get('blink_channels', False)

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
        vbox2 = Widgets.VBox()

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
        vbox2.add_widget(w, stretch=0)

        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Blink channels")
        btn1.add_callback('activated',
                          lambda w, tf: self._set_blink_mode_cb(tf == True))
        btn1.set_tooltip("Choose this to blink across channels")
        btn1.set_state(self.blink_channels)
        self.w.blink_channels = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Blink images in channel", group=btn1)
        btn2.set_state(not self.blink_channels)
        btn2.add_callback('activated',
                          lambda w, tf: self._set_blink_mode_cb(tf == False))
        btn2.set_tooltip("Choose this to blink images within a channel")
        self.w.blink_within = btn2
        hbox.add_widget(btn2)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox2.add_widget(hbox, stretch=0)

        fr.set_widget(vbox2)
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
        self.fv.stop_local_plugin(self.chname, str(self))
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
        if self.blink_channels:
            self.fv.gui_do(self.fv.next_channel)
        else:
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

    def _set_blink_mode_cb(self, tf):
        self.blink_channels = tf

    def __str__(self):
        return 'blink'

#END
