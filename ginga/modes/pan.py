#
# pan.py -- mode for scaling (zooming) and panning
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Pan Mode enables bindings that can set the pan position (the
position under the center pixel) and zoom level (scale) in a Ginga
image viewer.

Enter the mode by
-----------------
* Space, then "q"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* plus, equals : zoom in one zoom level
* minus, underscore : zoom out one zoom level
* 1-9,0 : zoom to level N (0 is 10)
* Shift + 1-9,0 : zoom to level -N (0 is -10)
* backquote : fit image to window size
* doublequote : toggle auto fit for new images "on" or "off" in this viewer
* singlequote : set auto fit for new images to "override" in this viewer
* p : pan to the position under the cursor
* c : pan to the center of the image
* z : save zoom level (scale)
* r : pan to cursor and zoom to saved scale level
* left/right/up/down arrow : pan left/right/up/down by a small percentage
* Shift + left/right/up/down arrow : pan left/right/up/down by a
  very small percentage
* pageup (pagedown) : pan up (down) by a large percentage of the screen
* home (end) : pan towards the top (bottom) of the image
* "?" : toggle auto center for new images "on" or "off" in this viewer
* "/" : set auto center for new images to "override" in this viewer
* scroll : zoom (scale) the image
* left drag : pan the view
* right drag : camera pan the view

