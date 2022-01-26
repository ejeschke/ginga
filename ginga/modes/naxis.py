#
# naxis.py -- mode for navigating data cubes
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.modes.mode_base import Mode


class NaxisMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_naxis=['__n', None, None],

            sc_naxis=['naxis+scroll'],

            ms_naxis=['naxis+left'],

            pa_naxis=['naxis+pan'])

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
            return
        _axis = len(image.axisdim) - axis
        if _axis < 0:
            # attempting to access a non-existant axis
            return

        axis_lim = image.axisdim[_axis]
        naxispath = list(image.naxispath)
        m = axis - 3

        idx = naxispath[m]
        if direction == 'down':
            idx = (idx + 1) % axis_lim
        else:
            idx = idx - 1
            if idx < 0:
                idx = axis_lim - 1

        naxispath[m] = idx
        image.set_naxispath(naxispath)
        if msg:
            self.onscreen_message("slice: %d" % (idx),
                                  delay=1.0)

    #####  KEYBOARD ACTION CALLBACKS #####

    #####  SCROLL ACTION CALLBACKS #####

    def sc_naxis(self, viewer, event, msg=True):
        """Interactively change the slice of the image in a data cube
        by scrolling.
        """
        # TODO: be able to pick axis
        axis = 3
        direction = self.get_direction(event.direction)

        return self._nav_naxis(viewer, axis, direction, msg=msg)

    #####  MOUSE ACTION CALLBACKS #####

    def ms_naxis(self, viewer, event, data_x, data_y, msg=True):

        # which axis (in FITS NAXIS terminology)
        # TODO: be able to pick axis
        axis = 3
        x, y = self.get_win_xy(viewer)

        image = viewer.get_image()
        if image is None:
            return

        _axis = len(image.axisdim) - axis
        if _axis < 0:
            # attempting to access a non-existant axis
            return

        axis_lim = image.axisdim[_axis]
        naxispath = list(image.naxispath)
        m = axis - 3

        if event.state in ('down', 'move'):
            win_wd, win_ht = viewer.get_window_size()
            x_pct = min(max(0.0, x / float(win_wd)), 1.0)
            idx = int(x_pct * axis_lim - 1)
            naxispath[m] = idx
            image.set_naxispath(naxispath)
            if msg:
                self.onscreen_message("slice: %d" % (idx),
                                      delay=1.0)

        return True

    ##### GESTURE ACTION CALLBACKS #####

    def pa_naxis(self, viewer, event, msg=True):
        """Interactively change the slice of the image in a data cube
        by pan gesture.
        """
        event = self._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False

        # TODO: be able to pick axis
        axis = 3
        direction = self.get_direction(event.direction)

        return self._nav_naxis(viewer, axis, direction, msg=msg)
