#
# naxis.py -- mode for navigating data cubes
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Naxis Mode enables bindings that can move through the slices in an
image stack in a Ginga image viewer.

Enter the mode by
-----------------
* Space, then "n"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* scroll : select previous or next slice of current axis
* Ctrl + scroll : select previous or next axis as current axis
* left drag : select slice as a function of percentage of cursor/window width
* up/down arrow : select previous or next axis as current axis

"""
from ginga.modes.mode_base import Mode


class NaxisMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_naxis=['__n', None, None],

            kp_naxis_up=['naxis+up', 'naxis+b'],
            kp_naxis_dn=['naxis+down', 'naxis+n'],
            sc_naxis_slice=['naxis+scroll'],
            sc_naxis_axis=['naxis+ctrl+scroll'],
            ms_naxis=['naxis+left'],
            pa_naxis=['naxis+pan'])

        # the axis being examined
        self.axis = 3

    def __str__(self):
        return 'naxis'

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def _nav_naxis(self, viewer, axis, direction, msg=True):
        """Interactively change the slice of the image in a data cube
        by scrolling.
        """
        image = viewer.get_image()
        if image is None:
            self.onscreen_message("No image", delay=1.0)
            return
        if axis < 3 or axis > len(image.axisdim):
            # attempting to access a non-existent axis
            self.onscreen_message("Bad axis: %d" % (self.axis), delay=1.0)
            return
        _axis = len(image.axisdim) - axis

        axis_lim = image.axisdim[_axis]
        naxispath = list(image.naxispath)
        m = axis - 3

        idx = naxispath[m]
        if direction == 'down':
            idx = (idx + 1) % axis_lim
        elif direction == 'up':
            idx = idx - 1
            if idx < 0:
                idx = axis_lim - 1
        else:
            # no change, except possibly axis
            pass

        naxispath[m] = idx
        image.set_naxispath(naxispath)
        if msg:
            self.onscreen_message("axis: %d  slice: %d" % (axis, idx),
                                  delay=1.0)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_naxis_up(self, viewer, event, data_x, data_y, msg=True):
        event.accept()
        self.axis += 1
        self._nav_naxis(viewer, self.axis, 'same', msg=msg)

    def kp_naxis_dn(self, viewer, event, data_x, data_y, msg=True):
        event.accept()
        self.axis -= 1
        self._nav_naxis(viewer, self.axis, 'same', msg=msg)

    #####  SCROLL ACTION CALLBACKS #####

    def sc_naxis_slice(self, viewer, event, msg=True):
        """Interactively change the slice of the image in a data cube
        by scrolling.
        """
        event.accept()
        direction = self.get_direction(event.direction)

        self._nav_naxis(viewer, self.axis, direction, msg=msg)

    def sc_naxis_axis(self, viewer, event, msg=True):
        """Interactively change the slice of the image in a data cube
        by scrolling.
        """
        event.accept()
        direction = self.get_direction(event.direction)
        if direction == 'up':
            self.axis += 1
        elif direction == 'down':
            self.axis -= 1

        self._nav_naxis(viewer, self.axis, 'same', msg=msg)

    #####  MOUSE ACTION CALLBACKS #####

    def ms_naxis(self, viewer, event, data_x, data_y, msg=True):

        event.accept()
        x, y = self.get_win_xy(viewer)

        image = viewer.get_image()
        if image is None:
            self.onscreen_message("No image", delay=1.0)
            return

        # which axis (in FITS NAXIS terminology)
        if self.axis < 3 or self.axis > len(image.axisdim):
            # attempting to access a non-existant axis
            self.onscreen_message("Bad axis: %d" % (self.axis), delay=1.0)
            return

        _axis = len(image.axisdim) - self.axis
        axis_lim = image.axisdim[_axis]
        naxispath = list(image.naxispath)
        m = self.axis - 3

        if event.state in ('down', 'move'):
            win_wd, win_ht = viewer.get_window_size()
            x_pct = min(max(0.0, x / float(win_wd)), 1.0)
            idx = int(x_pct * axis_lim - 1)
            naxispath[m] = idx
            image.set_naxispath(naxispath)
            if msg:
                self.onscreen_message("axis: %d  slice: %d" % (self.axis, idx),
                                      delay=1.0)

    ##### GESTURE ACTION CALLBACKS #####

    def pa_naxis(self, viewer, event, msg=True):
        """Interactively change the slice of the image in a data cube
        by pan gesture.
        """
        event.accept()
        event = self._pa_synth_scroll_event(event)
        if event.state != 'move':
            return

        # TODO: be able to pick axis
        direction = self.get_direction(event.direction)

        self._nav_naxis(viewer, self.axis, direction, msg=msg)
