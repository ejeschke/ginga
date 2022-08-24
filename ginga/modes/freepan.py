#
# freepan.py -- mode for scaling (zooming) and panning
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""FreePan Mode enables bindings that can set the pan position
(the center pixel) and zoom level (scale) in a Ginga image viewer.

It differs from Pan mode in the types of scrolling and panning
controls.

Enter the mode by
-----------------
* Space, then "w"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* middle drag : freely pan around the image
* left click : set pan under the cursor and zoom in
* right click : zoom out
* pan gesture : zoom in/out of the image
* Shift + pan gesture : zoom in/out of the image with origin set

"""
from ginga.modes.pan import PanMode


class FreePanMode(PanMode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_freepan=['__w', None, 'pan'],

            kp_zoom_fit=['freepan+backquote'],
            kp_pan_set=['freepan+p'],
            kp_pan_zoom_set=['freepan+r'],
            kp_pan_zoom_save=['freepan+z'],
            kp_pan_left=['freepan+*+left'],
            kp_pan_right=['freepan+*+right'],
            kp_pan_up=['freepan+*+up'],
            kp_pan_down=['freepan+*+down'],
            kp_pan_home=['freepan+*+home'],
            kp_pan_end=['freepan+*+end'],
            kp_pan_page_up=['freepan+*+page_up'],
            kp_pan_page_down=['freepan+*+page_down'],
            kp_center=['freepan+c'],

            sc_zoom=['freepan+scroll'],
            sc_zoom_origin=['freepan+shift+scroll'],

            ms_freepan=['freepan+middle'],
            ms_zoom_in=['freepan+left'],
            ms_zoom_out=['freepan+right', 'freepan+ctrl+left'],

            pa_zoom=['freepan+pan'],
            pa_zoom_origin=['freepan+shift+pan'])

    def __str__(self):
        return 'freepan'

    def start(self):
        self.viewer.switch_cursor('pan')

    def stop(self):
        self.viewer.switch_cursor('pick')
        self.onscreen_message(None)

    #####  KEYBOARD ACTION CALLBACKS #####

    #####  SCROLL ACTION CALLBACKS #####

    #####  MOUSE ACTION CALLBACKS #####

    def ms_freepan(self, viewer, event, data_x, data_y):
        """A 'free' pan, where the image is panned by dragging the cursor
        towards the area you want to see in the image.  The entire image is
        pannable by dragging towards each corner of the window.
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
            self.pan_start(viewer, ptype=1)

        else:
            self.pan_stop(viewer)

    def ms_zoom_in(self, viewer, event, data_x, data_y, msg=False):
        """Zoom in one level by a mouse click.
        """
        if not self.canzoom:
            return False
        event.accept()

        if not (event.state == 'down'):
            return

        with viewer.suppress_redraw:
            viewer.panset_xy(data_x, data_y)

            if self.settings.get('scroll_zoom_direct_scale', True):
                zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
                # change scale by 100%
                amount = self._scale_adjust(2.0, 15.0, zoom_accel, max_limit=4.0)
                self._scale_image(viewer, 0.0, amount, msg=msg)
            else:
                viewer.zoom_in()

            if hasattr(viewer, 'center_cursor'):
                viewer.center_cursor()
            if msg:
                self.onscreen_message(viewer.get_scale_text(),
                                      delay=1.0)

    def ms_zoom_out(self, viewer, event, data_x, data_y, msg=False):
        """Zoom out one level by a mouse click.
        """
        if not self.canzoom:
            return False
        event.accept()

        if not (event.state == 'down'):
            return

        with viewer.suppress_redraw:
            # TODO: think about whether it is the correct behavior to
            # set the pan position when zooming out
            #viewer.panset_xy(data_x, data_y)

            if self.settings.get('scroll_zoom_direct_scale', True):
                zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
                # change scale by 100%
                amount = self._scale_adjust(2.0, 15.0, zoom_accel, max_limit=4.0)
                self._scale_image(viewer, 180.0, amount, msg=msg)
            else:
                viewer.zoom_out()

            if hasattr(viewer, 'center_cursor'):
                viewer.center_cursor()
            if msg:
                self.onscreen_message(viewer.get_scale_text(),
                                      delay=1.0)
        return True

    ##### GESTURE ACTION CALLBACKS #####

    def pa_zoom(self, viewer, event, msg=True):
        """Interactively zoom the image by a pan gesture.
        (the back end must support gestures)
        """
        if not self.canzoom:
            return False
        event.accept()
        event = self._pa_synth_scroll_event(event)
        if event.state == 'move':
            self._sc_zoom(viewer, event, msg=msg, origin=None)

    def pa_zoom_origin(self, viewer, event, msg=True):
        """Like pa_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        if not self.canzoom:
            return False
        event.accept()
        event = self._pa_synth_scroll_event(event)
        if event.state == 'move':
            origin = (event.data_x, event.data_y)
            self._sc_zoom(viewer, event, msg=msg, origin=origin)
