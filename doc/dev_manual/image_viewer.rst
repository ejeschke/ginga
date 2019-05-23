
.. _ch-image-viewer-operations:

*****************************
Ginga Image Viewer Operations
*****************************

This chapter describes the operations supported by the basic Ginga image
viewer and how to access them programatically.


Manipulating the view programatically
=====================================

The sections below describe how to manipulate the view programatically.
For all of these API examples we assume the viewer object is contained
in variable ``v``.  One way to create one::

  >>> from ginga import toolkit
  >>> toolkit.use('qt5')
  >>> from ginga.gw import Viewers
  >>> from ginga.misc import log
  >>> logger = log.get_logger("viewer1", log_stderr=True, level=40)
  >>> v = Viewers.CanvasView(logger=logger)
  
Many of the API calls simply set a value in the viewer's settings
object; if so, we note the associated keyword for that setting.


Loading the Viewer
==================

The image viewer can load data in a number of formats, but all formats
are wrapped with a class that corresponds to the *model* part of the
model-view-controller design used by Ginga.
For more information on creating an image wrapper object,
see :ref:`ch-image-data-wrappers`.

Once you have successfully loaded an image wrapper, you can set it into
the image viewer::

  >>> v.set_image(img)


Scaling
=======

In Ginge lexicon, "scaling" is setting a precise scale factor for pixels.
For example a scale factor of 2.0 means that two pixels are shown in the
viewer for every one pixel of data.

Ginga allows different scale factors for the X and Y axes.

Set a precise scale for X and Y::

  >>> v.set_scale((0.5, 0.5))

.. note:: Corresponds to the viewer setting ``scale``.

Get the scale for X and Y::

  >>> v.get_scale_xy()
  (0.5, 0.5)

If the scale factors are always set to the same value and adjusted
equally in tandem, then you can obtain the general scale value as::

  >>> v.get_scale_max()
  0.5

  
Scaling Limits
--------------

Ginga places a limit on the scale when the scale would result in an
aberrant viewing condition.  For example, it will cease to increase the
scale when the pixel size approaches the window size.

Ginga has a feature for setting arbitrary hard limits on the minimum and
maximum scale.

To get the scale limits (returns minimum and maximum scale)::

  >>> v.get_scale_limits()
  (1e-05, 10000.0)

To set the scale limits::

  >>> v.set_scale_limits(min_scale, max_scale)

The limits apply to all dimensions.  A value of ``None`` (the default)
means that no artificial limit will be imposed.


Zooming
=======

Although Ginga uses scale factors to accomplish image scaling, it also
supports the concept of zooming via *levels*.  It does this by mapping a
zoom level to a scale factor according to the *zoom algorithm* (see
following section) in use. 

Zoom algorithms assume that a 1:1 scale is always zoom level 0.
Providing a negative zoom level zooms "out" (smaller scale) while a
positive value zooms "in" (larger scale).  

Set a zoom level::

  >>> v.zoom_to(4)

Zoom in one level::

  >>> v.zoom_in()

Zoom out three levels::

  >>> v.zoom_out(3)

Zoom so that the loaded image fits the window::

  >>> v.zoom_fit()

Get the current zoom level corresponding to the current scale::

  >>> v.get_zoom()
  -8.544

.. note:: Zoom levels need not be integers, and there should be an
   invertable mapping between scale and zoom level defined by the zoom
   algorithm.


Zoom Algorithms
---------------

There are two main zoom algorithms, "step" and "rate", for determining
zoom levels and corresponding scales.  The step algorithm just zooms in
integer multiples of the pixels: 1, 2, 3, 4, ... or 1/2, 1/3, 1/4, etc.
The rate algorithm simply applies a multiplier to the current scale to
arrive at the new scale.  This can be more appropriate to achieve a
faster (or slower) rate of zoom than stepping. 

Get the zoom algorithm in use::

  >>> v.get_zoom_algorithm()
  'step'

Set the zoom algorithm::

  >>> v.set_zoom_algorithm('rate')

.. note:: Corresponds to the viewer setting ``zoom_algorithm``.
  
Get the zoom rate::

  >>> v.get_zoomrate()
  1.4142135623730951

Set the zoom rate::

  >>> v.set_zoomrate(1.1)

.. note:: Corresponds to the viewer setting ``zoom_rate``.
   The zoom rate should be defined as a value greater than 1.
   This value is ignored when the "step" algorithm is in use.
 
  
