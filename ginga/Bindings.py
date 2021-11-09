#
# Bindings.py -- Bindings classes for Ginga FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
import os.path
import itertools
import numpy as np

from ginga.misc import Bunch, Settings, Callback
from ginga import trcalc
from ginga import cmap, imap
from ginga.util.paths import icondir
from ginga.util import wcs


class ImageViewBindings(object):
    """
    Mouse Operation and Bindings

    """

    def __init__(self, logger, settings=None):
        super(ImageViewBindings, self).__init__()

        self.logger = logger

        self.canpan = False
        self.canzoom = False
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
        self._save = {}

        if settings is None:
            # No settings passed.  Set up defaults.
            settings = Settings.SettingGroup(name='bindings',
                                             logger=self.logger)
            self.initialize_settings(settings)
        self.settings = settings

        self.features = dict(
            # name, attr pairs
            pan='canpan', zoom='canzoom', cuts='cancut', cmap='cancmap',
            flip='canflip', rotate='canrotate')
        self.cursor_map = {}

    def initialize_settings(self, settings):
        settings.add_settings(
            # You should rarely have to change these.
            btn_nobtn=0x0,
            btn_left=0x1,
            btn_middle=0x2,
            btn_right=0x4,
            btn_back=0x8,
            btn_forward=0x10,

            # define our cursors
            ## cur_pick = 'thinCrossCursor',
            ## cur_pan = 'openHandCursor',

            # Set up our standard modifiers
            mod_shift=['shift_l', 'shift_r'],
            mod_ctrl=['control_l', 'control_r'],
            mod_win=['meta_right'],

            # Define our modes
            # Mode 'meta' is special: it is an intermediate mode that
            # is used primarily to launch other modes
            # If the mode initiation character is preceeded by a double
            # underscore, then the mode must be initiated from the "meta"
            # mode.
            dmod_meta=['space', None, None],
            dmod_draw=['__b', None, None],
            dmod_cmap=['__y', None, None],
            dmod_cuts=['__s', None, None],
            dmod_dist=['__d', None, None],
            dmod_contrast=['__t', None, None],
            dmod_rotate=['__r', None, None],
            dmod_pan=['__q', None, 'pan'],
            dmod_freepan=['__w', None, 'pan'],
            dmod_camera=['__c', None, 'pan'],
            dmod_naxis=['__n', None, None],

            default_mode_type='locked',
            default_lock_mode_type='softlock',

            # KEYBOARD
            kp_zoom_in=['+', '='],
            kp_zoom_out=['-', '_'],
            kp_zoom=['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
            kp_zoom_inv=['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
            kp_zoom_fit=['backquote', 'pan+backquote', 'freepan+backquote'],
            kp_autozoom_toggle=['doublequote', 'pan+doublequote'],
            kp_autozoom_override=['singlequote', 'pan+singlequote'],
            kp_dist_reset=['D', 'dist+D'],
            kp_dist_prev=['dist+up', 'dist+b'],
            kp_dist_next=['dist+down', 'dist+n'],
            kp_pan_set=['p', 'pan+p', 'freepan+p'],
            kp_pan_zoom_set=['pan+1', 'freepan+1'],
            kp_pan_zoom_save=['pan+z', 'freepan+z'],
            kp_pan_left=['pan+*+left', 'freepan+*+left'],
            kp_pan_right=['pan+*+right', 'freepan+*+right'],
            kp_pan_up=['pan+*+up', 'freepan+*+up'],
            kp_pan_down=['pan+*+down', 'freepan+*+down'],
            kp_pan_home=['pan+*+home', 'freepan+*+home'],
            kp_pan_end=['pan+*+end', 'freepan+*+end'],
            kp_pan_page_up=['pan+*+page_up', 'freepan+*+page_up'],
            kp_pan_page_down=['pan+*+page_down', 'freepan+*+page_down'],
            kp_pan_px_xminus=['shift+left'],
            kp_pan_px_xplus=['shift+right'],
            kp_pan_px_yminus=['shift+down'],
            kp_pan_px_yplus=['shift+up'],
            kp_pan_px_center=['shift+home'],
            kp_center=['c', 'pan+c', 'freepan+c'],
            kp_cut_255=['cuts+A'],
            kp_cut_lo=['cuts+l'],
            kp_cut_hi=['cuts+h'],
            kp_cut_minmax=['cuts+S'],
            kp_cut_auto=['a', 'cuts+a'],
            kp_autocuts_alg_prev=['cuts+up', 'cuts+b'],
            kp_autocuts_alg_next=['cuts+down', 'cuts+n'],
            kp_autocuts_toggle=[':', 'cuts+:'],
            kp_autocuts_override=[';', 'cuts+;'],
            kp_autocenter_toggle=['?', 'pan+?'],
            kp_autocenter_override=['/', 'pan+/'],
            kp_contrast_restore=['T', 'contrast+T'],
            kp_cmap_reset=['Y', 'cmap+Y'],
            kp_cmap_restore=['cmap+r'],
            kp_cmap_invert=['I', 'cmap+I'],
            kp_cmap_prev=['cmap+up', 'cmap+b'],
            kp_cmap_next=['cmap+down', 'cmap+n'],
            kp_toggle_cbar=['cmap+c'],
            kp_imap_reset=['cmap+i'],
            kp_imap_prev=['cmap+left', 'cmap+j'],
            kp_imap_next=['cmap+right', 'cmap+k'],
            kp_flip_x=['[', '{', 'rotate+[', 'rotate+{'],
            kp_flip_y=[']', '}', 'rotate+]', 'rotate+}'],
            kp_swap_xy=['backslash', '|', 'rotate+backslash', 'rotate+|'],
            kp_rotate_reset=['R', 'rotate+R'],
            kp_save_profile=['S'],
            kp_rotate_inc90=['.', 'rotate+.'],
            kp_rotate_dec90=[',', 'rotate+,'],
            kp_orient_lh=['o', 'rotate+o'],
            kp_orient_rh=['O', 'rotate+O'],
            kp_poly_add=['v', 'draw+v'],
            kp_poly_del=['z', 'draw+z'],
            kp_edit_del=['draw+x'],
            kp_reset=['escape'],
            kp_lock=['L', 'meta+L'],
            kp_softlock=['l', 'meta+l'],
            kp_camera_save=['camera+s'],
            kp_camera_reset=['camera+r'],
            kp_camera_toggle3d=['camera+3'],

            # pct of a window of data to move with pan key commands
            key_pan_pct=0.666667,
            # amount to move (in pixels) when using key pan arrow
            key_pan_px_delta=1.0,

            # SCROLLING/WHEEL
            sc_pan=['ctrl+scroll'],
            sc_pan_fine=['pan+shift+scroll'],
            sc_pan_coarse=['pan+ctrl+scroll'],
            sc_zoom=['scroll', 'freepan+scroll'],
            sc_zoom_fine=[],
            sc_zoom_coarse=[],
            sc_zoom_origin=['shift+scroll', 'freepan+shift+scroll'],
            sc_cuts_fine=['cuts+ctrl+scroll'],
            sc_cuts_coarse=['cuts+scroll'],
            sc_cuts_alg=[],
            sc_dist=['dist+scroll'],
            sc_cmap=['cmap+scroll'],
            sc_imap=['cmap+ctrl+scroll'],
            sc_camera_track=['camera+scroll'],
            sc_naxis=['naxis+scroll'],

            scroll_pan_acceleration=1.0,
            scroll_pan_lock_x=False,
            scroll_pan_lock_y=False,
            # 1.0 is appropriate for a mouse, 0.1 for most trackpads
            scroll_zoom_acceleration=1.0,
            #scroll_zoom_acceleration=0.1,
            scroll_zoom_direct_scale=False,

            mouse_zoom_acceleration=1.085,
            mouse_rotate_acceleration=0.75,
            pan_reverse=False,
            pan_multiplier=1.0,
            pan_min_scroll_thumb_pct=0.0,
            pan_max_scroll_thumb_pct=0.9,
            zoom_scroll_reverse=False,

            # MOUSE/BUTTON
            ms_none=['nobtn'],
            ms_cursor=['left'],
            ms_wheel=[],
            ms_draw=['draw+left', 'win+left', 'right'],

            ms_rotate=['rotate+left'],
            ms_rotate_reset=['rotate+right'],
            ms_contrast=['contrast+left', 'ctrl+right'],
            ms_contrast_restore=['contrast+right', 'ctrl+middle'],
            ms_pan=['pan+left', 'ctrl+left'],
            ms_zoom=['pan+right'],
            ms_freepan=['freepan+middle'],
            ms_zoom_in=['freepan+left'],
            ms_zoom_out=['freepan+right', 'freepan+ctrl+left'],
            ms_cutlo=['cuts+shift+left'],
            ms_cuthi=['cuts+ctrl+left'],
            ms_cutall=['cuts+left'],
            ms_cut_auto=['cuts+right'],
            ms_panset=['pan+middle', 'shift+left', 'middle'],
            ms_cmap_rotate=['cmap+left'],
            ms_cmap_restore=['cmap+right'],
            ms_camera_orbit=['camera+left'],
            ms_camera_pan_delta=['camera+right'],
            ms_naxis=['naxis+left'],

            # GESTURES (some backends only)
            pi_zoom=['pinch'],
            pi_zoom_origin=['shift+pinch'],
            pa_pan=['pan'],
            pa_zoom=['freepan+pan'],
            pa_zoom_origin=['freepan+shift+pan'],
            pa_naxis=['naxis+pan'],

            pinch_actions=['zoom'],
            pinch_zoom_acceleration=1.0,
            pinch_rotate_acceleration=1.0,
            pan_pan_acceleration=1.0,

            # No messages for following operations:
            msg_panset=False,
        )

    def get_settings(self):
        return self.settings

    def window_map(self, viewer):
        #self.to_default_mode(viewer)
        pass

    def set_bindings(self, viewer):
        viewer.add_callback('map', self.window_map)

        bindmap = viewer.get_bindmap()
        bindmap.clear_button_map()
        bindmap.clear_event_map()

        bindmap.add_callback('mode-set', self.mode_set_cb, viewer)

        # Set up bindings
        self.setup_settings_events(viewer, bindmap)

    def set_mode(self, viewer, name, mode_type='oneshot'):
        bindmap = viewer.get_bindmap()
        bindmap.set_mode(name, mode_type=mode_type)

    def mode_set_cb(self, bm, mode, mode_type, viewer):
        cursor_name = self.cursor_map.get(mode, 'pick')
        viewer.switch_cursor(cursor_name)

    def parse_combo(self, combo, modes_set, modifiers_set, pfx):
        """
        Parse a string into a mode, a set of modifiers and a trigger.
        """
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

            if '*' in items:
                items.remove('*')
                # modifier wildcard
                mods = '*'
            else:
                mods = items.intersection(modifiers_set)

            mode = items.intersection(modes_set)
            if len(mode) == 0:
                mode = None
            else:
                mode = mode.pop()

        if pfx is not None:
            trigger = pfx + trigger

        return (mode, mods, trigger)

    def setup_settings_events(self, viewer, bindmap):

        d = self.settings.get_dict()
        if len(d) == 0:
            self.initialize_settings(self.settings)
            d = self.settings.get_dict()

        # First scan settings for buttons and modes
        bindmap.clear_button_map()
        bindmap.clear_modifier_map()
        bindmap.clear_mode_map()
        bindmap.clear_event_map()

        mode_type = self.settings.get('default_mode_type', 'oneshot')
        bindmap.set_default_mode_type(mode_type)

        for name, value in d.items():
            if name.startswith('mod_'):
                modname = name[4:]
                for combo in value:
                    # NOTE: for now no chorded combinations to make modifiers
                    keyname = combo
                    bindmap.add_modifier(keyname, modname)

            elif name.startswith('cur_'):
                curname = name[4:]
                self.add_cursor(viewer, curname, value)

            elif name.startswith('btn_'):
                btnname = name[4:]
                bindmap.map_button(value, btnname)

            elif name.startswith('dmod_'):
                mode_name = name[5:]
                keyname, mode_type, curname = value
                bindmap.add_mode(keyname, mode_name, mode_type=mode_type,
                                 msg=None)
                if curname is not None:
                    self.cursor_map[mode_name] = curname

        self.merge_actions(viewer, bindmap, self, d.items())

    def merge_actions(self, viewer, bindmap, obj, tups):

        modes_set = bindmap.get_modes()
        modifiers_set = bindmap.get_modifiers()

        # Add events
        for name, value in tups:
            if len(name) <= 3:
                continue

            pfx = name[:3]
            if pfx not in ('kp_', 'ms_', 'sc_', 'gs_', 'pi_', 'pa_'):
                continue

            evname = name[3:]
            for combo in value:
                mode, modifiers, trigger = self.parse_combo(combo, modes_set,
                                                            modifiers_set, pfx)
                if modifiers == '*':
                    # wildcard; register for all modifier combinations
                    modifiers_poss = set([])
                    for i in range(len(modifiers_set) + 1):
                        modifiers_poss = modifiers_poss.union(
                            itertools.combinations(modifiers_set, i))
                    for modifiers in modifiers_poss:
                        bindmap.map_event(mode, modifiers, trigger, evname)
                else:
                    bindmap.map_event(mode, modifiers, trigger, evname)

            # Register for this symbolic event if we have a handler for it
            try:
                cb_method = getattr(obj, name)

            except AttributeError:
                # Do we need a warning here?
                #self.logger.warning("No method found matching '%s'" % (name))
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

            elif pfx == 'pi_':
                # pinch event
                event = '%s-pinch' % evname
                viewer.enable_callback(event)
                if cb_method:
                    viewer.add_callback(event, cb_method)

            elif pfx == 'pa_':
                # pan event
                event = '%s-pan' % evname
                viewer.enable_callback(event)
                if cb_method:
                    viewer.add_callback(event, cb_method)

            elif pfx == 'gs_':
                # for backward compatibility
                self.logger.warning("'gs_' bindings will be deprecated in a future "
                                    "version--please update your bindings.cfg")
                viewer.set_callback(evname, cb_method)

    def reset(self, viewer):
        bindmap = viewer.get_bindmap()
        bindmap.reset_mode(viewer)
        viewer.onscreen_message(None)

    def add_cursor(self, viewer, curname, curpath):
        if not curpath.startswith('/'):
            curpath = os.path.join(icondir, curpath)
        cursor = viewer.make_cursor(curpath, 8, 8)
        viewer.define_cursor(curname, cursor)

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
            if feat not in self.features:
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
            xy_mn, xy_mx = viewer.get_limits()
            win_wd, win_ht = viewer.get_window_size()

            if (win_x >= win_wd):
                win_x = win_wd - 1
            if (win_y >= win_ht):
                win_y = win_ht - 1

            # Figure out data x,y based on percentage of X axis
            # and Y axis
            off_x, off_y = viewer.window_to_offset(win_x, win_y)
            max_x, max_y = viewer.window_to_offset(win_wd, win_ht)
            wd_x = abs(max_x) * 2.0
            ht_y = abs(max_y) * 2.0
            panx = (off_x + abs(max_x)) / float(wd_x)
            pany = (off_y + abs(max_y)) / float(ht_y)

            # Account for user preference
            if self.settings.get('pan_reverse', False):
                panx = 1.0 - panx
                pany = 1.0 - pany

            data_x = (xy_mn[0] + xy_mx[0]) * panx
            data_y = (xy_mn[1] + xy_mx[1]) * pany
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
            off_x, off_y = viewer.window_to_offset(win_x, win_y)
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

        except Exception as e:
            viewer.onscreen_message("Pan position set error; see log",
                                    delay=2.0)
            # most likely image does not have a valid wcs
            self.logger.error("Error setting pan position: %s" % (
                str(e)))

    def _get_key_pan_pct(self, event):
        amt = self.settings.get('key_pan_pct', 2 / 3.0)
        if 'ctrl' in event.modifiers:
            amt /= 5.0
        if 'shift' in event.modifiers:
            amt /= 10.0
        return amt

    def calc_pan_pct(self, viewer, pad=0):
        """Calculate values for vertical/horizontal panning by percentages
        from the current pan position.
        """
        limits = viewer.get_limits()

        tr = viewer.tform['data_to_scrollbar']

        # calculate the corners of the entire image in unscaled cartesian
        mxwd, mxht = limits[1][:2]
        mxwd, mxht = mxwd + pad, mxht + pad
        mnwd, mnht = limits[0][:2]
        mnwd, mnht = mnwd - pad, mnht - pad

        arr = np.array([(mnwd, mnht), (mxwd, mnht),
                        (mxwd, mxht), (mnwd, mxht)],
                       dtype=float)
        x, y = tr.to_(arr).T

        rx1, rx2 = np.min(x), np.max(x)
        ry1, ry2 = np.min(y), np.max(y)

        rect = viewer.get_pan_rect()
        arr = np.array(rect, dtype=float)
        x, y = tr.to_(arr).T

        qx1, qx2 = np.min(x), np.max(x)
        qy1, qy2 = np.min(y), np.max(y)

        # this is the range of X and Y of the entire image
        # in the viewer (unscaled)
        rng_x, rng_y = abs(rx2 - rx1), abs(ry2 - ry1)

        # this is the *visually shown* range of X and Y
        abs_x, abs_y = abs(qx2 - qx1), abs(qy2 - qy1)

        # calculate the width of the slider arms as a ratio
        min_pct = self.settings.get('pan_min_scroll_thumb_pct', 0.0)
        max_pct = self.settings.get('pan_max_scroll_thumb_pct', 0.9)
        xthm_pct = max(min_pct, min(abs_x / (rx2 - rx1), max_pct))
        ythm_pct = max(min_pct, min(abs_y / (ry2 - ry1), max_pct))

        # calculate the pan position as a ratio
        pct_x = min(max(0.0, abs(0.0 - rx1) / rng_x), 1.0)
        pct_y = min(max(0.0, abs(0.0 - ry1) / rng_y), 1.0)

        bnch = Bunch.Bunch(rng_x=rng_x, rng_y=rng_y, vis_x=abs_x, vis_y=abs_y,
                           thm_pct_x=xthm_pct, thm_pct_y=ythm_pct,
                           pan_pct_x=pct_x, pan_pct_y=pct_y)
        return bnch

    def pan_by_pct(self, viewer, pct_x, pct_y, pad=0):
        """Called when the scroll bars are adjusted by the user.
        """
        # Sanity check on inputs
        pct_x = min(1.0, max(0.0, pct_x))
        pct_y = min(1.0, max(0.0, pct_y))

        limits = viewer.get_limits()

        tr = viewer.tform['data_to_scrollbar']

        mxwd, mxht = limits[1][:2]
        mxwd, mxht = mxwd + pad, mxht + pad
        mnwd, mnht = limits[0][:2]
        mnwd, mnht = mnwd - pad, mnht - pad

        arr = np.array([(mnwd, mnht), (mxwd, mnht),
                        (mxwd, mxht), (mnwd, mxht)],
                       dtype=float)
        x, y = tr.to_(arr).T

        rx1, rx2 = np.min(x), np.max(x)
        ry1, ry2 = np.min(y), np.max(y)

        crd_x = rx1 + (pct_x * (rx2 - rx1))
        crd_y = ry1 + (pct_y * (ry2 - ry1))

        pan_x, pan_y = tr.from_((crd_x, crd_y))
        self.logger.debug("crd=%f,%f pan=%f,%f" % (
            crd_x, crd_y, pan_x, pan_y))

        viewer.panset_xy(pan_x, pan_y)

    def pan_omni(self, viewer, direction, amount, msg=False,
                 lock_x=False, lock_y=False):
        # calculate current pan pct
        res = self.calc_pan_pct(viewer, pad=0)

        ang_rad = math.radians(90.0 - direction)
        amt_x = 0 if lock_x else math.cos(ang_rad) * amount
        amt_y = 0 if lock_y else math.sin(ang_rad) * amount

        # modify the pct, as per the params
        pct_page_x = res.vis_x / res.rng_x
        amt_x = amt_x * pct_page_x
        pct_page_y = res.vis_y / res.rng_y
        amt_y = amt_y * pct_page_y

        pct_x = res.pan_pct_x + amt_x
        pct_y = res.pan_pct_y + amt_y

        # update the pan position by pct
        self.pan_by_pct(viewer, pct_x, pct_y)

    def pan_lr(self, viewer, pct_vw, sign, msg=False):
        # calculate current pan pct
        res = self.calc_pan_pct(viewer, pad=0)

        pct_page = res.vis_x / res.rng_x
        # modify the pct, as per the params
        amt = sign * pct_vw * pct_page
        pct_x = res.pan_pct_x + amt

        # update the pan position by pct
        self.pan_by_pct(viewer, pct_x, res.pan_pct_y)

    def pan_ud(self, viewer, pct_vh, sign, msg=False):
        # calculate current pan pct
        res = self.calc_pan_pct(viewer, pad=0)

        pct_page = res.vis_y / res.rng_y
        # modify the pct, as per the params
        amt = sign * pct_vh * pct_page
        pct_y = res.pan_pct_y + amt

        # update the pan position by pct
        self.pan_by_pct(viewer, res.pan_pct_x, pct_y)

    def pan_delta_px(self, viewer, x_px, y_px):
        pan_x, pan_y = viewer.get_pan(coord='data')[:2]
        pan_x += x_px
        pan_y += y_px
        viewer.panset_xy(pan_x, pan_y)

    def pan_center_px(self, viewer):
        data_x, data_y = viewer.get_last_data_xy()
        ndata_x = float(int(data_x + viewer.data_off))
        ndata_y = float(int(data_y + viewer.data_off))
        x_px, y_px = ndata_x - data_x, ndata_y - data_y
        self.pan_delta_px(viewer, x_px, y_px)

    def get_direction(self, direction, rev=False):
        """
        Translate a direction in compass degrees into 'up' or 'down'.
        """
        if (direction < 90.0) or (direction >= 270.0):
            if not rev:
                return 'up'
            else:
                return 'down'
        elif (90.0 <= direction < 270.0):
            if not rev:
                return 'down'
            else:
                return 'up'
        else:
            return 'none'

    def get_win_xy(self, viewer):
        x, y = viewer.get_last_win_xy()

        if not viewer.window_has_origin_upper():
            wd, ht = viewer.get_window_size()
            y = ht - y

        return x, y

    def _tweak_colormap(self, viewer, x, y, mode):
        win_wd, win_ht = viewer.get_window_size()

        # translate Y cursor position as a percentage of the window
        # height into a scaling factor
        y_pct = (win_ht - y) / float(win_ht)

        # I tried to mimic ds9's exponential scale feel along the Y-axis
        def exp_scale(i):
            return (1.0 / (i**3)) * 0.0002 + (1.0 / i) * 0.085

        scale_pct = exp_scale(1.0 - y_pct)

        # translate X cursor position as a percentage of the window
        # width into a shifting factor
        shift_pct = x / float(win_wd) - 0.5

        viewer.scale_and_shift_cmap(scale_pct, shift_pct)

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

    def _cutlow_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_vip()
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
        image = viewer.get_vip()
        minval, maxval = image.get_minmax()
        spread = maxval - minval
        loval, hival = viewer.get_cut_levels()
        loval = minval + (pct * spread)
        if msg:
            viewer.onscreen_message("Cut low: %.4f" % (loval))
        viewer.cut_levels(loval, hival)

    def _cuthigh_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        image = viewer.get_vip()
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
        image = viewer.get_vip()
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

    def cut_pct(self, viewer, pct, msg=True):
        msg = self.settings.get('msg_cuts', msg)
        loval, hival = viewer.get_cut_levels()
        spread = hival - loval
        loval = loval + (pct * spread)
        hival = hival - (pct * spread)
        if msg:
            viewer.onscreen_message("Cut low: %.4f  high: %.4f" % (
                loval, hival), delay=1.0)
        viewer.cut_levels(loval, hival)

    def _adjust_cuts(self, viewer, direction, pct, msg=True):
        direction = self.get_direction(direction)
        if direction == 'up':
            self.cut_pct(viewer, pct, msg=msg)
        elif direction == 'down':
            self.cut_pct(viewer, -pct, msg=msg)

    def _scale_image(self, viewer, direction, factor, msg=True):
        msg = self.settings.get('msg_zoom', msg)
        rev = self.settings.get('zoom_scroll_reverse', False)
        scale_x, scale_y = viewer.get_scale_xy()
        direction = self.get_direction(direction, rev=rev)
        mult = 1.0
        if direction == 'up':
            mult = factor
        elif direction == 'down':
            mult = 1.0 / factor
        scale_x, scale_y = scale_x * mult, scale_y * mult
        scale = max(scale_x, scale_y)
        #viewer.scale_to(scale_x, scale_y)
        viewer.scale_to(scale, scale)
        if msg:
            viewer.onscreen_message(viewer.get_scale_text(),
                                    delay=0.4)

    def _zoom_xy(self, viewer, x, y, msg=True):
        win_wd, win_ht = viewer.get_window_size()
        delta = float(x - self._start_x)
        factor = self.settings.get('mouse_zoom_acceleration', 1.085)
        direction = 0.0
        if delta < 0.0:
            direction = 180.0
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
                if idx < 0:
                    idx = len(algs) - 1
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

    def _cycle_cuts_alg(self, viewer, msg, direction='down'):
        if self.cancut:
            msg = self.settings.get('msg_autocuts_alg', msg)
            algs = viewer.get_autocut_methods()
            settings = viewer.get_settings()
            algname = settings.get('autocut_method', 'minmax')
            idx = algs.index(algname)
            if direction == 'down':
                idx = (idx + 1) % len(algs)
            else:
                idx = idx - 1
                if idx < 0:
                    idx = len(algs) - 1
            algname = algs[idx]
            viewer.set_autocut_params(algname)
            if msg:
                viewer.onscreen_message("Autocuts alg: %s" % (algname),
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
                if idx < 0:
                    idx = len(cmapnames) - 1
            cmapname = cmapnames[idx]
            viewer.set_color_map(cmapname)
            if msg:
                viewer.onscreen_message("Color map: %s" % (cmapname),
                                        delay=1.0)

    def _reset_cmap(self, viewer, msg):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            # default
            cmapname = 'gray'
            viewer.set_color_map(cmapname)
            if msg:
                viewer.onscreen_message("Color map: %s" % (cmapname),
                                        delay=1.0)

    def _invert_cmap(self, viewer, msg):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            rgbmap = viewer.get_rgbmap()
            rgbmap.invert_cmap()
            if msg:
                viewer.onscreen_message("Inverted color map",
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
                if idx < 0:
                    idx = len(imapnames) - 1
            imapname = imapnames[idx]
            viewer.set_intensity_map(imapname)
            if msg:
                viewer.onscreen_message("Intensity map: %s" % (imapname),
                                        delay=1.0)

    def _reset_imap(self, viewer, msg):
        if self.cancmap:
            msg = self.settings.get('msg_imap', msg)
            # default
            imapname = 'ramp'
            viewer.set_intensity_map(imapname)
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
        ctr_x, ctr_y = viewer.get_center()
        if None in (self._start_x, self._start_y):
            # missed button down event, most likely, or we're getting this
            # motion callback too early
            return
        deg1 = math.degrees(math.atan2(ctr_y - self._start_y,
                                       self._start_x - ctr_x))
        deg2 = math.degrees(math.atan2(ctr_y - y, x - ctr_x))
        delta_deg = deg2 - deg1
        deg = math.fmod(self._start_rot + delta_deg, 360.0)
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

        (x, y, xn, yn, xe, ye) = wcs.calc_compass_center(image)
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

    def to_default_mode(self, viewer):
        self.reset(viewer)

    def pan_start(self, viewer, ptype=1):
        self._pantype = ptype

    def pan_set_origin(self, viewer, win_x, win_y, data_x, data_y):
        self._start_x, self._start_y = viewer.window_to_offset(win_x, win_y)
        self._start_panx, self._start_pany = viewer.get_pan()

    def pan_stop(self, viewer):
        self._start_x = None
        self._pantype = 1

    def restore_contrast(self, viewer, msg=True):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = viewer.get_rgbmap()
        rgbmap.reset_sarr()
        if msg:
            viewer.onscreen_message("Restored contrast", delay=0.5)
        return True

    def restore_colormap(self, viewer, msg=True):
        msg = self.settings.get('msg_cmap', msg)
        rgbmap = viewer.get_rgbmap()
        rgbmap.restore_cmap()
        if msg:
            viewer.onscreen_message("Restored color map", delay=0.5)
        return True

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_pan_set(self, viewer, event, data_x, data_y, msg=True):
        """Sets the pan position under the cursor."""
        if self.canpan:
            self._panset(viewer, data_x, data_y, msg=msg)
        return True

    def kp_pan_zoom_set(self, viewer, event, data_x, data_y, msg=True):
        """Sets the pan position under the cursor."""
        if self.canpan:
            reg = 1
            with viewer.suppress_redraw:
                viewer.panset_xy(data_x, data_y)
                scale_x, scale_y = self._save.get((viewer, 'scale', reg),
                                                  (1.0, 1.0))
                viewer.scale_to(scale_x, scale_y)
        return True

    def kp_pan_zoom_save(self, viewer, event, data_x, data_y, msg=True):
        """Save the current viewer scale for future use with
        kp_pan_zoom_set()."""
        reg = 1
        scale = viewer.get_scale_xy()
        self._save[(viewer, 'scale', reg)] = scale
        if msg:
            viewer.onscreen_message("Saved current scale", delay=0.5)
        return True

    def kp_pan_left(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        self.pan_lr(viewer, amt, -0.1, msg=msg)
        return True

    def kp_pan_right(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        self.pan_lr(viewer, amt, 0.1, msg=msg)
        return True

    def kp_pan_up(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        self.pan_ud(viewer, amt, 0.1, msg=msg)
        return True

    def kp_pan_down(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        self.pan_ud(viewer, amt, -0.1, msg=msg)
        return True

    def kp_pan_page_up(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        self.pan_ud(viewer, amt, 1.0, msg=msg)
        return True

    def kp_pan_page_down(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        amt = self._get_key_pan_pct(event)
        self.pan_ud(viewer, amt, -1.0, msg=msg)
        return True

    def kp_pan_home(self, viewer, event, data_x, data_y, msg=True):
        res = self.calc_pan_pct(viewer, pad=0)
        # 1.0 == max Y
        self.pan_by_pct(viewer, res.pan_pct_x, 1.0)

    def kp_pan_end(self, viewer, event, data_x, data_y, msg=True):
        res = self.calc_pan_pct(viewer, pad=0)
        # 0.0 == min Y
        self.pan_by_pct(viewer, res.pan_pct_x, 0.0)

    def kp_pan_px_xminus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        self.pan_delta_px(viewer, -px_amt, 0.0)
        return True

    def kp_pan_px_xplus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        self.pan_delta_px(viewer, px_amt, 0.0)
        return True

    def kp_pan_px_yminus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        self.pan_delta_px(viewer, 0.0, -px_amt)
        return True

    def kp_pan_px_yplus(self, viewer, event, data_x, data_y, msg=True):
        if not self.canpan:
            return False
        px_amt = self.settings.get('key_pan_px_delta', 1.0)
        self.pan_delta_px(viewer, 0.0, px_amt)
        return True

    def kp_pan_px_center(self, viewer, event, data_x, data_y, msg=True):
        """This pans so that the cursor is over the center of the
        current pixel."""
        if not self.canpan:
            return False
        self.pan_center_px(viewer)
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
            try:
                zoomval = (keylist.index(event.key))
            except IndexError:
                return False
            viewer.zoom_to(zoomval)
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                        delay=1.0)
        return True

    def kp_zoom_inv(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            keylist = self.settings.get('kp_zoom_inv')
            try:
                zoomval = - (keylist.index(event.key))
            except IndexError:
                return False
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

    def kp_autozoom_toggle(self, viewer, event, data_x, data_y, msg=True):
        if self.canzoom:
            msg = self.settings.get('msg_zoom', msg)
            val = viewer.get_settings().get('autozoom')
            if val == 'off':
                val = 'on'
            else:
                val = 'off'
            viewer.enable_autozoom(val)
            if msg:
                viewer.onscreen_message('Autozoom %s' % val, delay=1.0)
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

    def kp_cut_lo(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            _, hi = viewer.get_cut_levels()
            lo = viewer.get_data(data_x, data_y)
            viewer.cut_levels(lo, hi, no_reset=True)
        return True

    def kp_cut_hi(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            lo, _ = viewer.get_cut_levels()
            hi = viewer.get_data(data_x, data_y)
            viewer.cut_levels(lo, hi, no_reset=True)
        return True

    def kp_cut_minmax(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            image = viewer.get_vip()
            mn, mx = image.get_minmax(noinf=True)
            viewer.cut_levels(mn, mx, no_reset=True)
        return True

    def kp_cut_auto(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            if msg:
                viewer.onscreen_message("Auto cut levels", delay=1.0)
            viewer.auto_levels()
        return True

    def kp_autocuts_toggle(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            val = viewer.get_settings().get('autocuts')
            if val == 'off':
                val = 'on'
            else:
                val = 'off'
            viewer.enable_autocuts(val)
            if msg:
                viewer.onscreen_message('Autocuts %s' % val, delay=1.0)
        return True

    def kp_autocuts_override(self, viewer, event, data_x, data_y, msg=True):
        if self.cancut:
            msg = self.settings.get('msg_cuts', msg)
            viewer.enable_autocuts('override')
            if msg:
                viewer.onscreen_message('Autocuts Override', delay=1.0)
        return True

    def kp_autocuts_alg_prev(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_cuts_alg(viewer, msg, direction='up')
        return True

    def kp_autocuts_alg_next(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_cuts_alg(viewer, msg, direction='down')
        return True

    def kp_autocenter_toggle(self, viewer, event, data_x, data_y, msg=True):
        if self.canpan:
            msg = self.settings.get('msg_pan', msg)
            val = viewer.get_settings().get('autocenter')
            if val == 'off':
                val = 'on'
            else:
                val = 'off'
            viewer.set_autocenter(val)
            if msg:
                viewer.onscreen_message('Autocenter %s' % val, delay=1.0)
        return True

    def kp_autocenter_override(self, viewer, event, data_x, data_y, msg=True):
        if self.canpan:
            msg = self.settings.get('msg_pan', msg)
            viewer.set_autocenter('override')
            if msg:
                viewer.onscreen_message('Autocenter Override', delay=1.0)
        return True

    def kp_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        if self.cancmap:
            msg = self.settings.get('msg_cmap', msg)
            self.restore_contrast(viewer, msg=msg)
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

    def kp_transform_reset(self, viewer, event, data_x, data_y):
        if self.canflip:
            viewer.transform(False, False, False)
        return True

    def kp_dist(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_dist(viewer, msg)
        return True

    def kp_dist_reset(self, viewer, event, data_x, data_y, msg=True):
        self._reset_dist(viewer, msg)
        return True

    def kp_dist_prev(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_dist(viewer, msg, direction='up')
        return True

    def kp_dist_next(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_dist(viewer, msg, direction='down')
        return True

    def kp_cmap_reset(self, viewer, event, data_x, data_y, msg=True):
        self._reset_cmap(viewer, msg)
        return True

    def kp_cmap_restore(self, viewer, event, data_x, data_y, msg=True):
        self.restore_colormap(viewer, msg)
        return True

    def kp_cmap_invert(self, viewer, event, data_x, data_y, msg=True):
        self._invert_cmap(viewer, msg)
        return True

    def kp_cmap_prev(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_cmap(viewer, msg, direction='up')
        return True

    def kp_cmap_next(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_cmap(viewer, msg, direction='down')
        return True

    def kp_toggle_cbar(self, viewer, event, data_x, data_y, msg=True):
        canvas = viewer.get_private_canvas()
        # canvas already has a color bar?
        objs = list(canvas.get_objects_by_kinds(('colorbar', 'drawablecolorbar')))
        tf = (len(objs) == 0)
        viewer.show_color_bar(tf)
        return True

    def kp_imap_reset(self, viewer, event, data_x, data_y, msg=True):
        self._reset_imap(viewer, msg)
        return True

    def kp_imap_prev(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_imap(viewer, msg, direction='up')
        return True

    def kp_imap_next(self, viewer, event, data_x, data_y, msg=True):
        self._cycle_imap(viewer, msg, direction='down')
        return True

    def kp_rotate_reset(self, viewer, event, data_x, data_y):
        if self.canrotate:
            viewer.rotate(0.0)
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

    def _toggle_lock(self, viewer, mode_type):
        bm = viewer.get_bindmap()
        # toggle default mode type to locked/oneshot
        dfl_modetype = bm.get_default_mode_type()
        # get current mode
        mode_name, cur_modetype = bm.current_mode()

        if dfl_modetype in ('locked', 'softlock'):
            if mode_type == dfl_modetype:
                mode_type = 'oneshot'

        # install the lock type
        bm.set_default_mode_type(mode_type)
        bm.set_mode(mode_name, mode_type=mode_type)

    def kp_lock(self, viewer, event, data_x, data_y):
        self._toggle_lock(viewer, 'locked')
        return True

    def kp_softlock(self, viewer, event, data_x, data_y):
        self._toggle_lock(viewer, 'softlock')
        return True

    def kp_save_profile(self, viewer, event, data_x, data_y, msg=True):
        viewer.checkpoint_profile()
        if msg:
            viewer.onscreen_message("Profile saved", delay=0.5)
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

        x, y = self.get_win_xy(viewer)

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

    def _scale_adjust(self, factor, event_amt, zoom_accel, max_limit=None):
        # adjust scale by factor, amount encoded in event and zoom acceleration value
        amount = factor - ((factor - 1.0) * (1.0 - min(event_amt, 15.0) / 15.0) *
                           zoom_accel)
        amount = max(1.000000001, amount)
        if max_limit is not None:
            amount = min(amount, max_limit)
        return amount

    def ms_zoom_in(self, viewer, event, data_x, data_y, msg=False):
        """Zoom in one level by a mouse click.
        """
        if not self.canzoom:
            return True

        if not (event.state == 'down'):
            return True

        with viewer.suppress_redraw:
            viewer.panset_xy(data_x, data_y)

            if self.settings.get('scroll_zoom_direct_scale', True):
                zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
                # change scale by 100%
                amount = self._scale_adjust(2.0, 15.0, zoom_accel, max_limit=4.0)
                self._scale_image(viewer, 0.0, amount, msg=msg)
            else:
                viewer.zoom_in()

            if hasattr(viewer, 'center_cursor'):
                viewer.center_cursor()
            if msg:
                viewer.onscreen_message(viewer.get_scale_text(),
                                        delay=1.0)
        return True

    def ms_zoom_out(self, viewer, event, data_x, data_y, msg=False):
        """Zoom out one level by a mouse click.
        """
        if not self.canzoom:
            return True

        if not (event.state == 'down'):
            return True

        with viewer.suppress_redraw:
            # TODO: think about whether it is the correct behavior to
            # set the pan position when zooming out
            #viewer.panset_xy(data_x, data_y)

            if self.settings.get('scroll_zoom_direct_scale', True):
                zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
                # change scale by 100%
                amount = self._scale_adjust(2.0, 15.0, zoom_accel, max_limit=4.0)
                self._scale_image(viewer, 180.0, amount, msg=msg)
            else:
                viewer.zoom_out()

            if hasattr(viewer, 'center_cursor'):
                viewer.center_cursor()
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

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._rotate_xy(viewer, x, y)

        elif event.state == 'down':
            if msg:
                viewer.onscreen_message("Rotate (drag around center)",
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

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._tweak_colormap(viewer, x, y, 'preview')

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            if msg:
                viewer.onscreen_message(
                    "Shift and stretch colormap (drag mouse)", delay=1.0)
        else:
            viewer.onscreen_message(None)
        return True

    def ms_contrast_restore(self, viewer, event, data_x, data_y, msg=True):
        """An interactive way to restore the colormap contrast settings after
        a warp operation.
        """
        if self.cancmap and (event.state == 'down'):
            self.restore_contrast(viewer, msg=msg)
        return True

    def ms_cmap_rotate(self, viewer, event, data_x, data_y, msg=True):
        """Shift the colormap by dragging the cursor left or right.
        Stretch the colormap by dragging the cursor up or down.
        """
        if not self.cancmap:
            return True
        msg = self.settings.get('msg_cmap', msg)

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._rotate_colormap(viewer, x, y, 'preview')

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            if msg:
                viewer.onscreen_message("Rotate colormap (drag mouse L/R)",
                                        delay=1.0)
        else:
            viewer.onscreen_message(None)
        return True

    def ms_cmap_restore(self, viewer, event, data_x, data_y, msg=True):
        """An interactive way to restore the colormap settings after
        a rotate or invert operation.
        """
        if self.cancmap and (event.state == 'down'):
            self.restore_colormap(viewer, msg)
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

        x, y = self.get_win_xy(viewer)

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

        x, y = self.get_win_xy(viewer)

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

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            self._cutboth_xy(viewer, x, y)

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            image = viewer.get_vip()
            #self._loval, self._hival = viewer.get_cut_levels()
            self._loval, self._hival = viewer.autocuts.calc_cut_levels(image)

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

        return True

    #####  SCROLL ACTION CALLBACKS #####

    def sc_cuts_coarse(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it coarsely.
        """
        if self.cancut:
            # adjust the cut by 10% on each end
            self._adjust_cuts(viewer, event.direction, 0.1, msg=msg)
        return True

    def sc_cuts_fine(self, viewer, event, msg=True):
        """Adjust cuts interactively by setting the low AND high cut
        levels.  This function adjusts it finely.
        """
        if self.cancut:
            # adjust the cut by 1% on each end
            self._adjust_cuts(viewer, event.direction, 0.01, msg=msg)
        return True

    def sc_cuts_alg(self, viewer, event, msg=True):
        """Adjust cuts algorithm interactively.
        """
        if self.cancut:
            direction = self.get_direction(event.direction)
            self._cycle_cuts_alg(viewer, msg, direction=direction)
        return True

    def zoom_step(self, viewer, event, msg=True, origin=None, adjust=1.5):
        with viewer.suppress_redraw:

            if origin is not None:
                # get cartesian canvas coords of data item under cursor
                data_x, data_y = origin[:2]
                off_x, off_y = viewer.data_to_offset(data_x, data_y)
                # set the pan position to the data item
                viewer.set_pan(data_x, data_y)

            # scale by the desired means
            if self.settings.get('scroll_zoom_direct_scale', True):
                zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
                # change scale by 50%
                amount = self._scale_adjust(adjust, event.amount, zoom_accel,
                                            max_limit=4.0)
                self._scale_image(viewer, event.direction, amount, msg=msg)

            else:
                rev = self.settings.get('zoom_scroll_reverse', False)
                direction = self.get_direction(event.direction, rev=rev)

                if direction == 'up':
                    viewer.zoom_in()

                elif direction == 'down':
                    viewer.zoom_out()

                if msg:
                    viewer.onscreen_message(viewer.get_scale_text(),
                                            delay=0.4)

            if origin is not None:
                # now adjust the pan position to keep the offset
                data_x2, data_y2 = viewer.offset_to_data(off_x, off_y)
                dx, dy = data_x2 - data_x, data_y2 - data_y
                viewer.panset_xy(data_x - dx, data_y - dy)

    def _sc_zoom(self, viewer, event, msg=True, origin=None):
        if not self.canzoom:
            return True

        msg = self.settings.get('msg_zoom', msg)

        self.zoom_step(viewer, event, msg=msg, origin=origin,
                       adjust=1.5)
        return True

    def sc_zoom(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by the zoom steps configured under Preferences.
        """
        self._sc_zoom(viewer, event, msg=msg, origin=None)
        return True

    def sc_zoom_origin(self, viewer, event, msg=True):
        """Like sc_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        origin = (event.data_x, event.data_y)
        self._sc_zoom(viewer, event, msg=msg, origin=origin)
        return True

    def sc_zoom_coarse(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if not self.canzoom:
            return True

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
        # change scale by 20%
        amount = self._scale_adjust(1.2, event.amount, zoom_accel, max_limit=4.0)
        self._scale_image(viewer, event.direction, amount, msg=msg)
        return True

    def sc_zoom_fine(self, viewer, event, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if not self.canzoom:
            return True

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 1.0)
        # change scale by 5%
        amount = self._scale_adjust(1.05, event.amount, zoom_accel, max_limit=4.0)
        self._scale_image(viewer, event.direction, amount, msg=msg)
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
        # Internal factor to adjust the panning speed so that user-adjustable
        # scroll_pan_acceleration is normalized to 1.0 for "normal" speed
        scr_pan_adj_factor = 1.4142135623730951
        amount = (event.amount * scr_pan_adj_factor * pan_accel) / 360.0

        lock_x = self.settings.get('scroll_pan_lock_x', False)
        lock_y = self.settings.get('scroll_pan_lock_y', False)

        self.pan_omni(viewer, direction, amount, lock_x=lock_x, lock_y=lock_y)
        return True

    def sc_pan_coarse(self, viewer, event, msg=True):
        event.amount = event.amount / 2.0
        return self.sc_pan(viewer, event, msg=msg)

    def sc_pan_fine(self, viewer, event, msg=True):
        event.amount = event.amount / 5.0
        return self.sc_pan(viewer, event, msg=msg)

    def sc_naxis(self, viewer, event, msg=True):
        """Interactively change the slice of the image in a data cube
        by scrolling.
        """
        # TODO: be able to pick axis
        axis = 3
        direction = self.get_direction(event.direction)

        return self._nav_naxis(viewer, axis, direction, msg=msg)

    def sc_dist(self, viewer, event, msg=True):
        """Interactively change the color distribution algorithm
        by scrolling.
        """
        direction = self.get_direction(event.direction)
        self._cycle_dist(viewer, msg, direction=direction)
        return True

    def sc_cmap(self, viewer, event, msg=True):
        """Interactively change the color map by scrolling.
        """
        direction = self.get_direction(event.direction)
        self._cycle_cmap(viewer, msg, direction=direction)
        return True

    def sc_imap(self, viewer, event, msg=True):
        """Interactively change the intensity map by scrolling.
        """
        direction = self.get_direction(event.direction)
        self._cycle_imap(viewer, msg, direction=direction)
        return True

    ##### GESTURE ACTION CALLBACKS #####

    def gs_pan(self, viewer, state, dx, dy, msg=True):
        if not self.canpan:
            return True

        method = 1
        x, y = viewer.get_last_win_xy()

        # User has "Pan Reverse" preference set?
        rev = self.settings.get('pan_reverse', False)
        if rev:
            dx, dy = -dx, -dy

        if state == 'move':
            # Internal factor to adjust the panning speed so that user-adjustable
            # pan_pan_acceleration is normalized to 1.0 for "normal" speed
            pan_pan_adj_factor = 1.0
            pan_accel = (self.settings.get('pan_pan_acceleration', 1.0) *
                         pan_pan_adj_factor)

            if method == 1:
                # METHOD 1
                # similar to moving by the scroll bars
                # calculate current pan pct
                res = self.calc_pan_pct(viewer, pad=0)

                # modify the pct, as relative to the offsets
                amt_x = float(dx) / res.rng_x * pan_accel
                amt_y = float(dy) / res.rng_y * pan_accel

                pct_x = res.pan_pct_x - amt_x
                pct_y = res.pan_pct_y + amt_y

                # update the pan position by pct
                self.pan_by_pct(viewer, pct_x, pct_y)

            elif method == 2:
                # METHOD 2
                # similar to using a drag pan
                x, y = x + dx * pan_accel, y + dy * pan_accel

                data_x, data_y = self.get_new_pan(viewer, x, y,
                                                  ptype=self._pantype)
                viewer.panset_xy(data_x, data_y)

            elif method == 3:
                # METHOD 3
                # calculate new position from pan gesture offsets
                data_x, data_y = viewer.get_pan(coord='data')
                x, y = viewer.get_canvas_xy(data_x, data_y)

                x, y = x - dx * pan_accel, y - dy * pan_accel

                data_x, data_y = viewer.get_data_xy(x, y)
                viewer.panset_xy(data_x, data_y)

        elif state == 'start':
            #self._start_panx, self._start_pany = viewer.get_pan()
            data_x, data_y = viewer.get_last_data_xy()
            self.pan_set_origin(viewer, x, y, data_x, data_y)
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

    def _pinch_zoom_rotate(self, viewer, state, rot_deg, scale, msg=True,
                           origin=None):
        pinch_actions = self.settings.get('pinch_actions', [])

        with viewer.suppress_redraw:

            if state == 'start':
                self._start_scale_x, self._start_scale_y = viewer.get_scale_xy()
                self._start_rot = viewer.get_rotation()
                return True

            if origin is not None:
                # get cartesian canvas coords of data item under cursor
                data_x, data_y = origin[:2]
                off_x, off_y = viewer.data_to_offset(data_x, data_y)
                # set the pan position to the data item
                viewer.set_pan(data_x, data_y)

            msg_str = None
            if self.canzoom and ('zoom' in pinch_actions):
                # scale by the desired means
                scale_accel = self.settings.get('pinch_zoom_acceleration', 1.0)
                scale = scale * scale_accel
                # NOTE: scale reported by Qt (the only toolkit that really gives
                # us a pinch gesture right now) the scale reports are iterative
                # so it makes more sense to keep updating the scale than to base
                # the scale on the original scale captured when the gesture starts
                ## scale_x, scale_y = (self._start_scale_x * scale,
                ##                     self._start_scale_y * scale)
                scale_x, scale_y = viewer.get_scale_xy()
                scale_x, scale_y = scale_x * scale, scale_y * scale

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

            if origin is not None:
                # now adjust the pan position to keep the offset
                data_x2, data_y2 = viewer.offset_to_data(off_x, off_y)
                dx, dy = data_x2 - data_x, data_y2 - data_y
                viewer.panset_xy(data_x - dx, data_y - dy)

            if msg and (msg_str is not None):
                viewer.onscreen_message(msg_str, delay=0.4)

        return True

    def gs_pinch(self, viewer, state, rot_deg, scale, msg=True):
        return self._pinch_zoom_rotate(viewer, state, rot_deg, scale, msg=msg)

    def pi_zoom(self, viewer, event, msg=True):
        """Zoom and/or rotate the viewer by a pinch gesture.
        (the back end must support gestures)
        """
        return self._pinch_zoom_rotate(viewer, event.state, event.rot_deg,
                                       event.scale, msg=msg)

    def pi_zoom_origin(self, viewer, event, msg=True):
        """Like pi_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        origin = (event.data_x, event.data_y)
        return self._pinch_zoom_rotate(viewer, event.state, event.rot_deg,
                                       event.scale, msg=msg, origin=origin)

    def pa_pan(self, viewer, event, msg=True):
        """Interactively pan the image by a pan gesture.
        (the back end must support gestures)
        """
        return self.gs_pan(viewer, event.state,
                           event.delta_x, event.delta_y, msg=msg)

    def _pa_synth_scroll_event(self, event):

        dx, dy = float(event.delta_x), float(event.delta_y)
        amount = math.sqrt(dx ** 2.0 + dy ** 2.0)
        if dx == 0.0:
            if dy > 0:
                direction = 0.0
            else:
                direction = 180.0
        else:
            direction = math.atan(dy / dx)

        self.logger.debug("scroll amount=%f direction=%f" % (
            amount, direction))

        # synthesize a scroll event
        event = ScrollEvent(button=event.button, state=event.state,
                            mode=event.mode, modifiers=event.modifiers,
                            direction=direction, amount=amount,
                            data_x=event.data_x, data_y=event.data_y,
                            viewer=event.viewer)
        return event

    def pa_zoom(self, viewer, event, msg=True):
        """Interactively zoom the image by a pan gesture.
        (the back end must support gestures)
        """
        event = self._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False
        self._sc_zoom(viewer, event, msg=msg, origin=None)
        return True

    def pa_zoom_origin(self, viewer, event, msg=True):
        """Like pa_zoom(), but pans the image as well to keep the
        coordinate under the cursor in that same position relative
        to the window.
        """
        event = self._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False
        origin = (event.data_x, event.data_y)
        self._sc_zoom(viewer, event, msg=msg, origin=origin)
        return True

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

    ##### CAMERA MOTION CALLBACKS #####

    def get_camera(self, viewer):
        renderer = viewer.renderer
        if not hasattr(renderer, 'camera'):
            return None, None
        return renderer.camera

    def sc_camera_track(self, viewer, event, msg=True):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return

        zoom_accel = self.settings.get('scroll_zoom_acceleration', 6.0)
        delta = event.amount * zoom_accel

        direction = self.get_direction(event.direction)
        if direction == 'down':
            delta = - delta

        camera.track(delta)
        camera.calc_gl_transform()

        scales = camera.get_scale_2d()
        # TODO: need to set scale in viewer settings, without triggering a
        # scale operation on this viewer
        viewer.update_widget()
        return True

    def ms_camera_orbit(self, viewer, event, data_x, data_y, msg=True):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            camera.orbit(self._start_x, self._start_y, x, y)
            self._start_x, self._start_y = x, y
            camera.calc_gl_transform()
            ## pos = tuple(camera.position.get())
            ## mst = "Camera position: (%.4f, %.4f, %.4f)" % pos
            ## if msg:
            ##     viewer.onscreen_message(mst, delay=0.5)
            tup = camera.position.get()

        elif event.state == 'down':
            self._start_x, self._start_y = x, y

        ## else:
        ##     viewer.onscreen_message(None)

        viewer.update_widget()
        return True

    def ms_camera_pan_delta(self, viewer, event, data_x, data_y, msg=True):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        x, y = self.get_win_xy(viewer)

        if event.state == 'move':
            dx, dy = x - self._start_x, self._start_y - y
            camera.pan_delta(dx, dy)
            self._start_x, self._start_y = x, y
            camera.calc_gl_transform()

        elif event.state == 'down':
            self._start_x, self._start_y = x, y
            ## if msg:
            ##     viewer.onscreen_message("Camera translate", delay=1.0)

        ## else:
        ##     viewer.onscreen_message(None)

        # TODO: need to get the updated pan position and set it in
        # viewer's settings without triggering a callback to the viewer
        # itself
        tup = camera.position.get()
        data_x, data_y = viewer.tform['data_to_native'].from_(tup[:2])

        viewer.update_widget()
        return True

    def kp_camera_reset(self, viewer, event, data_x, data_y):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        camera.reset()
        camera.calc_gl_transform()
        viewer.onscreen_message("Reset camera", delay=0.5)
        viewer.update_widget()
        return True

    def kp_camera_save(self, viewer, event, data_x, data_y):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        camera.save_positions()
        viewer.onscreen_message("Saved camera position", delay=0.5)
        return True

    def kp_camera_toggle3d(self, viewer, event, data_x, data_y):
        camera = self.get_camera(viewer)
        if camera is None:
            # this viewer doesn't have a camera
            return False

        renderer = viewer.renderer
        renderer.mode3d = not renderer.mode3d
        viewer.update_widget()
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


class PinchEvent(UIEvent):
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 rot_deg=None, scale=None, data_x=None, data_y=None,
                 viewer=None):
        super(PinchEvent, self).__init__()
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.rot_deg = rot_deg
        self.scale = scale
        self.data_x = data_x
        self.data_y = data_y
        self.viewer = viewer


class PanEvent(UIEvent):
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 delta_x=None, delta_y=None, data_x=None, data_y=None,
                 viewer=None):
        super(PanEvent, self).__init__()
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.delta_x = delta_x
        self.delta_y = delta_y
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
        self.event_names = ['keydown', 'keyup',
                            'btn-down', 'btn-move', 'btn-up',
                            'scroll', 'pinch', 'pan']
        self.eventmap = {}

        self._kbdmode = None
        self._kbdmode_types = ('held', 'oneshot', 'locked', 'softlock')
        self._kbdmode_type = 'held'
        self._kbdmode_type_default = 'softlock'
        self._delayed_reset = False
        self._modifiers = frozenset([])

        # Set up button mapping
        if btnmap is None:
            btnmap = {0x1: 'cursor', 0x2: 'wheel', 0x4: 'draw'}
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
                self.add_modifier(keyname, 'win')
        else:
            self.modifier_map = modifier_map

        # Set up mode mapping
        if mode_map is None:
            self.mode_map = {}
        else:
            self.mode_map = mode_map

        self._empty_set = frozenset([])
        self.mode_tbl = dict()

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

    def has_mode(self, mode_name):
        key = 'mode_%s' % mode_name
        return key in self.mode_map

    def remove_mode(self, mode_name):
        key = 'mode_%s' % mode_name
        del self.mode_map[key]

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
        if keyname is not None:
            # Key to launch this mode
            if keyname[0:2] == '__':
                keyname = keyname[2]
                self.mode_tbl[keyname] = bnch
            else:
                self.mode_map[keyname] = bnch
        self.mode_map['mode_%s' % mode_name] = bnch

    def set_mode(self, name, mode_type=None):
        if mode_type is None:
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
        except Exception:
            bnch = None
        self._kbdmode = None
        self._kbdmode_type = 'held'
        self._delayed_reset = False
        self.logger.debug("set keyboard mode reset")
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

    def get_button(self, btncode):
        return self.btnmap.get(btncode, None)

    def clear_event_map(self):
        self.eventmap = {}

    def map_event(self, mode, modifiers, trigger, eventname):
        self.eventmap[(mode, frozenset(tuple(modifiers)),
                       trigger)] = Bunch.Bunch(name=eventname)

    def register_for_events(self, viewer):
        # Add callbacks for interesting events
        viewer.add_callback('motion', self.window_motion)
        viewer.add_callback('button-press', self.window_button_press)
        viewer.add_callback('button-release', self.window_button_release)
        viewer.add_callback('key-press', self.window_key_press)
        viewer.add_callback('key-release', self.window_key_release)
        ## viewer.add_callback('drag-drop', self.window_drag_drop)
        viewer.add_callback('scroll', self.window_scroll)
        viewer.add_callback('map', self.window_map)
        viewer.add_callback('focus', self.window_focus)
        viewer.add_callback('enter', self.window_enter)
        viewer.add_callback('leave', self.window_leave)
        if viewer.has_callback('pinch'):
            viewer.add_callback('pinch', self.window_pinch)
        if viewer.has_callback('pan'):
            viewer.add_callback('pan', self.window_pan)

        for pfx in self.event_names:
            # TODO: add moded versions of callbacks?
            viewer.enable_callback('%s-none' % (pfx))

    def mode_key_down(self, viewer, keyname):
        """This method is called when a key is pressed and was not handled
        by some other handler with precedence, such as a subcanvas.
        """
        # Is this a mode key?
        if keyname not in self.mode_map:
            if (keyname not in self.mode_tbl) or (self._kbdmode != 'meta'):
                # No
                return False
            bnch = self.mode_tbl[keyname]
        else:
            bnch = self.mode_map[keyname]

        mode_name = bnch.name
        self.logger.debug("cur mode='%s' mode pressed='%s'" % (
            self._kbdmode, mode_name))

        if mode_name == self._kbdmode:
            # <== same key was pressed that started the mode we're in
            # standard handling is to close the mode when we press the
            # key again that started that mode
            self.reset_mode(viewer)
            return True

        if self._delayed_reset:
            # <== this shouldn't happen, but put here to reset handling
            # of delayed_reset just in case (see cursor up handling)
            self._delayed_reset = False
            return True

        if ((self._kbdmode in (None, 'meta')) or
            (self._kbdmode_type != 'locked') or (mode_name == 'meta')):
            if self._kbdmode is not None:
                self.reset_mode(viewer)

            # activate this mode
            if self._kbdmode in (None, 'meta'):
                mode_type = bnch.type
                if mode_type is None:
                    mode_type = self._kbdmode_type_default
                self.set_mode(mode_name, mode_type)
                if bnch.msg is not None:
                    viewer.onscreen_message(bnch.msg)

                return True

        return False

    def mode_key_up(self, viewer, keyname):
        """This method is called when a key is pressed in a mode and was
        not handled by some other handler with precedence, such as a
        subcanvas.
        """
        # Is this a mode key?
        if keyname not in self.mode_map:
            # <== no
            return False

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

        return False

    def window_map(self, viewer):
        return True

    def window_focus(self, viewer, has_focus):
        if not has_focus:
            # fixes a problem with not receiving key release events when the
            # window loses focus
            self._modifiers = frozenset([])
        return False

    def window_enter(self, viewer):
        return False

    def window_leave(self, viewer):
        return False

    def window_key_press(self, viewer, keyname):
        self.logger.debug("keyname=%s" % (keyname))
        # Is this a modifer key?
        if keyname in self.modifier_map:
            bnch = self.modifier_map[keyname]
            self._modifiers = self._modifiers.union(set([bnch.name]))
            return True

        if self.mode_key_down(viewer, keyname):
            return True

        trigger = 'kp_' + keyname
        try:
            if keyname == 'escape':
                idx = (None, self._empty_set, trigger)
            else:
                idx = (self._kbdmode, self._modifiers, trigger)
            emap = self.eventmap[idx]
            cbname = 'keydown-%s' % (emap.name)

        except KeyError:
            try:
                # TEMP: hack to get around the issue of how keynames
                # are generated--shifted characters with no modifiers
                idx = (self._kbdmode, self._empty_set, trigger)
                emap = self.eventmap[idx]
                cbname = 'keydown-%s' % (emap.name)

            except KeyError:
                # no entry for this mode, try non-mode entry
                try:
                    idx = (None, self._empty_set, trigger)
                    emap = self.eventmap[idx]
                    cbname = 'keydown-%s' % (emap.name)

                except KeyError:
                    cbname = 'key-down-%s' % str(self._kbdmode).lower()

        self.logger.debug("idx=%s" % (str(idx)))
        last_x, last_y = viewer.get_last_data_xy()

        event = KeyEvent(key=keyname, state='down', mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         data_x=last_x, data_y=last_y)
        return viewer.make_ui_callback_viewer(viewer, cbname, event, last_x, last_y)

    def window_key_release(self, viewer, keyname):
        self.logger.debug("keyname=%s" % (keyname))

        # Is this a modifer key?
        if keyname in self.modifier_map:
            bnch = self.modifier_map[keyname]
            self._modifiers = self._modifiers.difference(set([bnch.name]))
            return True

        if self.mode_key_up(viewer, keyname):
            return True

        trigger = 'kp_' + keyname
        try:
            idx = (self._kbdmode, self._modifiers, trigger)
            emap = self.eventmap[idx]
            cbname = 'keyup-%s' % (emap.name)

        except KeyError:
            try:
                idx = (self._kbdmode, self._empty_set, trigger)
                emap = self.eventmap[idx]
                cbname = 'keyup-%s' % (emap.name)

            except KeyError:
                try:
                    idx = (None, self._empty_set, trigger)
                    emap = self.eventmap[idx]
                    cbname = 'keyup-%s' % (emap.name)

                except KeyError:
                    cbname = 'key-up-%s' % str(self._kbdmode).lower()

        last_x, last_y = viewer.get_last_data_xy()

        event = KeyEvent(key=keyname, state='up', mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         data_x=last_x, data_y=last_y)

        return viewer.make_ui_callback_viewer(viewer, cbname, event, last_x, last_y)

    def window_button_press(self, viewer, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d btncode=%s" % (data_x, data_y,
                                                    hex(btncode)))
        self._button |= btncode
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False
        trigger = 'ms_' + button
        try:
            idx = (self._kbdmode, self._modifiers, trigger)
            emap = self.eventmap[idx]
            cbname = '%s-down' % (emap.name)

        except KeyError:
            # no entry for this mode, try non-mode entry
            try:
                idx = (None, self._modifiers, trigger)
                emap = self.eventmap[idx]
                cbname = '%s-down' % (emap.name)

            except KeyError:
                idx = None
                cbname = 'btn-down-%s' % str(self._kbdmode).lower()

        #self.logger.debug("Event map for %s" % (str(idx)))
        self.logger.debug("making callback for %s (mode=%s)" % (
            cbname, self._kbdmode))

        event = PointEvent(button=button, state='down', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback_viewer(viewer, cbname, event, data_x, data_y)

    def window_motion(self, viewer, btncode, data_x, data_y):

        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False
        trigger = 'ms_' + button
        try:
            idx = (self._kbdmode, self._modifiers, trigger)
            emap = self.eventmap[idx]
            cbname = '%s-move' % (emap.name)

        except KeyError:
            # no entry for this mode, try non-mode entry
            try:
                idx = (None, self._modifiers, trigger)
                emap = self.eventmap[idx]
                cbname = '%s-move' % (emap.name)

            except KeyError:
                idx = None
                cbname = 'btn-move-%s' % str(self._kbdmode).lower()

        ## self.logger.debug("making callback for %s (mode=%s)" % (
        ##     cbname, self._kbdmode))

        event = PointEvent(button=button, state='move', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback_viewer(viewer, cbname, event, data_x, data_y)

    def window_button_release(self, viewer, btncode, data_x, data_y):
        self.logger.debug("x,y=%d,%d button=%s" % (data_x, data_y,
                                                   hex(btncode)))
        self._button &= ~btncode
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False
        trigger = 'ms_' + button
        try:
            idx = (self._kbdmode, self._modifiers, trigger)
            # release mode if this is a oneshot mode
            if (self._kbdmode_type == 'oneshot') or (self._delayed_reset):
                self.reset_mode(viewer)
            emap = self.eventmap[idx]
            cbname = '%s-up' % (emap.name)

        except KeyError:
            # no entry for this mode, try non-mode entry
            try:
                idx = (None, self._modifiers, trigger)
                emap = self.eventmap[idx]
                cbname = '%s-up' % (emap.name)

            except KeyError:
                idx = None
                cbname = 'btn-up-%s' % str(self._kbdmode).lower()

        event = PointEvent(button=button, state='up', mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback_viewer(viewer, cbname, event, data_x, data_y)

    def window_scroll(self, viewer, direction, amount, data_x, data_y):
        try:
            idx = (self._kbdmode, self._modifiers, 'sc_scroll')
            emap = self.eventmap[idx]
            cbname = '%s-scroll' % (emap.name)

        except KeyError:
            # no entry for this mode, try non-mode entry
            try:
                idx = (None, self._modifiers, 'sc_scroll')
                emap = self.eventmap[idx]
                cbname = '%s-scroll' % (emap.name)

            except KeyError:
                idx = None
                cbname = 'scroll-%s' % str(self._kbdmode).lower()

        event = ScrollEvent(button='scroll', state='scroll', mode=self._kbdmode,
                            modifiers=self._modifiers, viewer=viewer,
                            direction=direction, amount=amount,
                            data_x=data_x, data_y=data_y)
        return viewer.make_ui_callback_viewer(viewer, cbname, event)

    def window_pinch(self, viewer, state, rot_deg, scale):
        btncode = 0
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False
        trigger = 'pi_pinch'
        try:
            idx = (self._kbdmode, self._modifiers, trigger)
            emap = self.eventmap[idx]
            cbname = '%s-pinch' % (emap.name)

        except KeyError:
            # no entry for this mode, try non-mode entry
            try:
                idx = (None, self._modifiers, trigger)
                emap = self.eventmap[idx]
                cbname = '%s-pinch' % (emap.name)

            except KeyError:
                idx = None
                cbname = 'pinch-%s' % (str(self._kbdmode).lower())

        last_x, last_y = viewer.get_last_data_xy()
        event = PinchEvent(button=button, state=state, mode=self._kbdmode,
                           modifiers=self._modifiers, viewer=viewer,
                           rot_deg=rot_deg, scale=scale,
                           data_x=last_x, data_y=last_y)

        self.logger.debug("making callback for %s (mode=%s)" % (
            cbname, self._kbdmode))
        return viewer.make_ui_callback_viewer(viewer, cbname, event)

    def window_pan(self, viewer, state, delta_x, delta_y):
        btncode = 0
        button = self.get_button(btncode)
        if button is None:
            self.logger.error("unrecognized button code (%x)" % (btncode))
            return False
        trigger = 'pa_pan'
        try:
            idx = (self._kbdmode, self._modifiers, trigger)
            emap = self.eventmap[idx]
            cbname = '%s-pan' % (emap.name)

        except KeyError:
            # no entry for this mode, try non-mode entry
            try:
                idx = (None, self._modifiers, trigger)
                emap = self.eventmap[idx]
                cbname = '%s-pan' % (emap.name)

            except KeyError:
                idx = None
                cbname = 'pan-%s' % (str(self._kbdmode).lower())

        last_x, last_y = viewer.get_last_data_xy()
        event = PanEvent(button=button, state=state, mode=self._kbdmode,
                         modifiers=self._modifiers, viewer=viewer,
                         delta_x=delta_x, delta_y=delta_y,
                         data_x=last_x, data_y=last_y)

        self.logger.debug("making callback for %s (mode=%s)" % (
            cbname, self._kbdmode))
        return viewer.make_ui_callback_viewer(viewer, cbname, event)


#END
