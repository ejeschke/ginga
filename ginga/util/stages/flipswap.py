# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch
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

    def build_gui(self, container):
        # TRANSFORM OPTIONS
        fr = Widgets.Frame("Transform")

        captions = (('Flip X', 'checkbutton', 'Flip Y', 'checkbutton',
                    'Swap XY', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        for name in ('flip_x', 'flip_y', 'swap_xy'):
            btn = b[name]
            btn.set_state(False)
            btn.add_callback('activated', self.set_transforms_cb)
        b.flip_x.set_tooltip("Flip the image around the X axis")
        b.flip_y.set_tooltip("Flip the image around the Y axis")
        b.swap_xy.set_tooltip("Swap the X and Y axes in the image")
        fr.set_widget(w)

        container.set_widget(fr)

    def set_transforms_cb(self, *args):
        self.flip_x = self.w.flip_x.get_state()
        self.flip_y = self.w.flip_y.get_state()
        self.swap_xy = self.w.swap_xy.get_state()
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