Panning
=======

The "pan position" defines the point on which the viewer should be
centered.  Normally this is specified in data coordinates, but 
it can also be specified in world coordinates if a valid WCS is
available in an image that is loaded.

Get the pan position in data coordinates (the default)::

  >>> v.get_pan()
  (1136.0, 2136.5)

Set the pan position::

  >>> v.set_pan((500.0, 1500.0))

Get the pan position in world coordinates (in this case, degrees)::

  >>> v.get_pan(coord='wcs')
  (300.16929984148425, 22.80602873666544)

Set the pan position in world coordinates::

  >>> v.set_pan((298.21, 24.6), coord='wcs')

.. note:: Corresponds to the viewer settings ``pan`` and ``pan_coord``.
  
Pan to 25% of the X axis and 75% of the Y axis::

  >>> v.panset_pct(0.25, 0.75)

Center the image (i.e., pan to center)::

  >>> v.center_image()

Get the coordinates in the actual data corresponding to the
area shown in the display for the current zoom level and pan::

  >>> v.get_pan_rect()
  array([[ 886. , 1886.5],
         [ 886. , 2386.5],
         [1386. , 2386.5],
         [1386. , 1886.5]])

The values are returned as corners lower-left, upper-left, upper-right,
lower-right.


Transforms
==========

The Ginga viewer provides three quick transforms in addition to rotation
(described below).  These are flipping in the X axis, flipping in the Y
axis, and swapping axes.  These three transforms can be set in a single
call, with three booleans, in the order just listed.

Flip the view in the X dimension::

  >>> v.transform(True, False, False)

Flip the view in the Y dimension::

  >>> v.transform(False, True, False)

Flip the view in the X dimension and swap the X and Y axes::

  >>> v.transform(True, False, True)

Get the existing transforms:: 

  >>> v.get_transforms()
  (True, False, True)

.. note:: Corresponds to the viewer settings ``flip_x``, ``flip_y`` and
   ``swap_xy``.
  
Attempt to orient the viewer according to the image loaded (may set
transforms to accomplish this):: 

  >>> v.auto_orient()


Rotation
========

The Ginga viewer can also rotate the image.  Values are specified in
degrees.

Rotate the view 45 degrees::

  >>> v.rotate(45.0)

Get current rotation:

  >>> v.get_rotation()
  45.0

.. note:: Corresponds to the viewer setting ``rot_deg``.


Cut Levels
==========

The cut levels are Ginga's lexicon for the low and high values used to
establish the mapping from data values to the minimum and maximum
pixel luminance values in the viewer.  Values in the data below the low
cut value will be driven to the bottom luminance value and values above
the high cut value will be driven to the top luminance value.  The
values in between are scaled to the range between these values.

Setting cut levels on the viewer::

  >>> v.cut_levels(lo_val, hi_val)

Get current cut levels::

  >>> v.get_cut_levels()
  (440.6118816303353, 606.8032622632695)

.. note:: Corresponds to the viewer setting ``cuts``.

Auto cut levels
---------------

Calculating and applying an auto cut levels (aka "auto levels"), using
the current algorithm setting and parameters::

  >>> v.auto_levels()

Find out what automatic cut levels algorithms are available::

  >>> v.get_autocut_methods()
  ('minmax', 'median', 'histogram', 'stddev', 'zscale')

Set viewer to use a specific algorithm, with parameters::

  >>> v.set_autocut_params('histogram', pct=0.90)

.. note:: Every auto cuts algorithm is encapsulated into an auto cuts
   class.  The parameters can vary according to the parameters of the
   algorithm and are passed as keyword parameters to this call.

.. todo:: Have link here to all the autocut classes and their parameters

Retrieve the current autocuts object::

  >>> v.autocuts
  <ginga.AutoCuts.Histogram at 0x7fb404a19dd8>

Explicitly set the autocuts object directly::

  >>> from ginga.AutoCuts import ZScale
  >>> ac = ZScale(v.get_logger(), contrast=0.4)
  >>> v.set_autocuts(ac)

.. note:: Unless you are using a custom autocuts class it is generally
   easier to just use the set_autocut_params() method.


Color Distribution
==================

The color distribution algorithm distributes the values in the image
*after* the cut levels to the colors defined by the color map.  This
normally describes a mapping curve such as linear, logarithmic, etc.

