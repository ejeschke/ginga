.. _ch-programming-internals:

+++++++++++++++
Ginga Internals
+++++++++++++++

This chapter explains the secret inner workings of Ginga and its classes
so that you can subclass them and use them in your own applications.

Introduction
============

Ginga uses a version of the `Model-View-Controller
design pattern <http://en.wikipedia.org/wiki/Model_view_controller>`_.
The MVC pattern spells out a division of responsibilities and
encapsulation where the Model provides various ways to access and
interface to the data, the View provides ways to display the data and
the Controller provides the methods and user interface hooks for
controlling the view.

The Model
---------

.. _fig-astroimage:
.. figure:: figures/class_structure_astroimage.png
   :scale: 100%
   :figclass: h

   Hierarchy of Ginga ``AstroImage`` class

The Model classes are rooted in the base class ``BaseImage``.  The basic
interface to the data is expected to be a Numpy-like array object that is
obtained via the ``get_data()`` method on the model.  It also provides
methods for obtaining scaled, cutouts and transformed views of the data,
and methods for getting and setting key-value like metadata.

There are two subclasses defined on BaseImage: ``RGBImage`` and
``AstroImage``.  RGBImage is used for displaying 3 channel RGB type
images such as JPEG, TIFF, PNG, etc.  AstroImage is the subclass used to
represent astronomical images and its organization is shown in
Figure :ref:`fig-astroimage`.  It has two delegate objects devoted to
handling World Coordinate System transformations and file IO.

New models can be created, subclassing from BaseImage or AstroImage.
As long as the model
`duck types <http://en.wikipedia.org/wiki/Duck_typing>`_ like a BaseImage
it can be loaded into a view object with the ``set_image()`` method.
AstroImage provides a few convenience methods for accessing WCS information
from the attached "wcs" attribute.

The View
--------

.. _fig-imageviewer:
.. figure:: figures/class_structure_viewer.png
   :scale: 100%
   :figclass: h

   Class structure of Ginga basic widget viewer

Figure :ref:`fig-imageviewer` shows the class inheritance of the
``CanvasView`` class, which is the prototypical viewer class to use in a
program.
The viewer is rooted in the base class ``ImageViewBase``, which
contains the settings that control the view, such as scale (zoom),
pan position, rotation, transformation, etc along with a large number of
methods to manipulate the viewer.
Ginga supports "backends" for different widget sets (Qt, Gtk, Tk,
etc.) through various subclasses of this base class, which provide an
native window or canvas widget that can be painted with the resulting
RGB[A] image produced by a renderer.  A ``CanvasView`` viewer can be
created for any supported back end.

Every viewer has a dedicated renderer as a delegate object.
Renderers are also arranged in a hierarchical class structure.
The base renderer class is ``RenderBase``, which specifies an abstract
base class that should be implemented to render a Ginga canvas onto a
back end-specific viewer.

The Controller
--------------

The control interface is a combination of methods on the view object and
a pluggable ``Bindings`` class which handles the mapping of user input
events such as mouse, gesture and keystrokes into methods in the viewer.
There are many callback functions that can be registered,
allowing the user to create their own custom user interface for
manipulating the view.

``CanvasView`` connects various user interface events (mouse/cursor,
keystrokes, etc.) with methods in the ``BindingMapper`` and ``Bindings``
delegate objects to implement most of the user event handling logic.
With this layered class construction combined with appropriate delegate
objects, it is possible to minimize the widget specific code and reuse a
large amount of code across widget sets and platforms.
This architecture makes it a fairly simple process to port the basic Ginga
functionality to a new widget set.  All that is required is that the new
widget set have some kind of native widget that supports painting an RGB
image (like a canvas or image widget) and a way to register for user
interaction events on that widget.


Graphics on Ginga
=================

.. _fig-drawingcanvas:
.. figure:: figures/class_structure_drawingcanvas.png
   :scale: 100%
   :figclass: h

   Class structure of Ginga ``DrawingCanvas`` class.

Ginga's graphics are all rendered from objects placed on a Ginga canvas,
including images.
A Ginga canvas is a bit different from other types of canvases used in
other graphics programs. For one thing, it has no inherent color or
scale in any type of unit; it acts as a container for other graphics
objects that are stacked in a particular order.  A canvas itself is an
object that can be placed on a canvas and so it is quite straightforward
to have canvases nested in canvases or several canvases stacked together
on one canvas, etc.
The type of canvas that you will see used most frequently (primarily for
its flexibility) is the ``DrawingCanvas``, so named because it not only
allows all the typical objects to be placed on it, but it also has
methods that allow the user to draw or edit objects interactively on it.
The relationship of a viewer to a canvas is that the viewer displays
a canvas with a certain scale, rotation, transformations, color-mapping,
pan position, etc.  A canvas might be shared with another viewer which
has different settings for those things.

