++++++++++++++++++++++++++++++++++++++++++++
Detailed Installation Instructions for Ginga
++++++++++++++++++++++++++++++++++++++++++++

===========
Dependences
===========

Ginga is written entirely in Python, and only uses supporting Python
packages.  There is nothing to compile, unless you need to compile one
of the supporting packages.

On recent Linux, Mac and Windows versions, all of the packages are
available in binary (installable) form; it should not be necessary to
compile anything.  But as always, YMMV.

You will need:

* python (v. 2.7 or higher)
* numpy

Highly recommended, because some features will not be available without it:

* scipy

For opening FITS files you will need ONE of (astropy recommended):

* astropy
* pyfits
* fitsio

For WCS resolution you will need ONE of:

* kapteyn
* astLib
* starlink
* astropy

Also, depending on which GUI toolkit you prefer (and what you want to
do), you will need either: 

* python-gtk
* python-cairo

OR

* python-qt4

OR

* python-pyside (qt4 alternative)

OR

* python-Tkinter

OR

* matplotlib

Certain plugins in the reference viewer (or features of those plugins)
will not work without the following packages:

* matplotlib (Pick, Cuts, Histogram)
* webkit (WBrowser (online help))

Helpful, but not necessary (may optimize or speed up certain
operations):

* python-numexpr
* python-magic

==============================
Notes on Supported Widget Sets
==============================

In the discussion below, we differentiate between the Ginga viewing
widget, such as used in the examples/\*/example\*.py programs and the full
reference viewer, which includes many plugins (scripts/ginga).

.. note:: For the full reference viewer, Mac and Windows users
	  should probably install the Qt version, unless you are
	  the tinkering sort.  Linux can use either Qt or Gtk fine.

Qt/PySide
=========

Ginga can use either PyQt or PySide, version 4.  It will auto-detect
which one is installed.  There is support for both the basic widget and
the full reference viewer.
  
.. note:: If you have both installed and you want to use a specific one
	  then set the environment variable QT_API to either "pyqt" or
	  "pyside".  This is the same procedure as for Matplotlib.


Gtk
===

Ginga can use Gtk version 2 or 3, but at the present time only Gtk 2 is
supported for the full reference viewer, due to some dependences in the
plugins to version 2.  The viewing widget by itself is fine with either
version.  Ginga will auto-detect which versions are installed and
default to version 2 if available.

Tk
===

Ginga's Tk support is limited to the viewing widget itself.  For
overplotting (graphics) support you also need to build and install the
"aggdraw" module, which you can find 
`here <http://ejeschke.github.io/aggdraw/>`_.

Matplotlib
==========

Ginga can render directly into a Matplotlib figure.  Support is limited
to the viewing widget itself.  Any of the backends that Matplotlib
supports is usable.  Performance is not as good as to one of the
"native" backends listed above, but oh, the overplot options!


========================
Installation from Source
========================

Clone from github::

    $ git clone https://github.com/ejeschke/ginga.git

Or see links on `this page <http://ejeschke.github.io/ginga/>`_
to get a zip or tar ball.

Unpack, go into the top level directory and:: 

    $ python setup.py install

The reference viewer can then be run using the command "ginga"

Alternatively you can download and install via `pip`::

    $ pip install ginga

==============================
Platform Specific Instructions
==============================

Linux
=====

Install the necessary dependences.  If you are on a relatively recent
version of Ubuntu, something like the following will work::

    $ apt-get install python-numpy python-scipy python-matplotlib \
      python-pyfits python-pywcs python-gtk python-cairo python-webkit \
      python-magic git pip

Or::

    $ apt-get install python-numpy python-scipy python-matplotlib \
      python-pyfits python-pywcs python-qt4 python-webkit python-magic \
      git pip

(if you want to use the Qt version)

.. note:: `astropy` is preferred over pyfits + pywcs, but was not in the
	  default repositories as of this writing.  Use "pip install
	  astropy" to install it if you like.

Then install ginga with pip::

    $ pip install ginga

or by obtaining the source and installing as described above.


Mac
===

The two recommended ways to install on the Mac are:

* Install from `macports <http://www.macports.org/>`_
* Install from `homebrew <http://brew.sh/>`_

Either method should provide all the modules necessary to run
Ginga.  Then install Ginga from source as described above.

With macports you will need to install the necessary packages.  Assuming 
that you have a working macports installed, it will be something like::

    port install python27 
    port install py27-numpy py27-matplotlib py27-pil py27-scipy 
    port install py27-astropy py27-pyqt4 py27-pip
    pip install ginga

Have a cup of your favorite beverage.  It takes a while to compile all these!


Windows
=======

Binary packages corresponding to all the ones described in the Linux
section are available online.

Install the necessary dependences and then install Ginga from source as
described above. 

.. note:: We need help from someone who runs Mac or Windows and is
	  skilled enough to make better (e.g. all-in-one) binary
	  installation packages! 

	  Please contact us if you can help.

