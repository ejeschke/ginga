.. _sec-plugins-mosaic:

Mosaic
======

.. warning:: This can be very memory intensive.

This plugin is used to automatically create a mosaic in the channel using
images provided by the user (e.g., using :ref:`plugins-fbrowser`).
The position of an image on the mosaic is determined by its WCS without
distortion correction. This is meant as a quick-look tool, not an
`AstroDrizzle <http://ssb.stsci.edu/doc/stsci_python_x/drizzlepac.doc/html/index.html>`_
replacement. The mosaic only exists in memory but you can save it out to a
FITS file using :ref:`sec-plugins-global-saveimage`.

When a mosaic falls out of memory, it is no longer accessible in Ginga.
To avoid this, you must configure your session such that your Ginga data cache
is sufficiently large (see :ref:`ch-customization`).

.. automodule:: ginga.misc.plugins.Mosaic
