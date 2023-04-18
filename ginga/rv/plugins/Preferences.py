# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Make changes to channel settings graphically in the UI.

**Plugin Type: Local**

``Preferences`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**

The ``Preferences`` plugin sets the preferences *on a per-channel basis*.
The preferences for a given channel are inherited from the "Image"
channel until they are explicitly set and saved using this plugin.

If "Save Settings" is pressed, it will save the settings to the user's
$HOME/.ginga folder (a "channel_NAME.cfg" file for each channel NAME)
so that when a channel with the same name is created in future Ginga
sessions it will obtain the same settings.

**Color Distribution Preferences**

.. figure:: figures/cdist-prefs.png
   :width: 400px
   :align: center
   :alt: Color Distribution preferences

   "Color Distribution" preferences.

The "Color Distribution" preferences control the preferences used for the
data value to color index conversion that occurs after cut levels are
applied and just before final color mapping is performed.  It concerns
how the values between the low and high cut levels are distributed to
the color and intensity mapping phase.

The "Algorithm" control is used to set the algorithm used for the
mapping.  Click the control to show the list, or simply scroll the mouse
wheel while hovering the cursor over the control.  There are eight
algorithms available: linear, log, power, sqrt, squared, asinh, sinh,
and histeq.  The name of each algorithm is indicative of how
the data is mapped to the colors in the color map.  "linear" is the
default.

**Color Mapping Preferences**

.. figure:: figures/cmap-prefs.png
   :width: 400px
   :align: center
   :alt: Color Mapping preferences

   "Color Mapping" preferences.

The "Color Mapping" preferences control the preferences used for the
color map and intensity map, used during the final phase of the color
mapping process. Together with the "Color Distribution" preferences, these
control the mapping of data values into a 24-bpp RGB visual representation.

The "Colormap" control selects which color map should be loaded and
used.  Click the control to show the list, or simply scroll the mouse
wheel while hovering the cursor over the control.

.. note:: Ginga comes with a good selection of color maps, but should you
          want more, you can add custom ones or, if ``matplotlib`` is
          installed, you can load all the ones that it has.
          See "Customizing Ginga" for details.

The "Intensity" control selects which intensity map should be used
with the color map.  The intensity map is applied just before the color
map, and can be used to change the standard linear scale of values into
an inverted scale, logarithmic, etc.

The "Invert CMap" checkbox can be used to invert the selected color map
(note that a number of colormaps are also selectable from the "Colormap"
controlin inverted form).

The "Rotate" control can be used to rotate the colormap, while the
"Unrotate CMap" button will restore the rotation to its default, unrotated
state.

The "Color Defaults" button will reset all the color mapping controls to
the default values: "gray" color map, "ramp" (linear) intensity, and no
inversion or rotation of the color map.

**Contrast and Brightness (Bias) Preferences**

.. figure:: figures/contrast-prefs.png
   :width: 400px
   :align: center
   :alt: Contrast and Brightness (Bias) preferences

   "Contrast and Brightness (Bias)" preferences.

The "Contrast" and "Brightness" controls will set the contrast and brightness
(aka "bias") of the viewer.  They offer an alternative to 1) using the contrast
mode within the viewer window, or 2) manipulating the color bar by dragging (to
set brightness/bias) or scrolling (to set contrast).

The "Default Contrast" and "Default Brightness" controls set their respective
settings back to the default value.

**Auto Cuts Preferences**

.. figure:: figures/autocuts-prefs.png
   :width: 400px
   :align: center
   :alt: Auto Cuts Preferences

   "Auto Cuts" preferences.

The "Auto Cuts" preferences control the calculation of cut levels for
the view when the auto cut levels button or key is pressed, or when
loading a new image with auto cuts enabled.  You can also set the cut
levels manually from here.

The "Cut Low" and "Cut High" fields can be used to manually specify lower
and upper cut levels.  Pressing "Cut Levels" will set the levels to these
values manually. If a value is missing, it is assumed to default to the
whatever the current value is.

Pressing "Auto Levels" will calculate the levels according to an algorithm.
The "Auto Method" control is used to choose which auto cuts algorithm
used: "minmax" (minimum maximum values), "median" (based on median
filtering), "histogram" (based on an image histogram), "stddev" (based on
the standard deviation of pixel values), or "zscale" (based on the ZSCALE
algorithm popularized by IRAF).
As the algorithm is changed, the boxes under it may also change to
allow changes to parameters particular to each algorithm.

**Transform Preferences**

.. figure:: figures/transform-prefs.png
   :width: 400px
   :align: center
   :alt: Transform Preferences

   "Transform" preferences.

The "Transform" preferences provide for transforming the view of the image
by flipping the view in X or Y, swapping the X and Y axes, or rotating
the image in arbitrary amounts.

The "Flip X" and "Flip Y" checkboxes cause the image view to be
flipped in the corresponding axis.

The "Swap XY" checkbox causes the image view to be altered by swapping
the X and Y axes.  This can be combined with "Flip X" and "Flip Y" to rotate
the image in 90 degree increments.  These views will render more quickly
than arbitrary rotations using the "Rotate" control.

The "Rotate" control will rotate the image view the specified amount.
The value should be specified in degrees.  "Rotate" can be specified in
conjunction with flipping and swapping.

The "Restore" button will restore the view to the default view, which
is unflipped, unswapped, and unrotated.

**WCS Preferences**

.. figure:: figures/wcs-prefs.png
   :width: 400px
   :align: center
   :alt: WCS Preferences

   "WCS" preferences.

The "WCS" preferences control the display preferences for the World
Coordinate System (WCS) calculations used to report the cursor position in the
image.

The "WCS Coords" control is used to select the coordinate system in
which to display the result.

The "WCS Display" control is used to select a sexagesimal (``H:M:S``)
readout or a decimal degrees readout.

**Zoom Preferences**

.. figure:: figures/zoom-prefs.png
   :width: 400px
   :align: center
   :alt: Zoom preferences

   "Zoom" preferences.

The "Zoom" preferences control Ginga's zooming/scaling behavior.
Ginga supports two zoom algorithms, chosen using the "Zoom Alg" control:

* The "step" algorithm zooms the image inwards in discrete
  steps of 1X, 2X, 3X, etc. or outwards in steps of 1/2X, 1/3X, 1/4X,
  etc.  This algorithm results in the least artifacts visually, but is a
  bit slower to zoom over wide ranges when using a scrolling motion
  because more "throw" is required to achieve a large zoom change
  (this is not the case if one uses of the shortcut zoom keys, such as
  the digit keys).

* The "rate" algorithm zooms the image by advancing the scaling at
  a rate defined by the value in the "Zoom Rate" box.  This rate defaults
  to the square root of 2.  Larger numbers cause larger changes in scale
  between zoom levels.  If you like to zoom your images rapidly, at a
  small cost in image quality, you would likely want to choose this
  option.

Note that regardless of which method is chosen for the zoom algorithm,
the zoom can be controlled by holding down ``Ctrl`` (coarse) or ``Shift``
(fine) while scrolling to constrain the zoom rate (assuming the default
mouse bindings).

The "Stretch XY" control can be used to stretch one of the axes (X or
Y) relative to the other.  Select an axis with this control and roll the
scroll wheel while hovering over the "Stretch Factor" control to
stretch the pixels in the selected axis.

The "Scale X" and "Scale Y" controls offer direct access to the
underlying scaling, bypassing the discrete zoom steps.  Here, exact
values can be typed to scale the image.  Conversely, you will see these
values change as the image is zoomed.

The "Scale Min" and "Scale Max" controls can be used to place a
limit on how much the image can be scaled.

The "Interpolation" control allows you to choose how the image will be
interpolated.  Depending on which support packages are installed, the
following choices can be made:

* "basic" is nearest-neighbor using a built in algorithm, this is always
  available, is reasonably fast, and is the default.
* "area"
* "bicubic"
* "lanczos"
* "linear"
* "nearest" is nearest-neighbor (using support package)

The "Zoom Defaults" button will restore the controls to the Ginga
default values.

**Pan Preferences**

.. figure:: figures/pan-prefs.png
   :width: 400px
   :align: center
   :alt: Pan Preferences

   "Pan" preferences.

The "Pan" preferences control Ginga's panning behavior.

The "Pan X" and "Pan Y" controls offer direct access to set the pan
position in the image (the part of the image located at the center of
the window) -- you can see them change as you pan around the image.
You can set these values and then press "Apply Pan" to pan to that exact
position.

If the "Pan Coord" control is set to "data" then panning is controlled by
data coordinates in the image; if set to "WCS" then the values shown in
the "Pan X" and "Pan Y" controls will be WCS coordinates (assuming a valid
WCS is in the image).  In the latter case, the "WCS sexagesimal" control
can be left unchecked to show/set the coordinates in degrees, or checked to
show/set the values in standard sexigesimal notation.

The "Center Image" button sets the pan position to the center of the
image, as calculated by halving the dimensions in X and Y.

The "Mark Center" check box, when checked, will cause Ginga to draw a
small reticle in the center of the image.  This is useful for knowing
the pan position and for debugging.

**General Preferences**

.. figure:: figures/general-prefs.png
   :width: 400px
   :align: center
   :alt: General Preferences

   "General" preferences.

The "Num Images" setting specifies how many images can be retained in
buffers in this channel before being ejected.  A value of zero (0) means
unlimited--images will never be ejected.  If an image was loaded from
some accessible storage and it is ejected, it will automatically be
reloaded if the image is revisited by navigating the channel.

The "Sort Order" setting determines whether images are sorted in the
channel alphabetically by name or by the time when they were loaded.
This principally affects the order in which images are cycled when using
the up/down "arrow" keys or buttons, and not necessarily how they are
displayed in plugins like "Contents" or "Thumbs" (which generally have
their own setting preference for ordering).

The "Use scrollbars" check box controls whether the channel viewer will
show scroll bars around the edge of the viewer frame to pan the image.

**Reset (Viewer) Preferences**

.. figure:: figures/reset-prefs.png
   :width: 400px
   :align: center
   :alt: Reset (Viewer) Preferences

   "Reset" (Viewer) preferences.

Each channel viewer has a *viewer profile* that is initialized to the state
of the viewer just after creation and the restoration of saved settings for
that channel.  When switching between images, the attributes of the viewer
can be reset to this profile according to the checked boxes in this section.
*If nothing is checked, nothing will be reset from the viewer profile*.

To use this feature, set your viewer preferences as you prefer and
click the "Update Viewer Profile" button at the bottom of the plugin.
Now check which items should be reset to those values between images.
Finally, click the "Save Settings" button at the bottom if you want these
settings to be persistent across Ginga restarts and set as the default user
profile for this channel when you restart ginga and recreate this channel.

* "Reset Scale" will reset the zoom (scale) level to the viewer profile
* "Reset Pan" will reset the pan position to the viewer profile
* "Reset Transform" will reset any flip/swap transforms to the viewer profile
* "Reset Rotation" will reset any rotation to the viewer profile
* "Reset Cuts" will reset any cut levels to the viewer profile
* "Reset Distribution" will reset any color distribution to the viewer profile
* "Reset Contrast" will reset any contrast/bias to the viewer profile
* "Reset Color Map" will reset any color map settings to the viewer profile

.. tip:: If you use this feature you may also want to set "Remember (Image)
         Preferences" (see below).

.. note:: The complete order of adjustments is:

          * any reset items from the default viewer profile, if any
          * any remembered items from the image profile are applied, if any
          * any auto adjustments (cuts/zoom/center) are applied, if they were
            not overridden by a remembered setting

**Remember (Image) Preferences**

.. figure:: figures/remember-prefs.png
   :width: 400px
   :align: center
   :alt: Remember (Image) Preferences

   "Remember" (Image) preferences.

When an image is loaded, an *image profile* is created and attached to the
image metadata in the channel.  These profiles are continuously updated with
viewer state as the image is manipulated.  The "Remember" preferences
control which attributes of these profiles are restored to the viewer state
when the image is navigated (back) to in the channel:

* "Remember Scale" will restore the zoom (scale) level of the image
* "Remember Pan" will restore the pan position in the image
* "Remember Transform" will restore any flip or swap axes transforms
* "Remember Rotation" will restore any rotation of the image
* "Remember Cuts" will restore any cut levels for the image
* "Remember Distribution" will restore any color distribution (linear,log,etc)
* "Remember Contrast" will restore any contrast/bias adjustment
* "Remember Color Map" will restore any color map choices made

*If nothing is checked, nothing will be restored from the image profile*.

.. note:: These items will be set BEFORE any auto (cut/zoom/center new)
          adjustments are made. If a remembered item is set, it will override
          any auto adjustment setting for the channel.

.. tip:: If you use this feature you may also want to set "Reset (Viewer)
         Preferences" (see above).

***An Example***

As an example of using the Reset and Remember settings, suppose that you
frequently use the contrast adjustment. You would like the contrast that
you set with a particular image to be restored when that image is viewed
again. However, when you view a new image, you would like the contrast to
start out at some normal setting.

To accomplish this, manually reset the contrast to the desired default
setting.  Check "Reset Contrast" and then press "Update Viewer Profile".
Finally, check "Remember Contrast".  Click "Save Settings" to make the
channel settings persistent.

**New Image Preferences**

.. figure:: figures/newimages-prefs.png
   :width: 400px
   :align: center
   :alt: New Image Preferences

   "New Image" preferences.

The "New Images" preferences determine how Ginga reacts when a new image
is loaded into the channel.  *This includes when an older image is
revisited by clicking on its thumbnail in the ``Thumbs`` plugin or
double-clicking on it's name in the ``Contents`` plugin*.

The "Cut New" setting controls whether an automatic cut-level
calculation should be performed on the new image, or whether the
currently set cut levels should be applied.  The possible settings are:

* "off": always use the currently set cut levels;
* "once": calculate a new cut levels for the first image visited,
  then turn "off";
* "override": calculate a new cut levels until the user overrides
  it by manually setting a cut levels, then turn "off"; or
* "on": calculate a new cut levels always.

.. tip:: The "override" setting is provided for the convenience of
         having automatic cut levels, while preventing a manually set
         cuts from being overridden when a new image is ingested.  When
         typed in the image window, the semicolon key can be used to
         toggle the mode back to override (from "off"), while colon will
         set the preference to "on".  The ``Info`` (tab: Synopsis) plugin
         shows the state of this setting.

The "Zoom New" setting controls whether visiting an image should set the
zoom level to fit the image to the window.  The possible settings are:

* "off": always use the currently set zoom levels;
* "once": fit the first image to the window, then turn to "off";
* "override": images are automatically fitted until the zoom level is
  changed manually, then the mode automatically changes to "off", or
* "on": the new image is always zoomed to fit.

.. tip:: The "override" setting is provided for the convenience of
         having an automatic zoom, while preventing a manually set zoom
         level from being overridden when a new image is ingested.  When
         typed in the image window,  the apostrophe (a.k.a. "single quote")
         key can be used to toggle the mode back to "override" (from
         "off"), while quote (a.k.a. double quote) will set the preference
         to "on".  The ``Info`` (tab: Synopsis) plugin shows the state of
         this setting.

The "Center New" setting controls whether visiting an image should cause
the pan position to be reset to the center of the image.   The possible
settings are:

* "off": leave the current pan position as is;
* "once": center the first image visited, then turn to "off";
* "override": images are automatically centered until the pan position is
  changed manually, then the mode automatically changes to "off", or
* "on": the new image is always centered.

The "Follow New" setting is used to control whether Ginga will change
the display if a new image is loaded into the channel.  If unchecked,
the image is loaded (as seen, for example, by its appearance in the
``Thumbs`` tab), but the display will not change to the new image.  This
setting is useful in cases where new images are being loaded by some
automated means into a channel and the user wishes to study the current
image without being interrupted.

The "Raise New" setting controls whether Ginga will raise the tab of a
channel when an image is loaded into that channel.  If unchecked, then
Ginga will not raise the tab when an image is loaded into that
particular channel.

The "Create Thumbnail" setting controls whether Ginga will create a
thumbnail for images loaded into that channel.  In cases where many
images are being loaded into a channel frequently (e.g., a low frequency
video feed), it may be undesirable to create thumbnails for all of them.

The "Auto Orient" setting controls whether Ginga should attempt to orient
images by default according to image metadata. This is currently only useful
for RGB (e.g. JPEG) images that contain such metadata. It does not auto
orient by WCS, at present.

**ICC Profiles Preferences**

.. figure:: figures/icc-prefs.png
   :width: 400px
   :align: center
   :alt: ICC Profiles Preferences

   "ICC Profiles" preferences.

Ginga can make use of ICC (color management) profiles in the rendering
chain using the LittleCMS library.

.. note:: To make use of ICC profiles, create a "profiles" folder in the
          Ginga "home" (usually $HOME/.ginga) and put any necessary profiles
          there.  A working profile should be set by adding a value for
          "icc_working_profile" in your $HOME/.ginga/general.cfg file--
          do not include any leading path, just the filename of an ICC file
          in the profiles folder.  This will be used to convert any RGB files
          containing a profile to the working profile.

You can set the output profiles for any channel in this section of the
Preferences plugin.

The "Output ICC profile" control selects which profile to use for the
output rendering to the display.  The choices are from your profile files
in $HOME/.ginga/profiles.  Normally this should be a display profile.

The "Rendering intent" control chooses the algorithm used to render the
color in the ICC conversion process.  The choices are:

* absolute_colorimetric
* perceptual
* relative_colorimetric
* saturation

The "Proof ICC profile" and "Proof intent" are similarly chosen for proofing.

The "Black point compensation" checkbox turns on or off this feature in the
color conversion process.  See the documentation for LittleCMS or ICC color
management in general for details on these choices.

"""
import math

from ginga.gw import Widgets
from ginga.misc import ParamSet, Bunch

from ginga import cmap, imap, trcalc
from ginga import GingaPlugin
from ginga import AutoCuts, ColorDist
from ginga.util import wcs, wcsmod, rgb_cms

__all_ = ['Preferences']


class Preferences(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Preferences, self).__init__(fv, fitsimage)

        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        self.zoomalg_names = ('step', 'rate')

        # get Preferences preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Preferences')
        self.settings.add_defaults(orientation=None)
        self.settings.load(onError='silent')

        self.t_ = self.fitsimage.get_settings()
        self.autocuts_cache = {}
        self.gui_up = False

        self.calg_names = ColorDist.get_dist_names()
        self.autozoom_options = self.fitsimage.get_autozoom_options()
        self.autocut_options = self.fitsimage.get_autocuts_options()
        self.autocut_methods = self.fitsimage.get_autocut_methods()
        self.autocenter_options = self.fitsimage.get_autocenter_options()
        self.pancoord_options = ('data', 'wcs')
        self.sort_options = ('loadtime', 'alpha')

        for key in ['color_map', 'intensity_map',
                    'color_algorithm', 'color_hashsize',
                    'color_map_invert', 'color_map_rot_pct',
                    'contrast', 'brightness']:
            self.t_.get_setting(key).add_callback(
                'set', self.rgbmap_changed_ext_cb)

        self.t_.get_setting('autozoom').add_callback(
            'set', self.autozoom_changed_ext_cb)
        self.t_.get_setting('autocenter').add_callback(
            'set', self.autocenter_changed_ext_cb)
        self.t_.get_setting('autocuts').add_callback(
            'set', self.autocuts_changed_ext_cb)
        for key in ['switchnew', 'raisenew', 'genthumb', 'auto_orient']:
            self.t_.get_setting(key).add_callback(
                'set', self.set_chprefs_ext_cb)

        for key in ['pan']:
            self.t_.get_setting(key).add_callback(
                'set', self.pan_changed_ext_cb)
        for key in ['scale']:
            self.t_.get_setting(key).add_callback(
                'set', self.scale_changed_ext_cb)

        self.t_.get_setting('zoom_algorithm').add_callback(
            'set', self.set_zoomalg_ext_cb)
        self.t_.get_setting('zoom_rate').add_callback(
            'set', self.set_zoomrate_ext_cb)
        for key in ['scale_x_base', 'scale_y_base']:
            self.t_.get_setting(key).add_callback(
                'set', self.scalebase_changed_ext_cb)
        self.t_.get_setting('rot_deg').add_callback(
            'set', self.set_rotate_ext_cb)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            self.t_.get_setting(name).add_callback(
                'set', self.set_transform_ext_cb)

        self.t_.get_setting('autocut_method').add_callback('set',
                                                           self.set_autocut_method_ext_cb)
        self.t_.get_setting('autocut_params').add_callback('set',
                                                           self.set_autocut_params_ext_cb)
        self.t_.get_setting('cuts').add_callback(
            'set', self.cutset_cb)

        self.t_.setdefault('wcs_coords', 'icrs')
        self.t_.setdefault('wcs_display', 'sexagesimal')

        # buffer len (number of images in memory)
        self.t_.add_defaults(numImages=4)
        self.t_.get_setting('numImages').add_callback('set', self.set_buflen_ext_cb)

        self.icc_profiles = list(rgb_cms.get_profiles())
        self.icc_profiles.insert(0, None)
        self.icc_intents = rgb_cms.get_intents()

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))
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
        try:
            index = self.calg_names.index(self.t_.get('color_algorithm',
                                                      "linear"))
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_calg_cb)

        fr.set_widget(w)
        vbox.add_widget(fr)

        # COLOR MAPPING OPTIONS
        fr = Widgets.Frame("Color Mapping")

        captions = (('Colormap:', 'label', 'Colormap', 'combobox'),
                    ('Intensity:', 'label', 'Intensity', 'combobox'),
                    ('Rotate:', 'label', 'rotate_cmap', 'hscale'),
                    ('Invert CMap', 'checkbutton', 'Unrotate CMap', 'button',
                     'Color Defaults', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        self.w.cmap_choice = b.colormap
        self.w.imap_choice = b.intensity

        b.invert_cmap.set_tooltip("Invert color map")
        b.invert_cmap.set_state(False)
        b.invert_cmap.add_callback('activated', self.invert_cmap_cb)

        b.rotate_cmap.set_tracking(True)
        b.rotate_cmap.set_limits(0, 100, incr_value=1)
        b.rotate_cmap.set_value(0)
        b.rotate_cmap.add_callback('value-changed', self.rotate_cmap_cb)
        b.rotate_cmap.set_tooltip("Rotate the colormap")

        b.colormap.set_tooltip("Choose a color map for this image")
        b.intensity.set_tooltip("Choose an intensity map for this image")
        b.unrotate_cmap.set_tooltip("Undo cmap rotation")
        b.unrotate_cmap.add_callback('activated', lambda w: self.unrotate_cmap())
        b.color_defaults.set_tooltip("Restore all color map settings to defaults")
        b.color_defaults.add_callback('activated',
                                      lambda w: self.set_default_cmaps())
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

        # CONTRAST MANIPULATIONS
        fr = Widgets.Frame("Contrast and Brightness (Bias)")

        captions = (('Contrast:', 'label', 'contrast', 'hscale'),
                    ('Brightness:', 'label', 'brightness', 'hscale'),
                    ('_cb1', 'spacer', '_hbox_cb', 'hbox'))
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.contrast.set_tracking(True)
        b.contrast.set_limits(0, 100, incr_value=1)
        b.contrast.set_value(50)
        b.contrast.add_callback('value-changed', self.contrast_cb)
        b.contrast.set_tooltip("Set contrast for the viewer")

        b.brightness.set_tracking(True)
        b.brightness.set_limits(0, 100, incr_value=1)
        b.brightness.set_value(50)
        b.brightness.add_callback('value-changed', self.brightness_cb)
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
        vbox.add_widget(fr)

        # AUTOCUTS OPTIONS
        fr = Widgets.Frame("Auto Cuts")
        vbox2 = Widgets.VBox()
        fr.set_widget(vbox2)

        captions = (('Cut Low:', 'label', 'Cut Low Value', 'llabel',
                     'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High Value', 'llabel',
                     'Cut High', 'entry'),
                    ('spacer_1', 'spacer', 'spacer_2', 'spacer',
                     'Cut Levels', 'button'),
                    ('Auto Method:', 'label', 'Auto Method', 'combobox',
                     'Auto Levels', 'button'),)
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        loval, hival = self.t_['cuts']
        b.cut_levels.set_tooltip("Set cut levels manually")
        b.auto_levels.set_tooltip("Set cut levels by algorithm")
        b.cut_low.set_tooltip("Set low cut level (press Enter)")
        b.cut_low.set_length(9)
        b.cut_low_value.set_text('%.4g' % (loval))
        b.cut_high.set_tooltip("Set high cut level (press Enter)")
        b.cut_high.set_length(9)
        b.cut_high_value.set_text('%.4g' % (hival))

        b.cut_low.add_callback('activated', self.cut_levels)
        b.cut_high.add_callback('activated', self.cut_levels)
        b.cut_levels.add_callback('activated', self.cut_levels)
        b.auto_levels.add_callback('activated', self.auto_levels)

        # Setup auto cuts method choice
        combobox = b.auto_method
        index = 0
        method = self.t_.get('autocut_method', "histogram")
        for name in self.autocut_methods:
            combobox.append_text(name)
            index += 1
        try:
            index = self.autocut_methods.index(method)
            combobox.set_index(index)
        except Exception:
            pass
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

        b.rotate.set_limits(-359.99999999, 359.99999999, incr_value=10.0)
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
                    ('Scale Min:', 'label', 'Scale Min', 'entryset'),
                    ('Scale Max:', 'label', 'Scale Max', 'entryset'),
                    ('Interpolation:', 'label', 'Interpolation', 'combobox'),
                    ('Zoom Defaults', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        index = 0
        for name in self.zoomalg_names:
            b.zoom_alg.append_text(name.capitalize())
            index += 1
        zoomalg = self.t_.get('zoom_algorithm', "step")
        try:
            index = self.zoomalg_names.index(zoomalg)
            b.zoom_alg.set_index(index)
        except Exception:
            pass
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
        b.zoom_rate.set_limits(1.01, 10.0, incr_value=0.1)
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
        b.scale_min.set_text(str(scale_min))
        b.scale_min.add_callback('activated', self.set_scale_limit_cb)
        b.scale_min.set_tooltip("Set the minimum allowed scale in any axis")

        b.scale_max.set_text(str(scale_max))
        b.scale_max.add_callback('activated', self.set_scale_limit_cb)
        b.scale_min.set_tooltip("Set the maximum allowed scale in any axis")

        index = 0
        for name in trcalc.interpolation_methods:
            b.interpolation.append_text(name)
            index += 1
        interp = self.t_.get('interpolation', "basic")
        try:
            index = trcalc.interpolation_methods.index(interp)
        except ValueError:
            # previous choice might not be available if preferences
            # were saved when opencv was being used--if so, default
            # to "basic"
            index = trcalc.interpolation_methods.index('basic')
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
        pan_coord = self.t_.get('pan_coord', "data")
        if pan_coord == 'data':
            pan_x, pan_y = pan_x + coord_offset, pan_y + coord_offset
        b.pan_x.set_tooltip("Coordinate for the pan position in X axis")
        b.pan_x.set_text(str(pan_x))
        #b.pan_x.add_callback('activated', self.set_pan_cb)
        b.pan_y.set_tooltip("Coordinate for the pan position in Y axis")
        b.pan_y.set_text(str(pan_y))
        #b.pan_y.add_callback('activated', self.set_pan_cb)
        b.apply_pan.add_callback('activated', self.set_pan_cb)
        b.apply_pan.set_tooltip("Set the pan position")
        b.wcs_sexagesimal.set_tooltip("Display pan position in sexagesimal")
        b.wcs_sexagesimal.add_callback('activated',
                                       lambda w, tf: self._update_pan_coords())

        index = 0
        for name in self.pancoord_options:
            b.pan_coord.append_text(name)
            index += 1
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

        exp = Widgets.Expander("General")

        captions = (('Num Images:', 'label', 'Num Images', 'entryset'),
                    ('Sort Order:', 'label', 'Sort Order', 'combobox'),
                    ('Use scrollbars', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.num_images.set_tooltip(
            "Maximum number of in memory images in channel (0==unlimited)")
        num_images = self.t_.get('numImages', 0)
        self.w.num_images.set_text(str(num_images))
        self.w.num_images.add_callback('activated', self.set_buffer_cb)

        combobox = b.sort_order
        index = 0
        for name in self.sort_options:
            combobox.append_text(name)
            index += 1
        option = self.t_.get('sort_order', 'loadtime')
        index = self.sort_options.index(option)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_sort_cb)
        b.sort_order.set_tooltip("Sort order for images in channel")

        scrollbars = self.t_.get('scrollbars', 'off')
        self.w.use_scrollbars.set_state(scrollbars in ['on', 'auto'])
        self.w.use_scrollbars.add_callback('activated', self.set_scrollbars_cb)
        b.use_scrollbars.set_tooltip("Use scrollbars around viewer")

        fr = Widgets.Frame()
        fr.set_widget(w)
        exp.set_widget(fr)
        vbox.add_widget(exp, stretch=0)

        exp = Widgets.Expander("Reset (Viewer)")

        captions = (('Reset Scale', 'checkbutton',
                     'Reset Pan', 'checkbutton'),
                    ('Reset Transform', 'checkbutton',
                    'Reset Rotation', 'checkbutton'),
                    ('Reset Cuts', 'checkbutton',
                     'Reset Distribution', 'checkbutton'),
                    ('Reset Contrast', 'checkbutton',
                     'Reset Color Map', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        self.w.reset_scale.set_state(self.t_.get('viewer_restore_scale', False))
        self.w.reset_scale.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_scale.set_tooltip("Reset scale between images")
        self.w.reset_pan.set_state(self.t_.get('viewer_restore_pan', False))
        self.w.reset_pan.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_pan.set_tooltip("Reset pan position between images")
        self.w.reset_transform.set_state(
            self.t_.get('viewer_restore_transform', False))
        self.w.reset_transform.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_transform.set_tooltip("Reset transform between images")
        self.w.reset_rotation.set_state(
            self.t_.get('viewer_restore_rotation', False))
        self.w.reset_rotation.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_rotation.set_tooltip("Reset rotation between images")
        self.w.reset_cuts.set_state(self.t_.get('viewer_restore_cuts', False))
        self.w.reset_cuts.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_cuts.set_tooltip("Reset cut levels between images")
        self.w.reset_distribution.set_state(
            self.t_.get('viewer_restore_distribution', False))
        self.w.reset_distribution.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_distribution.set_tooltip("Reset color distribution between images")
        self.w.reset_contrast.set_state(
            self.t_.get('viewer_restore_contrast', False))
        self.w.reset_contrast.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_contrast.set_tooltip("Reset contrast/bias between images")
        self.w.reset_color_map.set_state(
            self.t_.get('viewer_restore_color_map', False))
        self.w.reset_color_map.add_callback('activated', self.reset_viewer_cb)
        self.w.reset_color_map.set_tooltip("Reset color map between images")

        fr = Widgets.Frame()
        vb2 = Widgets.VBox()
        txt_w = Widgets.TextArea(wrap=True, editable=False)
        txt_w.set_text("Check items you want to be reset from the default viewer profile when switching between images. This happens BEFORE any items remembered with image are set.")
        vb2.add_widget(txt_w, stretch=0)
        vb2.add_widget(w, stretch=1)
        fr.set_widget(vb2)
        exp.set_widget(fr)
        vbox.add_widget(exp, stretch=0)

        exp = Widgets.Expander("Remember (Image)")

        captions = (('Remember Scale', 'checkbutton',
                     'Remember Pan', 'checkbutton'),
                    ('Remember Transform', 'checkbutton',
                    'Remember Rotation', 'checkbutton'),
                    ('Remember Cuts', 'checkbutton',
                     'Remember Distribution', 'checkbutton'),
                    ('Remember Contrast', 'checkbutton',
                     'Remember Color Map', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        self.w.remember_scale.set_state(self.t_.get('profile_use_scale', False))
        self.w.remember_scale.add_callback('activated', self.set_profile_cb)
        self.w.remember_scale.set_tooltip("Remember scale with image")
        self.w.remember_pan.set_state(self.t_.get('profile_use_pan', False))
        self.w.remember_pan.add_callback('activated', self.set_profile_cb)
        self.w.remember_pan.set_tooltip("Remember pan position with image")
        self.w.remember_transform.set_state(
            self.t_.get('profile_use_transform', False))
        self.w.remember_transform.add_callback('activated', self.set_profile_cb)
        self.w.remember_transform.set_tooltip("Remember transform with image")
        self.w.remember_rotation.set_state(
            self.t_.get('profile_use_rotation', False))
        self.w.remember_rotation.add_callback('activated', self.set_profile_cb)
        self.w.remember_rotation.set_tooltip("Remember rotation with image")
        self.w.remember_cuts.set_state(self.t_.get('profile_use_cuts', False))
        self.w.remember_cuts.add_callback('activated', self.set_profile_cb)
        self.w.remember_cuts.set_tooltip("Remember cut levels with image")
        self.w.remember_distribution.set_state(
            self.t_.get('profile_use_distribution', False))
        self.w.remember_distribution.add_callback('activated', self.set_profile_cb)
        self.w.remember_distribution.set_tooltip("Remember color distribution algorithm with image")
        self.w.remember_contrast.set_state(
            self.t_.get('profile_use_contrast', False))
        self.w.remember_contrast.add_callback('activated', self.set_profile_cb)
        self.w.remember_contrast.set_tooltip("Remember contrast/bias with image")
        self.w.remember_color_map.set_state(
            self.t_.get('profile_use_color_map', False))
        self.w.remember_color_map.add_callback('activated', self.set_profile_cb)
        self.w.remember_color_map.set_tooltip("Remember color map with image")

        fr = Widgets.Frame()
        vb2 = Widgets.VBox()
        txt_w = Widgets.TextArea(wrap=True, editable=False)
        txt_w.set_text("Check items you want remembered with each image and restored to the viewer when each image is viewed again. Note that these override auto cut/zoom/center new settings.")
        vb2.add_widget(txt_w, stretch=0)
        vb2.add_widget(w, stretch=1)
        fr.set_widget(vb2)
        exp.set_widget(fr)
        vbox.add_widget(exp, stretch=0)

        exp = Widgets.Expander("New Images")

        captions = (('Cut New:', 'label', 'Cut New', 'combobox'),
                    ('Zoom New:', 'label', 'Zoom New', 'combobox'),
                    ('Center New:', 'label', 'Center New', 'combobox'),
                    ('Follow New', 'checkbutton', 'Raise New', 'checkbutton'),
                    ('Create thumbnail', 'checkbutton',
                     'Auto Orient', 'checkbutton'),
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
        b.cut_new.set_tooltip("Automatically set cut levels when switching images")

        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.append_text(name)
            index += 1
        option = self.t_.get('autozoom', "off")
        index = self.autozoom_options.index(option)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_autozoom_cb)
        b.zoom_new.set_tooltip("Automatically fit image to window when switching images")

        combobox = b.center_new
        index = 0
        for name in self.autocenter_options:
            combobox.append_text(name)
            index += 1
        option = self.t_.get('autocenter', "off")
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = {True: 'on', False: 'off'}
            option = choice[option]
        index = self.autocenter_options.index(option)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_autocenter_cb)
        b.center_new.set_tooltip("Automatically center image in window when switching images")

        b.follow_new.set_tooltip("View new images as they arrive")
        b.raise_new.set_tooltip("Raise and focus tab for new images")
        b.create_thumbnail.set_tooltip("Create thumbnail for new images")
        b.auto_orient.set_tooltip("Auto orient new (RGB) images")

        self.w.follow_new.set_state(True)
        self.w.follow_new.add_callback('activated', self.set_chprefs_cb)
        self.w.raise_new.set_state(True)
        self.w.raise_new.add_callback('activated', self.set_chprefs_cb)
        self.w.create_thumbnail.set_state(True)
        self.w.create_thumbnail.add_callback('activated', self.set_chprefs_cb)
        self.w.auto_orient.set_state(True)
        self.w.auto_orient.add_callback('activated', self.set_chprefs_cb)

        fr = Widgets.Frame()
        fr.set_widget(w)
        exp.set_widget(fr)
        vbox.add_widget(exp, stretch=0)

        exp = Widgets.Expander("ICC Profiles")

        captions = (('Output ICC profile:', 'label', 'Output ICC profile',
                     'combobox'),
                    ('Rendering intent:', 'label', 'Rendering intent',
                     'combobox'),
                    ('Proof ICC profile:', 'label', 'Proof ICC profile',
                     'combobox'),
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
        try:
            index = self.icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for the viewer display")

        value = self.t_.get('icc_output_intent', 'perceptual')
        combobox = b.rendering_intent
        index = 0
        for name in self.icc_intents:
            combobox.append_text(name)
            index += 1
        try:
            index = self.icc_intents.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for the viewer display")

        value = self.t_.get('icc_proof_profile', None)
        combobox = b.proof_icc_profile
        index = 0
        for name in self.icc_profiles:
            combobox.append_text(str(name))
            index += 1
        try:
            index = self.icc_profiles.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("ICC profile for soft proofing")

        value = self.t_.get('icc_proof_intent', None)
        combobox = b.proof_intent
        index = 0
        for name in self.icc_intents:
            combobox.append_text(name)
            index += 1
        try:
            index = self.icc_intents.index(value)
            combobox.set_index(index)
        except Exception:
            pass
        combobox.add_callback('activated', self.set_icc_profile_cb)
        combobox.set_tooltip("Rendering intent for soft proofing")

        value = self.t_.get('icc_black_point_compensation', False)
        b.black_point_compensation.set_state(value)
        b.black_point_compensation.add_callback(
            'activated', self.set_icc_profile_cb)
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
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Save Settings")
        btn.add_callback('activated', lambda w: self.save_preferences())
        btn.set_tooltip("Save current settings for channel (across restarts)")
        btns.add_widget(btn)
        btn = Widgets.Button("Update Viewer Profile")
        btn.add_callback('activated', self.update_viewer_profile_cb)
        btn.set_tooltip("Update viewer profile from current settings (click 'Save Settings' to make persistent)")
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.gui_up = True

    def set_cmap_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        map from the preferences pane."""
        name = cmap.get_names()[index]
        self.t_.set(color_map=name)

    def set_imap_cb(self, w, index):
        """This callback is invoked when the user selects a new intensity
        map from the preferences pane."""
        name = imap.get_names()[index]
        self.t_.set(intensity_map=name)

    def set_calg_cb(self, w, index):
        """This callback is invoked when the user selects a new color
        hashing algorithm from the preferences pane."""
        #index = w.get_index()
        name = self.calg_names[index]
        self.t_.set(color_algorithm=name)

    def unrotate_cmap(self):
        self.t_.set(color_map_rot_pct=0.0)

    def set_default_cmaps(self):
        cmap_name = "gray"
        imap_name = "ramp"
        index = self.cmap_names.index(cmap_name)
        self.w.cmap_choice.set_index(index)
        index = self.imap_names.index(imap_name)
        self.w.imap_choice.set_index(index)
        self.t_.set(color_map=cmap_name, intensity_map=imap_name,
                    color_map_invert=False, color_map_rot_pct=0.0)

    def contrast_cb(self, w, val):
        pct = val / 100.0
        self.t_.set(contrast=pct)

    def brightness_cb(self, w, val):
        pct = val / 100.0
        self.t_.set(brightness=pct)

    def rotate_cmap_cb(self, w, val):
        pct = val / 100.0
        self.t_.set(color_map_rot_pct=pct)

    def invert_cmap_cb(self, w, tf):
        self.t_.set(color_map_invert=tf)

    def restore_contrast_cb(self, w):
        self.t_.set(contrast=0.5)

    def restore_brightness_cb(self, w):
        self.t_.set(brightness=0.5)

    def set_default_distmaps(self):
        name = 'linear'
        index = self.calg_names.index(name)
        self.w.calg_choice.set_index(index)
        self.t_.set(color_algorithm=name)

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

    def set_scale_limit_cb(self, *args):
        scale_min = self.w.scale_min.get_text().lower()
        if scale_min == 'none':
            scale_min = None
        else:
            scale_min = float(scale_min)
        scale_max = self.w.scale_max.get_text().lower()
        if scale_max == 'none':
            scale_max = None
        else:
            scale_max = float(scale_max)
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

    def cut_levels(self, w):
        fitsimage = self.fitsimage
        loval, hival = fitsimage.get_cut_levels()
        try:
            lostr = self.w.cut_low.get_text().strip()
            if lostr != '':
                loval = float(lostr)

            histr = self.w.cut_high.get_text().strip()
            if histr != '':
                hival = float(histr)
            self.logger.debug("locut=%f hicut=%f" % (loval, hival))

            return fitsimage.cut_levels(loval, hival)
        except Exception as e:
            self.fv.show_error("Error cutting levels: %s" % (str(e)))

        return True

    def auto_levels(self, w):
        self.fitsimage.auto_levels()

    def cutset_cb(self, setting, value):
        if not self.gui_up:
            return
        loval, hival = value
        self.w.cut_low_value.set_text('%.4g' % (loval))
        self.w.cut_high_value.set_text('%.4g' % (hival))

    def config_autocut_params(self, method):
        try:
            index = self.autocut_methods.index(method)
            self.w.auto_method.set_index(index)
        except Exception:
            pass

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

    def set_autocut_method_ext_cb(self, setting, value):
        if not self.gui_up:
            return

        autocut_method = self.t_['autocut_method']
        self.fv.gui_do(self.config_autocut_params, autocut_method)

    def set_autocut_params_ext_cb(self, setting, value):
        if not self.gui_up:
            return

        params = self.t_['autocut_params']
        params_d = dict(params)   # noqa
        self.ac_params.update_params(params_d)
        #self.fv.gui_do(self.ac_params.params_to_widgets)

    def set_autocut_method_cb(self, w, idx):
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
        flip_x, flip_y, swap_xy = (
            self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy'])
        self.w.flip_x.set_state(flip_x)
        self.w.flip_y.set_state(flip_y)
        self.w.swap_xy.set_state(swap_xy)

    def rgbmap_changed_ext_cb(self, setting, value):
        if not self.gui_up:
            return

        calg_name = self.t_['color_algorithm']
        try:
            idx = self.calg_names.index(calg_name)
        except IndexError:
            idx = 0
        self.w.algorithm.set_index(idx)

        cmap_name = self.t_['color_map']
        try:
            idx = self.cmap_names.index(cmap_name)
        except IndexError:
            idx = 0
        self.w.colormap.set_index(idx)

        imap_name = self.t_['intensity_map']
        try:
            idx = self.imap_names.index(imap_name)
        except IndexError:
            idx = 0
        self.w.intensity.set_index(idx)

        contrast_pct = self.t_['contrast']
        self.w.contrast.set_value(int(contrast_pct * 100))

        bright_pct = self.t_['brightness']
        self.w.brightness.set_value(int(bright_pct * 100))

        self.w.invert_cmap.set_state(self.t_['color_map_invert'])

        rot_pct = self.t_['color_map_rot_pct']
        self.w.rotate_cmap.set_value(int(rot_pct * 100))

    def set_buflen_ext_cb(self, setting, value):
        num_images = self.t_['numImages']

        # update the datasrc length
        chinfo = self.channel
        chinfo.datasrc.set_bufsize(num_images)
        self.logger.debug("num images was set to {0}".format(num_images))

        if not self.gui_up:
            return
        self.w.num_images.set_text(str(num_images))

    def set_sort_cb(self, w, index):
        """This callback is invoked when the user selects a new sort order
        from the preferences pane."""
        name = self.sort_options[index]
        self.t_.set(sort_order=name)

    def set_scrollbars_cb(self, w, tf):
        """This callback is invoked when the user checks the 'Use Scrollbars'
        box in the preferences pane."""
        scrollbars = 'on' if tf else 'off'
        self.t_.set(scrollbars=scrollbars)

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
        elif pan_coord == 'wcs':
            pan_x = float(pan_xs)
            pan_y = float(pan_ys)
        else:
            coord_offset = self.fv.settings.get('pixel_coords_offset', 0.0)
            pan_x = float(pan_xs) - coord_offset
            pan_y = float(pan_ys) - coord_offset

        self.fitsimage.set_pan(pan_x, pan_y, coord=pan_coord)
        return True

    def _update_pan_coords(self):
        pan_coord = self.t_.get('pan_coord', 'data')
        pan_x, pan_y = self.fitsimage.get_pan(coord=pan_coord)
        if pan_coord == 'wcs':
            use_sex = self.w.wcs_sexagesimal.get_state()
            if use_sex:
                pan_x = wcs.ra_deg_to_str(pan_x, precision=7,
                                          format='%02d:%02d:%02d.%07d')
                pan_y = wcs.dec_deg_to_str(pan_y, precision=7,
                                           format='%s%02d:%02d:%02d.%07d')
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
        auto_orient = (self.w.auto_orient.get_state() != 0)
        self.t_.set(switchnew=switchnew, raisenew=raisenew,
                    genthumb=genthumb, auto_orient=auto_orient)

    def set_chprefs_ext_cb(self, *args):
        if self.gui_up:
            self.w.follow_new.set_state(self.t_['switchnew'])
            self.w.raise_new.set_state(self.t_['raisenew'])
            self.w.create_thumbnail.set_state(self.t_['genthumb'])
            self.w.auto_orient.set_state(self.t_['auto_orient'])

    def set_profile_cb(self, *args):
        remember_scale = (self.w.remember_scale.get_state() != 0)
        remember_pan = (self.w.remember_pan.get_state() != 0)
        remember_cuts = (self.w.remember_cuts.get_state() != 0)
        remember_transform = (self.w.remember_transform.get_state() != 0)
        remember_rotation = (self.w.remember_rotation.get_state() != 0)
        remember_distribution = (self.w.remember_distribution.get_state() != 0)
        remember_contrast = (self.w.remember_contrast.get_state() != 0)
        remember_color_map = (self.w.remember_color_map.get_state() != 0)
        self.t_.set(profile_use_scale=remember_scale,
                    profile_use_pan=remember_pan,
                    profile_use_cuts=remember_cuts,
                    profile_use_transform=remember_transform,
                    profile_use_rotation=remember_rotation,
                    profile_use_distribution=remember_distribution,
                    profile_use_contrast=remember_contrast,
                    profile_use_color_map=remember_color_map)

    def reset_viewer_cb(self, *args):
        reset_scale = (self.w.reset_scale.get_state() != 0)
        reset_pan = (self.w.reset_pan.get_state() != 0)
        reset_cuts = (self.w.reset_cuts.get_state() != 0)
        reset_transform = (self.w.reset_transform.get_state() != 0)
        reset_rotation = (self.w.reset_rotation.get_state() != 0)
        reset_distribution = (self.w.reset_distribution.get_state() != 0)
        reset_contrast = (self.w.reset_contrast.get_state() != 0)
        reset_color_map = (self.w.reset_color_map.get_state() != 0)
        self.t_.set(viewer_restore_scale=reset_scale,
                    viewer_restore_pan=reset_pan,
                    viewer_restore_cuts=reset_cuts,
                    viewer_restore_transform=reset_transform,
                    viewer_restore_rotation=reset_rotation,
                    viewer_restore_distribution=reset_distribution,
                    viewer_restore_contrast=reset_contrast,
                    viewer_restore_color_map=reset_color_map)

    def update_viewer_profile_cb(self, *args):
        self.fitsimage.capture_default_viewer_profile()

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

        self.w.contrast.set_value(int(prefs.get('contrast', 0.5) * 100))
        self.w.brightness.set_value(int(prefs.get('brightness', 0.5) * 100))
        self.w.invert_cmap.set_state(prefs.get('color_map_invert', False))
        self.w.rotate_cmap.set_value(int(prefs.get('color_map_rot_pct', 0.0) * 100))

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
        self.w.zoom_rate.set_enabled(zoomalg != 'step')
        self.w.stretch_factor.set_enabled(zoomalg != 'step')

        self.scalebase_changed_ext_cb(prefs, None)

        scale_x, scale_y = self.fitsimage.get_scale_xy()
        self.w.scale_x.set_text(str(scale_x))
        self.w.scale_y.set_text(str(scale_y))

        scale_min = prefs.get('scale_min', None)
        self.w.scale_min.set_text(str(scale_min))
        scale_max = prefs.get('scale_max', None)
        self.w.scale_max.set_text(str(scale_max))

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
        prefs.setdefault('auto_orient', True)
        self.w.auto_orient.set_state(prefs['auto_orient'])

        num_images = prefs.get('numImages', 0)
        self.w.num_images.set_text(str(num_images))

        # remember settings
        prefs.setdefault('profile_use_scale', False)
        self.w.remember_scale.set_state(prefs['profile_use_scale'])
        prefs.setdefault('profile_use_pan', False)
        self.w.remember_pan.set_state(prefs['profile_use_pan'])
        prefs.setdefault('profile_use_cuts', False)
        self.w.remember_cuts.set_state(prefs['profile_use_cuts'])
        prefs.setdefault('profile_use_transform', False)
        self.w.remember_transform.set_state(prefs['profile_use_transform'])
        prefs.setdefault('profile_use_rotation', False)
        self.w.remember_rotation.set_state(prefs['profile_use_rotation'])
        prefs.setdefault('profile_use_color_map', False)
        self.w.remember_color_map.set_state(prefs['profile_use_color_map'])

        # viewer profile settings
        prefs.setdefault('viewer_restore_scale', False)
        self.w.reset_scale.set_state(prefs['viewer_restore_scale'])
        prefs.setdefault('viewer_restore_pan', False)
        self.w.reset_pan.set_state(prefs['viewer_restore_pan'])
        prefs.setdefault('viewer_restore_cuts', False)
        self.w.reset_cuts.set_state(prefs['viewer_restore_cuts'])
        prefs.setdefault('viewer_restore_transform', False)
        self.w.reset_transform.set_state(prefs['viewer_restore_transform'])
        prefs.setdefault('viewer_restore_rotation', False)
        self.w.reset_rotation.set_state(prefs['viewer_restore_rotation'])
        prefs.setdefault('viewer_restore_color_map', False)
        self.w.reset_color_map.set_state(prefs['viewer_restore_color_map'])

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

# END
