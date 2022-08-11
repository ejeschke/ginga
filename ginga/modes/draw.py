#
# draw.py -- mode for drawing on canvases
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Draw Mode enables bindings that can facilitate drawing.

Enter the mode by
-----------------
* Space, then "b"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* v : add a vertex to a polygon object, while drawing or editing a canvas
* z : delete a vertex from a polygon object, while drawing or editing a canvas
* x : delete a selected object while editing a canvas
* left drag : draw on the canvas in the defined shape
* right drag : draw on the canvas in the defined shape

"""
from ginga.modes.mode_base import Mode


class DrawMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_draw=['__b', None, None],

            # NOTE: these only here to generate events. The events are
            # handled by the DrawingCanvas mixin
            kp_poly_add=['v', 'draw+v'],
            kp_poly_del=['z', 'draw+z'],
            kp_edit_del=['draw+x'],

            ms_draw=['draw+left', 'win+left', 'right'])

        ## bm = viewer.get_bindmap()
        ## bm.add_mode('__b', str(self), mode_type='locked', msg=None)

        ## bd = viewer.get_bindings()
        ## bd.merge_actions(self.viewer, bm, self, actions.items())

    def __str__(self):
        return 'draw'

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)
