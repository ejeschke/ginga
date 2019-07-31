++++++++++
What's New
++++++++++

Ver 3.0.0 (unreleased)
======================
- Dropped Python 2 support. Ginga now requires Python 3.5 or later.
- Fixed an issue with some RGB images being viewed flipped
- Improved accuracy of Qt-based timers
- Pick plugin enhanced with option to center on found object; also
  default shape changed to a box rather than a rectangle
- Added support for ASDF and GWCS.
- Fixed drag-and-drop functionality in FBrowser plugin on Windows.
- Enabled HDU sorting via config file in MultiDim.
- Fixed a bug where display would get corrupted when adjusting
  interactive cuts or contrast on rotated image
- Improved smoothness and updates of Zoom plugin image
- Improved smoothness and updates when rotating or shifting color map
- Fixed broken banner
- Improved ``pip`` installation commands for different backends.
- Fixed a bug where identically named HDUs could not be loaded by MultiDim
- Fixed a bug where compressed HDUs could not be loaded by MultiDim
- Plugins with splitter type panels now remember their sizes when closed
- LineProfile plugin's default Y-axis label is now "Signal", to be more
  scientifically accurate.
- Simplified plugins Colorbar, Contents, Cursor, Errors, Header, Info,
  Log, Pan, and Thumbs plugins.  Made all of these restartable.
  Subclasses of these plugins may require refactoring in a couple of cases.
- Selecting item in FBrowser now populates its text box properly.
- Support opening all extensions of given extension name from
  a FITS file (e.g., ``filename.fits[SCI,*]``) from Ginga command
  line or FBrowser.
- New Downloads plugin for monitoring/managing URI downloads
- Supports PySide2 (alternative Qt5 backend)
- Added statistics line to Histogram plugin
- Removed support for gtk2, since it is not supported for Python 3

Ver 2.7.2 (2018-11-05)
======================
- Fix for linewidth attribute in shapes for AGG backend
- Fix for ellipse rotation in OpenCv backend
- Better text rendering for OpenCv backend (loadable fonts)
- enhancements to the Ruler plugin for reference viewer
- supports quick loading from astropy NDData (or subclassed) objects
- Support for scaling fonts on high-dpi displays
- Fixed a bug where adjusting autocuts parameters in Preferences would
  crash the Qt backend
- Fixed a bug that caused windows to disappear when changing workspace
  to MDI mode under Gtk3 backend
- Fixed a bug where local plugins were not properly closed when a
  channel is deleted
- Fixed a bug in which the ColorMapPlugin canvas was not scaled to the
  correct size
- Improvements to synchronous refresh feature to reduce jitter and
  increase frame rate
- Fix for navigating certain data cubes with MutltiDim plugin
- Added new percentage transform and coordinate mapper type (allow
  placement of objects as a percentage of the window size)
- Updates to Compass canvas type and Pan plugin
- Documentation improvements for writing plugins

Ver 2.7.1 (2018-07-09)
======================
- Fix for image rendering bug which shows last row and column of image
  being drawn twice
- Added option to "Compass" draw type to be in pixels (X/Y) or wcs (N/E)
- Changed Pan plugin to attempt to draw both kinds of compasses
- Log plugin enhanced to show lines logged before it was opened
- Info plugin adds convenience controls for "Follow New" and "Raise New"
- WCSMatch plugin enhanced to offer fine grained control over sync
- fixed an issue in Debian build that caused long start up times
- User can dynamically add scrollbars to channel viewers in Preferences
- Made Gtk backend default to 'gtk3'
  - "-t gtk" now invokes gtk3 instead of gtk2
  - choose "-t gtk2" if you want the gtk2 back end
- Fixed a bug with opening wildcard-type filespec from the command line
- Fixed an issue in Thumbs plugin with opening FITS tables from the
  command line
- Fixes for some keyboard focus (Gtk) and unintentional channel changes
  (Qt) when viewer is in MDI mode
- IRAF plugin moved to experimental folder
- Allow setting of initial channel list, local, global and disabled
  plugins from general configuration file
- Fix for a bug when using OpenCv acceleration on dtype('>f8') arrays
- Fixed a bug where colormap scale markers were sometimes not spaced
  wide enough
- Workaround for failed PDF build in RTD documentation

Ver 2.7.0 (2018-02-02)
======================
- Fix for gtk 4.0 (use "gtk3" backend, it works for 4.0)
- Fix for broken polygon containment test
- Addition of configurable zoom handlers for pan gestures
- Fix for some broken tests under python 2.7
- Update to mode handling via keyboard shortcuts

  - addition of a new "meta" mode used primarily for mode switching
  - most modes now initiated from meta mode, which frees up keys
    for other uses
  - see Ginga quick reference for details on how the new bindings work

- Efficiency update for Thumbs plugin when many thumbs are present
- Default for the save_layout option is now True, so the reference
  viewer will write out its layout state on exit and restore it on
  startup.  See documentation in the "customization" section of the
  manual.
- Plugins can now be organized by category and these categories are
  used to construct a hierarchical Operations menu
- Zoom and Header plugins are now not started by default
- Fix for "sortable" checkbox behavior on Header plugin
- Default keyboard mode type is now 'locked' (prev 'oneshot')
- Fixes for missing CSS file in installation script
- Less confusing behavior for workspace and toolbar arrow buttons

Ver 2.6.6 (2017-11-02)
======================
- Fix for broken sorting in Contents plugin in gtk backends
- Fix for resize bug in switching in and out of grid view in gtk
  backends
- Updated to have efficient support for gtk3

  - please install compatible pycairo from github.com/pygobject/pycairo
    if you get a "Not implemented yet" exception bubbling up from a
    method called cairo.ImageSurface.create_for_data()

