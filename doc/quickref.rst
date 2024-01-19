.. _ginga-quick-reference:

+++++++++++++++
Quick Reference
+++++++++++++++

=================
Main image window
=================

These keyboard and mouse operations are available when the main image
window has the focus.

.. _mode_control_commands:

Mode control commands
=====================

About modes
-----------

Certain keystrokes invoke a *mode*---modes are usually indicated by the
*mode indicator*: a small black rectangle with the mode name in one corner
of the view.  In a mode, there are usually some special key, cursor, and
scroll bindings that override *some* of the default ones.

Modes additionally have a *mode type* which can be set to one of the following:

* `held`: mode is active while the activating key is held down
* `oneshot`: mode is released by initiating and finishing a cursor drag
  or when `Esc` is pressed, if no cursor drag is performed
* `locked`: mode is locked until the mode key is pressed again (or `Esc`)

By default, most modes are activated in "locked" type.  The mode type is
indicated in the brackets after the mode name in the mode indicator.
The following keys are important for initiating a mode:

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| Space                | Enter "meta" mode. Next keystroke will trigger   |
|                      | a particular mode.                               |
+----------------------+--------------------------------------------------+
| Esc                  | Exit any mode.                                   |
+----------------------+--------------------------------------------------+

.. _meta_mode:

"meta" mode
-----------

Most modes are defined so that they are invoked from a special intermediate
mode called "meta".  In that case a two-key sequence is required to enter
the mode: pressing the key that invokes "meta" and then pressing the key that
invokes the desired mode.  The following table shows the modes that can be
triggered from meta mode.

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| Space                | Exit/Enter "meta" mode.                          |
+----------------------+--------------------------------------------------+
| b                    | Enter draw mode (canvas must be enabled to draw).|
+----------------------+--------------------------------------------------+
| q                    | Enter :ref:`Pan mode <pan_mode>`.                |
+----------------------+--------------------------------------------------+
| w                    | Enter :ref:`Zoom mode <zoom_mode>`.              |
+----------------------+--------------------------------------------------+
| r                    | Enter :ref:`Rotate mode <rotate_mode>`.          |
+----------------------+--------------------------------------------------+
| t                    | Enter :ref:`Contrast mode <contrast_mode>`.      |
+----------------------+--------------------------------------------------+
| y                    | Enter :ref:`CMap (color map) mode <cmap_mode>`.  |
+----------------------+--------------------------------------------------+
| s                    | Enter :ref:`Cuts mode <cuts_mode>`.              |
+----------------------+--------------------------------------------------+
| d                    | Enter Color Distribution ("dist") mode.          |
|                      | See :ref:`Dist mode <dist_mode>`.                |
+----------------------+--------------------------------------------------+
| n                    | Enter naxis (cube axis navigation) mode.         |
|                      | See :ref:`Naxis mode <naxis_mode>`.              |
+----------------------+--------------------------------------------------+
| L                    | Toggle the normal lock to the current mode or    |
|                      | any future modes.                                |
+----------------------+--------------------------------------------------+


.. _panning_zooming_commands:

Panning and zooming commands
============================

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| scroll-wheel         | Zoom in or out.                                  |
+----------------------+--------------------------------------------------+
| Shift + scroll-wheel | Zoom while keeping location under the cursor.    |
+----------------------+--------------------------------------------------+
| Ctrl + scroll-wheel  | Pan in direction of scroll.                      |
+----------------------+--------------------------------------------------+
| Digit                | Zoom image to zoom steps 1, 2, ..., 9, 10.       |
| (1234567890)         |                                                  |
+----------------------+--------------------------------------------------+
| Shift + Digit        | Zoom image to zoom steps -1, -2, ..., -9, -10.   |
+----------------------+--------------------------------------------------+
| Backquote (\`)       | Zoom image to fit window and center it.          |
+----------------------+--------------------------------------------------+
| Minus, Underscore    | Zoom out.                                        |
| (-, \_)              |                                                  |
+----------------------+--------------------------------------------------+
| Equals, Plus         | Zoom in.                                         |
| (=, +)               |                                                  |
+----------------------+--------------------------------------------------+
| Middle (scroll)      | Set pan position (under cursor).                 |
| button click         |                                                  |
+----------------------+--------------------------------------------------+
| p                    | Set pan position (under cursor) for zooming.     |
+----------------------+--------------------------------------------------+
| Shift + left-click   | Set pan position for zooming.                    |
+----------------------+--------------------------------------------------+
| Shift + arrow key    | Move pan position 1 pixel in that direction.     |
+----------------------+--------------------------------------------------+
| c                    | Set pan position to the center of the image.     |
+----------------------+--------------------------------------------------+
| Ctrl + left-drag     | Proportional pan (press and drag left mouse      |
|                      | button.                                          |
+----------------------+--------------------------------------------------+
| slash (/)            | Set autocenter for new images to *override*.     |
+----------------------+--------------------------------------------------+
| question (?)         | Toggle autocenter for images to *on* or *off*.   |
+----------------------+--------------------------------------------------+
| apostrophe (')       | Set autozoom for new images to *override*.       |
+----------------------+--------------------------------------------------+
| double quote (")     | Toggle autozoom for new images to *on* or *off*. |
+----------------------+--------------------------------------------------+

.. _cut_levels_colormap_commands:

Cut levels and colormap commands
================================

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| a                    | Auto cut levels.                                 |
+----------------------+--------------------------------------------------+
| D                    | Reset color distribution algorithm to "linear".  |
+----------------------+--------------------------------------------------+
| T                    | Restore the contrast (via colormap) to its       |
|                      | original (unstretched, unshifted) state.         |
+----------------------+--------------------------------------------------+
| Y                    | Restore the color map to default (gray).         |
+----------------------+--------------------------------------------------+
| I                    | Invert the color map.                            |
+----------------------+--------------------------------------------------+
| semicolon (;)        | Set autocuts for new images to *override*.       |
+----------------------+--------------------------------------------------+
| colon (:)            | Toggle autocuts for new images to *on* or *off*. |
+----------------------+--------------------------------------------------+

.. _transform_commands:

Transform commands
==================

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| Left bracket ([)     | Toggle flip image in X.                          |
+----------------------+--------------------------------------------------+
| Left brace ({)       | Reset to no flip of image in X.                  |
+----------------------+--------------------------------------------------+
| Right bracket (])    | Toggle flip image in Y.                          |
+----------------------+--------------------------------------------------+
| Right brace (})      | Reset to no flip image in Y.                     |
+----------------------+--------------------------------------------------+
| Backslash (\\)       | Swap X and Y axes.                               |
+----------------------+--------------------------------------------------+
| Vertical bar (|)     | Reset to no swap of X and Y axes.                |
+----------------------+--------------------------------------------------+
| R                    | Restore rotation to 0 degrees and additionally   |
|                      | undo any flip/swap transformations.              |
+----------------------+--------------------------------------------------+
| period (.)           | Increment current rotation by 90 degrees.        |
+----------------------+--------------------------------------------------+
| comma (,)            | Decrement current rotation by 90 degrees.        |
+----------------------+--------------------------------------------------+
| o                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Left.            |
+----------------------+--------------------------------------------------+
| O                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Right.           |
+----------------------+--------------------------------------------------+

.. _pan_mode:

Pan mode
========

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| left-drag            | Pan proportionally to drag.                      |
+----------------------+--------------------------------------------------+
| pan-gesture          | Pan proportionally to gesture.                   |
+----------------------+--------------------------------------------------+
| middle-click         | Set pan position.                                |
+----------------------+--------------------------------------------------+
| right-drag           | Zoom in/out proportionally to L/R drag.          |
+----------------------+--------------------------------------------------+
| scroll-wheel         | Zoom in or out.                                  |
+----------------------+--------------------------------------------------+
| pinch-gesture        | Zoom in/out porportionally to gesture.           |
+----------------------+--------------------------------------------------+
| <Modifier> +         | Pan in direction of arrow key. Adding Ctrl       |
| arrow key            | reduces amount, adding Shift reduces more.       |
+----------------------+--------------------------------------------------+
| p                    | Pan to position under cursor.                    |
+----------------------+--------------------------------------------------+
| z                    | Save current scale (see below for use).          |
+----------------------+--------------------------------------------------+
| backquote (`)        | Zoom to fit window and center.                   |
+----------------------+--------------------------------------------------+
| r                    | Pan to cursor and zoom to saved scale level      |
|                      | (or 1:1 if no scale level saved).                |
+----------------------+--------------------------------------------------+
| c                    | Set pan position to the center of the image.     |
+----------------------+--------------------------------------------------+
| slash (/)            | Set autocenter for new images to *override*.     |
+----------------------+--------------------------------------------------+
| question (?)         | Toggle autocenter for images to *on* or *off*.   |
+----------------------+--------------------------------------------------+
| apostrophe (')       | Set autozoom for new images to *override*.       |
+----------------------+--------------------------------------------------+
| double quote (")     | Toggle autozoom for new images to *on* or *off*. |
+----------------------+--------------------------------------------------+

.. _zoom_mode:

Zoom mode
=========

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| scroll-wheel         | Zoom in or out.                                  |
+----------------------+--------------------------------------------------+
| left-click           | Set pan position, zoom in a step and warp cursor |
|                      | to pan position (if supported on backend).       |
+----------------------+--------------------------------------------------+
| right-click          | Set pan position, zoom out a step and warp       |
|                      | cursor to pan position (if supported on backend).|
+----------------------+--------------------------------------------------+
| middle-drag          | Pans freely over entire image in proportion      |
|                      | to cursor position versus window.                |
+----------------------+--------------------------------------------------+
| p, z, backquote, r,  | (Same as for :ref:`Pan mode <pan_mode>`.)        |
| c, arrow keys, pan   |                                                  |
| and pinch gestures   |                                                  |
+----------------------+--------------------------------------------------+

.. _dist_mode:

Dist mode
=========

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| scroll-wheel         | Select distribution from linear, log, etc.       |
+----------------------+--------------------------------------------------+
| b, up-arrow          | Select prev distribution in list.                |
+----------------------+--------------------------------------------------+
| n, down-arrow        | Select next distribution in list.                |
+----------------------+--------------------------------------------------+
| D                    | Reset color distribution algorithm to "linear".  |
+----------------------+--------------------------------------------------+

.. _cuts_mode:

Cuts mode
=========

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| left-drag            | Interactive cut *both* low and high levels       |
|                      | (vertical cuts low, horizontal cuts high).       |
+----------------------+--------------------------------------------------+
| Ctrl + left-drag     | Interactive cut low level only                   |
|                      | (horizontal drag).                               |
+----------------------+--------------------------------------------------+
| Ctrl + pan gesture   | Change cut high level up/down.                   |
+----------------------+--------------------------------------------------+
| Shift + left-drag    | Interactive cut high level only                  |
|                      | (horizontal drag).                               |
+----------------------+--------------------------------------------------+
| Shift + pan gesture  | Change cut low level up/down.                    |
+----------------------+--------------------------------------------------+
| scroll-wheel         | Squeeze or stretch gap between cuts.             |
|                      | Coarse (10%) adjustment in/out.                  |
+----------------------+--------------------------------------------------+
| Ctrl + scroll-wheel  | Squeeze or stretch gap between cuts.             |
|                      | Fine (1%) adjustment in/out.                     |
+----------------------+--------------------------------------------------+
| pinch gesture        | Squeeze or stretch gap between cuts.             |
+----------------------+--------------------------------------------------+
| a, right-click       | Do an auto level to restore cuts.                |
+----------------------+--------------------------------------------------+
| k                    | Set the high cut to the value under the cursor.  |
+----------------------+--------------------------------------------------+
| l                    | Set the low cut to the value under the cursor.   |
+----------------------+--------------------------------------------------+
| S                    | Set cuts to min/max values.                      |
+----------------------+--------------------------------------------------+
| A                    | Set cuts to 0/255 values (for 8bpp RGB images).  |
+----------------------+--------------------------------------------------+
| b, up-arrow          | Select prev auto cuts algorithm in list.         |
+----------------------+--------------------------------------------------+
| n, down-arrow        | Select next auto cuts algorithm in list.         |
+----------------------+--------------------------------------------------+
| semicolon (;)        | Set autocuts for new images to *override*.       |
+----------------------+--------------------------------------------------+
| colon (:)            | Toggle autocuts for new images to *on* or *off*. |
+----------------------+--------------------------------------------------+

.. _contrast_mode:

Contrast mode
=============

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| left-drag            | Interactive shift/stretch colormap (AKA contrast |
|                      | and bias). Left/Right controls shift, Up/Down    |
|                      | controls stretch.                                |
+----------------------+--------------------------------------------------+
| right-click          | Restore the contrast (via colormap) to its       |
|                      | original (unstretched, unshifted) state.         |
+----------------------+--------------------------------------------------+
| scroll-wheel         | Increase/decrease contrast.                      |
|                      | (add Ctrl to adjust it more finely).             |
+----------------------+--------------------------------------------------+
| Shift + scroll-wheel | Increase/decrease brightness (bias).             |
|                      | (add Ctrl to adjust it more finely).             |
+----------------------+--------------------------------------------------+
| Ctrl + pan gesture   | Increase/decrease contrast.                      |
+----------------------+--------------------------------------------------+
| Shift + pan gesture  | Increase/decrease brightness (bias).             |
+----------------------+--------------------------------------------------+
| T                    | Restore the contrast (via colormap) to its       |
|                      | original (unstretched, unshifted) state.         |
+----------------------+--------------------------------------------------+

.. _rotate_mode:

Rotate mode
===========

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| left-drag            | Drag around center of window to rotate image.    |
+----------------------+--------------------------------------------------+
| right-click          | Restore rotation to 0 degrees (does not reset    |
|                      | any flip/swap transformations).                  |
+----------------------+--------------------------------------------------+
| R                    | Restore rotation to 0 degrees and additionally   |
|                      | undo any flip/swap transformations.              |
+----------------------+--------------------------------------------------+
| Left bracket ([)     | Toggle flip image in X.                          |
+----------------------+--------------------------------------------------+
| Left brace ({)       | Reset to no flip of image in X.                  |
+----------------------+--------------------------------------------------+
| Right bracket (])    | Toggle flip image in Y.                          |
+----------------------+--------------------------------------------------+
| Right brace (})      | Reset to no flip image in Y.                     |
+----------------------+--------------------------------------------------+
| Backslash (\\)       | Swap X and Y axes.                               |
+----------------------+--------------------------------------------------+
| Vertical bar (|)     | Reset to no swap of X and Y axes.                |
+----------------------+--------------------------------------------------+
| period (.)           | Increment current rotation by 90 degrees.        |
+----------------------+--------------------------------------------------+
| comma (,)            | Decrement current rotation by 90 degrees.        |
+----------------------+--------------------------------------------------+
| o                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Left.            |
+----------------------+--------------------------------------------------+
| O                    | Orient image by transforms and rotation so that  |
|                      | WCS indicates North=Up and East=Right.           |
+----------------------+--------------------------------------------------+

.. _cmap_mode:

Cmap mode
=========

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| scroll               | Select color map.                                |
+----------------------+--------------------------------------------------+
| left-drag            | Rotate color map.                                |
+----------------------+--------------------------------------------------+
| right-click          | Unrotate color map.                              |
+----------------------+--------------------------------------------------+
| b, up-arrow          | Select prev color map in list.                   |
+----------------------+--------------------------------------------------+
| n, down-arrow        | Select next color map in list.                   |
+----------------------+--------------------------------------------------+
| I                    | Toggle invert color map.                         |
+----------------------+--------------------------------------------------+
| r                    | Restore color map to unrotated, uninverted state.|
+----------------------+--------------------------------------------------+
| Ctrl + scroll        | Select intensity map.                            |
+----------------------+--------------------------------------------------+
| j, left-arrow        | Select prev intensity map in list.               |
+----------------------+--------------------------------------------------+
| k, right-arrow       | Select next intensity map in list.               |
+----------------------+--------------------------------------------------+
| i                    | Restore intensity map to "ramp".                 |
+----------------------+--------------------------------------------------+
| c                    | Toggle a color bar overlay on the image.         |
+----------------------+--------------------------------------------------+
| Y                    | Restore the color map to default ('gray').       |
+----------------------+--------------------------------------------------+

.. _naxis_mode:

Naxis mode
==========

.. note:: Naxis mode can be used when viewing data that has more than 2
          dimensions (e.g., data cubes).

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| scroll               | Select previous or next slice of current axis.   |
+----------------------+--------------------------------------------------+
| Ctrl + scroll        | Select previous or next axis as current axis.    |
+----------------------+--------------------------------------------------+
| left drag            | select slice as a function of percentage of      |
|                      | cursor/window width.                             |
+----------------------+--------------------------------------------------+
| up-arrow             | Select prev axis as current axis.                |
+----------------------+--------------------------------------------------+
| down-arrow           | Select next axis as current axis.                |
+----------------------+--------------------------------------------------+

.. _plot_mode:

Plot mode
=========

Plot mode is only valid when the viewer is used with a ``PlotAide``
object to display a graph.

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| scroll               | Zoom the X axis.                                 |
|                      | (Sets `autoaxis_x` to `off`, if it was `on`)     |
+----------------------+--------------------------------------------------+
| Ctrl + scroll        | Zoom the Y axis. (Sets `autoaxis_y` to `off`)    |
+----------------------+--------------------------------------------------+
| x                    | Toggle `autoaxis_x` between `on` and `off`.      |
+----------------------+--------------------------------------------------+
| p                    | Toggle `autoaxis_x` between `pan` and `off`.     |
+----------------------+--------------------------------------------------+
| y                    | Toggle `autoaxis_y` between `on` and `off`.      |
+----------------------+--------------------------------------------------+
| v                    | Toggle `autoaxis_y` between `vis` and `off`.     |
+----------------------+--------------------------------------------------+

The graph can be flipped in X or Y and the axes swapped, using the keystroke
commands found in the transform section above (:ref:`transform_commands`).

To understand the role of the `autoaxis_x` and `autoaxis_y` settings, please
see the chapter on plots (:ref:`ch-plots`).

.. _autozoom_setting:

Autozoom setting
================

The "autozoom" setting can be set to one of the following: "on", "override",
"once" or "off".  This affects the behavior of the viewer when changing to a
new image (when done in the typical way) as follows:

* `on`: the image will be scaled to fit the window
* `override`: like `on`, except that once the zoom/scale is changed by the
  user manually it turns the setting to `off`
* `once`: like `on`, except that the setting is turned to `off` after the
  first image
* `off`: an image scaled to the current viewer setting

(In the :ref:`Reference Viewer <reference_viewer>`, this is set under the
"Zoom New" setting in the channel preferences.)

.. _autocenter_setting:

Autocenter setting
==================

The "autocenter" setting can be set to one of the following: "on", "override",
"once" or "off".  This affects the behavior of the viewer when changing to a
new image (when done in the typical way) as follows:

* `on`: the pan position will be set to the center of the image
* `override`: like `on`, except that once the pan position is changed by the
  user manually it turns the setting to `off`
* `once`: like `on`, except that the setting is turned to `off` after the
  first image
* `off`: the pan position is taken from the current viewer setting

(In the :ref:`Reference Viewer <reference_viewer>`, this is set under the
"Center New" setting in the channel preferences.)

.. _autocuts_setting:

Autocuts setting
================

The "autocuts" setting can be set to one of following: "on", "override",
"once" or "off". This affects the behavior of the viewer when changing to a
new image (when done in the typical way) as follows:

* `on`: the cut levels for the image will be calculated and set according
  to the autocuts algorithm setting
* `override`: like `on`, except that once the cut levels are changed by the
  user manually it turns the setting to `off`
* `once`: like `on`, except that the setting is turned to `off` after the
  first image
* `off`: the cut levels are applied from the current viewer setting

(In the ref:`Reference Viewer <reference_viewer>`, this is set under the
"Cut New" setting in the channel preferences.)


.. _reference_viewer:

Reference Viewer Only
=====================

+----------------------+--------------------------------------------------+
| Commmand             | Description                                      |
+======================+==================================================+
| H                    | Raise **Header** tab (if Header plugin has been  |
|                      | started).                                        |
+----------------------+--------------------------------------------------+
| Z                    | Raise **Zoom** tab (if Zoom plugin has been      |
|                      | started).                                        |
+----------------------+--------------------------------------------------+
| D                    | Raise **Dialogs** tab.                           |
+----------------------+--------------------------------------------------+
| C                    | Raise **Contents** tab.                          |
+----------------------+--------------------------------------------------+
| less than (<)        | Toggle collapse left pane.                       |
+----------------------+--------------------------------------------------+
| greater than (>)     | Toggle collapse right pane.                      |
+----------------------+--------------------------------------------------+
| f                    | Toggle full screen.                              |
+----------------------+--------------------------------------------------+
| F                    | Panoramic full screen.                           |
+----------------------+--------------------------------------------------+
| h                    | Pop up a quick help tab for the current mode.    |
+----------------------+--------------------------------------------------+
| m                    | Maximize window.                                 |
+----------------------+--------------------------------------------------+
| J                    | Cycle workspace type (tabs/mdi/stack/grid).      |
|                      | Note that "mdi" type is not supported on all     |
|                      | platforms.                                       |
+----------------------+--------------------------------------------------+
| k                    | Add a channel with a generic name.               |
+----------------------+--------------------------------------------------+
| Left, Right          | Previous/Next channel.                           |
| (arrow keys)         |                                                  |
+----------------------+--------------------------------------------------+
| Up, Down             | Previous/Next image in channel.                  |
| (arrow keys)         |                                                  |
+----------------------+--------------------------------------------------+

.. note:: If there are one or more plugins active, additional mouse
	  or keyboard bindings may be present. In general, the left
	  mouse button is used to select, pick or move, and the right
	  mouse button is used to draw a shape for the operation.

	  On the Mac, Ctrl + mouse button can also be used to draw
          or right-click. You can also invoke draw mode as described
          above in the section on modes.
