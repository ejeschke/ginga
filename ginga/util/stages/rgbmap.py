# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga import trcalc, cmap, imap, ColorDist
from ginga.RGBMap import RGBMapper
from ginga.gw import Widgets

from .base import Stage


class RGBMap(Stage):

    _stagename = 'rgb-mapper'

    def __init__(self):
        super(RGBMap, self).__init__()

        self.rgbmap = None
        self.calg_names = ColorDist.get_dist_names()
        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        self.order = 'RGB'

        self.calg_name = 'linear'
        self.cmap_name = 'gray'
        self.imap_name = 'ramp'
        self.hash_size = 256
        # TODO: currently hash size cannot be changed
        self.viewer = None

    def build_gui(self, container):
        self.viewer = self.pipeline.get('viewer')
        top = Widgets.VBox()

        # create and initialize RGB mapper
        self.rgbmap = RGBMapper(self.logger)
        self.rgbmap.set_hash_size(self.hash_size)
        self.rgbmap.set_color_algorithm(self.calg_name)
        self.rgbmap.set_color_map(self.cmap_name)
        self.rgbmap.set_intensity_map(self.imap_name)
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
        index = 0
        for name in self.calg_names:
            options.append(name)
            combobox.append_text(name)
            index += 1
        try:
            index = self.calg_names.index(self.calg_name)
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
        index = 0
        for name in self.cmap_names:
            options.append(name)
            combobox.append_text(name)
            index += 1
        try:
            index = self.cmap_names.index(self.cmap_name)
        except Exception:
            index = self.cmap_names.index('gray')
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_cmap_cb)

        combobox = b.intensity
        options = []
        index = 0
        for name in self.imap_names:
            options.append(name)
            combobox.append_text(name)
            index += 1
        try:
            index = self.imap_names.index(self.imap_name)
        except Exception:
            index = self.imap_names.index('ramp')
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_imap_cb)

        b.copy_from_viewer.set_tooltip("Copy settings from viewer")
        b.copy_from_viewer.add_callback('activated', self.copy_from_viewer_cb)

        top.add_widget(fr, stretch=0)

        container.set_widget(top)

    def set_cmap_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        map from the preferences pane."""
        name = cmap.get_names()[index]
        self.rgbmap.set_color_map(name)

        self.pipeline.run_from(self)

    def set_imap_cb(self, w, index):
        """This callback is invoked when the user selects a new intensity
        map from the preferences pane."""
        name = imap.get_names()[index]
        self.rgbmap.set_intensity_map(name)

        self.pipeline.run_from(self)

    def set_calg_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the preferences pane."""
        name = self.calg_names[index]
        self.rgbmap.set_color_algorithm(name)

        self.pipeline.run_from(self)

    def set_default_cmaps(self):
        cmap_name = "gray"
        imap_name = "ramp"
        index = self.cmap_names.index(cmap_name)
        self.w.cmap_choice.set_index(index)
        self.rgbmap.set_color_map(cmap_name)
        index = self.imap_names.index(imap_name)
        self.w.imap_choice.set_index(index)
        self.rgbmap.set_intensity_map(imap_name)

        self.pipeline.run_from(self)

    def set_default_distmaps(self):
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.set_index(index)
        self.rgbmap.set_color_algorithm(name)

        self.pipeline.run_from(self)

    def copy_from_viewer_cb(self, w):
        rgbmap = self.viewer.get_rgbmap()
        rgbmap.copy_attributes(self.rgbmap, keylist=self.settings_keys)

        self.pipeline.run_from(self)

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
