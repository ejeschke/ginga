#
# cmap.py -- mode for setting color map
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""CMap Mode enables bindings that can adjust the color and intensity
maps of an image in a Ginga image viewer.

Enter the mode by
-----------------
* Space, then "y"

Exit the mode by
----------------
* Esc

Default bindings in mode
------------------------
* Y : reset colormap to default (gray)
* r : restore color map (undo any color map inversion, rotation or stretch)
* I : invert current color map (preserving any rotation or stretch)
* up arrow : set previous colormap in list (preserves any rotation or stretch)
* down arrow : set next colormap in list (preserves any rotation or stretch)
* c : overlay a visible colormap on the image
* i : restore the default intensity map to "ramp", the default
* j, left arrow : set previous intensity map in list
* k, right arrow : set next intensity map in list
* scroll : choose color map from list
* Ctrl + scroll : choose intensity map from list
* left drag : rotate current color map
* right click : restore color map (same as "r")

"""
from ginga import cmap, imap
from ginga.modes.mode_base import Mode


class CMapMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_cmap=['__y', None, None],

            kp_cmap_reset=['Y', 'cmap+Y'],
            kp_cmap_restore=['cmap+r'],
            kp_cmap_invert=['I', 'cmap+I'],
            kp_cmap_prev=['cmap+up', 'cmap+b'],
            kp_cmap_next=['cmap+down', 'cmap+n'],
            kp_toggle_cbar=['cmap+c'],
            kp_imap_reset=['cmap+i'],
            kp_imap_prev=['cmap+left', 'cmap+j'],
            kp_imap_next=['cmap+right', 'cmap+k'],

            sc_cmap=['cmap+scroll'],
            sc_imap=['cmap+ctrl+scroll'],

            ms_cmap_rotate=['cmap+left'],
            ms_cmap_restore=['cmap+right'])

    def __str__(self):
        return 'cmap'

    @property
    def cancmap(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('cmap')

    def start(self):
        pass

    def stop(self):
        self.onscreen_message(None)

    def restore_colormap(self, viewer, msg=True):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = viewer.get_rgbmap()
        rgbmap.restore_cmap()
        if msg:
            self.onscreen_message("Restored color map", delay=0.5)
        return True

    def _rotate_colormap(self, viewer, x, y, mode):
        win_wd, win_ht = viewer.get_window_size()

        # translate X cursor position as a percentage of the window
        # width into a shifting factor
        half_wd = win_wd / 2.0
        shift_pct = (x - half_wd) / float(half_wd)
        num = int(shift_pct * 255)
        self.logger.debug("rotating color map by %d steps" % (num))

        rgbmap = viewer.get_rgbmap()
        with rgbmap.suppress_changed:
            rgbmap.restore_cmap(callback=False)
            rgbmap.rotate_cmap(num)

    def _cycle_cmap(self, viewer, msg, direction='down'):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = viewer.get_rgbmap()
        cm = rgbmap.get_cmap()
        cmapname = cm.name
        cmapnames = cmap.get_names()
        idx = cmapnames.index(cmapname)
        if direction == 'down':
            idx = (idx + 1) % len(cmapnames)
        else:
            idx = idx - 1
            if idx < 0:
                idx = len(cmapnames) - 1
        cmapname = cmapnames[idx]
        viewer.set_color_map(cmapname)
        if msg:
            self.onscreen_message("Color map: %s" % (cmapname),
                                  delay=1.0)

    def _reset_cmap(self, viewer, msg):
        msg = self.settings.get('msg_cmap', msg)
        # default
        cmapname = 'gray'
        viewer.set_color_map(cmapname)
        if msg:
            self.onscreen_message("Color map: %s" % (cmapname),
                                  delay=1.0)

    def _invert_cmap(self, viewer, msg):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = viewer.get_rgbmap()
        rgbmap.invert_cmap()
        if msg:
            self.onscreen_message("Inverted color map", delay=1.0)

    def _cycle_imap(self, viewer, msg, direction='down'):
        msg = self.settings.get('msg_imap', msg)
        rgbmap = viewer.get_rgbmap()
        im = rgbmap.get_imap()
        imapname = im.name
        imapnames = imap.get_names()
        idx = imapnames.index(imapname)
        if direction == 'down':
            idx = (idx + 1) % len(imapnames)
        else:
            idx = idx - 1
            if idx < 0:
                idx = len(imapnames) - 1
        imapname = imapnames[idx]
        viewer.set_intensity_map(imapname)
        if msg:
            self.onscreen_message("Intensity map: %s" % (imapname),
                                  delay=1.0)

    def _reset_imap(self, viewer, msg):
        msg = self.settings.get('msg_imap', msg)
        # default
        imapname = 'ramp'
        viewer.set_intensity_map(imapname)
        if msg:
            self.onscreen_message("Intensity map: %s" % (imapname),
                                  delay=1.0)

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_cmap_reset(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._reset_cmap(viewer, msg)

    def kp_cmap_restore(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self.restore_colormap(viewer, msg)
        return True

    def kp_cmap_invert(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._invert_cmap(viewer, msg)
        return True

    def kp_cmap_prev(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._cycle_cmap(viewer, msg, direction='up')
        return True

    def kp_cmap_next(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._cycle_cmap(viewer, msg, direction='down')
        return True

    def kp_toggle_cbar(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        canvas = viewer.get_private_canvas()
        # canvas already has a color bar?
        objs = list(canvas.get_objects_by_kinds(('colorbar', 'drawablecolorbar')))
        tf = (len(objs) == 0)
        viewer.show_color_bar(tf)
        return True

    def kp_imap_reset(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._reset_imap(viewer, msg)
        return True

    def kp_imap_prev(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._cycle_imap(viewer, msg, direction='up')
        return True

    def kp_imap_next(self, viewer, event, data_x, data_y, msg=True):
        if not self.cancmap:
            return False
        event.accept()
        self._cycle_imap(viewer, msg, direction='down')
        return True

    #####  SCROLL ACTION CALLBACKS #####

    def sc_cmap(self, viewer, event, msg=True):
        """Interactively change the color map by scrolling.
        """
        if not self.cancmap:
            return False
        event.accept()
        direction = self.get_direction(event.direction)
        self._cycle_cmap(viewer, msg, direction=direction)

    def sc_imap(self, viewer, event, msg=True):
        """Interactively change the intensity map by scrolling.
        """
        if not self.cancmap:
            return False
        event.accept()
        direction = self.get_direction(event.direction)
        self._cycle_imap(viewer, msg, direction=direction)

    #####  MOUSE ACTION CALLBACKS #####

    def ms_cmap_rotate(self, viewer, event, data_x, data_y, msg=True):
        """Shift the colormap by dragging the cursor left or right.
        Stretch the colormap by dragging the cursor up or down.
        """
        if not self.cancmap:
            return False
        event.accept()
        msg = self.settings.get('msg_cmap', msg)

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._rotate_colormap(viewer, x, y, 'preview')

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            if msg:
                self.onscreen_message("Rotate colormap (drag mouse L/R)",
                                      delay=1.0)
        else:
            self.onscreen_message(None)

    def ms_cmap_restore(self, viewer, event, data_x, data_y, msg=True):
        """An interactive way to restore the colormap settings after
        a rotate or invert operation.
        """
        if not self.cancmap:
            return False
        event.accept()
        if event.state == 'down':
            self.restore_colormap(viewer, msg)
