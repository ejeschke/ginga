#
# panzoom_base.py -- mode for scaling (zooming) and panning
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy as np

from ginga.misc import Bunch
from ginga.modes.mode_base import Mode


class PanZoomMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        # TODO: define pan cursor

        self._pantype = 1
        self._start_panx = 0
        self._start_pany = 0

        self._start_scale_x = 0
        self._start_scale_y = 0

    def get_new_pan(self, viewer, win_x, win_y, ptype=1):

        if ptype == 1:
            # This is a "free pan", similar to dragging the "lens"
            # over the canvas.
            xy_mn, xy_mx = viewer.get_limits()
            win_wd, win_ht = viewer.get_window_size()

            if (win_x >= win_wd):
                win_x = win_wd - 1
            if (win_y >= win_ht):
                win_y = win_ht - 1

            # Figure out data x,y based on percentage of X axis
            # and Y axis
            off_x, off_y = viewer.window_to_offset(win_x, win_y)
            max_x, max_y = viewer.window_to_offset(win_wd, win_ht)
            wd_x = abs(max_x) * 2.0
            ht_y = abs(max_y) * 2.0
            panx = (off_x + abs(max_x)) / float(wd_x)
            pany = (off_y + abs(max_y)) / float(ht_y)

            # Account for user preference
            if self.settings.get('pan_reverse', False):
                panx = 1.0 - panx
                pany = 1.0 - pany

            data_x = (xy_mn[0] + xy_mx[0]) * panx
            data_y = (xy_mn[1] + xy_mx[1]) * pany
            return data_x, data_y

        elif ptype == 2:
            # This is a "drag pan", similar to dragging the canvas
            # under the "lens" or "viewport".
            if self._start_x is None:
                # user has not held the mouse button yet
                # return current pan values
                return (self._start_panx, self._start_pany)

            scale_x, scale_y = viewer.get_scale_xy()
            multiplier = self.settings.get('pan_multiplier', 1.0)
            off_x, off_y = viewer.window_to_offset(win_x, win_y)
            delta_x = float(self._start_x - off_x) / scale_x * multiplier
            delta_y = float(self._start_y - off_y) / scale_y * multiplier

            data_x = self._start_panx + delta_x
            data_y = self._start_pany + delta_y

        return (data_x, data_y)

    def _panset(self, viewer, data_x, data_y, msg=True):
        try:
            msg = self.settings.get('msg_panset', msg)
            if msg:
                self.onscreen_message("Pan position set", delay=0.4)

            res = viewer.panset_xy(data_x, data_y)
            return res

        except Exception as e:
            self.onscreen_message("Pan position set error; see log",
                                  delay=2.0)
            # most likely image does not have a valid wcs
            self.logger.error("Error setting pan position: %s" % (
                str(e)))

    def _get_key_pan_pct(self, event):
        amt = self.settings.get('key_pan_pct', 2 / 3.0)
        if 'ctrl' in event.modifiers:
            amt /= 5.0
        if 'shift' in event.modifiers:
            amt /= 10.0
        return amt

    def _scale_image(self, viewer, direction, factor, msg=True):
        msg = self.settings.get('msg_zoom', msg)
        rev = self.settings.get('zoom_scroll_reverse', False)
        scale_x, scale_y = viewer.get_scale_xy()
        direction = self.get_direction(direction, rev=rev)
        mult = 1.0
        if direction == 'up':
            mult = factor
        elif direction == 'down':
            mult = 1.0 / factor
        scale_x, scale_y = scale_x * mult, scale_y * mult
        scale = max(scale_x, scale_y)
        #viewer.scale_to(scale_x, scale_y)
        viewer.scale_to(scale, scale)
        if msg:
            self.onscreen_message(viewer.get_scale_text(),
                                  delay=0.4)

    def _scale_adjust(self, factor, event_amt, zoom_accel, max_limit=None):
        # adjust scale by factor, amount encoded in event and zoom acceleration value
        amount = factor - ((factor - 1.0) * (1.0 - min(event_amt, 15.0) / 15.0) *
                           zoom_accel)
        amount = max(1.000000001, amount)
        if max_limit is not None:
            amount = min(amount, max_limit)
        return amount

    def _zoom_xy(self, viewer, x, y, msg=True):
        win_wd, win_ht = viewer.get_window_size()
        delta = float(x - self._start_x)
        factor = self.settings.get('mouse_zoom_acceleration', 1.085)
        direction = 0.0
        if delta < 0.0:
            direction = 180.0
        self._start_x = x
        self._scale_image(viewer, direction, factor, msg=msg)

    def _get_pct_xy(self, viewer, x, y):
        win_wd, win_ht = viewer.get_window_size()
        x_pct = float(x - self._start_x) / win_wd
        y_pct = float(y - self._start_y) / win_ht
        return (x_pct, y_pct)

    def to_default_mode(self, viewer):
        self.reset(viewer)

    def pan_start(self, viewer, ptype=1):
        self._pantype = ptype

    def pan_set_origin(self, viewer, win_x, win_y, data_x, data_y):
        self._start_x, self._start_y = viewer.window_to_offset(win_x, win_y)
        self._start_panx, self._start_pany = viewer.get_pan()

    def pan_stop(self, viewer):
        self._start_x = None
        self._pantype = 1

    def zoom_step(self, viewer, event, msg=True, origin=None, adjust=1.5):
        with viewer.suppress_redraw:

            if origin is not None:
                # get cartesian canvas coords of data item under cursor
                data_x, data_y = origin[:2]
                off_x, off_y = viewer.data_to_offset(data_x, data_y)
                # set the pan position to the data item
                viewer.set_pan(data_x, data_y)

            # scale by the desired means
            if self.settings.get('scroll_zoom_direct_scale', True):
                zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
                # change scale by 50%
                amount = self._scale_adjust(adjust, event.amount, zoom_accel,
                                            max_limit=4.0)
                self._scale_image(viewer, event.direction, amount, msg=msg)

            else:
                rev = self.settings.get('zoom_scroll_reverse', False)
                direction = self.get_direction(event.direction, rev=rev)

                if direction == 'up':
                    viewer.zoom_in()

                elif direction == 'down':
                    viewer.zoom_out()

                if msg:
                    self.onscreen_message(viewer.get_scale_text(),
                                          delay=0.4)

            if origin is not None:
                # now adjust the pan position to keep the offset
                data_x2, data_y2 = viewer.offset_to_data(off_x, off_y)
                dx, dy = data_x2 - data_x, data_y2 - data_y
                viewer.panset_xy(data_x - dx, data_y - dy)

    def _sc_zoom(self, viewer, event, msg=True, origin=None):
        if not self.canzoom:
            return True

        msg = self.settings.get('msg_zoom', msg)

        self.zoom_step(viewer, event, msg=msg, origin=origin,
                       adjust=1.5)
        return True

    def _pinch_zoom_rotate(self, viewer, state, rot_deg, scale, msg=True,
                           origin=None):
        pinch_actions = self.settings.get('pinch_actions', [])

        with viewer.suppress_redraw:

            if state == 'start':
                self._start_scale_x, self._start_scale_y = viewer.get_scale_xy()
                self._start_rot = viewer.get_rotation()
                return True

            if origin is not None:
                # get cartesian canvas coords of data item under cursor
                data_x, data_y = origin[:2]
                off_x, off_y = viewer.data_to_offset(data_x, data_y)
                # set the pan position to the data item
                viewer.set_pan(data_x, data_y)

            msg_str = None
            if self.canzoom and ('zoom' in pinch_actions):
                # scale by the desired means
                scale_accel = self.settings.get('pinch_zoom_acceleration', 1.0)
                scale = scale * scale_accel
                # NOTE: scale reported by Qt (the only toolkit that really gives
                # us a pinch gesture right now) the scale reports are iterative
                # so it makes more sense to keep updating the scale than to base
                # the scale on the original scale captured when the gesture starts
                ## scale_x, scale_y = (self._start_scale_x * scale,
                ##                     self._start_scale_y * scale)
                scale_x, scale_y = viewer.get_scale_xy()
                scale_x, scale_y = scale_x * scale, scale_y * scale

                viewer.scale_to(scale_x, scale_y)
                msg_str = viewer.get_scale_text()
                msg = self.settings.get('msg_zoom', True)

            if self.canrotate and ('rotate' in pinch_actions):
                deg = self._start_rot - rot_deg
                rotate_accel = self.settings.get('pinch_rotate_acceleration', 1.0)
                deg = rotate_accel * deg
                viewer.rotate(deg)
                if msg_str is None:
                    msg_str = "Rotate: %.2f" % (deg)
                    msg = self.settings.get('msg_rotate', msg)

            if origin is not None:
                # now adjust the pan position to keep the offset
                data_x2, data_y2 = viewer.offset_to_data(off_x, off_y)
                dx, dy = data_x2 - data_x, data_y2 - data_y
                viewer.panset_xy(data_x - dx, data_y - dy)

            if msg and (msg_str is not None):
                self.onscreen_message(msg_str, delay=0.4)

        return True
