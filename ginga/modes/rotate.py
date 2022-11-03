#
# rotate.py -- mode for rotating images
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Rotate Mode enables bindings that can flip or swap the axes of an
image, or rotate it, in a Ginga image viewer.

Enter the mode by
-----------------
* Space, then "r"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* "[" : (toggle) flip the image in the X axis
* "{" : Restore the X axis
* "]" : (toggle) flip the image in the Y axis
* "}" : Restore the Y axis
* backslash : (toggle) swap the X and Y axes
* "|" : Restore the swapped axes to normal
* R : reset rotation to 0 deg (does not reset any flips or swaps)
* t : resets any flips or swaps
* period : rotate image incrementally by +90 deg
* comma : rotate image by incrementally -90 deg
* o : orient the image so that North points up and East points left
* O : orient the image so that North points up and East points right
* left drag : rotate the image interactively
* right click : reset the rotation to 0 deg (same as R)
* rotation gesture : rotate the image interactively

"""
import math

from ginga import trcalc
from ginga.util import wcs
from ginga.modes.mode_base import Mode


class RotateMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_rotate=['__r', None, None],

            kp_flip_x=['[', '{', 'rotate+[', 'rotate+{'],
            kp_flip_y=[']', '}', 'rotate+]', 'rotate+}'],
            kp_swap_xy=['backslash', '|', 'rotate+backslash', 'rotate+|'],
            kp_rotate_reset=['R', 'rotate+r', 'rotate+R'],
            kp_transform_reset=['rotate+t'],
            kp_rotate_inc90=['.', 'rotate+.'],
            kp_rotate_dec90=[',', 'rotate+,'],
            kp_orient_lh=['o', 'rotate+o'],
            kp_orient_rh=['O', 'rotate+O'],

            ms_rotate=['rotate+left'],
            ms_rotate_reset=['rotate+right'],
            pi_rotate=['rotate+pinch'],

            mouse_rotate_acceleration=0.75,
            pinch_rotate_acceleration=1.0)

        self._start_rot = 0

    def __str__(self):
        return 'rotate'

    @property
    def canflip(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('flip')

    @property
    def canrotate(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('rotate')

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def _rotate_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_rotate', msg)
        ctr_x, ctr_y = viewer.get_center()
        if None in (self._start_x, self._start_y):
            # missed button down event, most likely, or we're getting this
            # motion callback too early
            return
        deg1 = math.degrees(math.atan2(ctr_y - self._start_y,
                                       self._start_x - ctr_x))
        deg2 = math.degrees(math.atan2(ctr_y - y, x - ctr_x))
        delta_deg = deg2 - deg1
        deg = math.fmod(self._start_rot + delta_deg, 360.0)
        if msg:
            self.onscreen_message("Rotate: %.2f" % (deg))
        viewer.rotate(deg)

    def _rotate_inc(self, viewer, inc_deg, msg=True):
        msg = self.settings.get('msg_rotate_inc', msg)
        cur_rot_deg = viewer.get_rotation()
        rot_deg = math.fmod(cur_rot_deg + inc_deg, 360.0)
        viewer.rotate(rot_deg)
        if msg:
            self.onscreen_message("Rotate Inc: (%.2f) %.2f" % (
                inc_deg, rot_deg), delay=1.0)

    def _orient(self, viewer, righthand=False, msg=True):
        msg = self.settings.get('msg_orient', msg)
        image = viewer.get_image()

        (x, y, xn, yn, xe, ye) = wcs.calc_compass_center(image)
        degn = math.degrees(math.atan2(xn - x, yn - y))
        self.logger.info("degn=%f xe=%f ye=%f" % (
            degn, xe, ye))
        # rotate east point also by degn
        xe2, ye2 = trcalc.rotate_pt(xe, ye, degn, xoff=x, yoff=y)
        dege = math.degrees(math.atan2(xe2 - x, ye2 - y))
        self.logger.info("dege=%f xe2=%f ye2=%f" % (
            dege, xe2, ye2))

        # if right-hand image, flip it to make left hand
        xflip = righthand
        if dege > 0.0:
            xflip = not xflip
        if xflip:
            degn = - degn

        viewer.transform(xflip, False, False)
        viewer.rotate(degn)
        if msg:
            self.onscreen_message("Orient: rot=%.2f flipx=%s" % (
                degn, str(xflip)), delay=1.0)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_flip_x(self, viewer, event, data_x, data_y, msg=True):
        if not self.canflip:
            return False
        event.accept()
        msg = self.settings.get('msg_transform', msg)
        flipX, flipY, swapXY = viewer.get_transforms()
        if event.key == '[':
            flipx = not flipX
        else:
            flipx = False
        viewer.transform(flipx, flipY, swapXY)
        if msg:
            self.onscreen_message("Flip X=%s" % flipx, delay=1.0)

    def kp_flip_y(self, viewer, event, data_x, data_y, msg=True):
        if not self.canflip:
            return False
        event.accept()
        msg = self.settings.get('msg_transform', msg)
        flipX, flipY, swapXY = viewer.get_transforms()
        if event.key == ']':
            flipy = not flipY
        else:
            flipy = False
        viewer.transform(flipX, flipy, swapXY)
        if msg:
            self.onscreen_message("Flip Y=%s" % flipy, delay=1.0)

    def kp_swap_xy(self, viewer, event, data_x, data_y, msg=True):
        if not self.canflip:
            return False
        event.accept()
        msg = self.settings.get('msg_transform', msg)
        flipX, flipY, swapXY = viewer.get_transforms()
        if event.key == 'backslash':
            swapxy = not swapXY
        else:
            swapxy = False
        viewer.transform(flipX, flipY, swapxy)
        if msg:
            self.onscreen_message("Swap XY=%s" % swapxy, delay=1.0)

    def kp_transform_reset(self, viewer, event, data_x, data_y):
        if not self.canflip:
            return False
        event.accept()
        viewer.transform(False, False, False)
        self.onscreen_message("Flips/swaps reset", delay=0.5)

    def kp_rotate_reset(self, viewer, event, data_x, data_y):
        if not self.canrotate:
            return False
        event.accept()
        viewer.rotate(0.0)

    def kp_rotate_inc90(self, viewer, event, data_x, data_y, msg=True):
        if not self.canrotate:
            return False
        event.accept()
        self._rotate_inc(viewer, 90.0, msg=msg)

    def kp_rotate_dec90(self, viewer, event, data_x, data_y, msg=True):
        if not self.canrotate:
            return False
        event.accept()
        self._rotate_inc(viewer, -90.0, msg=msg)

    def kp_orient_lh(self, viewer, event, data_x, data_y, msg=True):
        if not self.canrotate:
            return False
        event.accept()
        self._orient(viewer, righthand=False, msg=msg)

    def kp_orient_rh(self, viewer, event, data_x, data_y, msg=True):
        if not self.canrotate:
            return False
        event.accept()
        self._orient(viewer, righthand=True, msg=msg)

    #####  SCROLL ACTION CALLBACKS #####

    #####  MOUSE ACTION CALLBACKS #####

    def ms_rotate(self, viewer, event, data_x, data_y, msg=True):
        """Rotate the image by dragging the cursor left or right.
        """
        if not self.canrotate:
            return False
        event.accept()
        msg = self.settings.get('msg_rotate', msg)

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._rotate_xy(viewer, x, y)

        elif event.state == 'down':
            if msg:
                self.onscreen_message("Rotate (drag around center)",
                                      delay=1.0)
            self._start_x, self._start_y = x, y
            self._start_rot = viewer.get_rotation()

        else:
            self.onscreen_message(None)

    def ms_rotate_reset(self, viewer, event, data_x, data_y, msg=True):
        if not self.canrotate:
            return False
        event.accept()
        msg = self.settings.get('msg_rotate', msg)

        if event.state == 'down':
            viewer.rotate(0.0)
            self.onscreen_message("Rotation reset", delay=0.5)

    ##### GESTURE ACTION CALLBACKS #####

    # NOTE: rotation is currently handled by default in the pinch
    # gesture handler in the "pan" mode.  This function is here
    # in case one wanted to make a binding to only rotate and not
    # zoom as well via pinch.  There is no default binding for it.
    #
    def pi_rotate(self, viewer, event, msg=True):
        if not self.canrotate:
            return False
        event.accept()
        if event.state == 'start':
            self._start_rot = viewer.get_rotation()
        else:
            msg_str = None
            deg = self._start_rot - event.rot_deg
            rotate_accel = self.settings.get('pinch_rotate_acceleration', 1.0)
            deg = rotate_accel * deg
            viewer.rotate(deg)
            if msg_str is None:
                msg_str = "Rotate: %.2f" % (deg)
                msg = self.settings.get('msg_rotate', msg)

            if msg and msg_str is not None:
                self.onscreen_message(msg_str, delay=0.4)
