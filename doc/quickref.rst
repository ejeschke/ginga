.. _ginga-quick-reference:

+++++++++++++++++++++
Ginga Quick Reference
+++++++++++++++++++++

=================
Main image window
=================

These keyboard and mouse operations are available when the main image
window has the focus.

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
| Middle (scroll)      | Pan image freely (when zoomed in)                |
| button drag          |                                                  |
+----------------------+--------------------------------------------------+
| p                    | Set pan position for zooming                     |
+----------------------+--------------------------------------------------+
| Shift + Left click   | Set pan position for zooming                     |
+----------------------+--------------------------------------------------+
| c                    | Set pan position to the center of the image      |
+----------------------+--------------------------------------------------+
| q                    | Pan (drag) mode; Left drag, press ESC to exit    | 
+----------------------+--------------------------------------------------+
| w                    | Pan (free) mode; Left drag                       | 
+----------------------+--------------------------------------------------+
| Ctrl + Left drag     | Proportional pan (press and drag left mouse      |
|                      |     button                                       |
+----------------------+--------------------------------------------------+
| apostrophe (')       | Set autozoom for new images to *override*        |
+----------------------+--------------------------------------------------+
| doublequote (")      | Set autozoom for new images to *on*              |
+----------------------+--------------------------------------------------+
| Ctrl + Scroll wheel  | Adjust zoom by intermediate coarse steps         |
|   turned             |                                                  | 
+----------------------+--------------------------------------------------+
| Shift + Scroll wheel | Adjust zoom by intermediate fine steps           |
|  turned              |                                                  |
+----------------------+--------------------------------------------------+

Cut levels and colormap commands
================================

+----------------------+--------------------------------------------------+
| a                    | Auto cut levels                                  |
+----------------------+--------------------------------------------------+
| d                    | Cycle color distribution algorithm               |
+----------------------+--------------------------------------------------+
| D                    | Reset color distribution algorithm to "linear"   |
+----------------------+--------------------------------------------------+
| period (.)           | Interactive cut *both* low and high (with left   |
|                      |   mouse button)                                  |
+----------------------+--------------------------------------------------+
| slash (/)            | Interactive warp colormap (with left mouse       |
|                      |   button)                                        |
+----------------------+--------------------------------------------------+
| question (?)         | Restore the color map to its original state      |
+----------------------+--------------------------------------------------+
| semicolon (;)        | Set autocuts for new images to *override*        |
+----------------------+--------------------------------------------------+
| colon (:)            | Set autocuts for new images to *on*              |
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
| r                    | Interactive rotate (with left mouse button)      |
+----------------------+--------------------------------------------------+
| R                    | Restore rotation to 0 degrees                    |
+----------------------+--------------------------------------------------+
| e                    | Increment current rotation by 90 degrees         |
+----------------------+--------------------------------------------------+
| E                    | Increment current rotation by -90 degrees        |
+----------------------+--------------------------------------------------+
| o                    | Orient image by WCS so North=Up and East=Left    |
+----------------------+--------------------------------------------------+
| O                    | Orient image by WCS so North=Up and East=Right   |
+----------------------+--------------------------------------------------+

Reference Viewer Only
=====================

+----------------------+--------------------------------------------------+
| I                    | Raise Info tab                                   |
+----------------------+--------------------------------------------------+
| H                    | Raise Header tab                                 |
+----------------------+--------------------------------------------------+
| Z                    | Raise Zoom tab                                   |
+----------------------+--------------------------------------------------+
| D                    | Raise Dialogs tab                                |
+----------------------+--------------------------------------------------+
| T                    | Raise Thumbs tab                                 |
+----------------------+--------------------------------------------------+
| C                    | Raise Contents tab                               |
+----------------------+--------------------------------------------------+
| left angle (<)       | Toggle collapse left pane                        |
+----------------------+--------------------------------------------------+
| right angle (>)      | Toggle collapse right pane                       | 
+----------------------+--------------------------------------------------+
| f                    | Toggle full screen                               | 
+----------------------+--------------------------------------------------+
| F                    | Panoramic full screen                            | 
+----------------------+--------------------------------------------------+
| m                    | Maximize window                                  | 
+----------------------+--------------------------------------------------+

.. note:: If there are one or more plugins active, additional mouse
	  or keyboard bindings may be present.  In general, the left
	  mouse button is used to select, pick or move, and the right
	  mouse button is used to draw a shape for the operation.  

	  On the Mac, control + mouse button can also be used to draw
	  or right click.  You can also press and release the space bar
	  to make the next drag operation a drawing operation.




