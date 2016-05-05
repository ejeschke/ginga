.. Ginga documentation master file, created by
   sphinx-quickstart on Fri Sep  6 11:46:55 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

+++++++++++++++++++++++++++++++
Ginga: Image Viewer and Toolkit
+++++++++++++++++++++++++++++++

.. toctree::
   :maxdepth: 2

===========
About Ginga
===========

Ginga is a toolkit designed for building viewers for scientific image
data in Python, visualizing 2D pixel data in numpy arrays.
It can view astronomical data such as contained in files based on the
FITS (Flexible Image Transport System) file format.  It is written and
is maintained by software engineers at the Subaru Telescope, National
Astronomical Observatory of Japan.

The Ginga toolkit centers around an image display class which supports
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms and canvases for plotting scalable
geometric forms.  In addition to this widget, a general purpose
"reference" FITS viewer is provided, based on a plugin framework.
A fairly complete set of "standard" plugins are provided for features
that we expect from a modern FITS viewer: panning and zooming windows,
star catalog access, cuts, star pick/fwhm, thumbnails, etc.

=====================
Copyright and License
=====================

Copyright (c) 2011-2016 Eric R. Jeschke. All rights reserved.

Ginga is distributed under an open-source BSD licence. Please see the
file LICENSE.txt in the top-level directory for details.

====================================
Requirements and Supported Platforms
====================================

Because Ginga is written in pure python, it can run on any platform that
has the required python modules and has a supported widget set.
The basic Ginga display class supports the Qt, Gtk, Tk widget sets
natively as well as any matplotlib Figure, while the full reference
viewer supports Qt and Gtk.  Ginga can also be used in ipython notebooks.

==================
Getting the source
==================

Clone from github::

    $ git clone https://github.com/ejeschke/ginga.git

Or see links on `this page <http://ejeschke.github.io/ginga/>`_
to get a zip or tar ball.

=========================
Building and Installation
=========================

Download and install from `pip`::

    $ pip install ginga

Or, if you have downloaded the source, go into the top level directory and::

    $ python setup.py install

The reference viewer can then be run using the command "ginga"

.. toctree::
   :maxdepth: 1

   install

=============
Documentation
=============

.. toctree::
   :maxdepth: 1

   WhatsNew
   quickref
   FAQ
   manual/index
   ref_api

Some training videos are available in the
`downloads <https://github.com/ejeschke/ginga/downloads>`_ section at
github.
Be sure to also check out the
`wiki <https://github.com/ejeschke/ginga/wiki>`_.

===========
Bug reports
===========

Please file an issue with the `issue tracker
<https://github.com/ejeschke/ginga/issues>`_
on github.

Ginga has a logging facility, and it would be most helpful if you can
invoke Ginga with the logging options to capture any logged errors::

    $ ginga --loglevel=20 --log=ginga.log

If the difficulty is with non-display or non-working WCS for a
particular image file please be ready to supply the file for our aid in
debugging.

==============
Developer Info
==============

In the source code `examples/*` directories, see example{1,2}_gtk.py (Gtk),
example{1,2}_qt.py (Qt), example{1,2}_tk.py (Tk) or
example{1,2,3,4,5}_mpl.py (matplotlib).
There is more information for developers in the :ref:`manual`.

See also the Module Index at the bottom of this document.

=========
Etymology
=========

"Ginga" is the romanized spelling of the Japanese word "銀河" (hiragana:
ぎんが), meaning "galaxy" (in general) and, more familiarly, the Milky
Way. This viewer was written by software engineers at
`Subaru Telescope <http://subarutelescope.org/>`_,
National Astronomical Observatory of Japan--thus the connection.

=============
Pronunciation
=============

Ginga the viewer may be pronounced "ging-ga" (proper japanese) or
"jing-ga" (perhaps easier for western tongues). The latter pronunciation
has meaning in the Brazilian dance/martial art capoeira: a fundamental
rocking or back and forth swinging motion.  Pronounciation as "jin-ja"
is considered poor form.
