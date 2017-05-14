.. _ginga-faq:

+++++++++++++
The Ginga FAQ
+++++++++++++

---------
Platforms
---------

Does Ginga run on Mac/Windows/Linux/XYZ?
----------------------------------------
Ginga is written entirely in the Python programming language, and uses only 
supporting Python packages.  As long as a platform supports Python 
and the necessary packages, it can run some version of Ginga.  On recent 
Linux, Mac and Windows versions, all of these packages are available.

Does Ginga work with Python 3?
------------------------------
Yes. Just install with Python 3.  Of course, you need all the
supporting modules for Python 3 (NumPy, SciPy, Qt 5, etc.)

--------
Toolkits
--------

What GUI toolkit does Ginga use?
--------------------------------
It depends what exactly you want to run. Ginga is both a toolkit for
building viewers and also includes a "reference viewer".  The example
programs currently support Qt, GTK, Tk, matplotlib and web browser via
HTML5 canvas.  Some other toolkits are being worked on and may be
partially supported.

The full reference viewer currently supports Qt and Gtk.  The difference
is explained here, in Section :ref:`ch-programming-ginga`.

Can Ginga work with PyQt5?
--------------------------
Yes.

Can Ginga work with Gtk3?
-------------------------
Yes, although the performance is not on par with Gtk2 yet. Cairo for
Python 3 still lacks the important ImageSurface.create_for_data()
API call, so we have to use a workaround. Detailed instructions can be found in Section :ref:`ch-install`.

----------------
Control Bindings
----------------

Can I get DS9-like user interface mappings?
-------------------------------------------
Save the file called `bindings.cfg.ds9
<https://raw.github.com/ejeschke/ginga/master/examples/bindings/bindings.cfg.ds9>`_
and drop it in your $HOME/.ginga folder as "bindings.cfg".
Then restart Ginga.

Can I customize the user interface mappings?
--------------------------------------------
Yes. There is more information in the :ref:`sec-bindings` section.

Where can I find a quick reference of the bindings?
---------------------------------------------------
See Section :ref:`ginga-quick-reference`.

-------------
Miscellaneous
-------------

Does Ginga work with IRAF (a la DS9)?
-------------------------------------
Yes. See Section :ref:`sec-plugins-IRAF`.

Does Ginga work with SAMP?
--------------------------
Yes. See Section :ref:`sec-plugins-SAMP`.

Is it possible to control Ginga remotely?
-----------------------------------------
Yes. See Section :ref:`sec-plugins-RC`.

When are you going to add the XYZ feature that DS9 has?
-------------------------------------------------------
Maybe never.  The Ginga package design goal was never to replace DS9,
but to provide a full featured Python FITS widget that we could use to
build directly in Python.  This is clearly seen if you look at the 
example programs in examples/*/example*.py.  The idea was to make it 
easy for someone to build any kind of custom viewer by having a
full-featured widget to build on.

That said, we did write a reference viewer because we needed something
with many of the convenience features of a modern FITS viewer.  DS9 is
almost the size of a small OS, however, and I'm not sure it is wise to
try to match it feature for feature.  Instead, since Ginga is
plugin-based, you can write plugins to give you the features you need.
DS9 is a "everything including kitchen sink" kind of viewer, whereas
ginga reference viewer is more like a "take what you need from the
pantry and whip it up" type viewer.

Please send a pull request!

-----------------------
World Coordinate System
-----------------------

What library are you using for WCS?
-----------------------------------
We are lucky to have several possible choices for a Python WCS package
compatible with Ginga:
`AstLib <http://astlib.sourceforge.net/>`_,
`Kapteyn <http://www.astro.rug.nl/software/kapteyn/>`_,
`Starlink <https://github.com/timj/starlink-pyast>`_ and
:ref:`Astropy WCS <astropy:astropy-wcs>`.

Kapteyn and Astropy wrap Mark Calabretta's "WCSLIB", astLib wraps
Jessica Mink's "wcstools", and I'm not sure what Starlink uses.
Note that Astlib and starlink require pyfits (or Astropy) to be
installed in order to create a WCS object from a FITS header.

To force the use of a particular one add this to your "general.cfg"
in $HOME/.ginga:

WCSpkg = 'package'

Replace 'package' with one of {'Astropy', 'Kapteyn', 'Starlink' or
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
There are two possible choices for a Python FITS file reading package
compatible with Ginga:
:ref:`Astropy FITS <astropy:astropy-io-fits>` and
`fitsio <https://github.com/esheldon/fitsio>`_.
Both are originally based on the CFITSIO library (although Astropy's
version uses very little of it any more, while fitsio is still
tracking the current version).

To force the use of a particular one add this to your "general.cfg"
in $HOME/.ginga:

FITSpkg = 'package'

Replace 'package' with one of {'Astropy', 'fitsio', 'choose'}.
If you pick 'choose', Ginga will try to pick one for you.

How easy is it for Ginga to support a new file formats besides FITS?
--------------------------------------------------------------------
Pretty easy.  See Section :ref:`sec-custom-io`.

--------------------------
Problems Displaying Images
--------------------------
Nothing changes in the image when I change settings under "Preferences".

.. note:: The Preferences plugin sets the preferences on a *per-channel*
	  basis.  Make sure the channel you are looking at has the same
	  name as the prefix for the preferences.  For example: "Image"
	  and "Image: Preferences" or "Image1" and "Image1: Preferences".

          The preferences for a given channel are copied from the
	  default "Image" channel until they are explicitly set and
	  saved using this plugin.  So if you want preferences that
	  follow around from channel to channel, save them as
	  preferences for "Image" and any new channels created will get
	  those as well, unless you have saved different ones under
	  those channel names.

Nothing changes in the image when I change the "Auto Cuts" settings under
Preferences.  I've checked that I'm adjusting preferences for the same
channel that I'm viewing.

.. note:: What is the setting for "Cut New" under the New Images section
	  in Preferences for this channel?

          If that setting is "Off" then you have elected not to have
	  Ginga apply Auto Levels when an image is loaded in that
	  channel.  Press 'a' in the image window to force an auto cut
	  levels--it will use the new settings.

No image shows in the display, and I get an error in the terminal about
histogram and keyword "density".

.. note:: You need a slightly newer version of NumPy.

          I recommend getting at least NumPy>1.7.

