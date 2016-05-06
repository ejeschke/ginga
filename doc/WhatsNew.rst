++++++++++++++++++++
What's New in Ginga?
++++++++++++++++++++

Ver 2.2.20160505170200
======================
Ginga has merged the astropy-helpers template.  This should make it more
compatible management-wise with other astropy-affiliated packages.

Ver 2.2.20150203025858
======================
Ginga drawing canvas objects now can specify points and radii in world
coordinates degrees and sexigesimal notation.

- default is still data coordinates
- can play with this from Drawing plugin in reference viewer

Ver 2.1.20141203011503
======================
Major updates to the drawing features of ginga:

- new canvas types including ellipses, boxes, triangles, paths, images
- objects are editable: press 'b' to go into edit mode to select and
  manipulate objects graphically (NOTE: 'b' binding is considered
  experimental for now--editing interface is still evolving)
- editing: scale, rotate, move; change: fill, alpha transparency, etc.
- editing features available in all versions of the widget
- updated Drawing plugin of reference viewer to make use of all this

Ver 2.0.20140905210415
======================
Updates to the core display and bindings classes:

- improvements to interactive rotation command--now resume rotation from
  current value and direction is relative to horizontal motion of mouse
- most keyboard modes are now locking and not oneshot (press to turn on,
  press again (or hit escape) to turn off
- additional mouse button functionality in modes (see quick reference)
- some changes to default keyboard bindings (see quick reference)
- changes to auto cuts parameters always result in a new autocut being
  done (instead of having to explicity perform the autocut)--users seem
  to expect this
- autocenter preference changed from True/False to on/override/off

Reference viewer only: new global plugin "Toolbar" provides GUI buttons
for many operations that previously had only keyboard bindings

Ver 2.0.20140811184717
======================
Codebase has been refactored to work with python3 via the "six" module.
Tests can now be run with py.test as well as nosetest.


Ver 2.0.20140626204441
======================
Support has been added for image overlays.  It's now possible to overlay
RGB images on top of the canvas.  The images scale, transform and rotate
wrt the canvas.


Ver 2.0.20140520035237
======================
Auto cut levels algorithms have been updated.  "zscale" has been
reinforced by using the module from the "numdisplay" package, which does
a fair sight closer to IRAF than the previous one Ginga was using.
Also, the algorithm "median" (median filtering) makes a comeback.  It's
now fast enough to include and produces more usable results.


Ver 2.0.20140417032430
======================
New interactive command to orient the image by WCS to North=Up.  The
default binding to 'o' creates left-handed orientation ('O' for
right-handed).  Added a command to rotate the image in 90 deg
increments.  Default binding to 'e' rotates by 90 deg ('E' for -90
deg).


Ver 2.0.20140412025038
======================
Major update for scale (mapping) algorithms

The scale mapping algorithms (for mapping data values during rendering)
havebeen completely refactored.  They are now separated from the RGBMap
class and are pluggable.  Furthermore I have redone them modeled after
the ds9 algorithms.

There are now eight algorithms available: linear, log, power, sqrt, squared,
asinh, sinh, histeq.  You can choose the mapping from the Preferences plugin
or cycle through them using the binding to the 's' key (Use 'S' to reset to
linear).  There is also a mouse wheel mapping than can be assigned to
this function if you customize your bindings.  It is not enabled by default.

The Preferences plugin has been updated to make the function a little
clearer, since there was some confusion also with the intensity map feature
that is also part of the final color mapping process.


Ver 2.0.20140114070809
======================

- The SAMP plugin has been updated to work with the new astropy.vo.samp
  module.
- The Catalogs plugin has been updated to allow the user to define the
  radius of the conesearch or image search by drawing a circle (as well as
  the previous option--a rectangle).

Ver 2.0.20131218034517
======================
The user interface mapping just got a bit easier to use.  Ginga now
provides a way to do most UI remapping just by placing a simple config
file in your ~/.ginga directory.  An example for ds9 users is in the
new "examples" folder.

Many simple examples were moved out of "scripts" and stored under
subdirectories (by GUI toolkit) in "examples".


Ver 2.0.20131201230846
======================
Ginga gets trackpad gestures!  The Qt rendering class gets support for
pinch and pan gestures:

* The pinch/rotate gesture works as expected on a Mac trackpad
* The pan gesture is not a two-finger pan but a "non-standard", Qt-specific
  one-finger pan.  These are experimental for now, but are enabled by
  default in this release.

Also in this release there has been a lot of updates to the
documentation.  The developer and internals sections in particular have
a lot of new material.


Ver 2.0.20131030190529
======================
The great renaming

I really dislike it when developers do this, so it pains me to do it now,
but I have performed a mass renaming of classes.  FitsImage ended up being
the View in the MVC way of doing things, yet it shared the same naming
style as the model classes AstroImage and PythonImage.  This would have
been the source of endless confusion to developers down the road.  Also,
PythonImage needed to get renamed to something more akin to what it
actually represents.

So the renaming went like this:

* FitsImage -> ImageView
* FitsImage{XYZ} -> ImageView{XYZ}
* PythonImage -> RGBImage

So we have:

* M: BaseImage, AstroImage, RGBImage
* V: ImageView{XYZ}
* C: Bindings, BindMap

I did this in the brand new 2.0 version so at least devs have a heads up
that things will not be backward compatible.

And I apologize in advance for any renaming and support issues this may
cause for you.  Fire up your editor of choice and do a query/replace of
"FitsImage" with "ImageView" and you should be good to go.


Ver 1.5-20131022230350
======================
Ginga gets a Matplotlib backend!

Ginga can now render to any Matplotlib FigureCanvas.  The performance using
this backend is not as fast as the others, but it is acceptable and opens
up huge opportunities for overplotting.

See scripts/example{1,2,3,4,5}_mpl.py

Also merges in bug fixes for recent changes to astropy, and support for
other python WCS packages such as kapteyn and astLib.


Ver 1.5-20130923184124
======================

Efficiency improvements
-----------------------
Efforts to improve speed of entire rendering pipeline and widget
specific redrawing

* Decent improvements, Ginga can now render HD video (no sound) at 30
  FPS on older hardware (see scripts/example1_video.py).  This
  translates to a slightly speedier feel overall for many operations
  viewing regular scientific files.
* Fixed a bug that gave an error message of
  Callback.py:83 (make_callback) | Error making callback 'field-info':
  'Readout' object has no attribute 'fitsimage'

* Version bump


Ver 1.4.20130718005402
======================

New Agg backend
---------------
There is now an Agg rendering version of the ImageView object.

* uses the python "aggdraw" module for drawing; get it here  -->
  https://github.com/ejeschke/aggdraw
* this will make it easy to support all kinds of surfaces because the
  graphics drawing code does not have to be replicated for each
  toolkit
* see example code in /scripts/example1_agg_gtk.py
* currently not needed for Gtk, Qt versions of the object

New Tk backend
--------------
There is now a Tk rendering version of the ImageView object.

* see ginga.tkw.ImageViewTk
* renders on a Tk canvas
* see example code in /scripts/example{1,2}_tk.py
* you will need the aggdraw module (see above) to use it

AutoCuts
--------

* the ginga.AutoCuts module has been refactored into individual classes
  for each algorithm
* The Preferences plugin for ginga now exposes all of the parameters
    used for each cut levels algorithm and will save them

Etc
---

* additions to the manual (still incomplete, but coming along)
* lots of docstrings for methods added (sphinx API doc coming)
* many colors added to the color drawing example programs
* WhatsNew.txt file added
