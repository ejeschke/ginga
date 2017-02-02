.. _sec-plugins-wcsmatch:

WCSMatch
========

.. image:: figures/wcsmatch-plugin.png
   :width: 400px
   :align: center

WCSMatch is a global plugin for the Ginga image viewer that allows
you to roughly align images with different scales and orientations
using the images' World Coordinate System for viewing purposes.

Usage
-----
To use, simply start the plugin, and from the plugin GUI select a
channel from the drop-down menu labeled "Reference Channel".  The
image contained in that channel will be used as a reference for
zooming and orienting the images in the other channels.

The channels will be synchronized in viewing (zoom, pan, rotate,
transform).  To "unlock" the synchronization, simply select "None"
from the "Reference Channel" drop-down menu.

Currently there is no way to limit the channels that are affected
by the plugin.
