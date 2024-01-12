# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``Toolbar`` provides a set of convenience UI controls for common operations
on viewers.

**Plugin Type: Global**

``Toolbar`` is a global plugin.  Only one instance can be opened.

**Usage**

Hovering over an icon on the toolbar should provide you with usage tool tip.

"""
import os.path

from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga.events import KeyEvent
from ginga import GingaPlugin

__all__ = ['Toolbar']


class Toolbar(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Toolbar, self).__init__(fv)

        # active view
        self.active = None
        # holds our gui widgets
        self.w = Bunch.Bunch()
        self.gui_up = False

        # get local plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Toolbar')
        self.settings.load(onError='silent')

        self.modetype = self.settings.get('mode_type', 'oneshot')

        fv.set_callback('add-channel', self.add_channel_cb)
        fv.set_callback('delete-channel', self.delete_channel_cb)
        fv.set_callback('channel-change', self.focus_cb)
        fv.add_callback('add-image-info', self._ch_image_added_cb)
        fv.add_callback('remove-image-info', self._ch_image_removed_cb)

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(0)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))
        self.orientation = orientation
        vbox.set_spacing(0)
        vbox.set_border_width(0)

        tb = Widgets.Toolbar(orientation=orientation)

        for tup in (
            #("Load", 'button', 'fits_open_48', "Open an image file",
            #None),
            ("FlipX", 'toggle', 'flip_x', "Flip image in X axis",
             self.flipx_cb),
            ("FlipY", 'toggle', 'flip_y', "Flip image in Y axis",
             self.flipy_cb),
            ("SwapXY", 'toggle', 'swap_xy', "Swap X and Y axes",
             self.swapxy_cb),
            ("---",),
            ("Rot90", 'button', 'rot90ccw', "Rotate image 90 deg",
             self.rot90_cb),
            ("RotN90", 'button', 'rot90cw', "Rotate image -90 deg",
             self.rotn90_cb),
            ("OrientRH", 'button', 'orient_nw', "Orient image N=Up E=Right",
             self.orient_rh_cb),
            ("OrientLH", 'button', 'orient_ne', "Orient image N=Up E=Left",
             self.orient_lh_cb),
            ("---",),
            ## ("Prev", 'button', 'prev', "Go to previous channel",
            ##  lambda w: self.fv.prev_channel()),
            ## ("Next", 'button', 'next', "Go to next channel",
            ##  lambda w: self.fv.next_channel()),
            ("Up", 'button', 'up', "Go to previous image in channel",
             lambda w: self.fv.prev_img()),
            ("Down", 'button', 'down', "Go to next image in channel",
             lambda w: self.fv.next_img()),
            ("---",),
            ("Zoom In", 'button', 'zoom_in', "Zoom in",
             lambda w: self.fv.zoom_in()),
            ("Zoom Out", 'button', 'zoom_out', "Zoom out",
             lambda w: self.fv.zoom_out()),
            ("Zoom Fit", 'button', 'zoom_fit', "Zoom to fit window size",
             lambda w: self.fv.zoom_fit()),
            ("Zoom 1:1", 'button', 'zoom_100', "Zoom to 100% (1:1)",
             lambda w: self.fv.zoom_1_to_1()),
            ("---",),
            ("Pan", 'toggle', 'pan', "Pan with left, zoom with right",
             lambda w, tf: self.mode_cb(tf, 'pan')),
            ("Zoom", 'toggle', 'crosshair',
             "Left/right click zooms in/out;\n"
             "hold middle to pan freely over image",
             lambda w, tf: self.mode_cb(tf, 'zoom')),
            ("Rotate", 'toggle', 'rotate',
             "Drag left to rotate; click right to reset to 0 deg",
             lambda w, tf: self.mode_cb(tf, 'rotate')),
            ("Dist", 'toggle', 'sqrt',
             "Scroll to set color distribution algorithm",
             lambda w, tf: self.mode_cb(tf, 'dist')),
            ("CMap", 'toggle', 'palette',
             "Scroll to set color map",
             lambda w, tf: self.mode_cb(tf, 'cmap')),
            ("Cuts", 'toggle', 'cuts',
             "Left/right sets hi cut, up/down sets lo cut",
             lambda w, tf: self.mode_cb(tf, 'cuts')),
            ("Contrast", 'toggle', 'contrast',
             "Contrast/bias with left/right/up/down",
             lambda w, tf: self.mode_cb(tf, 'contrast')),
            ("ModeLock", 'toggle', 'lock',
             "Modes are oneshot or locked", self.set_locked_cb),
            ("---",),
            ("Center", 'button', 'center_image', "Center image",
             self.center_image_cb),
            ("Restore", 'button', 'reset_rotation',
             "Reset all transformations and rotations",
             self.reset_all_transforms_cb),
            ("AutoLevels", 'button', 'auto_cuts', "Auto cut levels",
             self.auto_levels_cb),
            ("ResetContrast", 'button', 'reset_contrast', "Reset contrast",
             self.reset_contrast_cb),
            ("---",),
            ("Preferences", 'button', 'settings', "Set channel preferences (in focused channel)",
             lambda w: self.start_plugin_cb('Preferences')),
            ("FBrowser", 'button', 'folder_open', "Open file (in focused channel)",
             lambda w: self.start_plugin_cb('FBrowser')),
            ("MultiDim", 'button', 'layers', "Select HDUs or cube slices (in focused channel)",
             lambda w: self.start_plugin_cb('MultiDim')),
            ("Header", 'button', 'tags', "View image metadata (Header plugin)",
             lambda w: self.start_global_plugin_cb('Header')),
            ("ZoomPlugin", 'button', 'microscope', "Magnify detail (Zoom plugin)",
             lambda w: self.start_global_plugin_cb('Zoom')),
            ):  # noqa

            name = tup[0]
            if name == '---':
                tb.add_separator()
                continue
            if tup[1] not in ['button', 'toggle']:
                btn = Widgets.make_widget(name, tup[1])
                tb.add_widget(btn)
            else:
                iconpath = os.path.join(self.fv.iconpath, "%s.svg" % (tup[2]))
                btn = tb.add_action(None, toggle=(tup[1] == 'toggle'),
                                    iconpath=iconpath, iconsize=(24, 24))
            if tup[3]:
                btn.set_tooltip(tup[3])
            if tup[4]:
                btn.add_callback('activated', tup[4])

            # add to our widget dict
            self.w[Widgets.name_mangle(name, pfx='btn_')] = btn

            # add widget to toolbar
            #tb.add_widget(btn)

        hbox = Widgets.HBox()
        hbox.add_widget(tb, stretch=0)
        # stretcher
        hbox.add_widget(Widgets.Label(''), stretch=1)
        #sw.set_widget(tb)

        #top.add_widget(sw, stretch=1)

        container.add_widget(hbox, stretch=0)
        self.gui_up = True

    # CALLBACKS

    def add_channel_cb(self, viewer, channel):
        chviewer = channel.fitsimage
        chviewer.add_callback('transform', self.viewer_transform_cb)

        bm = chviewer.get_bindmap()
        bm.add_callback('mode-set', self.mode_set_cb, chviewer)

    def delete_channel_cb(self, viewer, channel):
        self.logger.debug("delete channel %s" % (channel.name))
        # we don't keep around any baggage on channels so nothing
        # to delete

    def focus_cb(self, viewer, channel):
        self.update_channel_buttons(channel)

        chviewer = channel.fitsimage
        self.active = chviewer
        self._update_toolbar_state(chviewer)
        return True

    def center_image_cb(self, w):
        view = self._get_viewer()
        view.center_image()
        return True

    def reset_contrast_cb(self, w):
        view, mode = self._get_mode('contrast')
        event = KeyEvent()
        mode.kp_contrast_restore(view, event, 'x', 0.0, 0.0)
        return True

    def auto_levels_cb(self, w):
        view = self._get_viewer()
        view.auto_levels()
        return True

    def rot90_cb(self, w):
        view = self._get_viewer()
        view.rotate_delta(90.0)
        return True

    def rotn90_cb(self, w):
        view = self._get_viewer()
        view.rotate_delta(-90.0)
        return True

    def orient_lh_cb(self, w):
        view, mode = self._get_mode('rotate')
        event = KeyEvent()
        mode.kp_orient_lh(view, event, 'x', 0.0, 0.0)
        return True

    def orient_rh_cb(self, w):
        view, mode = self._get_mode('rotate')
        event = KeyEvent()
        mode.kp_orient_rh(view, event, 'x', 0.0, 0.0)
        return True

    def reset_all_transforms_cb(self, w):
        view = self._get_viewer()
        with view.suppress_redraw:
            view.rotate(0.0)
            view.transform(False, False, False)

        return True

    def start_plugin_cb(self, name):
        self.fv.start_operation(name)
        return True

    def start_global_plugin_cb(self, name):
        self.fv.start_global_plugin(name, raise_tab=True)
        return True

    def flipx_cb(self, w, tf):
        view = self._get_viewer()
        flip_x, flip_y, swap_xy = view.get_transforms()
        flip_x = tf
        view.transform(flip_x, flip_y, swap_xy)
        return True

    def flipy_cb(self, w, tf):
        view = self._get_viewer()
        flip_x, flip_y, swap_xy = view.get_transforms()
        flip_y = tf
        view.transform(flip_x, flip_y, swap_xy)
        return True

    def swapxy_cb(self, w, tf):
        view = self._get_viewer()
        flip_x, flip_y, swap_xy = view.get_transforms()
        swap_xy = tf
        view.transform(flip_x, flip_y, swap_xy)
        return True

    def mode_cb(self, tf, modename):
        if self.active is None:
            self.active = self._get_viewer()
        chviewer = self.active
        if chviewer is None:
            return
        bm = chviewer.get_bindmap()
        if not tf:
            bm.reset_mode(chviewer)
            self.fv.show_status("")
            return True

        bm.set_mode(modename)
        # just in case mode change failed
        self._update_toolbar_state(chviewer)
        self.fv.show_status(f"Type 'h' in the viewer to show help for mode {modename}")
        return True

    def mode_set_cb(self, bm, mode, mtype, chviewer):
        # called whenever the user interaction mode is changed
        # in the viewer
        if self.active is None:
            self.active = self._get_viewer()
        if chviewer != self.active:
            return True
        self._update_toolbar_state(chviewer)
        return True

    def viewer_transform_cb(self, chviewer):
        # called whenever the transform (flip x/y, swap axes) is done
        # in the viewer
        if self.active is None:
            self.active = self._get_viewer()
        if chviewer != self.active:
            return True
        self._update_toolbar_state(chviewer)
        return True

    def new_image_cb(self, chviewer, image):
        self._update_toolbar_state(chviewer)
        return True

    def set_locked_cb(self, w, tf):
        if tf:
            modetype = 'locked'
        else:
            modetype = 'oneshot'
        if self.active is None:
            self.active = self._get_viewer()
        chviewer = self.active
        if chviewer is None:
            return

        # get current bindmap, make sure that the mode is consistent
        # with current lock button
        bm = chviewer.get_bindmap()
        modename, cur_modetype = bm.current_mode()
        bm.set_default_mode_type(modetype)

        bm.set_mode(modename, mode_type=modetype)
        if not tf:
            # turning off lock also resets the mode
            bm.reset_mode(chviewer)

        self._update_toolbar_state(chviewer)
        return True

    # LOGIC

    def _get_viewer(self):
        channel = self.fv.get_channel_info()
        return channel.fitsimage

    def _get_mode(self, mode_name):
        channel = self.fv.get_channel_info()
        view = channel.fitsimage
        bd = view.get_bindings()
        mode = bd.get_mode_obj(mode_name)
        return view, mode

    def _ch_image_added_cb(self, shell, channel, info):
        if channel != shell.get_current_channel():
            return
        self.update_channel_buttons(channel)

    def _ch_image_removed_cb(self, shell, channel, info):
        if channel != shell.get_current_channel():
            return
        self.update_channel_buttons(channel)

    def update_channel_buttons(self, channel):
        if not self.gui_up:
            return
        # Update toolbar channel buttons
        enabled = len(channel) > 1
        self.w.btn_up.set_enabled(enabled)
        self.w.btn_down.set_enabled(enabled)

    def _update_toolbar_state(self, chviewer):
        if (chviewer is None) or (not self.gui_up):
            return
        self.logger.debug("updating toolbar state")
        try:
            # update transform toggles
            flipx, flipy, swapxy = chviewer.get_transforms()
            # toolbar follows view
            self.w.btn_flipx.set_state(flipx)
            self.w.btn_flipy.set_state(flipy)
            self.w.btn_swapxy.set_state(swapxy)

            # update mode toggles
            bm = chviewer.get_bindmap()
            modename, mode_type = bm.current_mode()
            self.logger.debug("modename=%s" % (modename))
            # toolbar follows view
            self.w.btn_pan.set_state(modename == 'pan')
            self.w.btn_zoom.set_state(modename == 'zoom')
            self.w.btn_rotate.set_state(modename == 'rotate')
            self.w.btn_dist.set_state(modename == 'dist')
            self.w.btn_cuts.set_state(modename == 'cuts')
            self.w.btn_contrast.set_state(modename == 'contrast')
            self.w.btn_cmap.set_state(modename == 'cmap')

            default_mode_type = bm.get_default_mode_type()
            if 'btn_modelock' in self.w:
                is_locked = (default_mode_type in ('locked', 'softlock'))
                self.w.btn_modelock.set_state(is_locked)

        except Exception as e:
            self.logger.error("error updating toolbar: %s" % str(e))
            raise e

    def __str__(self):
        return 'toolbar'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Toolbar', package='ginga')

# END
