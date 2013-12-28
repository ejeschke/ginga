=============
+++++++++++++
The Ginga FAQ
+++++++++++++

--------------------------
Problems displaying images
--------------------------
No image shows in the display, and I get an error in the terminal about
histogram and keyword "density". 

.. note:: You need a slightly newer version of numpy.

	  I recommend getting at least numpy-1.6.1.

-------------
Miscellaneous
-------------

Can I get ds9-like user interface mappings?
-------------------------------------------
Save the file called called `bindings.cfg.ds9 
<https://raw.github.com/ejeschke/ginga/master/examples/bindings/bindings.cfg.ds9>`_
and drop it in your $HOME/.ginga folder as "bindings.cfg".
Then restart Ginga.

How can I customize the user interface mappings?
------------------------------------------------
There is more information in Section :ref:`sec-bindings`.

When are you going to add the XYZ feature that ds9 has?
-------------------------------------------------------
Maybe never.  The ginga package design goal was never to "replace ds9",
but to provide a full featured python FITS widget that we could use to
build stuff in python directly.  This is clearly seen if you look at all
the example programs in examples/*/example*.py.  The idea was to
make it easy for someone to build any kind of custom viewer, by having a
full-featured widget to build on.

That said, we did write a reference viewer, because we needed something
with many of the convenience features of a modern FITS viewer.  ds9 is
almost the size of a small OS, however, and I'm not sure it is wise to
try to match it feature for feature.  Instead, since Ginga is
plugin-based, you can write plugins to give you the features you need.
ds9 is a "everything including kitchen sink" kind of viewer, whereas
ginga reference viewer is more like a "take what you need from the
pantry and whip it up" type viewer.  

Please send a pull request!

-----------------------
World Coordinate System
-----------------------

What library are you using for WCS?
-----------------------------------
We are lucky to have several possible choices for a python WCS package
compatible with Ginga: 
`astLib <http://astlib.sourceforge.net/>`_, 
`kapteyn <http://www.astro.rug.nl/software/kapteyn/>`_,
`starlink <https://github.com/timj/starlink-pyast>`_ and
`astropy <https://github.com/astropy/astropy>`_.

kapteyn and astropy wrap Doug Calabretta's "WCSLIB", astLib wraps
Doug Mink's "wcstools", and I'm not sure what starlink uses (their own?).
Note that astlib and starlink require pyfits (or astropy) to be
installed in order to create a WCS object from a FITS header. 

To force the use of a particular one add this to your "general.cfg"
in $HOME/.ginga:

WCSpkg = 'package'

Replace 'package' with one of {'astropy', 'kapteyn', 'starlink' or
'astlib', 'choose'}.  If you pick 'choose' Ginga will try to pick one
for you. 

How easy is it for Ginga to support a custom WCS?
-------------------------------------------------
Pretty easy.  See Section :ref:`sec-custom-wcs`.


--------------------
I/O and File Formats
--------------------

What library are you using for FITS I/O?
----------------------------------------
There are two possible choices for a python FITS file reading package
compatible with Ginga: 
`astropy <https://github.com/astropy/astropy>`_ and
`fitsio <https://github.com/esheldon/fitsio>`_.  
Both are based on the CFITSIO library, although it seems that astropy's
version has changed quite a bit from the original, while fitsio is still
tracking the current version. 

To force the use of a particular one add this to your "general.cfg"
in $HOME/.ginga:

FITSpkg = 'package'

Replace 'package' with one of {'astropy', 'fitsio', 'choose'}.
If you pick 'choose', Ginga will try to pick one for you.

How easy is it for Ginga to support a new file formats besides FITS?
--------------------------------------------------------------------
Pretty easy.  See Section :ref:`sec-custom-io`.

