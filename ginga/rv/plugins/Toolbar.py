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
from ginga.toolkit import family
from ginga.misc import Bunch
from ginga.events import KeyEvent
from ginga import GingaPlugin
from ginga.util import viewer as gviewer

__all__ = ['Toolbar', 'Toolbar_Common', 'Toolbar_Ginga_Image',
           'Toolbar_Ginga_Plot', 'Toolbar_Ginga_Table']


class Toolbar(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super().__init__(fv)

        # active view
        self.channel = None
        self.opname_prefix = 'Toolbar_'

        # get local plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Toolbar')
        self.settings.add_defaults(close_unfocused_toolbars=True)
        self.settings.load(onError='silent')

        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('channel-change', self.focus_cb)
        fv.add_callback('viewer-select', self.viewer_select_cb)

    def build_gui(self, container):
        self.w.nb = Widgets.StackWidget()

        container.add_widget(self.w.nb, stretch=1)

    # CALLBACKS

    def add_channel_cb(self, fv, channel):
        if self.channel is None:
            self.focus_cb(fv, channel)

    def delete_channel_cb(self, fv, channel):
        self.logger.debug("delete channel %s" % (channel.name))
        if channel is self.channel:
            self.channel = None

    def focus_cb(self, fv, channel):
        self.logger.debug("{} focused".format(channel.name))
        if channel is not self.channel:
            old_channel, self.channel = self.channel, channel

            if self.channel is not None:
                opname = self.get_opname(self.channel)
                self.logger.debug(f"starting {opname} in {channel}")
                self.start_local_plugin(self.channel, opname)

            # NOTE: can stop toolbar plugins that aren't focused
            # but it is more efficient to keep them open
            if self.settings.get('close_unfocused_toolbars', False):
                if old_channel is not None:
                    opname = self.get_opname(old_channel)
                    self.logger.debug(f"stopping {opname} in {old_channel}")
                    self.stop_local_plugin(old_channel, opname)

        return True

    def viewer_select_cb(self, fv, channel, old_viewer, new_viewer):
        self.logger.debug("viewer changed: {}".format(new_viewer.name))
        if channel is self.channel and channel is not None:
            #opname = self.get_opname(self.channel)
            opname = self.opname_prefix + new_viewer.vname.replace(' ', '_')
            self.start_local_plugin(self.channel, opname)

            if old_viewer is not None and old_viewer is not new_viewer:
                opname = self.opname_prefix + old_viewer.vname.replace(' ', '_')
                self.stop_local_plugin(self.channel, opname)

    def redo(self, channel, dataobj):
        # NOTE: we need to call redo() specifically for our toolbars
        # because they are not started nor managed like regular local
        # plugins by the core, they are managed by us
        opname = self.get_opname(channel)
        opmon = channel.opmon
        p_obj = opmon.get_plugin(opname)
        try:
            p_obj.redo()
        except Exception as e:
            self.logger.error(f"error updating toolbar {opmon}: {e}")

    # LOGIC

    def get_opname(self, channel):
        opname = self.opname_prefix + channel.viewer.vname.replace(' ', '_')
        return opname

    def start_local_plugin(self, channel, opname, future=None):
        wname = "{}_{}".format(channel.name, opname)
        if wname in self.w and self.w[wname] is not None:
            vbox = self.w[wname]
            idx = self.w.nb.index_of(vbox)
            self.logger.debug(f"raising {wname}")
            self.w.nb.set_index(idx)
            return
        opmon = channel.opmon
        p_obj = opmon.get_plugin(opname)
        vbox = Widgets.VBox()
        p_obj.build_gui(vbox)
        self.w.nb.add_widget(vbox)
        self.w[wname] = vbox
        p_obj.start()

    def stop_local_plugin(self, channel, opname):
        opmon = channel.opmon
        p_obj = opmon.get_plugin(opname)
        try:
            p_obj.stop()
        except Exception as e:
            pass
        wname = "{}_{}".format(channel.name, opname)
        try:
            vbox = self.w[wname]
            self.w.nb.remove(vbox)
            self.w[wname] = None
            vbox.delete()
        except Exception as e:
            self.logger.error(f"error stopping plugin '{wname}'")

    def __str__(self):
        return 'toolbar'


class Toolbar_Common(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super().__init__(fv, fitsimage)

        # holds our gui widgets
        self.w = Bunch.Bunch()
        self.viewers = []
        self.layout_common = [
            # (Name, type, icon, tooltip)
            ("viewer", 'combobox', None, "Select compatible viewer",
             self.viewer_cb),
            ("Up", 'button', 'up', "Go to previous image in channel",
             lambda w: self.fv.prev_img()),
            ("Down", 'button', 'down', "Go to next image in channel",
             lambda w: self.fv.next_img()),
            ("---",)]

        self.gui_up = False

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))

    def stop(self):
        self.viewers = []
        self.gui_up = False

    def start_local_plugin(self, name):
        self.fv.start_operation(name)

    def start_global_plugin(self, name):
        self.fv.start_global_plugin(name, raise_tab=True)

    def build_toolbar(self, tb_w, layout):

        for tup in layout:
            name = tup[0]
            if name == '---':
                tb_w.add_separator()
                continue
            if tup[1] not in ['button', 'toggle']:
                btn = Widgets.make_widget(name, tup[1])
                tb_w.add_widget(btn)
            else:
                iconpath = tup[2]
                if not iconpath.startswith(os.path.sep):
                    iconpath = os.path.join(self.fv.iconpath, "%s.svg" % (iconpath))
                btn = tb_w.add_action(None, toggle=(tup[1] == 'toggle'),
                                      iconpath=iconpath, iconsize=(24, 24))
            if tup[3]:
                btn.set_tooltip(tup[3])
            if tup[4]:
                btn.add_callback('activated', tup[4])

            # add to our widget dict
            self.w[Widgets.name_mangle(name, pfx='btn_')] = btn

        return tb_w

    def viewer_cb(self, w, idx):
        vinfo = self.viewers[idx]
        self.logger.debug(f"viewer {vinfo.name} selected")
        dataobj = self.channel.viewer.get_dataobj()
        self.channel.open_with_viewer(vinfo, dataobj)

    def _update_viewer_selection(self):
        if not self.gui_up:
            return

        dataobj = self.channel.get_current_image()

        # find available viewers that can view this kind of object
        viewers = gviewer.get_viewers(dataobj)
        if viewers != self.viewers:
            # repopulate viewer selector
            self.viewers = viewers
            new_names = [viewer.name for viewer in viewers]
            self.w.btn_viewer.clear()
            self.logger.debug("available viewers for {} are {}".format(type(dataobj), new_names))
            for name in new_names:
                self.w.btn_viewer.append_text(name)
            # set the box to the viewer we have selected
            cur_name = self.channel.viewer.vname
            if cur_name in new_names:
                self.w.btn_viewer.set_text(cur_name)

    def __str__(self):
        return 'toolbarbase'


