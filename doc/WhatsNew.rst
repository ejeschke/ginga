++++++++++
What's New
++++++++++

Ver 5.0.1 (2024-03-31)
======================
- Fixed an issue where --modules option did not start a global plugin
  automatically
- Improved error checking on contains_pts() method for canvas items
- Removed references to distutils module, deprecated in python 3.12
- Added default antialiasing to cairo renderer
- Fixed drawing of dimension labels for rectangles specified in WCS
  coordinates
- Fixed drawing of Crosshair canvas object in opengl backend
- Fixed drawing of XRange and YRange in non-data coordinates

Ver 5.0.0 (2024-02-24)
======================
- Add Contrast and Brightness adjustments in "Preferences" plugin
- Modifications to PIL backend

  - support pillow v10.0
  - now supports linewidth attribute

- Add support for VizieR catalog sources
- Fixed an issue with programatically setting selections in TreeView
  (qt backend)
- Added a quit confirmation dialog to the reference viewer
  (can be overridden with a setting in general.cfg)
- Fix for mouse scrolling in histogram plot via Histogram plugin
- Fix for ScreenShot plugin with pyside6, qt6 backends
- Fix for context menu pop up in pyside2
- Fix for a logger annoyance message when mousing over far edge of image
- Updates for deprecations in numpy 2.0
- Fix for missing menubar on some versions of Qt and Mac OS X
- Fix for importing mpl colormaps with recent versions of matplotlib
- Fix for utcnow(), deprecated in Python 3.12
- Renamed mode "freepan" to "zoom" (bindings and activation are the
  same as before) to better reflect what the mode does
- Changed icons and cursors from PNG (bitmap) to SVG (vector) format
- Added color distribution ("stretch") control to Info plugin
- Added LoaderConfig plugin; allows setting of loader priorities for
  various MIME types
- Fixed an issue with the "none-move" event, affected Crosshair plugin
  and "hover" event on canvas items
- Added an internationalization framework (see "Internationalization"
  chapter in the Ginga manual).  Not yet enabled for reference viewer
- Added button in Toolbar plugin to activate cmap (colormap) mode
- Added mode help; type 'h' in the viewer window when you are in a mode
  to display a help tab for that mode (reference viewer only)
- Better support for touchpad gestures in modes
- Better support for RGB files

  - Support additional types (ico/icns/tga/bmp)
  - RGB video files can be opened (with OpenCv loader) and examined with
    MultiDim plugin or naxis mode (video frames is treated as axis 3)

- Added PluginConfig plugin; allows configuration of all Ginga plugins
  graphically; can enable/disable, change menu categories, etc.
- Removed --profile and --debug command-line options
- Fix a number of issues with the help system to make it simpler and
  more robust; removed WBrowser plugin, handle URLs with Python webbrowser
  module
- Number of threads can be configured in general settings file
- Fixes to various examples for third-party package changes
  (particularly matplotlib backend examples)
- Fixes for event handler treatment of return boolean values

Ver 4.1.0 (2022-06-30)
======================
- change implementation of splash banner to a pop-up modal dialog
  with version string
- fixed menubar integration on Mac OS X
- fixed an issue with auto cuts saved parameters not being loaded
  correctly
- fixed an issue with certain auto cuts methods not getting enough
  samples when the image size is very small
- removed old, deprecated StandardPixelRenderer
- RGB mapping has been refactored to use a pipeline
- Removed deprecated preload feature
- Fix for focusing plugins that have no GUI
- Added feature to reset viewer attributes between images (can be
  used synergistically with the "remember" feature). See "Reset (Viewer)"
  and "Remember (Image)" settings in the "Preferences" plugin.
- Fixed bug with pg backend loading icons
- Pick plugin settings now has options to set the autozoom and autocuts
  settings for the "Image" and "Contour" viewers (see "plugin_Pick.cfg"
  file in .../ginga/examples/configs)
- Fixed an issue with readout of values under the cursor when an image
  is plotted at a non-zero origin

Ver 4.0.1 (2022-12-27)
======================
- fixed a DeprecationWarning with jupyterw back end
- fixed a bug for Toolbar plugin that prevented N-E and N-W orientation
  from working as well as contrast restore
- fixes a bug in exporting ginga canvas objects to astropy regions objects
  and the test suite for it

