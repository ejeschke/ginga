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

        if settings == None:
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
            mod_draw = ['meta_right'],
            
            # Define our custom modifiers
            dmod_draw = ['space', 'oneshot', None],
            dmod_cmapwarp = ['/', 'oneshot', None],
            #dmod_cutlo = ['<', 'oneshot', "Cut low"],
            #dmod_cuthi = ['>', 'oneshot', "Cut high"],
            dmod_cutall = ['.', 'oneshot', None],
            dmod_rotate = ['r', 'oneshot', None],
            dmod_freepan = ['q', 'oneshot', None],

            # KEYBOARD
            kp_zoom_in = ['+', '='],
            kp_zoom_out = ['-', '_'],
            kp_zoom = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            kp_zoom_inv = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
            kp_zoom_fit = ['backquote'],
            kp_autozoom_on = ['doublequote'],
            kp_autozoom_override = ['singlequote'],
            kp_dist = ['s'],
            kp_dist_reset = ['S'],
            kp_pan_set = ['p'],
            kp_center = ['c'],
            kp_cut_255 = ['A'],
            kp_cut_auto = ['a'],
            kp_autocuts_on = [':'],
            kp_autocuts_override = [';'],
            kp_cmap_restore = ['?'],
            kp_cmap_reset = [],
            kp_imap_reset = [],
            kp_flip_x = ['[', '{'],
            kp_flip_y = [']', '}'],
            kp_swap_xy = ['backslash', '|'],
            kp_rotate_reset = ['R'],
            kp_rotate_inc90 = ['e'],
            kp_rotate_dec90 = ['E'],
            kp_orient_lh = ['o'],
            kp_orient_rh = ['O'],
            kp_poly_add = ['x', 'draw+x'],
            kp_poly_del = ['z', 'draw+z'],
            kp_reset = ['escape'],
            
            # SCROLLING/WHEEL
            sc_pan = [],
            sc_pan_fine = [],
            sc_pan_coarse = [],
            sc_zoom = ['scroll'],
            sc_zoom_fine = ['shift+scroll'],
            sc_zoom_coarse = ['ctrl+scroll'],
            sc_contrast_fine = ['cutall+scroll'],
            sc_contrast_coarse = [],
            sc_dist = [],
            sc_cmap = ['cmapwarp+scroll'],
            sc_imap = [],
            
            scroll_pan_acceleration = 1.0,
            scroll_zoom_acceleration = 1.0,
            pan_reverse = False,
            zoom_scroll_reverse = False,
            
            # MOUSE/BUTTON
            ms_none = ['nobtn'],
            ms_cursor = ['left'],
            ms_wheel = [],
            ms_draw = ['draw+left', 'right'],
            
            ms_rotate = ['rotate+left'],
            ms_cmapwarp = ['cmapwarp+left', 'ctrl+right'],
            ms_cmaprest = ['ctrl+middle'],
            ms_pan = ['ctrl+left'],
            ms_freepan = ['freepan+left', 'middle'],
            ms_cutlo = ['cutlo+left'],
            ms_cuthi = ['cuthi+left'],
            ms_cutall = ['cutall+left'],
            ms_panset = ['shift+left'],
            
            # GESTURES (Qt version only)
            gs_pinch = [],
            pinch_actions = ['zoom'],
            pinch_zoom_acceleration = 1.0,
            pinch_rotate_acceleration = 1.0,
            )

    def window_map(self, fitsimage):
        self.to_default_mode(fitsimage)

    def set_bindings(self, fitsimage):
        fitsimage.add_callback('map', self.window_map)

        bindmap = fitsimage.get_bindmap()
        bindmap.clear_button_map()
        bindmap.clear_event_map()

        # Set up bindings
        self.setup_settings_events(fitsimage, bindmap)
        
    def set_modifier(self, fitsimage, name, modtype='oneshot'):
        bindmap = fitsimage.get_bindmap()
        bindmap.set_modifier(name, modtype=modtype)
        
    def parse_combo(self, combo):
        modifier, trigger = None, combo
        if '+' in combo:
            if combo.endswith('+'):
                if not combo.startswith('+'):
                    # special case: probably contains the keystroke '+'
                    idx = combo.index['+']
                    modifier, trigger = combo[:idx], combo[idx+1:]
            else:
                modifier, trigger = combo.split('+')
        return (modifier, trigger)

    def setup_settings_events(self, fitsimage, bindmap):

        d = self.settings.getDict()
        if len(d) == 0:
            self.initialize_settings(self.settings)
            d = self.settings.getDict()

        # First scan settings for buttons and modifiers
        bindmap.clear_modifier_map()

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
                modname = name[5:]
                keyname, modtype, msg = value
                bindmap.add_modifier(keyname, modname, modtype=modtype,
                                     msg=msg)
                    
        # Add events
        for name, value in d.items():
            if len(name) <= 3:
                continue

            pfx = name[:3]
            if not pfx in ('kp_', 'ms_', 'sc_', 'gs_'):
                continue
            
            evname = name[3:]
            for combo in value:
                modifier, trigger = self.parse_combo(combo)
                bindmap.map_event(modifier, trigger, evname)

            # Register for this symbolic event if we have a handler for it
            try:
                cb_method = getattr(self, name)

            except AttributeError:
                self.logger.warn("No method found matching '%s'" % (name))
                cb_method = None

            if pfx == 'kp_':
                # keyboard event
                event = 'keydown-%s' % (evname)
                fitsimage.enable_callback(event)
                if cb_method:
                    fitsimage.add_callback(event, cb_method)
            
            elif pfx == 'ms_':
                # mouse/button event
                for action in ('down', 'move', 'up'):
                    event = '%s-%s' % (evname, action)
                    fitsimage.enable_callback(event)
                    if cb_method:
                        fitsimage.add_callback(event, cb_method)

            elif pfx == 'sc_':
                # scrolling event
                event = '%s-scroll' % evname
                fitsimage.enable_callback(event)
                if cb_method:
                    fitsimage.add_callback(event, cb_method)

            elif pfx == 'gs_':
                if evname == 'pinch':
                    fitsimage.set_callback('pinch', cb_method)
                
    def reset(self, fitsimage):
        bindmap = fitsimage.get_bindmap()
        bindmap.reset_modifier(fitsimage)
        self.pan_stop(fitsimage)
        fitsimage.onscreen_message(None)

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
            fitsimage.enable(rotate=False, flip=True)
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

    def get_new_pan(self, fitsimage, win_x, win_y, ptype=1):

        if ptype == 1:
            # This is a "free pan", similar to dragging the "lens"
            # over the canvas.
            dat_wd, dat_ht = fitsimage.get_data_size()
            win_wd, win_ht = fitsimage.get_window_size()

            if (win_x >= win_wd):
                win_x = win_wd - 1
            if (win_y >= win_ht):
                win_y = win_ht - 1

            # Figure out data x,y based on percentage of X axis
            # and Y axis
            off_x, off_y = fitsimage.canvas2offset(win_x, win_y)
            max_x, max_y = fitsimage.canvas2offset(win_wd, win_ht)
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
            if self._start_x == None:
                # user has not held the mouse button yet
                # return current pan values
                return (self._start_panx, self._start_pany)

            scale_x, scale_y = fitsimage.get_scale_xy()
            off_x, off_y = fitsimage.canvas2offset(win_x, win_y)
            delta_x = float(self._start_x - off_x) / scale_x
            delta_y = float(self._start_y - off_y) / scale_y
            
            data_x = self._start_panx + delta_x
            data_y = self._start_pany + delta_y
            
        return (data_x, data_y)

    def _panset(self, fitsimage, data_x, data_y, msg=True, redraw=True):
        try:
            msg = self.settings.get('msg_panset', msg)
            if msg:
                fitsimage.onscreen_message("Pan position set", delay=0.4)

            res = fitsimage.panset_xy(data_x, data_y, redraw=redraw)
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
        
    def _tweak_colormap(self, fitsimage, x, y, mode):
        win_wd, win_ht = fitsimage.get_window_size()

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

        fitsimage.scaleNshift_cmap(scale_pct, shift_pct)

    def _cutlow_pct(self, fitsimage, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = fitsimage.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = fitsimage.get_cut_levels()
        loval = loval + (pct * spread)
        if msg:
            fitsimage.onscreen_message("Cut low: %.4f" % (loval),
                                   redraw=False)
        fitsimage.cut_levels(loval, hival, redraw=True)

    def _cutlow_xy(self, fitsimage, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = fitsimage.get_window_size()
        pct = float(x) / float(win_wd)
        image = fitsimage.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = fitsimage.get_cut_levels()
        loval = minval + (pct * spread)
        if msg:
            fitsimage.onscreen_message("Cut low: %.4f" % (loval),
                                       redraw=False)
        fitsimage.cut_levels(loval, hival, redraw=True)

    def _cuthigh_pct(self, fitsimage, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = fitsimage.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = fitsimage.get_cut_levels()
        hival = hival - (pct * spread)
        if msg:
            fitsimage.onscreen_message("Cut high: %.4f" % (hival),
                                       redraw=False)
        fitsimage.cut_levels(loval, hival, redraw=True)

    def _cuthigh_xy(self, fitsimage, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = fitsimage.get_window_size()
        pct = 1.0 - (float(x) / float(win_wd))
        image = fitsimage.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = fitsimage.get_cut_levels()
        hival = maxval - (pct * spread)
        if msg:
            fitsimage.onscreen_message("Cut high: %.4f" % (hival),
                                       redraw=False)
        fitsimage.cut_levels(loval, hival, redraw=True)

    def _cutboth_xy(self, fitsimage, x, y, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        win_wd, win_ht = fitsimage.get_window_size()
        xpct = 1.0 - (float(x) / float(win_wd))
        #ypct = 1.0 - (float(y) / float(win_ht))
        ypct = (float(win_ht - y) / float(win_ht))
        spread = self._hival - self._loval
        hival = self._hival - (xpct * spread)
        loval = self._loval + (ypct * spread)
        if msg:
            fitsimage.onscreen_message("Cut low: %.4f  high: %.4f" % (
                loval, hival), redraw=False)
        fitsimage.cut_levels(loval, hival, redraw=True)

    def _cut_pct(self, fitsimage, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = fitsimage.get_image()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = fitsimage.get_cut_levels()
        loval = loval + (pct * spread)
        hival = hival - (pct * spread)
        if msg:
            fitsimage.onscreen_message("Cut low: %.4f  high: %.4f" % (
                loval, hival), delay=1.0, redraw=False)
        fitsimage.cut_levels(loval, hival, redraw=True)

    def _adjust_contrast(self, fitsimage, direction, pct, msg=True):
        direction = self.get_direction(direction)
        if direction == 'up':
            self._cut_pct(fitsimage, pct, msg=msg)
        elif direction == 'down':
            self._cut_pct(fitsimage, -pct, msg=msg)

    def _scale_image(self, fitsimage, direction, factor, msg=True):
        msg = self.settings.get('msg_zoom', msg)
        rev = self.settings.get('zoom_scroll_reverse', False)
        scale_x, scale_y = fitsimage.get_scale_xy()
        direction = self.get_direction(direction, rev=rev)
        if direction == 'up':
                mult = 1.0 + factor
        elif direction == 'down':
                mult = 1.0 - factor
        scale_x, scale_y = scale_x * mult, scale_y * mult
        fitsimage.scale_to(scale_x, scale_y)
        if msg:
            fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                       delay=0.4)

    def _cycle_dist(self, fitsimage, msg, direction='down'):
        if self.cancmap:
            msg = self.settings.get('msg_dist', msg)
            rgbmap = fitsimage.get_rgbmap()
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
                fitsimage.onscreen_message("Color dist: %s" % (algname),
                                           delay=1.0)

    def _reset_dist(self, fitsimage, msg):
        if self.cancmap:
            msg = self.settings.get('msg_dist', msg)
            rgbmap = fitsimage.get_rgbmap()
            algname = 'linear'
            rgbmap.set_hash_algorithm(algname)
            if msg:
                fitsimage.onscreen_message("Color dist: %s" % (algname),
                                           delay=1.0)

    def _cycle_cmap(self, fitsimage, msg, direction='down'):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            rgbmap = fitsimage.get_rgbmap()
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
                fitsimage.onscreen_message("Color map: %s" % (cmapname),
                                           delay=1.0)

    def _reset_cmap(self, fitsimage, msg):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            rgbmap = fitsimage.get_rgbmap()
            # default
            cmapname = 'ramp'
            rgbmap.set_cmap(cmap.get_cmap(cmapname))
            if msg:
                fitsimage.onscreen_message("Color map: %s" % (cmapname),
                                           delay=1.0)

    def _cycle_imap(self, fitsimage, msg, direction='down'):
        if self.cancmap:
            msg = self.settings.get('msg_imap', msg)
            rgbmap = fitsimage.get_rgbmap()
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
                fitsimage.onscreen_message("Intensity map: %s" % (imapname),
                                           delay=1.0)

    def _reset_imap(self, fitsimage, msg):
        if self.cancmap:
            msg = self.settings.get('msg_imap', msg)
            rgbmap = fitsimage.get_rgbmap()
            # default
            imapname = 'ramp'
            rgbmap.set_imap(imap.get_imap(imapname))
            if msg:
                fitsimage.onscreen_message("Intensity map: %s" % (imapname),
                                           delay=1.0)

    def _rotate_xy(self, fitsimage, x, y, msg=True):
        msg = self.settings.get('msg_rotate', msg)
        win_wd, win_ht = fitsimage.get_window_size()
        pct = float(x) / float(win_wd)
        deg = 360.0 * pct
        if msg:
            fitsimage.onscreen_message("Rotate: %.2f" % (deg),
                                       redraw=False)
        fitsimage.rotate(deg)

    def _rotate_inc(self, fitsimage, inc_deg, msg=True):
        msg = self.settings.get('msg_rotate_inc', msg)
        cur_rot_deg = fitsimage.get_rotation()
        rot_deg = math.fmod(cur_rot_deg + inc_deg, 360.0)
        fitsimage.rotate(rot_deg)
        if msg:
            fitsimage.onscreen_message("Rotate Inc: (%.2f) %.2f" % (
                inc_deg, rot_deg), delay=1.0)

    def _orient(self, fitsimage, righthand=False, msg=True):
        msg = self.settings.get('msg_orient', msg)
        image = fitsimage.get_image()

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
            
        fitsimage.transform(xflip, False, False)
        fitsimage.rotate(degn)
        if msg:
            fitsimage.onscreen_message("Orient: rot=%.2f flipx=%s" % (
                degn, str(xflip)), delay=1.0)

    def to_default_mode(self, fitsimage):
        self._ispanning = False
        fitsimage.switch_cursor('pick')
        
    def pan_start(self, fitsimage, ptype=1):
        # If already panning then ignore multiple keystrokes
        if self._ispanning:
            return
        self._pantype = ptype
        fitsimage.switch_cursor('pan')
        self._ispanning = True
        
    def pan_set_origin(self, fitsimage, win_x, win_y, data_x, data_y):
        self._start_x, self._start_y = fitsimage.canvas2offset(win_x, win_y)
        self._start_panx, self._start_pany = fitsimage.get_pan()
        
    def pan_stop(self, fitsimage):
        self._ispanning = False
        self._start_x = None
        self._pantype = 1
        self.to_default_mode(fitsimage)

    def restore_colormap(self, fitsimage, msg=True):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = fitsimage.get_rgbmap()
        rgbmap.reset_sarr()
        if msg:
            fitsimage.onscreen_message("Restored color map", delay=0.5)
        return True


    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_pan_set(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canpan:
            self._panset(fitsimage, data_x, data_y, redraw=True,
                         msg=msg)
        return True

    def kp_center(self, fitsimage, keyname, data_x, data_y):
        if self.canpan:
            fitsimage.center_image()
        return True

    def kp_zoom_out(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            fitsimage.zoom_out()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_in(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            fitsimage.zoom_in()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            keylist = self.settings.get('kp_zoom')
            zoomval = (keylist.index(keyname) + 1)
            fitsimage.zoom_to(zoomval)
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_inv(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            keylist = self.settings.get('kp_zoom_inv')
            zoomval = - (keylist.index(keyname) + 1)
            fitsimage.zoom_to(zoomval)
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_fit(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            fitsimage.zoom_fit()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_autozoom_on(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            fitsimage.enable_autozoom('on')
            if msg:
                fitsimage.onscreen_message('Autozoom On', delay=1.0)
        return True

    def kp_autozoom_override(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            fitsimage.enable_autozoom('override')
            if msg:
                fitsimage.onscreen_message('Autozoom Override', delay=1.0)
        return True
            
    def kp_cut_255(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            fitsimage.cut_levels(0.0, 255.0, no_reset=True)
        return True

    def kp_cut_auto(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            if msg:
                fitsimage.onscreen_message("Auto cut levels", delay=1.0)
            fitsimage.auto_levels()
        return True

    def kp_autocuts_on(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            fitsimage.enable_autocuts('on')
            if msg:
                fitsimage.onscreen_message('Autocuts On', delay=1.0)
        return True

    def kp_autocuts_override(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            fitsimage.enable_autocuts('override')
            if msg:
                fitsimage.onscreen_message('Autocuts Override', delay=1.0)
        return True

    def kp_cmap_restore(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            self.restore_colormap(fitsimage, msg=msg)
        return True

    def kp_flip_x(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = fitsimage.get_transforms()
            if keyname == '[':
                flipx = not flipX
            else:
                flipx = False
            fitsimage.transform(flipx, flipY, swapXY)
            if msg:
                fitsimage.onscreen_message("Flip X=%s" % flipx, delay=1.0)
        return True

    def kp_flip_y(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = fitsimage.get_transforms()
            if keyname == ']':
                flipy = not flipY
            else:
                flipy = False
            fitsimage.transform(flipX, flipy, swapXY)
            if msg:
                fitsimage.onscreen_message("Flip Y=%s" % flipy, delay=1.0)
        return True

    def kp_swap_xy(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canflip:
            msg = self.settings.get('msg_transform', msg)
            flipX, flipY, swapXY = fitsimage.get_transforms()
            if keyname == 'backslash':
                swapxy = not swapXY
            else:
                swapxy = False
            fitsimage.transform(flipX, flipY, swapxy)
            if msg:
                fitsimage.onscreen_message("Swap XY=%s" % swapxy, delay=1.0)
        return True

    def kp_dist(self, fitsimage, keyname, data_x, data_y, msg=True):
        self._cycle_dist(fitsimage, msg)
        return True

    def kp_dist_reset(self, fitsimage, keyname, data_x, data_y, msg=True):
        self._reset_dist(fitsimage, msg)
        return True

    def kp_cmap_reset(self, fitsimage, keyname, data_x, data_y, msg=True):
        self._reset_cmap(fitsimage, msg)
        return True

    def kp_imap_reset(self, fitsimage, keyname, data_x, data_y, msg=True):
        self._reset_imap(fitsimage, msg)
        return True

    def kp_rotate_reset(self, fitsimage, keyname, data_x, data_y):
        if self.canrotate:
            fitsimage.rotate(0.0)
        return True

    def kp_rotate_inc90(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canrotate:
            self._rotate_inc(fitsimage, 90.0, msg=msg)
        return True

    def kp_rotate_dec90(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canrotate:
            self._rotate_inc(fitsimage, -90.0, msg=msg)
        return True

    def kp_orient_lh(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canrotate:
            self._orient(fitsimage, righthand=False, msg=msg)
        return True

    def kp_orient_rh(self, fitsimage, keyname, data_x, data_y,
                            msg=True):
        if self.canrotate:
            self._orient(fitsimage, righthand=True, msg=msg)
        return True

    def kp_reset(self, fitsimage, keyname, data_x, data_y):
        self.reset(fitsimage)
        return True

    #####  MOUSE ACTION CALLBACKS #####

    # def ms_none(self, fitsimage, action, data_x, data_y):
    #     return False

    # def ms_cursor(self, fitsimage, action, data_x, data_y):
    #     return False

    # def ms_wheel(self, fitsimage, action, data_x, data_y):
    #     return False

    # def ms_draw(self, fitsimage, action, data_x, data_y):
    #     return False

    def ms_rotate(self, fitsimage, action, data_x, data_y, msg=True):
        """Rotate the image by dragging the cursor left or right.
        """
        if not self.canrotate:
            return True
        msg = self.settings.get('msg_rotate', msg)

        x, y = fitsimage.get_last_win_xy()
        if action == 'move':
            self._rotate_xy(fitsimage, x, y)
            
        elif action == 'down':
            if msg:
                fitsimage.onscreen_message("Rotate (drag mouse L-R)",
                                           delay=1.0)
            self._start_x = x
            
        else:
            fitsimage.onscreen_message(None)
        return True


    def ms_cmapwarp(self, fitsimage, action, data_x, data_y, msg=True):
        """Shift the colormap by dragging the cursor left or right.
        Stretch the colormap by dragging the cursor up or down.
        """
        if not self.cancmap:
            return True
        msg = self.settings.get('msg_cmap', msg)
        
        x, y = fitsimage.get_last_win_xy()
        if not fitsimage._originUpper:
            y = fitsimage._imgwin_ht - y
        if action == 'move':
            self._tweak_colormap(fitsimage, x, y, 'preview')
            
        elif action == 'down':
            self._start_x, self._start_y = x, y
            if msg:
                fitsimage.onscreen_message("Shift and stretch colormap (drag mouse)",
                                           delay=1.0)
        else:
            fitsimage.onscreen_message(None)
        return True

            
    def ms_cmaprest(self, fitsimage, action, data_x, data_y, msg=True):
        """An interactive way to restore the colormap settings after
        a warp operation.
        """
        if self.cancmap and (action == 'down'):
            self.restore_colormap(fitsimage, msg=msg)
            return True


    def ms_pan(self, fitsimage, action, data_x, data_y):
        """A 'drag' or proportional pan, where the image is panned by
        'dragging the canvas' up or down.  The amount of the pan is
        proportionate to the length of the drag.
        """
        if not self.canpan:
            return True
        
        x, y = fitsimage.get_last_win_xy()
        if action == 'move':
            data_x, data_y = self.get_new_pan(fitsimage, x, y,
                                              ptype=self._pantype)
            fitsimage.panset_xy(data_x, data_y, redraw=True)
            
        elif action == 'down':
            self.pan_set_origin(fitsimage, x, y, data_x, data_y)
            self.pan_start(fitsimage, ptype=2)

        else:
            self.pan_stop(fitsimage)
        return True
            
    def ms_freepan(self, fitsimage, action, data_x, data_y):
        """A 'free' pan, where the image is panned by dragging the cursor
        towards the area you want to see in the image.  The entire image is
        pannable by dragging towards each corner of the window.
        """
        if not self.canpan:
            return True
        
        x, y = fitsimage.get_last_win_xy()
        if action == 'move':
            data_x, data_y = self.get_new_pan(fitsimage, x, y,
                                              ptype=self._pantype)
            fitsimage.panset_xy(data_x, data_y, redraw=True)
            
        elif action == 'down':
            self.pan_start(fitsimage, ptype=1)

        else:
            self.pan_stop(fitsimage)
        return True
            
    def ms_cutlo(self, fitsimage, action, data_x, data_y):
        """An interactive way to set the low cut level.
        """
        if not self.cancut:
            return True
        
        x, y = fitsimage.get_last_win_xy()
        if action == 'move':
            self._cutlow_xy(fitsimage, x, y)
            
        elif action == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = fitsimage.get_cut_levels()

        else:
            fitsimage.onscreen_message(None)
        return True
            
    def ms_cuthi(self, fitsimage, action, data_x, data_y):
        """An interactive way to set the high cut level.
        """
        if not self.cancut:
            return True
        
        x, y = fitsimage.get_last_win_xy()
        if action == 'move':
            self._cuthigh_xy(fitsimage, x, y)
            
        elif action == 'down':
            self._start_x, self._start_y = x, y
            self._loval, self._hival = fitsimage.get_cut_levels()

        else:
            fitsimage.onscreen_message(None)
        return True
            
    def ms_cutall(self, fitsimage, action, data_x, data_y):
        """An interactive way to set the low AND high cut levels.
        """
        if not self.cancut:
            return True
        
        x, y = fitsimage.get_last_win_xy()
        if not fitsimage._originUpper:
            y = fitsimage._imgwin_ht - y
        if action == 'move':
            self._cutboth_xy(fitsimage, x, y)
            
        elif action == 'down':
            self._start_x, self._start_y = x, y
            image = fitsimage.get_image()
            self._loval, self._hival = self.autocuts.calc_cut_levels(image)

        else:
            fitsimage.onscreen_message(None)
        return True
            
    def ms_panset(self, fitsimage, action, data_x, data_y,
                  msg=True):
        """An interactive way to set the pan position.  The location
        (data_x, data_y) will be centered in the window.
        """
        if self.canpan and (action == 'down'):
            self._panset(fitsimage, data_x, data_y, redraw=True,
                         msg=msg)
        return True

    #####  SCROLL ACTION CALLBACKS #####

    def sc_contrast_coarse(self, fitsimage, direction, amount, data_x, data_y,
                           msg=True):
        """Adjust contrast interactively by setting the low AND high cut
        levels.  This function adjusts it coarsely.
        """
        if self.cancut:
            self._adjust_contrast(fitsimage, direction, 0.01, msg=msg)
        return True

    def sc_contrast_fine(self, fitsimage, direction, amount, data_x, data_y,
                         msg=True):
        """Adjust contrast interactively by setting the low AND high cut
        levels.  This function adjusts it finely.
        """
        if self.cancut:
            self._adjust_contrast(fitsimage, direction, 0.001, msg=msg)
        return True

    def sc_zoom(self, fitsimage, direction, amount, data_x, data_y, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by the zoom steps configured under Preferences.
        """
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            rev = self.settings.get('zoom_scroll_reverse', False)
            direction = self.get_direction(direction, rev=rev)
            if direction == 'up':
                fitsimage.zoom_in()
            elif direction == 'down':
                fitsimage.zoom_out()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=0.4)
        return True

    def sc_zoom_coarse(self, fitsimage, direction, amount, data_x, data_y,
                       msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if self.canzoom:
            zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
            amount = zoom_accel * 0.20
            self._scale_image(fitsimage, direction, amount, msg=msg)
        return True

    def sc_zoom_fine(self, fitsimage, direction, amount, data_x, data_y,
                     msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if self.canzoom:
            zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
            amount = zoom_accel * 0.08
            self._scale_image(fitsimage, direction, 0.08, msg=msg)
        return True

    def sc_pan(self, fitsimage, direction, amount, data_x, data_y, msg=True):
        """Interactively pan the image by scrolling motion.
        """
        if not self.canpan:
            return True

        # User has "Pan Reverse" preference set?
        rev = self.settings.get('pan_reverse', False)
        if rev:
            direction = math.fmod(direction + 180.0, 360.0)

        pan_accel = self.settings.get('scroll_pan_acceleration', 1.0)
        num_degrees = amount * pan_accel
        ang_rad = math.radians(90.0 - direction)

        # Calculate distance of pan amount, based on current scale
        wd, ht = fitsimage.get_data_size()
        # pageSize = min(wd, ht)
        ((x0, y0), (x1, y1), (x2, y2), (x3, y3)) = fitsimage.get_pan_rect()
        page_size = min(abs(x2 - x0), abs(y2 - y0))
        distance = (num_degrees / 360.0) * page_size
        self.logger.debug("angle=%f ang_rad=%f distance=%f" % (
            direction, ang_rad, distance))
        
        # Calculate new pan position
        pan_x, pan_y = fitsimage.get_pan()
        new_x = pan_x + math.cos(ang_rad) * distance
        new_y = pan_y + math.sin(ang_rad) * distance

        # cap pan position
        new_x = min(max(new_x, 0.0), wd)
        new_y = min(max(new_y, 0.0), ht)
        
        # Because pan position is reported +0.5
        new_x, new_y = new_x - 0.5, new_y - 0.5
        #print "data x,y=%f,%f   new x, y=%f,%f" % (pan_x, pan_y, new_x, new_y)

        fitsimage.panset_xy(new_x, new_y, redraw=True)

        # For checking result
        #pan_x, pan_y = fitsimage.get_pan()
        #print "new pan x,y=%f, %f" % (pan_x, pan_y)
        return True

    def sc_pan_coarse(self, fitsimage, direction, amount, data_x, data_y,
                      msg=True):
        amount = amount / 2.0
        return self.sc_pan(fitsimage, direction, amount, data_x, data_y,
                           msg=msg)

    def sc_pan_fine(self, fitsimage, direction, amount, data_x, data_y,
                      msg=True):
        amount = amount / 5.0
        return self.sc_pan(fitsimage, direction, amount, data_x, data_y,
                           msg=msg)

    def sc_dist(self, fitsimage, direction, amount, data_x, data_y,
                   msg=True):

        direction = self.get_direction(direction)
        self._cycle_dist(fitsimage, msg, direction=direction)
        return True

    def sc_cmap(self, fitsimage, direction, amount, data_x, data_y,
                    msg=True):

        direction = self.get_direction(direction)
        self._cycle_cmap(fitsimage, msg, direction=direction)
        return True

    def sc_imap(self, fitsimage, direction, amount, data_x, data_y,
                    msg=True):

        direction = self.get_direction(direction)
        self._cycle_imap(fitsimage, msg, direction=direction)
        return True

    ##### GESTURE ACTION CALLBACKS #####

    def gs_pinch(self, fitsimage, state, rot_deg, scale, msg=True):
        pinch_actions = self.settings.get('pinch_actions', [])
        if state == 'start':
            self._start_scale_x, self._start_scale_y = fitsimage.get_scale_xy()
            self._start_rot = fitsimage.get_rotation()
        else:
            msg_str = None
            if self.canzoom and ('zoom' in pinch_actions):
                scale_accel = self.settings.get('pinch_zoom_acceleration', 1.0)
                scale = scale * scale_accel
                scale_x, scale_y = (self._start_scale_x * scale,
                                    self._start_scale_y * scale)
                fitsimage.scale_to(scale_x, scale_y, redraw=False)
                msg_str = fitsimage.get_scale_text()
                msg = self.settings.get('msg_zoom', True)
                
            if self.canrotate and ('rotate' in pinch_actions):
                deg = self._start_rot - rot_deg
                rotate_accel = self.settings.get('pinch_rotate_acceleration', 1.0)
                deg = rotate_accel * deg
                fitsimage.rotate(deg)
                if msg_str == None:
                    msg_str = "Rotate: %.2f" % (deg)
                    msg = self.settings.get('msg_rotate', msg)
                
            if msg and (msg_str != None):
                fitsimage.onscreen_message(msg_str, delay=0.4)
        return True        

    def gs_pan(self, fitsimage, state, dx, dy):
        if not self.canpan:
            return True
        
        x, y = fitsimage.get_last_win_xy()
        if state == 'move':
            data_x, data_y = self.get_new_pan(fitsimage, x, y,
                                              ptype=self._pantype)
            fitsimage.panset_xy(data_x, data_y, redraw=True)
            
        elif state == 'start':
            data_x, data_y = fitsimage.get_last_data_xy()
            self.pan_set_origin(fitsimage, x, y, data_x, data_y)
            self.pan_start(fitsimage, ptype=2)

        else:
            self.pan_stop(fitsimage)
        return True
        

class BindingMapError(Exception):
    pass

class BindingMapper(Callback.Callbacks):
    """The BindingMapper class maps physical events (key presses, button
    clicks, mouse movement, etc) into logical events.  By registering for
    logical events, plugins and other event handling code doesn't need to
    care about the physical controls bindings.  The bindings can be changed
    and everything continues to work.
    """

    def __init__(self, logger, btnmap=None, modmap=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger
        
        # For event mapping
        self.eventmap = {}

        self._kbdmod = None
        self._kbdmod_types = ('held', 'oneshot', 'locked')
        self._kbdmod_type = 'held'
        self._delayed_reset = False

        # Set up button mapping
        if btnmap == None:
            btnmap = { 0x1: 'cursor', 0x2: 'wheel', 0x4: 'draw' }
        self.btnmap = btnmap
        self._button = 0

        # Set up modifier mapping
        if modmap == None:
            self.modmap = {}
            for keyname in ('shift_l', 'shift_r'):
                self.add_modifier(keyname, 'shift')
            for keyname in ('control_l', 'control_r'):
                self.add_modifier(keyname, 'ctrl')
            for keyname in ('meta_right',):
                self.add_modifier(keyname, 'draw')
        else:
            self.modmap = modmap

        # For callbacks
        for name in ('mode-set', ):
            self.enable_callback(name)

    def set_modifier_map(self, modmap):
        self.modmap = modmap
        
    def clear_modifier_map(self):
        self.modmap = {}

    def current_modifier(self):
        return self._kbdmod

    def get_modifiers(self):
        res = set([])
        for keyname, bnch in self.modmap.items():
            res.add(bnch.name)
        return res

    def add_modifier(self, keyname, modname, modtype='held', msg=None):
        assert modtype in self._kbdmod_types, \
               ValueError("Bad modifier type '%s': must be one of %s" % (
            modtype, self._kbdmod_types))

        bnch = Bunch.Bunch(name=modname, type=modtype, msg=msg)
        self.modmap[keyname] = bnch
        self.modmap['mod_%s' % modname] = bnch
        
    def set_modifier(self, name, modtype='oneshot'):
        assert modtype in self._kbdmod_types, \
               ValueError("Bad modifier type '%s': must be one of %s" % (
            modtype, self._kbdmod_types))
        self._kbdmod = name
        self._kbdmod_type = modtype
        self.make_callback('mode-set', self._kbdmod, self._kbdmod_type)
        
    def reset_modifier(self, fitsimage):
        try:
            bnch = self.modmap['mod_%s' % self._kbdmod]
        except:
            bnch = None
        self._kbdmod = None
        self._kbdmod_type = 'held'
        self._delayed_reset = False
        # clear onscreen message, if any
        if (bnch != None) and (bnch.msg != None):
            fitsimage.onscreen_message(None)
        self.make_callback('mode-set', self._kbdmod, self._kbdmod_type)
        
    def clear_button_map(self):
        self.btnmap = {}
        
    def map_button(self, btncode, alias):
        """For remapping the buttons to different names. 'btncode' is a
        fixed button code and 'alias' is a logical name.
        """
        self.btnmap[btncode] = alias

    def get_buttons(self):
        res = set([])
        for keyname, alias in self.btnmap.items():
            res.add(alias)
        return res
        
    def clear_event_map(self):
        self.eventmap = {}
        
    def map_event(self, modifier, alias, eventname):
        self.eventmap[(modifier, alias)] = Bunch.Bunch(name=eventname)
        
    def register_for_events(self, fitsimage):
        # Add callbacks for interesting events
        fitsimage.add_callback('motion', self.window_motion)
        fitsimage.add_callback('button-press', self.window_button_press)
        fitsimage.add_callback('button-release', self.window_button_release)
        fitsimage.add_callback('key-press', self.window_key_press)
        fitsimage.add_callback('key-release', self.window_key_release)
        ## fitsimage.add_callback('drag-drop', self.window_drag_drop)
        fitsimage.add_callback('scroll', self.window_scroll)
        ## fitsimage.add_callback('map', self.window_map)
        ## fitsimage.add_callback('focus', self.window_focus)
        ## fitsimage.add_callback('enter', self.window_enter)
        ## fitsimage.add_callback('leave', self.window_leave)

    def window_map(self, fitsimage):
        pass

    def window_focus(self, fitsimage, hasFocus):
        return True
            
    def window_enter(self, fitsimage):
        return True
    
    def window_leave(self, fitsimage):
        return True
    
    def window_key_press(self, fitsimage, keyname):
        self.logger.debug("keyname=%s" % (keyname))
        # Is this a modifier key?
        if keyname in self.modmap:
            bnch = self.modmap[keyname]
            if self._kbdmod_type == 'locked':
                if bnch.name == self._kbdmod:
                    self.reset_modifier(fitsimage)
                return True
                
            if self._delayed_reset:
                if bnch.name == self._kbdmod:
                    self._delayed_reset = False
                return False

            # if there is not a modifier active now,
            # activate this one
            if self._kbdmod == None:
                self.set_modifier(bnch.name, bnch.type)
                if bnch.msg != None:
                    fitsimage.onscreen_message(bnch.msg)
                return True
        
        try:
            # TEMP: hack to get around the issue of how keynames
            # are generated. This assumes standard modifiers are
            # mapped to names "shift" and "ctrl"
            if (self._kbdmod in ('shift', 'ctrl')) or (keyname == 'escape'):
                idx = (None, keyname)
            else:
                idx = (self._kbdmod, keyname)

            self.logger.debug("idx=%s" % (str(idx)))
            emap = self.eventmap[idx]

        except KeyError:
            return False

        cbname = 'keydown-%s' % (emap.name)
        last_x, last_y = fitsimage.get_last_data_xy()

        return fitsimage.make_callback(cbname, keyname, last_x, last_y)
            

    def window_key_release(self, fitsimage, keyname):
        self.logger.debug("keyname=%s" % (keyname))

        try:
            idx = (self._kbdmod, keyname)
            emap = self.eventmap[idx]

        except KeyError:
            emap = None

        # Is this a modifier key?
        if keyname in self.modmap:
            bnch = self.modmap[keyname]
            if self._kbdmod == bnch.name:
                # <-- the current modifier key is being released
                if bnch.type == 'held':
                    if self._button == 0:
                        # if no button is being held, then reset modifier
                        self.reset_modifier(fitsimage)
                    else:
                        self._delayed_reset = True
                return True

        # release modifier if this is a oneshot modifier
        ## if self._kbdmod_type == 'oneshot':
        ##     self.reset_modifier(fitsimage)

        if emap == None:
            return False
        
        cbname = 'keyup-%s' % (emap.name)
        last_x, last_y = fitsimage.get_last_data_xy()

        return fitsimage.make_callback(cbname, keyname, last_x, last_y)

        
    def window_button_press(self, fitsimage, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d btncode=%s" % (data_x, data_y,
                                                   hex(btncode)))
        try:
            self._button |= btncode
            button = self.btnmap[btncode]
            idx = (self._kbdmod, button)
            self.logger.debug("Event map for %s" % (str(idx)))
            emap = self.eventmap[idx]

        except KeyError:
            #self.logger.warn("No button map binding for %s" % (str(btncode)))
            return False
        
        cbname = '%s-down' % (emap.name)
        self.logger.debug("making callback for %s (mod=%s)" % (
            cbname, self._kbdmod))
        return fitsimage.make_callback(cbname, 'down', data_x, data_y)


    def window_motion(self, fitsimage, btncode, data_x, data_y):
        try:
            button = self.btnmap[btncode]
            idx = (self._kbdmod, button)
            emap = self.eventmap[idx]

        except KeyError:
            return False

        cbname = '%s-move' % (emap.name)
        return fitsimage.make_callback(cbname, 'move', data_x, data_y)


    def window_button_release(self, fitsimage, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d button=%s" % (data_x, data_y,
                                                   hex(btncode)))
        try:
            self._button &= ~btncode
            button = self.btnmap[btncode]
            idx = (self._kbdmod, button)
            # release modifier if this is a oneshot modifier
            if (self._kbdmod_type == 'oneshot') or (self._delayed_reset):
                self.reset_modifier(fitsimage)
            emap = self.eventmap[idx]

        except KeyError:
            #self.logger.warn("No button map binding for %s" % (str(btncode)))
            return False

        cbname = '%s-up' % (emap.name)
        return fitsimage.make_callback(cbname, 'up', data_x, data_y)
            

    def window_scroll(self, fitsimage, direction, amount, data_x, data_y):
        try:
            idx = (self._kbdmod, 'scroll')
            emap = self.eventmap[idx]

        except KeyError:
            return False

        cbname = '%s-scroll' % (emap.name)
        return fitsimage.make_callback(cbname, direction, amount,
                                       data_x, data_y)


#END
