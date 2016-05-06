.. _manual:

###################################
The Ginga Viewer and Toolkit Manual
###################################

銀河

Ginga is a toolkit for building viewers for scientific data in Python,
particularly astronomical data.  It also includes a reference viewer for
viewing FITS (Flexible Image Transport System) files.
The Ginga viewer is based on an image display object which supports
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms and canvases for plotting scalable
geometric forms.  In addition to this widget, the reference viewer
provides a flexible plugin framework for extending the viewer with many
different features.  A fairly complete set of standard plugins are provided
for features that we expect from a modern viewer: panning and zooming
windows, star catalog access, cuts, star pick/fwhm, thumbnails, etc.

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