Ver 4.0.0 (2022-12-20)
======================
- fixed getattr functionality in Bunch
- removed the "mock" backend; use "pil" backend for similar purposes
- fixed a longstanding issue where events registered on a canvas could
  be masked by default key/cursor bindings (not associated with a mode).
  This meant, for example, that only certain keystrokes could be
  captured by an event handler registered on a ginga canvas, because any
  keystrokes that had a default binding would take precedence.
  Now such bindings are only executed if the event is not handled by any
  active canvas bindings.
- Removed the "Quick Mode" and "From Peak" options in the Pick plugin
  to simplify operation.
- Many deprecated camelcase (non-PEP8) methods were removed. Use the
  "snake-case" names instead.
- Fixed an issue with setting the scale manually in the Preferences plugin
- Fixed a bug that can cause an incorrect cropping of image when the window
  is resized
- Refactor modes from Bindings module into separate modules:

  - modes can now be written and understood as having a very similar
    structure to a plugin.
  - mode docstrings can be written and maintained better to document the
    modes and the code implementing a mode is much easier to understand
    since it is encapsulated rather than all mixed together in one huge
    file.

- Added an AutoLoad plugin that can monitor a folder for new files and
  load them.
- Fixed a bug in the Overlays plugin where the overlay value was
  reported as the value under the cursor rather than the data value
- Fixed an issue with loading RGB images with opencv-python
- Fixed an issue where manual cut levels changes weren't reflected in
  the Thumbs icon
- ScreenShot now correctly captures the background color of the viewer
- Fixed a DeprecationWarning related to use of entry points
- File loaders are now discoverable under the "ginga_loaders" entry point.
  Loaders can be registered for MIME types and a ``mime.types`` file can be
  added to your ``$HOME/.ginga`` to identify types by file extension.
- ColorMapPicker plugin can now be launched as a local or global plugin

Ver 3.4.0 (2022-06-28)
======================
- Added start_server option to RC plugin configuration; can configure
  whether ginga should start the remote control server when the plugin
  starts or not
- fixed an error with auto-orientation of RGB images loaded with OpenCv
- fixed a bug where get_channel_on_demand() would throw an error if the
  channel already exists
- fixed a bug in ingesting the metadata (header) of RGB images
- added support for backends pyqt6 and pyside6; removed support for
  pyqt4 and pyside
- fix for a bug in ICC profiling with temp file creation
- new option in Collage plugin to select more accurate (but slower)
  mosaicing using the 'warp' method
- fixed an issue with numpy floats and drawing lines and ploygons with
  the Qt backend
- add option for suppressing FITS verify warnings when opening files
  using astropy.io.fits
- worked around a bug in recent versions of aggdraw (for "agg" backend)
  that caused problems for drawing ellipses
- added ability to read and write astropy-regions shapes in the Drawing
  plugin

Ver 3.3.0 (2022-02-16)
======================
- Fixed an issue with image rotation when OpenCv is installed
- Removed support for OpenCL
- Fixed Crosshair plugin to update the plot when image changes in
  channel
- Fixed an issue where a thumbnail could be generated even if the
  channel was configured not to generate thumbs
- Fixed an issue where wcs_world2pix() was called instead of all_world2pix()
  if wcs_astropy was used.  This may have affected graphic overlays
  plotted in ra/dec instead of pixels.
- Closing the reference viewer now stops all plugins first
- Fix to RC plugin for better error handling if another process is using
  the port
- Fixed a bug where using the fitsio loader the primary header was not
  set correctly in some instances
- Additions to the "pg" backend to add functionality already in the Qt
  and Gtk backends
- Fixed a bug with writing FITS files when using fitsio wrapper
- Fixed a bug where creating a new workspace did not set the correct
  workspace type that was selected in the drop down menu
- Updated pg widgets web backend due to changes to Tornado asyncio handling
- Changes to 'histogram' and 'stddev' autocuts algorithms:
  
  - choice of sampling by grid now; useful for mosaics and collages
  - for previous parameter of usecrop=True, use sample=crop
    
- Moved loading of FITS HDUs from AstroImage to io_fits module,
  encapsulating the details of this file format into the module
  responsible for loading those files:

  - added loading of FITS tables via the fitsio package in io_fits
  - TableView can now view tables loaded with either astropy or fitsio
  - inherit_primary_header in general.cfg now defaults to True and
    actually controls the behavior of always saving the primary header
    if set to False

- Fixed a rounding bug in displaying sexagesimal formatted coordinates:

  - deprecated ginga.util.wcs.{raDegToString,decDegToString}
  - use ginga.util.wcs.{ra_deg_to_str,dec_deg_to_str} instead