- Addition of a "Quick Mode" to the Pick plugin--see documentation
- More consistent font handing between widgets and Ginga canvases
- Bug fix for importing some types of matplotlib color maps
- Add antialiasing for Qt back end
- Bug fixes and enhancements for Qt gestures
  - holding shift with pinch now keeps position under cursor
- New Jupyter notebooks back end based on ipywidgets
  - requirements: $ pip install ipyevents
  - see examples/jupyter-notebook/
- Fixes to various reference viewer plugins

Ver 2.6.5 (2017-07-31)
======================
- Coordinate transforms refactored for speed and code clarity
- Some canvas shapes refactored for better code reuse
- Allow max and min scale limits to be disabled (by None)
- Fixed a bug that prevented the reference viewer from resizing
  correctly with Qt back end
- Refactored WCS wrapper module for code clarity
- Set minimum astropy version requirement to 1.X
- Fixed a bug in NAXIS selection GUI (MultiDim plugin)
- Fixed MDI window resizing with Gtk back ends
- Fixed an error where zoom 100% button did not correctly zoom to 1:1 scale
- Several fixes for astropy 2.0 compatibility
- Fixed a bug in the FBrowser plugin when channel displaying a table
  and attempting to load a new file
- Fixed a bug when setting the pan position manually by wcs coordinates
- Updates for changes in PIL.ImageCms module
- Fix for window corruption on certain expose events
- New default bindings for touch pads and differentiation from wheel zoom

Ver 2.6.4 (2017-06-07)
======================
- Added new ScreenShot plugin to take PNG/JPEG snaps of the viewer
  window
- Enhancements to the Pick plugin

  - Added ability to make shapes besides rectangles for enclosing pick area.
    Masks out unwanted pixels.  Choose the shape in the Settings tab.
  - Changed behavior of pick log to only write the log when the user clicks
    the save button.
  - Changed the name of the save button to "Save as FITS table" to make it
    clear what is being written.
  - If "Show candidates" is selected in Settings, then ALL of the candidates
    are saved to the log.
  - Added documentation to the manual
  - Bug fix for error when changing radius

- Improvements to layout of Operations menu (plugin categories)
- Colorbar scale now placed below the color wedge and is more legible
- Bug fixes for LineProfile plugin
- Slit function for Cuts plugin can be enabled from GUI
- Bug fixes for Slit function
- Info plugin can now control new image cut/zoom/center settings
- Fixed an issue with the MultiDim plugin that could result in a hang
  with some back ends
- New canvas type for displaying WCS grid overlay and new WCSAxes plugin
  that uses it
- Bug fixes to scrolling via scrollbars and vert/horiz percentages
- Enhancements to the LineProfile plugin

  - several new shapes besides the standard point
  - plot multiple lines

Ver 2.6.3 (2017-03-30)
======================
- Fix for issue that stops ginga startup when loading externally
  distributed plugins that have errors
- Fix for an issue loading plugins from the command line when they
  are nested in a package
- Added bindings for moving +/- pixel delta in X or Y and centering on the
  pixel
- Fixes for some key mappings for tk, matplotlib and HTML5 canvas backends
- Fixes for IRAF plugin under python 3
- Fix for a bug using remote control (RC) plugin from python2 client to
  python 3 ginga
- Documentation updates

Ver 2.6.2 (2017-02-16)
======================
- Added some colormaps from ds9 that don't have equivalents in Ginga or
  matplotlib
- Fix for recognizing CompImage HDU type when using astropy.io.fits
- Add new experimental OpenGL back end
- Fixes for Tk back end on python 3
- You can now write separately distributed and installable plugins for
  the reference viewer that Ginga will find and load on startup
- Added --sep option to load command line files into separate channels
- New help screen feature available for plugins
- Lots of updates to documentation
- Fixed a stability issue with drag and dropping large number of files
  under Linux
- Fixes for python3 and several example programs
- Fix for interactive rotation bug under matplotlib back end

Ver 2.6.1 (2016-12-22)
======================
- Added a working MDI workspace for gtk2/gtk3.
- Added scrollbar frames.  See examples/qt/example1_qt.py for standalone
  widget.  Can be added to reference viewer by putting 'scrollbars = "on"'
  in your channel_Image.cfg preferences.
- Reorganized reference viewer files under "rv" folder.
- Improved Pick plugin: nicer contour plot, pick log uses table widget,
  pick log saved as a FITS table HDU
- Pick and Zoom plugins can now use a specific color map, rather than
  always using the same one as the channel window
- gtk3 reference viewer can now be resized smaller than the original
  layout (gtk2 still cannot)
- added ability to save the reference viewer size, layout and position
  on screen
- gtk MDI windows now remember their size and location when toggling
  workspace types
- Fixes for problems with pinch and scroll gestures with Qt5 backend
- Fixed a bug where scale changes between X and Y axes unexpectedly at
  extreme zoom levels
- Fixed a bug where cursor could get stuck on a pan cursor
- Added ability to define a cursor for any mode
- Added documented virtual methods to ImageView base class
- Added a workaround for a bug in early versions of Qt5 where excessive
  mouse motion events accumulate in the event queue

Ver 2.6.0 (2016-11-16)
======================
With release 2.6.0 we are moving to a new versioning scheme that makes
use of github tagged releases and a "dev" versioning scheme for updates
between releases.

This release includes many bugfixes and improvements, new canvas types
(XRange and YRange), a Command plugin, WCSMatch plugin, dynamically
configurable workspaces, OpenCv acceleration, an HTML5 backend and much
much more.

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
