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

When are you going to add the XYZ feature that ds9 has?
-------------------------------------------------------
Maybe never.  The ginga package design goal was never to "replace ds9",
but to provide a full featured python FITS widget that we could use to
build stuff in python directly.  This is clearly seen if you look at all
the example programs in scripts/example{1,2}_xyz.py.  The idea was to
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

How easy is it for Ginga to support a custom WCS?
-------------------------------------------------
Pretty easy.  See Section :ref:`sec-custom-wcs`.

How easy is it for Ginga to support a new file formats besides FITS?
--------------------------------------------------------------------
Pretty easy.  See Section :ref:`sec-custom-io`.