Find out what color distribution algorithms are available::

  >>> v.get_color_algorithms()
  ['linear', 'log', 'power', 'sqrt', 'squared', 'asinh', 'sinh', 'histeq']

Set a specific color distribution algorithm::

  >>> v.set_color_algorithm('log')

Find out which one is being used::

  >>> v.get_settings().get('color_algorithm')
  'log'

  
Color Map
=========

Find out what color maps are available::

  >>> from ginga import cmap
  >>> cmap.get_names()
  ['Accent',
   'Accent_r',
   'afmhot',
   'afmhot_r',
   ...
  'YlOrBr_r',
  'YlOrRd',
  'YlOrRd_r']

Set a color map::

  >>> v.set_color_map('YlOrBr_r')

Find out which one is being used::

  >>> v.get_settings().get('color_map')
  'YlOrBr_r'

Enable matplotlib color maps to be available (if ``matplotlib`` is installed)::

  >>> cmap.add_matplotlib_cmaps()

Invert the color map::

  >>> v.invert_cmap()

Shift the color map by ``pct`` percent::

  >>> v.shift_cmap(0.2)

Stretch/shrink and shift color map::

  >>> v.scale_and_shift_cmap(scale_pct, shift_pct)
  

Intensity Map
=============

.. note:: Intensity maps are a feature that largely duplicates the
   functionality of color distributions (see above).  It performs a
   remapping of the colors after the color mapping phase has been
   applied.  We suggest that most users will want to leave the default
   setting of 'ramp', which is leaves the color map as is.

Find out what intensity maps are available::

  >>> from ginga import imap
  >>> imap.get_names()
  ['equa',
   'expo',
   'gamma',
   'jigsaw',
   'lasritt',
   'log',
   'neg',
   'neglog',
   'null',
   'ramp',
   'stairs',
   'ultrasmooth']

Set an intensity map::

  >>> v.set_intensity_map('lasritt')

Find out which one is being used::

  >>> v.get_settings().get('intensity_map')
  'lasritt'


Auto configuration
==================

Ginga has some settings that control whether certain initializations are
performed when a new image is set in the viewer.

Enable auto orientation of new image (see ``auto_orient()`` under
"Transforms"):: 

  >>> v.enable_auto_orient(True)

.. note:: Corresponds to the viewer setting ``auto_orient``.

Enable auto centering (pan to center of new image)::

  >>> v.enable_autocenter('on')

.. note:: Corresponds to the viewer setting ``autocenter``.

Enable auto cuts (calculate and set cut levels of new image)::

  >>> v.enable_autocuts('on')

.. note:: Corresponds to the viewer setting ``autocuts``.

Enable auto zoom (scale to fit new image to window)::

  >>> v.enable_autozoom('on')

.. note:: Corresponds to the viewer setting ``autozoom``.

The autocenter, autocuts, and autozoom settings allow the following
values:

* 'on': apply to every new image
* 'once': apply to the first image set only, then turn 'off'
* 'override': apply to each image until the user overrides manually,
  then turn 'off', and
* 'off': never apply
  

Miscellaneous Operations
========================

Set the background color of the viewer::

  >>> v.set_bg(0.2, 0.2, 0.2)

.. note:: Corresponds to the viewer setting ``color_bg``.

Set the foreground color of the viewer (used for some text overlays)::

  >>> v.set_fg(0.8, 0.9, 0.7)

.. note:: Corresponds to the viewer setting ``color_fg``.

Put a message onscreen for 2 seconds::

  >>> v.onscreen_message("Hello, world!", delay=2.0)

Get the last position of the cursor in data coordinates::

  >>> v.get_last_data_xy()
  (782.4466094067262, 2136.5)

Whether the viewer widget should take focus when the cursor enters the
window::

  >>> v.set_enter_focus(True)

.. note:: Corresponds to the viewer setting ``enter_focus``.
  
Get the bounding box of viewer extents (returns lower-left and
upper-right corners of the bounding box)::

  >>> v.get_limits()
  ((0.0, 0.0), (2272.0, 4273.0))

.. note:: Normally the limits are defined by an image that is loaded, if
   any. But they can also be overridden, as shown below.

Set explicit limits for the viewer::
  
  >>> v.set_limits(((250.0, 250.0), (2500.0, 2500.0)))

.. note:: Corresponds to the viewer setting ``limits``.
  
  
  
