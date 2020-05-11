# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage


class Scale(Stage):

    _stagename = 'scale'

    def __init__(self):
        super(Scale, self).__init__()

        self.scale = 1.0
        self.interp = 'lanczos'

    def build_gui(self, container):
        captions = (('Scale:', 'label', 'Scale', 'entryset'),
                    ('Interpolation:', 'label', 'Interpolation', 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)
        b.scale.set_tooltip("Set the scale")
        b.scale.set_text(str(1.0))
        b.scale.add_callback('activated', self.set_scale_cb)

        index = 0
        for name in trcalc.interpolation_methods:
            b.interpolation.append_text(name)
            index += 1
        try:
            index = trcalc.interpolation_methods.index(self.interp)
        except ValueError:
            # previous choice might not be available if preferences
            # were saved when opencv was being used--if so, default
            # to "basic"
            index = trcalc.interpolation_methods.index('basic')
        b.interpolation.set_index(index)
        b.interpolation.set_tooltip("Choose interpolation method")
        b.interpolation.add_callback('activated', self.set_interp_cb)

        container.set_widget(w)

    def set_scale_cb(self, widget):
        self.scale = float(widget.get_text())
        self.pipeline.run_from(self)

    def set_interp_cb(self, w, idx):
        self.interp = trcalc.interpolation_methods[idx]
        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None or np.isclose(self.scale, 1.0):
            self.pipeline.send(res_np=data)
            return

        ht, wd = data.shape[:2]
        res_np, scales = trcalc.get_scaled_cutout_basic(data, 0, 0,
                                                        wd - 1, ht - 1,
                                                        self.scale, self.scale,
                                                        interpolation=self.interp,
                                                        logger=self.pipeline.logger)
        self.pipeline.send(res_np=res_np)

    def __str__(self):
        return self._stagename
