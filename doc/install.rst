.. _ch-install:

++++++++++++++++++++++++++++++++++++++++++++
Detailed Installation Instructions for Ginga
++++++++++++++++++++++++++++++++++++++++++++

============
Dependencies
============

Ginga is written entirely in Python, and only uses supporting Python
packages.  There is nothing to compile (unless you need to compile one
of the supporting packages).

In recent Linux, Mac, and Windows versions, all of the packages are
available in binary (installable) form.  It should not be necessary
to compile anything, but as always, your mileage may vary.

REQUIRED
========

* python (either v. 2.7 **OR** v. 3.4 or higher)
* numpy  (v. 1.7 or higher)

Highly recommended, because some features will not be available without it:

* scipy
* pillow
* opencv

For opening `FITS <https://fits.gsfc.nasa.gov/>`_ files you will
need one of the following packages:

* astropy
* fitsio

For `WCS <https://fits.gsfc.nasa.gov/fits_wcs.html>`_ resolution
you will need one of the following packages:

* astropy
* kapteyn
* astLib
* starlink

BACKENDS (one or more)
======================

Ginga can draw its output to a number of different back ends.
Depending on which GUI toolkit you prefer (and what you want to
do), you will need at least one of the following:

* python-qt4
* python-qt5
* python-pyside (qt4 alternative)
* python-gtk (gtk2) **AND** python-cairo
* python gtk3 (gi) **AND** python-cairo
* python-Tkinter
* matplotlib
* tornado
* aggdraw
* PIL (pillow)
* OpenCv

RECOMMENDED
===========
Certain plugins in the reference viewer (or features of those plugins)
will not work without the following packages:

* matplotlib (required by: Pick, Cuts, Histogram, LineProfile)
* webkit (required by: WBrowser (used for online help))
* scipy (required by: Pick, some built-in
  :ref:`auto cuts algorithms <autoset_cut_levels>` used when you load an image)

To save a movie:

* mencoder (required by: Cuts)

Helpful, but not necessary (may optimize or speed up certain operations):

* python-opencv (speeds up rotation, mosaicing and some transformations)
* python-pyopencl (speeds up rotation, mosaicing and some transformations)
* python-numexpr (speeds up rotation a little)
* python-filemagic (aids in identifying files when opening them)
* python-PIL or pillow (useful for various RGB file manipulations)

==============================
Notes on Supported Widget Sets
==============================

In the discussion below, we differentiate between the Ginga viewing
widget, such as used in the ``examples/\*/example\*.py`` programs and the
full reference viewer, which includes many plugins (``ginga``).

.. note:: For the full reference viewer, Mac and Windows users
	  should probably install the Qt version, unless you are
	  the tinkering sort.  Linux can use either Qt or Gtk fine.

Qt/PySide
=========

Ginga can use either PyQt or PySide, version 4 or 5.  It will auto-detect
which one is installed.  There is support for both the basic widget and
the full reference viewer.

.. note:: If you have both installed and you want to use a specific one
	  then set the environment variable QT_API to either "pyqt" or
	  "pyside".  This is the same procedure as for Matplotlib.


Gtk
===

Ginga can use either Gtk 2 (with pygtk) or Gtk 3 (with gi).  (If you have
an older version of pycairo package, you may need to install a newer version
from `pycairo repository <https://github.com/pygobject/pycairo>`_).


Tk
==

Ginga's Tk support is limited to the viewing widget itself.  For
overplotting (graphics) support, you will also need:

* ``pillow``/PIL package
* ``OpenCv`` module
* ``aggdraw`` module (which you can find at
  `aggdraw repository <https://github.com/pytroll/aggdraw>`_)

Matplotlib
==========

Ginga can render directly into a Matplotlib figure.  Support is limited
to the viewing widget itself.  Any of the backends that Matplotlib
supports is usable.  Performance is not as good as to one of the
"native" backends listed above, but oh, the overplot options!

HTML5 web browser
=================

Ginga can render into an HTML5 canvas via a web server.  Support is limited
to the viewing widget itself.  See the notes in ``examples/pg/example2_pg.py``.
Tested browsers include Chromium (Chrome), Firefox, and Safari.

.. _install_generic:

==================
Basic Installation
==================

You can download and install via ``pip``::

   pip install ginga

Or via ``conda``::

   conda install ginga -c conda-forge

The reference viewer can then be run using the command ``ginga``.

========================
Installation from Source
========================

#. Clone from Github::

     git clone https://github.com/ejeschke/ginga.git

   Or see links on `this page <http://ejeschke.github.io/ginga/>`_
   to get a ZIP file or tarball.

#. Unpack, go into the top level directory, and run::

     python setup.py install

==============================
Platform Specific Instructions
==============================

.. _linux_install_instructions:

Linux
=====

#. Install the necessary dependences.  If you are on a relatively recent
   version of Ubuntu (e.g., v14.04 or later), something like the following
   will work::

     apt-get install python-numpy python-scipy python-matplotlib \
     python-astropy python-qt4 python-webkit python-magic git pip

   Or::

     apt-get install python-numpy python-scipy python-matplotlib \
     python-astropy python-gtk python-cairo python-webkit \
     python-magic git pip

   (if you want to use the Gtk version)

#. Follow instructions for :ref:`install_generic`.

Mac/Windows
===========

.. note:: Ginga can be installed and run fine using a working Macports or
          Homebrew installation.  Follow the package advice given
	  above under :ref:`linux_install_instructions`.

Anaconda
--------

For Mac/Windows users, we recommend installing the
`Anaconda distribution <http://continuum.io/downloads>`.
This distribution already includes all of the necessary packages to run
Ginga.

After installing Anaconda, open the Anaconda Prompt and follow instructions
under :ref:`install_generic`.

Enthought Canopy
----------------

As an alternative, you also have the choice of Enthought Canopy.

#. Install the `free version <https://www.enthought.com/canopy-express/>`_.
#. Open the Canopy package manager.
#. Search for and install "astropy".
#. Search for and install "pyside" (free version of Qt bindings).
#. Start the Canopy command prompt.
#. Follow instructions under :ref:`install_generic`.
