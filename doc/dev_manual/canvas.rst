.. _ch-canvas_graphics:

+++++++++++++++++++++
Ginga Canvas Graphics
+++++++++++++++++++++

This chapter describes the basic architecture of Ginga's
canvas-viewer-renderer model, and describes how to do graphics
operations on canvases.

Canvases and Canvas Objects
===========================

Ginga's canvas is based on the ``DrawingCanvas`` class.
On the canvas can be placed a number of different kinds of
*canvas objects*, including many geometric shapes.  The set of canvas
objects includes:

* ``Text``:  a piece of text having a single point coordinate.
* ``Polygon``:  a closed polygon defined by N points.
* ``Path``:  an open polygon defined by N points.
* ``Box``:  a rectangular shape defined by a single center point,
  two radii and a rotation angle.
* ``Ellipse``:  an elliptical shape defined by a single center point,
  two radii and a rotation angle.
* ``Triangle``:  an equilateral triangular shape defined by a single
  center point, two radii and a rotation angle.
* ``Circle``:  a circular shape defined by a center point and a radius.
* ``Point``:  a marker for a point defined by a single point and a
  radius for the "arms".
* ``Rectangle`` -- a rectangular shape defined by two points.
* ``Line`` -- a line defined by two points.
* ``RightTriangle`` -- a right triangle defined by two points.
* ``Compass`` -- a compass defined by a point and a radius.
* ``Ruler`` -- a ruler defined by two points.
* ``Crosshair`` -- a crosshair defined by one point.
* ``Annulus`` -- an annulus defined by one point, a radius and a width.
* ``Annulus2R`` -- an annulus defined by one point, two radii and two widths.
* ``Image`` -- a raster image anchored by a point.
* ``NormImage`` -- a subclass of ``Image``, with rendering done with the
  aid of a colormap, a color distribution algorithm (linear, log, etc),
  and defined low and high cut levels.
* ``CompoundObject``:  a compound object combining a series of other
  canvas objects.
* ``Canvas``:  a transparent subcanvas on which items can be placed.
* ``DrawingCanvas``:  Like a ``Canvas``, but also can support manual
  drawing operations initiated in a viewer to create shapes on itself.
* ``ColorBar``: a bar with a color range and ticks and value markers to
  help indicate the mapping of color to the value range of the data.
* ``ModeIndicator``: a small rectangular overlay with text indicating
  that the user has entered a special keyboard/mouse mode.

All canvas objects are subclasses of ``CanvasObjectBase`` and may also
contain mixin classes that define common attributes or behavior.  For
example, ``Line``, ``Ruler`` and ``RightTriangle`` are all subclasses of
the mixin class ``TwoPointMixin``.

.. note:: In most general canvas systems you can layer objects in any
          order.  In Ginga there is an optimization of canvas redrawing
          that merges image bitmaps before updating other kinds of
          canvas objects.  This means that while images can be stacked in
          any order, effectively you cannot have other objects
          appear *underneath* image objects.  For most uses of the
          viewer this is not a big limitation.

Viewers
=======
All Ginga viewers are subclasses of ``ImageViewBase``.  These objects
implement a viewport onto a ``DrawingCanvas`` object.  Each viewer
contains a handle to a canvas and provides a particular view onto that
canvas defined by:

* dimensions of their viewport (i.e. the height and
  width of the native widget's window into which the viewer is rendering),
* scale in X and Y dimensions,
* a *pan position* linking the center of the viewport to a canvas
  coordinate,
* a transform consisting of possible flips in X, Y axes and/or swapping
  of X/Y axes, and
* a rotation.

Two different ``ImageView``-based viewers can share the same canvas
handle, providing different views into the same canvas.  Another typical
arrangement for sharing is where each viewer has a private canvas, and
on each private canvas is placed a shared transparent subcanvas, an
arrangement which allows each viewer to have a mix of private and shared
canvas objects.  Another common idiom is to layer multiple 
``DrawingCanvas`` objects to more easily manage multiple collections of
overlaid graphics.

The various subclasses of ``ImageView`` are designed to render into a
different widget set's "native" canvas using a ``CanvasRenderer``
customized for that target. 

Using Canvases
==============
The recommended way of using canvases is to create your own
``DrawingCanvas`` and add (or remove) it to/from the existing (default)
viewer canvas.

Creating a Ginga Canvas
-----------------------
Assuming we have created a viewer (``view``):

.. code-block:: python

    v_canvas = view.get_canvas()
    DrawingCanvas = v_canvas.get_draw_class('drawingcanvas')
    mycanvas = DrawingCanvas()
    v_canvas.add(mycanvas)

You can create several different canvases and add them or remove them as
needed from the default viewer canvas.  The items added to individual
canvases stay on those canvases, allowing a good deal of control in
managing canvas overlays on top of images, which appear under those
canvases.

Enabling User Interaction on a Canvas
-------------------------------------
To enable user interaction on a canvas, use the following methods on it:

.. code-block:: python

    mycanvas.set_surface(view)     # associate the canvas with a viewer
    mycanvas.ui_set_active(True)   # enable user interaction on this canvas

User Drawing on a Canvas
------------------------
To enable user drawing on the canvas, enable user interaction as
described above, then use the following methods:

.. code-block:: python

    mycanvas.enable_draw(True)     # enable user drawing on this canvas
    mycanvas.set_draw_mode('draw')

    # without this call, you can only draw with the right mouse button
    # using the default user interface bindings
    mycanvas.register_for_cursor_drawing(view)

If you want to get a callback after something has been drawn:

.. code-block:: python

    # the callback function gets the canvas and the tag of the drawn
    # object as parameters
    #
    def draw_cb(canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        # do something with ``obj``
        ...

    mycanvas.add_callback('draw-event', draw_cb)

Set Drawing Parameters
----------------------
To set the drawing parameters (what will be drawn by the user):

.. code-block:: python

    mycanvas.set_drawtype('box', color='red')

To see the kinds of objects that can be drawn on a Ginga canvas, refer
to the section above on "Canvases and Canvas Objects".
With the ``set_drawtype`` call, most drawing types are specified in all
lower case with no spaces (e.g. "righttriangle").
Various object attributes (line and fill, etc) are set by keyword
parameters:

.. code-block:: python

    mycanvas.set_drawtype('polygon', color='lightblue', linewidth=2,
                          fill=True, fillcolor='yellow', fillalpha=0.4)

Editing Objects on a Canvas
---------------------------
DrawingCanvases have a built in editor that can handle basic editing
of drawn (or programatically) added items.

To enable user editing on a canvas, add the following calls in the setup
of the canvas:

.. code-block:: python

    mycanvas.enable_edit(True)     # enable user editing on this canvas

To set the mode on a canvas from drawing to editing:

.. code-block:: python

    mycanvas.set_draw_mode('edit')

If you want to get a callback after an object has been edited on a canvas:

.. code-block:: python

    # the callback function gets the canvas and the object reference
    # of the edited object as parameters
    #
    def edit_cb(canvas, obj):
        # do something with ``obj``
        ...

    mycanvas.add_callback('edit-event', edit_cb)

It is also possible to set a direct edit callback on the object itself.
Assuming we have a handle to an object (``obj``) that has been added to
a canvas (drawn or added programatically):

.. code-block:: python

    # the callback function gets the object reference of the edited
    # object as a parameter
    #
    def obj_edit_cb(obj):
        # do something with ``obj``
        print("object of type '{}' has been edited".format(obj.kind))

    obj.add_callback('edited', obj_edit_cb)

"Pick" Callbacks
----------------
There are a group of actions under the umbrella term of "pick callbacks"
that can be registered for objects on a ``DrawingCanvas``.

To set the canvas mode from "draw" or "edit" to "pick":

.. code-block:: python

    mycanvas.set_draw_mode('pick')

NOTE: Canvas objects are not "pickable" by default.  To make an object
"pickable", set it's "pickable" attribute to `True`.  This can be done
before or after it has been drawn or placed on a canvas:

.. code-block:: python

    obj.pickable = True
    obj.add_callback('pick-down', pick_cb, 'down')
    obj.add_callback('pick-up', pick_cb, 'up')
    obj.add_callback('pick-move', pick_cb, 'move')
    obj.add_callback('pick-hover', pick_cb, 'hover')
    obj.add_callback('pick-enter', pick_cb, 'enter')
    obj.add_callback('pick-leave', pick_cb, 'leave')
    obj.add_callback('pick-key', pick_cb, 'key')

From the above example you can see all the possible callbacks for
"pick".  In setting up the callback, we append a "pick type" string to
the callback signature so that we can easily distinguish the pick action
in the callback (you could also just define different callback functions):

.. code-block:: python

    # callback parameters are: the object, the canvas, the event, a
    # point (in data coordinates) and the pick "type"

    def pick_cb(obj, canvas, event, pt, ptype):
        print("pick event '%s' with obj %s at (%.2f, %.2f)" % (
            ptype, obj.kind, pt[0], pt[1]))
        return True

The pick type (``ptype`` in the above example) will be one of:

* "enter": cursor entered the area of the object,
* "hover": cursor is hovering over the object,
* "leave": cursor as exited the area of the object,
* "down": cursor was pressed down inside the object,
* "move": cursor is being moved while pressed,
* "up": cursor was released,
* "key": a key was pressed while the cursor was inside the object


Support for Astropy regions
===========================
Ginga provides a module for plotting Astropy ``regions`` shapes on
canvases.  To use this, import the ``ginga.util.ap_regions`` module and
use one of the three module functions
``astropy_region_to_ginga_canvas_object``, ``add_region``, or
``ginga_canvas_object_to_astropy_region``.

``astropy_region_to_ginga_canvas_object`` takes a ``regions`` shape and
returns a Ginga canvas object that most closely implements the shape.
The object returned can be used like any Ginga canvas object: it can be
used in a compound object, added to a canvas, etc.
Assuming you have a viewer ``v`` and an Astropy region ``r``:

.. code-block:: python

    from ginga.util import ap_region
    obj = ap_region.astropy_region_to_ginga_canvas_object(r)
    canvas = v.get_canvas()
    canvas.add(obj)

``add_region`` is a convenience method for both converting an object and
adding it to a canvas.  

.. code-block:: python

    ap_region.add_region(canvas, r)

``ginga_canvas_object_to_astropy_region`` provides the reverse
transformation, taking a Ginga canvas object and converting it to the
closest representation as an Astropy region.

.. code-block:: python

    r = ap_region.ginga_canvas_object_to_astropy_region(obj)

