#
# Preferences.py -- Preferences plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

from ginga import cmap, imap
from ginga import GingaPlugin
from ginga import AutoCuts, wcs

from ginga.misc import Bunch

class Preferences(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Preferences, self).__init__(fv, fitsimage)

        self.chname = self.fv.get_channelName(self.fitsimage)

        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        self.zoomalg_names = ('step', 'rate')
        
        self.autocuts_cache = {}
        self.gui_up = False

        rgbmap = fitsimage.get_rgbmap()
        self.calg_names = rgbmap.get_hash_algorithms()
        self.calg_names.sort()
        self.autozoom_options = self.fitsimage.get_autozoom_options()
        self.autocut_options = self.fitsimage.get_autocuts_options()
        self.autocut_methods = self.fitsimage.get_autocut_methods()

        self.t_ = self.fitsimage.get_settings()
        self.t_.getSetting('autocuts').add_callback('set',
                                               self.autocuts_changed_ext_cb)
        self.t_.getSetting('autozoom').add_callback('set',
                                               self.autozoom_changed_ext_cb)
        for key in ['pan']:
            self.t_.getSetting(key).add_callback('set',
                                          self.pan_changed_ext_cb)
        for key in ['scale']:
            self.t_.getSetting(key).add_callback('set',
                                          self.scale_changed_ext_cb)

        self.t_.getSetting('zoom_algorithm').add_callback('set', self.set_zoomalg_ext_cb)
        self.t_.getSetting('zoom_rate').add_callback('set', self.set_zoomrate_ext_cb)
        for key in ['scale_x_base', 'scale_y_base']:
            self.t_.getSetting(key).add_callback('set', self.scalebase_changed_ext_cb)
        self.t_.getSetting('rot_deg').add_callback('set', self.set_rotate_ext_cb)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            self.t_.getSetting(name).add_callback('set', self.set_transform_ext_cb)

        for name in ('autocut_method', 'autocut_params'):
            self.t_.getSetting(name).add_callback('set', self.set_autocuts_ext_cb)

        self.t_.setdefault('wcs_coords', 'icrs')
        self.t_.setdefault('wcs_display', 'sexagesimal')

    def build_gui(self, container):
        sw = QtGui.QScrollArea()

        twidget = QtHelp.VBox()
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                               QtGui.QSizePolicy.Fixed)
        twidget.setSizePolicy(sp)
        vbox = twidget.layout()
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(2)
        sw.setWidgetResizable(True)
        sw.setWidget(twidget)

        # COLOR MAPPING OPTIONS
        fr = QtHelp.Frame("Colors")

        captions = (('Colormap', 'combobox', 'Intensity', 'combobox'),
                    ('Algorithm', 'combobox', 'Table Size', 'entry'),
                    ('Color Defaults', 'button'))
        w, b = QtHelp.build_info(captions)
        self.w.cmap_choice = b.colormap
        self.w.imap_choice = b.intensity
        self.w.calg_choice = b.algorithm
        self.w.table_size = b.table_size
        b.color_defaults.clicked.connect(self.set_default_maps)
        b.colormap.setToolTip("Choose a color map for this image")
        b.intensity.setToolTip("Choose an intensity map for this image")
        b.algorithm.setToolTip("Choose a color mapping algorithm")
        b.table_size.setToolTip("Set size of the color mapping table")
        b.color_defaults.setToolTip("Restore default color and intensity maps")
        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        combobox = b.colormap
        options = []
        index = 0
        for name in self.cmap_names:
            options.append(name)
            combobox.addItem(name)
            index += 1
        cmap_name = self.t_.get('color_map', "ramp")
        try:
            index = self.cmap_names.index(cmap_name)
        except Exception:
            index = self.cmap_names.index('ramp')
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_cmap_cb)

        combobox = b.intensity
        options = []
        index = 0
        for name in self.imap_names:
            options.append(name)
            combobox.addItem(name)
            index += 1
        imap_name = self.t_.get('intensity_map', "ramp")
        try:
            index = self.imap_names.index(imap_name)
        except Exception:
            index = self.imap_names.index('ramp')
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_imap_cb)

        combobox = b.algorithm
        options = []
        index = 0
        for name in self.calg_names:
            options.append(name)
            combobox.addItem(name)
            index += 1
        index = self.calg_names.index(self.t_.get('color_algorithm', "linear"))
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_calg_cb)

        entry = b.table_size
        entry.setText(str(self.t_.get('color_hashsize', 65535)))
        entry.returnPressed.connect(lambda: self.set_tablesize_cb(entry))

        # ZOOM OPTIONS
        fr = QtHelp.Frame("Zoom")

        captions = (('Zoom Alg', 'combobox', 'Zoom Rate', 'spinfloat'),
                    ('Stretch XY', 'combobox', 'Stretch Factor', 'spinfloat'),
                    ('Scale X', 'entry', 'Scale Y', 'entry'),
                    ('Scale Min', 'spinfloat', 'Scale Max', 'spinfloat'),
                    ('Zoom Defaults', 'button'))
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        index = 0
        for name in self.zoomalg_names:
            b.zoom_alg.addItem(name.capitalize())
            index += 1
        zoomalg = self.t_.get('zoom_algorithm', "step")            
        index = self.zoomalg_names.index(zoomalg)
        b.zoom_alg.setCurrentIndex(index)
        b.zoom_alg.setToolTip("Choose Zoom algorithm")
        b.zoom_alg.activated.connect(self.set_zoomalg_cb)
            
        index = 0
        for name in ('X', 'Y'):
            b.stretch_xy.addItem(name)
            index += 1
        b.stretch_xy.setCurrentIndex(0)
        b.stretch_xy.setToolTip("Stretch pixels in X or Y")
        b.stretch_xy.activated.connect(lambda v: self.set_stretch_cb())
            
        b.stretch_factor.setRange(1.0, 10.0)
        b.stretch_factor.setValue(1.0)
        b.stretch_factor.setSingleStep(0.10)
        b.stretch_factor.setDecimals(8)
        b.stretch_factor.valueChanged.connect(lambda v: self.set_stretch_cb())
        b.stretch_factor.setToolTip("Length of pixel relative to 1 on other side")
        b.stretch_factor.setEnabled(zoomalg!='step')

        zoomrate = self.t_.get('zoom_rate', math.sqrt(2.0))
        b.zoom_rate.setRange(1.1, 3.0)
        b.zoom_rate.setValue(zoomrate)
        b.zoom_rate.setSingleStep(0.1)
        b.zoom_rate.setDecimals(8)
        b.zoom_rate.setEnabled(zoomalg!='step')
        b.zoom_rate.setToolTip("Step rate of increase/decrease per zoom level")
        b.zoom_rate.valueChanged.connect(self.set_zoomrate_cb)

        b.zoom_defaults.clicked.connect(self.set_zoom_defaults_cb)
        
        scale_x, scale_y = self.fitsimage.get_scale_xy()
        b.scale_x.setToolTip("Set the scale in X axis")
        b.scale_x.setText(str(scale_x))
        b.scale_x.returnPressed.connect(self.set_scale_cb)
        b.scale_y.setToolTip("Set the scale in Y axis")
        b.scale_y.setText(str(scale_y))
        b.scale_y.returnPressed.connect(self.set_scale_cb)

        scale_min, scale_max = self.t_['scale_min'], self.t_['scale_max']
        b.scale_min.setRange(0.00001, 1.0)
        b.scale_min.setValue(scale_min)
        b.scale_min.setDecimals(8)
        b.scale_min.setSingleStep(1.0)
        b.scale_min.valueChanged.connect(lambda w: self.set_scale_limit_cb())
        b.scale_min.setToolTip("Set the minimum allowed scale in any axis")

        b.scale_max.setRange(1.0, 10000.0)
        b.scale_max.setValue(scale_max)
        b.scale_max.setSingleStep(1.0)
        b.scale_max.setDecimals(8)
        b.scale_max.valueChanged.connect(lambda w: self.set_scale_limit_cb())
        b.scale_min.setToolTip("Set the maximum allowed scale in any axis")

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        # PAN OPTIONS
        fr = QtHelp.Frame("Panning")

        captions = (('Pan X', 'entry'),
                    ('Pan Y', 'entry', 'Center Image', 'button'),
                    ('Reverse Pan', 'checkbutton', 'Mark Center', 'checkbutton'))
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        pan_x, pan_y = self.fitsimage.get_pan()
        b.pan_x.setToolTip("Set the pan position in X axis")
        b.pan_x.setText(str(pan_x+0.5))
        b.pan_x.returnPressed.connect(self.set_pan_cb)
        b.pan_y.setToolTip("Set the pan position in Y axis")
        b.pan_y.setText(str(pan_y+0.5))
        b.pan_y.returnPressed.connect(self.set_pan_cb)

        b.center_image.setToolTip("Set the pan position to center of the image")
        b.center_image.clicked.connect(self.center_image_cb)
        b.reverse_pan.setToolTip("Reverse the pan direction")
        b.reverse_pan.stateChanged.connect(self.set_misc_cb)
        b.mark_center.setToolTip("Mark the center (pan locator)")
        b.mark_center.stateChanged.connect(self.set_misc_cb)

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        # TRANSFORM OPTIONS
        fr = QtHelp.Frame("Transform")

        captions = (('Flip X', 'checkbutton', 'Flip Y', 'checkbutton',
                     'Swap XY', 'checkbutton'), ('Rotate', 'spinfloat'),
                    ('Restore', 'button'),)
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        for name in ('flip_x', 'flip_y', 'swap_xy'):
            btn = b[name]
            btn.setChecked(self.t_.get(name, False))
            btn.stateChanged.connect(lambda w: self.set_transforms_cb())
        b.flip_x.setToolTip("Flip the image around the X axis")
        b.flip_y.setToolTip("Flip the image around the Y axis")
        b.swap_xy.setToolTip("Swap the X and Y axes in the image")
        b.rotate.setToolTip("Rotate the image around the pan position")
        b.restore.setToolTip("Clear any transforms and center image")
        b.restore.clicked.connect(self.restore_cb)

        b.rotate.setRange(0.00, 359.99999999)
        b.rotate.setValue(0.00)
        b.rotate.setSingleStep(10.0)
        b.rotate.setDecimals(8)
        b.rotate.valueChanged.connect(lambda w: self.rotate_cb())

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        # AUTOCUTS OPTIONS
        fr = QtHelp.Frame("Auto Cuts")

        captions = (('Auto Method', 'combobox'),
                    )
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        # Setup auto cuts method choice
        combobox = b.auto_method
        index = 0
        method = self.t_.get('autocut_method', "histogram")
        for name in self.autocut_methods:
            combobox.addItem(name)
            index += 1
        index = self.autocut_methods.index(method)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(lambda w: self.set_autocut_method_cb())
        b.auto_method.setToolTip("Choose algorithm for auto levels")

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        self.w.acvbox = QtHelp.VBox()
        fr.layout().addWidget(self.w.acvbox, stretch=1,
                              alignment=QtCore.Qt.AlignLeft)

        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        # WCS OPTIONS
        fr = QtHelp.Frame("WCS")

        captions = (('WCS Coords', 'combobox', 'WCS Display', 'combobox'),
                    )
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        b.wcs_coords.setToolTip("Set WCS coordinate system")
        b.wcs_display.setToolTip("Set WCS display format")

        # Setup WCS coords method choice
        combobox = b.wcs_coords
        index = 0
        for name in wcs.coord_types:
            combobox.addItem(name)
            index += 1
        method = self.t_.get('wcs_coords', "")
        try:
            index = wcs.coord_types.index(method)
            combobox.setCurrentIndex(index)
        except ValueError:
            pass
        combobox.activated.connect(lambda w: self.set_wcs_params_cb())

        # Setup WCS display format method choice
        combobox = b.wcs_display
        index = 0
        for name in wcs.display_types:
            combobox.addItem(name)
            index += 1
        method = self.t_.get('wcs_display', "sexagesimal")
        try:
            index = wcs.display_types.index(method)
            combobox.setCurrentIndex(index)
        except ValueError:
            pass
        combobox.activated.connect(lambda w: self.set_wcs_params_cb())

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        fr = QtHelp.Frame("New Images")

        captions = (('Cut New', 'combobox', 'Zoom New', 'combobox'),
                    ('Center New', 'checkbutton', 'Follow New', 'checkbutton'),
                    ('Raise New', 'checkbutton', 'Create thumbnail', 'checkbutton'),)
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        combobox = b.cut_new
        index = 0
        for name in self.autocut_options:
            combobox.addItem(name)
            index += 1
        option = self.t_.get('autocuts', "off")
        index = self.autocut_options.index(option)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_autocuts_cb)
        b.cut_new.setToolTip("Automatically set cut levels for new images")

        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.addItem(name)
            index += 1
        option = self.t_.get('autozoom', "off")
        index = self.autozoom_options.index(option)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_autozoom_cb)
        b.zoom_new.setToolTip("Automatically fit new images to window")

        b.center_new.setToolTip("Automatically center new images")
        b.follow_new.setToolTip("View new images as they arrive")
        b.raise_new.setToolTip("Raise and focus tab for new images")
        b.create_thumbnail.setToolTip("Create thumbnail for new images")

        self.w.center_new.setChecked(True)
        self.w.center_new.stateChanged.connect(
            lambda w: self.set_chprefs_cb())
        self.w.follow_new.setChecked(True)
        self.w.follow_new.stateChanged.connect(
            lambda w: self.set_chprefs_cb())
        self.w.raise_new.setChecked(True)
        self.w.raise_new.stateChanged.connect(
            lambda w: self.set_chprefs_cb())
        self.w.create_thumbnail.setChecked(True)
        self.w.create_thumbnail.stateChanged.connect(
            lambda w: self.set_chprefs_cb())

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)
        #layout.set_child_size(15, -1)

        btn = QtGui.QPushButton("Save Settings")
        btn.clicked.connect(self.save_preferences)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        #container.addWidget(sw, stretch=1, alignment=QtCore.Qt.AlignTop)
        container.addWidget(sw, stretch=1)
        
        self.gui_up = True
        
    def set_cmap_cb(self, index):
        """This callback is invoked when the user selects a new color
        map from the preferences pane."""
        name = cmap.get_names()[index]
        self.set_cmap_byname(name)
        self.t_.set(color_map=name)

    def set_cmap_byname(self, name, redraw=True):
        # Get colormap
        try:
            cm = cmap.get_cmap(name)
        except KeyError:
            raise ValueError("No such color map name: '%s'" % (name))

        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_cmap(cm)
        
    def set_imap_cb(self, index):
        """This callback is invoked when the user selects a new intensity
        map from the preferences pane."""
        name = imap.get_names()[index]
        self.set_imap_byname(name)
        self.t_.set(intensity_map=name)

    def set_imap_byname(self, name, redraw=True):
        # Get intensity map
        try:
            im = imap.get_imap(name)
        except KeyError:
            raise ValueError("No such intensity map name: '%s'" % (name))

        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_imap(im)

    def set_calg_cb(self, index):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the preferences pane."""
        #index = w.currentIndex()
        name = self.calg_names[index]
        self.set_calg_byname(name)

    def set_tablesize_cb(self, w):
        value = int(w.text())
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(value)
        self.t_.set(color_hashsize=value)

    def set_calg_byname(self, name, redraw=True):
        # Get color mapping algorithm
        rgbmap = self.fitsimage.get_rgbmap()
        try:
            rgbmap.set_hash_algorithm(name)
        except KeyError:
            raise ValueError("No such color algorithm name: '%s'" % (name))

        # Doesn't this force a redraw?  Following redraw should be unecessary.
        self.t_.set(color_algorithm=name)
        if redraw:
            self.fitsimage.redraw(whence=2)

    def set_default_maps(self):
        cmap_name = "ramp"
        imap_name = "ramp"
        index = self.cmap_names.index(cmap_name)
        self.w.cmap_choice.setCurrentIndex(index)
        index = self.imap_names.index(imap_name)
        self.w.imap_choice.setCurrentIndex(index)
        self.set_cmap_byname(cmap_name)
        self.t_.set(color_map=cmap_name)
        self.set_imap_byname(imap_name)
        self.t_.set(intensity_map=imap_name)
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.setCurrentIndex(index)
        self.set_calg_byname(name)
        self.t_.set(color_algorithm=name)
        hashsize = 65535
        self.t_.set(color_hashsize=hashsize)
        self.w.table_size.setText(str(hashsize))
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(hashsize)
        
    def set_zoomrate_cb(self):
        rate = self.w.zoom_rate.value()
        self.t_.set(zoom_rate=rate)
        
    def set_zoomrate_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        self.w.zoom_rate.setValue(value)
        
    def set_zoomalg_cb(self, idx):
        self.t_.set(zoom_algorithm=self.zoomalg_names[idx])
        
    def set_zoomalg_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        if value == 'step':
            self.w.zoom_alg.setCurrentIndex(0)
            self.w.zoom_rate.setEnabled(False)
            self.w.stretch_factor.setEnabled(False)
        else:
            self.w.zoom_alg.setCurrentIndex(1)
            self.w.zoom_rate.setEnabled(True)
            self.w.stretch_factor.setEnabled(True)

    def scalebase_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        scale_x_base, scale_y_base = self.fitsimage.get_scale_base_xy()

        ratio = float(scale_x_base) / float(scale_y_base)
        if ratio < 1.0:
            # Y is stretched
            idx = 1
            ratio = 1.0 / ratio
        elif ratio > 1.0:
            # X is stretched
            idx = 0
        else:
            idx = self.w.stretch_xy.currentIndex()

        # Update stretch controls to reflect actual scale
        self.w.stretch_xy.setCurrentIndex(idx)
        self.w.stretch_factor.setValue(ratio)
        
    def set_zoom_defaults_cb(self):
        rate = math.sqrt(2.0)
        self.w.stretch_factor.setValue(1.0)
        self.t_.set(zoom_algorithm='step', zoom_rate=rate,
                    scale_x_base=1.0, scale_y_base=1.0)
        
    def set_stretch_cb(self):
        axis = self.w.stretch_xy.currentIndex()
        value = self.w.stretch_factor.value()
        if axis == 0:
            self.t_.set(scale_x_base=value, scale_y_base=1.0)
        else:
            self.t_.set(scale_x_base=1.0, scale_y_base=value)
        
    def pan_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        pan_x, pan_y = value
        fits_x, fits_y = pan_x + 0.5, pan_y + 0.5
        self.w.pan_x.setText(str(fits_x))
        self.w.pan_y.setText(str(fits_y))

    def set_scale_cb(self):
        scale_x = float(self.w.scale_x.text())
        scale_y = float(self.w.scale_y.text())
        self.fitsimage.scale_to(scale_x, scale_y)

    def scale_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        scale_x, scale_y = value
        self.w.scale_x.setText(str(scale_x))
        self.w.scale_y.setText(str(scale_y))

    def set_scale_limit_cb(self):
        scale_min = float(self.w.scale_min.value())
        scale_max = float(self.w.scale_max.value())
        self.t_.set(scale_min=scale_min, scale_max=scale_max)

    def set_autozoom_cb(self, idx):
        option = self.autozoom_options[idx]
        self.fitsimage.enable_autozoom(option)
        self.t_.set(autozoom=option)

    def autozoom_changed_ext_cb(self, setting, option):
        if not self.gui_up:
            return
        index = self.autozoom_options.index(option)
        self.w.zoom_new.setCurrentIndex(index)

    def config_autocut_params(self, method, pct):
        index = self.autocut_methods.index(method)
        self.w.auto_method.setCurrentIndex(index)
        self.w.hist_pct.setValue(pct)
        if method != 'histogram':
            self.w.hist_pct.setEnabled(False)
        else:
            self.w.hist_pct.setEnabled(True)
        
    def set_autocuts_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        method = self.t_['autocut_method']
        pct = self.t_['autocut_hist_pct']
        self.config_autocut_params(method, pct)

    def config_autocut_params(self, method):
        index = self.autocut_methods.index(method)
        self.w.auto_method.setCurrentIndex(index)
        
        # remove old params
        layout = self.w.acvbox.layout()
        for child in QtHelp.children(layout):
            QtHelp.removeWidget(layout, child)

        # Create new autocuts object of the right kind
        ac = AutoCuts.get_autocuts(method)(self.logger)

        # Build up a set of control widgets for the autocuts
        # algorithm tweakable parameters
        paramlst = ac.get_params_metadata()

        params = self.autocuts_cache.setdefault(method, {})
        self.ac_params = QtHelp.ParamSet(self.logger, params)

        w = self.ac_params.build_params(paramlst)
        self.ac_params.add_callback('changed', self.autocut_params_changed_cb)

        self.w.acvbox.layout().addWidget(w, stretch=1)

    def set_autocuts_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        if setting.name == 'autocut_method':
            self.config_autocut_params(value)
        elif setting.name == 'autocut_params':
            params = dict(value)
            self.ac_params.params.update(params)
            self.ac_params.sync_params()

    def set_autocut_method_cb(self):
        idx = self.w.auto_method.currentIndex()
        method = self.autocut_methods[idx]

        self.config_autocut_params(method)

        params = self.ac_params.get_params()
        params = list(params.items())
        self.t_.set(autocut_method=method, autocut_params=params)

    def autocut_params_changed_cb(self, paramObj, params):
        params = list(params.items())
        self.t_.set(autocut_params=params)
        
    def set_autocuts_cb(self, index):
        option = self.autocut_options[index]
        self.fitsimage.enable_autocuts(option)
        self.t_.set(autocuts=option)

    def autocuts_changed_ext_cb(self, setting, option):
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        if self.gui_up:
            self.w.cut_new.setCurrentIndex(index)

    def set_transforms_cb(self):
        flip_x = (self.w.flip_x.checkState() != 0)
        flip_y = (self.w.flip_y.checkState() != 0)
        swap_xy = (self.w.swap_xy.checkState() != 0)
        self.t_.set(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)
        return True

    def set_transform_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        flip_x, flip_y, swap_xy = \
                self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy']
        self.w.flip_x.setChecked(flip_x)
        self.w.flip_y.setChecked(flip_y)
        self.w.swap_xy.setChecked(swap_xy)
        
    def rotate_cb(self):
        deg = self.w.rotate.value()
        self.t_.set(rot_deg=deg)
        return True

    def set_rotate_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        self.w.rotate.setValue(value)
        return True

    def center_image_cb(self):
        self.fitsimage.center_image()
        return True

    def set_pan_cb(self):
        pan_x = float(self.w.pan_x.text()) - 0.5
        pan_y = float(self.w.pan_y.text()) - 0.5
        self.fitsimage.set_pan(pan_x, pan_y)
        return True

    def restore_cb(self):
        self.t_.set(flip_x=False, flip_y=False, swap_xy=False,
                    rot_deg=0.0)
        self.fitsimage.center_image()
        return True

    def set_misc_cb(self):
        revpan = (self.w.reverse_pan.checkState() != 0)
        self.t_.set(reverse_pan=revpan)
        self.fitsimage.set_pan_reverse(revpan)

        markc = (self.w.mark_center.checkState() != 0)
        self.t_.set(show_pan_position=markc)
        self.fitsimage.show_pan_mark(markc)
        return True

    def set_chprefs_cb(self):
        autocenter = (self.w.center_new.checkState() != 0)
        switchnew = (self.w.follow_new.checkState() != 0)
        raisenew = (self.w.raise_new.checkState() != 0)
        genthumb = (self.w.create_thumbnail.checkState() != 0)
        self.t_.set(switchnew=switchnew, raisenew=raisenew,
                    autocenter=autocenter, genthumb=genthumb)

    def set_wcs_params_cb(self):
        idx = self.w.wcs_coords.currentIndex()
        try:
            ctype = wcs.coord_types[idx]
        except IndexError:
            ctype = 'icrs'
        idx = self.w.wcs_display.currentIndex()
        dtype = wcs.display_types[idx]
        self.t_.set(wcs_coords=ctype, wcs_display=dtype)

    def preferences_to_controls(self):
        prefs = self.t_

        # color map
        rgbmap = self.fitsimage.get_rgbmap()
        cm = rgbmap.get_cmap()
        try:
            index = self.cmap_names.index(cm.name)
        except ValueError:
            # may be a custom color map installed
            index = 0
        self.w.cmap_choice.setCurrentIndex(index)

        calg = rgbmap.get_hash_algorithm()
        index = self.calg_names.index(calg)
        self.w.calg_choice.setCurrentIndex(index)

        size = rgbmap.get_hash_size()
        self.w.table_size.setText(str(size))

        im = rgbmap.get_imap()
        try:
            index = self.imap_names.index(im.name)
        except ValueError:
            # may be a custom intensity map installed
            index = 0
        self.w.imap_choice.setCurrentIndex(index)

        # TODO: this is a HACK to get around Qt's callbacks
        # on setting widget values--need a way to disable callbacks
        # for direct setting
        auto_zoom = prefs.get('autozoom', 'off')

        # zoom settings
        zoomalg = prefs.get('zoom_algorithm', "step")            
        index = self.zoomalg_names.index(zoomalg)
        self.w.zoom_alg.setCurrentIndex(index)

        zoomrate = self.t_.get('zoom_rate', math.sqrt(2.0))
        self.w.zoom_rate.setValue(zoomrate)
        self.w.zoom_rate.setEnabled(zoomalg!='step')
        self.w.stretch_factor.setEnabled(zoomalg!='step')

        self.scalebase_changed_ext_cb(prefs, None)
        
        scale_x, scale_y = self.fitsimage.get_scale_xy()
        self.w.scale_x.setText(str(scale_x))
        self.w.scale_y.setText(str(scale_y))

        scale_min = prefs.get('scale_min', 0.00001)
        self.w.scale_min.setValue(scale_min)
        scale_max = prefs.get('scale_max', 10000.0)
        self.w.scale_max.setValue(scale_max)

        # panning settings
        pan_x, pan_y = self.fitsimage.get_pan()
        self.w.pan_x.setText(str(pan_x+0.5))
        self.w.pan_y.setText(str(pan_y+0.5))

        self.w.reverse_pan.setChecked(prefs.get('reverse_pan', False))
        self.w.mark_center.setChecked(prefs.get('show_pan_position', False))

        # transform settings
        self.w.flip_x.setChecked(prefs.get('flip_x', False))
        self.w.flip_y.setChecked(prefs.get('flip_y', False))
        self.w.swap_xy.setChecked(prefs.get('swap_xy', False))
        self.w.rotate.setValue(prefs.get('rot_deg', 0.00))

        # auto cuts settings
        autocuts = prefs.get('autocuts', 'off')
        index = self.autocut_options.index(autocuts)
        self.w.cut_new.setCurrentIndex(index)

        autocut_method = prefs.get('autocut_method', None)
        if autocut_method == None:
            autocut_method = 'histogram'
        else:
            params = prefs.get('autocut_params', {})
            p = self.autocuts_cache.setdefault(autocut_method, {})
            p.update(params)

        self.config_autocut_params(autocut_method)

        # auto zoom settings
        auto_zoom = prefs.get('autozoom', 'off')
        index = self.autozoom_options.index(auto_zoom)
        self.w.zoom_new.setCurrentIndex(index)

        # wcs settings
        method = prefs.get('wcs_coords', "icrs")
        try:
            index = wcs.coord_types.index(method)
            self.w.wcs_coords.setCurrentIndex(index)
        except ValueError:
            pass

        method = prefs.get('wcs_display', "sexagesimal")
        try:
            index = wcs.display_types.index(method)
            self.w.wcs_display.setCurrentIndex(index)
        except ValueError:
            pass

        # misc settings
        prefs.setdefault('autocenter', False)
        self.w.center_new.setChecked(prefs['autocenter'])
        prefs.setdefault('switchnew', True)
        self.w.follow_new.setChecked(prefs['switchnew'])
        prefs.setdefault('raisenew', True)
        self.w.raise_new.setChecked(prefs['raisenew'])
        prefs.setdefault('genthumb', True)
        self.w.create_thumbnail.setChecked(prefs['genthumb'])

    def save_preferences(self):
        self.t_.save()

    def close(self):
        self.fv.stop_operation_channel(self.chname, str(self))
        return True
        
    def start(self):
        self.preferences_to_controls()

    def pause(self):
        pass
        
    def resume(self):
        pass
        
    def stop(self):
        self.gui_up = False
        
    def redo(self):
        pass

    def __str__(self):
        return 'preferences'
    
#END
