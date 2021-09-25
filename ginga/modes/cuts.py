#
# cuts.py -- mode for setting cuts levels
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

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
            ms_cut_auto=['cuts+right'],
            )

        self.cancut = True
        self._hival = 0.0
        self._loval = 0.0

    def __str__(self):
        return 'cuts'

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    #####  Help methods #####
    # Methods used by the callbacks to do actions.

    def _cycle_cuts_alg(self, viewer, msg, direction='down'):
        if self.cancut:
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
        image = viewer.get_image()
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
        image = viewer.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        loval = minval + (pct * spread)
        if msg:
            self.onscreen_message("Cut low: %.4f" % (loval))
        viewer.cut_levels(loval, hival)

    def _cuthigh_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_image()
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
        image = viewer.get_image()
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
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            viewer.cut_levels(0.0, 255.0, no_reset=True)
        return True

    def kp_cut_lo(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            _, hi = viewer.get_cut_levels()
            lo = viewer.get_data(data_x, data_y)
            viewer.cut_levels(lo, hi, no_reset=True)
        return True

    def kp_cut_hi(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            lo, _ = viewer.get_cut_levels()
            hi = viewer.get_data(data_x, data_y)
            viewer.cut_levels(lo, hi, no_reset=True)
        return True

    def kp_cut_minmax(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            image = viewer.get_image()
            mn, mx = image.get_minmax(noinf=True)
            viewer.cut_levels(mn, mx, no_reset=True)
        return True

    def kp_cut_auto(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            if msg:
                self.onscreen_message("Auto cut levels", delay=1.0)
            viewer.auto_levels()
        return True

    def kp_autocuts_toggle(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            val = viewer.get_settings().get('autocuts')
            if val == 'off':
                val = 'on'
            else:
                val = 'off'
            viewer.enable_autocuts(val)
            if msg:
                self.onscreen_message('Autocuts %s' % val, delay=1.0)
        return True

    def kp_autocuts_override(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            viewer.enable_autocuts('override')
            if msg:
                self.onscreen_message('Autocuts override', delay=1.0)
        return True

    def kp_autocuts_alg_prev(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_cuts_alg(viewer, msg, direction='up')
        return True

    def kp_autocuts_alg_next(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_cuts_alg(viewer, msg, direction='down')
        return True

    #####  SCROLL ACTION CALLBACKS #####

    def sc_cuts_coarse(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it coarsely.
        """
        if self.cancut:
            # adjust the cut by 10% on each end
            self._adjust_cuts(viewer, event.direction, 0.1, msg=msg)
        return True

    def sc_cuts_fine(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it finely.
        """
        if self.cancut:
            # adjust the cut by 1% on each end
            self._adjust_cuts(viewer, event.direction, 0.01, msg=msg)
        return True

    def sc_cuts_alg(self, viewer, event, msg=True):
        """Adjust cuts algorithm interactively.
        """
        if self.cancut:
            direction = self.get_direction(event.direction)
            self._cycle_cuts_alg(viewer, msg, direction=direction)
        return True

    #####  MOUSE ACTION CALLBACKS #####

    def ms_cutlo(self, viewer, event, data_x, data_y):
        """An interactive way to set the low cut level.
        """
        if not self.cancut:
            return True

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._cutlow_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = viewer.get_cut_levels()

        else:
            self.onscreen_message(None)
        return True

    def ms_cuthi(self, viewer, event, data_x, data_y):
        """An interactive way to set the high cut level.
        """
        if not self.cancut:
            return True

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._cuthigh_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = viewer.get_cut_levels()

        else:
            self.onscreen_message(None)
        return True

    def ms_cutall(self, viewer, event, data_x, data_y):
        """An interactive way to set the low AND high cut levels.
        """
        if not self.cancut:
            return True

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._cutboth_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            image = viewer.get_image()
            #self._loval, self._hival = viewer.get_cut_levels()
            self._loval, self._hival = viewer.autocuts.calc_cut_levels(image)

        else:
            self.onscreen_message(None)
        return True

    def ms_cut_auto(self, viewer, event, data_x, data_y, msg=True):
        return self.kp_cut_auto(viewer, event, data_x, data_y,
                                msg=msg)
