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
* ``Triangle``:  an equilateral triangluar shape defined by a single
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
* ``Annulus`` -- an annulus defined by one point and two radii.
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

