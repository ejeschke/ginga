.. _ginga-quick-reference:

+++++++++++++++++++++
Ginga Quick Reference
+++++++++++++++++++++

=================
Main image window
=================

These keyboard and mouse operations are available when the main image
window has the focus.

Mode control commands
=====================

About modes
-----------
Certain keystrokes invoke a *mode*--modes are usually indicated by a
small black rectangle with the mode name in one corner of the view.
In a mode, there are usually some special key, cursor and scroll bindings
which will override *some* of the default ones.

Modes additionally have a *mode type* which can be set to one of:

* `held`: mode is active while the activating key is held down
* `oneshot`: mode is released by initiating and finishing a cursor drag,
  or when `Esc` is pressed, if no cursor drag is performed
* `locked`: mode is locked until the mode key is pressed again (or `Esc`)
* `softlock`: mode is locked until another mode key is pressed (or `Esc`)

By default most modes are activated in "oneshot" type, unless the mode
lock is toggled.

+----------------------+--------------------------------------------------+
| Esc                  | Exit any mode.  Does not toggle the lock.        |
+----------------------+--------------------------------------------------+
| l                    | Toggle the soft lock to the current mode or any  |
|                      |   future modes.                                  |
+----------------------+--------------------------------------------------+
| L                    | Toggle the normal lock to the current mode or    |
|                      |   any future modes.                              |
+----------------------+--------------------------------------------------+

Panning and Zooming commands
============================

