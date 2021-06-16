# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc, cmap, imap, ColorDist
from ginga.RGBMap import RGBMapper
from ginga.gw import Widgets, ColorBar

from .base import Stage, StageAction


class RGBMap(Stage):

    _stagename = 'rgb-mapper'

    def __init__(self):
        super().__init__()

        self.rgbmap = None
        self.calg_names = ColorDist.get_dist_names()
        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        self.order = 'RGB'

        self._calg_name = 'linear'
        self._cmap_name = 'gray'
        self._imap_name = 'ramp'
        self._hash_size = 256
        # TODO: currently hash size cannot be changed
        self.viewer = None
        self.fv = None

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')
        self.fv = self.pipeline.get("fv")
        top = Widgets.VBox()

        # create and initialize RGB mapper
        self.rgbmap = RGBMapper(self.logger)
        self.rgbmap.set_hash_size(self._hash_size)
        self.rgbmap.set_color_algorithm(self._calg_name)
        self.rgbmap.set_color_map(self._cmap_name)
        self.rgbmap.set_intensity_map(self._imap_name)
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

        ## entry = b.table_size
        ## entry.set_text(str(self.t_.get('color_hashsize', 65535)))
        ## entry.add_callback('activated', self.set_tablesize_cb)

        fr.set_widget(w)
        top.add_widget(fr, stretch=0)

        # COLOR MAPPING OPTIONS
        fr = Widgets.Frame("Color Mapping")

        captions = (('Colormap:', 'label', 'Colormap', 'combobox'),
                    ('Intensity:', 'label', 'Intensity', 'combobox'),
                    ('Color Defaults', 'button', 'Copy from viewer', 'button'))
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)
        self.w.cmap_choice = b.colormap
        self.w.imap_choice = b.intensity
        b.color_defaults.add_callback('activated',
                                      lambda w: self.set_default_cmaps())
        b.colormap.set_tooltip("Choose a color map for this image")
        b.intensity.set_tooltip("Choose an intensity map for this image")
        b.color_defaults.set_tooltip("Restore default color and intensity maps")
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

        # COLOR MAP MANIPULATIONS
        fr = Widgets.Frame("Color Map Manipulations")

        captions = (('Contrast:', 'label', 'stretch', 'hscale'),
                    ('Brightness:', 'label', 'shift', 'hscale'),
                    ('Rotate:', 'label', 'rotate', 'hscale'),
                    ('Invert', 'button', 'Restore', 'button'))
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.stretch.set_tracking(True)
        b.stretch.set_limits(0, 100, incr_value=1)
        b.stretch.set_value(100)
        b.stretch.add_callback('value-changed', self.stretch_cmap_cb)
        b.stretch.set_tooltip("Stretch color map")

        b.shift.set_tracking(True)
        b.shift.set_limits(-100, 100, incr_value=1)
        b.shift.set_value(0)
        b.shift.add_callback('value-changed', self.shift_cmap_cb)
        b.shift.set_tooltip("Shift color map")

        b.rotate.set_tracking(True)
        b.rotate.set_limits(-100, 100, incr_value=1)
        b.rotate.set_value(0)
        b.rotate.add_callback('value-changed', self.rotate_cmap_cb)
        b.rotate.set_tooltip("Rotate when shifting")

        b.invert.set_tooltip("Invert color map")
        b.invert.add_callback('activated', self.invert_cmap_cb)
        b.restore.set_tooltip("Restore color map")
        b.restore.add_callback('activated', self.restore_cmap_cb)

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
        cbar.cbar_view.cut_levels(0, self._hash_size - 1)
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

    def set_cmap_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        map from the preferences pane."""
        old_cmap_name = self._cmap_name
        name = cmap.get_names()[index]
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
        name = imap.get_names()[index]
        self.imap_name = name
        self.pipeline.push(StageAction(self,
                                       dict(imap_name=old_imap_name),
                                       dict(imap_name=self._imap_name),
                                       descr="rgbmap / change imap"))

        self.pipeline.run_from(self)

    def set_calg_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the preferences pane."""
        old_calg_name = self._calg_name
        name = self.calg_names[index]
        self.calg_name = name
        self.pipeline.push(StageAction(self,
                                       dict(calg_name=old_calg_name),
                                       dict(calg_name=self._calg_name),
                                       descr="rgbmap / change calg"))

        self.pipeline.run_from(self)

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

    def stretch_cmap_cb(self, w, val):
        self.rgbmap.reset_sarr(callback=False)
        stretch_val = 100.0 - val
        scale_pct = stretch_val / 100.0
        shift_val = self.w.shift.get_value()
        shift_pct = - shift_val / 100.0

        self.rgbmap.scale_and_shift(scale_pct, shift_pct)

        #self.fv.gui_do(self.pipeline.run_from, self)

    def shift_cmap_cb(self, w, val):
        self.rgbmap.reset_sarr(callback=False)
        shift_pct = - val / 100.0
        stretch_val = 100.0 - self.w.stretch.get_value()
        scale_pct = stretch_val / 100.0

        self.rgbmap.scale_and_shift(scale_pct, shift_pct)

        #self.fv.gui_do(self.pipeline.run_from, self)

    def rotate_cmap_cb(self, w, val):
        self.rgbmap.calc_cmap()
        pct = val / 100.0
        num = int(255 * pct)
        self.rgbmap.rotate_cmap(num)
        #self.rgbmap.shift(shift_pct, rotate=rotate)

        #self.pipeline.run_from(self)

    def invert_cmap_cb(self, w):
        self.rgbmap.invert_cmap()

        self.pipeline.run_from(self)

    def restore_cmap_cb(self, w):
        self.rgbmap.restore_cmap()

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
        image_order = trcalc.guess_order(data.shape)
        rgbobj = self.rgbmap.get_rgbarray(data, order=self.order,
                                          image_order=image_order)
        res_np = rgbobj.get_array(self.order)

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