"""
import math

from ginga.modes.mode_base import Mode


class PanMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_pan=['__q', None, 'pan'],

            kp_zoom_in=['+', '='],
            kp_zoom_out=['-', '_'],
            kp_zoom=['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            kp_zoom_inv=['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
            kp_zoom_fit=['backquote', 'pan+backquote'],
            kp_autozoom_toggle=['doublequote', 'pan+doublequote'],
            kp_autozoom_override=['singlequote', 'pan+singlequote'],
            kp_pan_set=['p', 'pan+p'],
            kp_pan_zoom_set=['pan+r'],
            kp_pan_zoom_save=['pan+z'],
            kp_pan_left=['pan+*+left'],
            kp_pan_right=['pan+*+right'],
            kp_pan_up=['pan+*+up'],
            kp_pan_down=['pan+*+down'],
            kp_pan_home=['pan+*+home'],
            kp_pan_end=['pan+*+end'],
            kp_pan_page_up=['pan+*+page_up'],
            kp_pan_page_down=['pan+*+page_down'],
            kp_pan_px_xminus=['shift+left'],
            kp_pan_px_xplus=['shift+right'],
            kp_pan_px_yminus=['shift+down'],
            kp_pan_px_yplus=['shift+up'],
            kp_pan_px_center=['shift+home'],
            kp_center=['c', 'pan+c'],
            kp_autocenter_toggle=['?', 'pan+?'],
            kp_autocenter_override=['/', 'pan+/'],

            sc_pan=['ctrl+scroll'],
            sc_pan_fine=['pan+shift+scroll'],
            sc_pan_coarse=['pan+ctrl+scroll'],
            sc_zoom=['scroll'],
            sc_zoom_fine=[],
            sc_zoom_coarse=[],
            sc_zoom_origin=['shift+scroll'],

            ms_pan=['pan+left', 'ctrl+left'],
            ms_zoom=['pan+right'],
            ms_panset=['pan+middle', 'shift+left', 'middle'],

            pi_zoom=['pinch'],
            pi_zoom_origin=['shift+pinch'],
            pa_pan=['pan'],

            # can be list of any of: 'zoom', 'rotate'
            pinch_actions=['zoom'],
            scroll_pan_acceleration=1.0,
            scroll_pan_lock_x=False,
            scroll_pan_lock_y=False,
            # 1.0 is appropriate for a mouse, 0.1 for most trackpads
            scroll_zoom_acceleration=1.0,
            #scroll_zoom_acceleration=0.1,
            scroll_zoom_direct_scale=False,

            pan_reverse=False,
            pan_multiplier=1.0,
            #pan_min_scroll_thumb_pct=0.0,
            #pan_max_scroll_thumb_pct=0.9,
            zoom_scroll_reverse=False,

            mouse_zoom_acceleration=1.085,
            # pct of a window of data to move with pan key commands
            key_pan_pct=0.666667,
            # amount to move (in pixels) when using key pan arrow
            key_pan_px_delta=1.0,

            # No messages for following operations:
            msg_panset=False)

        # TODO: define pan cursor

        self._pantype = 1
        self._start_panx = 0
        self._start_pany = 0

        self._start_scale_x = 0
        self._start_scale_y = 0

        self._save = {}

    @property
    def canpan(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('pan')

    @property
    def canzoom(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('zoom')

    @property
    def canrotate(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('rotate')

    def __str__(self):
        return 'pan'

    def start(self):
        self.viewer.switch_cursor('pan')

    def stop(self):
        self.viewer.switch_cursor('pick')
        self.onscreen_message(None)

    #####  Help methods #####
    # Methods used by the callbacks to do actions.

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
            return

        msg = self.settings.get('msg_zoom', msg)

        self.zoom_step(viewer, event, msg=msg, origin=origin,
                       adjust=1.5)

    def _pinch_zoom_rotate(self, viewer, state, rot_deg, scale, msg=True,
                           origin=None):
        pinch_actions = self.settings.get('pinch_actions', [])

        with viewer.suppress_redraw:

            if state == 'start':
                self._start_scale_x, self._start_scale_y = viewer.get_scale_xy()
                self._start_rot = viewer.get_rotation()
                return

            if origin is not None:
                # get cartesian canvas coords of data item under cursor
                data_x, data_y = origin[:2]
                off_x, off_y = viewer.data_to_offset(data_x, data_y)
                # set the pan position to the data item
                viewer.set_pan(data_x, data_y)

            msg_str = None
            if self.canzoom and 'zoom' in pinch_actions:
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

            if self.canrotate and 'rotate' in pinch_actions:
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

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_pan_set(self, viewer, event, data_x, data_y, msg=True):
        """Sets the pan position under the cursor."""
        if not self.canpan:
            return False
        event.accept()
        self._panset(viewer, data_x, data_y, msg=msg)

    def kp_pan_zoom_set(self, viewer, event, data_x, data_y, msg=True):
        """Sets the pan position under the cursor."""
        if not self.canpan:
            return False
        event.accept()
        reg = 1
        with viewer.suppress_redraw:
            viewer.panset_xy(data_x, data_y)
            scale_x, scale_y = self._save.get((viewer, 'scale', reg),
                                              (1.0, 1.0))
            viewer.scale_to(scale_x, scale_y)

    def kp_pan_zoom_save(self, viewer, event, data_x, data_y, msg=True):
        """Save the current viewer scale for future use with
        kp_pan_zoom_set()."""
        if not self.canpan:
            return False
        event.accept()
        reg = 1
        scale = viewer.get_scale_xy()
        self._save[(viewer, 'scale', reg)] = scale
        if msg:
            self.onscreen_message("Saved current scale", delay=0.5)

    def kp_pan_left(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        amt = self._get_key_pan_pct(event)
        viewer.pan_lr(amt, -0.1)

    def kp_pan_right(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        amt = self._get_key_pan_pct(event)
        viewer.pan_lr(amt, 0.1)

    def kp_pan_up(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        amt = self._get_key_pan_pct(event)
        viewer.pan_ud(amt, 0.1)

    def kp_pan_down(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        amt = self._get_key_pan_pct(event)
        viewer.pan_ud(amt, -0.1)

    def kp_pan_page_up(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        amt = self._get_key_pan_pct(event)
        pct = 1.0
        if 'ctrl' in event.modifiers:
            # adjust X axis
            viewer.pan_lr(amt, pct)
        else:
            # adjust Y axis
            viewer.pan_ud(amt, pct)

    def kp_pan_page_down(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        amt = self._get_key_pan_pct(event)
        pct = -1.0
        if 'ctrl' in event.modifiers:
            # adjust X axis
            viewer.pan_lr(amt, pct)
        else:
            # adjust Y axis
            viewer.pan_ud(amt, pct)

    def kp_pan_home(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        res = viewer.calc_pan_pct(pad=0)
        # 1.0 == max
        if 'ctrl' in event.modifiers:
            # adjust X axis
            viewer.pan_by_pct(1.0, res.pan_pct_y)
        else:
            # adjust Y axis
            viewer.pan_by_pct(res.pan_pct_x, 1.0)

    def kp_pan_end(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        res = viewer.calc_pan_pct(pad=0)
        # 0.0 == min
        if 'ctrl' in event.modifiers:
            # adjust X axis
            viewer.pan_by_pct(0.0, res.pan_pct_y)
        else:
            # adjust Y axis
            viewer.pan_by_pct(res.pan_pct_x, 0.0)

    def kp_pan_px_xminus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(-px_amt, 0.0)

    def kp_pan_px_xplus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(px_amt, 0.0)

    def kp_pan_px_yminus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(0.0, -px_amt)

    def kp_pan_px_yplus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(0.0, px_amt)

    def kp_pan_px_center(self, viewer, event, data_x, data_y, msg=True):
        """This pans so that the cursor is over the center of the
        current pixel."""
        if not self.canpan:
            return False
        event.accept()
        viewer.pan_center_px()

    def kp_center(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        viewer.center_image()

    def kp_zoom_out(self, viewer, event, data_x, data_y, msg=True):
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)
        viewer.zoom_out()
        if msg:
            self.onscreen_message(viewer.get_scale_text(), delay=1.0)

    def kp_zoom_in(self, viewer, event, data_x, data_y, msg=True):
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)
        viewer.zoom_in()
        if msg:
            self.onscreen_message(viewer.get_scale_text(), delay=1.0)

    def kp_zoom(self, viewer, event, data_x, data_y, msg=True):
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)
        keylist = self.settings.get('kp_zoom')
        try:
            zoomval = (keylist.index(event.key))
        except IndexError:
            return
        viewer.zoom_to(zoomval)
        if msg:
            self.onscreen_message(viewer.get_scale_text(), delay=1.0)

    def kp_zoom_inv(self, viewer, event, data_x, data_y, msg=True):
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)
        keylist = self.settings.get('kp_zoom_inv')
        try:
            zoomval = - (keylist.index(event.key))
        except IndexError:
            return
        viewer.zoom_to(zoomval)
        if msg:
            self.onscreen_message(viewer.get_scale_text(), delay=1.0)

    def kp_zoom_fit(self, viewer, event, data_x, data_y, msg=True):
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)
        viewer.zoom_fit()
        if msg:
            self.onscreen_message(viewer.get_scale_text(), delay=1.0)

    def kp_autozoom_toggle(self, viewer, event, data_x, data_y, msg=True):
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)
        val = viewer.get_settings().get('autozoom')
        if val == 'off':
            val = 'on'
        else:
            val = 'off'
        viewer.enable_autozoom(val)
        if msg:
            self.onscreen_message('Autozoom %s' % val, delay=1.0)

    def kp_autozoom_override(self, viewer, event, data_x, data_y, msg=True):
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)
        viewer.enable_autozoom('override')
        if msg:
            self.onscreen_message('Autozoom Override', delay=1.0)

    def kp_autocenter_toggle(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        msg = self.settings.get('msg_pan', msg)
        val = viewer.get_settings().get('autocenter')
        if val == 'off':
            val = 'on'
        else:
            val = 'off'
        viewer.set_autocenter(val)
        if msg:
            self.onscreen_message('Autocenter %s' % val, delay=1.0)

    def kp_autocenter_override(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        event.accept()
        msg = self.settings.get('msg_pan', msg)
        viewer.set_autocenter('override')
        if msg:
            self.onscreen_message('Autocenter Override', delay=1.0)

    #####  SCROLL ACTION CALLBACKS #####

    def sc_zoom(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by the zoom steps configured under Preferences.
        """
        event.accept()
        self._sc_zoom(viewer, event, msg=msg, origin=None)

    def sc_zoom_origin(self, viewer, event, msg=True):
        """Like sc_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        event.accept()
        origin = (event.data_x, event.data_y)
        self._sc_zoom(viewer, event, msg=msg, origin=origin)

    def sc_zoom_coarse(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if not self.canzoom:
            return False
        event.accept()

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
        # change scale by 20%
        amount = self._scale_adjust(1.2, event.amount, zoom_accel, max_limit=4.0)
        self._scale_image(viewer, event.direction, amount, msg=msg)

    def sc_zoom_fine(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if not self.canzoom:
            return False
        event.accept()

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
        # change scale by 5%
        amount = self._scale_adjust(1.05, event.amount, zoom_accel, max_limit=4.0)
        self._scale_image(viewer, event.direction, amount, msg=msg)

    def sc_pan(self, viewer, event, msg=True):
        """Interactively pan the image by scrolling motion.
        """
        if not self.canpan:
            return False
        event.accept()

        # User has "Pan Reverse" preference set?
        rev = self.settings.get('pan_reverse', False)
        direction = event.direction

        if rev:
            direction = math.fmod(direction + 180.0, 360.0)

        pan_accel = self.settings.get('scroll_pan_acceleration', 1.0)
        # Internal factor to adjust the panning speed so that user-adjustable
        # scroll_pan_acceleration is normalized to 1.0 for "normal" speed
        scr_pan_adj_factor = 1.4142135623730951
        amount = (event.amount * scr_pan_adj_factor * pan_accel) / 360.0

        lock_x = self.settings.get('scroll_pan_lock_x', False)
        lock_y = self.settings.get('scroll_pan_lock_y', False)

        viewer.pan_omni(direction, amount, lock_x=lock_x, lock_y=lock_y)

    def sc_pan_coarse(self, viewer, event, msg=True):
        if not self.canpan:
            return False
        event.accept()
        event.amount = event.amount / 2.0
        self.sc_pan(viewer, event, msg=msg)

    def sc_pan_fine(self, viewer, event, msg=True):
        if not self.canpan:
            return False
        event.accept()
        event.amount = event.amount / 5.0
        self.sc_pan(viewer, event, msg=msg)

    #####  MOUSE ACTION CALLBACKS #####

    def ms_zoom(self, viewer, event, data_x, data_y, msg=True):
        """Zoom the image by dragging the cursor left or right.
        """
        if not self.canzoom:
            return False
        event.accept()
        msg = self.settings.get('msg_zoom', msg)

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._zoom_xy(viewer, x, y)

        elif event.state == 'down':
            if msg:
                self.onscreen_message("Zoom (drag mouse L-R)",
                                      delay=1.0)
            self._start_x, self._start_y = x, y

        else:
            self.onscreen_message(None)

    def ms_pan(self, viewer, event, data_x, data_y):
        """A 'drag' or proportional pan, where the image is panned by
        'dragging the canvas' up or down.  The amount of the pan is
        proportionate to the length of the drag.
        """
        if not self.canpan:
            return False
        event.accept()

        x, y = viewer.get_last_win_xy()
        if event.state == 'move':
            data_x, data_y = self.get_new_pan(viewer, x, y,
                                              ptype=self._pantype)
            viewer.panset_xy(data_x, data_y)

        elif event.state == 'down':
            self.pan_set_origin(viewer, x, y, data_x, data_y)
            self.pan_start(viewer, ptype=2)

        else:
            self.pan_stop(viewer)

    def ms_panset(self, viewer, event, data_x, data_y,
                  msg=True):
        """An interactive way to set the pan position.  The location
        (data_x, data_y) will be centered in the window.
        """
        if not self.canpan:
            return False
        event.accept()
        if event.state == 'down':
            self._panset(viewer, data_x, data_y, msg=msg)

    ##### GESTURE ACTION CALLBACKS #####

    def pa_pan(self, viewer, event, msg=True):
        """Interactively pan the image by a pan gesture.
        (the back end must support gestures)
        """
        if not self.canpan:
            return False
        event.accept()

        method = 1
        x, y = viewer.get_last_win_xy()
        dx, dy = event.delta_x, event.delta_y

        # User has "Pan Reverse" preference set?
        rev = self.settings.get('pan_reverse', False)
        if rev:
            dx, dy = -dx, -dy

        if event.state == 'move':
            # Internal factor to adjust the panning speed so that user-adjustable
            # pan_pan_acceleration is normalized to 1.0 for "normal" speed
            pan_pan_adj_factor = 1.0
            pan_accel = (self.settings.get('pan_pan_acceleration', 1.0) *
                         pan_pan_adj_factor)

            if method == 1:
                # METHOD 1
                # similar to moving by the scroll bars
                # calculate current pan pct
                res = viewer.calc_pan_pct(pad=0)

                # modify the pct, as relative to the offsets
                amt_x = float(dx) / res.rng_x * pan_accel
                amt_y = float(dy) / res.rng_y * pan_accel

                pct_x = res.pan_pct_x - amt_x
                pct_y = res.pan_pct_y + amt_y

                # update the pan position by pct
                viewer.pan_by_pct(pct_x, pct_y)

            elif method == 2:
                # METHOD 2
                # similar to using a drag pan
                x, y = x + dx * pan_accel, y + dy * pan_accel

                data_x, data_y = self.get_new_pan(viewer, x, y,
                                                  ptype=self._pantype)
                viewer.panset_xy(data_x, data_y)

            elif method == 3:
                # METHOD 3
                # calculate new position from pan gesture offsets
                data_x, data_y = viewer.get_pan(coord='data')
                x, y = viewer.get_canvas_xy(data_x, data_y)

                x, y = x - dx * pan_accel, y - dy * pan_accel

                data_x, data_y = viewer.get_data_xy(x, y)
                viewer.panset_xy(data_x, data_y)

        elif event.state == 'start':
            #self._start_panx, self._start_pany = viewer.get_pan()
            data_x, data_y = viewer.get_last_data_xy()
            self.pan_set_origin(viewer, x, y, data_x, data_y)
            self.pan_start(viewer, ptype=2)

        else:
            self.pan_stop(viewer)

    def pi_zoom(self, viewer, event, msg=True):
        """Zoom and/or rotate the viewer by a pinch gesture.
        (the back end must support gestures)
        """
        if not self.canzoom:
            return False
        event.accept()
        self._pinch_zoom_rotate(viewer, event.state, event.rot_deg,
                                event.scale, msg=msg)

    def pi_zoom_origin(self, viewer, event, msg=True):
        """Like pi_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        if not self.canzoom:
            return False
        event.accept()
        origin = (event.data_x, event.data_y)
        self._pinch_zoom_rotate(viewer, event.state, event.rot_deg,
                                event.scale, msg=msg, origin=origin)
