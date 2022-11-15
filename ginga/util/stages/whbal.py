# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.canvas.CanvasObject import get_canvas_types
from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage, StageAction


class WhiteBalance(Stage):
    """
    White balance a 2D image.
    """

    _stagename = 'white-balance'

    def __init__(self):
        super().__init__()

        self.dc = get_canvas_types()
        self.crosshair_color = 'cyan'
        self._rval = 255
        self._gval = 255
        self._bval = 255
        self._lum = 255
        self.picker_obj = None
        self.viewer = None

        canvas = self.dc.DrawingCanvas()
        canvas.enable_edit(True)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_draw_mode('edit')
        self.canvas = canvas

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')

        fr = Widgets.Frame("White Balance")

        vbox = Widgets.VBox()
        captions = (('R:', 'label', 'rval', 'entry',
                     'G:', 'label', 'gval', 'entry',
                     'B:', 'label', 'bval', 'entry'),
                    ('Luminosity:', 'label', 'lum', 'entry')
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        # b.rval.set_limits(0, 255, 1)
        # b.gval.set_limits(0, 255, 1)
        # b.bval.set_limits(0, 255, 1)
        b.rval.set_text(str(self._rval))
        b.gval.set_text(str(self._gval))
        b.bval.set_text(str(self._bval))
        self._calc_lum()
        b.lum.set_text(str(self._lum))
        b.rval.add_callback('activated', self.chval_cb)
        b.gval.add_callback('activated', self.chval_cb)
        b.bval.add_callback('activated', self.chval_cb)
        b.lum.add_callback('activated', self.chlum_cb)

        vbox.add_widget(w, stretch=0)
        hbox = Widgets.HBox()
        hbox.set_spacing(2)
        self.w.white = Widgets.RadioButton("White")
        #self.w.gray = Widgets.RadioButton("Gray", group=self.w.white)
        self.w.white.set_state(True)
        self.w.white.set_enabled(False)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        hbox.add_widget(self.w.white, stretch=0)
        #hbox.add_widget(self.w.gray, stretch=0)
        vbox.add_widget(hbox, stretch=0)

        fr.set_widget(vbox)
        container.set_widget(fr)

        self.viewer = self.pipeline.get('viewer')
        self.canvas.set_surface(self.viewer)
        self.canvas.register_for_cursor_drawing(self.viewer)

        x, y = 0, 0
        self.picker_obj = self.dc.Crosshair(x, y, color=self.crosshair_color)

    @property
    def rval(self):
        return self._rval

    @rval.setter
    def rval(self, val):
        self._rval = val
        if self.gui_up:
            self.w.rval.set_text(str(self._rval))

    @property
    def gval(self):
        return self._gval

    @gval.setter
    def gval(self, val):
        self._gval = val
        if self.gui_up:
            self.w.gval.set_text(str(self._gval))

    @property
    def bval(self):
        return self._bval

    @bval.setter
    def bval(self, val):
        self._bval = val
        if self.gui_up:
            self.w.bval.set_text(str(self._bval))

    @property
    def lum(self):
        return self._lum

    @lum.setter
    def lum(self, val):
        self._lum = val
        if self.gui_up:
            self.w.lum.set_text("%.4f" % self._lum)

    def _calc_lum(self):
        #lum = (whiteR + whiteG + whiteB) / 3
        lum = (self._rval * 0.2126 + self._gval * 0.7152 + self._bval * 0.0722)
        self.lum = lum

    def edit_cb(self, canvas, picker_obj):
        old = self._get_state()

        x, y = picker_obj.points[0]
        x, y = int(x), int(y)
        #print(f"x, y is {x},{y}")

        idx = self.pipeline.index(self)
        data = self.pipeline.get_data(self.pipeline[idx - 1])
        self.verify_2d(data)
        tup = data[..., 0:3][y, x]
        self.rval, self.gval, self.bval = [int(n) for n in tup]
        self._calc_lum()
        new = self._get_state()
        self.pipeline.push(StageAction(self, old, new,
                                       descr="whbal / change val"))
        self.pipeline.run_from(self)

    def chval_cb(self, w):
        old = self._get_state()
        self.rval, self.gval, self.bval = [int(n)
                                           for n in [self.w.rval.get_text().strip(),
                                                     self.w.gval.get_text().strip(),
                                                     self.w.bval.get_text().strip()]]
        self._calc_lum()
        new = self._get_state()
        self.pipeline.push(StageAction(self, old, new,
                                       descr="whbal / change rgb"))
        self.pipeline.run_from(self)

    def chlum_cb(self, w):
        old = self._get_state()
        self.lum = float(self.w.lum.get_text().strip())
        new = self._get_state()
        self.pipeline.push(StageAction(self, old, new,
                                       descr="whbal / change lum"))
        self.pipeline.run_from(self)

    def _get_state(self):
        return dict(rval=self._rval, gval=self._gval, bval=self._bval,
                    lum=self._lum)

    def resume(self):
        # insert canvas, if not already
        p_canvas = self.viewer.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas)

        if not self.canvas.has_object(self.picker_obj):
            self.canvas.add(self.picker_obj)

        self.canvas.ui_set_active(True, viewer=self.viewer)

    def pause(self):
        self.canvas.ui_set_active(False)

        # remove the canvas from the image
        p_canvas = self.viewer.get_canvas()
        try:
            p_canvas.delete_object(self.canvas)
        except Exception:
            pass

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        #imgR = imgR * lum / whiteR
        #imgG = imgG * lum / whiteG
        #imgB = imgB * lum / whiteB
        mn, mx = trcalc.get_minmax_dtype(data.dtype)
        res_np = data * self._lum / np.array((self._rval, self._gval,
                                              self._bval))
        res_np = res_np.clip(mn, mx).astype(data.dtype)
        print("calculated result")

        self.pipeline.send(res_np=res_np)

    def export_as_dict(self):
        d = super().export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super().import_from_dict(d)
        self.rval = d['rval']
        self.gval = d['gval']
        self.bval = d['bval']
        self.lum = d['lum']