All objects that can be drawn by Ginga (e.g. placed in a canvas) are
decended from the ``CanvasObjectBase`` type, and made by using
subclasses or composing with mixin classes to derive new object types.
We will use the general term "Ginga canvas objects" to describe these
various entities.
In Figure :ref:`fig-drawingcanvas` we can see that a ``DrawingCanvas``
is a composite of a ``UIMixin`` (user-interface mixin), a
``DrawingMixin`` and a ``Canvas``.  A ``Canvas`` in turn is a composite
of a ``CanvasMixin`` and a ``CompoundObject``. A ``CompoundObject``
is a composite of a ``CompoundMixin`` and a ``CanvasObjectBase``.

Other Ginga canvas objects have a simpler pedigree. For example, a
``Box`` is a composite of a ``OnePointTwoRadiusMixin`` and a
``CanvasObjectBase``--so is an ``Ellipse``.  The use of these mixin
classes allows common functionality and attributes to be shared where
the similarities allow.

For more information on canvases and canvas objects, refer to
Chapter:ref:`_ch-canvas_graphics`.


Renderers
=========

Every viewer delegates the actual drawing of its canvas to a *renderer*.
Renderers all descend from ``RenderBase`` (in ``ginga.canvas.render``) and
fall into two broad styles:

* **Standard pixel renderers** (``pil``, ``agg``, ``opencv``, ``cairo``, the
  Qt ``qt`` renderer, ...) subclass ``StandardPipelineRenderer``.  They run a
  CPU *pipeline* (``createbg`` -> ``overlays`` -> ``iccprofile`` ->
  ``flipswap`` -> ``rotate`` -> ``output``) that composites the image and
  overlays into an RGBA array, and draw vector graphics (shapes, text) on top
  with the backend's 2D drawing API.

* **GPU / vector-replay renderers** (``opengl`` and ``vulkan``) additionally
  mix in ``VectorRenderMixin`` (in ``ginga.vec.CanvasRenderVec``).  Rather
  than run the CPU pipeline, they *record* every draw operation into a render
  list (via a recording ``RenderContext`` returned by ``setup_cr()``) and
  *replay* it onto the GPU each frame (``draw_vector()``).  Images are handed
  to the GPU as textures and colormapped in a fragment shader; shapes are
  drawn from vertex buffers.  This is the model a GPU renderer needs, because
  zoom/pan/rotate become cheap transform changes rather than re-rasterization.

A renderer is chosen with the ``renderer`` viewer setting (or the reference
viewer's ``-r/--renderer`` option); each backend viewer keeps a list of
renderers it can host and picks the first that initializes, so a request for
an unavailable renderer falls back gracefully.  The factory
``ginga.canvas.render.get_render_class(name)`` maps a name to a class.


The standard pixel renderer
---------------------------

``StandardPipelineRenderer`` (in ``ginga.canvas.render``) composites a frame
on the CPU by running a :class:`~ginga.util.pipeline.Pipeline` of *stages*
(each stage transforms a Numpy array and passes it to the next); the stages
live in ``ginga.util.stages.render``:

#. **createbg** -- allocate the background array at the window size and fill
   it with the viewer's background color.
#. **overlays** -- draw every image on the canvas into that array (see the
   per-image sub-pipeline below).
#. **iccprofile** -- apply an output ICC color profile, if one is configured.
#. **flipswap** -- apply the viewer's flip/swap-axes transforms.
#. **rotate** -- apply the viewer's rotation.
#. **output** -- deliver the array in the RGB(A) channel order the backend
   wants.

The result is a single RGBA array; the backend then draws the vector graphics
(shapes, text, ...) on top of it using its native 2D drawing API, via the
``RenderContext`` returned by ``setup_cr()``.  (This is the key difference
from the GPU renderers, which record *all* drawing -- images included -- into
a render list and replay it on the GPU.)

The ``whence`` optimization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Re-running the whole pipeline for every little change would be wasteful, so
every redraw carries a ``whence`` value: a hint of *what* changed, and hence
how far *down* the pipeline the work must start.  A lower ``whence`` means
more of the pipeline must re-run.  ``render_whence()`` looks the value up in a
table and runs the pipeline from the first stage whose threshold it meets:

======  ==============  =========================================
whence  runs from       typically triggered by
======  ==============  =========================================
<= 2.0  overlays        new data, zoom, pan, cut levels, colormap
<= 2.3  iccprofile      ICC output profile change
<= 2.5  flipswap        flip / swap-axes transform
<= 2.6  rotate          rotation
>= 3.0  (none)          only the vector graphics changed (e.g. fg)
======  ==============  =========================================

