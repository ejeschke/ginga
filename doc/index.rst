.. Ginga documentation master file, created by
   `sphinx-quickstart` on Fri Sep  6 11:46:55 2013.
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
data in Python, visualizing 2D pixel data in NumPy_ arrays.
It can view astronomical data such as contained in files based on the
`FITS (Flexible Image Transport System) <https://en.wikipedia.org/wiki/FITS>`_ file format.  
It is written and is maintained by software engineers at the Subaru Telescope, National
Astronomical Observatory of Japan.

The Ginga toolkit centers around an image display class which supports
zooming and panning, color and intensity mapping, a choice of several
automatic cut levels algorithms and canvases for plotting scalable
geometric forms. In addition to this widget, a general purpose
"reference" FITS viewer is provided, based on a plugin framework.

A fairly complete set of "standard" plugins are provided for features
that we expect from a modern FITS viewer: panning and zooming windows,
star catalog access, cuts, star pick/FWHM_, thumbnails, etc.

=====================
Copyright and License
=====================

Copyright (c) 2011-2017 Eric R. Jeschke. All rights reserved.

Ginga is distributed under an open-source BSD licence. Please see the
file `LICENSE.txt` in the top-level directory for details.

====================================
Requirements and Supported Platforms
====================================

Because Ginga is written in pure Python, it can run on any platform that
has the required Python modules and has a supported widget set.
The basic Ginga display class supports the Qt_ (4 and 5), PySide_, Gtk_ (2
and 3), Tk_ widget sets natively as well as any Matplotlib Figure, and
HTML5 canvases in a web browser. The full reference viewer supports Qt
and Gtk variants. Ginga can also be used in `Jupyter notebooks <http://jupyter-notebook-beginner-guide.readthedocs.io/en/latest/what_is_jupyter.html>`_. 

==================
Getting the Source
==================

Clone from Github::

    $ git clone https://github.com/ejeschke/ginga.git

To get a zip or tar ball instead, see the links on `About Ginga <http://ejeschke.github.io/ginga/>`_.

=========================
Building and Installation
=========================

Download and install from `pip`::

    $ pip install ginga

Or, if you have downloaded the source, go into the top-level directory and run the following::

    $ python setup.py install

The reference viewer can then be run using the command `ginga`.

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
   optimizing
   ref_api

Some training videos are available in the
`downloads <https://github.com/ejeschke/ginga/downloads>`_ page on 
Github.

Be sure to also check out the
`Ginga wiki <https://github.com/ejeschke/ginga/wiki>`_.

===========
Bug Reports
===========

Please file an issue with the `issue tracker
<https://github.com/ejeschke/ginga/issues>`_
on Github.

Ginga has a logging facility, and it would be most helpful if you can
invoke Ginga with the logging options to capture any logged errors::

    $ ginga --loglevel=20 --log=ginga.log

If the difficulty is with non-display or non-working `World Coordinate System (WCS)`__ for a
particular image file please be ready to supply the file for our aid in
debugging.

==============
Developer Info
==============

In the source code `examples/*` directories, see `example{1,2}_gtk.py` (Gtk_),
`example{1,2}_qt.py` (Qt_), `example{1,2}_tk.py` (Tk_) or
`example{1,2,3,4,5}_mpl.py` (Matplotlib_).
There is more information for developers in the :ref:`manual`.

See also the `Module Index <py-modindex.html>`_ for a complete list of the available modules.

=========
Etymology
=========

"Ginga" is the romanized spelling of the Japanese word "銀河" (Hiragana:
ぎんが), meaning "galaxy" (in general) and, more familiarly, the Milky
Way. This viewer was written by software engineers at
`Subaru Telescope <http://subarutelescope.org/>`_,
National Astronomical Observatory of Japan---thus the connection.

=============
Pronunciation
=============

Ginga the viewer may be pronounced "ging-ga" (proper Japanese) or
"jing-ga" (perhaps easier for Westerners). The latter pronunciation
has meaning in the Brazilian dance/martial art Capoeira_: a fundamental
rocking or back and forth swinging motion. Pronunciation as "jin-ja"
is considered poor form.


.. _Qt: https://en.wikipedia.org/wiki/Qt_(software)
.. _Tk: http://wiki.tcl.tk/487
.. _Gtk: https://www.gtk.org/
.. _Capoeira: https://en.wikipedia.org/wiki/Capoeira
.. _FWHM: https://en.wikipedia.org/wiki/Full_width_at_half_maximum
.. _PySide: https://wiki.qt.io/PySide
.. _Matplotlib: https://matplotlib.org/
.. _NumPy: http://www.numpy.org/
.. _WCS: http://www.atnf.csiro.au/people/mcalabre/WCS/
__ WCS_
