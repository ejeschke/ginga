+++++++++++++++++
General operation
+++++++++++++++++

This chapter describes general manipulations of images using Ginga.  For
the most part these apply both to Ginga ImageView classes that can be
embedded in a python application as well as to the reference viewer
distributed with Ginga.  In cases where we are referring to something
that is only available in the reference viewer these will be prefixed by
the notation "[RV]".

===========
Terminology
===========

In this manual we will use the following terms to describe operations
with the mouse:

* *Click* or *Left-click* means to click on an item with
  the left mouse button;
* *Drag* or *Left-drag* means to click, hold and drag with
  the left mouse button;
* *Scroll* means to scroll with the middle mouse wheel;
* *Scroll-click* means to click with the middle mouse wheel/button;
* *Scroll-drag* means to click, hold and drag with the middle
  mouse wheel/button;
* *Right-click* means to click on an item with the right mouse
  button;
* *Right-drag* means to click, hold and drag with the right
  mouse button.

Mouse operations are also modified by the keyboard buttons *Shift*,
and *Ctrl*.  *Shift-click* means to press *and hold* the
Shift key while clicking with left mouse button,
*Shift-right-click* is the same using the right mouse button,
etc.
Some mouse-controlled operations in Ginga are initiated by a key stroke.
In these cases the key is pressed and released (not held), and then the
mouse is used to control the operation.  Such operations are either
terminated by releasing the mouse button (if the operation employs a
drag), clicking on the image or pressing the `Esc` key (if not a
drag operation).

.. note:: Key and mouse bindings can be changed completely by the user.
	  We describe the standard bindings here.  For more information
	  on changing the bindings, see Section :ref:`sec-bindings`.

=========================
Loading a FITS image file
=========================

There are several ways to load a file into Ginga:

* Ginga supports drag-and-drop in a typical desktop environment, so
  you can simply drag and drop files from a graphical file manager such
  as the Mac Finder or Linux Nautilus onto the main FITS viewing pane to
  load an image.

* [RV] Another way is to invoke the FBrowser plugin, which opens in the
  Dialogs tab.  The plugin pane shows file and folder contents and allows
  navigation up and down the filesystem hierarchy by double-clicking on
  folder names.   Simply navigate to the location of the FITS file and
  double-click on the file name to load it, or drag it onto the image pane.

* [RV] Use the "Load Image" entry from the `File` menu on the main menu
  bar at the top of the window.  This opens a standard file dialog popup
  window where you can navigate to the file you wish to load.

.. _zooming-and-panning:

===================
Zooming and panning
===================

The display object used throughout most of the Ginga panels has built-in
support for zooming and panning.  The :ref:`ginga-quick-reference` has the
complete listing of default keyboard and mouse bindings.
Briefly, the scroll wheel of the mouse can be used to zoom in and out,
along with the "+" and "-" keys.  The backquote key will fit the
image to the window.  Digit keys (1, 2, etc) will zoom in to the
corresponding zoom level, while holding Shift and pressing a zoom key
zooms out to the corresponding level.

When zoomed in, panning is enabled.  Panning takes two forms.
*Free panning* allows scrolling around the entire image by mapping
the entire image boundaries to the window boundaries.  For example,
moving the mouse to the upper right-hand corner of the window will pan to
the upper right hand corner of the image, etc.  There are two ways to
initiate a free pan: Scroll-dragging (pressing the mouse scroll wheel
and dragging) or press and release "q" and then Left-drag.
*Proportional panning* or "drag panning" pans the image in direct
proportion to the distance the mouse is moved; a common idiom is
dragging the image canvas in the direction you want to move it under the
window.  To utilize a proportional pan, Ctrl-drag the canvas.

[RV] The Pan plugin (usually embedded under the Info tab) shows the
outline of the current pan position as a rectangle on a small version of
the whole image.  Dragging this outline will also pan the image in the main
window.  You can also click anywhere in the Pan window to set the pan
position, or right drag an outline to roughly specify the region to zoom
and pan to together.

