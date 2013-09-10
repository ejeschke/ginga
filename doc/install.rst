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
* python-numpy

Highly recommended, because some features will not work without them:

* python-scipy
* python-astropy

Also, depending on which GUI toolkit you prefer, you will need either:

* python-gtk
* python-cairo

OR

* python-qt4

OR

* python-pyside (qt4 alternative)

OR

* python-Tkinter

*NOTE*

* Mac and Windows platforms should probably install the Qt version,
unless you are adventurous.  Either one works fine on Linux.
* The Tk version of Ginga supports only the widget and example programs,
not the full reference viewer.

Certain plugins in the reference viewer (or features of those plugins)
will not work without the following packages:

* python-matplotlib (Pick, Cuts, Histogram)
* python-webkit (WBrowser (online help))

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

====================
Binary Installations
====================

Linux
=====

Install the necessary dependences.  If you are on a relatively recent
version of Ubuntu, something like the following will work::

    $ apt-get install python-numpy python-scipy python-matplotlib \
      python-pyfits python-pywcs python-gtk python-cairo python-webkit
      git pip

Or::

    $ apt-get install python-numpy python-scipy python-matplotlib \
      python-pyfits python-pywcs python-qt4 python-webkit git pip

(if you want to use the Qt version)

.. note:: `astropy` is preferred over pyfits + pywcs, but was not in the
	  default repositories as of this writing.

Then install ginga with pip::

    $ pip install ginga

or by obtaining the source and installing as described above.


Mac
===

The three recommended ways to install on the Mac are:

* Install the Enthought python distribution
* Install the Anaconda python distribution
* Install from macports

The first two methods should provide all the modules necessary to run
Ginga.  Then install Ginga from source as described above.

With macports you will need to install the necessary packages as
described in the Linux section.

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

