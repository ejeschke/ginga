# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage


class Scale(Stage):
    """
    The Scale stage will scale a 2D image.

    If 'Long Side' (`longside`) is set to some pixel size, then the image
    is scaled so that the long side will be that many pixels; the other
    side will be scaled to keep the aspect ratio.

    If 'Long Side' is not set, or 'Scale' (`scale`) has been set to some
    float value, then the image is scaled according to that scale.

    'Interpolation' (`interp`) informs what kind of interpolation will be
    done to the image during the scaling.
    """

    _stagename = 'scale'

    def __init__(self):
        super(Scale, self).__init__()

        self.longside = None
        self.scale = 1.0
        self.interp = 'lanczos'
        self.viewer = None

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')

        fr = Widgets.Frame("Scale")

        captions = ((),
                    ('Long side:', 'label', 'longside', 'entryset'),
                    ('Interpolation:', 'label', 'Interpolation', 'combobox'),
                    ('Scale:', 'label', 'scale', 'entryset'),
                    ('_sp1', 'spacer', 'hbox1', 'hbox'),
                    ('Output Size:', 'label', 'size', 'llabel'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')

        b.longside.set_tooltip("Set the length of the long side in pixels")
        b.longside.set_text("")
        b.longside.add_callback('activated', self.set_longside_cb)

        b.scale.set_tooltip("Set the scale")
        b.scale.set_text(str(1.0))
        b.scale.add_callback('activated', self.set_scale_cb)

        b.copy_from_viewer = Widgets.Button("Copy from viewer")
        b.copy_from_viewer.set_tooltip("Copy scale setting from viewer")
        b.copy_from_viewer.add_callback('activated', self.copy_from_viewer_cb)
        b.hbox1.add_widget(b.copy_from_viewer, stretch=0)
        b.hbox1.add_widget(Widgets.Label(''), stretch=1)

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

        b.size.set_text('unknown')

        self.w.update(b)
        fr.set_widget(w)

        container.set_widget(fr)

    def set_longside_cb(self, widget):
        length = widget.get_text().strip()
        if len(length) == 0:
            self.longside = None
        else:
            self.longside = int(length)

        self.pipeline.run_from(self)

    def set_scale_cb(self, widget):
        self.scale = float(widget.get_text())
        self.w.longside.set_text('')
        self.longside = None

        self.pipeline.run_from(self)

    def set_interp_cb(self, w, idx):
        self.interp = trcalc.interpolation_methods[idx]

        self.pipeline.run_from(self)

    def copy_from_viewer_cb(self, widget):
        self.scale = self.viewer.get_scale()
        self.w.scale.set_text(str(self.scale))

        self.pipeline.run_from(self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None or (self.longside is None and
                                            np.isclose(self.scale, 1.0)):
            if self.gui_up:
                self.w.scale.set_text(str(1.0))
                _ht, _wd = data.shape[:2]
                self.w.size.set_text("{}x{}".format(_wd, _ht))

            self.pipeline.send(res_np=data)
            return

        ht, wd = data.shape[:2]

        if self.longside is not None:
            aspect = trcalc.get_aspect(data.shape)
            if aspect > 0:
                new_wd, new_ht = (self.longside,
                                  int(np.floor(self.longside / aspect)))
            else:
                new_wd, new_ht = (int(np.floor(self.longside * aspect)),
                                  self.longside)

            res_np, scales = trcalc.get_scaled_cutout_wdht(data, 0, 0,
                                                           wd - 1, ht - 1,
                                                           new_wd, new_ht,
                                                           interpolation=self.interp,
                                                           logger=self.logger)
            if self.gui_up:
                self.w.scale.set_text("%10.4f" % (scales[0]))

        else:
            res_np, scales = trcalc.get_scaled_cutout_basic(data, 0, 0,
                                                            wd - 1, ht - 1,
                                                            self.scale, self.scale,
                                                            interpolation=self.interp,
                                                            logger=self.logger)

        if self.gui_up:
            _ht, _wd = res_np.shape[:2]
            self.w.size.set_text("{}x{}".format(_wd, _ht))

        self.pipeline.send(res_np=res_np)
