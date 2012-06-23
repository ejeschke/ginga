#
# Mixins.py -- Mixin classes for FITS viewer.
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:38:36 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import Bunch

class UIMixin(object):

    def __init__(self):
        self.ui_active = False
        
        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop', 
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     ):
            self.enable_callback(name)

    def ui_isActive(self):
        return self.ui_active
    
    def ui_setActive(self, tf):
        self.ui_active = tf
    
    ## def make_callback(self, name, *args, **kwdargs):
    ##     if hasattr(self, 'objects'):
    ##         # Invoke callbacks on all our layers that have the UI mixin
    ##         for obj in self.objects:
    ##             if isinstance(obj, UIMixin) and obj.ui_isActive():
    ##                 obj.make_callback(name, *args, **kwdargs)

    ##     return super(UIMixin, self).make_callback(name, *args, **kwdargs)

    def make_callback(self, name, *args, **kwdargs):
        """Invoke callbacks on all objects (i.e. layers) from the top to
        the bottom, returning when the first one returns True.  If none
        returns True, then make the callback on our 'native' layer.
        """
        if hasattr(self, 'objects'):
            # Invoke callbacks on all our layers that have the UI mixin
            num = len(self.objects) - 1
            while num >= 0:
                obj = self.objects[num]
                if isinstance(obj, UIMixin) and obj.ui_isActive():
                    res = obj.make_callback(name, *args, **kwdargs)
                    if res:
                        return res
                num -= 1

        if self.ui_active:
            return super(UIMixin, self).make_callback(name, *args, **kwdargs)


