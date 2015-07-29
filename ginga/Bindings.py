#
# Bindings.py -- Bindings classes for Ginga FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math

from ginga.misc import Bunch, Settings, Callback
from ginga import AutoCuts, trcalc
from ginga import cmap, imap


class ImageViewBindings(object):
    """
    Mouse Operation and Bindings

    """

    def __init__(self, logger, settings=None):
        super(ImageViewBindings, self).__init__()

        self.logger = logger

        self.canpan = False
        self.canzoom = False
        self._ispanning = False
        self.cancut = False
        self.cancmap = False
        self.canflip = False
        self.canrotate = False

        # For panning
        self._pantype = 1
        self._start_x = None
        self._start_y = None
        self._start_panx = 0
        self._start_pany = 0

        self._start_scale_x = 0
        self._start_scale_y = 0
        self._start_rot = 0

        if settings is None:
            # No settings passed.  Set up defaults.
            settings = Settings.SettingGroup(name='bindings',
                                             logger=self.logger)
            self.initialize_settings(settings)
        self.settings = settings
        self.autocuts = AutoCuts.ZScale(self.logger)

        self.features = dict(
            # name, attr pairs
            pan='canpan', zoom='canzoom', cuts='cancut', cmap='cancmap',
            flip='canflip', rotate='canrotate')

    def initialize_settings(self, settings):
        settings.addSettings(
            # You should rarely have to change these.
            btn_nobtn = 0x0,
            btn_left  = 0x1,
            btn_middle= 0x2,
            btn_right = 0x4,

            # Set up our standard modifiers
            mod_shift = ['shift_l', 'shift_r'],
            mod_ctrl = ['control_l', 'control_r'],
            mod_meta = ['meta_right'],

            # Define our modes
            dmod_draw = ['space', None, None],
            dmod_cmap = ['y', None, None],
            dmod_cuts = ['s', None, None],
            dmod_dist = ['d', None, None],
            dmod_contrast = ['t', None, None],
            dmod_rotate = ['r', None, None],
            dmod_pan = ['q', None, None],
            dmod_freepan = ['w', None, None],

            # KEYBOARD
            kp_zoom_in = ['+', '='],
            kp_zoom_out = ['-', '_'],
            kp_zoom = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            kp_zoom_inv = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
            kp_zoom_fit = ['backquote'],
            kp_autozoom_on = ['doublequote'],
            kp_autozoom_override = ['singlequote'],
            kp_dist_reset = ['D'],
            kp_pan_set = ['p'],
            kp_center = ['c'],
            kp_cut_255 = ['A'],
            kp_cut_auto = ['a'],
            kp_autocuts_on = [':'],
            kp_autocuts_override = [';'],
            kp_autocenter_override = ['/'],
            kp_contrast_restore = ['T'],
            kp_cmap_reset = ['Y'],
            kp_imap_reset = [],
            kp_flip_x = ['[', '{'],
            kp_flip_y = [']', '}'],
            kp_swap_xy = ['backslash', '|'],
            kp_rotate_reset = ['R'],
            kp_rotate_inc90 = ['.'],
            kp_rotate_dec90 = [','],
            kp_orient_lh = ['o'],
            kp_orient_rh = ['O'],
            kp_poly_add = ['v', 'draw+v'],
            kp_poly_del = ['z', 'draw+z'],
            kp_edit_del = ['draw+x'],
            kp_reset = ['escape'],
            kp_lock = ['l'],

            # SCROLLING/WHEEL
            sc_pan = [],
            sc_pan_fine = [],
            sc_pan_coarse = [],
            sc_zoom = ['scroll'],
            sc_zoom_fine = ['shift+scroll'],
            sc_zoom_coarse = ['ctrl+scroll'],
            sc_cuts_fine = ['cuts+scroll'],
            sc_cuts_coarse = [],
            sc_dist = ['dist+scroll'],
            sc_cmap = ['cmap+scroll'],
            sc_imap = [],
            #sc_draw = ['draw+scroll'],

            scroll_pan_acceleration = 1.0,
            # 1.0 is appropriate for a mouse, 0.1 for most trackpads
            scroll_zoom_acceleration = 1.0,
            #scroll_zoom_acceleration = 0.1,
            mouse_zoom_acceleration = 1.085,
            mouse_rotate_acceleration = 0.75,
            pan_reverse = False,
            pan_multiplier = 1.0,
            zoom_scroll_reverse = False,

            # MOUSE/BUTTON
            ms_none = ['nobtn'],
            ms_cursor = ['left'],
            ms_wheel = [],
            ms_draw = ['draw+left', 'meta+left', 'right'],

            ms_rotate = ['rotate+left'],
            ms_rotate_reset = ['rotate+right'],
            ms_contrast = ['contrast+left', 'ctrl+right'],
            ms_contrast_restore = ['contrast+right', 'ctrl+middle'],
            ms_pan = ['pan+left', 'ctrl+left'],
            ms_zoom = ['pan+right'],
            ms_freepan = ['freepan+left', 'middle'],
            ms_zoom_in = ['freepan+middle'],
            ms_zoom_out = ['freepan+right'],
            ## ms_cutlo = ['cutlo+left'],
            ## ms_cuthi = ['cuthi+left'],
            ms_cutall = ['cuts+left'],
            ms_cut_auto = ['cuts+right'],
            ms_panset = ['pan+middle', 'shift+left'],

            # GESTURES (some backends only)
            gs_pinch = [],
            # Rotate gesture usually doesn't work so well on most platforms
            # so don't enable by default
            #gs_rotate = [],
            gs_pan = [],
            gs_swipe = [],
            gs_tap = [],
            pinch_actions = ['zoom'],
            pinch_zoom_acceleration = 1.0,
            pinch_rotate_acceleration = 1.0,
            )

    def get_settings(self):
        return self.settings

    def window_map(self, viewer):
        self.to_default_mode(viewer)

    def set_bindings(self, viewer):
        viewer.add_callback('map', self.window_map)

        bindmap = viewer.get_bindmap()
        bindmap.clear_button_map()
        bindmap.clear_event_map()

        # Set up bindings
        self.setup_settings_events(viewer, bindmap)

    def set_mode(self, viewer, name, mode_type='oneshot'):
        bindmap = viewer.get_bindmap()
        bindmap.set_mode(name, mode_type=mode_type)

    def parse_combo(self, combo, modes_set, modifiers_set):
        mode, mods, trigger = None, set([]), combo
        if '+' in combo:
            if combo.endswith('+'):
                # special case: probably contains the keystroke '+'
                trigger, combo = '+', combo[:-1]
                if '+' in combo:
                    items = set(combo.split('+'))
                else:
                    items = set(combo)
            else:
                # trigger is always specified last
                items = combo.split('+')
                trigger, items = items[-1], set(items[:-1])

            mods = items.intersection(modifiers_set)
            mode = items.intersection(modes_set)
            if len(mode) == 0:
                mode = None
            else:
                mode = mode.pop()

        return (mode, mods, trigger)

    def setup_settings_events(self, viewer, bindmap):

        d = self.settings.getDict()
        if len(d) == 0:
            self.initialize_settings(self.settings)
            d = self.settings.getDict()

        # First scan settings for buttons and modes
        bindmap.clear_modifier_map()
        bindmap.clear_mode_map()

        for name, value in d.items():
            if name.startswith('mod_'):
                modname = name[4:]
                for combo in value:
                    # NOTE: for now no chorded combinations
                    keyname = combo
                    bindmap.add_modifier(keyname, modname)

            elif name.startswith('btn_'):
                btnname = name[4:]
                bindmap.map_button(value, btnname)

            elif name.startswith('dmod_'):
                mode_name = name[5:]
                keyname, mode_type, msg = value
                bindmap.add_mode(keyname, mode_name, mode_type=mode_type,
                                     msg=msg)

        modes_set = bindmap.get_modes()
        modifiers_set = bindmap.get_modifiers()

        # Add events
        for name, value in d.items():
            if len(name) <= 3:
                continue

            pfx = name[:3]
            if not pfx in ('kp_', 'ms_', 'sc_', 'gs_'):
                continue

            evname = name[3:]
            for combo in value:
                mode, modifiers, trigger = self.parse_combo(combo, modes_set,
                                                            modifiers_set)
                bindmap.map_event(mode, modifiers, trigger, evname)

            # Register for this symbolic event if we have a handler for it
            try:
                cb_method = getattr(self, name)

            except AttributeError:
                self.logger.warn("No method found matching '%s'" % (name))
                cb_method = None

            if pfx == 'kp_':
                # keyboard event
                event = 'keydown-%s' % (evname)
                viewer.enable_callback(event)
                if cb_method:
                    viewer.add_callback(event, cb_method)

            elif pfx == 'ms_':
                # mouse/button event
                for action in ('down', 'move', 'up'):
                    event = '%s-%s' % (evname, action)
                    viewer.enable_callback(event)
                    if cb_method:
                        viewer.add_callback(event, cb_method)

            elif pfx == 'sc_':
                # scrolling event
                event = '%s-scroll' % evname
                viewer.enable_callback(event)
                if cb_method:
                    viewer.add_callback(event, cb_method)

            elif pfx == 'gs_':
                viewer.set_callback(evname, cb_method)

    def reset(self, viewer):
        bindmap = viewer.get_bindmap()
        bindmap.reset_mode(viewer)
        self.pan_stop(viewer)
        viewer.onscreen_message(None)

    #####  ENABLERS #####
    # These methods are a quick way to enable or disable certain user
    # interface features in a ImageView window

    def enable_pan(self, tf):
        """Enable the image to be panned interactively (True/False)."""
        self.canpan = tf

    def enable_zoom(self, tf):
        """Enable the image to be zoomed interactively (True/False)."""
        self.canzoom = tf

    def enable_cuts(self, tf):
        """Enable the cuts levels to be set interactively (True/False)."""
        self.cancut = tf

    def enable_cmap(self, tf):
        """Enable the color map to be warped interactively (True/False)."""
        self.cancmap = tf

    def enable_flip(self, tf):
        """Enable the image to be flipped interactively (True/False)."""
        self.canflip = tf

    def enable_rotate(self, tf):
        """Enable the image to be rotated interactively (True/False)."""
        self.canrotate = tf

    def enable(self, **kwdargs):
        """
        General enable function encompassing all user interface features.
        Usage (e.g.):
            viewer.enable(rotate=False, flip=True)
        """
        for feat, value in kwdargs:
            feat = feat.lower()
            if not feat in self.features:
                raise ValueError("'%s' is not a feature. Must be one of %s" % (
                    feat, str(self.features)))

            attr = self.features[feat]
            setattr(self, attr, bool(value))

    def enable_all(self, tf):
        for feat, attr in self.features.items():
            setattr(self, attr, bool(tf))


    #####  Help methods #####
    # Methods used by the callbacks to do actions.

    def get_new_pan(self, viewer, win_x, win_y, ptype=1):

        if ptype == 1:
            # This is a "free pan", similar to dragging the "lens"
            # over the canvas.
            dat_wd, dat_ht = viewer.get_data_size()
            win_wd, win_ht = viewer.get_window_size()

            if (win_x >= win_wd):
                win_x = win_wd - 1
            if (win_y >= win_ht):
                win_y = win_ht - 1

            # Figure out data x,y based on percentage of X axis
            # and Y axis
            off_x, off_y = viewer.canvas2offset(win_x, win_y)
            max_x, max_y = viewer.canvas2offset(win_wd, win_ht)
            wd_x = abs(max_x) * 2.0
            ht_y = abs(max_y) * 2.0
            panx = (off_x + abs(max_x)) / float(wd_x)
            pany = (off_y + abs(max_y)) / float(ht_y)

            # Account for user preference
            if self.settings.get('pan_reverse', False):
                panx = 1.0 - panx
                pany = 1.0 - pany

            data_x, data_y = panx * dat_wd, pany * dat_ht
            return data_x, data_y

        elif ptype == 2:
            # This is a "drag pan", similar to dragging the canvas
            # under the "lens" or "viewport".
            if self._start_x is None:
                # user has not held the mouse button yet
                # return current pan values
                return (self._start_panx, self._start_pany)

            scale_x, scale_y = viewer.get_scale_xy()
            multiplier = self.settings.get('pan_multiplier', 1.0)
            off_x, off_y = viewer.canvas2offset(win_x, win_y)
            delta_x = float(self._start_x - off_x) / scale_x * multiplier
            delta_y = float(self._start_y - off_y) / scale_y * multiplier

            data_x = self._start_panx + delta_x
            data_y = self._start_pany + delta_y

        return (data_x, data_y)

    def _panset(self, viewer, data_x, data_y, msg=True):
        try:
            msg = self.settings.get('msg_panset', msg)
            if msg:
                viewer.onscreen_message("Pan position set", delay=0.4)

            res = viewer.panset_xy(data_x, data_y)
            return res

        except ImageView.ImageViewCoordsError as e:
            # coords are not within the data area
            pass

    def get_direction(self, direction, rev=False):
        """
        Translate a direction in compass degrees into 'up' or 'down'.
        """
        if (direction < 90.0) or (direction > 270.0):
            if not rev:
                return 'up'
            else:
                return 'down'
        elif (90.0 < direction < 270.0):
            if not rev:
                return 'down'
            else:
                return 'up'
        else:
            return 'none'

    def _tweak_colormap(self, viewer, x, y, mode):
        win_wd, win_ht = viewer.get_window_size()

        # translate Y cursor position as a percentage of the window
        # height into a scaling factor
        y_pct = (win_ht - y) / float(win_ht)
        # I tried to mimic ds9's exponential scale feel along the Y-axis
        def exp_scale(i):
            return (1.0/(i**3))*0.0002 + (1.0/i)*0.085
        scale_pct = exp_scale(1.0 - y_pct)

        # translate X cursor position as a percentage of the window
        # width into a shifting factor
        shift_pct = x / float(win_wd) - 0.5

        viewer.scale_and_shift_cmap(scale_pct, shift_pct)

    def _cutlow_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        loval = loval + (pct * spread)
        if msg:
            viewer.onscreen_message("Cut low: %.4f" % (loval))
        viewer.cut_levels(loval, hival)

    def _cutlow_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = viewer.get_window_size()
        pct = float(x) / float(win_wd)
        image = viewer.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        loval = minval + (pct * spread)
        if msg:
            viewer.onscreen_message("Cut low: %.4f" % (loval))
        viewer.cut_levels(loval, hival)

    def _cuthigh_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        hival = hival - (pct * spread)
        if msg:
            viewer.onscreen_message("Cut high: %.4f" % (hival))
        viewer.cut_levels(loval, hival)

    def _cuthigh_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = viewer.get_window_size()
        pct = 1.0 - (float(x) / float(win_wd))
        image = viewer.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        hival = maxval - (pct * spread)
        if msg:
            viewer.onscreen_message("Cut high: %.4f" % (hival))
        viewer.cut_levels(loval, hival)

    def _cutboth_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = viewer.get_window_size()
        xpct = 1.0 - (float(x) / float(win_wd))
        #ypct = 1.0 - (float(y) / float(win_ht))
        ypct = (float(win_ht - y) / float(win_ht))
        spread = self._hival - self._loval
        hival = self._hival - (xpct * spread)
        loval = self._loval + (ypct * spread)
        if msg:
            viewer.onscreen_message("Cut low: %.4f  high: %.4f" % (
                loval, hival))
        viewer.cut_levels(loval, hival)

    def _cut_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        loval = loval + (pct * spread)
        hival = hival - (pct * spread)
        if msg:
            viewer.onscreen_message("Cut low: %.4f  high: %.4f" % (
                loval, hival), delay=1.0)
        viewer.cut_levels(loval, hival)

    def _adjust_cuts(self, viewer, direction, pct, msg=True):
        direction = self.get_direction(direction)
        if direction == 'up':
            self._cut_pct(viewer, pct, msg=msg)
        elif direction == 'down':
            self._cut_pct(viewer, -pct, msg=msg)

    def _scale_image(self, viewer, direction, factor, msg=True):
        msg = self.settings.get('msg_zoom', msg)
        rev = self.settings.get('zoom_scroll_reverse', False)
        scale_x, scale_y = viewer.get_scale_xy()
        direction = self.get_direction(direction, rev=rev)
        if direction == 'up':
                mult = 1.0 + factor
        elif direction == 'down':
                mult = 1.0 - factor
        scale_x, scale_y = scale_x * mult, scale_y * mult
        viewer.scale_to(scale_x, scale_y)
        if msg:
            viewer.onscreen_message(viewer.get_scale_text(),
                                       delay=0.4)

    def _zoom_xy(self, viewer, x, y, msg=True):
        win_wd, win_ht = viewer.get_window_size()
        delta = float(x - self._start_x)
        factor = math.fabs(self.settings.get('mouse_zoom_acceleration', 1.085)
                           - 1.0)
        direction = 0.0
        if delta < 0.0:
            direction = 180.0
        #print("factor=%f direction=%f" % (factor, direction))
        self._start_x = x
        self._scale_image(viewer, direction, factor, msg=msg)

    def _cycle_dist(self, viewer, msg, direction='down'):
        if self.cancmap:
            msg = self.settings.get('msg_dist', msg)
            rgbmap = viewer.get_rgbmap()
            algs = rgbmap.get_hash_algorithms()
            algname = rgbmap.get_hash_algorithm()
            idx = algs.index(algname)
            if direction == 'down':
                idx = (idx + 1) % len(algs)
            else:
                idx = idx - 1
                if idx < 0: idx = len(algs) - 1
            algname = algs[idx]
            rgbmap.set_hash_algorithm(algname)
            if msg:
                viewer.onscreen_message("Color dist: %s" % (algname),
                                           delay=1.0)

    def _reset_dist(self, viewer, msg):
        if self.cancmap:
            msg = self.settings.get('msg_dist', msg)
            rgbmap = viewer.get_rgbmap()
            algname = 'linear'
            rgbmap.set_hash_algorithm(algname)
            if msg:
                viewer.onscreen_message("Color dist: %s" % (algname),
                                           delay=1.0)

    def _cycle_cmap(self, viewer, msg, direction='down'):
        if self.cancmap:
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
                if idx < 0: idx = len(cmapnames) - 1
            cmapname = cmapnames[idx]
            rgbmap.set_cmap(cmap.get_cmap(cmapname))
            if msg:
                viewer.onscreen_message("Color map: %s" % (cmapname),
                                           delay=1.0)

    def _reset_cmap(self, viewer, msg):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            rgbmap = viewer.get_rgbmap()
            # default
            cmapname = 'gray'
            rgbmap.set_cmap(cmap.get_cmap(cmapname))
            if msg:
                viewer.onscreen_message("Color map: %s" % (cmapname),
                                           delay=1.0)

    def _cycle_imap(self, viewer, msg, direction='down'):
        if self.cancmap:
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
                if idx < 0: idx = len(imapnames) - 1
            imapname = imapnames[idx]
            rgbmap.set_imap(imap.get_imap(imapname))
            if msg:
                viewer.onscreen_message("Intensity map: %s" % (imapname),
                                           delay=1.0)

    def _reset_imap(self, viewer, msg):
        if self.cancmap:
            msg = self.settings.get('msg_imap', msg)
            rgbmap = viewer.get_rgbmap()
            # default
            imapname = 'ramp'
            rgbmap.set_imap(imap.get_imap(imapname))
            if msg:
                viewer.onscreen_message("Intensity map: %s" % (imapname),
                                           delay=1.0)

    def _get_pct_xy(self, viewer, x, y):
        win_wd, win_ht = viewer.get_window_size()
        x_pct = float(x - self._start_x) / win_wd
        y_pct = float(y - self._start_y) / win_ht
        return (x_pct, y_pct)

    def _rotate_xy(self, viewer, x, y, msg=True):
        msg = self.settings.get('msg_rotate', msg)
        x_pct, y_pct = self._get_pct_xy(viewer, x, y)
        delta_deg = x_pct * 360.0
        factor = self.settings.get('mouse_rotate_acceleration', 0.75)
        deg = math.fmod(self._start_rot + delta_deg * factor, 360.0)
        if msg:
            viewer.onscreen_message("Rotate: %.2f" % (deg))
        viewer.rotate(deg)

    def _rotate_inc(self, viewer, inc_deg, msg=True):
        msg = self.settings.get('msg_rotate_inc', msg)
        cur_rot_deg = viewer.get_rotation()
        rot_deg = math.fmod(cur_rot_deg + inc_deg, 360.0)
        viewer.rotate(rot_deg)
        if msg:
            viewer.onscreen_message("Rotate Inc: (%.2f) %.2f" % (
                inc_deg, rot_deg), delay=1.0)

    def _orient(self, viewer, righthand=False, msg=True):
        msg = self.settings.get('msg_orient', msg)
        image = viewer.get_image()

        (x, y, xn, yn, xe, ye) = image.calc_compass_center()
        degn = math.degrees(math.atan2(xn - x, yn - y))
        self.logger.info("degn=%f xe=%f ye=%f" % (
            degn, xe, ye))
        # rotate east point also by degn
        xe2, ye2 = trcalc.rotate_pt(xe, ye, degn, xoff=x, yoff=y)
        dege = math.degrees(math.atan2(xe2 - x, ye2 - y))
        self.logger.info("dege=%f xe2=%f ye2=%f" % (
            dege, xe2, ye2))

        # if right-hand image, flip it to make left hand
        xflip = righthand
        if dege > 0.0:
            xflip = not xflip
        if xflip:
            degn = - degn

        viewer.transform(xflip, False, False)
        viewer.rotate(degn)
        if msg:
            viewer.onscreen_message("Orient: rot=%.2f flipx=%s" % (
                degn, str(xflip)), delay=1.0)

    def to_default_mode(self, viewer):
        self._ispanning = False
        viewer.switch_cursor('pick')

    def pan_start(self, viewer, ptype=1):
        # If already panning then ignore multiple keystrokes
        if self._ispanning:
            return
        self._pantype = ptype
        viewer.switch_cursor('pan')
        self._ispanning = True

    def pan_set_origin(self, viewer, win_x, win_y, data_x, data_y):
        self._start_x, self._start_y = viewer.canvas2offset(win_x, win_y)
        self._start_panx, self._start_pany = viewer.get_pan()

    def pan_stop(self, viewer):
        self._ispanning = False
        self._start_x = None
        self._pantype = 1
        self.to_default_mode(viewer)

    def restore_colormap(self, viewer, msg=True):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = viewer.get_rgbmap()
        rgbmap.reset_sarr()
        if msg:
            viewer.onscreen_message("Restored color map", delay=0.5)
        return True


    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_pan_set(self, viewer, event, data_x, data_y, msg=True):
        if self.canpan:
            self._panset(viewer, data_x, data_y, msg=msg)
        return True

    def kp_center(self, viewer, event, data_x, data_y):
        if self.canpan:
            viewer.center_image()
        return True

    def kp_zoom_out(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.zoom_out()
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_in(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.zoom_in()
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            keylist = self.settings.get('kp_zoom')
            zoomval = (keylist.index(event.key) + 1)
            viewer.zoom_to(zoomval)
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_inv(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            keylist = self.settings.get('kp_zoom_inv')
            zoomval = - (keylist.index(event.key) + 1)
            viewer.zoom_to(zoomval)
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_fit(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.zoom_fit()
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_autozoom_on(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.enable_autozoom('on')
            if msg:
                viewer.onscreen_message('Autozoom On', delay=1.0)
        return True

    def kp_autozoom_override(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            viewer.enable_autozoom('override')
            if msg:
                viewer.onscreen_message('Autozoom Override', delay=1.0)
        return True

    def kp_cut_255(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            viewer.cut_levels(0.0, 255.0, no_reset=True)
        return True

    def kp_cut_auto(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            if msg:
                viewer.onscreen_message("Auto cut levels", delay=1.0)
            viewer.auto_levels()
        return True

    def kp_autocuts_on(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            viewer.enable_autocuts('on')
            if msg:
                viewer.onscreen_message('Autocuts On', delay=1.0)
        return True

    def kp_autocuts_override(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            viewer.enable_autocuts('override')
            if msg:
                viewer.onscreen_message('Autocuts Override', delay=1.0)
        return True

    def kp_autocenter_override(self, viewer, event, data_x, data_y, msg=True):
        if self.canpan:
            msg = self.settings.get('msg_cuts', msg)
            viewer.set_autocenter('override')
            if msg:
                viewer.onscreen_message('Autocenter Override', delay=1.0)
        return True

    def kp_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            self.restore_colormap(viewer, msg=msg)
        return True

    def kp_flip_x(self, viewer, event, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = viewer.get_transforms()
            if event.key == '[':
                flipx = not flipX
            else:
                flipx = False
            viewer.transform(flipx, flipY, swapXY)
            if msg:
                viewer.onscreen_message("Flip X=%s" % flipx, delay=1.0)
        return True

    def kp_flip_y(self, viewer, event, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = viewer.get_transforms()
            if event.key == ']':
                flipy = not flipY
            else:
                flipy = False
            viewer.transform(flipX, flipy, swapXY)
            if msg:
                viewer.onscreen_message("Flip Y=%s" % flipy, delay=1.0)
        return True

    def kp_swap_xy(self, viewer, event, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = viewer.get_transforms()
            if event.key == 'backslash':
                swapxy = not swapXY
            else:
                swapxy = False
            viewer.transform(flipX, flipY, swapxy)
            if msg:
                viewer.onscreen_message("Swap XY=%s" % swapxy, delay=1.0)
        return True

    def kp_dist(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_dist(viewer, msg)
        return True

    def kp_dist_reset(self, viewer, event, data_x, data_y, msg=True):
        self._reset_dist(viewer, msg)
        return True

    def kp_cmap_reset(self, viewer, event, data_x, data_y, msg=True):
        self._reset_cmap(viewer, msg)
        return True

    def kp_imap_reset(self, viewer, event, data_x, data_y, msg=True):
        self._reset_imap(viewer, msg)
        return True

    def kp_rotate_reset(self, viewer, event, data_x, data_y):
        if self.canrotate:
            viewer.rotate(0.0)
            # also reset all transforms
            viewer.transform(False, False, False)
        return True

    def kp_rotate_inc90(self, viewer, event, data_x, data_y, msg=True):
        if self.canrotate:
            self._rotate_inc(viewer, 90.0, msg=msg)
        return True

    def kp_rotate_dec90(self, viewer, event, data_x, data_y, msg=True):
        if self.canrotate:
            self._rotate_inc(viewer, -90.0, msg=msg)
        return True

    def kp_orient_lh(self, viewer, event, data_x, data_y, msg=True):
        if self.canrotate:
            self._orient(viewer, righthand=False, msg=msg)
        return True

    def kp_orient_rh(self, viewer, event, data_x, data_y,
                            msg=True):
        if self.canrotate:
            self._orient(viewer, righthand=True, msg=msg)
        return True

    def kp_reset(self, viewer, event, data_x, data_y):
        self.reset(viewer)
        return True

    def kp_lock(self, viewer, event, data_x, data_y):
        bm = viewer.get_bindmap()
        # toggle default mode type to locked/oneshot
        dfl_modetype = bm.get_default_mode_type()
        # get current mode
        mode_name, cur_modetype = bm.current_mode()

        if dfl_modetype == 'locked':
            mode_type = 'oneshot'
            bm.set_default_mode_type(mode_type)
            # turning off lock also resets the mode
            bm.reset_mode(viewer)
        else:
            mode_type = 'locked'
            bm.set_default_mode_type(mode_type)
            bm.set_mode(mode_name, mode_type=mode_type)
        return True

    #####  MOUSE ACTION CALLBACKS #####

    ## def ms_none(self, viewer, event, data_x, data_y):
    ##     return False

    ## def ms_cursor(self, viewer, event, data_x, data_y):
    ##     return False

    ## def ms_wheel(self, viewer, event, data_x, data_y):
    ##     return False

    ## def ms_draw(self, viewer, event, data_x, data_y):
    ##     return False

    def ms_zoom(self, viewer, event, data_x, data_y, msg=True):
        """Zoom the image by dragging the cursor left or right.
        """
        if not self.canzoom:
            return True
        msg = self.settings.get('msg_zoom', msg)

        x, y = viewer.get_last_win_xy()
        if event.state == 'move':
            self._zoom_xy(viewer, x, y)

        elif event.state == 'down':
            if msg:
                viewer.onscreen_message("Zoom (drag mouse L-R)",
                                           delay=1.0)
            self._start_x, self._start_y = x, y

        else:
            viewer.onscreen_message(None)
        return True

    def ms_zoom_in(self, viewer, event, data_x, data_y, msg=True):
        """Zoom in one level by a mouse click.
        """
        if not self.canzoom:
            return True

        if event.state == 'down':
            viewer.panset_xy(data_x, data_y)
            viewer.zoom_in()
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=1.0)
        return True

    def ms_zoom_out(self, viewer, event, data_x, data_y, msg=True):
        """Zoom out one level by a mouse click.
        """
        if not self.canzoom:
            return True

        if event.state == 'down':
            viewer.panset_xy(data_x, data_y)
            viewer.zoom_out()
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=1.0)
        return True


    def ms_rotate(self, viewer, event, data_x, data_y, msg=True):
        """Rotate the image by dragging the cursor left or right.
        """
        if not self.canrotate:
            return True
        msg = self.settings.get('msg_rotate', msg)

        x, y = viewer.get_last_win_xy()
        if event.state == 'move':
            self._rotate_xy(viewer, x, y)

        elif event.state == 'down':
            if msg:
                viewer.onscreen_message("Rotate (drag mouse L-R)",
                                           delay=1.0)
            self._start_x, self._start_y = x, y
            self._start_rot = viewer.get_rotation()

        else:
            viewer.onscreen_message(None)
        return True


    def ms_rotate_reset(self, viewer, event, data_x, data_y, msg=True):
        if not self.canrotate:
            return True
        msg = self.settings.get('msg_rotate', msg)

        if event.state == 'down':
            viewer.rotate(0.0)
            viewer.onscreen_message("Rotation reset", delay=0.5)
        return True


    def ms_contrast(self, viewer, event, data_x, data_y, msg=True):
        """Shift the colormap by dragging the cursor left or right.
        Stretch the colormap by dragging the cursor up or down.
        """
        if not self.cancmap:
            return True
        msg = self.settings.get('msg_contrast', msg)

        x, y = viewer.get_last_win_xy()
        if not viewer._originUpper:
            y = viewer._imgwin_ht - y
        if event.state == 'move':
            self._tweak_colormap(viewer, x, y, 'preview')

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            if msg:
                viewer.onscreen_message("Shift and stretch colormap (drag mouse)",
                                           delay=1.0)
        else:
            viewer.onscreen_message(None)
        return True


    def ms_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        """An interactive way to restore the colormap settings after
        a warp operation.
        """
        if self.cancmap and (event.state == 'down'):
            self.restore_colormap(viewer, msg=msg)
            return True


    def ms_pan(self, viewer, event, data_x, data_y):
        """A 'drag' or proportional pan, where the image is panned by
        'dragging the canvas' up or down.  The amount of the pan is
        proportionate to the length of the drag.
        """
        if not self.canpan:
            return True

        x, y = viewer.get_last_win_xy()
        if event.state == 'move':
            data_x, data_y = self.get_new_pan(viewer, x, y,
                                              ptype=self._pantype)
            viewer.panset_xy(data_x, data_y)

        elif event.state == 'down':
            self.pan_set_origin(viewer, x, y, data_x, data_y)
            self.pan_start(viewer, ptype=2)

        else:
            self.pan_stop(viewer)
        return True

    def ms_freepan(self, viewer, event, data_x, data_y):
        """A 'free' pan, where the image is panned by dragging the cursor
        towards the area you want to see in the image.  The entire image is
        pannable by dragging towards each corner of the window.
        """
        if not self.canpan:
            return True

        x, y = viewer.get_last_win_xy()
        if event.state == 'move':
            data_x, data_y = self.get_new_pan(viewer, x, y,
                                              ptype=self._pantype)
            viewer.panset_xy(data_x, data_y)

        elif event.state == 'down':
            self.pan_start(viewer, ptype=1)

        else:
            self.pan_stop(viewer)
        return True

    def ms_cutlo(self, viewer, event, data_x, data_y):
        """An interactive way to set the low cut level.
        """
        if not self.cancut:
            return True

        x, y = viewer.get_last_win_xy()
        if event.state == 'move':
            self._cutlow_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = viewer.get_cut_levels()

        else:
            viewer.onscreen_message(None)
        return True

    def ms_cuthi(self, viewer, event, data_x, data_y):
        """An interactive way to set the high cut level.
        """
        if not self.cancut:
            return True

        x, y = viewer.get_last_win_xy()
        if event.state == 'move':
            self._cuthigh_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = viewer.get_cut_levels()

        else:
            viewer.onscreen_message(None)
        return True

    def ms_cutall(self, viewer, event, data_x, data_y):
        """An interactive way to set the low AND high cut levels.
        """
        if not self.cancut:
            return True

        x, y = viewer.get_last_win_xy()
        if not viewer._originUpper:
            y = viewer._imgwin_ht - y
        if event.state == 'move':
            self._cutboth_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            image = viewer.get_image()
            self._loval, self._hival = self.autocuts.calc_cut_levels(image)

        else:
            viewer.onscreen_message(None)
        return True

    def ms_cut_auto(self, viewer, event, data_x, data_y, msg=True):
        return self.kp_cut_auto(viewer, event, data_x, data_y,
                                msg=msg)

    def ms_panset(self, viewer, event, data_x, data_y,
                  msg=True):
        """An interactive way to set the pan position.  The location
        (data_x, data_y) will be centered in the window.
        """
        if self.canpan and (event.state == 'down'):
            self._panset(viewer, data_x, data_y, msg=msg)
        return True

    #####  SCROLL ACTION CALLBACKS #####

    def sc_cuts_coarse(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it coarsely.
        """
        if self.cancut:
            self._adjust_cuts(viewer, event.direction, 0.01, msg=msg)
        return True

    def sc_cuts_fine(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it finely.
        """
        if self.cancut:
            self._adjust_cuts(viewer, event.direction, 0.001, msg=msg)
        return True

    def sc_zoom_old(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by the zoom steps configured under Preferences.
        """
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            rev = self.settings.get('zoom_scroll_reverse', False)
            direction = self.get_direction(event.direction, rev=rev)
            if direction == 'up':
                viewer.zoom_in()
            elif direction == 'down':
                viewer.zoom_out()
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                           delay=0.4)
        return True

    def sc_zoom(self, viewer, event, msg=True):
        return self.sc_zoom_coarse(viewer, event, msg=msg)

    def sc_zoom_coarse(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if self.canzoom:
            zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
            amount = zoom_accel * 0.20
            self._scale_image(viewer, event.direction, amount, msg=msg)
        return True

    def sc_zoom_fine(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if self.canzoom:
            zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
            amount = zoom_accel * 0.08
            self._scale_image(viewer, event.direction, 0.08, msg=msg)
        return True

    def sc_pan(self, viewer, event, msg=True):
        """Interactively pan the image by scrolling motion.
        """
        if not self.canpan:
            return True

        # User has "Pan Reverse" preference set?
        rev = self.settings.get('pan_reverse', False)
        direction = event.direction
        if rev:
            direction = math.fmod(direction + 180.0, 360.0)

        pan_accel = self.settings.get('scroll_pan_acceleration', 1.0)
        num_degrees = event.amount * pan_accel
        ang_rad = math.radians(90.0 - direction)

        # Calculate distance of pan amount, based on current scale
        wd, ht = viewer.get_data_size()
        # pageSize = min(wd, ht)
        ((x0, y0), (x1, y1), (x2, y2), (x3, y3)) = viewer.get_pan_rect()
        page_size = min(abs(x2 - x0), abs(y2 - y0))
        distance = (num_degrees / 360.0) * page_size
        self.logger.debug("angle=%f ang_rad=%f distance=%f" % (
            direction, ang_rad, distance))

        # Calculate new pan position
        pan_x, pan_y = viewer.get_pan()
        new_x = pan_x + math.cos(ang_rad) * distance
        new_y = pan_y + math.sin(ang_rad) * distance

        # cap pan position
        new_x = min(max(new_x, 0.0), wd)
        new_y = min(max(new_y, 0.0), ht)

        # Because pan position is reported +0.5
        #new_x, new_y = new_x - 0.5, new_y - 0.5
        #print "data x,y=%f,%f   new x, y=%f,%f" % (pan_x, pan_y, new_x, new_y)

        viewer.panset_xy(new_x, new_y)

        # For checking result
        #pan_x, pan_y = viewer.get_pan()
        #print "new pan x,y=%f, %f" % (pan_x, pan_y)
        return True

    def sc_pan_coarse(self, viewer, event, msg=True):
        event.amount = event.amount / 2.0
        return self.sc_pan(viewer, event, msg=msg)

    def sc_pan_fine(self, viewer, event, msg=True):
        event.amount = event.amount / 5.0
        return self.sc_pan(viewer, event, msg=msg)

    def sc_dist(self, viewer, event, msg=True):

        direction = self.get_direction(event.direction)
        self._cycle_dist(viewer, msg, direction=direction)
        return True

    def sc_cmap(self, viewer, event, msg=True):

        direction = self.get_direction(event.direction)
        self._cycle_cmap(viewer, msg, direction=direction)
        return True

    def sc_imap(self, viewer, event, msg=True):

        direction = self.get_direction(event.direction)
        self._cycle_imap(viewer, msg, direction=direction)
        return True

    ##### GESTURE ACTION CALLBACKS #####

    def gs_pinch(self, viewer, state, rot_deg, scale, msg=True):
        pinch_actions = self.settings.get('pinch_actions', [])
        if state == 'start':
            self._start_scale_x, self._start_scale_y = viewer.get_scale_xy()
            self._start_rot = viewer.get_rotation()
        else:
            msg_str = None
            if self.canzoom and ('zoom' in pinch_actions):
                scale_accel = self.settings.get('pinch_zoom_acceleration', 1.0)
                scale = scale * scale_accel
                scale_x, scale_y = (self._start_scale_x * scale,
                                    self._start_scale_y * scale)
                viewer.scale_to(scale_x, scale_y)
                msg_str = viewer.get_scale_text()
                msg = self.settings.get('msg_zoom', True)

            if self.canrotate and ('rotate' in pinch_actions):
                deg = self._start_rot - rot_deg
                rotate_accel = self.settings.get('pinch_rotate_acceleration', 1.0)
                deg = rotate_accel * deg
                viewer.rotate(deg)
                if msg_str is None:
                    msg_str = "Rotate: %.2f" % (deg)
                    msg = self.settings.get('msg_rotate', msg)

            if msg and (msg_str is not None):
                viewer.onscreen_message(msg_str, delay=0.4)
        return True

    def gs_pan(self, viewer, state, dx, dy):
        if not self.canpan:
            return True

        if state == 'move':
            scale_x, scale_y = viewer.get_scale_xy()
            delta_x = float(dx) / scale_x
            delta_y = float(dy) / scale_y

            data_x = self._start_panx + delta_x
            data_y = self._start_pany + delta_y
            viewer.panset_xy(data_x, data_y)

        elif state == 'start':
            self._start_panx, self._start_pany = viewer.get_pan()
            self.pan_start(viewer, ptype=2)

        else:
            self.pan_stop(viewer)
        return True

    def gs_rotate(self, viewer, state, rot_deg, msg=True):
        if state == 'start':
            self._start_rot = viewer.get_rotation()
        else:
            msg_str = None
            if self.canrotate:
                deg = self._start_rot - rot_deg
                rotate_accel = self.settings.get('pinch_rotate_acceleration', 1.0)
                deg = rotate_accel * deg
                viewer.rotate(deg)
                if msg_str is None:
                    msg_str = "Rotate: %.2f" % (deg)
                    msg = self.settings.get('msg_rotate', msg)

            if msg and (msg_str is not None):
                viewer.onscreen_message(msg_str, delay=0.4)
        return True

class UIEvent(object):
    pass

class KeyEvent(UIEvent):
    def __init__(self, key=None, state=None, mode=None, modifiers=None,
                 data_x=None, data_y=None, viewer=None):
        super(KeyEvent, self).__init__()
        self.key = key
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.data_x = data_x
        self.data_y = data_y
        self.viewer = viewer

class PointEvent(UIEvent):
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 data_x=None, data_y=None, viewer=None):
        super(PointEvent, self).__init__()
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.data_x = data_x
        self.data_y = data_y
        self.viewer = viewer

class ScrollEvent(UIEvent):
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 direction=None, amount=None, data_x=None, data_y=None,
                 viewer=None):
        super(ScrollEvent, self).__init__()
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.direction = direction
        self.amount = amount
        self.data_x = data_x
        self.data_y = data_y
        self.viewer = viewer

class BindingMapError(Exception):
    pass

class BindingMapper(Callback.Callbacks):
    """The BindingMapper class maps physical events (key presses, button
    clicks, mouse movement, etc) into logical events.  By registering for
    logical events, plugins and other event handling code doesn't need to
    care about the physical controls bindings.  The bindings can be changed
    and everything continues to work.
    """

    def __init__(self, logger, btnmap=None, mode_map=None, modifier_map=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger

        # For event mapping
        self.eventmap = {}

        self._kbdmode = None
        self._kbdmode_types = ('held', 'oneshot', 'locked')
        self._kbdmode_type = 'held'
        self._kbdmode_type_default = 'oneshot'
        self._delayed_reset = False
        self._modifiers = frozenset([])

        # Set up button mapping
        if btnmap is None:
            btnmap = { 0x1: 'cursor', 0x2: 'wheel', 0x4: 'draw' }
        self.btnmap = btnmap
        self._button = 0

        # Set up modifier mapping
        if modifier_map is None:
            self.modifier_map = {}
            for keyname in ('shift_l', 'shift_r'):
                self.add_modifier(keyname, 'shift')
            for keyname in ('control_l', 'control_r'):
                self.add_modifier(keyname, 'ctrl')
            for keyname in ('meta_right',):
                self.add_modifier(keyname, 'meta')
        else:
            self.modifier_map = mode_map

        # Set up mode mapping
        if mode_map is None:
            self.mode_map = {}
        else:
            self.mode_map = mode_map

        self._empty_set = frozenset([])

        # For callbacks
        for name in ('mode-set', ):
            self.enable_callback(name)


    def add_modifier(self, keyname, modname):
        bnch = Bunch.Bunch(name=modname)
        self.modifier_map[keyname] = bnch
        self.modifier_map['mod_%s' % modname] = bnch

    def get_modifiers(self):
        return set([bnch.name for keyname, bnch
                    in self.modifier_map.items()])

    def clear_modifier_map(self):
        self.modifier_map = {}

    def set_mode_map(self, mode_map):
        self.mode_map = mode_map

    def clear_mode_map(self):
        self.mode_map = {}

    def current_mode(self):
        return (self._kbdmode, self._kbdmode_type)

    def get_modes(self):
        return set([bnch.name for keyname, bnch in self.mode_map.items()])

    def add_mode(self, keyname, mode_name, mode_type='held', msg=None):
        if mode_type is not None:
            assert mode_type in self._kbdmode_types, \
                   ValueError("Bad mode type '%s': must be one of %s" % (
                mode_type, self._kbdmode_types))

        bnch = Bunch.Bunch(name=mode_name, type=mode_type, msg=msg)
        self.mode_map[keyname] = bnch
        self.mode_map['mode_%s' % mode_name] = bnch

    def set_mode(self, name, mode_type=None):
        if mode_type == None:
            mode_type = self._kbdmode_type_default
        assert mode_type in self._kbdmode_types, \
               ValueError("Bad mode type '%s': must be one of %s" % (
            mode_type, self._kbdmode_types))
        self._kbdmode = name
        if name is None:
            # like a reset_mode()
            mode_type = 'held'
            self._delayed_reset = False
        self._kbdmode_type = mode_type
        self.logger.info("set keyboard mode to '%s' type=%s" % (name, mode_type))
        self.make_callback('mode-set', self._kbdmode, self._kbdmode_type)

    def set_default_mode_type(self, mode_type):
        assert mode_type in self._kbdmode_types, \
               ValueError("Bad mode type '%s': must be one of %s" % (
            mode_type, self._kbdmode_types))
        self._kbdmode_type_default = mode_type

    def get_default_mode_type(self):
        return self._kbdmode_type_default

    def reset_mode(self, viewer):
        try:
            bnch = self.mode_map['mode_%s' % self._kbdmode]
        except:
            bnch = None
        self._kbdmode = None
        self._kbdmode_type = 'held'
        self._delayed_reset = False
        self.logger.info("set keyboard mode reset")
        # clear onscreen message, if any
        if (bnch is not None) and (bnch.msg is not None):
            viewer.onscreen_message(None)
        self.make_callback('mode-set', self._kbdmode, self._kbdmode_type)

    def clear_button_map(self):
        self.btnmap = {}

    def map_button(self, btncode, alias):
        """For remapping the buttons to different names. 'btncode' is a
        fixed button code and 'alias' is a logical name.
        """
        self.btnmap[btncode] = alias

    def get_buttons(self):
        return set([alias for keyname, alias in self.btnmap.items()])

    def clear_event_map(self):
        self.eventmap = {}

    def map_event(self, mode, modifiers, alias, eventname):
        self.eventmap[(mode, frozenset(tuple(modifiers)),
                       alias)] = Bunch.Bunch(name=eventname)

    def register_for_events(self, viewer):
        # Add callbacks for interesting events
        viewer.add_callback('motion', self.window_motion)
        viewer.add_callback('button-press', self.window_button_press)
        viewer.add_callback('button-release', self.window_button_release)
        viewer.add_callback('key-press', self.window_key_press)
        viewer.add_callback('key-release', self.window_key_release)
        ## viewer.add_callback('drag-drop', self.window_drag_drop)
        viewer.add_callback('scroll', self.window_scroll)
        ## viewer.add_callback('map', self.window_map)
        ## viewer.add_callback('focus', self.window_focus)
        ## viewer.add_callback('enter', self.window_enter)
        ## viewer.add_callback('leave', self.window_leave)

    def window_map(self, viewer):
        pass

    def window_focus(self, viewer, hasFocus):
        return True

    def window_enter(self, viewer):
        return True

    def window_leave(self, viewer):
        return True

    def window_key_press(self, viewer, keyname):
        self.logger.debug("keyname=%s" % (keyname))
        # Is this a modifer key?
        if keyname in self.modifier_map:
            bnch = self.modifier_map[keyname]
            self._modifiers = self._modifiers.union(set([bnch.name]))
            return True

        # Is this a mode key?
        elif keyname in self.mode_map:
            bnch = self.mode_map[keyname]
            if self._kbdmode_type == 'locked':
                if bnch.name == self._kbdmode:
                    self.reset_mode(viewer)
                return True

            if self._delayed_reset:
                if bnch.name == self._kbdmode:
                    self._delayed_reset = False
                return False

            # if there is not a mode active now,
            # activate this one
            if self._kbdmode is None:
                mode_type = bnch.type
                if mode_type == None:
                    mode_type = self._kbdmode_type_default
                self.set_mode(bnch.name, mode_type)
                if bnch.msg is not None:
                    viewer.onscreen_message(bnch.msg)
                return True

        try:
            # TEMP: hack to get around the issue of how keynames
            # are generated.
            if keyname == 'escape':
                idx = (None, self._empty_set, keyname)
            else:
                idx = (self._kbdmode, self._modifiers, keyname)
            emap = self.eventmap[idx]

        except KeyError:
            try:
                idx = (None, self._empty_set, keyname)
                emap = self.eventmap[idx]
            except KeyError:
                return False

        self.logger.debug("idx=%s" % (str(idx)))
        cbname = 'keydown-%s' % (emap.name)
        last_x, last_y = viewer.get_last_data_xy()

        event = KeyEvent(key=keyname, state='down', mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         data_x=last_x, data_y=last_y)
        return viewer.make_ui_callback(cbname, event, last_x, last_y)


    def window_key_release(self, viewer, keyname):
        self.logger.debug("keyname=%s" % (keyname))

        # Is this a modifer key?
        if keyname in self.modifier_map:
            bnch = self.modifier_map[keyname]
            self._modifiers = self._modifiers.difference(set([bnch.name]))
            return True

        try:
            idx = (self._kbdmode, self._modifiers, keyname)
            emap = self.eventmap[idx]

        except KeyError:
            try:
                idx = (None, self._empty_set, keyname)
                emap = self.eventmap[idx]
            except KeyError:
                emap = None

        # Is this a mode key?
        if keyname in self.mode_map:
            bnch = self.mode_map[keyname]
            if self._kbdmode == bnch.name:
                # <-- the current mode key is being released
                if bnch.type == 'held':
                    if self._button == 0:
                        # if no button is being held, then reset mode
                        self.reset_mode(viewer)
                    else:
                        self._delayed_reset = True
                return True

        # release mode if this is a oneshot mode
        ## if self._kbdmode_type == 'oneshot':
        ##     self.reset_mode(viewer)

        if emap is None:
            return False

        cbname = 'keyup-%s' % (emap.name)
        last_x, last_y = viewer.get_last_data_xy()

        event = KeyEvent(key=keyname, state='up', mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         data_x=last_x, data_y=last_y)
        return viewer.make_ui_callback(cbname, event, last_x, last_y)


    def window_button_press(self, viewer, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d btncode=%s" % (data_x, data_y,
                                                   hex(btncode)))
        self._button |= btncode
        button = self.btnmap[btncode]
        try:
            idx = (self._kbdmode, self._modifiers, button)
            emap = self.eventmap[idx]

        except KeyError:
            # no entry for this mode, try unmodified entry
            try:
                idx = (None, self._empty_set, button)
                emap = self.eventmap[idx]
            except KeyError:
                #self.logger.warn("No button map binding for %s" % (str(btncode)))
                return False

        self.logger.debug("Event map for %s" % (str(idx)))
        cbname = '%s-down' % (emap.name)
        self.logger.debug("making callback for %s (mode=%s)" % (
            cbname, self._kbdmode))

        event = PointEvent(button=button, state='down', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback(cbname, event, data_x, data_y)


    def window_motion(self, viewer, btncode, data_x, data_y):

        button = self.btnmap[btncode]
        try:
            idx = (self._kbdmode, self._modifiers, button)
            emap = self.eventmap[idx]
        except KeyError:
            # no entry for this mode, try unmodified entry
            try:
                idx = (None, self._empty_set, button)
                emap = self.eventmap[idx]
            except KeyError:
                return False

        self.logger.debug("Event map for %s" % (str(idx)))
        cbname = '%s-move' % (emap.name)

        event = PointEvent(button=button, state='move', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback(cbname, event, data_x, data_y)


    def window_button_release(self, viewer, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d button=%s" % (data_x, data_y,
                                                   hex(btncode)))
        self._button &= ~btncode
        button = self.btnmap[btncode]
        try:
            idx = (self._kbdmode, self._modifiers, button)
            # release mode if this is a oneshot mode
            if (self._kbdmode_type == 'oneshot') or (self._delayed_reset):
                self.reset_mode(viewer)
            emap = self.eventmap[idx]

        except KeyError:
            # no entry for this mode, try unmodified entry
            try:
                idx = (None, self._empty_set, button)
                emap = self.eventmap[idx]
            except KeyError:
                #self.logger.warn("No button map binding for %s" % (str(btncode)))
                return False

        self.logger.debug("Event map for %s" % (str(idx)))
        cbname = '%s-up' % (emap.name)

        event = PointEvent(button=button, state='up', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback(cbname, event, data_x, data_y)


    def window_scroll(self, viewer, direction, amount, data_x, data_y):
        try:
            idx = (self._kbdmode, self._modifiers, 'scroll')
            emap = self.eventmap[idx]

        except KeyError:
            # no entry for this mode, try unmodified entry
            try:
                idx = (None, self._empty_set, 'scroll')
                emap = self.eventmap[idx]
            except KeyError:
                return False

        cbname = '%s-scroll' % (emap.name)

        event = ScrollEvent(button='scroll', state='scroll', mode=self._kbdmode,
                            modifiers=self._modifiers, viewer=viewer,
                            direction=direction, amount=amount,
                            data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback(cbname, event)


#END
