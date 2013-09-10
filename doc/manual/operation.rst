+++++++++++++++++
General operation
+++++++++++++++++

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

Mouse operations are also modified by the keyboard buttons {\tt Shift}
and {\tt Ctrl}.  \emph{Shift-click} means to press \emph{and hold} the
{\tt Shift} key while clicking with left mouse button,
\emph{Shift-right-click} is the same using the right mouse button,
etc.
Some mouse-controlled operations in Ginga are initiated by a key stroke.
In these cases the key is pressed and released (not held), and then the
mouse is used to control the operation.  Such operations are either
terminated by releasing the mouse button (if the operation employs a
drag), clicking on the image or pressing the {\tt Esc} key (if not a
drag operation).

=========================
Loading a FITS image file
=========================

There are several ways to load a file into Ginga:

* Ginga supports drag-and-drop in a typical desktop environment, so
  you can simply drag and drop files from a graphical file manager such
  as the Mac finder or Linux nautilus onto the main FITS viewing pane to
  load the image.

* Another way is to invoke the FBrowser plugin, which opens in the Dialogs
  tab.  The plugin pane shows file and folder contents and allows
  navigation up and down the filesystem hierarchy by double-clicking on
  folder names.   Simply navigate to the location of the FITS file and
  double-click on the file name to load it.

* Use the {\tt Load Image} entry from the {\tt File} menu on
  the main menu bar at the top of the window.  This opens a standard file
  dialog popup window where you can navigate to the file you wish to load.

===================
Zooming and panning
===================

The display object used throughout most of the Ginga panels has built-in
support for zooming and panning.  Appendix \ref{app:mousekbdref} has the
complete listing of default keyboard and mouse bindings.  
Briefly, the scroll wheel of the mouse can be used to zoom in and out,
along with the {\tt +} and {\tt -} keys.  The backquote key will fit the
image to the window.  Digit keys ({\tt 1, 2}, etc) will zoom in to the
corresponding zoom level, while holding Shift and pressing a zoom key
zooms out to the corresponding level.

When zoomed in, panning is enabled.  Panning takes two forms.
\emph{Free panning} allows scrolling around the entire image by mapping
the entire image boundaries to the window boundaries.  For example,
moving the mouse to the upper right-hand corner of the window will pan to
the upper right hand corner of the image, etc.  There are two ways to
initiate a free pan: Scroll-dragging (pressing the mouse scroll wheel
and dragging) or press and release {\tt q} and then Left-drag.
\emph{Proportional panning} or "drag panning" pans the image in direct
proportion to the distance the mouse is moved; a common idiom is
dragging the image canvas in the direction you want to move it under the
window.  To utilize a proportional pan, Ctrl-drag the canvas.  The Pan
plugin (usually embedded under the {\tt Info} tab) shows the outline of
the current pan position as a rectangle on a small version of the whole
image.  Dragging this outline will also pan the image in the main window.

Panning in Ginga is based on an (X, Y) coordinate known as the 
\emph{pan position}.  The pan position determines what Ginga will 
try to keep in the middle of the window as the image is zoomed.  
When zoomed out, one can Shift-click on a particular point in the image
(or press the {\tt p} key while hovering over a spot),
setting the pan position.  Zooming afterward will keep the pan
position in the center of the window.

Ginga has an auto zoom feature to automatically fit newly loaded images
to the window, similar to what happens when the backquote key is
pressed.  See section \ref{pref:zoomnew} for details.

==================
Setting cut levels
==================

When visualizing pixel data with an arbitrary pixel value range, the
range is mapped into a bytescaled range spanning from black to white
based on the low and high \emph{cut levels} defined in the view object.
These cut levels can be set manually by the user or automatically based
on a selection of algorithms supported by the view.

Manually setting cut levels
===========================

There are several ways to manually set the cut levels:

* The "Cut Low" and "Cut High" boxes in the Info plugin panel
  can be used.  The current values are shown to the left; simply type a
  new value in the corresponding box and press Enter or click the "Cut
  Levels" button below.

* Pressing and releasing the less than ({\tt \textless}) or greater than
  ({\tt \textgreater}) key
  will invoke an interactive cut levels, for the low and high value
  respectively.  After releasing the key, click and drag the mouse
  horizontally in the window to interactively set the level--when you
  reach the desired level, release the mouse button.

* Pressing and releasing the period ({\tt \.}) key will invoke a 
  dual (high and low) interactive cut levels.  After releasing the key,
  click and drag the mouse horizontally in the window to interactively
  set the high level, and vertically to set the low level--when you
  reach the desired levels, release the mouse button.

Automatically setting cut levels
================================

Ginga can algorithmically estimate and set the cut levels--a so called
"auto (cut) levels".  To activate the auto levels:

* Click the "Auto Levels" button in the Info plugin panel, or

* Press the ({\tt a}) key when the viewing widget has the focus.

The auto cut levels feature is controlled by several factors in the
preferences, including the choice of algorithm and some parameters to
the algorithm.  See section \ref{sec:autocuts} for details.
Ginga can also automatically set the cut levels for new images displayed
in the view.  See section \ref{pref:cutnew} for details.

==========================
Manipulating the color map
==========================

TBD
