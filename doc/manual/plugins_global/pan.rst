.. _sec-plugins-pan:

Pan
===

.. image:: figures/pan-plugin.png
   :align: center

The Pan plugin provides a small panning image that gives an overall
"birds-eye" view of the channel image that last had the focus.  If the
channel image is zoomed in 2X or greater then the pan region is shown
graphically in the Pan image by a rectangle.


Usage
-----
The channel image can be panned by clicking and/or dragging to place
the rectangle.  Using the right mouse button to drag a rectangle will
force the channel image viewer to try to match the region (taking into
account the differences in the aspect ratio between the drawn rectangle
and the window dimensions).  Scrolling in the Pan image will zoom the
channel image.  

The color/intensity map and cut levels of the Pan image are updated
when they are changed in the corresponding channel image.
The Pan image also displays the World Coordinate System compass, if
valid WCS metadata is present in the FITS HDU being viewed in the
channel.

The Pan plugin usually appears as a sub-pane under the "Info" tab, next
to the Info plugin.

