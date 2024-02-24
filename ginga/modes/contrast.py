#
# contrast.py -- mode for setting contrast
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Contrast Mode enables bindings that can adjust the contrast of
an image in a Ginga image viewer.

Enter the mode by
-----------------
* Space, then "t"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* T : restore contrast to defaults
* left drag : adjust contrast
  * Interactive shift/stretch colormap (aka contrast and bias).
  * Moving left/right controls shift, up/down controls stretch.
  * Release button when satisfied with the contrast.
* right click : restore contrast to defaults
* scroll wheel : change contrast (add Ctrl to change more finely)
* Shift + scroll wheel : change brightness (add Ctrl to change more finely)
* Ctrl + pan gesture : change contrast
* Shift + pan gesture : change brightness

"""
import numpy as np

from ginga.modes.mode_base import Mode


class ContrastMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_contrast=['__t', None, None],

            kp_contrast_restore=['T', 'contrast+t', 'contrast+T'],

            sc_contrast=['contrast+scroll', 'contrast+*+scroll'],

            ms_contrast=['contrast+left', 'ctrl+right'],
            ms_contrast_restore=['contrast+right', 'ctrl+middle'],

            pa_contrast=['contrast+ctrl+pan', 'contrast+shift+pan'])

    def __str__(self):
        return 'contrast'

    @property
    def cancmap(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('cmap')

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def restore_contrast(self, viewer, msg=True):
        viewer.get_settings().set(contrast=0.5, brightness=0.5)
        msg = self.settings.get('msg_cmap', msg)
        if msg:
            self.onscreen_message("Restored brightness and contrast",
                                  delay=0.5)
        return True

    def _tweak_colormap(self, viewer, x, y, mode):
        win_wd, win_ht = viewer.get_window_size()

        # translate Y cursor position as a percentage of the window
        # height into a contrast pct
        contrast_pct = np.clip(y, 0, win_ht) / float(win_ht)

        # translate X cursor position as a percentage of the window
        # width into a brightness pct
        brightness_pct = 1.0 - np.clip(x, 0, win_wd) / float(win_wd)

        with viewer.suppress_redraw:
            viewer.get_settings().set(contrast=contrast_pct,
                                      brightness=brightness_pct)

    def _change_contrast(self, viewer, msg, change_pct):
        msg = self.settings.get('msg_contrast', msg)
        pct = viewer.get_settings().get('contrast')
        change_factor = 1.0 + change_pct
        pct = min(1.0, max(0.0, pct * change_factor))
        viewer.get_settings().set(contrast=pct)
        if msg:
            self.onscreen_message("Contrast: %.2f%%" % (pct * 100),
                                  delay=1.0)

    def _change_brightness(self, viewer, msg, change_pct):
        msg = self.settings.get('msg_contrast', msg)
        pct = viewer.get_settings().get('brightness')
        change_factor = 1.0 + change_pct
        pct = min(1.0, max(0.0, pct * change_factor))
        viewer.get_settings().set(brightness=pct)
        if msg:
            self.onscreen_message("Brightness: %.2f%%" % (pct * 100),
                                  delay=1.0)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        msg = self.settings.get('msg_cmap', msg)
        self.restore_contrast(viewer, msg=msg)

    #####  SCROLL ACTION CALLBACKS #####

    def sc_contrast(self, viewer, event, msg=True):
        """Interactively change the contrast or brightness by scrolling.
        """
        if not self.cancmap:
            return False
        event.accept()
        rev = self.settings.get('zoom_scroll_reverse', False)
        direction = self.get_direction(event.direction, rev=rev)
        change_pct = 0.05
        if 'ctrl' in event.modifiers:
            change_pct = 0.01
        if direction == 'down':
            change_pct = - change_pct
        if 'shift' in event.modifiers:
            self._change_brightness(viewer, msg, change_pct)
        else:
            self._change_contrast(viewer, msg, change_pct)

    #####  MOUSE ACTION CALLBACKS #####

    def ms_contrast(self, viewer, event, data_x, data_y, msg=True):
        """Shift the colormap by dragging the cursor left or right.
        Stretch the colormap by dragging the cursor up or down.
        """
        if not self.cancmap:
            return False
        event.accept()
        msg = self.settings.get('msg_contrast', msg)

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._tweak_colormap(viewer, x, y, 'preview')

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            if msg:
                self.onscreen_message(
                    "Change contrast and brightness (drag mouse)", delay=1.0)
        else:
            self.onscreen_message(None)

    def ms_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        """An interactive way to restore the colormap contrast settings after
        a warp operation.
        """
        if not self.cancmap:
            return False
        event.accept()
        if event.state == 'down':
            self.restore_contrast(viewer, msg=msg)

    ##### GESTURE ACTION CALLBACKS #####

    def pa_contrast(self, viewer, event, msg=True):
        """Change the contrast or brightness by a pan gesture.
        (the back end must support gestures)
        """
        if not self.cancmap:
            return False
        event.accept()
        event = self._pa_synth_scroll_event(event)
        if event.state == 'move':
            rev = self.settings.get('zoom_scroll_reverse', False)
            direction = self.get_direction(event.direction, rev=rev)
            change_pct = 0.01
            if direction == 'down':
                change_pct = - change_pct
            if 'shift' in event.modifiers:
                self._change_brightness(viewer, msg, change_pct)
                return True
            elif 'ctrl' in event.modifiers:
                self._change_contrast(viewer, msg, change_pct)
                return True

        return False
