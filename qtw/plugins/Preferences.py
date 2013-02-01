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
from PyQt4 import QtGui, QtCore

import cmap, imap
import QtHelp
import GingaPlugin

import Bunch
import AutoCuts


class Preferences(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Preferences, self).__init__(fv, fitsimage)

        self.chname = self.fv.get_channelName(self.fitsimage)

        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        rgbmap = fitsimage.get_rgbmap()
        self.calg_names = rgbmap.get_hash_algorithms()
        self.calg_names.sort()
        self.autozoom_options = self.fitsimage.get_autozoom_options()
        self.autocut_options = self.fitsimage.get_autolevels_options()

        self.fitsimage.add_callback('autocuts', self.autocuts_changed_cb)
        self.fitsimage.add_callback('autozoom', self.autozoom_changed_cb)
        self.fitsimage.add_callback('pan-set', self.pan_changed_ext_cb)
        self.fitsimage.add_callback('zoom-set', self.scale_changed_ext_cb)

        self.t_ = self.fitsimage.get_settings()
        self.t_.getSetting('zoomalg').add_callback('set', self.set_zoomalg_ext_cb)
        self.t_.getSetting('zoomrate').add_callback('set', self.set_zoomrate_ext_cb)
        for key in ['scale_x_base', 'scale_y_base']:
            self.t_.getSetting(key).add_callback('set', self.scalebase_changed_ext_cb)
        self.t_.getSetting('rot_deg').add_callback('set', self.set_rotate_ext_cb)
        for name in ('flipx', 'flipy', 'swapxy'):
            self.t_.getSetting(name).add_callback('set', self.set_transform_ext_cb)

        for name in ('autolevels', 'autocut_method', 'autocut_hist_pct',
                     'autocut_bins'):
            self.t_.getSetting(name).add_callback('set', self.set_autolevels_ext_cb)

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
        b.color_defaults.clicked.connect(lambda w: self.set_default_maps())
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
        index = self.cmap_names.index(self.fv.default_cmap)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_cmap_cb)

        combobox = b.intensity
        options = []
        index = 0
        for name in self.imap_names:
            options.append(name)
            combobox.addItem(name)
            index += 1
        index = self.imap_names.index(self.fv.default_imap)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_imap_cb)

        combobox = b.algorithm
        options = []
        index = 0
        for name in self.calg_names:
            options.append(name)
            combobox.addItem(name)
            index += 1
        index = self.calg_names.index('linear')
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_calg_cb)

        entry = b.table_size
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
        for name in ('Step', 'Rate'):
            b.zoom_alg.addItem(name)
            index += 1
        b.zoom_alg.setCurrentIndex(0)
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
        b.stretch_factor.setEnabled(False)

        b.zoom_rate.setRange(1.1, 3.0)
        b.zoom_rate.setValue(math.sqrt(2.0))
        b.zoom_rate.setSingleStep(0.1)
        b.zoom_rate.setDecimals(8)
        b.zoom_rate.setEnabled(False)
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

        for btn in (b.flip_x, b.flip_y, b.swap_xy):
            btn.stateChanged.connect(lambda w: self.set_transforms_cb())
        b.flip_x.setToolTip("Flip the image around the X axis")
        b.flip_y.setToolTip("Flip the image around the Y axis")
        b.swap_xy.setToolTip("Swap the X and Y axes in the image")
        b.rotate.setToolTip("Rotate the image around the pan position")
        b.restore.setToolTip("Clear any transforms and center image")
        b.restore.clicked.connect(lambda w: self.restore_cb())

        b.rotate.setRange(0.00, 360.0)
        b.rotate.setValue(0.00)
        b.rotate.setSingleStep(10.0)
        b.rotate.setDecimals(5)
        b.rotate.valueChanged.connect(lambda w: self.rotate_cb())

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        # AUTOCUTS OPTIONS
        fr = QtHelp.Frame("Autocuts")

        captions = (('Cut New', 'combobox'),
                    ('Auto Method', 'combobox'),
                    ('Hist Pct', 'spinfloat'))
        w, b = QtHelp.build_info(captions)
        b.cut_new.setToolTip("Automatically set cut levels for new images")
        b.auto_method.setToolTip("Choose algorithm for auto levels")
        b.hist_pct.setToolTip("Percentage of image to save for Histogram algorithm")

        self.w.btn_cut_new = b.cut_new
        combobox = b.cut_new
        index = 0
        for name in self.autocut_options:
            combobox.addItem(name)
            index += 1
        option = self.t_['autolevels']
        index = self.autocut_options.index(option)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_autolevels)

        # Setup auto cuts method choice
        self.w.auto_method = b.auto_method
        combobox = b.auto_method
        index = 0
        self.autocut_method = self.fv.default_autocut_method
        self.autocut_methods = self.fitsimage.get_autocut_methods()
        for name in self.autocut_methods:
            combobox.addItem(name)
            index += 1
        index = self.autocut_methods.index(self.autocut_method)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(lambda w: self.set_autolevel_params())

        self.w.hist_pct = b.hist_pct
        b.hist_pct.setRange(0.90, 1.0)
        b.hist_pct.setValue(0.995)
        b.hist_pct.setSingleStep(0.001)
        b.hist_pct.setDecimals(5)
        b.hist_pct.valueChanged.connect(lambda w: self.set_autolevel_params())
        b.hist_pct.setEnabled(self.autocut_method == 'histogram')
        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        # AUTOZOOM OPTIONS
        fr = QtHelp.Frame("Autozoom")

        captions = (('Zoom New', 'combobox'),
                    )
        w, b = QtHelp.build_info(captions)
        self.w.btn_zoom_new = b.zoom_new
        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.addItem(name)
            index += 1
        option = self.t_['autozoom']
        index = self.autozoom_options.index(option)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_autozoom_cb)

        b.zoom_new.setToolTip("Automatically fit new images to window")

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        fr = QtHelp.Frame("New Images")

        captions = (('Follow new images', 'checkbutton',
                     'Raise new images', 'checkbutton'),
                    ('Create thumbnail', 'checkbutton'),)
        w, b = QtHelp.build_info(captions)
        b.follow_new_images.setToolTip("View new images as they arrive")
        b.create_thumbnail.setToolTip("Create thumbnail for new images")

        self.w.btn_follow_new_images = b.follow_new_images
        self.w.btn_follow_new_images.setChecked(True)
        self.w.btn_follow_new_images.stateChanged.connect(
            lambda w: self.set_chprefs_cb())
        self.w.btn_raise_new_images = b.raise_new_images
        self.w.btn_raise_new_images.setChecked(True)
        self.w.btn_raise_new_images.stateChanged.connect(
            lambda w: self.set_chprefs_cb())
        self.w.btn_create_thumbnail = b.create_thumbnail
        self.w.btn_create_thumbnail.setChecked(True)
        self.w.btn_create_thumbnail.stateChanged.connect(
            lambda w: self.set_chprefs_cb())

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)
        #layout.set_child_size(15, -1)

        btn = QtGui.QPushButton("Save Settings")
        btn.clicked.connect(lambda w: self.save_preferences())
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(lambda w: self.close())
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        #container.addWidget(sw, stretch=1, alignment=QtCore.Qt.AlignTop)
        container.addWidget(sw, stretch=1)

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
            raise FitsImageError("No such color map name: '%s'" % (name))

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
            raise FitsImageError("No such intensity map name: '%s'" % (name))

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

    def set_calg_byname(self, name, redraw=True):
        # Get color mapping algorithm
        rgbmap = self.fitsimage.get_rgbmap()
        try:
            rgbmap.set_hash_algorithm(name)
        except KeyError:
            raise FitsImageError("No such color algorithm name: '%s'" % (name))

        if redraw:
            self.fitsimage.redraw(whence=2)
        self.t_.set(color_algorithm=name)

    def set_default_maps(self):
        index = self.cmap_names.index(self.fv.default_cmap)
        self.w.cmap_choice.setCurrentIndex(index)
        index = self.imap_names.index(self.fv.default_imap)
        self.w.imap_choice.setCurrentIndex(index)
        self.set_cmap_byname(self.fv.default_cmap)
        self.t_.set(color_map=self.fv.default_cmap)
        self.set_imap_byname(self.fv.default_imap)
        self.t_.set(intensity_map=self.fv.default_imap)
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.setCurrentIndex(index)
        self.set_calg_byname(name)
        self.t_.set(color_algorithm=name)
        hashsize = 65535
        self.w.table_size.setText(str(hashsize))
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(hashsize)
        
    def set_zoomrate_cb(self):
        rate = self.w.zoom_rate.value()
        self.t_.set(zoomrate=rate)
        
    def set_zoomrate_ext_cb(self, setting, value):
        self.w.zoom_rate.setValue(value)
        
    def set_zoomalg_cb(self, idx):
        values = ('step', 'rate')
        self.t_.set(zoomalg=values[idx])
        
    def set_zoomalg_ext_cb(self, setting, value):
        if value == 'step':
            self.w.zoom_alg.setCurrentIndex(0)
            self.w.zoom_rate.setEnabled(False)
            self.w.stretch_factor.setEnabled(False)
        else:
            self.w.zoom_alg.setCurrentIndex(1)
            self.w.zoom_rate.setEnabled(True)
            self.w.stretch_factor.setEnabled(True)

    def scalebase_changed_ext_cb(self, setting, value):
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
            idx = self.w.stretch_xy.get_active()

        # Update stretch controls to reflect actual scale
        self.w.stretch_xy.setCurrentIndex(idx)
        self.w.stretch_factor.setValue(ratio)
        
    def set_zoom_defaults_cb(self):
        rate = math.sqrt(2.0)
        self.w.stretch_factor.setValue(1.0)
        self.t_.set(zoomalg='step', zoomrate=rate,
                    scale_x_base=1.0, scale_y_base=1.0)
        
    def set_stretch_cb(self):
        axis = self.w.stretch_xy.currentIndex()
        value = self.w.stretch_factor.value()
        if axis == 0:
            self.t_.set(scale_x_base=value, scale_y_base=1.0)
        else:
            self.t_.set(scale_x_base=1.0, scale_y_base=value)
        
    def pan_changed_ext_cb(self, fitsimage):
        if self.w.has_key('pan_x'):
            pan_x, pan_y = fitsimage.get_pan()
            fits_x, fits_y = pan_x + 0.5, pan_y + 0.5
            self.w.pan_x.setText(str(fits_x))
            self.w.pan_y.setText(str(fits_y))

    def set_scale_cb(self):
        scale_x = float(self.w.scale_x.text())
        scale_y = float(self.w.scale_y.text())
        self.fitsimage.scale_to(scale_x, scale_y)

    def scale_changed_ext_cb(self, fitsimage, zoomlevel, scale_x, scale_y):
        if not self.w.has_key('scale_x'):
            return
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

    def autozoom_changed_cb(self, fitsimage, option):
        index = self.autozoom_options.index(option)
        self.w.btn_zoom_new.setCurrentIndex(index)

    def config_autolevel_params(self, method, pct):
        index = self.autocut_methods.index(method)
        self.w.auto_method.setCurrentIndex(index)
        self.w.hist_pct.setValue(pct)
        if method != 'histogram':
            self.w.hist_pct.setEnabled(False)
        else:
            self.w.hist_pct.setEnabled(True)
        
    def set_autolevels_ext_cb(self, setting, value):
        method = self.t_['autocuts_method']
        pct = self.t_['autocuts_hist_pct']
        self.config_autolevel_params(method, pct)

    def set_autolevel_params(self):
        pct = self.w.hist_pct.value()
        idx = self.w.auto_method.currentIndex()
        method = self.autocut_methods[idx]
        self.w.hist_pct.setEnabled(method == 'histogram')
        self.fitsimage.set_autolevel_params(method, pct=pct)
        self.t_.set(autocut_method=method, autocut_hist_pct=pct)

    def set_autolevels(self, index):
        option = self.autocut_options[index]
        self.fitsimage.enable_autolevels(option)
        self.t_.set(autolevels=option)

    def autocuts_changed_cb(self, fitsimage, option):
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        self.w.btn_cut_new.setCurrentIndex(index)

    def set_transforms_cb(self):
        flipx = self.w.flip_x.checkState()
        flipy = self.w.flip_y.checkState()
        swapxy = self.w.swap_xy.checkState()
        self.t_.set(flipx=flipx, flipy=flipy, swapxy=swapxy)
        return True

    def set_transform_ext_cb(self, setting, value):
        flipx, flipy, swapxy = self.t_['flipx'], self.t_['flipy'], self.t_['swapxy']
        self.w.flip_x.setChecked(flipx)
        self.w.flip_y.setChecked(flipy)
        self.w.swap_xy.setChecked(swapxy)
        
    def rotate_cb(self):
        deg = self.w.rotate.value()
        self.t_.set(rot_deg=deg)
        return True

    def set_rotate_ext_cb(self, setting, value):
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
        self.t_.set(flipx=False, flipy=False, swapxy=False,
                    rot_deg=0.0)
        self.fitsimage.center_image()
        return True

    def set_misc_cb(self):
        revpan = self.w.reverse_pan.checkState()
        self.t_.set(reverse_pan=revpan)
        self.fitsimage.set_pan_reverse(revpan)

        markc = self.w.mark_center.checkState()
        self.t_.set(mark_center=markc)
        self.fitsimage.show_pan_mark(markc)
        return True

    def set_chprefs_cb(self):
        switchnew = self.w.follow_new_images.get_active()
        raisenew = self.w.raise_new_images.get_active()
        genthumb = self.w.create_thumb.get_active()
        self.t_.set(switchnew=switchnew, raisenew=raisenew,
                    genthumb=genthumb)

    def preferences_to_controls(self):
        prefs = self.t_

        prefs.setdefault('switchnew', True)
        self.w.btn_follow_new_images.setChecked(prefs['switchnew'])
        
        prefs.setdefault('raisenew', True)
        self.w.btn_raise_new_images.setChecked(prefs['raisenew'])
        
        prefs.setdefault('genthumb', True)
        self.w.btn_create_thumbnail.setChecked(prefs['genthumb'])

        rgbmap = self.fitsimage.get_rgbmap()
        cm = rgbmap.get_cmap()
        index = self.cmap_names.index(cm.name)
        self.w.cmap_choice.setCurrentIndex(index)
        calg = rgbmap.get_hash_algorithm()
        index = self.calg_names.index(calg)
        self.w.calg_choice.setCurrentIndex(index)
        size = rgbmap.get_hash_size()
        self.w.table_size.setText(str(size))

        im = rgbmap.get_imap()
        index = self.imap_names.index(im.name)
        self.w.imap_choice.setCurrentIndex(index)

        autolevels = prefs['autolevels']
        index = self.autocut_options.index(autolevels)
        self.w.btn_cut_new.setCurrentIndex(index)

        autocut_method = prefs['autocut_method']
        autocut_hist_pct = prefs['autocut_hist_pct']
        self.config_autolevel_params(autocut_method,
                                     autocut_hist_pct)
                                             
        auto_zoom = prefs['autozoom']
        index = self.autozoom_options.index(auto_zoom)
        self.w.btn_zoom_new.setCurrentIndex(index)

        (flipX, flipY, swapXY) = self.fitsimage.get_transforms()
        self.w.flip_x.setChecked(flipX)
        self.w.flip_y.setChecked(flipY)
        self.w.swap_xy.setChecked(swapXY)

        revpan = prefs['reverse_pan']
        self.w.reverse_pan.setChecked(revpan)

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
        pass
        
    def redo(self):
        pass

    def __str__(self):
        return 'preferences'
    
#END
