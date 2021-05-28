++++++++++++++++++++++
Optimizing Performance
++++++++++++++++++++++

There are several ways to optimize the performance of certain aspects of
Ginga's operation.

OpenCL Acceleration
-------------------
Ginga includes support for OpenCL accelerated array operations for some
operations (e.g. rotation).  *This support is not enabled by default*.

To enable OpenCL support, install the `pyopencl` module, e.g.::

    pip install pyopencl

If you are building your own program using a ginga viewer widget, simply
enable the support by::

    from ginga import trcalc
    trcalc.use('opencl')

If you are using the reference viewer, you can add the command line
option `--opencl` to enable support.

Alternatively, you can add the following line to your Ginga general options configuration file
(`$HOME/.ginga/general.cfg`)::

    use_opencl = True

.. note:: `pyopencl` may prompt you if it can't figure out which device
          is the obvious choice to use as for hardware acceleration. If
          so, you can set the `PYOPENCL_CTX` variable to prevent being
          prompted in the future.

          Example of being prompted by `pyopencl` package::

              $ ginga
              NVIDIA: no NVIDIA devices found
              Choose platform:
              [0] <pyopencl.Platform 'Intel(R) OpenCL' at 0x2d95fd0>
              [1] <pyopencl.Platform 'Clover' at 0x7f13f3ffcac0>
              Choice [0]:
              Set the environment variable PYOPENCL_CTX='' to avoid
              being asked again.


OpenCv Acceleration
-------------------
Ginga includes support for OpenCv accelerated operations (e.g. rotation
and rescaling).  *This support is used by default if the package is installed*.

To enable OpenCv support, install the python `opencv` module (you can
find it `here <https://pypi.python.org/pypi/opencv-python>`_).


numexpr Acceleration
--------------------
Ginga can use the `numexpr` package to speed up rotations.  However,
this is only used if the OpenCL and OpenCv optimizations are not being
used and the performance gain is not nearly as dramatic as with the
latter.

To enable `numexpr` acceleration, simply install the package, e.g.::

    pip install numexpr

It will be automatically detected and used when appropriate.
