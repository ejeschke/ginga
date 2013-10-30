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
from ginga.gtkw import GtkHelp

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

        self.t_ = fitsimage.get_settings()
        self.t_.getSetting('autocuts').add_callback('set',
                                               self.autocuts_changed_ext_cb)
        self.t_.getSetting('autozoom').add_callback('set',
                                               self.autozoom_changed_ext_cb)
        for key in ['scale']:
            self.t_.getSetting(key).add_callback('set',
                                          self.scale_changed_ext_cb)
        for key in ['pan']:
            self.t_.getSetting(key).add_callback('set',
                                          self.pan_changed_ext_cb)
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
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)

        vbox = gtk.VBox(spacing=2)
        vbox.set_border_width(4)
        sw.add_with_viewport(vbox)

       # COLOR MAPPING OPTIONS
        fr = gtk.Frame(label="Colors")
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
        b.colormap.set_tooltip_text("Choose a color map for this image")
        b.intensity.set_tooltip_text("Choose an intensity map for this image")
        b.algorithm.set_tooltip_text("Choose a color mapping algorithm")
        b.table_size.set_tooltip_text("Set size of the color mapping table")
        b.color_defaults.set_tooltip_text("Restore default color and intensity maps")
        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        combobox = b.colormap
        options = []
        index = 0
        for name in self.cmap_names:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        cmap_name = self.t_.get('color_map', "ramp")
        try:
            index = self.cmap_names.index(cmap_name)
        except Exception:
            index = self.cmap_names.index('ramp')
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_cmap_cb)

        combobox = b.intensity
        options = []
        index = 0
        for name in self.imap_names:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        imap_name = self.t_.get('intensity_map', "ramp")
        try:
            index = self.imap_names.index(imap_name)
        except Exception:
            index = self.imap_names.index('ramp')
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_imap_cb)

        combobox = b.algorithm
        options = []
        index = 0
        for name in self.calg_names:
            options.append(name)
            combobox.insert_text(index, name)
            index += 1
        index = self.calg_names.index(self.t_.get('color_algorithm', "linear"))
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_calg_cb)

        entry = b.table_size
        entry.set_text(str(self.t_.get('color_hashsize', 65535)))
        entry.connect('activate', self.set_tablesize_cb)

        # ZOOM OPTIONS
        fr = gtk.Frame(label="Zoom")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Zoom Alg', 'combobox', 'Zoom Rate', 'spinbutton'),
                    ('Stretch XY', 'combobox', 'Stretch Factor', 'spinbutton'),
                    ('Scale X', 'entry', 'Scale Y', 'entry'),
                    ('Scale Min', 'spinbutton', 'Scale Max', 'spinbutton'),
                    ('Zoom Defaults', 'button'))
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        index = 0
        for name in self.zoomalg_names:
            b.zoom_alg.insert_text(index, name.capitalize())
            index += 1
        zoomalg = self.t_.get('zoom_algorithm', "step")            
        index = self.zoomalg_names.index(zoomalg)
        b.zoom_alg.set_active(index)
        b.zoom_alg.set_tooltip_text("Choose Zoom algorithm")
        b.zoom_alg.sconnect('changed', lambda w: self.set_zoomalg_cb())
            
        index = 0
        for name in ('X', 'Y'):
            b.stretch_xy.insert_text(index, name)
            index += 1
        b.stretch_xy.set_active(0)
        b.stretch_xy.set_tooltip_text("Stretch pixels in X or Y")
        b.stretch_xy.sconnect('changed', lambda w: self.set_stretch_cb())
            
        b.stretch_factor.set_range(1.0, 10.0)
        b.stretch_factor.set_value(1.0)
        b.stretch_factor.set_increments(0.1, 0.25)
        b.stretch_factor.set_digits(5)
        b.stretch_factor.set_numeric(True)
        b.stretch_factor.sconnect('value-changed', lambda w: self.set_stretch_cb())
        b.stretch_factor.set_tooltip_text("Length of pixel relative to 1 on other side")
        b.stretch_factor.set_sensitive(zoomalg!='step')

        zoomrate = self.t_.get('zoom_rate', math.sqrt(2.0))
        b.zoom_rate.set_range(1.1, 3.0)
        b.zoom_rate.set_value(zoomrate)
        b.zoom_rate.set_increments(0.1, 0.5)
        b.zoom_rate.set_digits(5)
        b.zoom_rate.set_numeric(True)
        b.zoom_rate.set_sensitive(zoomalg!='step')
        b.zoom_rate.set_tooltip_text("Step rate of increase/decrease per zoom level")
        b.zoom_rate.sconnect('value-changed', self.set_zoomrate_cb)
        b.zoom_defaults.connect('clicked', self.set_zoom_defaults_cb)
        
        scale_x, scale_y = self.fitsimage.get_scale_xy()
        b.scale_x.set_tooltip_text("Set the scale in X axis")
        b.scale_x.set_text(str(scale_x))
        b.scale_x.connect("activate", lambda w: self.set_scale_cb())
        b.scale_y.set_tooltip_text("Set the scale in Y axis")
        b.scale_y.set_text(str(scale_y))
        b.scale_y.connect("activate", lambda w: self.set_scale_cb())

        scale_min, scale_max = self.t_['scale_min'], self.t_['scale_max']
        b.scale_min.set_range(0.00001, 1.0)
        b.scale_min.set_value(scale_min)
        b.scale_min.set_increments(1.0, 10.0)
        b.scale_min.set_digits(5)
        b.scale_min.set_numeric(True)
        b.scale_min.sconnect('value-changed', lambda w: self.set_scale_limit_cb())
        b.scale_min.set_tooltip_text("Set the minimum allowed scale in any axis")

        b.scale_max.set_range(1.0, 10000.0)
        b.scale_max.set_value(scale_max)
        b.scale_max.set_increments(1.0, 10.0)
        b.scale_max.set_digits(5)
        b.scale_max.set_numeric(True)
        b.scale_max.sconnect('value-changed', lambda w: self.set_scale_limit_cb())
        b.scale_min.set_tooltip_text("Set the maximum allowed scale in any axis")

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        # PAN OPTIONS
        fr = gtk.Frame(label="Panning")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Pan X', 'entry'),
                    ('Pan Y', 'entry', 'Center Image', 'button'),
                    ('Reverse Pan', 'checkbutton', 'Mark Center', 'checkbutton'))
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        pan_x, pan_y = self.fitsimage.get_pan()
        b.pan_x.set_tooltip_text("Set the pan position in X axis")
        b.pan_x.set_text(str(pan_x+0.5))
        b.pan_x.connect("activate", lambda w: self.set_pan_cb())
        b.pan_y.set_tooltip_text("Set the pan position in Y axis")
        b.pan_y.set_text(str(pan_y+0.5))
        b.pan_y.connect("activate", lambda w: self.set_pan_cb())
        b.center_image.set_tooltip_text("Set the pan position to center of the image")
        b.center_image.connect("clicked", lambda w: self.center_image_cb())
        b.reverse_pan.set_tooltip_text("Reverse the pan direction")
        b.reverse_pan.sconnect("toggled", lambda w: self.set_misc_cb())
        b.mark_center.set_tooltip_text("Mark the center (pan locator)")
        b.mark_center.sconnect("toggled", lambda w: self.set_misc_cb())

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        # TRANSFORM OPTIONS
        fr = gtk.Frame(label="Transform")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Flip X', 'checkbutton', 'Flip Y', 'checkbutton', 
                     'Swap XY', 'checkbutton'), ('Rotate', 'spinbutton'),
                    ('Restore', 'button'),)
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        for name in ('flip_x', 'flip_y', 'swap_xy'):
            btn = b[name]
            btn.set_active(self.t_.get(name, False))
            btn.sconnect("toggled", lambda w: self.set_transforms_cb())
            btn.set_mode(True)
        b.flip_x.set_tooltip_text("Flip the image around the X axis")
        b.flip_y.set_tooltip_text("Flip the image around the Y axis")
        b.swap_xy.set_tooltip_text("Swap the X and Y axes in the image")
        b.rotate.set_range(0.00, 359.99999999)
        b.rotate.set_value(self.t_.get('rot_deg', 0.00))
        b.rotate.set_increments(10.0, 30.0)
        b.rotate.set_digits(5)
        b.rotate.set_numeric(True)
        b.rotate.set_wrap(True)
        b.rotate.sconnect('value-changed', lambda w: self.rotate_cb())
        b.rotate.set_tooltip_text("Rotate image around the pan position")
        b.restore.set_tooltip_text("Clear any transforms and center image")
        b.restore.connect("clicked", lambda w: self.restore_cb())

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)
        
        # AUTOCUTS OPTIONS
        fr = gtk.Frame(label="Auto Cuts")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Auto Method', 'combobox'),
                    )
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        # Setup auto cuts method choice
        combobox = b.auto_method
        index = 0
        method = self.t_.get('autocut_method', "histogram")
        for name in self.autocut_methods:
            combobox.insert_text(index, name)
            index += 1
        index = self.autocut_methods.index(method)
        combobox.set_active(index)
        combobox.sconnect('changed', lambda w: self.set_autocut_method_cb())
        b.auto_method.set_tooltip_text("Choose algorithm for auto levels")

        self.w.acvbox = gtk.VBox()
        w.pack_end(self.w.acvbox, fill=True, expand=True)

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        # WCS OPTIONS
        fr = gtk.Frame(label="WCS")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('WCS Coords', 'combobox', 'WCS Display', 'combobox'),
                    )
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        b.wcs_coords.set_tooltip_text("Set WCS coordinate system")
        b.wcs_display.set_tooltip_text("Set WCS display format")

        # Setup WCS coords method choice
        combobox = b.wcs_coords
        index = 0
        for name in wcs.coord_types:
            combobox.insert_text(index, name)
            index += 1
        method = self.t_.get('wcs_coords', "")
        try:
            index = wcs.coord_types.index(method)
            combobox.set_active(index)
        except ValueError:
            pass
        combobox.sconnect('changed', lambda w: self.set_wcs_params_cb())

        # Setup WCS display format method choice
        combobox = b.wcs_display
        index = 0
        for name in wcs.display_types:
            combobox.insert_text(index, name)
            index += 1
        method = self.t_.get('wcs_display', "sexagesimal")
        try:
            index = wcs.display_types.index(method)
            combobox.set_active(index)
        except ValueError:
            pass
        combobox.sconnect('changed', lambda w: self.set_wcs_params_cb())

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        # NEW IMAGES OPTIONS
        fr = gtk.Frame(label="New Images")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = (('Cut New', 'combobox', 'Zoom New', 'combobox'),
                    ('Center New', 'checkbutton', 'Follow New', 'checkbutton'),
                    ('Raise New', 'checkbutton', 'Create thumbnail', 'checkbutton'),)
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)

        combobox = b.cut_new
        index = 0
        for name in self.autocut_options:
            combobox.insert_text(index, name)
            index += 1
        option = self.t_.get('autocuts', "off")
        index = self.autocut_options.index(option)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_autocuts_cb)

        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.insert_text(index, name)
            index += 1
        option = self.t_.get('autozoom', "off")
        index = self.autozoom_options.index(option)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_autozoom_cb)

        b.zoom_new.set_tooltip_text("Automatically fit new images to window")
        b.cut_new.set_tooltip_text("Automatically set cut levels for new images")
        b.center_new.set_tooltip_text("Automatically center new images")
        b.follow_new.set_tooltip_text("View new images as they arrive")
        b.raise_new.set_tooltip_text("Raise and focus tab for new images")
        b.create_thumbnail.set_tooltip_text("Create thumbnail for new images")

        self.w.center_new.set_active(True)
        self.w.center_new.sconnect("toggled", lambda w: self.set_chprefs_cb())
        self.w.follow_new.set_active(True)
        self.w.follow_new.sconnect("toggled", lambda w: self.set_chprefs_cb())
        self.w.raise_new.set_active(True)
        self.w.raise_new.sconnect("toggled", lambda w: self.set_chprefs_cb())
        self.w.create_thumbnail.set_active(True)
        self.w.create_thumbnail.sconnect("toggled",
                                              lambda w: self.set_chprefs_cb())

        fr.add(w)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)

        btn = gtk.Button("Save Settings")
        btn.connect('clicked', lambda w: self.save_preferences())
        btns.add(btn)
        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        vbox.pack_start(btns, padding=4, fill=True, expand=False)

        vbox.show_all()

        container.pack_start(sw, padding=0, fill=True, expand=True)

        self.gui_up = True

    def set_cmap_cb(self, w):
        """This callback is invoked when the user selects a new color
        map from the preferences pane."""
        index = w.get_active()
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
        
    def set_imap_cb(self, w):
        """This callback is invoked when the user selects a new intensity
        map from the preferences pane."""
        index = w.get_active()
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

    def set_calg_cb(self, w):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the preferences pane."""
        index = w.get_active()
        name = self.calg_names[index]
        self.set_calg_byname(name)

    def set_tablesize_cb(self, w):
        value = int(w.get_text())
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
        self.w.cmap_choice.set_active(index)
        index = self.imap_names.index(imap_name)
        self.w.imap_choice.set_active(index)
        self.set_cmap_byname(cmap_name)
        self.t_.set(color_map=cmap_name)
        self.set_imap_byname(imap_name)
        self.t_.set(intensity_map=imap_name)
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.set_active(index)
        self.set_calg_byname(name)
        self.t_.set(color_algorithm=name)
        hashsize = 65535
        self.t_.set(color_hashsize=hashsize)
        self.w.table_size.set_text(str(hashsize))
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(hashsize)
        
    def set_zoomrate_cb(self, w):
        rate = float(w.get_value())
        self.t_.set(zoom_rate=rate)
        
    def set_zoomrate_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        self.w.zoom_rate.set_value(value)
        
    def set_zoomalg_cb(self):
        idx = self.w.zoom_alg.get_active()
        self.t_.set(zoom_algorithm=self.zoomalg_names[idx])
        
    def set_zoomalg_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        if value == 'step':
            self.w.zoom_alg.set_active(0)
            self.w.zoom_rate.set_sensitive(False)
            self.w.stretch_factor.set_sensitive(False)
        else:
            self.w.zoom_alg.set_active(1)
            self.w.zoom_rate.set_sensitive(True)
            self.w.stretch_factor.set_sensitive(True)

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
            idx = self.w.stretch_xy.get_active()

        # Update stretch controls to reflect actual scale
        self.w.stretch_xy.set_active(idx)
        self.w.stretch_factor.set_value(ratio)
        
    def set_zoom_defaults_cb(self, w):
        rate = math.sqrt(2.0)
        self.w.stretch_factor.set_value(1.0)
        self.t_.set(zoom_algorithm='step', zoom_rate=rate,
                    scale_x_base=1.0, scale_y_base=1.0)
        
    def set_stretch_cb(self):
        axis = self.w.stretch_xy.get_active()
        value = self.w.stretch_factor.get_value()
        if axis == 0:
            self.t_.set(scale_x_base=value, scale_y_base=1.0)
        else:
            self.t_.set(scale_x_base=1.0, scale_y_base=value)
        
    def pan_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        pan_x, pan_y = value
        fits_x, fits_y = pan_x + 0.5, pan_y + 0.5
        self.w.pan_x.set_text(str(fits_x))
        self.w.pan_y.set_text(str(fits_y))
        
    def set_scale_cb(self):
        scale_x = float(self.w.scale_x.get_text())
        scale_y = float(self.w.scale_y.get_text())
        self.fitsimage.scale_to(scale_x, scale_y)

    def scale_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        scale_x, scale_y = value
        self.w.scale_x.set_text(str(scale_x))
        self.w.scale_y.set_text(str(scale_y))

    def set_scale_limit_cb(self):
        scale_min = self.w.scale_min.get_value()
        scale_max = self.w.scale_max.get_value()
        self.t_.set(scale_min=scale_min, scale_max=scale_max)

    def set_autozoom_cb(self, w):
        idx = w.get_active()
        option = self.autozoom_options[idx]
        self.fitsimage.enable_autozoom(option)
        self.t_.set(autozoom=option)

    def autozoom_changed_ext_cb(self, setting, option):
        if not self.gui_up:
            return
        index = self.autozoom_options.index(option)
        self.w.zoom_new.set_active(index)

    def config_autocut_params(self, method):
        index = self.autocut_methods.index(method)
        self.w.auto_method.set_active(index)

        # remove old params
        for child in self.w.acvbox.get_children():
            self.w.acvbox.remove(child)

        # Create new autocuts object of the right kind
        ac = AutoCuts.get_autocuts(method)(self.logger)

        # Build up a set of control widgets for the autocuts
        # algorithm tweakable parameters
        paramlst = ac.get_params_metadata()

        params = self.autocuts_cache.setdefault(method, {})
        self.ac_params = GtkHelp.ParamSet(self.logger, params)

        w = self.ac_params.build_params(paramlst)
        self.ac_params.add_callback('changed', self.autocut_params_changed_cb)

        self.w.acvbox.pack_start(w, fill=True, expand=True)
        w.show()

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
        idx = self.w.auto_method.get_active()
        method = self.autocut_methods[idx]
        self.config_autocut_params(method)

        params = self.ac_params.get_params()
        params = list(params.items())
        self.t_.set(autocut_method=method, autocut_params=params)
        
    def autocut_params_changed_cb(self, paramObj, params):
        params = list(params.items())
        self.t_.set(autocut_params=params)
        
    def set_autocuts_cb(self, w):
        idx = w.get_active()
        option = self.autocut_options[idx]
        self.fitsimage.enable_autocuts(option)
        self.t_.set(autocuts=option)

    def autocuts_changed_ext_cb(self, setting, option):
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        if self.gui_up:
            self.w.cut_new.set_active(index)

    def set_transforms_cb(self):
        flip_x = self.w.flip_x.get_active()
        flip_y = self.w.flip_y.get_active()
        swap_xy = self.w.swap_xy.get_active()
        self.t_.set(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)
        return True

    def set_transform_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        flip_x, flip_y, swap_xy = \
                self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy']
        self.w.flip_x.set_active(flip_x)
        self.w.flip_y.set_active(flip_y)
        self.w.swap_xy.set_active(swap_xy)
        
    def rotate_cb(self):
        deg = self.w.rotate.get_value()
        self.t_.set(rot_deg=deg)
        return True

    def set_rotate_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        self.w.rotate.set_value(value)
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
        self.t_.set(flip_x=False, flip_y=False, swap_xy=False,
                    rot_deg=0.0)
        self.fitsimage.center_image()
        return True

    def set_misc_cb(self):
        revpan = self.w.reverse_pan.get_active()
        self.t_.set(reverse_pan=revpan)
        self.fitsimage.set_pan_reverse(revpan)

        markc = self.w.mark_center.get_active()
        self.t_.set(show_pan_position=markc)
        self.fitsimage.show_pan_mark(markc)
        return True

    def set_chprefs_cb(self):
        autocenter = self.w.center_new.get_active()
        switchnew = self.w.follow_new.get_active()
        raisenew = self.w.raise_new.get_active()
        genthumb = self.w.create_thumbnail.get_active()
        self.t_.set(switchnew=switchnew, raisenew=raisenew,
                    autocenter=autocenter, genthumb=genthumb)

    def set_wcs_params_cb(self):
        idx = self.w.wcs_coords.get_active()
        try:
            ctype = wcs.coord_types[idx]
        except IndexError:
            ctype = 'icrs'
        idx = self.w.wcs_display.get_active()
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
        self.w.cmap_choice.set_active(index)

        calg = rgbmap.get_hash_algorithm()
        index = self.calg_names.index(calg)
        self.w.calg_choice.set_active(index)

        size = rgbmap.get_hash_size()
        self.w.table_size.set_text(str(size))

        im = rgbmap.get_imap()
        try:
            index = self.imap_names.index(im.name)
        except ValueError:
            # may be a custom intensity map installed
            index = 0
        self.w.imap_choice.set_active(index)

        # zoom settings
        zoomalg = prefs.get('zoom_algorithm', "step")            
        index = self.zoomalg_names.index(zoomalg)
        self.w.zoom_alg.set_active(index)

        zoomrate = self.t_.get('zoom_rate', math.sqrt(2.0))
        self.w.zoom_rate.set_value(zoomrate)
        self.w.zoom_rate.set_sensitive(zoomalg!='step')
        self.w.stretch_factor.set_sensitive(zoomalg!='step')

        self.scalebase_changed_ext_cb(prefs, None)
        
        scale_x, scale_y = self.fitsimage.get_scale_xy()
        self.w.scale_x.set_text(str(scale_x))
        self.w.scale_y.set_text(str(scale_y))

        scale_min = prefs.get('scale_min', 0.00001)
        self.w.scale_min.set_value(scale_min)
        scale_max = prefs.get('scale_max', 10000.0)
        self.w.scale_max.set_value(scale_max)

        # panning settings
        pan_x, pan_y = self.fitsimage.get_pan()
        self.w.pan_x.set_text(str(pan_x+0.5))
        self.w.pan_y.set_text(str(pan_y+0.5))

        self.w.reverse_pan.set_active(prefs.get('reverse_pan', False))
        self.w.mark_center.set_active(prefs.get('show_pan_position', False))

        # transform settings
        self.w.flip_x.set_active(prefs.get('flip_x', False))
        self.w.flip_y.set_active(prefs.get('flip_y', False))
        self.w.swap_xy.set_active(prefs.get('swap_xy', False))
        self.w.rotate.set_value(prefs.get('rot_deg', 0.00))

        # auto cuts settings
        autocuts = prefs.get('autocuts', 'off')
        index = self.autocut_options.index(autocuts)
        self.w.cut_new.set_active(index)

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
        self.w.zoom_new.set_active(index)

        # wcs settings
        method = prefs.get('wcs_coords', "icrs")
        try:
            index = wcs.coord_types.index(method)
            self.w.wcs_coords.set_active(index)
        except ValueError:
            pass

        method = prefs.get('wcs_display', "sexagesimal")
        try:
            index = wcs.display_types.index(method)
            self.w.wcs_display.set_active(index)
        except ValueError:
            pass

        # misc settings
        prefs.setdefault('autocenter', False)
        self.w.center_new.set_active(prefs['autocenter'])
        prefs.setdefault('switchnew', True)
        self.w.follow_new.set_active(prefs['switchnew'])
        prefs.setdefault('raisenew', True)
        self.w.raise_new.set_active(prefs['raisenew'])
        prefs.setdefault('genthumb', True)
        self.w.create_thumbnail.set_active(prefs['genthumb'])

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
