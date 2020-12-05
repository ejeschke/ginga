# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import trcalc
from ginga.gw import Widgets
from ginga.util import action

from .base import Stage


class FlipSwap(Stage):

    _stagename = 'flip-swap'

    def __init__(self):
        super(FlipSwap, self).__init__()

        self._flip_x = False
        self._flip_y = False
        self._swap_xy = False
        self.viewer = None

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')

        # TRANSFORM OPTIONS
        fr = Widgets.Frame("Flip / Swap")

        captions = (('Transform:', 'label', 'hbox1', 'hbox'),
                    ('_sp1', 'spacer', 'hbox2', 'hbox'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')

        for wname, name, tf in (('flip_x', "Flip X", self._flip_x),
                                ('flip_y', "Flip Y", self._flip_y),
                                ('swap_xy', "Swap XY", self._swap_xy)):
            btn = Widgets.CheckBox(name)
            b[wname] = btn
            btn.set_state(tf)
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

    @property
    def flip_x(self):
        return self._flip_x

    @flip_x.setter
    def flip_x(self, tf):
        self._flip_x = tf
        if self.gui_up:
            self.w.flip_x.set_state(tf)

    @property
    def flip_y(self):
        return self._flip_y

    @flip_y.setter
    def flip_y(self, tf):
        self._flip_y = tf
        if self.gui_up:
            self.w.flip_y.set_state(tf)

    @property
    def swap_xy(self):
        return self._swap_xy

    @swap_xy.setter
    def swap_xy(self, tf):
        self._swap_xy = tf
        if self.gui_up:
            self.w.swap_xy.set_state(tf)

    def _get_state(self):
        return dict(flip_x=self._flip_x, flip_y=self._flip_y,
                    swap_xy=self._swap_xy)

    def set_transforms_cb(self, *args):
        old = self._get_state()
        self._flip_x = self.w.flip_x.get_state()
        self._flip_y = self.w.flip_y.get_state()
        self._swap_xy = self.w.swap_xy.get_state()
        new = self._get_state()
        self.pipeline.push(action.AttrAction(self, old, new,
                                             descr="flip / swap"))
        self.pipeline.run_from(self)

    def copy_from_viewer_cb(self, widget):
        old = self._get_state()
        self.flip_x, self.flip_y, self.swap_xy = self.viewer.get_transforms()
        new = self._get_state()
        self.pipeline.push(action.AttrAction(self, old, new,
                                             descr="flip / swap"))
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

    def export_as_dict(self):
        d = super(FlipSwap, self).export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super(FlipSwap, self).import_from_dict(d)
        self.flip_x = d['flip_x']
        self.flip_y = d['flip_y']
        self.swap_xy = d['swap_xy']
