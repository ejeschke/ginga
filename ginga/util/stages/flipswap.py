# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage


class FlipSwap(Stage):

    _stagename = 'flip-swap'

    def __init__(self):
        super(FlipSwap, self).__init__()

        self.flip_x = False
        self.flip_y = False
        self.swap_xy = False
        self.viewer = None

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')

        # TRANSFORM OPTIONS
        fr = Widgets.Frame("Flip / Swap")

        captions = (('Transform:', 'label', 'hbox1', 'hbox'),
                    ('_sp1', 'spacer', 'hbox2', 'hbox'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')

        for wname, name in (('flip_x', "Flip X"), ('flip_y', "Flip Y"),
                            ('swap_xy', "Swap XY")):
            btn = Widgets.CheckBox(name)
            b[wname] = btn
            btn.set_state(False)
            btn.add_callback('activated', self.set_transforms_cb)
            b.hbox1.add_widget(btn, stretch=0)

        b.flip_x.set_tooltip("Flip the image around the X axis")
        b.flip_y.set_tooltip("Flip the image around the Y axis")
        b.swap_xy.set_tooltip("Swap the X and Y axes in the image")

        b.copy_from_viewer = Widgets.Button("Copy from viewer")
        b.copy_from_viewer.set_tooltip("Copy flip/swap setting from viewer")
        b.copy_from_viewer.add_callback('activated', self.copy_from_viewer_cb)
        b.hbox2.add_widget(b.copy_from_viewer, stretch=0)
        b.hbox2.add_widget(Widgets.Label(''), stretch=1)

        self.w.update(b)
        fr.set_widget(w)

        container.set_widget(fr)

    def set_transforms_cb(self, *args):
        self.flip_x = self.w.flip_x.get_state()
        self.flip_y = self.w.flip_y.get_state()
        self.swap_xy = self.w.swap_xy.get_state()

        self.pipeline.run_from(self)

    def copy_from_viewer_cb(self, widget):
        self.flip_x, self.flip_y, self.swap_xy = self.viewer.get_transforms()
        self.w.flip_x.set_state(self.flip_x)
        self.w.flip_y.set_state(self.flip_y)
        self.w.swap_xy.set_state(self.swap_xy)

        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        res_np = trcalc.transform(data, flip_x=self.flip_x, flip_y=self.flip_y,
                                  swap_xy=self.swap_xy)

        self.pipeline.send(res_np=res_np)
