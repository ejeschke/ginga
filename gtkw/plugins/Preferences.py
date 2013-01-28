#
# Preferences.py -- Preferences plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import gtk
import GtkHelp

import cmap, imap
import GingaPlugin

import Bunch
import AutoCuts


class Preferences(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Preferences, self).__init__(fv, fitsimage)

        self.w.tooltips = self.fv.w.tooltips

        self.chname = self.fv.get_channelName(self.fitsimage)
        self.prefs = self.fv.settings.getSettings(self.chname)

        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        rgbmap = fitsimage.get_rgbmap()
        self.calg_names = rgbmap.get_hash_algorithms()
        self.calg_names.sort()
        self.autozoom_options = self.fitsimage.get_autozoom_options()
        self.autocut_options = self.fitsimage.get_autolevels_options()

        self.fitsimage.add_callback('autocuts', self.autocuts_changed_cb)
        self.fitsimage.add_callback('autozoom', self.autozoom_changed_cb)
        self.fitsimage.add_callback('pan-set', self.pan_changed_cb)

        self.t_ = self.fitsimage.get_settings()
        self.t_.getSetting('zoomalg').add_callback('set', self.set_zoomalg_ext_cb)
        self.t_.getSetting('zoomrate').add_callback('set', self.set_zoomrate_ext_cb)
        self.t_.getSetting('rot_deg').add_callback('set', self.set_rotate_ext_cb)
        for name in ('flipx', 'flipy', 'swapxy'):
            self.t_.getSetting(name).add_callback('set', self.set_transform_ext_cb)

        for name in ('flipx', 'flipy', 'swapxy'):
            self.t_.getSetting(name).add_callback('set', self.set_transform_ext_cb)

        for name in ('autolevels', 'autocut_method', 'autocut_hist_pct',
                     'autocut_bins'):
            self.t_.getSetting(name).add_callback('set', self.set_autolevels_ext_cb)
            
    def build_gui(self, container):
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)

        vbox = gtk.VBox(spacing=2)
        vbox.set_border_width(4)
        sw.add_with_viewport(vbox)

        ## self.w.conftitle = gtk.Label()
        ## #lbl.modify_font(self.font11)
        ## vbox.pack_start(self.w.conftitle, padding=4, fill=True, expand=False)

        # COLOR MAPPING OPTIONS
        fr = gtk.Frame("Colors")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Colormap', 'combobox', 'Intensity', 'combobox'),
                    ('Algorithm', 'combobox', 'Table Size', 'entry'),
                    ('Color Defaults', 'button'))
        w, b = GtkHelp.build_info(captions)
        self.w.cmap_choice = b.colormap
        self.w.imap_choice = b.intensity
        self.w.calg_choice = b.algorithm
        self.w.table_size = b.table_size
        b.color_defaults.connect('clicked', lambda w: self.set_default_maps())
        self.w.tooltips.set_tip(b.colormap,
                                "Choose a color map for this image")
        self.w.tooltips.set_tip(b.intensity,
                                "Choose an intensity map for this image")
        self.w.tooltips.set_tip(b.algorithm,
                                "Choose a color mapping algorithm")
        self.w.tooltips.set_tip(b.table_size,
                                "Set size of the color mapping table")
        self.w.tooltips.set_tip(b.color_defaults,
                                "Restore default color and intensity maps")
        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        combobox = b.colormap
        options = []
        index = 0
        for name in self.cmap_names:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        index = self.cmap_names.index(self.fv.default_cmap)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_cmap_cb)

        combobox = b.intensity
        options = []
        index = 0
        for name in self.imap_names:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        index = self.imap_names.index(self.fv.default_imap)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_imap_cb)

        combobox = b.algorithm
        options = []
        index = 0
        for name in self.calg_names:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        index = self.calg_names.index('linear')
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_calg_cb)

        entry = b.table_size
        entry.connect('activate', self.set_tablesize_cb)

        # ZOOM OPTIONS
        fr = gtk.Frame("Zoom")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Zoom Alg', 'combobox', 'Zoom Rate', 'spinbutton'),
                    ('Stretch XY', 'combobox', 'Stretch Factor', 'spinbutton'),
                    ('Zoom Defaults', 'button'))
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        index = 0
        for name in ('Step', 'Rate'):
            b.zoom_alg.insert_text(index, name)
            index += 1
        b.zoom_alg.set_active(0)
        self.w.tooltips.set_tip(b.zoom_alg,
                                "Choose Zoom algorithm")
        b.zoom_alg.sconnect('changed', lambda w: self.set_zoomalg_cb())
            
        index = 0
        for name in ('X', 'Y'):
            b.stretch_xy.insert_text(index, name)
            index += 1
        b.stretch_xy.set_active(0)
        self.w.tooltips.set_tip(b.stretch_xy,
                                "Stretch pixels in X or Y")
        b.stretch_xy.sconnect('changed', lambda w: self.set_stretch_cb())
            
        b.stretch_factor.set_range(1.0, 10.0)
        b.stretch_factor.set_value(1.0)
        b.stretch_factor.set_increments(0.01, 0.1)
        b.stretch_factor.set_digits(5)
        b.stretch_factor.set_numeric(True)
        b.stretch_factor.sconnect('value-changed', lambda w: self.set_stretch_cb())
        self.w.tooltips.set_tip(b.stretch_factor,
                                "Length of pixel relative to 1 on other side")
        b.stretch_factor.set_sensitive(False)

        b.zoom_rate.set_range(1.1, 3.0)
        b.zoom_rate.set_value(math.sqrt(2.0))
        b.zoom_rate.set_increments(0.1, 0.5)
        b.zoom_rate.set_digits(5)
        b.zoom_rate.set_numeric(True)
        b.zoom_rate.set_sensitive(False)
        self.w.tooltips.set_tip(b.zoom_rate,
                                "Step rate of increase/decrease per zoom level")
        b.zoom_rate.sconnect('value-changed', self.set_zoomrate_cb)
        b.zoom_defaults.connect('clicked', self.set_zoom_defaults_cb)
        
        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        # PAN
        fr = gtk.Frame("Panning")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Pan X', 'entry'),
                    ('Pan Y', 'entry', 'Center Image', 'button'),
                    ('Reverse Pan', 'checkbutton', 'Mark Center', 'checkbutton'))
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        pan_x, pan_y = self.fitsimage.get_pan()
        self.w.tooltips.set_tip(b.pan_x,
                                "Set the pan position in X axis")
        b.pan_x.set_text(str(pan_x+0.5))
        b.pan_x.connect("activate", lambda w: self.set_pan_cb())
        self.w.tooltips.set_tip(b.pan_y,
                                "Set the pan position in Y axis")
        b.pan_y.set_text(str(pan_y+0.5))
        b.pan_y.connect("activate", lambda w: self.set_pan_cb())
        self.w.tooltips.set_tip(b.center_image,
                                "Set the pan position to center of the image")
        b.center_image.connect("clicked", lambda w: self.center_image_cb())
        self.w.tooltips.set_tip(b.reverse_pan,
                                "Reverse the pan direction")
        b.reverse_pan.sconnect("toggled", lambda w: self.set_misc_cb())
        self.w.tooltips.set_tip(b.mark_center,
                                "Mark the center (pan locator)")
        b.mark_center.sconnect("toggled", lambda w: self.set_misc_cb())

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        # TRANSFORM OPTIONS
        fr = gtk.Frame("Transform")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Flip X', 'checkbutton', 'Flip Y', 'checkbutton', 
                     'Swap XY', 'checkbutton'), ('Rotate', 'spinbutton'),
                    ('Restore', 'button'),)
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        for btn in (b.flip_x, b.flip_y, b.swap_xy):
            btn.sconnect("toggled", lambda w: self.set_transforms_cb())
            btn.set_mode(True)
        self.w.tooltips.set_tip(b.flip_x,
                                "Flip the image around the X axis")
        self.w.tooltips.set_tip(b.flip_y,
                                "Flip the image around the Y axis")
        self.w.tooltips.set_tip(b.swap_xy,
                                "Swap the X and Y axes in the image")
        b.rotate.set_range(0.00, 360.0)
        b.rotate.set_value(0.00)
        b.rotate.set_increments(1.00, 10.0)
        b.rotate.set_digits(5)
        b.rotate.set_numeric(True)
        b.rotate.set_wrap(True)
        b.rotate.sconnect('value-changed', lambda w: self.rotate_cb())
        self.w.tooltips.set_tip(b.rotate,
                                "Rotate image around the pan position")
        self.w.tooltips.set_tip(b.restore,
                                "Clear any transforms and center image")
        b.restore.connect("clicked", lambda w: self.restore_cb())

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)
        
        # AUTOCUTS OPTIONS
        fr = gtk.Frame("Autocuts")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Cut New', 'combobox'),
                    ('Auto Method', 'combobox'),
                    ('Hist Pct', 'spinbutton'))
        w, b = GtkHelp.build_info(captions)
        self.w.tooltips.set_tip(b.cut_new,
                                "Automatically set cut levels for new images")
        self.w.tooltips.set_tip(b.auto_method,
                                "Choose algorithm for auto levels")
        self.w.tooltips.set_tip(b.hist_pct,
                                "Percentage of image to save for Histogram algorithm")

        self.w.btn_cut_new = b.cut_new
        combobox = b.cut_new
        index = 0
        for name in self.autocut_options:
            combobox.insert_text(index, name)
            index += 1
        option = self.t_['autolevels']
        index = self.autocut_options.index(option)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_autolevels)

        # Setup auto cuts method choice
        self.w.auto_method = b.auto_method
        combobox = b.auto_method
        index = 0
        self.autocut_method = self.t_['autocut_method']
        self.autocut_methods = self.fitsimage.get_autocut_methods()
        for name in self.autocut_methods:
            combobox.insert_text(index, name)
            index += 1
        index = self.autocut_methods.index(self.autocut_method)
        combobox.set_active(index)
        combobox.sconnect('changed', lambda w: self.set_autolevel_params())

        self.w.hist_pct = b.hist_pct
        b.hist_pct.set_range(0.90, 1.0)
        b.hist_pct.set_value(0.995)
        b.hist_pct.set_increments(0.001, 0.01)
        b.hist_pct.set_digits(5)
        b.hist_pct.set_numeric(True)
        b.hist_pct.sconnect('value-changed', lambda w: self.set_autolevel_params())
        b.hist_pct.set_sensitive(self.autocut_method == 'histogram')
        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        # AUTOZOOM OPTIONS
        fr = gtk.Frame("Autozoom")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Zoom New', 'combobox'),
            ('Min Zoom', 'spinbutton', 'Max Zoom', 'spinbutton'))
        w, b = GtkHelp.build_info(captions)
        self.w.btn_zoom_new = b.zoom_new
        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.insert_text(index, name)
            index += 1
        option = self.t_['autozoom']
        index = self.autozoom_options.index(option)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_autozoom)

        self.w.min_zoom = b.min_zoom
        self.w.max_zoom = b.max_zoom
        b.min_zoom.set_range(-20, 20)
        b.min_zoom.set_increments(1, 10)
        b.min_zoom.set_numeric(True)
        b.min_zoom.sconnect('value-changed', lambda w: self.set_zoom_minmax())
        b.max_zoom.set_range(-20, 20)
        b.max_zoom.set_increments(1, 10)
        b.max_zoom.set_numeric(True)
        b.max_zoom.sconnect('value-changed', lambda w: self.set_zoom_minmax())
        self.w.tooltips.set_tip(b.zoom_new,
                                "Automatically fit new images to window")
        self.w.tooltips.set_tip(b.min_zoom,
                                "Minimum zoom level for fitting to window")
        self.w.tooltips.set_tip(b.max_zoom,
                                "Maximum zoom level for fitting to window")
        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        fr = gtk.Frame("New Images")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Follow new images', 'checkbutton',
                     'Raise new images', 'checkbutton'),
                    ('Create thumbnail', 'checkbutton'),)
        w, b = GtkHelp.build_info(captions)
        self.w.tooltips.set_tip(b.follow_new_images,
                                "View new images as they arrive")
        self.w.tooltips.set_tip(b.create_thumbnail,
                                "Create thumbnail for new images")

        self.w.btn_follow_new_images = b.follow_new_images
        self.w.btn_follow_new_images.set_active(True)
        self.w.btn_follow_new_images.sconnect("toggled",
                                              lambda w: self.controls_to_preferences())
        self.w.btn_raise_new_images = b.raise_new_images
        self.w.btn_raise_new_images.set_active(True)
        self.w.btn_raise_new_images.sconnect("toggled",
                                              lambda w: self.controls_to_preferences())
        self.w.btn_create_thumbnail = b.create_thumbnail
        self.w.btn_create_thumbnail.set_active(True)
        self.w.btn_create_thumbnail.sconnect("toggled",
                                              lambda w: self.controls_to_preferences())

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)
        btns.set_child_size(15, -1)

        btn = gtk.Button("Save Settings")
        btn.connect('clicked', lambda w: self.save_preferences())
        btns.add(btn)
        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        vbox.pack_start(btns, padding=4, fill=True, expand=False)

        vbox.show_all()

        container.pack_start(sw, padding=0, fill=True, expand=True)

    def set_cmap_cb(self, w):
        """This callback is invoked when the user selects a new color
        map from the preferences pane."""
        index = w.get_active()
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
        
    def set_imap_cb(self, w):
        """This callback is invoked when the user selects a new intensity
        map from the preferences pane."""
        index = w.get_active()
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

    def set_calg_cb(self, w):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the preferences pane."""
        index = w.get_active()
        name = self.calg_names[index]
        self.set_calg_byname(name)

    def set_tablesize_cb(self, w):
        value = int(w.get_text())
        print "value is %d" % (value) 
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
        self.w.cmap_choice.set_active(index)
        index = self.imap_names.index(self.fv.default_imap)
        self.w.imap_choice.set_active(index)
        self.set_cmap_byname(self.fv.default_cmap)
        self.prefs.color_map = self.fv.default_cmap
        self.set_imap_byname(self.fv.default_imap)
        self.prefs.intensity_map = self.fv.default_imap
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.set_active(index)
        self.set_calg_byname(name)
        self.prefs.color_algorithm = name
        hashsize = 65535
        self.w.table_size.set_text(str(hashsize))
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(hashsize)
        
    def set_zoomrate_cb(self, w):
        rate = float(w.get_value())
        self.t_.set(zoomrate=rate)
        
    def set_zoomrate_ext_cb(self, setting, value):
        self.w.zoom_rate.set_value(value)
        
    def set_zoomalg_cb(self):
        idx = self.w.zoom_alg.get_active()
        values = ('step', 'rate')
        self.t_.set(zoomalg=values[idx])
        
    def set_zoomalg_ext_cb(self, setting, value):
        if value == 'step':
            self.w.zoom_alg.set_active(0)
            self.w.zoom_rate.set_sensitive(False)
            self.w.stretch_factor.set_sensitive(False)
        else:
            self.w.zoom_alg.set_active(1)
            self.w.zoom_rate.set_sensitive(True)
            self.w.stretch_factor.set_sensitive(True)

    def set_zoom_defaults_cb(self, w):
        rate = math.sqrt(2.0)
        self.w.stretch_factor.set_value(1.0)
        self.t_.set(zoomalg='step', zoomrate=rate,
                    scale_x_base=1.0, scale_y_base=1.0)
        
    def set_stretch_cb(self):
        axis = self.w.stretch_xy.get_active()
        value = self.w.stretch_factor.get_value()
        if axis == 0:
            self.t_.set(scale_x_base=value, scale_y_base=1.0)
        else:
            self.t_.set(scale_x_base=1.0, scale_y_base=value)
        
    def set_autozoom(self, w):
        idx = w.get_active()
        option = self.autozoom_options[idx]
        self.fitsimage.enable_autozoom(option)
        self.prefs.auto_scale = option

    def pan_changed_cb(self, fitsimage):
        if self.w.has_key('pan_x'):
            pan_x, pan_y = fitsimage.get_pan()
            fits_x, fits_y = pan_x + 0.5, pan_y + 0.5
            self.w.pan_x.set_text(str(fits_x))
            self.w.pan_y.set_text(str(fits_y))

    def autozoom_changed_cb(self, fitsimage, option):
        index = self.autozoom_options.index(option)
        if self.w.has_key('btn_zoom_new'):
            self.w.btn_zoom_new.set_active(index)

    def set_zoom_minmax(self):
        zmin = self.w.min_zoom.get_value()
        zmax = self.w.max_zoom.get_value()
        self.fitsimage.set_autozoom_limits(zmin, zmax)
        self.prefs.zoom_min = zmin
        self.prefs.zoom_max = zmax

    def config_autolevel_params(self, method, pct):
        index = self.autocut_methods.index(method)
        self.w.auto_method.set_active(index)
        self.w.hist_pct.set_value(pct)
        if method != 'histogram':
            self.w.hist_pct.set_sensitive(False)
        else:
            self.w.hist_pct.set_sensitive(True)
        
    def set_autolevels_ext_cb(self, setting, value):
        method = self.t_['autocuts_method']
        pct = self.t_['autocuts_hist_pct']
        self.config_autolevel_params(method, pct)

    def set_autolevel_params(self):
        pct = self.w.hist_pct.get_value()
        idx = self.w.auto_method.get_active()
        method = self.autocut_methods[idx]
        self.w.hist_pct.set_sensitive(method == 'histogram')
        self.fitsimage.set_autolevel_params(method, pct=pct)
        self.prefs.autocut_method = method
        self.prefs.autocut_hist_pct = pct

        self.fitsimage.auto_levels()
        
    def set_autolevels(self, w):
        idx = w.get_active()
        option = self.autocut_options[idx]
        self.fitsimage.enable_autolevels(option)
        self.prefs.auto_levels = option

    def autocuts_changed_cb(self, fitsimage, option):
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        if self.w.has_key('btn_cut_new'):
            self.w.btn_cut_new.set_active(index)

    def set_transforms_cb(self):
        flipx = self.w.flip_x.get_active()
        flipy = self.w.flip_y.get_active()
        swapxy = self.w.swap_xy.get_active()
        self.t_.set(flipx=flipx, flipy=flipy, swapxy=swapxy)
        return True

    def set_transform_ext_cb(self, setting, value):
        flipx, flipy, swapxy = self.t_['flipx'], self.t_['flipy'], self.t_['swapxy']
        self.w.flip_x.set_active(flipx)
        self.w.flip_y.set_active(flipy)
        self.w.swap_xy.set_active(swapxy)
        self.prefs.flipX = flipx
        self.prefs.flipY = flipy
        self.prefs.swapXY = swapxy
        
    def rotate_cb(self):
        deg = self.w.rotate.get_value()
        self.t_.set(rot_deg=deg)
        return True

    def set_rotate_ext_cb(self, setting, value):
        self.w.rotate.set_value(value)
        self.prefs.rotate_deg = value
        return True

    def center_image_cb(self):
        self.fitsimage.center_image()
        return True

    def set_pan_cb(self):
        pan_x = float(self.w.pan_x.get_text()) - 0.5
        pan_y = float(self.w.pan_y.get_text()) - 0.5
        self.fitsimage.set_pan(pan_x, pan_y)
        return True

    def restore_cb(self):
        self.w.flip_x.set_active(False)
        self.w.flip_y.set_active(False)
        self.w.swap_xy.set_active(False)
        self.fitsimage.center_image(redraw=False)
        self.fitsimage.rotate(0.0, redraw=False)
        self.set_transforms_cb()
        return True

    def set_misc_cb(self):
        revpan = self.w.reverse_pan.get_active()
        self.prefs.reverse_pan = revpan
        self.fitsimage.set_pan_reverse(revpan)

        markc = self.w.mark_center.get_active()
        self.prefs.mark_center = markc
        self.fitsimage.show_pan_mark(markc)
        return True

    def controls_to_preferences(self):
        prefs = self.prefs

        prefs.switchnew = self.w.btn_follow_new_images.get_active()
        prefs.raisenew = self.w.btn_raise_new_images.get_active()
        prefs.genthumb = self.w.btn_create_thumbnail.get_active()

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

        prefs.auto_levels = self.t_['autolevels']
        prefs.autocut_method = self.t_['autocut_method']
        prefs.autocut_hist_pct = self.t_['autocut_hist_pct']

        prefs.auto_scale = self.t_['autozoom']
        zmin, zmax = self.fitsimage.get_autozoom_limits()
        prefs.zoom_min = zmin
        prefs.zoom_max = zmax
                
        prefs.reverse_pan = self.t_['reverse_pan']

    def preferences_to_controls(self):
        prefs = self.prefs
        #print "prefs=%s" % (str(prefs))

        prefs.switchnew = prefs.get('switchnew', True)
        self.w.btn_follow_new_images.set_active(prefs.switchnew)
        
        prefs.raisenew = prefs.get('raisenew', True)
        self.w.btn_raise_new_images.set_active(prefs.raisenew)
        
        prefs.genthumb = prefs.get('genthumb', True)
        self.w.btn_create_thumbnail.set_active(prefs.genthumb)

        rgbmap = self.fitsimage.get_rgbmap()
        cm = rgbmap.get_cmap()
        index = self.cmap_names.index(cm.name)
        self.w.cmap_choice.set_active(index)
        calg = rgbmap.get_hash_algorithm()
        index = self.calg_names.index(calg)
        self.w.calg_choice.set_active(index)
        size = rgbmap.get_hash_size()
        self.w.table_size.set_text(str(size))

        im = rgbmap.get_imap()
        index = self.imap_names.index(im.name)
        self.w.imap_choice.set_active(index)

        auto_levels = self.t_['autolevels']
        index = self.autocut_options.index(auto_levels)
        self.w.btn_cut_new.set_active(index)

        autocut_method = self.t_['autocut_method']
        autocut_hist_pct = self.t_['autocut_hist_pct']
        self.config_autolevel_params(autocut_method,
                                     autocut_hist_pct)
                                             
        auto_scale = self.t_['autozoom']
        index = self.autozoom_options.index(auto_scale)
        self.w.btn_zoom_new.set_active(index)

        zmin, zmax = self.fitsimage.get_autozoom_limits()
        self.w.min_zoom.set_value(zmin)
        self.w.max_zoom.set_value(zmax)

        (flipX, flipY, swapXY) = self.fitsimage.get_transforms()
        self.w.flip_x.set_active(flipX)
        self.w.flip_y.set_active(flipY)
        self.w.swap_xy.set_active(swapXY)

        revpan = self.t_['reverse_pan']
        self.w.reverse_pan.set_active(revpan)

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
