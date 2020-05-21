# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage


class Rotate(Stage):

    _stagename = 'rotate'

    def __init__(self):
        super(Rotate, self).__init__()

        self.rot_deg = 0.0
        self.clip = True

    def build_gui(self, container):
        fr = Widgets.Frame("Rotate")

        captions = (('Rotate:', 'label', 'Rotate', 'entryset'),
                    ('Clip:', 'label', 'Clip', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.rotate.set_tooltip("Rotate the image around the pan position")
        b.rotate.set_text("0.0")
        b.rotate.add_callback('activated', self.rotate_cb)
        b.clip.set_state(self.clip)
        b.clip.set_tooltip("Clip rotated image")
        b.clip.add_callback('activated', self.clip_cb)

        fr.set_widget(w)

        container.set_widget(fr)

    def rotate_cb(self, widget):
        self.rot_deg = float(widget.get_text().strip())
        self.pipeline.run_from(self)

    def clip_cb(self, widget, tf):
        self.clip = tf
        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None or np.isclose(self.rot_deg, 0.0):
            self.pipeline.send(res_np=data)
            return

        if self.clip:
            res_np = trcalc.rotate_clip(data, self.rot_deg,
                                        logger=self.logger)
        else:
            res_np = trcalc.rotate(data, self.rot_deg, pad=0,
                                   logger=self.logger)

        self.pipeline.send(res_np=res_np)
