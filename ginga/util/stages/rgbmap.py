# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import ColorDist, trcalc
from ginga import cmap as mod_cmap
from ginga import imap as mod_imap

from .base import Stage, StageAction, StageError


class RGBMapError(StageError):
    pass


class RGBMap(Stage):

    _stagename = 'rgb-mapper'

    def __init__(self):
        super().__init__()

        self.rgbmap = None
        self.calg_names = ColorDist.get_dist_names()
        self.cmap_names = mod_cmap.get_names()
        self.imap_names = mod_imap.get_names()
        self.order = 'RGB'

        self._calg_name = 'linear'
        self._cmap_name = 'gray'
        self._imap_name = 'ramp'
        self._invert_cmap = False
        self._rotate_cmap_pct = 0.0
        self._contrast = 0.5
        self._brightness = 0.5

        self.viewer = None
        self.fv = None

    def build_gui(self, container):
        from ginga.gw import Widgets, ColorBar

        self.viewer = self.pipeline.get('viewer')
        self.fv = self.pipeline.get("fv")
        top = Widgets.VBox()

        # create and initialize RGB mapper
        # TODO: currently hash size cannot be changed
        from ginga.RGBMap import RGBMapper
        self.rgbmap = RGBMapper(self.logger)
        self.rgbmap.get_settings().set(color_algorithm=self._calg_name,
                                       color_map=self._cmap_name,
                                       intensity_map=self._imap_name,
                                       color_map_invert=self._invert_cmap,
                                       color_map_rot_pct=self._rotate_cmap_pct,
                                       contrast=self._contrast,
                                       brightness=self._brightness)
        self.rgbmap.add_callback('changed', self.rgbmap_changed_cb)

        self.settings_keys = list(self.rgbmap.settings_keys)
        self.settings_keys.remove('color_hashsize')

        fr = Widgets.Frame("Color Distribution")

        captions = (('Algorithm:', 'label', 'Algorithm', 'combobox'),
                    #('Table Size:', 'label', 'Table Size', 'entryset'),
                    ('Dist Defaults', 'button'))

        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)
        self.w.calg_choice = b.algorithm
        #self.w.table_size = b.table_size
        b.algorithm.set_tooltip("Choose a color distribution algorithm")
        #b.table_size.set_tooltip("Set size of the distribution hash table")
        b.dist_defaults.set_tooltip("Restore color distribution defaults")
        b.dist_defaults.add_callback('activated',
                                     lambda w: self.set_default_distmaps())

        combobox = b.algorithm
        options = []
        for name in self.calg_names:
            options.append(name)
            combobox.append_text(name)
        try:
            index = self.calg_names.index(self._calg_name)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_calg_cb)

        fr.set_widget(w)
        top.add_widget(fr, stretch=0)

        # COLOR MAPPING OPTIONS
        fr = Widgets.Frame("Color Mapping")

        captions = (('Colormap:', 'label', 'Colormap', 'combobox'),
                    ('Intensity:', 'label', 'Intensity', 'combobox'),
                    ('Rotate:', 'label', 'rotate_cmap', 'hscale'),
                    ('Invert CMap', 'checkbutton', 'Unrotate CMap', 'button'),
                    ('Color Defaults', 'button', 'Copy from viewer', 'button'))
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)
        self.w.cmap_choice = b.colormap
        self.w.imap_choice = b.intensity

        b.invert_cmap.set_tooltip("Invert color map")
        b.invert_cmap.set_state(False)
        b.invert_cmap.add_callback('activated', self.invert_cmap_cb)

        b.rotate_cmap.set_tracking(False)
        b.rotate_cmap.set_limits(0, 100, incr_value=1)
        b.rotate_cmap.set_value(0)
        b.rotate_cmap.add_callback('value-changed', self.rotate_cmap_cb)
        b.rotate_cmap.set_tooltip("Rotate the colormap")

        b.colormap.set_tooltip("Choose a color map for this image")
        b.intensity.set_tooltip("Choose an intensity map for this image")
        b.unrotate_cmap.set_tooltip("Undo cmap rotation")
        b.unrotate_cmap.add_callback('activated', self.unrotate_cmap_cb)
        b.color_defaults.set_tooltip("Restore all color map settings to defaults")
        b.color_defaults.add_callback('activated',
                                      lambda w: self.set_default_cmaps())
        fr.set_widget(w)

        combobox = b.colormap
        options = []
        for name in self.cmap_names:
            options.append(name)
            combobox.append_text(name)
        try:
            index = self.cmap_names.index(self._cmap_name)
        except Exception:
            index = self.cmap_names.index('gray')
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_cmap_cb)

        combobox = b.intensity
        options = []
        for name in self.imap_names:
            options.append(name)
            combobox.append_text(name)
        try:
            index = self.imap_names.index(self._imap_name)
        except Exception:
            index = self.imap_names.index('ramp')
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_imap_cb)

        b.copy_from_viewer.set_tooltip("Copy settings from viewer")
        b.copy_from_viewer.add_callback('activated', self.copy_from_viewer_cb)

        top.add_widget(fr, stretch=0)

        # CONTRAST MANIPULATIONS
        fr = Widgets.Frame("Contrast and Brightness (Bias)")

        captions = (('Contrast:', 'label', 'contrast', 'hscale'),
                    ('Brightness:', 'label', 'brightness', 'hscale'),
                    ('_cb1', 'spacer', '_hbox_cb', 'hbox'))
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.contrast.set_tracking(False)
        b.contrast.set_limits(0, 100, incr_value=1)
        b.contrast.set_value(50)
        b.contrast.add_callback('value-changed', self.contrast_set_cb)
        b.contrast.set_tooltip("Set contrast for the viewer")

        b.brightness.set_tracking(False)
        b.brightness.set_limits(0, 100, incr_value=1)
        b.brightness.set_value(50)
        b.brightness.add_callback('value-changed', self.brightness_set_cb)
        b.brightness.set_tooltip("Set brightness/bias for the viewer")

        btn = Widgets.Button('Default Contrast')
        btn.set_tooltip("Reset contrast to default")
        btn.add_callback('activated', self.restore_contrast_cb)
        b._hbox_cb.add_widget(btn, stretch=0)
        btn = Widgets.Button('Default Brightness')
        btn.set_tooltip("Reset brightness to default")
        btn.add_callback('activated', self.restore_brightness_cb)
        b._hbox_cb.add_widget(btn, stretch=0)

        fr.set_widget(w)
        top.add_widget(fr, stretch=0)

        # add colorbar
        fr = Widgets.Frame("Color Map")
        height = 50
        settings = self.rgbmap.get_settings()
        settings.set(cbar_height=height, fontsize=10)
        cbar = ColorBar.ColorBar(self.logger, rgbmap=self.rgbmap,
                                 link=True,
                                 settings=settings)
        vmax = self.rgbmap.get_hash_size() - 1
        cbar.cbar_view.cut_levels(0, vmax)
        cbar_w = cbar.get_widget()
        cbar_w.resize(-1, height)

        self.colorbar = cbar
        #cbar.add_callback('motion', self.cbar_value_cb)

        top.add_widget(cbar_w, stretch=0)

        container.set_widget(top)

    @property
    def calg_name(self):
        return self._calg_name

    @calg_name.setter
    def calg_name(self, val):
        self._calg_name = val
        if self.gui_up:
            idx = self.calg_names.index(val)
            self.w.algorithm.set_index(idx)
            self.rgbmap.set_color_algorithm(val)

    @property
    def cmap_name(self):
        return self._cmap_name

    @cmap_name.setter
    def cmap_name(self, val):
        self._cmap_name = val
        if self.gui_up:
            idx = self.cmap_names.index(val)
            self.w.colormap.set_index(idx)
            self.rgbmap.set_color_map(val)

    @property
    def imap_name(self):
        return self._imap_name

    @imap_name.setter
    def imap_name(self, val):
        self._imap_name = val
        if self.gui_up:
            idx = self.imap_names.index(val)
            self.w.intensity.set_index(idx)
            self.rgbmap.set_intensity_map(val)

    @property
    def invert_cmap(self):
        return self._invert_cmap

    @invert_cmap.setter
    def invert_cmap(self, tf):
        self._invert_cmap = tf
        if self.gui_up:
            self.w.invert_cmap.set_state(tf)
            self.rgbmap.get_settings().set(color_map_invert=tf)

    @property
    def rotate_cmap(self):
        return self._rotate_cmap_pct

    @rotate_cmap.setter
    def rotate_cmap(self, pct):
        self._rotate_cmap_pct = pct
        if self.gui_up:
            self.w.rotate_cmap.set_value(int(pct * 100.0))
            self.rgbmap.get_settings().set(color_map_rot_pct=pct)

    @property
    def contrast(self):
        return self._contrast

    @contrast.setter
    def contrast(self, pct):
        self._contrast = pct
        if self.gui_up:
            self.w.contrast.set_value(int(pct * 100))
            self.rgbmap.get_settings().set(contrast=pct)

    @property
    def brightness(self):
        return self._brightness

    @brightness.setter
    def brightness(self, pct):
        self._brightness = pct
        if self.gui_up:
            self.w.brightness.set_value(int(pct * 100))
            self.rgbmap.get_settings().set(brightness=pct)

    def set_cmap_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        map from the UI."""
        old_cmap_name = self._cmap_name
        name = mod_cmap.get_names()[index]
        self.cmap_name = name
        self.pipeline.push(StageAction(self,
                                       dict(cmap_name=old_cmap_name),
                                       dict(cmap_name=self._cmap_name),
                                       descr="rgbmap / change cmap"))

        self.pipeline.run_from(self)

    def set_imap_cb(self, w, index):
        """This callback is invoked when the user selects a new intensity
        map from the preferences pane."""
        old_imap_name = self._imap_name
        name = mod_imap.get_names()[index]
        self.imap_name = name
        self.pipeline.push(StageAction(self,
                                       dict(imap_name=old_imap_name),
                                       dict(imap_name=self._imap_name),
                                       descr="rgbmap / change imap"))

        self.pipeline.run_from(self)

    def set_calg_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the UI."""
        old_calg_name = self._calg_name
        name = self.calg_names[index]
        self.calg_name = name
        self.pipeline.push(StageAction(self,
                                       dict(calg_name=old_calg_name),
                                       dict(calg_name=self._calg_name),
                                       descr="rgbmap / change calg"))

        self.pipeline.run_from(self)

    def rotate_cmap_cb(self, w, val):
        old_val = self._rotate_cmap_pct
        pct = val / 100.0
        self.rotate_cmap = pct
        self.pipeline.push(StageAction(self,
                                       dict(rotate_cmap=old_val),
                                       dict(rotate_cmap=self._rotate_cmap_pct),
                                       descr=f"rgbmap / rotate cmap: {pct}"))

        self.pipeline.run_from(self)

    def invert_cmap_cb(self, w, tf):
        old_val = self._invert_cmap
        self.invert_cmap = tf
        self.pipeline.push(StageAction(self,
                                       dict(invert_cmap=old_val),
                                       dict(invert_cmap=self._invert_cmap),
                                       descr=f"rgbmap / invert cmap {tf}"))

        self.pipeline.run_from(self)

    def unrotate_cmap_cb(self, w):
        self.rotate_cmap_cb(w, 0)

    def set_default_cmaps(self):
        old = dict(cmap_name=self._cmap_name, imap_name=self._imap_name)
        cmap_name = "gray"
        imap_name = "ramp"
        new = dict(cmap_name=cmap_name, imap_name=imap_name)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="rgbmap / change cmap,imap"))
        self.cmap_name = cmap_name
        self.imap_name = imap_name

        self.pipeline.run_from(self)

    def contrast_set_cb(self, w, val):
        old_val = self._contrast
        pct = val / 100.0
        self.contrast = pct
        self.pipeline.push(StageAction(self,
                                       dict(contrast=old_val),
                                       dict(contrast=self._contrast),
                                       descr=f"rgbmap / contrast: {pct}"))

        self.pipeline.run_from(self)

    def brightness_set_cb(self, w, val):
        old_val = self._brightness
        pct = val / 100.0
        self.brightness = pct
        self.pipeline.push(StageAction(self,
                                       dict(brightness=old_val),
                                       dict(brightness=self._brightness),
                                       descr=f"rgbmap / brightness: {pct}"))

        self.pipeline.run_from(self)

    def restore_contrast_cb(self, w):
        self.contrast_set_cb(w, 50)

    def restore_brightness_cb(self, w):
        self.brightness_set_cb(w, 50)

    def set_default_distmaps(self):
        old = dict(calg_name=self._calg_name)
        name = 'linear'
        new = dict(calg_name=name)
        self.pipeline.push(StageAction(self, old, new,
                                       descr="rgbmap / change calg"))
        self.calg_name = name

        self.pipeline.run_from(self)

    def copy_from_viewer_cb(self, w):
        rgbmap = self.viewer.get_rgbmap()
        rgbmap.copy_attributes(self.rgbmap, keylist=self.settings_keys)

        self.pipeline.run_from(self)

    def rgbmap_changed_cb(self, rgbmap):
        self.fv.gui_do_oneshot('pl-rgbmap', self.pipeline.run_from, self)

    def run(self, prev_stage):
        data = self.pipeline.get_data(prev_stage)
        self.verify_2d(data)

        if self._bypass or data is None:
            self.pipeline.send(res_np=data)
            return

        if not np.issubdtype(data.dtype, np.uint):
            data = data.astype(np.uint)

        # get RGB mapped array
        res_np = self.rgbmap.get_rgb_array(data, order=self.order)

        self.pipeline.send(res_np=res_np)

    def __str__(self):
        return self._stagename

    def _get_state(self):
        return dict(calg_name=self._calg_name, cmap_name=self._cmap_name,
                    imap_name=self._imap_name)

    def export_as_dict(self):
        d = super().export_as_dict()
        d.update(self._get_state())
        return d

    def import_from_dict(self, d):
        super().import_from_dict(d)
        self.calg_name = d['calg_name']
        self.cmap_name = d['cmap_name']
        self.imap_name = d['imap_name']


