# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.gw import Widgets

from .base import Stage


class ChannelMixer(Stage):

    _stagename = 'channel-mixer'

    def __init__(self):
        super(ChannelMixer, self).__init__()

        self.order = 'RGB'
        # "standard" RGB conversion
        self.std = np.array([0.2126, 0.7152, 0.0722])
        self.mix = np.copy(self.std)

    def build_gui(self, container):
        fr = Widgets.Frame("Channel Mixer")
        top = Widgets.VBox()

        grid = Widgets.GridBox(rows=2, columns=3)
        grid.set_row_spacing(0)
        grid.add_widget(Widgets.Label('Red:'), 0, 0)
        red = Widgets.SpinBox(dtype=float)
        red.set_value(self.mix[0])
        red.set_tooltip("Amount of red channel to mix in")
        grid.add_widget(red, 1, 0)
        self.w.red = red
        grid.add_widget(Widgets.Label('Green:'), 0, 1)
        grn = Widgets.SpinBox(dtype=float)
        grn.set_value(self.mix[1])
        grn.set_tooltip("Amount of green channel to mix in")
        grid.add_widget(grn, 1, 1)
        self.w.grn = grn
        grid.add_widget(Widgets.Label('Blue:'), 0, 2)
        blu = Widgets.SpinBox(dtype=float)
        blu.set_value(self.mix[2])
        blu.set_tooltip("Amount of blue channel to mix in")
        grid.add_widget(blu, 1, 2)
        self.w.blu = blu

        for i, name in enumerate(['red', 'grn', 'blu']):
            adj = self.w[name]
            lower, upper = 0.0, 100.0
            adj.set_limits(lower, upper, incr_value=1.0)
            adj.set_decimals(2)
            adj.set_value(self.mix[i] * 100)
            adj.add_callback('value-changed', self.set_mix_cb, name, i)

        top.add_widget(grid, stretch=0)

        tbar = Widgets.Toolbar(orientation='horizontal')
        lbl = Widgets.Label()
        self.w.total = lbl
        tbar.add_widget(lbl)
        act = tbar.add_action('Std')
        act.set_tooltip("Reset mix to standard grey")
        act.add_callback('activated', self.set_std_cb)

        top.add_widget(tbar, stretch=0)
        self._gui_update_total()

        fr.set_widget(top)
        container.set_widget(fr)

    def _gui_update_mix(self):
        for i, name in enumerate(['red', 'grn', 'blu']):
            adj = self.w[name]
            adj.set_value(self.mix[i] * 100)

    def _gui_update_total(self):
        lbl = self.w.total
        total = np.sum(self.mix)
        lbl.set_text("%6.2f%%" % (total * 100.0))

    def set_mix_cb(self, widget, val, name, i):
        self.mix[i] = val / 100.0
        if self.gui_up:
            self._gui_update_total()

        self.pipeline.run_from(self)

    def set_std_cb(self, widget):
        self.mix = np.copy(self.std)
        if self.gui_up:
            self._gui_update_mix()

        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        res_np = (data[:, :, 0] * self.mix[0] +
                  data[:, :, 1] * self.mix[1] +
                  data[:, :, 2] * self.mix[2])

        ht, wd = data.shape[:2]
        res_np = res_np.reshape((ht, wd))

        #res_np = res_np.clip(0, 255).astype(data.dtype)

        self.pipeline.send(res_np=res_np)
