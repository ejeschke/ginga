#
# Preferences.py -- Preferences plugin for fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Nov 16 13:11:06 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from QtHelp import QtGui, QtCore

import cmap, imap
import QtHelp
import GingaPlugin

import Bunch


class Preferences(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Preferences, self).__init__(fv, fitsimage)

        self.chname = self.fv.get_channelName(self.fitsimage)
        self.prefs = self.fv.settings.getSettings(self.chname)

        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        rgbmap = fitsimage.get_rgbmap()
        self.calg_names = rgbmap.get_hash_algorithms()
        self.calg_names.sort()
        self.autozoom_options = self.fitsimage.get_autoscale_options()
        self.autocut_options = self.fitsimage.get_autolevels_options()

        self.fitsimage.add_callback('autocuts', self.autocuts_changed_cb)
        self.fitsimage.add_callback('autozoom', self.autozoom_changed_cb)

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

        fr = QtHelp.Frame("Colors")

        captions = (('Colormap', 'combobox', 'Intensity', 'combobox'),
                    ('Algorithm', 'combobox', 'Table Size', 'entry'),
                    ('Defaults', 'button'))
        w, b = QtHelp.build_info(captions)
        self.w.cmap_choice = b.colormap
        self.w.imap_choice = b.intensity
        self.w.calg_choice = b.algorithm
        self.w.table_size = b.table_size
        b.defaults.clicked.connect(lambda w: self.set_default_maps())
        b.colormap.setToolTip("Choose a color map for this image")
        b.intensity.setToolTip("Choose an intensity map for this image")
        b.algorithm.setToolTip("Choose a color mapping algorithm")
        b.table_size.setToolTip("Set size of the color mapping table")
        b.defaults.setToolTip("Restore default color and intensity maps")
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

        fr = QtHelp.Frame("Autozoom")

        captions = (('Zoom New', 'combobox'),
            ('Min Zoom', 'spinbutton', 'Max Zoom', 'spinbutton'))
        w, b = QtHelp.build_info(captions)
        self.w.btn_zoom_new = b.zoom_new
        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.addItem(name)
            index += 1
        option = self.fitsimage.t_autoscale
        index = self.autozoom_options.index(option)
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_autoscale)

        self.w.min_zoom = b.min_zoom
        self.w.max_zoom = b.max_zoom
        b.min_zoom.setRange(-20, 20)
        b.min_zoom.setSingleStep(1)
        b.min_zoom.valueChanged.connect(lambda w: self.set_zoom_minmax())
        b.max_zoom.setRange(-20, 20)
        b.max_zoom.setSingleStep(1)
        b.max_zoom.valueChanged.connect(lambda w: self.set_zoom_minmax())
        b.zoom_new.setToolTip("Automatically fit new images to window")
        b.min_zoom.setToolTip("Minimum zoom level for fitting to window")
        b.max_zoom.setToolTip("Maximum zoom level for fitting to window")
        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

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
        option = self.fitsimage.t_autolevels
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

        fr = QtHelp.Frame("Transform")

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(5)

        for name in ('Flip X', 'Flip Y', 'Swap XY' ):
            btn = QtGui.QCheckBox(name)
            btn.stateChanged.connect(lambda w: self.set_transforms())
            self.w[QtHelp._name_mangle(name, pfx='btn_')] = btn
            layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        self.w.btn_flip_x.setToolTip("Flip the image around the X axis")
        self.w.btn_flip_y.setToolTip("Flip the image around the Y axis")
        self.w.btn_swap_xy.setToolTip("Swap the X and Y axes in the image")

        fr.layout().addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)
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
            lambda w: self.controls_to_preferences())
        self.w.btn_raise_new_images = b.raise_new_images
        self.w.btn_raise_new_images.setChecked(True)
        self.w.btn_raise_new_images.stateChanged.connect(
            lambda w: self.controls_to_preferences())
        self.w.btn_create_thumbnail = b.create_thumbnail
        self.w.btn_create_thumbnail.setChecked(True)
        self.w.btn_create_thumbnail.stateChanged.connect(
            lambda w: self.controls_to_preferences())

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
        self.prefs.color_map = name

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
        self.prefs.intensity_map = name

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
        self.prefs.color_algorithm = name

    def set_default_maps(self):
        index = self.cmap_names.index(self.fv.default_cmap)
        self.w.cmap_choice.setCurrentIndex(index)
        index = self.imap_names.index(self.fv.default_imap)
        self.w.imap_choice.setCurrentIndex(index)
        self.set_cmap_byname(self.fv.default_cmap)
        self.prefs.color_map = self.fv.default_cmap
        self.set_imap_byname(self.fv.default_imap)
        self.prefs.intensity_map = self.fv.default_imap
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.setCurrentIndex(index)
        self.set_calg_byname(name)
        self.prefs.color_algorithm = name
        hashsize = 65535
        self.w.table_size.setText(str(hashsize))
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(hashsize)
        
    def set_autoscale(self, index):
        option = self.autozoom_options[index]
        self.fitsimage.enable_autoscale(option)
        self.prefs.auto_scale = option

    def autozoom_changed_cb(self, fitsimage, option):
        index = self.autozoom_options.index(option)
        self.w.btn_zoom_new.setCurrentIndex(index)

    def set_zoom_minmax(self):
        zmin = self.w.min_zoom.value()
        zmax = self.w.max_zoom.value()
        self.fitsimage.set_autoscale_limits(zmin, zmax)
        self.prefs.zoom_min = zmin
        self.prefs.zoom_max = zmax

    def config_autolevel_params(self, method, pct):
        index = self.autocut_methods.index(method)
        self.w.auto_method.setCurrentIndex(index)
        self.w.hist_pct.setValue(pct)
        if method != 'histogram':
            self.w.hist_pct.setEnabled(False)
        else:
            self.w.hist_pct.setEnabled(True)
        
    def set_autolevel_params(self):
        pct = self.w.hist_pct.value()
        idx = self.w.auto_method.currentIndex()
        method = self.autocut_methods[idx]
        self.w.hist_pct.setEnabled(method == 'histogram')
        self.fitsimage.set_autolevel_params(method, pct=pct)
        self.prefs.autocut_method = method
        self.prefs.autocut_hist_pct = pct

        self.fitsimage.auto_levels()
        
    def set_autolevels(self, index):
        option = self.autocut_options[index]
        self.fitsimage.enable_autolevels(option)
        self.prefs.auto_levels = option

    def autocuts_changed_cb(self, fitsimage, option):
        print "autocuts changed to %s" % option
        index = self.autocut_options.index(option)
        self.w.btn_cut_new.setCurrentIndex(index)

    def set_transforms(self):
        flipX = self.w.btn_flip_x.checkState()
        flipY = self.w.btn_flip_y.checkState()
        swapXY = self.w.btn_swap_xy.checkState()
        self.prefs.flipX = flipX
        self.prefs.flipY = flipY
        self.prefs.swapXY = swapXY

        self.fitsimage.transform(flipX, flipY, swapXY)
        return True

    def controls_to_preferences(self):
        prefs = self.prefs

        prefs.switchnew = self.w.btn_follow_new_images.checkState()
        prefs.raisenew = self.w.btn_raise_new_images.checkState()
        prefs.genthumb = self.w.btn_create_thumbnail.checkState()

        (flipX, flipY, swapXY) = self.fitsimage.get_transforms()
        prefs.flipX = flipX
        prefs.flipY = flipY
        prefs.swapXY = swapXY
        
        ## loval, hival = self.fitsimage.get_cut_levels()
        ## prefs.cutlo = loval
        ## prefs.cuthi = hival

        # Get the color and intensity maps
        rgbmap = self.fitsimage.get_rgbmap()
        cm = rgbmap.get_cmap()
        prefs.color_map = cm.name
        prefs.color_algorithm = rgbmap.get_hash_algorithm()
        im = rgbmap.get_imap()
        prefs.intensity_map = im.name

        prefs.auto_levels = self.fitsimage.t_autolevels
        prefs.autocut_method = self.fitsimage.t_autocut_method
        prefs.autocut_hist_pct = self.fitsimage.t_autocut_hist_pct

        prefs.auto_scale = self.fitsimage.t_autoscale
        zmin, zmax = self.fitsimage.get_autoscale_limits()
        prefs.zoom_min = zmin
        prefs.zoom_max = zmax
                
    def preferences_to_controls(self):
        prefs = self.prefs
        #print "prefs=%s" % (str(prefs))

        prefs.switchnew = prefs.get('switchnew', True)
        self.w.btn_follow_new_images.setChecked(prefs.switchnew)
        
        prefs.raisenew = prefs.get('raisenew', True)
        self.w.btn_raise_new_images.setChecked(prefs.raisenew)
        
        prefs.genthumb = prefs.get('genthumb', True)
        self.w.btn_create_thumbnail.setChecked(prefs.genthumb)

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

        auto_levels = self.fitsimage.t_autolevels
        index = self.autocut_options.index(auto_levels)
        self.w.btn_cut_new.setCurrentIndex(index)

        autocut_method = self.fitsimage.t_autocut_method
        autocut_hist_pct = self.fitsimage.t_autocut_hist_pct
        self.config_autolevel_params(autocut_method,
                                     autocut_hist_pct)
                                             
        auto_scale = self.fitsimage.t_autoscale
        index = self.autozoom_options.index(auto_scale)
        self.w.btn_zoom_new.setCurrentIndex(index)

        zmin, zmax = self.fitsimage.get_autoscale_limits()
        self.w.min_zoom.setValue(zmin)
        self.w.max_zoom.setValue(zmax)

        (flipX, flipY, swapXY) = self.fitsimage.get_transforms()
        self.w.btn_flip_x.setChecked(flipX)
        self.w.btn_flip_y.setChecked(flipY)
        self.w.btn_swap_xy.setChecked(swapXY)

    def save_preferences(self):
        self.controls_to_preferences()
        self.fv.settings.save(self.chname, "prefs")

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
