.. _sec-plugins-info:

Info
====

.. image:: figures/info-plugin.png
   :width: 400px
   :align: center

The Info plugin provides a pane of commonly useful metadata about the
associated channel image.  Common information includes some
FITS header values, the equinox, dimensions of the image, minimum and
maximum values and the zoom level.  As the cursor is moved around the
image, the X, Y, Value, RA and DEC values are updated to reflect the
value under the cursor.

As a global plugin, Info responds to a change of focus to a new channel
by displaying the metadata from the new channel.

Usage
-----
At the bottom of the Info interface are the cut levels controls. Here
the low and high cut levels are shown and can be adjusted.  Pressing the
"Auto Levels" button will recalculate cut levels based on the current
auto cut levels algorithm and parameters defined in the channel
preferences.

Below the "Auto Levels" button, the status of the settings for
"Cut New", "Zoom New" and "Center New" are shown for the currently active
channel.  These indicate how new images that are added to the channel
will be affected by auto cut levels, fitting to the window and panning
to the center of the image.

.. note:: The Info plugin typically appears under the "Synopsis" tab in
          the user interface.
