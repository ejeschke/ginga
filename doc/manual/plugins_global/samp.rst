.. _sec-plugins-SAMP:

SAMP Control
------------

.. image:: figures/SAMP-plugin.png
   :align: center

Ginga includes a plugin for enabling SAMP (Simple Applications Messaging
Protocol) support.  With SAMP support, Ginga can be controlled and
interoperate with other astronomical desktop applications.

The SAMP module is not started by default.  To start it when Ginga
starts, specify the command line option::

    --modules=SAMP

otherwise, start it using `Start SAMP` from the `Plugins` menu.

Currently, SAMP support is limited to `image.load.fits` messages,
meaning that Ginga will load a FITS file if it receives one of these
messages.

Ginga's SAMP plugin uses the astropy.vo,samp module, so you will need to
have that installed to use the plugin.  By default, Ginga's SAMP plugin
will attempt to start a SAMP hub if one is not found running.