class Toolbar_Ginga_Image(Toolbar_Common):
    """A toolbar for the Ginga Image viewer.
    """

    def __init__(self, fv, chviewer):
        # superclass defines some variables for us, like logger
        super().__init__(fv, chviewer)

        # get local plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('toolbar_Ginga_Image')
        self.settings.load(onError='silent')

        self.modetype = self.settings.get('mode_type', 'oneshot')

        chviewer.add_callback('transform', self.viewer_transform_cb)

        bm = chviewer.get_bindmap()
        bm.add_callback('mode-set', self.mode_set_cb)

        self.layout = [
            # (Name, type, icon, tooltip)
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
             lambda w: self.start_local_plugin('Preferences')),
            ("FBrowser", 'button', 'folder_open', "Open file (in focused channel)",
             lambda w: self.start_local_plugin('FBrowser')),
            ("MultiDim", 'button', 'layers', "Select HDUs or cube slices (in focused channel)",
             lambda w: self.start_local_plugin('MultiDim')),
            ("Header", 'button', 'tags', "View image metadata (Header plugin)",
             lambda w: self.start_global_plugin('Header')),
            ("ZoomPlugin", 'button', 'microscope', "Magnify detail (Zoom plugin)",
             lambda w: self.start_global_plugin('Zoom'))]

    def build_gui(self, container):
        # TODO: fix for GTK
        if family.startswith('gtk'):
            self.orientation = 'horizontal'
        else:
            self.orientation = Widgets.get_orientation(container)
        tb_w = Widgets.Toolbar(orientation=self.orientation)

        self.build_toolbar(tb_w, self.layout_common)
        self.build_toolbar(tb_w, self.layout)
        self.w.toolbar = tb_w

        container.add_widget(tb_w, stretch=1)
        self.gui_up = True

    def start(self):
        self._update_toolbar_state()

    # CALLBACKS

    def center_image_cb(self, w):
        self.fitsimage.center_image()
        return True

    def reset_contrast_cb(self, w):
        view, mode = self._get_mode('contrast')
        event = KeyEvent()
        mode.kp_contrast_restore(view, event, 'x', 0.0, 0.0)
        return True

    def auto_levels_cb(self, w):
        self.fitsimage.auto_levels()
        return True

    def rot90_cb(self, w):
        self.fitsimage.rotate_delta(90.0)
        return True

    def rotn90_cb(self, w):
        self.fitsimage.rotate_delta(-90.0)
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
        view = self.fitsimage
        with view.suppress_redraw:
            view.rotate(0.0)
            view.transform(False, False, False)
        return True

    def flipx_cb(self, w, tf):
        view = self.fitsimage
        flip_x, flip_y, swap_xy = view.get_transforms()
        flip_x = tf
        view.transform(flip_x, flip_y, swap_xy)
        return True

    def flipy_cb(self, w, tf):
        view = self.fitsimage
        flip_x, flip_y, swap_xy = view.get_transforms()
        flip_y = tf
        view.transform(flip_x, flip_y, swap_xy)
        return True

    def swapxy_cb(self, w, tf):
        view = self.fitsimage
        flip_x, flip_y, swap_xy = view.get_transforms()
        swap_xy = tf
        view.transform(flip_x, flip_y, swap_xy)
        return True

    def mode_cb(self, tf, modename):
        bm = self.fitsimage.get_bindmap()
        if not tf:
            bm.reset_mode(self.fitsimage)
            self.fv.show_status("")
            return True

        bm.set_mode(modename)
        # just in case mode change failed
        self._update_toolbar_state()
        self.fv.show_status(f"Type 'h' in the viewer to show help for mode {modename}")
        return True

    def mode_set_cb(self, bm, mode, mtype):
        # called whenever the user interaction mode is changed
        # in the viewer
        self._update_toolbar_state()
        return True

    def viewer_transform_cb(self, chviewer):
        # called whenever the transform (flip x/y, swap axes) is done
        # in the viewer
        self._update_toolbar_state()
        return True

    def set_locked_cb(self, w, tf):
        if tf:
            modetype = 'locked'
        else:
            modetype = 'oneshot'
        chviewer = self.fitsimage

        # get current bindmap, make sure that the mode is consistent
        # with current lock button
        bm = chviewer.get_bindmap()
        modename, cur_modetype = bm.current_mode()
        bm.set_default_mode_type(modetype)

        bm.set_mode(modename, mode_type=modetype)
        if not tf:
            # turning off lock also resets the mode
            bm.reset_mode(chviewer)

        self._update_toolbar_state()
        return True

    # LOGIC

    def _get_mode(self, mode_name):
        view = self.fitsimage
        bd = view.get_bindings()
        mode = bd.get_mode_obj(mode_name)
        return view, mode

    def redo(self):
        self._update_toolbar_state()

    def clear(self):
        self._update_toolbar_state()

    def _update_toolbar_state(self):
        if not self.gui_up:
            return
        self.logger.debug("updating toolbar state")
        chviewer = self.fitsimage
        try:
            self._update_viewer_selection()

            # Update toolbar channel buttons
            enabled = len(self.channel) > 1
            self.w.btn_up.set_enabled(enabled)
            self.w.btn_down.set_enabled(enabled)

            bd = chviewer.get_bindings()
            can_flip = bd.get_feature_allow('flip')
            self.w.btn_flipx.set_enabled(can_flip)
            self.w.btn_flipy.set_enabled(can_flip)
            self.w.btn_swapxy.set_enabled(can_flip)

            # update transform toggles
            flipx, flipy, swapxy = chviewer.get_transforms()
            # toolbar follows view
            self.w.btn_flipx.set_state(flipx)
            self.w.btn_flipy.set_state(flipy)
            self.w.btn_swapxy.set_state(swapxy)

            can_rotate = bd.get_feature_allow('rotate')
            self.w.btn_rotate.set_enabled(can_rotate)
            self.w.btn_restore.set_enabled(can_rotate & can_flip)
            self.w.btn_rot90.set_enabled(can_rotate)
            self.w.btn_rotn90.set_enabled(can_rotate)
            self.w.btn_orientrh.set_enabled(can_rotate)
            self.w.btn_orientlh.set_enabled(can_rotate)

            can_pan = bd.get_feature_allow('pan')
            can_zoom = bd.get_feature_allow('zoom')
            self.w.btn_pan.set_enabled(can_pan & can_zoom)
            self.w.btn_center.set_enabled(can_pan)

            self.w.btn_zoom_in.set_enabled(can_zoom)
            self.w.btn_zoom_out.set_enabled(can_zoom)
            self.w.btn_zoom_fit.set_enabled(can_zoom)
            self.w.btn_zoom_1_1.set_enabled(can_zoom)
            self.w.btn_zoom.set_enabled(can_pan & can_zoom)

            can_cut = bd.get_feature_allow('cut')
            self.w.btn_cuts.set_enabled(can_cut)
            self.w.btn_autolevels.set_enabled(can_cut)

            can_cmap = bd.get_feature_allow('cmap')
            self.w.btn_contrast.set_enabled(can_cmap)
            self.w.btn_resetcontrast.set_enabled(can_cmap)
            self.w.btn_dist.set_enabled(can_cmap)
            self.w.btn_cmap.set_enabled(can_cmap)

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
        return 'toolbar_ginga_image'


