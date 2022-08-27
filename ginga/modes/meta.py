#
# meta.py -- special mode for launching other modes
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Meta Mode.

Enter the mode by
-----------------
* Space

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* escape : exit any mode
* L : toggle mode lock/oneshot
* S : save image profile

"""
from ginga.modes.mode_base import Mode


class MetaMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            # Mode 'meta' is special: it is an intermediate mode that
            # is used primarily to launch other modes
            dmod_meta=['space', None, None],

            # KEYBOARD
            kp_save_profile=['S'],
            kp_reset=['escape'],
            kp_lock=['L', 'meta+L'],

            # MOUSE/BUTTON
            ms_none=['nobtn'],
            ms_cursor=['left'],
            ms_wheel=[])

    def __str__(self):
        return 'meta'

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def kp_reset(self, viewer, event, data_x, data_y):
        event.accept()
        bm = viewer.get_bindmap()
        bm.reset_mode(viewer)
        viewer.onscreen_message(None)
        return True

    def _toggle_lock(self, viewer, mode_type):
        bm = viewer.get_bindmap()
        # toggle default mode type to locked/oneshot
        dfl_modetype = bm.get_default_mode_type()
        # get current mode
        mode_name, cur_modetype = bm.current_mode()

        if dfl_modetype in ['locked']:
            if mode_type == dfl_modetype:
                mode_type = 'oneshot'

        # install the lock type
        bm.set_default_mode_type(mode_type)
        bm.set_mode(mode_name, mode_type=mode_type)

    def kp_lock(self, viewer, event, data_x, data_y):
        event.accept()
        self._toggle_lock(viewer, 'locked')

    def kp_save_profile(self, viewer, event, data_x, data_y, msg=True):
        event.accept()
        viewer.checkpoint_profile()
        if msg:
            viewer.onscreen_message("Profile saved", delay=0.5)
