#
# dist.py -- mode for controlling color distribution
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Dist Mode enables bindings that can adjust the color distribution
of an image in a Ginga image viewer.

These algorithms are similar to "curves" type profiles: "linear",
"log", "power", "sqrt", "squared", "asinh", "sinh", "histeq"

Enter the mode by
-----------------
* Space, then "d"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* D : reset the color distribution algorithm to "linear"
* b, up arrow : select the previous distribution algorithm in the list
* n, down arrow : select the next distribution algorithm in the list
* scroll : select the color distribution algorithm by scrolling

"""
from ginga.modes.mode_base import Mode


class DistMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_dist=['__d', None, None],

            kp_dist_reset=['D', 'dist+d', 'dist+D'],
            kp_dist_prev=['dist+up', 'dist+b'],
            kp_dist_next=['dist+down', 'dist+n'],

            sc_dist=['dist+scroll'])

    def __str__(self):
        return 'dist'

    @property
    def cancmap(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('cmap')

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def _cycle_dist(self, viewer, msg, direction='down'):
        msg = self.settings.get('msg_dist', msg)
        rgbmap = viewer.get_rgbmap()
        algs = rgbmap.get_hash_algorithms()
        algname = rgbmap.get_hash_algorithm()
        idx = algs.index(algname)
        if direction == 'down':
            idx = (idx + 1) % len(algs)
        else:
            idx = idx - 1
            if idx < 0:
                idx = len(algs) - 1
        algname = algs[idx]
        rgbmap.set_hash_algorithm(algname)
        if msg:
            self.onscreen_message("Color dist: %s" % (algname),
                                  delay=1.0)

    def _reset_dist(self, viewer, msg):
        msg = self.settings.get('msg_dist', msg)
        rgbmap = viewer.get_rgbmap()
        algname = 'linear'
        rgbmap.set_hash_algorithm(algname)
        if msg:
            self.onscreen_message("Color dist: %s" % (algname),
                                  delay=1.0)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_dist(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._cycle_dist(viewer, msg)

    def kp_dist_reset(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._reset_dist(viewer, msg)

    def kp_dist_prev(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._cycle_dist(viewer, msg, direction='up')

    def kp_dist_next(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._cycle_dist(viewer, msg, direction='down')

    #####  SCROLL ACTION CALLBACKS #####

    def sc_dist(self, viewer, event, msg=True):
        """Interactively change the color distribution algorithm
        by scrolling.
        """
        if not self.cancmap:
            return False
        event.accept()
        direction = self.get_direction(event.direction)
        self._cycle_dist(viewer, msg, direction=direction)

    #####  MOUSE ACTION CALLBACKS #####
