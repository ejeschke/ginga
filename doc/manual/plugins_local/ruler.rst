.. _sec-plugins-ruler:

Ruler
=====

.. image:: figures/ruler_plugin.png
   :align: center

Ruler is a simple plugin designed to measure distances on an image.  It
does this by calculating a spherical triangulation via WCS mapping of
three points defined by a single line drawn on the image.  By default,
the distance is shown in arcminutes of sky, but using the Units control
it can be changed to show pixel distance instead.

When another line is drawn it replaces the first one, and when the
plugin is closed the graphic overlay is removed.  Should you want
"sticky rulers", use the Drawing plugin (and choose "Ruler" as the
drawing type).

Usage
-----
Click and drag to establish a ruler between two points.

Display the Zoom tab at the same time to precisely see detail
while drawing the ruler, if desired.

To erase the old and make a new ruler, click and drag again.

Editing
-------
To edit an existing ruler, click the radio button in the plugin
UI labeled 'Edit'.  If the ruler does not become selected
immediately, click on it.  This should establish a bounding box around
the ruler and show its control points.  Drag within the bounding box to
move the ruler or click and drag the endpoints to edit the ruler.

Units
-----
The units shown for distance can be selected from the drop-down box
in the UI.  You have a choice of 'arcmin', 'degrees' or 'pixels'.
The first two require a valid and working WCS in the image.
