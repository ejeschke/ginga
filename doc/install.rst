.. _ch-install:

++++++++++++
Installation
++++++++++++

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

* python (v. 3.7 or higher)
* setuptools-scm
* numpy  (v. 1.14 or higher)
* astropy
* pillow

Strongly recommended, because some features will not be available without it:

* scipy
* opencv-python (also distributed as opencv or python-opencv,
  depending on where you get it from)
* exifread
* beautifulsoup4
* docutils (to display help for plugins)

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

.. TODO: This can be broken down in a clearer way.

* QtPy (PyQt5 or PyQt6)
* PySide (pyside2 or pyside6)
* pygobject (gi) **AND** pycairo (GTK 3)
* `tkinter <https://docs.python.org/3/library/tk.html>`_
* matplotlib
* tornado
* `aggdraw <https://github.com/pytroll/aggdraw>`_
* Pillow (PIL fork)

RECOMMENDED
===========

Certain plugins in the reference viewer (or features of those plugins)
will not work without the following packages:

* matplotlib (required by: Pick, Cuts, Histogram, LineProfile)
* scipy (required by: Pick, some built-in
  :ref:`auto cuts algorithms <autoset_cut_levels>` used when you load an image)
* astroquery (required by Catalogs)

To save a movie:

* mencoder (command line tool required by: Cuts)

Helpful, but not necessary (may optimize or speed up certain operations):

* opencv-python (speeds up rotation, mosaicing and some transformations)
* pyopengl + pycairo (for using OpenGL features; very useful for 4K or larger
  monitors)
* filemagic (aids in identifying files when opening them)

==============================
Notes on Supported Widget Sets
==============================

In the discussion below, we differentiate between the Ginga viewing
widget, such as used in the ``examples/\*/example\*.py`` programs and the
full reference viewer, which includes many plugins (``ginga``).

.. note:: For the full reference viewer, Mac and Windows users
	  should probably install the Qt version, unless you are
	  the tinkering sort.  Linux can use either Qt or GTK fine.

Qt/PySide
=========

Ginga can use either PyQt or PySide, for Qt version 5 or 6.  It will
auto-detect which one is installed, using the ``qtpy`` compatibility package.
There is support for both the basic widget and the full reference viewer.

.. note:: If you have both installed and you want to use a specific one
	  then set the environment variable QT_API to either "pyqt" or
	  "pyside".  This is the same procedure as for Matplotlib.

GTK
===

Ginga can use GTK 3 (with ``gi``).  (If you have an older version of
``pycairo`` package, you may need to install a newer version from
``pycairo``).

Tk
==

Ginga's Tk support is limited to the viewing widget itself.  For
overplotting (graphics) support, you will also need one of:

* Pillow
* opencv-python
* aggdraw

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

You can download and install via ``pip`` by choosing the command that best
suits your needs (full selection is defined in
`setup configuration file <https://github.com/ejeschke/ginga/blob/main/setup.cfg>`_
)::

   pip install ginga  # The most basic installation

   pip install ginga[recommended,qt5]  # Qt5

   pip install ginga[recommended,gtk3]  # GTK 3

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

     pip install -e .

==============================
Platform Specific Instructions
==============================

.. _linux_install_instructions:

Linux (Debian/Ubuntu)
=====================

If you are on a relatively recent version of Debian or Ubuntu,
something like the following will work::

     apt install python3-ginga

If you are using another distribution of Linux, we recommend to install
via Anaconda or Miniconda as described below.

Mac/Windows/Linux (others)
==========================

Anaconda
--------

For Mac/Windows or other Linux users, we recommend installing the
`Anaconda distribution <http://continuum.io/downloads>`_ (or Miniconda).
This distribution already includes all of the necessary packages to run
Ginga.

After installing Anaconda, open the Anaconda Prompt and follow instructions
under :ref:`install_generic` via ``conda``.

=============
Running tests
=============

#. Install the following packages::

    $ pip install -e .[test]

#. Run the tests using `pytest`::

    $ pytest

======================
Building documentation
======================

#. Install the following packages::

    $ pip install -e .[docs]

#. Build the documentation using `make`::

   $ cd doc
   $ make html
