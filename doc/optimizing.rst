++++++++++++++++++++++
Optimizing Performance
++++++++++++++++++++++

There are several ways to optimize the performance of certain aspects of
Ginga's operation.

OpenCv Acceleration
-------------------
Ginga includes support for OpenCv accelerated operations (e.g. rotation
and rescaling).  *This support is used by default if the package is installed*.

To enable OpenCv support, install the python `opencv` module (you can
find it `here <https://pypi.python.org/pypi/opencv-python>`_).

OpenGl Acceleration
-------------------
Ginga includes support for OpenGL rendering with Qt or Gtk back ends.
To use this with the Reference Viewer, simply append the command line
option --opengl.  This can be particularly useful with high resolution
displays.

Note that certain aspects of normal rendering for Ginga canvas objects
are unavailable or different with OpenGL:

* Inability to specify ``linestyle`` parameter (lines are always solid)
* Inability to specify ``linewidth`` parameter (always defaults to 1)