- Fixed an issue where the Catalogs plugin would not start correctly if
  astroquery was not installed
- The keywords ``save_primary_header`` and ``inherit_primary_header`` in
  the ``AstroImage`` constructor are deprecated. Use these same keywords
  in ``AstroImage.load_hdu()`` or ``AstroImage.load_file()`` methods
  instead. Several other methods in ``AstroImage`` are deprecated as
  well; they were previously pending deprecation.
- Fixed an issue where image might not be redrawn properly if scale or
  pan is set directly via a viewer's settings object (not the usual case)

Ver 3.2.0 (2021-06-07)
======================
- Minimum supported Python version is now 3.7
- Fixed some numpy deprecation warnings with numpy 1.19.0
- Canvas shapes can now be copied
- Added an option to make a copy of existing shape in Drawing plugin
- Added an option to make a copy of existing cut in Cuts plugin
- Added new iqcalc_astropy module to handle FWHM fitting and source finding
  using astropy and photutils
- Added new calc_fwhm_lib configuration item to let Pick switch between
  iqcalc and iqcalc_astropy
- Fixed a bug where certain plots were not cleared in Pick plugin
- Removed support for matplotlib versions < 2.1
- Added bicubic and bilinear interpolation methods to OpenGL backend
- Fixed a bug where the FWHM labels in the plot didn't match report
  values in the Pick plugin
- Fixed a bug in gtk/cairo backend where paths were not drawn correctly
- Included a couple of additional bundled fonts to improve legibility of
  small text
- Fixed a bug in PixTable that reversed pixel indices on display
- Added box sum and median results to PixTable; also improved statistics
  display
- Fixed an issue for the Tk Ginga widget if PIL.ImageTk was not
  installed
- Changed splitter widget so that the "thumbs" have a visual indicator
- Fixed an issue with cursor warp in free panning with Gtk3 backend
- Fixed an issue where the cursor was not changed from the default
- Fixed Pick plugin to autozoom the pick and contour images
- Fixed an issue where Thumbs plugin might not show initial thumb(s)
  when main window is enlarged to certain sizes
- Added "orientation" setting to orientable plugins
- Enhancements to Histogram plugin: ability to click in plot to set low
  and high cuts levels, scroll plot to expand or contract cuts width
- Crosshair plugin enhanced to have fast X/Y cuts plot feature;
  cuts plot removed from Pick plugin
- Fixed an issue where the Pick plugin would not start due to a change
  to matplotlib canvas initialization
- Updates to Catalogs plugin:

  - new astronomical object lookup section for SIMBAD or NED
  - new ability to specify some astroquery catalog and image sources
    in the `plugins_Catalogs.cfg` configuration file
  - *API not compatible with previous releases, including configuration
    via `ginga_config.py`*
  
Ver 3.1.0 (2020-07-20)
======================
- Zoom and Pan plugins refactored. Now shows graphical overlays.
- Improved performance of rendering when flipping, swapping axes or
  rotating viewer.
- Fixed a bug where the display was not redrawn if an ICC profile was
  changed
- Fixed bugs relating to drawing XRange, YRange and Rectangle objects on
  rotated canvas
- Fixed a bug with fit image to window (zoom_fit) which was off by half
  a pixel
- Fixed an issue where an error message appears in the log if the scale
  is so small the image is invisible
- Fixed an issue where the readout under the cursor for value is
  reported for an empty row to the left and column below of pixels
- Removed dependence on astropy-helpers submodule.
- Fixed an issue where limits were not reset correctly if image being
  viewed is modified in place (and data array changes size)
- Fixed an issue with Mosaic plugin where images with a PC matrix were
  not always oriented correctly
- New Collage plugin offers an efficient alternative way to view mosaics
- Fix for a bug where using Zoom and PixTable at the same time can cause
  wrong results to be displayed in PixTable
- New ability to specify alternative Ginga home directories, with custom
  layouts and plugin configurations (--basedir option)
- Fix for a bug that caused a crash when closing the Help window with
  Qt/PySide backend

Ver 3.0.0 (2019-09-20)
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
- new styles added for Point canvas type: circle, square, diamond,
  hexagon, uptriangle, downtriangle
- New file opener framework
- Text objects can be resized and rotated in edit mode on the canvas
- Added ellipse and box annulus types as Annulus2R canvas object
- Supports plotting DS9 regions via 2-way conversion between Ginga canvas
  types and Astropy regions

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