class RGBMapStage(Stage):
    """A class that all stages participating in color mapping subclass.

    Establishes the bit depth of the RGB mapping.
    """
    def __init__(self, bpp=8):
        super().__init__()

        self.trace = False
        self.set_bpp(bpp)

    def _set_dtype(self):
        if self.bpp <= 8:
            self.dtype = np.dtype(np.uint8)
        elif self.bpp <= 16:
            self.dtype = np.dtype(np.uint16)
        else:
            self.dtype = np.dtype(np.uint32)

    def set_bpp(self, bpp):
        """
        Set the bit depth (per band) for the output.
        A typical "32-bit RGBA" image would be 8; a 48-bit image would
        be 16, etc.
        """
        self.bpp = bpp
        self.maxc = int(2 ** self.bpp - 1)
        self._set_dtype()


class RGBInput(RGBMapStage):
    """First stage of a sub-pipeline that accepts the input to be colored
    this should usually be the output of the "Cuts" stage of rendering.
    """
    _stagename = 'rgbmap-input'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.in_arr = None

    def set_input(self, in_arr):
        if not np.issubdtype(in_arr.dtype, np.uint):
            in_arr = in_arr.astype(np.uint)

        #self.verify_2d(in_arr)

        self.in_arr = in_arr

    def run(self, prev_stage):
        if prev_stage is not None:
            raise StageError("'{}' in wrong location".format(self._stagename))

        if self._bypass:
            self.pipeline.send(res_np=None)
            return

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             self.in_arr))
        self.pipeline.send(res_np=self.in_arr)