class Toolbar_Ginga_Plot(Toolbar_Common):
    """A toolbar for the Ginga Plot viewer.
    """

    def __init__(self, fv, chviewer):
        # superclass defines some variables for us, like logger
        super().__init__(fv, chviewer)

        # get local plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('toolbar_Ginga_Plot')
        self.settings.add_defaults(zoom_bump_pct=1.1)
        self.settings.load(onError='silent')

        self.layout = [
            # (Name, type, icon, tooltip)
            ("Zoom In", 'button', 'zoom_in', "Zoom in",
             lambda w: self.zoom_in()),
            ("Zoom Out", 'button', 'zoom_out', "Zoom out",
             lambda w: self.zoom_out()),
            ("Zoom Fit", 'button', 'zoom_fit', "Fit plot to window size",
             lambda w: self.zoom_fit()),
            ("Zoom Fit X", 'button', 'zoom_fit_x', "Fit X axis to window size",
             lambda w: self.zoom_fit_x()),
            ("Zoom Fit Y", 'button', 'zoom_fit_y', "Fit Y axis to window size",
             lambda w: self.zoom_fit_y()),
            ("---",),
            ("Preferences", 'button', 'settings', "Set channel preferences (in focused channel)",
             lambda w: self.start_local_plugin('Preferences')),
            ("FBrowser", 'button', 'folder_open', "Open file (in focused channel)",
             lambda w: self.start_local_plugin('FBrowser')),
            ("MultiDim", 'button', 'layers', "Select HDUs or cube slices (in focused channel)",
             lambda w: self.start_local_plugin('MultiDim')),
            ("Header", 'button', 'tags', "View image metadata (Header plugin)",
             lambda w: self.start_global_plugin('Header'))]

    def build_gui(self, container):
        # TODO: fix for GTK
        if family.startswith('gtk'):
            self.orientation = 'horizontal'
        else:
            self.orientation = Widgets.get_orientation(container)
        tb_w = Widgets.Toolbar(orientation=self.orientation)

        self.build_toolbar(tb_w, self.layout_common)
        self.build_toolbar(tb_w, self.layout)
        self.w.toolbar = tb_w

        container.add_widget(tb_w, stretch=1)
        self.gui_up = True

    def start(self):
        self._update_toolbar_state()

    # CALLBACKS

    def zoom_in(self):
        viewer = self.channel.get_viewer('Ginga Plot')
        pct = self.settings['zoom_bump_pct']
        viewer.zoom_plot(1 / pct, 1 / pct)

    def zoom_out(self):
        viewer = self.channel.get_viewer('Ginga Plot')
        pct = self.settings['zoom_bump_pct']
        viewer.zoom_plot(pct, pct)

    def zoom_fit_x(self):
        viewer = self.channel.get_viewer('Ginga Plot')
        viewer.zoom_fit(axis='x')

    def zoom_fit_y(self):
        viewer = self.channel.get_viewer('Ginga Plot')
        viewer.zoom_fit(axis='y')

    def zoom_fit(self):
        viewer = self.channel.get_viewer('Ginga Plot')
        viewer.zoom_fit(axis='xy')

    # LOGIC

    def redo(self):
        self._update_toolbar_state()

    def clear(self):
        self._update_toolbar_state()

    def _update_toolbar_state(self):
        if not self.gui_up:
            return
        self.logger.debug("updating toolbar state")
        try:
            self._update_viewer_selection()

            # Update toolbar channel buttons
            enabled = len(self.channel) > 1
            self.w.btn_up.set_enabled(enabled)
            self.w.btn_down.set_enabled(enabled)

        except Exception as e:
            self.logger.error("error updating toolbar: %s" % str(e))
            raise e

    def __str__(self):
        return 'toolbar_ginga_plot'