+----------------------+--------------------------------------------------+
| Scroll wheel turned  | Zoom in or out                                   |
+----------------------+--------------------------------------------------+
| Ctrl + Scroll wheel  | Adjust zoom by intermediate fine steps           |
|   turned             |                                                  | 
+----------------------+--------------------------------------------------+
| Shift + Scroll wheel | Zoom while keeping location under the cursor.    |
+----------------------+--------------------------------------------------+
| Digit                | Zoom image to zoom steps 1, 2, ..., 9, 10        |
| (1234567890)         |                                                  |
+----------------------+--------------------------------------------------+
| Shift + Digit        | Zoom image to zoom steps -1, -2, ..., -9, -10    |
+----------------------+--------------------------------------------------+
| Backquote (\`)       | Zoom image to fit window and center it           |
+----------------------+--------------------------------------------------+
| Minus, Underscore    | Zoom out                                         |
|    (-, \_)           |                                                  |
+----------------------+--------------------------------------------------+
| Equals, Plus         | Zoom in                                          | 
|    (=, +)            |                                                  |
+----------------------+--------------------------------------------------+
| Middle (scroll)      | Set pan position (under cursor)                  |
| button click         |                                                  |
+----------------------+--------------------------------------------------+
| p                    | Set pan position (under cursor) for zooming      |
+----------------------+--------------------------------------------------+
| Shift + Left click   | Set pan position for zooming                     |
+----------------------+--------------------------------------------------+
| c                    | Set pan position to the center of the image      |
+----------------------+--------------------------------------------------+
| q                    | Enter Pan mode. See Pan section.                 | 
+----------------------+--------------------------------------------------+
| w                    | Free Freepan mode. See Freepan section.          |
+----------------------+--------------------------------------------------+
| Ctrl + Left drag     | Proportional pan (press and drag left mouse      |
|                      |     button                                       |
+----------------------+--------------------------------------------------+
| slash (/)            | Set autocenter for new images to *override*      |
+----------------------+--------------------------------------------------+
| question (?)         | Toggle autocenter for images to *on* or *off*    |
+----------------------+--------------------------------------------------+
| apostrophe (')       | Set autozoom for new images to *override*        |
+----------------------+--------------------------------------------------+
| doublequote (")      | Toggle autozoom for new images to *on* or *off*  |
+----------------------+--------------------------------------------------+

Cut levels and colormap commands
================================

+----------------------+--------------------------------------------------+
| a                    | Auto cut levels                                  |
+----------------------+--------------------------------------------------+
| d                    | Enter Color Distribution ("dist") mode.          |
|                      |  See Dist section.                               |
+----------------------+--------------------------------------------------+
| D                    | Reset color distribution algorithm to "linear"   |
+----------------------+--------------------------------------------------+
| s                    | Enter Cuts mode. See Cuts section.               |
+----------------------+--------------------------------------------------+
| t                    | Enter Contrast mode. See Contrast section.       |
+----------------------+--------------------------------------------------+
| T                    | Restore the contrast (via colormap) to its       |
|                      |   original (unstretched, unshifted) state        |
+----------------------+--------------------------------------------------+
| y                    | Enter CMap (color map) mode.  See CMap section.  |
+----------------------+--------------------------------------------------+
| Y                    | Restore the color map to default (gray)          |
+----------------------+--------------------------------------------------+
| I                    | Invert the color map                             |
+----------------------+--------------------------------------------------+
| semicolon (;)        | Set autocuts for new images to *override*        |
+----------------------+--------------------------------------------------+
| colon (:)            | Toggle autocuts for new images to *on* or *off*  |
+----------------------+--------------------------------------------------+

Transform commands
==================

+----------------------+--------------------------------------------------+
| Left bracket ([)     | Toggle flip image in X                           |
+----------------------+--------------------------------------------------+
| Left brace ({)       | Reset to no flip of image in X                   |
+----------------------+--------------------------------------------------+
| Right bracket (])    | Toggle flip image in Y                           |
+----------------------+--------------------------------------------------+
| Right brace (})      | Reset to no flip image in Y                      |
+----------------------+--------------------------------------------------+
| Backslash (\\)       | Swap X and Y axes                                |
+----------------------+--------------------------------------------------+
| Vertical bar (|)     | Reset to no swap of X and Y axes                 |
+----------------------+--------------------------------------------------+
| r                    | Enter Rotate mode.  See Rotate section.          |
+----------------------+--------------------------------------------------+
| R                    | Restore rotation to 0 degrees and additionally   |
|                      |   undo any flip/swap transformations             |
+----------------------+--------------------------------------------------+
| period (.)           | Increment current rotation by 90 degrees         |
+----------------------+--------------------------------------------------+
| comma (,)            | Decrement current rotation by 90 degrees         |
+----------------------+--------------------------------------------------+
| o                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Left             |
+----------------------+--------------------------------------------------+
| O                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Right            |
+----------------------+--------------------------------------------------+

Pan mode
========

+----------------------+--------------------------------------------------+
| left drag            | Pan proportionally to drag                       |
+----------------------+--------------------------------------------------+
| middle click         | Set pan position                                 |
+----------------------+--------------------------------------------------+
| right drag           | Zoom in/out proportionally to L/R drag           |
+----------------------+--------------------------------------------------+
| <Modifier> +         | Pan in direction of arrow key. Adding Ctrl       |
|    arrow key         |   reduces amount, adding Shift reduces more.     |
+----------------------+--------------------------------------------------+
| p                    | Pan to position under cursor                     |
+----------------------+--------------------------------------------------+
| z                    | Save current scale (see below for use)           |
+----------------------+--------------------------------------------------+
| backquote            | Zoom to fit window and center                    |
+----------------------+--------------------------------------------------+
| 1                    | Pan to cursor and zoom to saved scale level      |
|                      |   (or 1:1 if no scale level saved)               |
+----------------------+--------------------------------------------------+
| c                    | Set pan position to the center of the image      |
+----------------------+--------------------------------------------------+
| slash (/)            | Set autocenter for new images to *override*      |
+----------------------+--------------------------------------------------+
| question (?)         | Toggle autocenter for images to *on* or *off*    |
+----------------------+--------------------------------------------------+
| apostrophe (')       | Set autozoom for new images to *override*        |
+----------------------+--------------------------------------------------+
| doublequote (")      | Toggle autozoom for new images to *on* or *off*  |
+----------------------+--------------------------------------------------+

Freepan mode
============

+----------------------+--------------------------------------------------+
| Scroll wheel turned  | Zoom while keeping location under the cursor     |
+----------------------+--------------------------------------------------+
| left click           | Set pan position, zoom in a step and warp cursor |
|                      |   to pan position (if supported on backend)      |
+----------------------+--------------------------------------------------+
| right click          | Set pan position, zoom out a step and warp       |
|                      |  cursor to pan position (if supported on backend)|
+----------------------+--------------------------------------------------+
| middle drag          | Pans freely over entire image in proportion      |
|                      |   to cursor position vs. window                  |
+----------------------+--------------------------------------------------+
| p, z, backquote, 1,  | [Same as for Pan mode]                           |
| c, arrow keys        |                                                  |
+----------------------+--------------------------------------------------+

Dist mode
=========

+----------------------+--------------------------------------------------+
| scroll               | Select distribution from linear, log, etc.       |
+----------------------+--------------------------------------------------+
| b, up_arrow          | Select prev distribution in list                 |
+----------------------+--------------------------------------------------+
| n, down_arrow        | Select next distribution in list                 |
+----------------------+--------------------------------------------------+
| D                    | Reset color distribution algorithm to "linear"   |
+----------------------+--------------------------------------------------+

Cuts mode
=========

+----------------------+--------------------------------------------------+
| left drag            | Interactive cut *both* low and high levels       |
|                      |   (vertical cuts low, horizontal cuts high)      |
+----------------------+--------------------------------------------------+
| Ctrl + left drag     | Interactive cut low level only                   |
|                      |   (horizontal drag)                              |
+----------------------+--------------------------------------------------+
| Shift + left drag    | Interactive cut high level only                  |
|                      |   (horizontal drag)                              |
+----------------------+--------------------------------------------------+
| scroll               | Coarse (10%) adjustment in/out                   |
+----------------------+--------------------------------------------------+
| Ctrl + scroll        | Fine (1%) adjustment in/out                      |
+----------------------+--------------------------------------------------+
| a, right click       | Do an auto levels to restore cuts                |
+----------------------+--------------------------------------------------+
| S                    | Set cuts to min/max values                       |
+----------------------+--------------------------------------------------+
| A                    | Set cuts to 0/255 values (for 8bpp RGB images)   |
+----------------------+--------------------------------------------------+
| b, up_arrow          | Select prev auto cuts algorithm in list          |
+----------------------+--------------------------------------------------+
| n, down_arrow        | Select next auto cuts algorithm in list          |
+----------------------+--------------------------------------------------+
| semicolon (;)        | Set autocuts for new images to *override*        |
+----------------------+--------------------------------------------------+
| colon (:)            | Toggle autocuts for new images to *on* or *off*  |
+----------------------+--------------------------------------------------+

Contrast mode
=============

+----------------------+--------------------------------------------------+
| left drag            | Interactive shift/stretch colormap (aka contrast |
|                      |   and bias).  L/R controls shift, U/D controls   |
|                      |   stretch                                        |
+----------------------+--------------------------------------------------+
| right click          | Restore the contrast (via colormap) to its       |
|                      |   original (unstretched, unshifted) state        |
+----------------------+--------------------------------------------------+
| T                    | Restore the contrast (via colormap) to its       |
|                      |   original (unstretched, unshifted) state        |
+----------------------+--------------------------------------------------+

Rotate mode
===========

+----------------------+--------------------------------------------------+
| left drag            | Drag around center of window to rotate image.    |
+----------------------+--------------------------------------------------+
| right click          | Restore rotation to 0 degrees (does not reset    |
|                      |   any flip/swap transformations)                 |
+----------------------+--------------------------------------------------+
| R                    | Restore rotation to 0 degrees and additionally   |
|                      |   undo any flip/swap transformations             |
+----------------------+--------------------------------------------------+
| Left bracket ([)     | Toggle flip image in X                           |
+----------------------+--------------------------------------------------+
| Left brace ({)       | Reset to no flip of image in X                   |
+----------------------+--------------------------------------------------+
| Right bracket (])    | Toggle flip image in Y                           |
+----------------------+--------------------------------------------------+
| Right brace (})      | Reset to no flip image in Y                      |
+----------------------+--------------------------------------------------+
| Backslash (\\)       | Swap X and Y axes                                |
+----------------------+--------------------------------------------------+
| Vertical bar (|)     | Reset to no swap of X and Y axes                 |
+----------------------+--------------------------------------------------+
| period (.)           | Increment current rotation by 90 degrees         |
+----------------------+--------------------------------------------------+
| comma (,)            | Decrement current rotation by 90 degrees         |
+----------------------+--------------------------------------------------+
| o                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Left             |
+----------------------+--------------------------------------------------+
| O                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Right            |
+----------------------+--------------------------------------------------+

Cmap mode
=========

+----------------------+--------------------------------------------------+
| scroll               | Select color map                                 |
+----------------------+--------------------------------------------------+
| left drag            | Rotate color map                                 |
+----------------------+--------------------------------------------------+
| right click          | Unrotate color map                               |
+----------------------+--------------------------------------------------+
| b, up_arrow          | Select prev color map in list                    |
+----------------------+--------------------------------------------------+
| n, down_arrow        | Select next color map in list                    |
+----------------------+--------------------------------------------------+
| I                    | Toggle invert color map                          |
+----------------------+--------------------------------------------------+
| r                    | Restore color map to unrotated, uninverted state |
+----------------------+--------------------------------------------------+
| Ctrl + scroll        | Select intensity map                             |
+----------------------+--------------------------------------------------+
| j, left_arrow        | Select prev intensity map in list                |
+----------------------+--------------------------------------------------+
| k, right_arrow       | Select next intensity map in list                |
+----------------------+--------------------------------------------------+
| i                    | Restore intensity map to "ramp"                  |
+----------------------+--------------------------------------------------+
| c                    | Toggle a color bar overlay on the image          |
+----------------------+--------------------------------------------------+
| Y                    | Restore the color map to default ('gray')        |
+----------------------+--------------------------------------------------+

Autozoom setting
================

The "autozoom" setting can be set to one of: "on", "override", "once" or
"off".  This affects the behavior of the viewer when changing to a new
image (when done in the typical way) as follows:

* `on`: the image will be scaled to fit the window
* `override`: like `on`, except that once the zoom/scale is changed by the
  user manually it turns the setting to `off`
* `once`: like `on`, except that the setting is turned to `off` after the
  first image
* `off`: an image scaled to the current viewer setting

[In the Reference Viewer, this is set under the "Zoom New" setting in the
channel preferences.]

Autocenter setting
==================

The "autocenter" setting can be set to one of: "on", "override", "once" or
"off".  This affects the behavior of the viewer when changing to a new
image (when done in the typical way) as follows:

* `on`: the pan position will be set to the center of the image
* `override`: like `on`, except that once the pan position is changed by the
  user manually it turns the setting to `off`
* `once`: like `on`, except that the setting is turned to `off` after the
  first image
* `off`: the pan position is taken from the current viewer setting

[In the Reference Viewer, this is set under the "Center New" setting in the
channel preferences.]

Autocuts setting
================

The "autocuts" setting can be set to one of: "on", "override", "once" or
"off".  This affects the behavior of the viewer when changing to a new
image (when done in the typical way) as follows:

* `on`: the cut levels for the image will be calculated and set according
  to the autocuts algorithm setting
* `override`: like `on`, except that once the cut levels are changed by the
  user manually it turns the setting to `off`
* `once`: like `on`, except that the setting is turned to `off` after the
  first image
* `off`: the cut levels are applied from the current viewer setting

[In the Reference Viewer, this is set under the "Cut New" setting in the
channel preferences.]


Reference Viewer Only
=====================

+----------------------+--------------------------------------------------+
| H                    | Raise Header tab                                 |
+----------------------+--------------------------------------------------+
| Z                    | Raise Zoom tab                                   |
+----------------------+--------------------------------------------------+
| D                    | Raise Dialogs tab                                |
+----------------------+--------------------------------------------------+
| C                    | Raise Contents tab                               |
+----------------------+--------------------------------------------------+
| less than (<)        | Toggle collapse left pane                        |
+----------------------+--------------------------------------------------+
| greater than (>)     | Toggle collapse right pane                       | 
+----------------------+--------------------------------------------------+
| f                    | Toggle full screen                               | 
+----------------------+--------------------------------------------------+
| F                    | Panoramic full screen                            | 
+----------------------+--------------------------------------------------+
| m                    | Maximize window                                  | 
+----------------------+--------------------------------------------------+
| j                    | Cycle workspace type (tabs/mdi/stack/grid).      | 
|                      |   Note that "mdi" type is not supported on all   |
|                      |   platforms.                                     |
+----------------------+--------------------------------------------------+
| k                    | Add a channel with a generic name.               | 
+----------------------+--------------------------------------------------+
| Left, Right          | Previous/Next channel.                           | 
|   (arrow keys)       |                                                  |
+----------------------+--------------------------------------------------+
| Up, Down             | Previous/Next image in channel.                  | 
|   (arrow keys)       |                                                  |
+----------------------+--------------------------------------------------+

.. note:: If there are one or more plugins active, additional mouse
	  or keyboard bindings may be present.  In general, the left
	  mouse button is used to select, pick or move, and the right
	  mouse button is used to draw a shape for the operation.  

	  On the Mac, control + mouse button can also be used to draw
	  or right click.  You can also press and release the space bar
	  to make the next drag operation a drawing operation.