class Distribute(RGBMapStage):
    """Distribute data according to a curve.

    This stage handles the distribution of input values according to a
    predefined mapping such as linear, log, power, sqrt, asinh, etc.
    """
    _stagename = 'rgbmap-distribute'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.dist = None
        self._hashsize = self.maxc + 1
        self.set_color_algorithm('linear')

    def set_dist(self, dist):
        self.dist = dist

    def get_dist(self):
        return self.dist

    def get_hash_size(self):
        return self._hashsize

    def set_hash_size(self, size):
        self._hashsize = size
        self.dist.set_hash_size(size)

    def set_color_algorithm(self, name):
        color_dist_class = ColorDist.get_dist(name)
        self.dist = color_dist_class(self._hashsize)

    def get_hasharray(self, arr_in):
        if self._bypass or arr_in is None:
            return arr_in

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        return self.dist.hash_array(arr_in)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        arr_out = self.get_hasharray(arr_in)

        if self.trace:
            self.logger.debug("{}: sending result ({})".format(self._stagename,
                                                               arr_out))
        self.pipeline.send(res_np=arr_out)


class ShiftMap(RGBMapStage):
    """Redistribute data according to a shift array.

    This stage handles colormap shifts and stretches, which are used to
    set brightness and contrast in the image.
    """
    _stagename = 'rgbmap-shift-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self._contrast = 0.5
        self._brightness = 0.5
        self._sarr = None

        self._reset_sarr()

    @property
    def contrast(self):
        return self._contrast

    def set_contrast(self, pct):
        self._contrast = pct
        scale_factor = self._contrast_to_scale(pct)
        self._stretch(scale_factor)

    @property
    def brightness(self):
        return self._brightness

    def set_brightness(self, pct):
        self._brightness = pct
        shift_pct = self._brightness_to_shift(pct)
        self._shift(shift_pct)

    def _scale_to_contrast(self, scale_factor, reset=False):
        if not reset:
            # if not reset, multipy by the current scale factor
            scale_factor *= self._scale_factor
        pct = np.clip((np.clip(scale_factor, 0.01, 20.0) * 1000) / 2000,
                      0.0, 1.0)
        pct = 1.0 - pct
        return pct

    def _contrast_to_scale(self, contrast_pct):
        # I tried to mimic ds9's exponential scale feel along the Y-axis
        i = np.clip(contrast_pct, 0.0001, 1.0)
        scale_factor = (1.0 / (i**3)) * 0.0001 + (1.0 / i) - 1.0
        scale_factor = np.clip(scale_factor, 0.0, self.maxc)
        return scale_factor

    def _brightness_to_shift(self, brightness_pct):
        pct = 1.0 - brightness_pct
        # convert to (-1.0, 1.0) for shift pct
        shift_pct = (pct - 0.5) * 2.0
        return shift_pct

    def _shift_to_brightness(self, shift_pct, reset=False):
        if not reset:
            # if not reset, add the current shift pct
            shift_pct += self._shift_pct
        pct = (np.clip(shift_pct, -1.0, 1.0) + 1) * 0.5
        return 1.0 - pct

    def _reset_sarr(self):
        maxlen = self.maxc + 1
        self._contrast = 0.5
        self._brightness = 0.5
        self._sarr = np.arange(maxlen)

    def _get_sarr(self):
        return self._sarr

    def _set_sarr(self, sarr):
        if sarr is not None:
            sarr = np.asarray(sarr).clip(0, self.maxc).astype(np.uint)
            maxlen = self.maxc + 1
            _len = len(sarr)
            if _len != maxlen:
                raise RGBMapError("shift map length %d != %d" % (_len, maxlen))
            self._sarr = sarr
        else:
            self._reset_sarr()

    def _shift_arr(self, sarr, pct, rotate=False):
        n = len(sarr)
        num = int(n * pct)
        arr = np.roll(sarr, num)
        if not rotate:
            if num > 0:
                arr[0:num] = sarr[0]
            elif num < 0:
                arr[n + num:n] = sarr[-1]
        return arr

    def _stretch_arr(self, sarr, scale):
        old_wd = len(sarr)
        new_wd = int(round(scale * old_wd))

        # Is there a more efficient way to do this?
        xi = np.mgrid[0:new_wd]
        iscale_x = float(old_wd) / float(new_wd)

        xi = (xi * iscale_x).astype(np.uint, copy=False)
        xi = xi.clip(0, old_wd - 1).astype(np.uint, copy=False)
        newdata = sarr[xi]
        return newdata

    def _scale_and_shift(self, scale_factor, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        # reset the shift array to normal
        maxlen = self.maxc + 1
        self._sarr = np.arange(maxlen)

        # limit shrinkage to 1% of original size
        scale = max(scale_factor, 0.01)

        work = self._stretch_arr(self._sarr, scale)
        n = len(work)
        if n < maxlen:
            # pad on the lowest and highest values of the shift map
            m = (maxlen - n) // 2 + 1
            barr = np.array([0] * m)
            tarr = np.array([self.maxc] * m)
            work = np.concatenate([barr, work, tarr])
            work = work[:maxlen]

        # we are mimicing ds9's stretch and shift algorithm here.
        # ds9 seems to cut the center out of the stretched array
        # BEFORE shifting
        n = len(work) // 2
        halflen = maxlen // 2
        work = work[n - halflen:n + halflen].astype(np.uint, copy=False)
        assert len(work) == maxlen, \
            RGBMapError("scaled shift map is != %d" % maxlen)

        # shift map according to the shift_pct
        work = self._shift_arr(work, shift_pct)
        assert len(work) == maxlen, \
            RGBMapError("shifted shift map is != %d" % maxlen)

        self._sarr = work

    def _stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        shift_pct = self._brightness_to_shift(self._brightness)
        self._scale_and_shift(scale_factor, shift_pct, callback=callback)

    def _shift(self, shift_pct, rotate=False, callback=True):
        scale_factor = self._contrast_to_scale(self._contrast)
        self._scale_and_shift(scale_factor, shift_pct, callback=callback)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        # run it through the shift array and clip the result
        # See NOTE [A]
        # arr_out = self._sarr[arr_in].clip(0, self.maxc).astype(np.uint, copy=False)
        arr_out = self._sarr[arr_in]
        # TODO: I think we can avoid this operation, if shift array contents
        # can be limited to 0..maxc
        #arr_out.clip(0, self.maxc, out=arr_out)

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             arr_out))
        self.pipeline.send(res_np=arr_out)


