#
# cuts.py -- mode for setting cuts levels
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""Cuts Mode enables bindings that can adjust the low and high cut
levels of an image in a Ginga image viewer.

Enter the mode by
-----------------
* Space, then "s"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* l : set low cut level to the value of the pixel under the cursor
* h : set high cut level to the value of the pixel under the cursor
* S : set the the low and high cut levels to the min/max values in
  the image
* A : set the low and high cut levels to 0, 255;
  useful for standard RGB images, mostly
* a : perform an auto cut levels using the currently selected auto cuts
  algorithm and parameters
* b, up arrow : select the previous auto cuts algorithm in the list
* n, down arrow : select the next auto cuts algorithm in the list
* colon : toggle auto cuts for new images "on" or "off" in this viewer
* semicolon : set auto cuts for new images to "override" in this viewer
* scroll : adjust contrast by squeezing or stretching levels;
  one direction squeezes, the other stretches
* Ctrl + scroll : adjust micro contrast by squeezing or stretching levels;
  similar to scroll, but amount of stretch/squeeze is reduced
* Shift + scroll : change current auto cuts algorithm
* left drag : adjust levels by moving cursor;
  moving left/right adjusts high level, up/down adjusts low level
* Shift + left drag : adjust low level by moving cursor;
  moving left/right adjusts low level
* Ctrl + left drag : adjust high level by moving cursor;
  moving left/right adjusts high level
* right click : perform an auto levels (same as "a")

