# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.canvas.CanvasObject import get_canvas_types
#from ginga import trcalc
from ginga.gw import Widgets
from ginga.util import action

from .base import Stage


class Crop(Stage):

    _stagename = 'crop-image'

    def __init__(self):
        super(Crop, self).__init__()

        self.dc = get_canvas_types()
        self.cropcolor = 'yellow'
        self.layertag = 'crop-layer'
        self._crop_rect = (0.0, 0.0, 1.0, 1.0)
        self._aspect = None
        self._img_dims = (1, 1)

        canvas = self.dc.DrawingCanvas()
        canvas.enable_edit(True)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.set_draw_mode('edit')
        self.canvas = canvas

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')

        fr = Widgets.Frame("Crop")

        captions = (('Crop %:', 'label', 'crop', 'llabel'),
                    ('Output size:', 'label', 'size', 'llabel'),
                    ('Aspect:', 'label', 'aspect', 'entryset'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        arr = np.asarray(self._crop_rect) * 100.0
        crop = "%6.2f,%6.2f to %6.2f,%6.2f" % tuple(arr)
        b.crop.set_text(crop)

        b.aspect.set_tooltip("Set the aspect ratio (wd/ht)")
        b.aspect.add_callback('activated', self._set_aspect_cb)
        if self._aspect is not None:
            b.aspect.set_text(str(self._aspect))

        fr.set_widget(w)
        container.set_widget(fr)

        self.canvas.set_surface(self.viewer)
        self.canvas.register_for_cursor_drawing(self.viewer)

        wd, ht = 100, 100
        self.crop_obj = self.dc.CompoundObject(
            self.dc.Rectangle(0, 0, wd, ht,
                              color=self.cropcolor),
            self.dc.Text(0, 0, "Crop",
                         color=self.cropcolor))
        self.crop_obj.objects[1].editable = False

        self._gui_update_crop()
        self.w.size.set_text("unknown")

    @property
    def crop_rect(self):
        return self._crop_rect

    @crop_rect.setter
    def crop_rect(self, val):
        self._crop_rect = val
        if self.gui_up:
            self._gui_update_crop()

    @property
    def aspect(self):
        return self._aspect

    @aspect.setter
    def aspect(self, val):
        self._aspect = val
        if self.gui_up:
            asp = self._aspect
            self.w.aspect.set_text('' if asp is None else str(asp))

    def _gui_update_crop(self):
        arr = np.asarray(self._crop_rect) * 100.0
        crop = "%6.2f,%6.2f to %6.2f,%6.2f" % tuple(arr)

        self.w.crop.set_text(crop)

    def resume(self):
        # insert canvas, if not already
        p_canvas = self.viewer.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        if not self.canvas.has_object(self.crop_obj):
            self.canvas.add(self.crop_obj)

        self.canvas.ui_set_active(True, viewer=self.viewer)

    def pause(self):
        self.canvas.ui_set_active(False)

        # remove the canvas from the image
        p_canvas = self.viewer.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass

    def edit_cb(self, canvas, obj):
        if obj.kind != 'rectangle':
            return True

        x1, y1, x2, y2 = obj.get_llur()
        old = self._get_state()
        self._update_crop_rect(x1, y1, x2, y2)
        new = self._get_state()
        self.pipeline.push(action.AttrAction(self, old, new,
                                             descr="change crop"))
        self.pipeline.run_from(self)

    def _update_crop_rect(self, x1, y1, x2, y2):
        # reposition other elements to match
        if self.aspect is not None:
            x1, y1, x2, y2 = self._enforce_aspect(x1, y1, x2, y2)
        rect = self.crop_obj.objects[0]
        rect.x1, rect.y1, rect.x2, rect.y2 = x1, y1, x2, y2
        text = self.crop_obj.objects[1]
        text.x, text.y = x1, y2 + 4
        self.viewer.redraw(whence=3)

        wd, ht = self._img_dims
        self.set_crop_rect(wd, ht, x1, y1, x2, y2)

    def set_crop_rect(self, wd, ht, x1, y1, x2, y2):
        x1p, y1p, x2p, y2p = [x1 / wd, y1 / ht, x2 / wd, y2 / ht]
        self.crop_rect = (x1p, y1p, x2p, y2p)

    def get_crop_rect_px(self, wd, ht, use_image_lim=False):
        x1p, y1p, x2p, y2p = np.array(self._crop_rect)
        x1, y1, x2, y2 = (int(x1p * wd), int(y1p * ht),
                          int(x2p * wd), int(y2p * ht))
        if use_image_lim:
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(x2, wd), min(y2, ht)
        return x1, y1, x2, y2

    def _set_aspect(self, asp_s):
        wd, ht = self._img_dims
        x1, y1, x2, y2 = self.get_crop_rect_px(wd, ht)

        if len(asp_s) == 0:
            self._aspect = None

        else:
            if ':' in asp_s:
                wd, ht = [float(n) for n in asp_s.split(':')]
                self._aspect = wd / ht
            else:
                self._aspect = float(asp_s)

        self._update_crop_rect(x1, y1, x2, y2)

    def _set_aspect_cb(self, widget):
        asp_s = widget.get_text().strip()
        old = self._get_state()
        self._set_aspect(asp_s)
        new = self._get_state()
        self.pipeline.push(action.AttrAction(self, old, new,
                                             descr="set aspect ratio"))
        self.pipeline.run_from(self)

    def _enforce_aspect(self, x1, y1, x2, y2):

        ctr_x, ctr_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if self.aspect > 0:
            wd = x2 - x1
            hht = wd / self.aspect * 0.5
            ctr_y = (y1 + y2) * 0.5
            y1, y2 = ctr_y - hht, ctr_y + hht
        else:
            ht = y2 - y1
            hwd = ht / self.aspect * 0.5
            ctr_x = (x1 + x2) * 0.5
            x1, x2 = ctr_x - hwd, ctr_x + hwd

        return x1, y1, x2, y2

    def _get_state(self):
        return dict(crop_rect=[float(n) for n in self._crop_rect],
                    aspect=self._aspect)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        ht, wd = data.shape[:2]
        dims = (wd, ht)

        if self._img_dims != dims:
            self._img_dims = dims

        x1, y1, x2, y2 = self.get_crop_rect_px(wd, ht,
                                               use_image_lim=True)
        res_np = data[y1:y2, x1:x2, ...]

        if self.gui_up:
            _ht, _wd = res_np.shape[:2]
            ## try:
            ##     asp_s = trcalc.calc_aspect_str(_wd, _ht)
            ## except Exception as e:
            ##     # sometimes Numpy throws a NaN error here
            ##     asp_s = "{}:{}".format(_wd, _ht)
            asp = _wd / _ht
            s = "{}x{} ({})".format(_wd, _ht, asp)
            self.w.size.set_text(s)

        self.pipeline.send(res_np=res_np)

    def export_as_dict(self):
        d = super(Crop, self).export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super(Crop, self).import_from_dict(d)
        self.crop_rect = d['crop_rect']
        self.aspect = d['aspect']