Within the **overlays** stage, each image runs its own small sub-pipeline
(``Scale`` -> ``Reorder`` -> ``Cuts`` -> ``RGBMap`` -> ``Merge`` for a
``normimage``), and ``whence`` selects the entry point there too: ``<= 0``
re-scales the cutout (new data / zoom / pan), ``<= 1`` re-applies the cut
levels, ``<= 2`` re-applies the RGB/color mapping, and anything higher just
re-merges the already-mapped tile into the background.  So dragging the cut
levels (``whence=1``) recuts and remaps but does not re-scale, while rotating
(``whence=2.6``) reuses the fully composited image and only re-rotates.

The GPU renderers use the same ``whence`` values but interpret them
differently -- since images live in GPU textures, most changes become
transform/uniform updates rather than re-running CPU stages.


The Vulkan renderer
-------------------

The Vulkan renderer (``renderer='vulkan'``, in ``ginga.vulkan``) is a
GPU-native, toolkit-agnostic renderer offered as an alternative to OpenGL
(which is being deprecated on some platforms).  It is *offscreen*: it renders
into a Vulkan image in GPU memory and copies the result back to a Numpy array,
which every backend can display via the same array path used by the
``pil``/``agg`` renderers.  There is no per-toolkit Vulkan window yet, so the
same renderer works for the qt, gtk3, gtk4, tk and pg (web/websocket) backends
(but *not* in-situ under Pyodide/PyScript, where the native binding and driver
are unavailable).

Requirements: the optional ``vulkan`` dependency (``pip install
ginga[vulkan]``, the PyPI Vulkan binding) plus a system Vulkan loader and a
device.  Mesa **lavapipe** provides a CPU/headless device, which is enough for
CI and machines without a GPU.

How it fits together (all under ``ginga/vulkan/``):

* ``vkcore.VulkanContext`` wraps the instance/device/queue/command pool and
  the buffer/image/texture/sampler helpers.  ``OffscreenColorTarget`` is the
  RGBA image drawn into and read back.
* ``pipelines.py`` holds the graphics pipelines: ``ShapePipeline`` (solid
  shapes and expanded wide/dashed lines), ``MultiImagePipeline`` (any number
  of images per frame, each with its own cached texture) and ``GlyphPipeline``
  (text tiles).  Shaders are GLSL compiled to SPIR-V, shipped as ``.spv`` under
  ``ginga/vulkan/glsl/`` (regenerate with ``glsl/compile.sh``; no runtime
  shader compiler is required).
* ``CanvasRenderVk.CanvasRendererGPU`` is the renderer.  It mixes
  ``VectorRenderMixin`` with ``StandardPipelineRenderer`` (for the coordinate
  bookkeeping only -- the CPU pipeline stages are not run), records draw ops,
  and in ``get_surface_as_array()`` replays them through a ``VulkanReplayEngine``
  that drives the pipelines into the shared render pass, then reads the pixels
  back.

Notable design points that a maintainer should know:

* **Colormapping is on the GPU.**  A monochrome image is uploaded as a raw
  ``R32_SFLOAT`` texture; the fragment shader applies the cut levels and indexes
  a colormap texel buffer built from the viewer's ``rgbmap`` (the color
  distribution is baked into that lookup table, as in the OpenGL renderer).  So
  cut-level, distribution and colormap changes update live *without*
  re-uploading the image.  RGB images shown through a ``normimage`` get the
  same interactive treatment per channel; images shown through the plain
  ``image`` type are drawn as native RGBA.
* **Textures are cached and only re-uploaded on change.**  Zoom and pan reuse
  the cached texture and just change the transform, so they never re-cut or
  re-upload -- the GPU stretches the texture over the new quad, analogous to
  OpenGL moving the camera.
