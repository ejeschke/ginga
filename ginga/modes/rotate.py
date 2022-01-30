#
# rotate.py -- mode for rotating images
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math

from ginga import trcalc
from ginga.util import wcs
from ginga.modes.mode_base import Mode


class RotateMode(Mode):
    """Rotate Mode enables bindings that can flip or swap the axes of an
    image, or rotate it, in a Ginga image viewer.

    Default bindings in mode
    ------------------------
    '[', '{' : flip the image in the X axis

    ']', '}' : flip the image in the Y axis

    backslash, '|' : swap the X and Y axes

    R : reset rotation to 0 deg
        Does not reset any flips or swaps

    t : resets any flips or swaps

    '.' : rotate image incrementally by +90 deg

    ',' : rotate image by incrementally -90 deg

    'o' : orient the image so that North points up and East points left

    'O' : orient the image so that North points up and East points right

    left drag : rotate the image interactively

    right click : reset the rotation to 0 deg (same as R)

    """

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
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = viewer.get_transforms()
            if event.key == '[':
                flipx = not flipX
            else:
                flipx = False
            viewer.transform(flipx, flipY, swapXY)
            if msg:
                self.onscreen_message("Flip X=%s" % flipx, delay=1.0)
        return True

    def kp_flip_y(self, viewer, event, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = viewer.get_transforms()
            if event.key == ']':
                flipy = not flipY
            else:
                flipy = False
            viewer.transform(flipX, flipy, swapXY)
            if msg:
                self.onscreen_message("Flip Y=%s" % flipy, delay=1.0)
        return True

    def kp_swap_xy(self, viewer, event, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = viewer.get_transforms()
            if event.key == 'backslash':
                swapxy = not swapXY
            else:
                swapxy = False
            viewer.transform(flipX, flipY, swapxy)
            if msg:
                self.onscreen_message("Swap XY=%s" % swapxy, delay=1.0)
        return True

    def kp_transform_reset(self, viewer, event, data_x, data_y):
        if self.canflip:
            viewer.transform(False, False, False)
            self.onscreen_message("Flips/swaps reset", delay=0.5)
        return True

    def kp_rotate_reset(self, viewer, event, data_x, data_y):
        if self.canrotate:
            viewer.rotate(0.0)
        return True

    def kp_rotate_inc90(self, viewer, event, data_x, data_y, msg=True):
        if self.canrotate:
            self._rotate_inc(viewer, 90.0, msg=msg)
        return True

    def kp_rotate_dec90(self, viewer, event, data_x, data_y, msg=True):
        if self.canrotate:
            self._rotate_inc(viewer, -90.0, msg=msg)
        return True

    def kp_orient_lh(self, viewer, event, data_x, data_y, msg=True):
        if self.canrotate:
            self._orient(viewer, righthand=False, msg=msg)
        return True

    def kp_orient_rh(self, viewer, event, data_x, data_y,
                     msg=True):
        if self.canrotate:
            self._orient(viewer, righthand=True, msg=msg)
        return True

    #####  SCROLL ACTION CALLBACKS #####

    #####  MOUSE ACTION CALLBACKS #####

    def ms_rotate(self, viewer, event, data_x, data_y, msg=True):
        """Rotate the image by dragging the cursor left or right.
        """
        if not self.canrotate:
            return True
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
        return True

    def ms_rotate_reset(self, viewer, event, data_x, data_y, msg=True):
        if not self.canrotate:
            return True
        msg = self.settings.get('msg_rotate', msg)

        if event.state == 'down':
            viewer.rotate(0.0)
            self.onscreen_message("Rotation reset", delay=0.5)
        return True

    ##### GESTURE ACTION CALLBACKS #####

    def gs_rotate(self, viewer, state, rot_deg, msg=True):
        if state == 'start':
            self._start_rot = viewer.get_rotation()
        else:
            msg_str = None
            if self.canrotate:
                deg = self._start_rot - rot_deg
                rotate_accel = self.settings.get('pinch_rotate_acceleration', 1.0)
                deg = rotate_accel * deg
                viewer.rotate(deg)
                if msg_str is None:
                    msg_str = "Rotate: %.2f" % (deg)
                    msg = self.settings.get('msg_rotate', msg)

            if msg and (msg_str is not None):
                self.onscreen_message(msg_str, delay=0.4)
        return True