class FitsImageZoomMixin(object):
    """
    Mouse Operation and Bindings

    In a FitsImageZoom window:

    * the left mouse button is used for controlling the current "operation";
    * the middle wheel/button is used for zooming (scroll) and panning (press
      and drag) around the image (must be zoomed in);

    Key Bindings

    In a FitsImageZoom window the following command keys are active by default:

    * 1,2,3,...,9,0: zoom to 1x, 2x, ... 9x, 10x. If you hold down Ctrl
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
        press mouse button 1 and drag left or right horizontally (X axis).
        It will shift the colormap (mapping of values to colors), depending
        on how far you drag. The display will adjust dynamically. 
    """

    def __init__(self):

        self.canzoom = False
        self._ispanning = False
        self.cancut = False
        self.canflip = False
        self._iscutlow = False
        self._iscuthigh = False
        self._ischgcmap = False
        self.isctrldown = False
        self.isshiftdown = False

        # For panning
        self._pantype = 1
        self._start_x = 0
        self._start_y = 0
        ## self._start_panx = 0
        ## self._start_pany = 0
        self._start_src_x = 0
        self._start_src_y = 0
        self.t_autopanset = False
        
        # User defined keys
        self.keys = Bunch.Bunch()
        self.keys.zoom_in = ['+', '=']
        self.keys.zoom_out = ['-', '_']
        self.keys.zoom = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        self.keys.zoom_fit = ['backquote']
        self.keys.autozoom_on = ['doublequote']
        self.keys.autozoom_override = ['singlequote']
        self.keys.ctrl = ['control_l', 'control_r']
        self.keys.shift = ['shift_l', 'shift_r']
        self.keys.pan1 = ['q']
        self.keys.pan2 = ['space']
        self.keys.panset = ['p']
        self.keys.cut_low = [',']
        self.keys.cut_high = ['.']
        self.keys.autocuts_on = [':']
        self.keys.autocuts_override = [';']
        self.keys.chgcmap = ['/']
        self.keys.cut_auto = ['a']
        self.keys.flipx = ['[', '{']
        self.keys.flipy = [']', '}']
        self.keys.swapxy = ['backslash', '|']
        self.keys.cancel = ['escape']

        # Add callbacks for interesting events
        self.add_callback('motion', self.window_motion)
        self.add_callback('button-press', self.window_button_press)
        self.add_callback('button-release', self.window_button_release)
        self.add_callback('key-press', self.window_key_press)
        self.add_callback('key-release', self.window_key_release)
        ## self.add_callback('drag-drop', self.window_drag_drop)
        self.add_callback('scroll', self.window_scroll)
        self.add_callback('map', self.window_map)
        ## self.add_callback('focus', self.window_focus)
        ## self.add_callback('enter', self.window_enter)
        ## self.add_callback('leave', self.window_leave)

    def window_map(self, fitsimage):
        self.to_default_mode()

    def get_key_bindings(self, featkey):
        return self.keys[featkey]
    
    def get_key_features(self):
        return self.keys.keys()
    
    def set_key_bindings(self, featkey, symlist):
        self.keys[featkey] = symlist
    
    def window_key_press(self, fitsimage, keyname):
        if (keyname in self.keys.ctrl):
            self.set_kbdmouse_mask(0x10)
            self.isctrldown = True
        if (keyname in self.keys.shift):
            self.set_kbdmouse_mask(0x20)
            self.isshiftdown = True
        if (keyname in self.keys.cancel):
            self.reset()
            
        if self.canzoom:
            if (keyname in self.keys.pan1) and self.canpan:
                if self._ispanning:
                    self.pan_stop()
                    return True
                self.onscreen_message("Free panning (click to stop)",
                                      delay=1.0)
                self.set_kbdmouse_mask(0x1000)
                self.pan_start(ptype=1)
                return True
            ## elif (keyname in self.keys.pan2) and self.canpan:
            ##     if self._ispanning:
            ##         self.pan_stop()
            ##         self.reset_kbdmouse_mask(0x1000)
            ##         return True
            ##     self._start_x = 0
            ##     self.set_kbdmouse_mask(0x1000)
            ##     self.onscreen_message("Drag panning (Esc to stop)",
            ##                           delay=1.0)
            ##     self.pan_start(ptype=2)
            ##     return True
            elif (keyname in self.keys.panset):
                self._panset(self.last_data_x, self.last_data_y,
                             redraw=False)
                return True
            elif keyname in self.keys.zoom_out:
                self.zoom_out()
                self.onscreen_message(self.get_scale_text(), delay=1.0)
                return True
            elif keyname in self.keys.zoom_in:
                self.zoom_in()
                self.onscreen_message(self.get_scale_text(), delay=1.0)
                return True
            elif keyname in self.keys.zoom:
                if keyname == '0':
                    keyname = '10'
                zoomval = int(keyname)
                if self.isctrldown:
                    zoomval = -zoomval
                self.zoom_to(zoomval)
                self.onscreen_message(self.get_scale_text(), delay=1.0)
                return True
            elif keyname in self.keys.zoom_fit:
                self.zoom_fit()
                self.onscreen_message(self.get_scale_text(), delay=1.0)
                return True
            elif keyname in self.keys.autozoom_on:
                self.enable_autoscale('on')
                self.onscreen_message('Autozoom On', delay=1.0)
                return True
            elif keyname in self.keys.autozoom_override:
                self.enable_autoscale('override')
                self.onscreen_message('Autozoom Override', delay=1.0)
                return True
            
        if self.cancut:
            if keyname in self.keys.cut_low:
                self._iscutlow = True
                self.set_kbdmouse_mask(0x1000)
                self.onscreen_message("Cut low (drag mouse L-R)")
                return True
            elif keyname in self.keys.cut_high:
                self._iscuthigh = True
                self.set_kbdmouse_mask(0x1000)
                self.onscreen_message("Cut high (drag mouse L-R)")
                return True
            elif keyname in self.keys.chgcmap:
                self._ischgcmap = True
                self.set_kbdmouse_mask(0x1000)
                self.onscreen_message("Shift colormap (drag mouse L-R)")
                return True
            elif keyname in self.keys.cut_auto:
                self.onscreen_message("Auto cut levels", delay=1.0)
                self.auto_levels()
                return True
            elif keyname in self.keys.autocuts_on:
                self.enable_autolevels('on')
                self.onscreen_message('Autocuts On', delay=1.0)
                return True
            elif keyname in self.keys.autocuts_override:
                self.enable_autolevels('override')
                self.onscreen_message('Autocuts Override', delay=1.0)
                return True

        if self.canflip:
            if keyname in self.keys.flipx:
                flipx = not self.isshiftdown
                flipX, flipY, swapXY = self.get_transforms()
                self.transform(flipx, flipY, swapXY)
                self.onscreen_message("Flip X=%s" % flipx, delay=1.0)
                return True
            elif keyname in self.keys.flipy:
                flipy = not self.isshiftdown
                flipX, flipY, swapXY = self.get_transforms()
                self.transform(flipX, flipy, swapXY)
                self.onscreen_message("Flip Y=%s" % flipy, delay=1.0)
                return True
            elif keyname in self.keys.swapxy:
                swapxy = not self.isshiftdown
                flipX, flipY, swapXY = self.get_transforms()
                self.transform(flipX, flipY, swapxy)
                self.onscreen_message("Swap XY=%s" % swapxy, delay=1.0)
                return True


    def window_key_release(self, fitsimage, keyname):
        if (keyname in self.keys.ctrl):
            self.reset_kbdmouse_mask(0x10)
            self.isctrldown = False
        if (keyname in self.keys.shift):
            self.reset_kbdmouse_mask(0x20)
            self.isshiftdown = False


    def reset(self):
        self._iscutlow = False
        self._iscuthigh = False
        self._ischgcmap = False
        self.pan_stop()
        self.reset_kbdmouse_mask(0x1000)
        self.onscreen_message(None)
        
    def window_button_press(self, fitsimage, button, data_x, data_y):
        self.logger.debug("x,y=%d,%d button=%s" % (data_x, data_y,
                                                   hex(button)))
        x, y = self.last_win_x, self.last_win_y

        if button & 0x1:
            if self._ispanning:
                self.pan_set_origin(x, y)
                return True
            elif self._ischgcmap:
                self._start_x = x
                return True
            elif self._iscutlow or self._iscuthigh:
                self._start_x = x
                self._loval, self._hival = self.get_cut_levels()
                return True
            elif self.t_autopanset:
                self._panset(data_x, data_y, redraw=False)
            elif button == 0x21:
                self._panset(data_x, data_y, redraw=False)
                #return True
            elif button == 0x11:
                self.pan_set_origin(x, y)
                self.pan_start(ptype=2)
                return True

        elif button & 0x2:
            if not self.isctrldown:
                if self.canzoom and self.canpan:
                    ptype = 1
                    if self.isshiftdown:
                        self.pan_set_origin(x, y)
                        ptype = 2
                    self.pan_start(ptype=ptype)
                    return True

        elif button & 0x4:
            pass


    def window_button_release(self, fitsimage, button, data_x, data_y):

        x, y = self.last_win_x, self.last_win_y
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        if button & 0x1:
            if self._ispanning:
                self.pan_stop()
                return True
            elif self._ischgcmap:
                #self._tweak_colormap(x, y, 'set')
                self.onscreen_message(None)
                self._ischgcmap = False
                self.reset_kbdmouse_mask(0x1000)
                return True
            elif self._iscutlow:
                #self._cutlow_xy(x, y)
                self.onscreen_message(None)
                self._iscutlow = False
                self.reset_kbdmouse_mask(0x1000)
                return True
            elif self._iscuthigh:
                #self._cuthigh_xy(x, y)
                self.onscreen_message(None)
                self._iscuthigh = False
                self.reset_kbdmouse_mask(0x1000)
                return True

        elif button & 0x2:
            if self._ispanning:
                self.pan_stop()
                return True
            elif self.isctrldown:
                self.rgbmap.reset_cmap()
                return True
            
        elif button & 0x4:
            pass
            

    def window_motion(self, fitsview, button, data_x, data_y):
        x, y = self.last_win_x, self.last_win_y
        # self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        if button & 0x1:
            if self._ischgcmap:
                self._tweak_colormap(x, y, 'preview')
                return True

            elif self._iscutlow:
                self._cutlow_xy(x, y)
                return True

            elif self._iscuthigh:
                self._cuthigh_xy(x, y)
                return True
            
        if self._ispanning:
            if self._pantype == 2:
                if not (button & 0x1):
                    return False
            panx, pany = self.get_new_pan(x, y, ptype=self._pantype)
            self.set_pan(panx, pany, redraw=True)
            return True


    def window_scroll(self, fitsimage, direction):
        ## if self._ispanning:
        ##     return True
        #print "shiftdown=%s ctrldown=%s" % (self.isshiftdown, self.isctrldown)
        if self._iscutlow or self._iscuthigh:
            pct = 0.01
            if self.isshiftdown and self.isctrldown:
                pct = 0.00001
            elif self.isshiftdown:
                pct = 0.0001
            elif self.isctrldown:
                pct = 0.001

            if self._iscutlow:
                fn = self._cutlow_pct
            else:
                fn = self._cuthigh_pct
                
            if direction == 'up':
                fn(pct)
            elif direction == 'down':
                fn(-pct)
            return True
            
        if self.isshiftdown or self.isctrldown:
            pct = 0.01
            if self.isshiftdown:
                pct = 0.001
            if direction in ('up', 'left'):
                self._cut_pct(pct)
            elif direction in ('down', 'right'):
                self._cut_pct(-pct)
            return True

        elif self.canzoom:
            if direction == 'up':
                self.zoom_in()
            elif direction == 'down':
                self.zoom_out()
            self.onscreen_message(self.get_scale_text(), delay=1.0)
            return True


    def get_new_pan(self, win_x, win_y, ptype=1):

        win_wd, win_ht = self.get_window_size()
        if ptype == 1:
            if (win_x >= win_wd):
                win_x = win_wd - 1
            if (win_y >= win_ht):
                win_y = win_ht - 1

            # Figure out data x,y based on percentage of X axis
            # and Y axis
            panx = float(win_x) / float(win_wd - 1)
            pany = 1.0 - (float(win_y) / float(win_ht - 1))

        elif ptype == 2:
            if self._start_x == 0:
                # user has not held the mouse button yet
                # return current pan values
                return self.get_pan()

            # OLD PAN 2 METHOD
            ## panx = min(1.0, max(0.0, self._start_panx +
            ##                     float(self._start_x - win_x) / float(win_wd)))
            ## pany = min(1.0, max(0.0, self._start_pany +
            ##                     float(win_y - self._start_y) / float(win_ht)))
            # NEW PAN 2 METHOD
            delta_x = self._start_x - win_x
            delta_y = win_y - self._start_y
            pxwd, pxht, src_x, src_y = self.get_scaling_info()
            panx = min(1.0, max(0.0, float(self._start_src_x + delta_x) /
                                float(pxwd)))
            pany = min(1.0, max(0.0, float(self._start_src_y + delta_y) /
                                float(pxht)))

        # Account for user transformations
        flipX, flipY, swapXY = self.get_transforms()
        if flipX:
            panx = 1.0 - panx
        if flipY:
            pany = 1.0 - pany
        if swapXY:
            panx, pany = pany, panx

        return (panx, pany)

    def _panset(self, data_x, data_y, redraw=True):
        try:
            self.onscreen_message("Pan position set", delay=1.0)

            res = self.panset_xy(data_x, data_y, redraw=redraw)
            return res

        except FitsImage.FitsImageCoordsError, e:
            # coords are not within the data area
            pass

    def _tweak_colormap(self, x, y, mode):
        dx = x - self._start_x
        win_wd, win_ht = self.get_window_size()
        pct = float(dx) / float(win_wd)
        self.shift_cmap(pct)

    def _cutlow_pct(self, pct):
        minval, maxval = self.get_minmax()
        spread = maxval - minval
        loval, hival = self.get_cut_levels()
        loval = loval + (pct * spread)
        self.onscreen_message("Cut low: %.4f" % (loval),
                              redraw=False)
        self.cut_levels(loval, hival, redraw=True)

    def _cutlow_xy(self, x, y):
        win_wd, win_ht = self.get_window_size()
        pct = float(x) / float(win_wd)
        minval, maxval = self.get_minmax()
        spread = maxval - minval
        loval, hival = self.get_cut_levels()
        loval = minval + (pct * spread)
        self.onscreen_message("Cut low: %.4f" % (loval),
                              redraw=False)
        self.cut_levels(loval, hival, redraw=True)

    def _cuthigh_pct(self, pct):
        minval, maxval = self.get_minmax()
        spread = maxval - minval
        loval, hival = self.get_cut_levels()
        hival = hival - (pct * spread)
        self.onscreen_message("Cut high: %.4f" % (hival),
                              redraw=False)
        self.cut_levels(loval, hival, redraw=True)

    def _cuthigh_xy(self, x, y):
        win_wd, win_ht = self.get_window_size()
        pct = 1.0 - (float(x) / float(win_wd))
        minval, maxval = self.get_minmax()
        spread = maxval - minval
        loval, hival = self.get_cut_levels()
        hival = maxval - (pct * spread)
        self.onscreen_message("Cut high: %.4f" % (hival),
                              redraw=False)
        self.cut_levels(loval, hival, redraw=True)

    def _cut_pct(self, pct):
        minval, maxval = self.get_minmax()
        spread = maxval - minval
        loval, hival = self.get_cut_levels()
        loval = loval + (pct * spread)
        hival = hival - (pct * spread)
        self.onscreen_message("Cut low: %.4f  high: %.4f" % (
            loval, hival), delay=1.0, redraw=False)
        self.cut_levels(loval, hival, redraw=True)

    def to_default_mode(self):
        self._ispanning = False
        self.switch_cursor('pick')
        
    def pan_start(self, ptype=1):
        # If already panning then ignore multiple keystrokes
        if self._ispanning:
            return
        self._pantype = ptype
        self.switch_cursor('pan')
        self._ispanning = True
        
    def pan_set_origin(self, win_x, win_y):
        #self._start_panx, self._start_pany = self.get_pan()
        pxwd, pxht, src_x, src_y = self.get_scaling_info()
        panx, pany = self.get_pan()
        self._start_src_x = int(round(panx * pxwd))
        self._start_src_y = int(round(pany * pxht))

        self._start_x = win_x
        self._start_y = win_y
        
    def pan_stop(self):
        self._ispanning = False
        self.reset_kbdmouse_mask(0x1000)
        self._start_x = 0
        self._pantype = 1
        self.to_default_mode()
        
    def enable_zoom(self, tf):
        self.canzoom = tf
        
    def enable_cuts(self, tf):
        self.cancut = tf
        
    def enable_flip(self, tf):
        self.canflip = tf

# END
