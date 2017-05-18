.. _sec-plugins-lineprofile:

LineProfile
===========

.. image:: figures/lineprofile-plugin.png
   :align: center
   :width: 600px

.. warning::

   There are no restrictions to what axes can be chosen.
   As such, the plot can be meaningless.

The ``LineProfile`` plugin is used for multidimensional (i.e., 3D or higher)
images. It plots the values of the pixels at the current cursor
position through the selected axis; or if a region is selected, it plots the
mean in each frame. This can be used to create normal spectral line profiles.
A marker is placed at the data point of the currently displayed frame.

Displayed X-axis is constructed using ``CRVAL*``, ``CDELT*``, ``CRPIX*``,
``CTYPE*``, and ``CUNIT*`` keywords from FITS header. If any of the keywords are
unavailabled, the axis falls back to ``NAXIS*`` values instead.

Displayed Y-axis is constructed using ``BTYPE`` and ``BUNIT``. If they are not
available, it simply labels pixel values as "Flux".


Usage
-----

1. Select an axis.
2. Pick a point or draw a region using the cursor.
3. Use :ref:`sec-plugins-multidim` to change step values of axes, if applicable.

.. automodule:: ginga.rv.plugins.LineProfile
