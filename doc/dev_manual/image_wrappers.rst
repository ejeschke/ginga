.. _ch-image-data-wrappers:

*******************
Image Data Wrappers
*******************

The image viewer can load data in a number of formats, but all formats
are wrapped with a class that corresponds to the *model* part of the
model-view-controller design used by Ginga.  These wrappers make the
data accessible in a common interface for the image viewer.  The most
common wrappers are ``AstroImage`` and ``RGBImage``, for single band
(i.e. "monchromatic") and multi-band (i.e. "RGB") data, respectively.

AstroImage
==========

An ``AstroImage`` combines image data with metadata (including keywords)
and optionally, world coordinate information.

Data can be loaded in a number of ways.  For the following examples,
assume that we created a wrapper object via::  

  >>> from ginga.AstroImage import AstroImage
  >>> img = AstroImage()

.. note:: Ginga provides extensive logging throughout the code, so if you
   are using a Python logger you can pass it to the constructor to have
   it log extra information about errors when methods on the image
   object are being used.  Assuming you had a logger configured as
   ``logger`` you would pass it like so:: 

     >>> img = AstroImage(logger=logger)

.. todo:: add a reference to the section on creating a logger

Once you have an object, you can load data directly contained in a
``numpy.ndarray``:: 

  >>> import numpy as np
  >>> data = np.random.randint(0, 10000, (2000, 3000), dtype=np.uint)
  >>> img.load_data(data)

.. note:: if you want to provide metadata (e.g. a separate set of
   FITS-type keywords) you can add it::

     >>> img.update_keywords(kw_dict)

From an ``astropy.io.fits.HDU``::

  >>> from astropy.io import fits
  >>> with fits.open("/path/to/image.fits") as fits_f:
  >>>     img.load_hdu(fits_f[0])

From an ``astropy.nddata.NDData`` (or subclass, like ``CCDData``)::

  >>> img.load_nddata(ndd_obj)

Files are best loaded from the appropriate file format loader module.
For a FITS file::

  >>> from ginga.util import io_fits
  >>> img = io_fits.load_file("/path/to/image.fits")

Or, e.g. to choose a particular HDU::

  >>> from ginga.util import io_fits
  >>> img = io_fits.load_file("/path/to/image.fits[SCI]")

.. todo:: add common API calls for AstroImage class

   
RGBImage
========

The ``RGBImage`` class is used to store conventional type 3 or 4-band
RGB images.

  >>> from ginga.RGBImage import RGBImage
  >>> img = RGBImage()

.. note:: ``RGBImage`` constructor also supports the ``logger`` keyword
   parameter described above::

     >>> img = RGBImage(logger=logger)


RGB images support the ``load_data`` method (note the shape and type of
the array):: 

  >>> data = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)
  >>> img.load_data(data)

Files can also be loaded from standard RGB formats (PNG, JPEG, etc)
using the ``io_rgb`` module::

  >>> from ginga.util import io_rgb
  >>> img = io_rgb.load_file("/path/to/image.jpg")


.. todo:: add common API calls for RGBImage class