class IntensityMap(RGBMapStage):
    """Map indexes through a curve.

    """
    _stagename = 'rgbmap-intensity-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.imap = None
        self._iarr = None
        self.set_intensity_map('ramp')

    def set_intensity_map(self, imap_name):
        im = mod_imap.get_imap(imap_name)
        self.set_imap(im)

    def set_imap(self, imap):
        self.imap = imap
        self.calc_imap()

    def calc_imap(self):
        arr = np.array(self.imap.ilst) * float(self.maxc)
        self._iarr = np.round(arr).astype(np.uint, copy=False)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        arr_out = self._iarr[arr_in]

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             arr_out))
        self.pipeline.send(res_np=arr_out)


class ColorMap(RGBMapStage):
    """Map indexes through a three-color lookup table.

    """
    _stagename = 'rgbmap-color-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.cmap = None
        self._carr = None
        self._inverted = False
        self._rot_pct = 0.0

        self.set_color_map('gray')

    @property
    def inverted(self):
        return self._inverted

    @property
    def rot_pct(self):
        return self._rot_pct

    def set_color_map(self, cmap_name):
        cm = mod_cmap.get_cmap(cmap_name)
        self.set_cmap(cm)

    def set_cmap(self, cmap):
        self.cmap = cmap
        self.calc_cmap()

    def invert_cmap(self, tf):
        self._inverted = tf
        self.calc_cmap()

    def rotate_color_map(self, pct):
        self._rot_pct = np.clip(pct, -1.0, 1.0)
        self.calc_cmap()

    def _gen_cmap(self):
        clst = self.cmap.clst
        self.maxc = len(clst) - 1
        arr = np.array(clst).transpose() * float(self.maxc)
        # does this really need to be the same type as rgbmap output type?
        carr = np.round(arr).astype(self.dtype, copy=False)
        return carr

    def reset_cmap(self):
        self._inverted = False
        self._rot_pct = 0.0
        self.calc_cmap()

    def calc_cmap(self):
        self._carr = self._gen_cmap()
        if self._inverted:
            self._carr = np.fliplr(self._carr)
        num = int((self.maxc + 1) * self._rot_pct)
        if num != 0:
            self._carr = np.roll(self._carr, num, axis=1)

    def get_order_indexes(self, order, cs):
        order = order.upper()
        if order == '':
            # assume standard RGB order if we don't find an order
            # explicitly set
            return [0, 1, 2]
        cs = cs.upper()
        return [order.index(c) for c in cs]

    def do_map_index(self, arr_in, map_arr):
        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        # prepare output array
        shape = arr_in.shape
        # get RGB order requested for output
        state = self.pipeline.get('state')
        order = state.order
        depth = len(order)
        image_order = trcalc.guess_order(shape)

        if (image_order is not None) and (len(image_order) > 1):
            # indexes contain RGB axis, so omit this
            res_shape = shape[:-1] + (depth, )
        else:
            res_shape = shape + (depth, )

        out = np.empty(res_shape, dtype=self.dtype, order='C')

        from ginga.RGBMap import RGBPlanes
        rgbobj = RGBPlanes(out, order)

        # set alpha channel
        if rgbobj.hasAlpha:
            aa = rgbobj.get_slice('A')
            aa.fill(self.maxc)

        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        arr_out = rgbobj.rgbarr

        # See NOTE [A]
        if (image_order is None) or (len(image_order) == 1):
            arr_out[..., [ri, gi, bi]] = map_arr[arr_in]

        elif len(image_order) == 2:
            mj, aj = self.get_order_indexes(image_order, 'MA')
            arr_out[..., [ri, gi, bi]] = map_arr[arr_in[..., mj]]

        else:
            # <== indexes already contain RGB info.
            rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
            arr_out[..., ri] = map_arr[:, 0][arr_in[..., rj]]
            arr_out[..., gi] = map_arr[:, 1][arr_in[..., gj]]
            arr_out[..., bi] = map_arr[:, 2][arr_in[..., bj]]

        # alpha = self.pipeline.get('alpha')
        # if alpha is not None:
        #     arr_out[..., -1] = alpha

        return arr_out

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        arr_out = self.do_map_index(arr_in, self._carr.T)

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             arr_out))
        self.pipeline.send(res_np=arr_out)
