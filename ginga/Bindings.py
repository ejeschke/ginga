#
# Bindings.py -- Bindings classes for Ginga FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga.misc import Bunch
from ginga import AutoCuts

class ImageViewBindings(object):
    """
    Mouse Operation and Bindings

    In a ImageViewEvent-based window with an instance of this bindings class:

    * the left mouse button is used for controlling the current "operation";
    * the middle wheel/button is used for zooming (scroll) and panning (press
      and drag) around the image (must be zoomed in);

    Key Bindings

    In a ImageViewEvent-based window the following command keys are active
    by default:

    * 1,2,3,...,9,0: zoom to 1x, 2x, ... 9x, 10x. If you hold down Shift
        key while pressing it will set to 1/2, 1/3, etc.
    * (backquote "`"): zoom to fit window
    * (double quote '"'): turn autozoom on; new images will be fit to the
       window
    * (single quote "'"): turn autozoom to override; new images will be fit
      to the window until the user zooms the image
    * (minus "-", underscore "_"): zoom out
    * (equal "=", plus "+"): zoom in
    * (left bracket "["): flip X (holding Shift (left brace "{") restores X
      to normal orientation)
    * (right bracket "]"): flip Y (holding Shift (right brace "}") restores Y
      to normal orientation)
    * (backslash \): swap XY (holding Shift (bar "|") restores XY to normal
      orientation)
    * a: auto cut levels
    * (colon ":"): turn autocuts on; new images will be auto cut levels
    * (semicolon ";"): turn autocuts to override; new images will be auto
      cut levels until the user changes cuts manually
    * (comma ','): set the low cut level. Press and release the key, then
        press mouse button 1 and drag left or right horizontally (X axis).
        It will set the low cut value to a percentage between min and max,
        depending on how far you drag. The display will adjust dynamically.
    * (period '.'): set the high cut level. Press and release the key, then
        press mouse button 1 and drag left or right horizontally (X axis).
        It will set the high cut value to a percentage between min and max,
        depending on how far you drag. The display will adjust dynamically.
    * (slash '/'): shift the color map. Press and release the key, then
        press mouse button 1 and drag around the window.  Dragging vertically
        stretches the colormap and dragging horizontally shifts it, depending
        on how far you drag. The display will adjust dynamically.
    p: sets the future pan position below the cursor
    c: centers the image by placing the pan position centrally
    r: rotate the image.  Press and release the key, then press mouse button
         1 and drag left or right horizontally (X axis).  The image is rotated
         by an amount proportional to the drag distance.
    R: set the rotation to 0 deg (no rotation).
    q: Start free panning.  Press mouse button 1 and drag around the window.
         The image will be panned in the direction you drag.
    """

    def __init__(self, logger):
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

        # User defined keys
        self.keys = Bunch.Bunch()
        self.keys.zoom_in = ['+', '=']
        self.keys.zoom_out = ['-', '_']
        self.keys.zoom = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        self.keys.zoom_inv = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')']
        self.keys.zoom_fit = ['backquote']
        self.keys.autozoom_on = ['doublequote']
        self.keys.autozoom_override = ['singlequote']
        # self.keys.ctrl = ['control_l', 'control_r']
        # self.keys.shift = ['shift_l', 'shift_r']
        self.keys.draw = ['space']
        self.keys.pan_free = ['q']
        self.keys.pan_drag = []
        self.keys.pan_set = ['p']
        self.keys.center = ['c']
        self.keys.cut_low = ['<']
        self.keys.cut_high = ['>']
        self.keys.cut_all = ['.']
        self.keys.cut_255 = ['A']
        self.keys.cut_auto = ['a']
        self.keys.autocuts_on = [':']
        self.keys.autocuts_override = [';']
        self.keys.cmap_warp = ['/']
        self.keys.cmap_restore = ['?']
        self.keys.flip_x = ['[', '{']
        self.keys.flip_y = [']', '}']
        self.keys.swap_xy = ['backslash', '|']
        self.keys.rotate = ['r']
        self.keys.rotate_reset = ['R']
        self.keys.cancel = ['escape']

        # User defined buttons
        self.btns = Bunch.Bunch()
        self.btns.rotate = []
        self.btns.cmapwarp = []
        self.btns.cmaprest = []
        self.btns.pan = []
        self.btns.freepan = []
        self.btns.cutlo = []
        self.btns.cuthi = []
        self.btns.cutall = []
        self.btns.panset = []

        # User defined scrolls
        self.scrs = Bunch.Bunch()
        self.scrs.contrast_coarse = []
        self.scrs.contrast_fine = []
        self.scrs.zoom = []
        self.scrs.zoom_coarse = []
        self.scrs.zoom_fine = []

        self.autocuts = AutoCuts.ZScale(self.logger)

        self.features = dict(
            # name, attr pairs
            pan='canpan', zoom='canzoom', cuts='cancut', cmap='cancmap',
            flip='canflip', rotate='canrotate')


    def window_map(self, fitsimage):
        self.to_default_mode(fitsimage)

    def set_bindings(self, fitsimage):

        fitsimage.add_callback('map', self.window_map)

        bindmap = fitsimage.get_bindmap()
        bindmap.clear_event_map()

        # Set up modifier mapping
        self.setup_default_modmap(fitsimage, bindmap)

        # Set up mouse button mapping
        self.setup_default_btnmap(fitsimage, bindmap)
        
        # Set up key bindings
        self.setup_default_key_events(fitsimage, bindmap)

        # Set up pointer bindings
        self.setup_default_btn_events(fitsimage, bindmap)
        
    def set_modifier(self, fitsimage, name, modtype='oneshot'):
        bindmap = fitsimage.get_bindmap()
        bindmap.set_modifier(name, modtype=modtype)
        
    def get_key_bindings(self, featkey):
        return self.keys[featkey]
    
    def get_key_features(self):
        return self.keys.keys()
    
    def set_key_bindings(self, featkey, symlist):
        self.keys[featkey] = symlist

    def setup_default_modmap(self, fitsimage, bindmap):

        # Establish our modifier keys.
        bindmap.clear_modifier_map()

        # Here we could change the meaning of standard modifiers
        # (i.e. shift becomes ctrl, etc.) or define new modifiers.
        for keyname in ('shift_l', 'shift_r'):
            bindmap.add_modifier(keyname, 'shift')
        for keyname in ('control_l', 'control_r'):
            bindmap.add_modifier(keyname, 'ctrl')
        for keyname in ('meta_right',):
            bindmap.add_modifier(keyname, 'draw')
        
    def setup_default_btnmap(self, fitsimage, bindmap):
        
        # Establish our names for the mouse or trackpad bindings
        bindmap.clear_button_map()

        # e.g. left btn == 'left', scroll wheel == 'middle', right == 'right'
        bindmap.map_button(0x0, 'nobtn')
        bindmap.map_button(0x1, 'left')
        bindmap.map_button(0x2, 'middle')
        bindmap.map_button(0x4, 'right')
        
    def setup_default_key_events(self, fitsimage, bindmap):

        for name in self.get_key_features():
            
            for key in self.get_key_bindings(name):
                bindmap.map_event(None, key, name)

            # Register for this symbolic event if we have a handler for it
            try:
                cb_method = getattr(self, 'kp_%s' % name)

                fitsimage.set_callback('keydown-%s' % name, cb_method)
            except AttributeError:
                pass

    def setup_default_btn_events(self, fitsimage, bindmap):
        
        # Generate standard symbolic mouse events for unmodified buttons:
        # xxxxx-{down, move, up}
        # e.g. 'left' button down generates 'cursor-down', moving the mouse
        # with no button pressed generates 'none-move', etc.
        for btnname, evtname in (('nobtn', 'none'), ('left', 'cursor'),
                                 ('middle', 'wheel'), ('right', 'draw')):
            bindmap.map_event(None, btnname, evtname)

        bindmap.map_event('shift', 'left', 'panset')
        bindmap.map_event('ctrl', 'left', 'pan')
        bindmap.map_event(None, 'middle', 'freepan')
        bindmap.map_event('ctrl', 'right', 'cmapwarp')
        bindmap.map_event('ctrl', 'middle', 'cmaprest')
        # NOTE: name 'scroll' is hardwired for the scrolling action
        bindmap.map_event(None, 'scroll', 'zoom')
        bindmap.map_event('shift', 'scroll', 'zoom-fine')
        bindmap.map_event('ctrl', 'scroll', 'zoom-coarse')

        # Mouse operations that are invoked by a preceeding key
        for name in ('rotate', 'cmapwarp', 'cutlo', 'cuthi', 'cutall',
                        'draw', 'pan', 'freepan'):
            bindmap.map_event(name, 'left', name)

        # Now register our actions (below) for these symbolic events
        for name in ('cursor', 'wheel', 'draw', 'rotate', 'cmapwarp',
                     'pan', 'freepan', 'cutlo', 'cuthi', 'cutall'):
            method = getattr(self, 'ms_'+name)
            for action in ('down', 'move', 'up'):
                fitsimage.set_callback('%s-%s' % (name, action), method)

        fitsimage.set_callback('panset-down', self.ms_panset)
        fitsimage.set_callback('cmaprest-down', self.ms_cmaprest)

        fitsimage.set_callback('zoom-scroll', self.sc_zoom)
        fitsimage.set_callback('zoom-coarse-scroll',
                               self.sc_zoom_coarse)
        fitsimage.set_callback('zoom-fine-scroll', self.sc_zoom_fine)

    def reset(self, fitsimage):
        self.reset_modifier(fitsimage)
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
            # This is a "free pan", similar to dragging the canvas
            # under the "lens" or "viewport".
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
            if fitsimage.get_pan_reverse():
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
            delta_x = (self._start_x - off_x) / scale_x
            delta_y = (self._start_y - off_y) / scale_y
            
            data_x = self._start_panx + delta_x
            data_y = self._start_pany + delta_y
            
        return (data_x, data_y)

    def _panset(self, fitsimage, data_x, data_y, msg=True, redraw=True):
        try:
            if msg:
                fitsimage.onscreen_message("Pan position set", delay=0.4)

            res = fitsimage.panset_xy(data_x, data_y, redraw=redraw)
            return res

        except ImageView.ImageViewCoordsError, e:
            # coords are not within the data area
            pass

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

    def _adjust_contrast(self, fitsimage, direction, pct):
        if direction in ('up', 'left'):
            self._cut_pct(fitsimage, pct)
        elif direction in ('down', 'right'):
            self._cut_pct(fitsimage, -pct)

    def _scale_image(self, fitsimage, direction, factor, msg=True):
        rev = fitsimage.get_pan_reverse()
        scale_x, scale_y = fitsimage.get_scale_xy()
        if direction == 'up':
            if not rev:
                mult = 1.0 + factor
            else:
                mult = 1.0 - factor
        elif direction == 'down':
            if not rev:
                mult = 1.0 - factor
            else:
                mult = 1.0 + factor
        scale_x, scale_y = scale_x * mult, scale_y * mult
        fitsimage.scale_to(scale_x, scale_y)
        if msg:
            fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                       delay=0.4)

    def _rotate_xy(self, fitsimage, x, y, msg=True):
        win_wd, win_ht = fitsimage.get_window_size()
        pct = float(x) / float(win_wd)
        deg = 360.0 * pct
        if msg:
            fitsimage.onscreen_message("Rotate: %.2f" % (deg),
                                       redraw=False)
        fitsimage.rotate(deg)

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
        rgbmap = fitsimage.get_rgbmap()
        rgbmap.reset_sarr()
        if msg:
            fitsimage.onscreen_message("Restored color map", delay=0.5)
        return True


    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_draw(self, fitsimage, action, data_x, data_y, msg=True):
        # Used to set up drawing for one-button devices
        self.set_modifier(fitsimage, 'draw')
        return True

    def kp_pan_free(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canpan:
            self.set_modifier(fitsimage, 'freepan')
            if msg:
                fitsimage.onscreen_message("Free panning (drag mouse)",
                                           delay=1.0)
        return True

    def kp_pan_set(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canpan:
            self._panset(fitsimage, data_x, data_y, redraw=True,
                         msg=msg)
        return True

    def kp_center(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canpan:
            fitsimage.center_image()
        return True

    def kp_zoom_out(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canzoom:
            fitsimage.zoom_out()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_in(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canzoom:
            fitsimage.zoom_in()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            zoomval = (self.keys.zoom.index(keyname) + 1)
            fitsimage.zoom_to(zoomval)
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_inv(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canzoom:
            zoomval = - (self.keys.zoom_inv.index(keyname) + 1)
            fitsimage.zoom_to(zoomval)
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_zoom_fit(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canzoom:
            fitsimage.zoom_fit()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=1.0)
        return True

    def kp_autozoom_on(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canzoom:
            fitsimage.enable_autozoom('on')
            if msg:
                fitsimage.onscreen_message('Autozoom On', delay=1.0)
        return True

    def kp_autozoom_override(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canzoom:
            fitsimage.enable_autozoom('override')
            if msg:
                fitsimage.onscreen_message('Autozoom Override', delay=1.0)
        return True
            
    def kp_cut_low(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancut:
            self.set_modifier(fitsimage, 'cutlo')
            if msg:
                fitsimage.onscreen_message("Cut low (drag mouse L-R)")
        return True

    def kp_cut_high(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancut:
            self.set_modifier(fitsimage, 'cuthi')
            if msg:
                fitsimage.onscreen_message("Cut high (drag mouse L-R)")
        return True

    def kp_cut_all(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancut:
            self.set_modifier(fitsimage, 'cutall')
            if msg:
                fitsimage.onscreen_message("Set cut levels (drag mouse)")
        return True

    def kp_cut_255(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancut:
            fitsimage.cut_levels(0.0, 255.0, no_reset=True)
        return True

    def kp_cut_auto(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancut:
            if msg:
                fitsimage.onscreen_message("Auto cut levels", delay=1.0)
            fitsimage.auto_levels()
        return True

    def kp_autocuts_on(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancut:
            fitsimage.enable_autocuts('on')
            if msg:
                fitsimage.onscreen_message('Autocuts On', delay=1.0)
        return True

    def kp_autocuts_override(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancut:
            fitsimage.enable_autocuts('override')
            if msg:
                fitsimage.onscreen_message('Autocuts Override', delay=1.0)
        return True

    def kp_cmap_warp(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancmap:
            self.set_modifier(fitsimage, 'cmapwarp')
            if msg:
                fitsimage.onscreen_message("Shift and stretch colormap (drag mouse)",
                                           delay=1.0)
        return True

    def kp_cmap_restore(self, fitsimage, action, data_x, data_y, msg=True):
        if self.cancmap:
            self.restore_colormap(fitsimage, msg=msg)
        return True

    def kp_flip_x(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canflip:
            flipx = (keyname == '[')
            flipX, flipY, swapXY = fitsimage.get_transforms()
            fitsimage.transform(flipx, flipY, swapXY)
            if msg:
                fitsimage.onscreen_message("Flip X=%s" % flipx, delay=1.0)
        return True

    def kp_flip_y(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canflip:
            flipy = (keyname == ']')
            flipX, flipY, swapXY = fitsimage.get_transforms()
            fitsimage.transform(flipX, flipy, swapXY)
            if msg:
                fitsimage.onscreen_message("Flip Y=%s" % flipy, delay=1.0)
        return True

    def kp_swap_xy(self, fitsimage, keyname, data_x, data_y, msg=True):
        if self.canflip:
            swapxy = (keyname == 'backslash')
            flipX, flipY, swapXY = fitsimage.get_transforms()
            fitsimage.transform(flipX, flipY, swapxy)
            if msg:
                fitsimage.onscreen_message("Swap XY=%s" % swapxy, delay=1.0)
        return True

    def kp_rotate_reset(self, fitsimage, action, data_x, data_y):
        if self.canrotate:
            fitsimage.rotate(0.0)
        return True

    def kp_rotate(self, fitsimage, action, data_x, data_y, msg=True):
        if self.canrotate:
            self.set_modifier(fitsimage, 'rotate')
            if msg:
                fitsimage.onscreen_message("Rotate (drag mouse L-R)",
                                           delay=1.0)
        return True


    #####  MOUSE ACTION CALLBACKS #####

    def ms_cursor(self, fitsimage, action, data_x, data_y):
        return True

    def ms_wheel(self, fitsimage, action, data_x, data_y):
        return True

    def ms_draw(self, fitsimage, action, data_x, data_y):
        return True

    def ms_rotate(self, fitsimage, action, data_x, data_y, msg=True):
        """Rotate the image by dragging the cursor left or right.
        """
        if not self.canrotate:
            return True

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
        if self.cancmap:
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
        if self.canpan:
            self._panset(fitsimage, data_x, data_y, redraw=True,
                         msg=msg)
        return True

    #####  SCROLL ACTION CALLBACKS #####

    def sc_contrast_coarse(self, fitsimage, direction, data_x, data_y,
                           msg=True):
        """Adjust contrast interactively by setting the low AND high cut
        levels.  This function adjusts it coarsely.
        """
        if self.cancut:
            self._adjust_contrast(fitsimage, direction, 0.01, msg=msg)
        return True

    def sc_contrast_fine(self, fitsimage, direction, data_x, data_y,
                         msg=True):
        """Adjust contrast interactively by setting the low AND high cut
        levels.  This function adjusts it finely.
        """
        if self.cancut:
            self._adjust_contrast(fitsimage, direction, 0.001, msg=msg)
        return True

    def sc_zoom(self, fitsimage, direction, data_x, data_y, msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by the zoom steps configured under Preferences.
        """
        if self.canzoom:
            rev = fitsimage.get_pan_reverse()
            if direction == 'up':
                if not rev:
                    fitsimage.zoom_in()
                else:
                    fitsimage.zoom_out()
            elif direction == 'down':
                if not rev:
                    fitsimage.zoom_out()
                else:
                    fitsimage.zoom_in()
            if msg:
                fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                           delay=0.4)
        return True

    def sc_zoom_coarse(self, fitsimage, direction, data_x, data_y,
                       msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if self.canzoom:
            self._scale_image(fitsimage, direction, 0.20, msg=msg)
        return True

    def sc_zoom_fine(self, fitsimage, direction, data_x, data_y,
                     msg=True):
        """Interactively zoom the image by scrolling motion.
        This zooms by adjusting the scale in x and y coarsely.
        """
        if self.canzoom:
            self._scale_image(fitsimage, direction, 0.08, msg=msg)
        return True


class BindingMapError(Exception):
    pass

class BindingMapper(object):
    """The BindingMapper class maps physical events (key presses, button
    clicks, mouse movement, etc) into logical events.  By registering for
    logical events, plugins and other event handling code doesn't need to
    care about the physical controls bindings.  The bindings can be changed
    and everything continues to work.
    """

    def __init__(self, logger, btnmap=None, modmap=None):
        super(BindingMapper, self).__init__()

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

    def set_modifier_map(self, modmap):
        self.modmap = modmap
        
    def clear_modifier_map(self):
        self.modmap = {}

    def get_modifiers(self):
        res = set([])
        for keyname, bnch in self.modmap.items():
            res.add(bnch.name)
        return res

    def add_modifier(self, keyname, modname, modtype='held'):
        assert modtype in self._kbdmod_types, \
               ValueError("Bad modifier type '%s': must be one of %s" % (
            modtype, self._kbdmod_types))

        bnch = Bunch.Bunch(name=modname, type=modtype)
        self.modmap[keyname] = bnch
        
    def set_modifier(self, name, modtype='oneshot'):
        assert modtype in self._kbdmod_types, \
               ValueError("Bad modifier type '%s': must be one of %s" % (
            modtype, self._kbdmod_types))
        self._kbdmod = name
        self._kbdmod_type = modtype
        
    def reset_modifier(self):
        self._kbdmod = None
        self._kbdmod_type = 'held'
        self._delayed_reset = False
        
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
                    self.reset_modifier()
                return True
                
            if self._delayed_reset:
                if bnch.name == self._kbdmod:
                    self._delayed_reset = False
                return False
            self._kbdmod = bnch.name
            self._kbdmod_type = bnch.type
            return True
        
        try:
            idx = (None, keyname)
            emap = self.eventmap[idx]

        except KeyError:
            return False

        cbname = 'keydown-%s' % (emap.name)
        last_x, last_y = fitsimage.get_last_data_xy()

        return fitsimage.make_callback(cbname, keyname, last_x, last_y)
            

    def window_key_release(self, fitsimage, keyname):
        self.logger.debug("keyname=%s" % (keyname))
        # Is this a modifier key?
        if keyname in self.modmap:
            bnch = self.modmap[keyname]
            if (self._kbdmod == bnch.name) and (bnch.type == 'held'):
                if self._button == 0:
                    self.reset_modifier()
                else:
                    self._delayed_reset = True
            return True
        
        try:
            idx = (None, keyname)
            emap = self.eventmap[idx]

        except KeyError:
            return False

        cbname = 'keyup%s' % (emap.name)
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
                self.reset_modifier()
            emap = self.eventmap[idx]

        except KeyError:
            #self.logger.warn("No button map binding for %s" % (str(btncode)))
            return False

        cbname = '%s-up' % (emap.name)
        return fitsimage.make_callback(cbname, 'up', data_x, data_y)
            

    def window_scroll(self, fitsimage, direction):
        try:
            idx = (self._kbdmod, 'scroll')
            emap = self.eventmap[idx]

        except KeyError:
            return False

        data_x, data_y = fitsimage.get_last_data_xy()

        cbname = '%s-scroll' % (emap.name)
        return fitsimage.make_callback(cbname, direction, data_x, data_y)


#END
