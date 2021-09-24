#
# pan.py -- mode for scaling (zooming) and panning
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math

from ginga.modes.panzoom_base import PanZoomMode


class PanMode(PanZoomMode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        actions = dict(
            kp_zoom_in=['+', '='],
            kp_zoom_out=['-', '_'],
            kp_zoom=['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            kp_zoom_inv=['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
            kp_zoom_fit=['backquote', 'pan+backquote', 'freepan+backquote'],
            kp_autozoom_toggle=['doublequote', 'pan+doublequote'],
            kp_autozoom_override=['singlequote', 'pan+singlequote'],
            kp_pan_set=['p', 'pan+p', 'freepan+p'],
            kp_pan_zoom_set=['pan+1', 'freepan+1'],
            kp_pan_zoom_save=['pan+z', 'freepan+z'],
            kp_pan_left=['pan+*+left', 'freepan+*+left'],
            kp_pan_right=['pan+*+right', 'freepan+*+right'],
            kp_pan_up=['pan+*+up', 'freepan+*+up'],
            kp_pan_down=['pan+*+down', 'freepan+*+down'],
            kp_pan_home=['pan+*+home', 'freepan+*+home'],
            kp_pan_end=['pan+*+end', 'freepan+*+end'],
            kp_pan_page_up=['pan+*+page_up', 'freepan+*+page_up'],
            kp_pan_page_down=['pan+*+page_down', 'freepan+*+page_down'],
            kp_pan_px_xminus=['shift+left'],
            kp_pan_px_xplus=['shift+right'],
            kp_pan_px_yminus=['shift+down'],
            kp_pan_px_yplus=['shift+up'],
            kp_pan_px_center=['shift+home'],
            kp_center=['c', 'pan+c', 'freepan+c'],
            kp_autocenter_toggle=['?', 'pan+?'],
            kp_autocenter_override=['/', 'pan+/'],

            sc_pan=['ctrl+scroll'],
            sc_pan_fine=['pan+shift+scroll'],
            sc_pan_coarse=['pan+ctrl+scroll'],
            sc_zoom=['scroll', 'freepan+scroll'],
            sc_zoom_fine=[],
            sc_zoom_coarse=[],
            sc_zoom_origin=['shift+scroll', 'freepan+shift+scroll'],

            ms_pan=['pan+left', 'ctrl+left'],
            ms_zoom=['pan+right'],
            ms_panset=['pan+middle', 'shift+left', 'middle'],

            pi_zoom=['pinch'],
            pi_zoom_origin=['shift+pinch'],
            pa_pan=['pan'],

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
            msg_panset=False,
            )
        self.settings.set_defaults(**actions)

        bm = viewer.get_bindmap()
        bm.add_mode('__q', str(self), mode_type='locked', msg=None)

        bd = viewer.get_bindings()
        bd.merge_actions(self.viewer, bm, self, actions.items())

        self._save = {}

        self.canpan = True
        self.canzoom = True

    def __str__(self):
        return 'pan'

    def start(self):
        self.viewer.switch_cursor('pan')

    def stop(self):
        self.viewer.switch_cursor('pick')
        self.onscreen_message(None)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_pan_set(self, viewer, event, data_x, data_y, msg=True):
        """Sets the pan position under the cursor."""
        if self.canpan:
            self._panset(viewer, data_x, data_y, msg=msg)
        return True

    def kp_pan_zoom_set(self, viewer, event, data_x, data_y, msg=True):
        """Sets the pan position under the cursor."""
        if self.canpan:
            reg = 1
            with viewer.suppress_redraw:
                viewer.panset_xy(data_x, data_y)
                scale_x, scale_y = self._save.get((viewer, 'scale', reg),
                                                  (1.0, 1.0))
                viewer.scale_to(scale_x, scale_y)
        return True

    def kp_pan_zoom_save(self, viewer, event, data_x, data_y, msg=True):
        """Save the current viewer scale for future use with
        kp_pan_zoom_set()."""
        reg = 1
        scale = viewer.get_scale_xy()
        self._save[(viewer, 'scale', reg)] = scale
        if msg:
            self.onscreen_message("Saved current scale", delay=0.5)
        return True

    def kp_pan_left(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        viewer.pan_lr(amt, -0.1)
        return True

    def kp_pan_right(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        viewer.pan_lr(amt, 0.1)
        return True

    def kp_pan_up(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        viewer.pan_ud(amt, 0.1)
        return True

    def kp_pan_down(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        viewer.pan_ud(amt, -0.1)
        return True

    def kp_pan_page_up(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        viewer.pan_ud(amt, 1.0)
        return True

    def kp_pan_page_down(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        viewer.pan_ud(amt, -1.0)
        return True

    def kp_pan_home(self, viewer, event, data_x, data_y, msg=True):
        res = viewer.calc_pan_pct(pad=0)
        # 1.0 == max Y
        viewer.pan_by_pct(res.pan_pct_x, 1.0)

    def kp_pan_end(self, viewer, event, data_x, data_y, msg=True):
        res = viewer.calc_pan_pct(pad=0)
        # 0.0 == min Y
        viewer.pan_by_pct(res.pan_pct_x, 0.0)

    def kp_pan_px_xminus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(-px_amt, 0.0)
        return True

    def kp_pan_px_xplus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(px_amt, 0.0)
        return True

    def kp_pan_px_yminus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(0.0, -px_amt)
        return True

    def kp_pan_px_yplus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        viewer.pan_delta_px(0.0, px_amt)
        return True

    def kp_pan_px_center(self, viewer, event, data_x, data_y, msg=True):
        """This pans so that the cursor is over the center of the
        current pixel."""
        if not self.canpan:
            return False
        viewer.pan_center_px()
        return True

    def kp_center(self, viewer, event, data_x, data_y):
        if self.canpan:
            viewer.center_image()
        return True

    def kp_zoom_out(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.zoom_out()
            if msg:
                self.onscreen_message(viewer.get_scale_text(),
                                      delay=1.0)
        return True

    def kp_zoom_in(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.zoom_in()
            if msg:
                self.onscreen_message(viewer.get_scale_text(),
                                      delay=1.0)
        return True

    def kp_zoom(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            keylist = self.settings.get('kp_zoom')
            try:
                zoomval = (keylist.index(event.key))
            except IndexError:
                return False
            viewer.zoom_to(zoomval)
            if msg:
                self.onscreen_message(viewer.get_scale_text(),
                                      delay=1.0)
        return True

    def kp_zoom_inv(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            keylist = self.settings.get('kp_zoom_inv')
            try:
                zoomval = - (keylist.index(event.key))
            except IndexError:
                return False
            viewer.zoom_to(zoomval)
            if msg:
                self.onscreen_message(viewer.get_scale_text(),
                                      delay=1.0)
        return True

    def kp_zoom_fit(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.zoom_fit()
            if msg:
                self.onscreen_message(viewer.get_scale_text(),
                                      delay=1.0)
        return True

    def kp_autozoom_toggle(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            val = viewer.get_settings().get('autozoom')
            if val == 'off':
                val = 'on'
            else:
                val = 'off'
            viewer.enable_autozoom(val)
            if msg:
                self.onscreen_message('Autozoom %s' % val, delay=1.0)
        return True

    def kp_autozoom_override(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.enable_autozoom('override')
            if msg:
                self.onscreen_message('Autozoom Override', delay=1.0)
        return True

    def kp_autocenter_toggle(self, viewer, event, data_x, data_y, msg=True):
        if self.canpan:
            msg = self.settings.get('msg_pan', msg)
            val = viewer.get_settings().get('autocenter')
            if val == 'off':
                val = 'on'
            else:
                val = 'off'
            viewer.set_autocenter(val)
            if msg:
                self.onscreen_message('Autocenter %s' % val, delay=1.0)
        return True

    def kp_autocenter_override(self, viewer, event, data_x, data_y, msg=True):
        if self.canpan:
            msg = self.settings.get('msg_pan', msg)
            viewer.set_autocenter('override')
            if msg:
                self.onscreen_message('Autocenter Override', delay=1.0)
        return True

    #####  SCROLL ACTION CALLBACKS #####

    def sc_zoom(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by the zoom steps configured under Preferences.
        """
        self._sc_zoom(viewer, event, msg=msg, origin=None)
        return True

    def sc_zoom_origin(self, viewer, event, msg=True):
        """Like sc_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        origin = (event.data_x, event.data_y)
        self._sc_zoom(viewer, event, msg=msg, origin=origin)
        return True

    def sc_zoom_coarse(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if not self.canzoom:
            return True

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
        # change scale by 20%
        amount = self._scale_adjust(1.2, event.amount, zoom_accel, max_limit=4.0)
        self._scale_image(viewer, event.direction, amount, msg=msg)
        return True

    def sc_zoom_fine(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if not self.canzoom:
            return True

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
        # change scale by 5%
        amount = self._scale_adjust(1.05, event.amount, zoom_accel, max_limit=4.0)
        self._scale_image(viewer, event.direction, amount, msg=msg)
        return True

    def sc_pan(self, viewer, event, msg=True):
        """Interactively pan the image by scrolling motion.
        """
        if not self.canpan:
            return True

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
        return True

    def sc_pan_coarse(self, viewer, event, msg=True):
        event.amount = event.amount / 2.0
        return self.sc_pan(viewer, event, msg=msg)

    def sc_pan_fine(self, viewer, event, msg=True):
        event.amount = event.amount / 5.0
        return self.sc_pan(viewer, event, msg=msg)

    #####  MOUSE ACTION CALLBACKS #####

    def ms_zoom(self, viewer, event, data_x, data_y, msg=True):
        """Zoom the image by dragging the cursor left or right.
        """
        if not self.canzoom:
            return True
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
        return True

    def ms_pan(self, viewer, event, data_x, data_y):
        """A 'drag' or proportional pan, where the image is panned by
        'dragging the canvas' up or down.  The amount of the pan is
        proportionate to the length of the drag.
        """
        if not self.canpan:
            return True

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
        return True

    def ms_panset(self, viewer, event, data_x, data_y,
                  msg=True):
        """An interactive way to set the pan position.  The location
        (data_x, data_y) will be centered in the window.
        """
        if self.canpan and (event.state == 'down'):
            self._panset(viewer, data_x, data_y, msg=msg)
        return True

    ##### GESTURE ACTION CALLBACKS #####

    def gs_pan(self, viewer, state, dx, dy, msg=True):
        if not self.canpan:
            return True

        method = 1
        x, y = viewer.get_last_win_xy()

        # User has "Pan Reverse" preference set?
        rev = self.settings.get('pan_reverse', False)
        if rev:
            dx, dy = -dx, -dy

        if state == 'move':
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

        elif state == 'start':
            #self._start_panx, self._start_pany = viewer.get_pan()
            data_x, data_y = viewer.get_last_data_xy()
            self.pan_set_origin(viewer, x, y, data_x, data_y)
            self.pan_start(viewer, ptype=2)

        else:
            self.pan_stop(viewer)

        return True

    def gs_pinch(self, viewer, state, rot_deg, scale, msg=True):
        return self._pinch_zoom_rotate(viewer, state, rot_deg, scale, msg=msg)

    def pi_zoom(self, viewer, event, msg=True):
        """Zoom and/or rotate the viewer by a pinch gesture.
        (the back end must support gestures)
        """
        return self._pinch_zoom_rotate(viewer, event.state, event.rot_deg,
                                       event.scale, msg=msg)

    def pi_zoom_origin(self, viewer, event, msg=True):
        """Like pi_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        origin = (event.data_x, event.data_y)
        return self._pinch_zoom_rotate(viewer, event.state, event.rot_deg,
                                       event.scale, msg=msg, origin=origin)

    def pa_pan(self, viewer, event, msg=True):
        """Interactively pan the image by a pan gesture.
        (the back end must support gestures)
        """
        return self.gs_pan(viewer, event.state,
                           event.delta_x, event.delta_y, msg=msg)

    def pa_zoom(self, viewer, event, msg=True):
        """Interactively zoom the image by a pan gesture.
        (the back end must support gestures)
        """
        event = self._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False
        self._sc_zoom(viewer, event, msg=msg, origin=None)
        return True

    def pa_zoom_origin(self, viewer, event, msg=True):
        """Like pa_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        event = self._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False
        origin = (event.data_x, event.data_y)
        self._sc_zoom(viewer, event, msg=msg, origin=origin)
        return True