"""
from ginga.modes.mode_base import Mode


class CutsMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_cuts=['__s', None, None],

            kp_cut_255=['cuts+A'],
            kp_cut_lo=['cuts+l'],
            kp_cut_hi=['cuts+h'],
            kp_cut_minmax=['cuts+S'],
            kp_cut_auto=['a', 'cuts+a'],
            kp_autocuts_alg_prev=['cuts+up', 'cuts+b'],
            kp_autocuts_alg_next=['cuts+down', 'cuts+n'],
            kp_autocuts_toggle=[':', 'cuts+:'],
            kp_autocuts_override=[';', 'cuts+;'],

            sc_cuts_fine=['cuts+ctrl+scroll'],
            sc_cuts_coarse=['cuts+scroll'],
            sc_cuts_alg=['cuts+shift+scroll'],

            ms_cutlo=['cuts+shift+left'],
            ms_cuthi=['cuts+ctrl+left'],
            ms_cutall=['cuts+left'],
            ms_cut_auto=['cuts+right'])

        self._hival = 0.0
        self._loval = 0.0

    def __str__(self):
        return 'cuts'

    @property
    def cancut(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('cut')

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    #####  Help methods #####
    # Methods used by the callbacks to do actions.

    def _cycle_cuts_alg(self, viewer, msg, direction='down'):
        msg = self.settings.get('msg_autocuts_alg', msg)
        algs = viewer.get_autocut_methods()
        settings = viewer.get_settings()
        algname = settings.get('autocut_method', 'minmax')
        idx = algs.index(algname)
        if direction == 'down':
            idx = (idx + 1) % len(algs)
        else:
            idx = idx - 1
            if idx < 0:
                idx = len(algs) - 1
        algname = algs[idx]
        viewer.set_autocut_params(algname)
        if msg:
            self.onscreen_message("Autocuts alg: %s" % (algname),
                                  delay=1.0)

    def _adjust_cuts(self, viewer, direction, pct, msg=True):
        direction = self.get_direction(direction)
        if direction == 'up':
            self.cut_pct(viewer, pct, msg=msg)
        elif direction == 'down':
            self.cut_pct(viewer, -pct, msg=msg)

    def _cutlow_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_vip()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        loval = loval + (pct * spread)
        if msg:
            self.onscreen_message("Cut low: %.4f" % (loval))
        viewer.cut_levels(loval, hival)

    def _cutlow_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = viewer.get_window_size()
        pct = float(x) / float(win_wd)
        image = viewer.get_vip()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        loval = minval + (pct * spread)
        if msg:
            self.onscreen_message("Cut low: %.4f" % (loval))
        viewer.cut_levels(loval, hival)

    def _cuthigh_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_vip()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        hival = hival - (pct * spread)
        if msg:
            self.onscreen_message("Cut high: %.4f" % (hival))
        viewer.cut_levels(loval, hival)

    def _cuthigh_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = viewer.get_window_size()
        pct = 1.0 - (float(x) / float(win_wd))
        image = viewer.get_vip()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        hival = maxval - (pct * spread)
        if msg:
            self.onscreen_message("Cut high: %.4f" % (hival))
        viewer.cut_levels(loval, hival)

    def _cutboth_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = viewer.get_window_size()
        xpct = 1.0 - (float(x) / float(win_wd))
        #ypct = 1.0 - (float(y) / float(win_ht))
        ypct = (float(win_ht - y) / float(win_ht))
        spread = self._hival - self._loval
        hival = self._hival - (xpct * spread)
        loval = self._loval + (ypct * spread)
        if msg:
            self.onscreen_message("Cut low: %.4f  high: %.4f" % (
                loval, hival))
        viewer.cut_levels(loval, hival)

    def cut_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        loval, hival = viewer.get_cut_levels()
        spread = hival - loval
        loval = loval + (pct * spread)
        hival = hival - (pct * spread)
        if msg:
            self.onscreen_message("Cut low: %.4f  high: %.4f" % (
                loval, hival), delay=1.0)
        viewer.cut_levels(loval, hival)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_cut_255(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        msg = self.settings.get('msg_cuts', msg)
        viewer.cut_levels(0.0, 255.0, no_reset=True)

    def kp_cut_lo(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        msg = self.settings.get('msg_cuts', msg)
        _, hi = viewer.get_cut_levels()
        lo = viewer.get_data(data_x, data_y)
        viewer.cut_levels(lo, hi, no_reset=True)

    def kp_cut_hi(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        msg = self.settings.get('msg_cuts', msg)
        lo, _ = viewer.get_cut_levels()
        hi = viewer.get_data(data_x, data_y)
        viewer.cut_levels(lo, hi, no_reset=True)

    def kp_cut_minmax(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_vip()
        mn, mx = image.get_minmax(noinf=True)
        viewer.cut_levels(mn, mx, no_reset=True)

    def kp_cut_auto(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        msg = self.settings.get('msg_cuts', msg)
        if msg:
            self.onscreen_message("Auto cut levels", delay=1.0)
        viewer.auto_levels()

    def kp_autocuts_toggle(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        msg = self.settings.get('msg_cuts', msg)
        val = viewer.get_settings().get('autocuts')
        if val == 'off':
            val = 'on'
        else:
            val = 'off'
        viewer.enable_autocuts(val)
        if msg:
            self.onscreen_message('Autocuts %s' % val, delay=1.0)

    def kp_autocuts_override(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        msg = self.settings.get('msg_cuts', msg)
        viewer.enable_autocuts('override')
        if msg:
            self.onscreen_message('Autocuts override', delay=1.0)

    def kp_autocuts_alg_prev(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        self._cycle_cuts_alg(viewer, msg, direction='up')

    def kp_autocuts_alg_next(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancut:
            return False
        event.accept()
        self._cycle_cuts_alg(viewer, msg, direction='down')

    #####  SCROLL ACTION CALLBACKS #####

    def sc_cuts_coarse(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it coarsely.
        """
        if not self.cancut:
            return False
        event.accept()
        # adjust the cut by 10% on each end
        self._adjust_cuts(viewer, event.direction, 0.1, msg=msg)

    def sc_cuts_fine(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it finely.
        """
        if not self.cancut:
            return False
        event.accept()
        # adjust the cut by 1% on each end
        self._adjust_cuts(viewer, event.direction, 0.01, msg=msg)

    def sc_cuts_alg(self, viewer, event, msg=True):
        """Adjust cuts algorithm interactively.
        """
        if not self.cancut:
            return False
        event.accept()
        direction = self.get_direction(event.direction)
        self._cycle_cuts_alg(viewer, msg, direction=direction)

    #####  MOUSE ACTION CALLBACKS #####

    def ms_cutlo(self, viewer, event, data_x, data_y):
        """An interactive way to set the low cut level.
        """
        if not self.cancut:
            return False
        event.accept()

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._cutlow_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = viewer.get_cut_levels()

        else:
            self.onscreen_message(None)

    def ms_cuthi(self, viewer, event, data_x, data_y):
        """An interactive way to set the high cut level.
        """
        if not self.cancut:
            return False
        event.accept()

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._cuthigh_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = viewer.get_cut_levels()

        else:
            self.onscreen_message(None)

    def ms_cutall(self, viewer, event, data_x, data_y):
        """An interactive way to set the low AND high cut levels.
        """
        if not self.cancut:
            return False
        event.accept()

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._cutboth_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            image = viewer.get_vip()
            #self._loval, self._hival = viewer.get_cut_levels()
            self._loval, self._hival = viewer.autocuts.calc_cut_levels(image)

        else:
            self.onscreen_message(None)

    def ms_cut_auto(self, viewer, event, data_x, data_y, msg=True):
        self.kp_cut_auto(viewer, event, data_x, data_y, msg=msg)