* **Clip space.**  Vulkan clip space has Y pointing *down* (like window
  pixels, unlike OpenGL's Y-up) and depth in ``[0, 1]``.  The 2D path maps
  window pixels straight to clip space with no Y-flip; the 3D camera path
  reuses ``ginga.opengl.Camera`` and applies a small correction matrix to the
  projection.
* **No native primitives for everything.**  As with OpenGL, Vulkan does not
  guarantee line widths greater than 1 or line stippling, and has no text
  primitive.  Wide and dashed lines are expanded into filled triangles
  (``ginga.canvas.stroke``) and text is rasterized with Pillow into an RGBA
  tile and blitted as a textured quad.

To try it in the reference viewer::

    ginga -t qt -r vulkan

or select ``vulkan`` from the renderer control in the ``gw`` example viewers.
A headless smoke test is ``ginga/tests/test_vulkan_*.py`` (these skip
automatically when the binding or a device is missing).


Miscellaneous Topics
====================

.. _sec-custom-wcs:

I want to use my own World Coordinate System!
---------------------------------------------

No problem.  Ginga encapsulates the WCS behind a pluggable object used
in the AstroImage class.  Your WCS should implement this abstract class:

.. code-block:: python

    def MyWCS(object):
        def __init__(self, logger):
            self.logger = logger

        def get_keyword(self, key):
            return self.header[key]

        def get_keywords(self, *args):
            return [self.header[key] for key in args]

        def load_header(self, header, fobj=None):
            pass

        def pixtoradec(self, idxs, coords='data'):
            # calculate ra_deg, dec_deg
            return (ra_deg, dec_deg)

        def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
            # calculate x, y
            return (x, y)

        def pixtosystem(self, idxs, system=None, coords='data'):
            return (deg1, deg2)

        def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
            return [[ra_deg_0, dec_deg_0], [ra_deg_1, dec_deg_1], ...,
                    [ra_deg_n, dec_deg_n]]

        def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
            return [[x0, y0], [x1, y1], ..., [xn, yn]]

To use your WCS with Ginga create your images like this:

.. code-block:: python

    from ginga.AstroImage import AstroImage
    AstroImage.set_wcsClass(MyWCS)
    ...

    image = AstroImage()
    ...
    view.set_image(image)

or you can override the WCS on a case-by-case basis:

.. code-block:: python

    from ginga.AstroImage import AstroImage
    ...

    image = AstroImage(wcsclass=MyWCS)
    ...
    view.set_image(image)

You could also subclass AstroImage or BaseImage and implement your own
WCS handling.  There are certain methods in AstroImage used for graphics
plotting and plugins, however, so these would need to be supported if
you expect the same functionality.

.. _sec-custom-io:

I want to use my own file storage format, not FITS!
---------------------------------------------------

First of all, you can always create an ``AstroImage`` and assign its
components for wcs and data explicitly.  Assuming you have your data
loaded into an ``numpy`` array named ``data``:

.. code-block:: python

    from ginga import AstroImage
    ...

    image = AstroImage()
    image.set_data(data)

To create a valid WCS for this image, you can set the header in the
image (this assumes ``header`` is a valid mapping of keywords to values):

.. code-block:: python

    image.update_keywords(header)

An ``AstroImage`` can then be loaded into a viewer object with
``set_dataobj()``.  If you need a custom WCS see the notes in Section
:ref:`sec-custom-wcs`.
If, however, you want to add a new type of custom loader into Ginga's
file loading framework, you can do so using the following instructions.

Adding a new kind of file opener
--------------------------------

Ginga's general file loading facility breaks the loading down into two
phases: first, the file is identified by its ``magic`` signature
(requires the optional Python module ``python-magic`` be installed) or MIME
type.  Once the general category of file is known,
methods in the specific I/O module devoted to that type are called to
load the file data.

The `ginga.util.loader` module is used to register file openers. An
opener is a class that understand how to load data objects from a
particular kind of file format.

For implementing your own special opener, take a look at the
``BaseIOHandler`` class in `ginga.util.io.io_base`. This is the base
class for all I/O openers for Ginga.  Subclass this class, and implement
all of the methods that raise ``NotImplementedError`` and optionally
implement any other methods marked with the comment "subclass should
override as needed".  You can study the `io_fits` and `io_rgb` modules
to see how these methods are implemented for specific formats.
Here is an example opener class for HDF5 standard image files:

.. literalinclude:: code/io_hdf5.py

Once you have created your opener class (e.g. ``HDF5FileHandler``), you
can register it by:

.. code-block:: python

    from ginga.util import loader
    import io_hdf5
    loader.add_opener(io_hdf5.HDF5FileHandler, ['application/x-hdf'])

If you want to use this with the Ginga reference viewer, a good place to
register the opener is in your ``ginga_config.py`` as discussed in
Section :ref:`sec-workspaceconfig` of the Reference Viewer Manual.
The best place is probably by implementing ``pre_gui_config`` and
registering it as shown above in that function.
Once your loader is registered, you will be able to drag and drop files
and use the reference viewers regular loading facilities to load your data.

Changes to Ginga API in v4.0.0
------------------------------
Prior to Ginga v4.0.0, it was possible to use a *combination* viewer and
canvas--a viewer object that acts also like a ginga canvas.  These were
accessible via the `ImageViewCanvas*` classes.

In Ginga v4.0.0 these "dual entity" classes have been removed, to
simplify the code and clearly delineate the use of each kind of object:
a viewer shows the contents of a canvas for some backend, whereas a
canvas contains the items to be viewed (and can be shared by viewers).

If you have legacy code that is making canvas API calls on the viewer,
you simply need to use the `get_canvas()` method on the viewer to get the
canvas object and then make the canvas API call on that.


Porting Ginga to a New Widget Set
---------------------------------

[*TBD*]