class Toolbar_Ginga_Table(Toolbar_Common):
    """A toolbar for the Ginga Table viewer.
    """

    def __init__(self, fv, chviewer):
        # superclass defines some variables for us, like logger
        super().__init__(fv, chviewer)

        # get local plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('toolbar_Ginga_Table')
        self.settings.load(onError='silent')

        self.layout = [
            # (Name, type, icon, tooltip)
            ("Preferences", 'button', 'settings', "Set channel preferences (in focused channel)",
             lambda w: self.start_local_plugin('Preferences')),
            ("FBrowser", 'button', 'folder_open', "Open file (in focused channel)",
             lambda w: self.start_local_plugin('FBrowser')),
            ("MultiDim", 'button', 'layers', "Select HDUs or cube slices (in focused channel)",
             lambda w: self.start_local_plugin('MultiDim')),
            ("Header", 'button', 'tags', "View image metadata (Header plugin)",
             lambda w: self.start_global_plugin('Header'))]

    def build_gui(self, container):
        # TODO: fix for GTK
        if family.startswith('gtk'):
            self.orientation = 'horizontal'
        else:
            self.orientation = Widgets.get_orientation(container)
        tb_w = Widgets.Toolbar(orientation=self.orientation)

        self.build_toolbar(tb_w, self.layout_common)
        self.build_toolbar(tb_w, self.layout)
        self.w.toolbar = tb_w

        container.add_widget(tb_w, stretch=1)
        self.gui_up = True

    def start(self):
        self._update_toolbar_state()

    # LOGIC

    def redo(self):
        self._update_toolbar_state()

    def clear(self):
        self._update_toolbar_state()

    def _update_toolbar_state(self):
        if not self.gui_up:
            return
        self.logger.debug("updating toolbar state")
        try:
            self._update_viewer_selection()

            # Update toolbar channel buttons
            enabled = len(self.channel) > 1
            self.w.btn_up.set_enabled(enabled)
            self.w.btn_down.set_enabled(enabled)

        except Exception as e:
            self.logger.error("error updating toolbar: %s" % str(e))
            raise e

    def __str__(self):
        return 'toolbar_ginga_table'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Toolbar', package='ginga')

# END
