#
# contrast.py -- mode for setting contrast
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.modes.mode_base import Mode


class ContrastMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_contrast=['__t', None, None],

            kp_contrast_restore=['T', 'contrast+t', 'contrast+T'],

            ms_contrast=['contrast+left', 'ctrl+right'],
            ms_contrast_restore=['contrast+right', 'ctrl+middle'],
            )

        self.cancmap = True

    def __str__(self):
        return 'contrast'

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def restore_contrast(self, viewer, msg=True):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = viewer.get_rgbmap()
        rgbmap.reset_sarr()
        if msg:
            self.onscreen_message("Restored contrast", delay=0.5)
        return True

    def _tweak_colormap(self, viewer, x, y, mode):
        win_wd, win_ht = viewer.get_window_size()

        # translate Y cursor position as a percentage of the window
        # height into a scaling factor
        y_pct = (win_ht - y) / float(win_ht)

        # I tried to mimic ds9's exponential scale feel along the Y-axis
        def exp_scale(i):
            return (1.0 / (i**3)) * 0.0002 + (1.0 / i) * 0.085

        scale_pct = exp_scale(1.0 - y_pct)

        # translate X cursor position as a percentage of the window
        # width into a shifting factor
        shift_pct = x / float(win_wd) - 0.5

        viewer.scale_and_shift_cmap(scale_pct, shift_pct)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            self.restore_contrast(viewer, msg=msg)
        return True

    #####  SCROLL ACTION CALLBACKS #####

    #####  MOUSE ACTION CALLBACKS #####

    def ms_contrast(self, viewer, event, data_x, data_y, msg=True):
        """Shift the colormap by dragging the cursor left or right.
        Stretch the colormap by dragging the cursor up or down.
        """
        if not self.cancmap:
            return True
        msg = self.settings.get('msg_contrast', msg)

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._tweak_colormap(viewer, x, y, 'preview')

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            if msg:
                self.onscreen_message(
                    "Shift and stretch colormap (drag mouse)", delay=1.0)
        else:
            self.onscreen_message(None)
        return True

    def ms_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        """An interactive way to restore the colormap contrast settings after
        a warp operation.
        """
        if self.cancmap and (event.state == 'down'):
            self.restore_contrast(viewer, msg=msg)
        return True
