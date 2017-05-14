.. _manual:

###################################
The Ginga Viewer and Toolkit Manual
###################################

銀河

Ginga is a toolkit for building viewers for scientific data in Python,
particularly astronomical data.  It also includes a reference viewer for viewing `FITS (Flexible Image Transport System) <https://fits.gsfc.nasa.gov//>`_ files.

The Ginga viewer is based on an image display widget that supports:

- Zooming and panning
- Color and intensity mapping
- A choice of several automatic cut levels algorithms, and
- Canvases for plotting scalable geometric forms.  

In addition to the image display widget, the Ginga viewer
provides a flexible plugin framework for extending the viewer with many different features.  

A relatively complete set of standard plugins is provided for features that we expect from a modern viewer: panning and zooming windows, star catalog access, cuts, star pick/fwhm, and thumbnails.

.. toctree::
   :maxdepth: 3

   introduction
   concepts
   operation
   canvas
   plugins
   customizing
   developers
   viewer
   internals
