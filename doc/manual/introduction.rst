++++++++++++
Introduction
++++++++++++

=====
About
=====

Ginga is a toolkit designed for building viewers for scientific image
data in Python, visualizing 2D pixel data in numpy arrays.  
It can view astronomical data such as contained in files based on the
FITS (Flexible Image Transport System) file format.  It is written and
is maintained by software engineers at the Subaru Telescope, National
Astronomical Observatory of Japan.  The code is released as open-source
under a BSD license and maintained at http://ejeschke.github.io/ginga/

========
Features
========

The Ginga toolkit centers around an image display object which supports 
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms and canvases for plotting scalable
geometric forms.  In addition to this widget, a general purpose
"reference" FITS viewer is provided, based on a plugin framework.
A fairly complete set of standard plugins are provided for features
that we expect from a modern FITS viewer: panning and zooming windows,
star catalog access, cuts, star pick/fwhm, thumbnails, etc. 

