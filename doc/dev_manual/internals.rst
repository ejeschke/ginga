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
There is also a mixin class, ``LayerImage`` that can be used to create
layered images with alpha compositing on each layer.

New models can be created, subclassing from BaseImage or AstroImage.
As long as the model
`duck types <http://en.wikipedia.org/wiki/Duck_typing>`_ like a BaseImage
it can be loaded into a view object with the ``set_image()`` method.
AstroImage provides convenience methods for accessing WCS information
that may be necessary when using the model in canvas subclasses of a
View that allow graphics drawing.

The View
--------

.. _fig-imageviewzoom:
.. figure:: figures/class_structure_viewer.png
   :scale: 100%
   :figclass: h

   Class structure of Ginga basic widget viewer

Figure :ref:`fig-imageviewzoom` shows the class inheritance of the
ImageViewZoom class, which is a typical end class to use in a program if
one is not planning to do any graphical overplotting.  The figure key
indicates the base class verses the widget specific classes.

The View classes are rooted in the base class ``ImageView``, which
handles image display, scaling (zooming), panning, manual cut levels,
auto cut levels, color mapping, transformations, and rotation.
The ImageView is quite powerful compared to base classes in most
inheritance designs, as it actually renders the view all the way out to
RGB image planes in the appropriate sizes for the widget target window.
Ginga supports "backends" for different widget sets (Gtk, Qt, Tk,
etc.) through various subclasses of this base class, which do the actual
painting of the resulting RGB image into a widget in the native widget set.

In this example, ``ImageViewXYZ`` is a class that renders to a native
widget in the "XYZ" toolkit.  ``ImageViewEvent`` adds event handlers for
various pointing and keyboard events, but without connecting them to any
particular handling scheme.  Finally, ``ImageViewZoom`` provides a
concrete implementation of event handling by connecting the handlers in
the ImageViewEvent class with the logic in the ``BindingMapper`` and
``Bindings`` delegate objects as will as some logic in the ``UIMixin``
class.  This event handling scheme is described in more detail in the
section on the Controller.  With this layered class construction, it is
possible to minimize the widget specific code and reuse a large amount
of code across widget sets and platforms.
Because the vast majority of work is done in the base class, and the
outer classes simply inherit the widget-specific ones and mix in the
others, it is a fairly simple matter to port the basic Ginga
functionality to a new widget set.  All that is required is that the new
widget set have some kind of native widget that supports painting an RGB
image (like a canvas or image widget) and a way to register for user
interaction events on that widget.

The Controller
--------------

The control interface is a combination of methods on the view object and
a pluggable ``Bindings`` class which handles the mapping of user input
events such as mouse, gesture and keystrokes into commands on the view.
There are many callback functions that can be registered,
allowing the user to create their own custom user interface for
manipulating the view.


Graphics on Ginga
=================

.. _fig_imageviewcanvas:
.. figure:: figures/class_structure_drawingcanvas.png
   :scale: 100%
   :figclass: h

   Class structure of Ginga ``DrawingCanvas`` class.

Ginga's graphics are all rendered from objects placed on a
``DrawingCanvas``.  All objects that can be put on a ``DrawingCanvas``
are rooted in the ``CanvasObject`` type (including ``DrawingCanvas``
itself).


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
(requires the optional Python module ``python-magic`` be installed), MIME
type, or filename extension.  Once the general category of file is known,
methods in the specific I/O module devoted to that type are called to
load the file data.

The `ginga.util.loader` module is used to register file openers. An
opener is a class that understand how to load data objects from a
particular kind of file format.  You'll want to start by examining this
module and especially looking at the examples at the bottom of that file
for how openers are registered. 

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
register it as follows:

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

Porting Ginga to a New Widget Set
---------------------------------

[*TBD*]