Panning in Ginga is based on an (X, Y) coordinate known as the
*pan position*.  The pan position determines what Ginga will
try to keep in the middle of the window as the image is zoomed.
When zoomed out, one can Shift-click on a particular point in the image
(or press the "p" key while hovering over a spot),
setting the pan position.  Zooming afterward will keep the pan
position in the center of the window.  To reset the pan position to the
center of the image, press 'c'.

Ginga has an auto zoom feature to automatically fit newly loaded images
to the window, similar to what happens when the backquote key is
pressed.  See section :ref:`preferences_zoom` for details.

================================
How Ginga maps an image to color
================================

The process of mapping an image to color in Ginga involves three
steps:

1) setting the *cut levels*, which scales all values in the image to a
   specified range,
2) a *color distribution algorithm*, which distributes values within
   that range to indexes into a color map table, and
3) an *intensity map* and *color map*, which are applied to these
   indexes to map the final values to RGB pixels.

.. _setting_cut_levels:

==================
Setting cut levels
==================

When visualizing pixel data with an arbitrary value range, the range is
first scaled into a limited range based on the low and high *cut levels*
defined in the view object.  These cut levels can be set manually by the
user or automatically based on an algorithm.

Manually setting cut levels
===========================

There are several ways to manually set the cut levels:

* Pressing and releasing the period ("s") key will put the viewer into
  "cuts" mode.  Here you can invoke a dual (high and low) interactive
  cut levels.  Click and drag the mouse horizontally in the window to
  interactively set the high level, and vertically to set the low
  level--when you reach the desired levels, release the mouse
  button. Scrolling the mouse wheel in this mode will also change the
  low and high cut levels simultaneously--toward or away from each
  other, resulting in lower or higher contrast.

* [RV] The "Cut Low" and "Cut High" boxes in the Info plugin panel
  can be used.  The current values are shown to the left; simply type a
  new value in the corresponding box and press Enter or click the "Cut
  Levels" button below.  Cut values can also be set from the "Histogram"
  plugin.

Automatically setting cut levels
================================

Ginga can algorithmically estimate and set the cut levels--a so called
"auto (cut) levels".  To activate the auto levels:

* Press the ("a") key when the viewing widget has the focus.

* [RV] Click the "Auto Levels" button in the Info plugin panel, or

[RV] The auto cut levels feature is controlled by several factors in the
preferences, including the choice of algorithm and some parameters to
the algorithm.  See section :ref:`preferences_autocuts` for details.
Ginga can also automatically set the cut levels for new images displayed
in the view.  See section :ref:`preferences_newimages` for details.

Setting the color scale algorithm
=================================

Ginga supports a number of color scale distribution algorithms,
including "linear", "log", "power", "sqrt", "squared", "asinh", "sinh"
and "histeq".  These can be sampled with the current color and intensity
maps by pressing the "d" key to go into "dist" mode, and then scrolling
the mouse.  To reset to the default ("linear") map, press "D" (capital D).

[RV] The color scale distribution algorithms can also be set from the
Preferences plugin, under the heading "Color Distribution".

Changing the color and intensity maps
=====================================

The color and intensity maps

===========================
Transforming the image view
===========================

Ginga provides several controls for transforming the image view.  The
image can be flipped in the X axis ("horizontally"), Y axis
("vertically"), have the X and Y axes swapped, or any combination
thereof.  These operations can be done by keyboard shortcuts:

* Press "[" to flip in X, "{" to restore.
* Press "]" to flip in Y, "}" to restore.
* Press "\" to swap X and Y axes, "|" to restore.

The image can also be rotated in arbitrary amounts.

An interactive rotate operation can be initiated by pressing "r" in the
image and then dragging the mouse horizontally left or right to set the
angle.  Press "R" (Shift+R) to restore the angle to 0 (unrotated).

.. note:: It is less computationally-intensive to rotate the image using
	  the simple transforms (flip, swap) than by the rotation
	  feature.  Rotation may slow down some viewing operations.

[RV] The image can also be transformed in the channel Preferences (see
:ref:`preferences_transform`) which has checkboxes for flip X, flip Y,
swap XY and a box for rotation by degrees.

