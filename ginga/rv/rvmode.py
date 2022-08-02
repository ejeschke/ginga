#
# rvmode.py -- special bindings for the reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.modes.mode_base import Mode


class RVMode(Mode):
    """Reference Viewer Mode enables bindings that are specific to use in
    the Ginga Reference image viewer, and not in standalone programs using
    the viewer widget.

    Default bindings in mode
    ------------------------
    Z : raise Zoom plugin (if activated)
    I : raise Info plugin (if activated)
    H : raise Header plugin (if activated)
    C : raise Contents plugin (if activated)
    D : raise Dialogs tab
    F : go borderless fullscreen
    f : toggle fullscreen
    m : toggle maximized
    < : toggle collapse left pane
    > : toggle collapse right pane
    up arrow : previous image in channel
    down arrow : next image in channel
    J : cycle workspace type
    k : add channel auto
    K : remove current channel
    f1 : show channel names
    left arrow : previous channel in workspace
    right arrow : next channel in workspace

    motion : show info under the cursor
    left click : focus this viewer/channel
    """
    # Needs to be set by reference viewer (via set_shell_ref) before any
    # channel viewers are created
    fv = None

    @classmethod
    def set_shell_ref(cls, fv):
        cls.fv = fv

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_rvmode=['__m', None, None],

            kp_raise_zoom=['Z'],
            kp_raise_info=['I'],
            kp_raise_header=['H'],
            kp_raise_contents=['C'],
            kp_raise_dialogs=['D'],

            kp_go_fullscreen=['F'],
            kp_toggle_fullscreen=['f'],
            kp_toggle_maximize=['m'],

            kp_collapse_pane_left=['<'],
            kp_collapse_pane_right=['>'],

            # channel and workspace
            kp_previous_image_in_channel=['up'],
            kp_next_image_in_channel=['down'],
            kp_cycle_workspace_type=['J'],
            kp_add_channel_auto=['k'],
            kp_remove_channel_auto=['K'],
            kp_show_channel_names=['f1'],
            kp_previous_channel_in_workspace=['left'],
            kp_next_channel_in_workspace=['n', 'right'],

            #ms_focus_viewer=['left'],
            ms_showxy=['nobtn'])

    def __str__(self):
        return 'rvmode'

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_raise_zoom(self, viewer, event, data_x, data_y, msg=True):
        self.fv.ds.raise_tab('Zoom')
        return True

    def kp_raise_info(self, viewer, event, data_x, data_y, msg=True):
        self.fv.ds.raise_tab('Info')
        return True

    def kp_raise_header(self, viewer, event, data_x, data_y, msg=True):
        self.fv.ds.raise_tab('Header')
        return True

    def kp_raise_contents(self, viewer, event, data_x, data_y, msg=True):
        self.fv.ds.raise_tab('Contents')
        return True

    def kp_raise_dialogs(self, viewer, event, data_x, data_y, msg=True):
        self.fv.ds.raise_tab('Dialogs')
        return True

    def kp_go_fullscreen(self, viewer, event, data_x, data_y, msg=True):
        self.fv.build_fullscreen()
        return True

    def kp_toggle_fullscreen(self, viewer, event, data_x, data_y, msg=True):
        self.fv.toggle_fullscreen()
        return True

    def kp_toggle_maximize(self, viewer, event, data_x, data_y, msg=True):
        self.fv.maximize()
        return True

    def kp_collapse_pane_left(self, viewer, event, data_x, data_y, msg=True):
        self.fv.collapse_pane('left')
        return True

    def kp_collapse_pane_right(self, viewer, event, data_x, data_y, msg=True):
        self.fv.collapse_pane('right')
        return True

    def kp_cycle_workspace_type(self, viewer, event, data_x, data_y, msg=True):
        self.fv.cycle_workspace_type()
        return True

    def kp_add_channel_auto(self, viewer, event, data_x, data_y, msg=True):
        self.fv.add_channel_auto()
        return True

    def kp_remove_channel_auto(self, viewer, event, data_x, data_y, msg=True):
        self.fv.remove_channel_auto()
        return True

    def kp_show_channel_names(self, viewer, event, data_x, data_y, msg=True):
        self.fv.show_channel_names()
        return True

    def kp_previous_image_in_channel(self, viewer, event, data_x, data_y,
                                     msg=True):
        self.fv.prev_img()
        return True

    def kp_next_image_in_channel(self, viewer, event, data_x, data_y, msg=True):
        self.fv.next_img()
        return True

    def kp_previous_channel_in_workspace(self, viewer, event, data_x, data_y,
                                         msg=True):
        self.fv.prev_channel()
        return True

    def kp_next_channel_in_workspace(self, viewer, event, data_x, data_y,
                                     msg=True):
        self.fv.next_channel()
        return True

    #####  SCROLL ACTION CALLBACKS #####

    #####  MOUSE ACTION CALLBACKS #####

    def ms_showxy(self, viewer, event, data_x, data_y, msg=True):
        """Motion event in the channel viewer window.  Show the pointing
        information under the cursor.
        """
        self.fv.showxy(viewer, data_x, data_y)
        return True

    # def ms_focus_viewer(self, viewer, event, data_x, data_y, msg=True):
    #     if event.state == 'down':
    #         chname = self.fv.get_channel_name(viewer)
    #         if chname is not None:
    #             self.fv.force_focus(chname)
    #     return True

    ##### GESTURE ACTION CALLBACKS #####
