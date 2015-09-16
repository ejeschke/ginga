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
from ginga.gw import Widgets
from ginga.misc import ParamSet, Bunch

from ginga import cmap, imap, trcalc
from ginga import GingaPlugin
from ginga import AutoCuts, ColorDist
from ginga.util import wcs, wcsmod, io_rgb

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

        self.calg_names = ColorDist.get_dist_names()
        self.autozoom_options = self.fitsimage.get_autozoom_options()
        self.autocut_options = self.fitsimage.get_autocuts_options()
        self.autocut_methods = self.fitsimage.get_autocut_methods()
        self.autocenter_options = self.fitsimage.get_autocenter_options()
        self.pancoord_options = ('data', 'wcs')

        self.t_ = self.fitsimage.get_settings()
        self.t_.getSetting('autocuts').add_callback('set',
                                               self.autocuts_changed_ext_cb)
        self.t_.getSetting('autozoom').add_callback('set',
                                               self.autozoom_changed_ext_cb)
        self.t_.getSetting('autocenter').add_callback('set',
                                                      self.autocenter_changed_ext_cb)
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

        ## for name in ('autocut_method', 'autocut_params'):
        ##     self.t_.getSetting(name).add_callback('set', self.set_autocuts_ext_cb)

        ## for key in ['color_algorithm', 'color_hashsize', 'color_map',
        ##             'intensity_map']:
        ##     self.t_.getSetting(key).add_callback('set', self.cmap_changed_ext_cb)

        self.t_.setdefault('wcs_coords', 'icrs')
        self.t_.setdefault('wcs_display', 'sexagesimal')

        # buffer len (number of images in memory)
        self.t_.addDefaults(numImages=4)
        self.t_.getSetting('numImages').add_callback('set', self.set_buflen_ext_cb)

        self.icc_profiles = list(io_rgb.get_profiles())
        self.icc_profiles.insert(0, None)
        self.icc_intents = io_rgb.get_intents()

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        self.orientation = orientation
        #vbox.set_border_width(4)
        vbox.set_spacing(2)

        # COLOR DISTRIBUTION OPTIONS
        fr = Widgets.Frame("Color Distribution")

        captions = (('Algorithm:', 'label', 'Algorithm', 'combobox'),
                    #('Table Size:', 'label', 'Table Size', 'entryset'),
                    ('Dist Defaults', 'button'))

        w, b = Widgets.build_info(captions, orientation=orientation)
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
        index = self.calg_names.index(self.t_.get('color_algorithm', "linear"))
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_calg_cb)

        ## entry = b.table_size
        ## entry.set_text(str(self.t_.get('color_hashsize', 65535)))
        ## entry.add_callback('activated', self.set_tablesize_cb)

        fr.set_widget(w)
        vbox.add_widget(fr)

        # COLOR MAPPING OPTIONS
        fr = Widgets.Frame("Color Mapping")

        captions = (('Colormap:', 'label', 'Colormap', 'combobox'),
                    ('Intensity:', 'label', 'Intensity', 'combobox'),
                    ('Color Defaults', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        self.w.cmap_choice = b.colormap
        self.w.imap_choice = b.intensity
        b.color_defaults.add_callback('activated',
                                      lambda w: self.set_default_cmaps())
        b.colormap.set_tooltip("Choose a color map for this image")
        b.intensity.set_tooltip("Choose an intensity map for this image")
        b.color_defaults.set_tooltip("Restore default color and intensity maps")
        fr.set_widget(w)
        vbox.add_widget(fr)

        combobox = b.colormap
        options = []
        index = 0
        for name in self.cmap_names:
            options.append(name)
            combobox.append_text(name)
            index += 1
        cmap_name = self.t_.get('color_map', "gray")
        try:
            index = self.cmap_names.index(cmap_name)
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
        imap_name = self.t_.get('intensity_map', "ramp")
        try:
            index = self.imap_names.index(imap_name)
        except Exception:
            index = self.imap_names.index('ramp')
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_imap_cb)

        # AUTOCUTS OPTIONS
        fr = Widgets.Frame("Auto Cuts")
        vbox2 = Widgets.VBox()
        fr.set_widget(vbox2)

        captions = (('Auto Method:', 'label', 'Auto Method', 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        # Setup auto cuts method choice
        combobox = b.auto_method
        index = 0
        method = self.t_.get('autocut_method', "histogram")
        for name in self.autocut_methods:
            combobox.append_text(name)
            index += 1
        index = self.autocut_methods.index(method)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_autocut_method_cb)
        b.auto_method.set_tooltip("Choose algorithm for auto levels")
        vbox2.add_widget(w, stretch=0)

        self.w.acvbox = Widgets.VBox()
        vbox2.add_widget(self.w.acvbox, stretch=1)

        vbox.add_widget(fr, stretch=0)

        # TRANSFORM OPTIONS
        fr = Widgets.Frame("Transform")

        captions = (('Flip X', 'checkbutton', 'Flip Y', 'checkbutton',
                    'Swap XY', 'checkbutton'),
                    ('Rotate:', 'label', 'Rotate', 'spinfloat'),
                    ('Restore', 'button'),)
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        for name in ('flip_x', 'flip_y', 'swap_xy'):
            btn = b[name]
            btn.set_state(self.t_.get(name, False))
            btn.add_callback('activated', self.set_transforms_cb)
        b.flip_x.set_tooltip("Flip the image around the X axis")
        b.flip_y.set_tooltip("Flip the image around the Y axis")
        b.swap_xy.set_tooltip("Swap the X and Y axes in the image")
        b.rotate.set_tooltip("Rotate the image around the pan position")
        b.restore.set_tooltip("Clear any transforms and center image")
        b.restore.add_callback('activated', self.restore_cb)

        b.rotate.set_limits(0.00, 359.99999999, incr_value=10.0)
        b.rotate.set_value(0.00)
        b.rotate.set_decimals(8)
        b.rotate.add_callback('value-changed', self.rotate_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        # WCS OPTIONS
        fr = Widgets.Frame("WCS")

        captions = (('WCS Coords:', 'label', 'WCS Coords', 'combobox'),
                    ('WCS Display:', 'label', 'WCS Display', 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.wcs_coords.set_tooltip("Set WCS coordinate system")
        b.wcs_display.set_tooltip("Set WCS display format")

        # Setup WCS coords method choice
        combobox = b.wcs_coords
        index = 0
        for name in wcsmod.coord_types:
            combobox.append_text(name)
            index += 1
        method = self.t_.get('wcs_coords', "")
        try:
            index = wcsmod.coord_types.index(method)
            combobox.set_index(index)
        except ValueError:
            pass
        combobox.add_callback('activated', self.set_wcs_params_cb)

        # Setup WCS display format method choice
        combobox = b.wcs_display
        index = 0
        for name in wcsmod.display_types:
            combobox.append_text(name)
            index += 1
        method = self.t_.get('wcs_display', "sexagesimal")
        try:
            index = wcsmod.display_types.index(method)
            combobox.set_index(index)
        except ValueError:
            pass
        combobox.add_callback('activated', self.set_wcs_params_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        # ZOOM OPTIONS
        fr = Widgets.Frame("Zoom")

        captions = (('Zoom Alg:', 'label', 'Zoom Alg', 'combobox'),
                    ('Zoom Rate:', 'label', 'Zoom Rate', 'spinfloat'),
                    ('Stretch XY:', 'label', 'Stretch XY', 'combobox'),
                    ('Stretch Factor:', 'label', 'Stretch Factor', 'spinfloat'),
                    ('Scale X:', 'label', 'Scale X', 'entryset'),
                    ('Scale Y:', 'label', 'Scale Y', 'entryset'),
                    ('Scale Min:', 'label', 'Scale Min', 'spinfloat'),
                    ('Scale Max:', 'label', 'Scale Max', 'spinfloat'),
                    ('Interpolation:', 'label', 'Interpolation', 'combobox'),
                    ('Zoom Defaults', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        index = 0
        for name in self.zoomalg_names:
            b.zoom_alg.append_text(name.capitalize())
            index += 1
        zoomalg = self.t_.get('zoom_algorithm', "step")
        index = self.zoomalg_names.index(zoomalg)
        b.zoom_alg.set_index(index)
        b.zoom_alg.set_tooltip("Choose Zoom algorithm")
        b.zoom_alg.add_callback('activated', self.set_zoomalg_cb)

        index = 0
        for name in ('X', 'Y'):
            b.stretch_xy.append_text(name)
            index += 1
        b.stretch_xy.set_index(0)
        b.stretch_xy.set_tooltip("Stretch pixels in X or Y")
        b.stretch_xy.add_callback('activated', self.set_stretch_cb)

        b.stretch_factor.set_limits(1.0, 10.0, incr_value=0.10)
        b.stretch_factor.set_value(1.0)
        b.stretch_factor.set_decimals(8)
        b.stretch_factor.add_callback('value-changed', self.set_stretch_cb)
        b.stretch_factor.set_tooltip("Length of pixel relative to 1 on other side")
        b.stretch_factor.set_enabled(zoomalg != 'step')

        zoomrate = self.t_.get('zoom_rate', math.sqrt(2.0))
        b.zoom_rate.set_limits(1.1, 3.0, incr_value=0.1)
        b.zoom_rate.set_value(zoomrate)
        b.zoom_rate.set_decimals(8)
        b.zoom_rate.set_enabled(zoomalg != 'step')
        b.zoom_rate.set_tooltip("Step rate of increase/decrease per zoom level")
        b.zoom_rate.add_callback('value-changed', self.set_zoomrate_cb)

        b.zoom_defaults.add_callback('activated', self.set_zoom_defaults_cb)

        scale_x, scale_y = self.fitsimage.get_scale_xy()
        b.scale_x.set_tooltip("Set the scale in X axis")
        b.scale_x.set_text(str(scale_x))
        b.scale_x.add_callback('activated', self.set_scale_cb)
        b.scale_y.set_tooltip("Set the scale in Y axis")
        b.scale_y.set_text(str(scale_y))
        b.scale_y.add_callback('activated', self.set_scale_cb)

        scale_min, scale_max = self.t_['scale_min'], self.t_['scale_max']
        b.scale_min.set_limits(0.00001, 1.0, incr_value=1.0)
        b.scale_min.set_value(scale_min)
        b.scale_min.set_decimals(8)
        b.scale_min.add_callback('value-changed', self.set_scale_limit_cb)
        b.scale_min.set_tooltip("Set the minimum allowed scale in any axis")

        b.scale_max.set_limits(1.0, 10000.0, incr_value=1.0)
        b.scale_max.set_value(scale_max)
        b.scale_max.set_decimals(8)
        b.scale_max.add_callback('value-changed', self.set_scale_limit_cb)
        b.scale_min.set_tooltip("Set the maximum allowed scale in any axis")

        index = 0
        for name in trcalc.interpolation_methods:
            b.interpolation.append_text(name)
            index += 1
        interp = self.t_.get('interpolation', "basic")
        index = trcalc.interpolation_methods.index(interp)
        b.interpolation.set_index(index)
        b.interpolation.set_tooltip("Choose interpolation method")
        b.interpolation.add_callback('activated', self.set_interp_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        # PAN OPTIONS
        fr = Widgets.Frame("Panning")

        captions = (('Pan X:', 'label', 'Pan X', 'entry',
                     'WCS sexagesimal', 'checkbutton'),
                    ('Pan Y:', 'label', 'Pan Y', 'entry',
                     'Apply Pan', 'button'),
                    ('Pan Coord:', 'label', 'Pan Coord', 'combobox'),
                    ('Center Image', 'button', 'Mark Center', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        pan_x, pan_y = self.fitsimage.get_pan()
        coord_offset = self.fv.settings.get('pixel_coords_offset', 0.0)
        b.pan_x.set_tooltip("Coordinate for the pan position in X axis")
        b.pan_x.set_text(str(pan_x + coord_offset))
        #b.pan_x.add_callback('activated', self.set_pan_cb)
        b.pan_y.set_tooltip("Coordinate for the pan position in Y axis")
        b.pan_y.set_text(str(pan_y + coord_offset))
        #b.pan_y.add_callback('activated', self.set_pan_cb)
        b.apply_pan.add_callback('activated', self.set_pan_cb)
        b.apply_pan.set_tooltip("Set the pan position")
        b.wcs_sexagesimal.set_tooltip("Display pan position in sexagesimal")

        index = 0
        for name in self.pancoord_options:
            b.pan_coord.append_text(name)
            index += 1
        pan_coord = self.t_.get('pan_coord', "data")
        index = self.pancoord_options.index(pan_coord)
        b.pan_coord.set_index(index)
        b.pan_coord.set_tooltip("Pan coordinates type")
        b.pan_coord.add_callback('activated', self.set_pan_coord_cb)

        b.center_image.set_tooltip("Set the pan position to center of the image")
        b.center_image.add_callback('activated', self.center_image_cb)
        b.mark_center.set_tooltip("Mark the center (pan locator)")
        b.mark_center.add_callback('activated', self.set_misc_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("New Images")

        captions = (('Cut New:', 'label', 'Cut New', 'combobox'),
                    ('Zoom New:', 'label', 'Zoom New', 'combobox'),
                    ('Center New:', 'label', 'Center New', 'combobox'),
                    ('Follow New', 'checkbutton', 'Raise New', 'checkbutton'),
                    ('Create thumbnail', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        combobox = b.cut_new
        index = 0
        for name in self.autocut_options:
            combobox.append_text(name)
            index += 1
        option = self.t_.get('autocuts', "off")
        index = self.autocut_options.index(option)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_autocuts_cb)
        b.cut_new.set_tooltip("Automatically set cut levels for new images")

        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.append_text(name)
            index += 1
        option = self.t_.get('autozoom', "off")
        index = self.autozoom_options.index(option)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_autozoom_cb)
        b.zoom_new.set_tooltip("Automatically fit new images to window")

        combobox = b.center_new
        index = 0
        for name in self.autocenter_options:
            combobox.append_text(name)
            index += 1
        option = self.t_.get('autocenter', "off")
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = { True: 'on', False: 'off' }
            option = choice[option]
        index = self.autocenter_options.index(option)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_autocenter_cb)
        b.center_new.set_tooltip("Automatically center new images in window")

        b.follow_new.set_tooltip("View new images as they arrive")
        b.raise_new.set_tooltip("Raise and focus tab for new images")
        b.create_thumbnail.set_tooltip("Create thumbnail for new images")

        self.w.follow_new.set_state(True)
        self.w.follow_new.add_callback('activated', self.set_chprefs_cb)
        self.w.raise_new.set_state(True)
        self.w.raise_new.add_callback('activated', self.set_chprefs_cb)
        self.w.create_thumbnail.set_state(True)
        self.w.create_thumbnail.add_callback('activated', self.set_chprefs_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        exp = Widgets.Expander("General")

        captions = (('Num Images:', 'label', 'Num Images', 'entryset'),
                    ('Output ICC profile:', 'label', 'Output ICC profile', 'combobox'),
                    ('Rendering intent:', 'label', 'Rendering intent', 'combobox'),
                    ('Proof ICC profile:', 'label', 'Proof ICC profile', 'combobox'),
                    ('Proof intent:', 'label', 'Proof intent', 'combobox'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.num_images.set_tooltip("Maximum number of in memory images in channel (0==unlimited)")
        num_images = self.t_.get('numImages', 0)
        self.w.num_images.set_text(str(num_images))
        self.w.num_images.add_callback('activated', self.set_buffer_cb)

        option = self.t_.get('output_icc', None)
        if option is None:
            (profile_name, intent_name, proof_name,
             proof_intent) = (None, 'perceptual', None, 'perceptual')
        else:
            (profile_name, intent_name, proof_name,
             proof_intent) = option

        combobox = b.output_icc_profile
        index = 0
        for name in self.icc_profiles:
            combobox.append_text(str(name))
            index += 1
        index = self.icc_profiles.index(profile_name)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)

        combobox = b.rendering_intent
        index = 0
        for name in self.icc_intents:
            combobox.append_text(name)
            index += 1
        index = self.icc_intents.index(intent_name)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)

        combobox = b.proof_icc_profile
        index = 0
        for name in self.icc_profiles:
            combobox.append_text(str(name))
            index += 1
        index = self.icc_profiles.index(proof_name)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)

        combobox = b.proof_intent
        index = 0
        for name in self.icc_intents:
            combobox.append_text(name)
            index += 1
        index = self.icc_intents.index(proof_intent)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)

        fr = Widgets.Frame()
        fr.set_widget(w)
        exp.set_widget(fr)
        vbox.add_widget(exp, stretch=0)

        exp = Widgets.Expander("Remember")

        captions = (('Save Scale', 'checkbutton',
                     'Save Pan', 'checkbutton'),
                    ('Save Transform', 'checkbutton',
                    'Save Rotation', 'checkbutton'),
                    ('Save Cuts', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        self.w.save_scale.set_state(self.t_.get('profile_use_scale', False))
        self.w.save_scale.add_callback('activated', self.set_profile_cb)
        self.w.save_scale.set_tooltip("Remember scale with image")
        self.w.save_pan.set_state(self.t_.get('profile_use_pan', False))
        self.w.save_pan.add_callback('activated', self.set_profile_cb)
        self.w.save_pan.set_tooltip("Remember pan position with image")
        self.w.save_transform.set_state(self.t_.get('profile_use_transform', False))
        self.w.save_transform.add_callback('activated', self.set_profile_cb)
        self.w.save_transform.set_tooltip("Remember transform with image")
        self.w.save_rotation.set_state(self.t_.get('profile_use_rotation', False))
        self.w.save_rotation.add_callback('activated', self.set_profile_cb)
        self.w.save_rotation.set_tooltip("Remember rotation with image")
        self.w.save_cuts.set_state(self.t_.get('profile_use_cuts', False))
        self.w.save_cuts.add_callback('activated', self.set_profile_cb)
        self.w.save_cuts.set_tooltip("Remember cut levels with image")

        fr = Widgets.Frame()
        fr.set_widget(w)
        exp.set_widget(fr)
        vbox.add_widget(exp, stretch=0)

        exp = Widgets.Expander("ICC Profiles")

        captions = (('Output ICC profile:', 'label', 'Output ICC profile', 'combobox'),
                    ('Rendering intent:', 'label', 'Rendering intent', 'combobox'),
                    ('Proof ICC profile:', 'label', 'Proof ICC profile', 'combobox'),
                    ('Proof intent:', 'label', 'Proof intent', 'combobox'),
                    ('__x', 'spacer', 'Black point compensation', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        value = self.t_.get('icc_output_profile', None)
        combobox = b.output_icc_profile
        index = 0
        for name in self.icc_profiles:
            combobox.append_text(str(name))
            index += 1
        index = self.icc_profiles.index(value)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for the viewer display")

        value = self.t_.get('icc_output_intent', 'perceptual')
        combobox = b.rendering_intent
        index = 0
        for name in self.icc_intents:
            combobox.append_text(name)
            index += 1
        index = self.icc_intents.index(value)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for the viewer display")

        value = self.t_.get('icc_proof_profile', None)
        combobox = b.proof_icc_profile
        index = 0
        for name in self.icc_profiles:
            combobox.append_text(str(name))
            index += 1
        index = self.icc_profiles.index(value)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for soft proofing")

        value = self.t_.get('icc_proof_intent', None)
        combobox = b.proof_intent
        index = 0
        for name in self.icc_intents:
            combobox.append_text(name)
            index += 1
        index = self.icc_intents.index(value)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for soft proofing")

        value = self.t_.get('icc_black_point_compensation', False)
        b.black_point_compensation.set_state(value)
        b.black_point_compensation.add_callback('activated', self.set_icc_profile_cb)
        b.black_point_compensation.set_tooltip("Use black point compensation")

        fr = Widgets.Frame()
        fr.set_widget(w)
        exp.set_widget(fr)
        vbox.add_widget(exp, stretch=0)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Save Settings")
        btn.add_callback('activated', lambda w: self.save_preferences())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.gui_up = True

    def set_cmap_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        map from the preferences pane."""
        name = cmap.get_names()[index]
        self.set_cmap_byname(name)
        self.t_.set(color_map=name)

    def set_cmap_byname(self, name):
        # Get colormap
        try:
            cm = cmap.get_cmap(name)
        except KeyError:
            raise ValueError("No such color map name: '%s'" % (name))

        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_cmap(cm)

    def set_imap_cb(self, w, index):
        """This callback is invoked when the user selects a new intensity
        map from the preferences pane."""
        name = imap.get_names()[index]
        self.set_imap_byname(name)
        self.t_.set(intensity_map=name)

    def set_imap_byname(self, name):
        # Get intensity map
        try:
            im = imap.get_imap(name)
        except KeyError:
            raise ValueError("No such intensity map name: '%s'" % (name))

        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_imap(im)

    def set_calg_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the preferences pane."""
        #index = w.get_index()
        name = self.calg_names[index]
        self.set_calg_byname(name)

    def set_tablesize_cb(self, w):
        value = int(w.get_text())
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(value)
        self.t_.set(color_hashsize=value)

    def set_calg_byname(self, name):
        # Get color mapping algorithm
        rgbmap = self.fitsimage.get_rgbmap()
        try:
            rgbmap.set_hash_algorithm(name)
        except KeyError:
            raise ValueError("No such color algorithm name: '%s'" % (name))

        # Doesn't this force a redraw?  Following redraw should be unecessary.
        self.t_.set(color_algorithm=name)
        self.fitsimage.redraw(whence=2)

    def set_default_cmaps(self):
        cmap_name = "gray"
        imap_name = "ramp"
        index = self.cmap_names.index(cmap_name)
        self.w.cmap_choice.set_index(index)
        index = self.imap_names.index(imap_name)
        self.w.imap_choice.set_index(index)
        self.set_cmap_byname(cmap_name)
        self.t_.set(color_map=cmap_name)
        self.set_imap_byname(imap_name)
        self.t_.set(intensity_map=imap_name)

    def set_default_distmaps(self):
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.set_index(index)
        self.set_calg_byname(name)
        self.t_.set(color_algorithm=name)
        hashsize = 65535
        self.t_.set(color_hashsize=hashsize)
        ## self.w.table_size.set_text(str(hashsize))
        rgbmap = self.fitsimage.get_rgbmap()
        rgbmap.set_hash_size(hashsize)

    def set_zoomrate_cb(self, w, rate):
        self.t_.set(zoom_rate=rate)

    def set_zoomrate_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        self.w.zoom_rate.set_value(value)

    def set_zoomalg_cb(self, w, idx):
        self.t_.set(zoom_algorithm=self.zoomalg_names[idx])

    def set_zoomalg_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        if value == 'step':
            self.w.zoom_alg.set_index(0)
            self.w.zoom_rate.set_enabled(False)
            self.w.stretch_factor.set_enabled(False)
        else:
            self.w.zoom_alg.set_index(1)
            self.w.zoom_rate.set_enabled(True)
            self.w.stretch_factor.set_enabled(True)

    def set_interp_cb(self, w, idx):
        self.t_.set(interpolation=trcalc.interpolation_methods[idx])

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
            idx = self.w.stretch_xy.get_index()

        # Update stretch controls to reflect actual scale
        self.w.stretch_xy.set_index(idx)
        self.w.stretch_factor.set_value(ratio)

    def set_zoom_defaults_cb(self, w):
        rate = math.sqrt(2.0)
        self.w.stretch_factor.set_value(1.0)
        self.t_.set(zoom_algorithm='step', zoom_rate=rate,
                    scale_x_base=1.0, scale_y_base=1.0)

    def set_stretch_cb(self, *args):
        axis = self.w.stretch_xy.get_index()
        value = self.w.stretch_factor.get_value()
        if axis == 0:
            self.t_.set(scale_x_base=value, scale_y_base=1.0)
        else:
            self.t_.set(scale_x_base=1.0, scale_y_base=value)

    def set_autocenter_cb(self, w, idx):
        option = self.autocenter_options[idx]
        self.fitsimage.set_autocenter(option)
        self.t_.set(autocenter=option)

    def autocenter_changed_ext_cb(self, setting, option):
        if not self.gui_up:
            return
        index = self.autocenter_options.index(option)
        self.w.center_new.set_index(index)

    def set_scale_cb(self, w):
        scale_x = float(self.w.scale_x.get_text())
        scale_y = float(self.w.scale_y.get_text())
        self.fitsimage.scale_to(scale_x, scale_y)

    def scale_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        scale_x, scale_y = value
        self.w.scale_x.set_text(str(scale_x))
        self.w.scale_y.set_text(str(scale_y))

    def set_scale_limit_cb(self, w, val):
        scale_min = float(self.w.scale_min.get_value())
        scale_max = float(self.w.scale_max.get_value())
        self.t_.set(scale_min=scale_min, scale_max=scale_max)

    def set_autozoom_cb(self, w, idx):
        option = self.autozoom_options[idx]
        self.fitsimage.enable_autozoom(option)
        self.t_.set(autozoom=option)

    def autozoom_changed_ext_cb(self, setting, option):
        if not self.gui_up:
            return
        index = self.autozoom_options.index(option)
        self.w.zoom_new.set_index(index)

    def config_autocut_params(self, method):
        index = self.autocut_methods.index(method)
        self.w.auto_method.set_index(index)

        # remove old params
        self.w.acvbox.remove_all()

        # Create new autocuts object of the right kind
        ac_class = AutoCuts.get_autocuts(method)

        # Build up a set of control widgets for the autocuts
        # algorithm tweakable parameters
        paramlst = ac_class.get_params_metadata()

        # Get the canonical version of this object stored in our cache
        # and make a ParamSet from it
        params = self.autocuts_cache.setdefault(method, Bunch.Bunch())
        self.ac_params = ParamSet.ParamSet(self.logger, params)

        # Build widgets for the parameter/attribute list
        w = self.ac_params.build_params(paramlst,
                                        orientation=self.orientation)
        self.ac_params.add_callback('changed', self.autocut_params_changed_cb)

        # Add this set of widgets to the pane
        self.w.acvbox.add_widget(w, stretch=1)

    def set_autocuts_ext_cb(self, setting, value):
        if not self.gui_up:
            return

        if setting.name == 'autocut_method':
            # NOTE: use gui_do?
            self.config_autocut_params(value)

        elif setting.name == 'autocut_params':
            # NOTE: use gui_do?
            # TODO: set the params from this tuple
            #params = dict(value)
            #self.ac_params.params.update(params)
            self.ac_params.params_to_widgets()

    def set_autocut_method_cb(self, w, idx):
        #idx = self.w.auto_method.get_index()
        method = self.autocut_methods[idx]

        self.config_autocut_params(method)

        args, kwdargs = self.ac_params.get_params()
        params = list(kwdargs.items())
        self.t_.set(autocut_method=method, autocut_params=params)

    def autocut_params_changed_cb(self, paramObj, ac_obj):
        """This callback is called when the user changes the attributes of
        an object via the paramSet.
        """
        args, kwdargs = paramObj.get_params()
        params = list(kwdargs.items())
        self.t_.set(autocut_params=params)

    def set_autocuts_cb(self, w, index):
        option = self.autocut_options[index]
        self.fitsimage.enable_autocuts(option)
        self.t_.set(autocuts=option)

    def autocuts_changed_ext_cb(self, setting, option):
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        if self.gui_up:
            self.w.cut_new.set_index(index)

    def set_transforms_cb(self, *args):
        flip_x = self.w.flip_x.get_state()
        flip_y = self.w.flip_y.get_state()
        swap_xy = self.w.swap_xy.get_state()
        self.t_.set(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)
        return True

    def set_transform_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        flip_x, flip_y, swap_xy = \
                self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy']
        self.w.flip_x.set_state(flip_x)
        self.w.flip_y.set_state(flip_y)
        self.w.swap_xy.set_state(swap_xy)

    def set_buflen_ext_cb(self, setting, value):
        num_images = self.t_['numImages']

        # update the datasrc length
        chname = self.fv.get_channelName(self.fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chinfo.datasrc.set_bufsize(num_images)
        self.logger.debug("num images was set to {0}".format(num_images))

        if not self.gui_up:
            return
        self.w.num_images.set_text(str(num_images))

    def set_icc_profile_cb(self, setting, idx):
        idx = self.w.output_icc_profile.get_index()
        output_profile_name = self.icc_profiles[idx]
        idx = self.w.rendering_intent.get_index()
        intent_name = self.icc_intents[idx]

        idx = self.w.proof_icc_profile.get_index()
        proof_profile_name = self.icc_profiles[idx]
        idx = self.w.proof_intent.get_index()
        proof_intent = self.icc_intents[idx]

        bpc = self.w.black_point_compensation.get_state()

        self.t_.set(icc_output_profile=output_profile_name,
                    icc_output_intent=intent_name,
                    icc_proof_profile=proof_profile_name,
                    icc_proof_intent=proof_intent,
                    icc_black_point_compensation=bpc)
        return True

    def rotate_cb(self, w, deg):
        #deg = self.w.rotate.get_value()
        self.t_.set(rot_deg=deg)
        return True

    def set_rotate_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        self.w.rotate.set_value(value)
        return True

    def center_image_cb(self, *args):
        self.fitsimage.center_image()
        return True

    def pan_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return
        self._update_pan_coords()

    def set_pan_cb(self, *args):
        idx = self.w.pan_coord.get_index()
        pan_coord = self.pancoord_options[idx]
        pan_xs = self.w.pan_x.get_text().strip()
        pan_ys = self.w.pan_y.get_text().strip()
        # TODO: use current value for other coord if only one coord supplied
        if (':' in pan_xs) or (':' in pan_ys):
            # TODO: get maximal precision
            pan_x = wcs.hmsStrToDeg(pan_xs)
            pan_y = wcs.dmsStrToDeg(pan_ys)
            pan_coord = 'wcs'
        else:
            coord_offset = self.fv.settings.get('pixel_coords_offset', 0.0)
            pan_x = float(pan_xs) - coord_offset
            pan_y = float(pan_ys) - coord_offset

        self.fitsimage.set_pan(pan_x, pan_y, coord=pan_coord)
        return True

    def _update_pan_coords(self):
        pan_coord = self.t_.get('pan_coord', 'data')
        pan_x, pan_y = self.fitsimage.get_pan(coord=pan_coord)
        #self.logger.debug("updating pan coords (%s) %f %f" % (pan_coord, pan_x, pan_y))
        if pan_coord == 'wcs':
            use_sex = self.w.wcs_sexagesimal.get_state()
            if use_sex:
                pan_x = wcs.raDegToString(pan_x, format='%02d:%02d:%010.7f')
                pan_y = wcs.decDegToString(pan_y, format='%s%02d:%02d:%09.7f')
        else:
            coord_offset = self.fv.settings.get('pixel_coords_offset', 0.0)
            pan_x += coord_offset
            pan_y += coord_offset

        self.w.pan_x.set_text(str(pan_x))
        self.w.pan_y.set_text(str(pan_y))

        index = self.pancoord_options.index(pan_coord)
        self.w.pan_coord.set_index(index)

    def set_pan_coord_cb(self, w, idx):
        pan_coord = self.pancoord_options[idx]
        pan_x, pan_y = self.fitsimage.get_pan(coord=pan_coord)
        self.t_.set(pan=(pan_x, pan_y), pan_coord=pan_coord)
        #self._update_pan_coords()
        return True

    def restore_cb(self, *args):
        self.t_.set(flip_x=False, flip_y=False, swap_xy=False,
                    rot_deg=0.0)
        self.fitsimage.center_image()
        return True

    def set_misc_cb(self, *args):
        markc = (self.w.mark_center.get_state() != 0)
        self.t_.set(show_pan_position=markc)
        self.fitsimage.show_pan_mark(markc)
        return True

    def set_chprefs_cb(self, *args):
        switchnew = (self.w.follow_new.get_state() != 0)
        raisenew = (self.w.raise_new.get_state() != 0)
        genthumb = (self.w.create_thumbnail.get_state() != 0)
        self.t_.set(switchnew=switchnew, raisenew=raisenew,
                    genthumb=genthumb)

    def set_profile_cb(self, *args):
        save_scale = (self.w.save_scale.get_state() != 0)
        save_pan = (self.w.save_pan.get_state() != 0)
        save_cuts = (self.w.save_cuts.get_state() != 0)
        save_transform = (self.w.save_transform.get_state() != 0)
        save_rotation = (self.w.save_rotation.get_state() != 0)
        self.t_.set(profile_use_scale=save_scale, profile_use_pan=save_pan,
                    profile_use_cuts=save_cuts,
                    profile_use_transform=save_transform,
                    profile_use_rotation=save_rotation)

    def set_buffer_cb(self, *args):
        num_images = int(self.w.num_images.get_text())
        self.logger.debug("setting num images {0}".format(num_images))
        self.t_.set(numImages=num_images)

    def set_wcs_params_cb(self, *args):
        idx = self.w.wcs_coords.get_index()
        try:
            ctype = wcsmod.coord_types[idx]
        except IndexError:
            ctype = 'icrs'
        idx = self.w.wcs_display.get_index()
        dtype = wcsmod.display_types[idx]
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
        self.w.cmap_choice.set_index(index)

        # color dist algorithm
        calg = rgbmap.get_hash_algorithm()
        index = self.calg_names.index(calg)
        self.w.calg_choice.set_index(index)

        ## size = rgbmap.get_hash_size()
        ## self.w.table_size.set_text(str(size))

        # intensity map
        im = rgbmap.get_imap()
        try:
            index = self.imap_names.index(im.name)
        except ValueError:
            # may be a custom intensity map installed
            index = 0
        self.w.imap_choice.set_index(index)

        # TODO: this is a HACK to get around Qt's callbacks
        # on setting widget values--need a way to disable callbacks
        # for direct setting
        auto_zoom = prefs.get('autozoom', 'off')

        # zoom settings
        zoomalg = prefs.get('zoom_algorithm', "step")
        index = self.zoomalg_names.index(zoomalg)
        self.w.zoom_alg.set_index(index)

        zoomrate = self.t_.get('zoom_rate', math.sqrt(2.0))
        self.w.zoom_rate.set_value(zoomrate)
        self.w.zoom_rate.set_enabled(zoomalg!='step')
        self.w.stretch_factor.set_enabled(zoomalg!='step')

        self.scalebase_changed_ext_cb(prefs, None)

        scale_x, scale_y = self.fitsimage.get_scale_xy()
        self.w.scale_x.set_text(str(scale_x))
        self.w.scale_y.set_text(str(scale_y))

        scale_min = prefs.get('scale_min', 0.00001)
        self.w.scale_min.set_value(scale_min)
        scale_max = prefs.get('scale_max', 10000.0)
        self.w.scale_max.set_value(scale_max)

        # panning settings
        self._update_pan_coords()
        self.w.mark_center.set_state(prefs.get('show_pan_position', False))

        # transform settings
        self.w.flip_x.set_state(prefs.get('flip_x', False))
        self.w.flip_y.set_state(prefs.get('flip_y', False))
        self.w.swap_xy.set_state(prefs.get('swap_xy', False))
        self.w.rotate.set_value(prefs.get('rot_deg', 0.00))

        # auto cuts settings
        autocuts = prefs.get('autocuts', 'off')
        index = self.autocut_options.index(autocuts)
        self.w.cut_new.set_index(index)

        autocut_method = prefs.get('autocut_method', None)
        if autocut_method is None:
            autocut_method = 'histogram'
        else:
            ## params = prefs.get('autocut_params', {})
            ## p = self.autocuts_cache.setdefault(autocut_method, {})
            ## p.update(params)
            pass
        self.config_autocut_params(autocut_method)

        # auto zoom settings
        auto_zoom = prefs.get('autozoom', 'off')
        index = self.autozoom_options.index(auto_zoom)
        self.w.zoom_new.set_index(index)

        # wcs settings
        method = prefs.get('wcs_coords', "icrs")
        try:
            index = wcsmod.coord_types.index(method)
            self.w.wcs_coords.set_index(index)
        except ValueError:
            pass

        method = prefs.get('wcs_display', "sexagesimal")
        try:
            index = wcsmod.display_types.index(method)
            self.w.wcs_display.set_index(index)
        except ValueError:
            pass

        # misc settings
        prefs.setdefault('switchnew', True)
        self.w.follow_new.set_state(prefs['switchnew'])
        prefs.setdefault('raisenew', True)
        self.w.raise_new.set_state(prefs['raisenew'])
        prefs.setdefault('genthumb', True)
        self.w.create_thumbnail.set_state(prefs['genthumb'])

        num_images = prefs.get('numImages', 0)
        self.w.num_images.set_text(str(num_images))

        # profile settings
        prefs.setdefault('profile_use_scale', False)
        self.w.save_scale.set_state(prefs['profile_use_scale'])
        prefs.setdefault('profile_use_pan', False)
        self.w.save_pan.set_state(prefs['profile_use_pan'])
        prefs.setdefault('profile_use_cuts', False)
        self.w.save_cuts.set_state(prefs['profile_use_cuts'])
        prefs.setdefault('profile_use_transform', False)
        self.w.save_transform.set_state(prefs['profile_use_transform'])
        prefs.setdefault('profile_use_rotation', False)
        self.w.save_rotation.set_state(prefs['profile_use_rotation'])

    def save_preferences(self):
        self.t_.save()

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
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
