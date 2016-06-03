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
* `oneshot`: mode is released by initiating and finishing a cursor drag
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
| q                    | Pan mode: left-drag pans porportionally,         |
|                      |   right-drag zooms, middle-click sets pan        |
|                      |   position                                       | 
+----------------------+--------------------------------------------------+
| w                    | Free pan mode: Left-click pans and zooms in,     |
|                      |   right-click pans and zooms out.  Middle-drag   |
|                      |   pans freely.                                   |
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
| Ctrl + Scroll wheel  | Adjust zoom by intermediate fine steps           |
|   turned             |                                                  | 
+----------------------+--------------------------------------------------+
| Shift + Scroll wheel | Adjust pan up/down (and left/right if you have   |
|  turned              |   a device that allows that)                     |
+----------------------+--------------------------------------------------+

Cut levels and colormap commands
================================

+----------------------+--------------------------------------------------+
| a                    | Auto cut levels                                  |
+----------------------+--------------------------------------------------+
| d                    | Go into Distribution ("dist") mode:              |
|                      |  scroll wheel to set algorithm used.             |
+----------------------+--------------------------------------------------+
| D                    | Reset color distribution algorithm to "linear"   |
+----------------------+--------------------------------------------------+
| s                    | Go into Cuts mode:                               |
|                      | - left drag does interactive cut *both* low      |
|                      | and high levels, right click resets to auto cuts |
|                      | ctrl+left: adjust low cut only                   |
|                      | shift+left: adjust high cut only                 |
|                      | scroll: coarse (10%) adjustment in/out           |
|                      | ctrl+scroll: fine (1%) adjustment                |
|                      | shift+scroll: cycle through auto cuts algorithms |
+----------------------+--------------------------------------------------+
| t                    | Contrast mode: interactive shift/stretch colormap|
|                      | (with left drag), right click restores colormap  |
+----------------------+--------------------------------------------------+
| T                    | Restore the contrast (via colormap) to its       |
|                      |   original (unstretched, unshifted) state        |
+----------------------+--------------------------------------------------+
| y                    | Color map mode: scroll wheel to set colormap;    |
|                      |   left drag rotates cmap, right click unrotates  |
+----------------------+--------------------------------------------------+
| Y                    | Restore the color map to default                 |
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
| r                    | Rotate mode: left-drag to rotate image,          |
|                      |   right-click restores to no rotation            |
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




