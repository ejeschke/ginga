++++++++++++
Introduction
++++++++++++

=====
About
=====

Ginga is a toolkit designed for building viewers for scientific image
data in Python, visualizing 2D pixel data in numpy arrays.  
By default the Ginga toolkit can view standard RGB(A) type images as
well as astronomical data such as contained in files based on the FITS
(Flexible Image Transport System) file format.
The viewer is easily extended to handle additional formats, so long as
the data can be accessed as numpy arrays.

The Ginga toolkit is written and maintained by software engineers at the
Subaru Telescope, National Astronomical Observatory of Japan, and the
Space Telescope Science Institute. The code is released as open-source
under a BSD license and maintained at http://ejeschke.github.io/ginga/ 

========
Features
========

The Ginga toolkit centers around an image display widget that supports 
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms, and canvases for plotting scalable
geometric forms.  

In addition to this widget, a general purpose reference FITS viewer is
provided, based on a plugin framework. A relatively complete set of
standard plugins are provided for features that we expect from a modern
FITS viewer: panning and zooming windows, star catalog access, cuts,
star pick/fwhm, thumbnails, etc.  


