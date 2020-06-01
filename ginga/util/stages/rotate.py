# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.canvas.CanvasObject import get_canvas_types
from ginga import trcalc
from ginga.gw import Widgets

from .base import Stage


class Rotate(Stage):

    _stagename = 'rotate'

    def __init__(self):
        super(Rotate, self).__init__()

        self.dc = get_canvas_types()
        self.cropcolor = 'limegreen'
        self.layertag = 'rotate-layer'
        self.rot_deg = 0.0
        self.clip = True
        self.add_alpha = False
        self.rot_obj = None
        self.viewer = None

        canvas = self.dc.DrawingCanvas()
        canvas.enable_edit(True)
        #canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_draw_mode('edit')
        self.canvas = canvas

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')

        fr = Widgets.Frame("Rotate")

        captions = (('Rotate:', 'label', 'Rotate', 'entryset'),
                    ('_sp1', 'spacer', 'hbox1', 'hbox')
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')

        b.rotate.set_tooltip("Rotate the image around the pan position")
        b.rotate.set_text("0.0")
        b.rotate.add_callback('activated', self.rotate_cb)

        b.clip = Widgets.CheckBox("Clip")
        b.clip.set_state(self.clip)
        b.clip.set_tooltip("Clip rotated image")
        b.clip.add_callback('activated', self.clip_cb)
        b.hbox1.add_widget(b.clip, stretch=0)

        b.add_alpha = Widgets.CheckBox("Add alpha")
        b.add_alpha.set_state(self.add_alpha)
        b.add_alpha.set_tooltip("Add alpha channel to rotated image")
        b.add_alpha.add_callback('activated', self.add_alpha_cb)
        b.hbox1.add_widget(b.add_alpha, stretch=0)

        b.copy_from_viewer = Widgets.Button("Copy from viewer")
        b.copy_from_viewer.set_tooltip("Copy rotation setting from viewer")
        b.copy_from_viewer.add_callback('activated', self.copy_from_viewer_cb)
        b.hbox1.add_widget(b.copy_from_viewer, stretch=0)
        b.hbox1.add_widget(Widgets.Label(''), stretch=1)

        self.w.update(b)
        fr.set_widget(w)

        container.set_widget(fr)

        self.viewer = self.pipeline.get('viewer')
        self.canvas.set_surface(self.viewer)
        self.canvas.register_for_cursor_drawing(self.viewer)

        self.rot_obj = self.dc.Crosshair(100, 100)

    def rotate_cb(self, widget):
        self.rot_deg = float(widget.get_text().strip())
        self.pipeline.run_from(self)

    def clip_cb(self, widget, tf):
        self.clip = tf
        self.pipeline.run_from(self)

    def add_alpha_cb(self, widget, tf):
        self.add_alpha = tf
        self.pipeline.run_from(self)

    def copy_from_viewer_cb(self, widget):
        self.rot_deg = self.viewer.get_rotation()
        self.w.rotate.set_text(str(self.rot_deg))

        self.pipeline.run_from(self)

    def resume(self):
        # insert canvas, if not already
        p_canvas = self.viewer.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        if not self.canvas.has_object(self.rot_obj):
            self.canvas.add(self.rot_obj)

        self.canvas.ui_set_active(True, viewer=self.viewer)

    def pause(self):
        self.canvas.ui_set_active(False)

        # remove the canvas from the image
        p_canvas = self.viewer.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None or np.isclose(self.rot_deg, 0.0):
            self.pipeline.send(res_np=data)
            return

        if self.add_alpha:
            minv, maxv = trcalc.get_minmax_dtype(data.dtype)
            data = trcalc.add_alpha(data, alpha=maxv)

        if self.clip:
            res_np = trcalc.rotate_clip(data, self.rot_deg,
                                        logger=self.logger)
        else:
            res_np = trcalc.rotate(data, self.rot_deg, pad=0,
                                   logger=self.logger)

        self.pipeline.send(res_np=res_np)
