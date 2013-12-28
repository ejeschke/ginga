.. _ch-programming-ginga:

+++++++++++++++++++++
Developing with Ginga
+++++++++++++++++++++

* :ref:`modindex`

Developers interested in using Ginga in their project will probably
follow one of two logical development paths: 

- using only the Ginga rendering class in a program of their own design, or
- starting with the full-featured reference viewer that comes with Ginga
  and customizing it for some special purpose, typically by modifying
  one of the plugins or writing a new plugin.

The first approach is probably best for when the developer has a custom
application in mind, needs a minimal but powerful viewer or wants to
develop an entirely new full-featured viewer.  The second approach is
probably best for end users or developers that are mostly satisfied with
the reference viewer as a general purpose tool and want to add some specific
enhancements or functionality.  Because the reference viewer is based on
a flexible plugin architecture this is fairly easy to do.  We examine
both approaches in this chapter.

===============================================
Using the basic rendering class in new programs
===============================================

First, let's take a look at how to use the "bare" Ginga rending class
by itself.  Ginga basically follows the Model-View-Controller (MVC)
design pattern, that is described in more detail in
the `chapter on internals <ch-programming-internals>`_.
The "view" classes are rooted in the base class ``ImageView``.
Ginga supports backends for different widget sets through various
subclasses of this class.   

Typically, a developer picks a GUI toolkit that has a supported backend
(Gtk, Qt or Tk) and writes a GUI program using that widget set with the
typical Python toolkit bindings and API.  Where they want a 
image view pane they instantiate the appropriate subclass of 
``ImageView``, and using the  ``get_widget()`` call extract the native
widget and insert it into the GUI layout.  A reference should be kept to
the view object.

Ginga does not create any additional GUI components beyond the image
pane itself, however it does provide a standard set of keyboard and
mouse bindings on the widget that can be enabled, disabled or changed.
The user interface bindings are configurable via a pluggable
``Bindings`` class which constitutes the "controller" part of the MVC
design.  There are a plethora of callbacks that can be registered,
allowing the user to create their own custom user interface for
manipulating the view.   

.. _fig1:
.. figure:: figures/barebonesviewer_qt.png
   :scale: 100%
   :figclass: h

   A simple, "bare bones" FITS viewer written in Qt.  

Listing 1 shows a code listing for a simple graphical FITS
viewer built using the subclass ``ImageViewZoom`` from the module
``ginga.qtw`` (screenshot in Figure :ref:`fig1`) written in around 100
or so lines of Python.  It creates a window containing an image view and
two buttons.  This example, included with the Ginga source (look in the
``examples`` directory), will open FITS files dragged and dropped on the 
image window or via a dialog popped up when clicking the "Open File"
button.   

.. code-block:: python

    #! /usr/bin/env python
    #
    # example1_qt.py -- Simple, configurable FITS viewer.
    #
    import sys, os
    import logging

    from ginga import AstroImage
    from ginga.qtw.QtHelp import QtGui, QtCore
    from ginga.qtw.ImageViewQt import ImageViewZoom


    class FitsViewer(QtGui.QMainWindow):

	def __init__(self, logger):
	    super(FitsViewer, self).__init__()
	    self.logger = logger

	    # Create the view object
	    fi = ImageViewZoom(self.logger)
	    fi.enable_autocuts('on')
	    fi.set_autocut_params('zscale')
	    fi.enable_autozoom('on')
	    fi.set_callback('drag-drop', self.drop_file)
	    fi.set_bg(0.2, 0.2, 0.2)
	    fi.ui_setActive(True)
	    self.fitsimage = fi

	    # Get the control object
	    bd = fi.get_bindings()
	    bd.enable_all(True)

	    w = fi.get_widget()
	    w.resize(512, 512)

	    vbox = QtGui.QVBoxLayout()
	    vbox.setContentsMargins(
                QtCore.QMargins(2, 2, 2, 2))
	    vbox.setSpacing(1)
	    vbox.addWidget(w, stretch=1)

	    hbox = QtGui.QHBoxLayout()
	    hbox.setContentsMargins(
                QtCore.QMargins(4, 2, 4, 2))

	    wopen = QtGui.QPushButton("Open File")
	    wopen.clicked.connect(self.open_file)
	    wquit = QtGui.QPushButton("Quit")
            self.connect(wquit,
                         QtCore.SIGNAL("clicked()"),
                         self, QtCore.SLOT("close()"))

	    hbox.addStretch(1)
	    for w in (wopen, wquit):
		hbox.addWidget(w, stretch=0)

	    hw = QtGui.QWidget()
	    hw.setLayout(hbox)
	    vbox.addWidget(hw, stretch=0)

	    vw = QtGui.QWidget()
	    self.setCentralWidget(vw)
	    vw.setLayout(vbox)

	def load_file(self, filepath):
            # create a model object
            image = AstroImage.AstroImage(logger=self.logger)
            image.load_file(filepath)

	    # load the model into the view
            self.fitsimage.set_image(image)
	    self.setWindowTitle(filepath)

	def open_file(self):
	    res = QtGui.QFileDialog.getOpenFileName(self,
	                          "Open FITS file",
                                  ".",
                                  "FITS files (*.fits)")
	    if isinstance(res, tuple):
		fileName = res[0].encode('ascii')
	    else:
		fileName = str(res)
	    self.load_file(fileName)

	def drop_file(self, fitsimage, paths):
	    fileName = paths[0]
	    self.load_file(fileName)


    def main(options, args):

	app = QtGui.QApplication(sys.argv)
	app.connect(app,
                    QtCore.SIGNAL('lastWindowClosed()'),
		    app, QtCore.SLOT('quit()'))

	logger = logging.getLogger("example1")
	logger.setLevel(logging.INFO)
	stderrHdlr = logging.StreamHandler()
	logger.addHandler(stderrHdlr)

	w = FitsViewer(logger)
	w.resize(524, 540)
	w.show()
	app.setActiveWindow(w)

	if len(args) > 0:
	    w.load_file(args[0])

	app.exec_()

    if __name__ == '__main__':
	main(None, sys.argv[1:])


Looking at the constructor for this particular viewer, you can see where
we create a ``ImageViewZoom`` object.  On this object we enable automatic
cut levels (using the 'zscale' algorithm), configure it to auto zoom the
image to fit the window and set a callback function for files dropped on
the window.  We extract the user-interface bindings with
``get_bindings()``, and on this object enable standard user interactive
controls for panning, zooming, cut levels, simple transformations (flip
x/y and swap axes), rotation and color map warping.
We then extract the platform-specific widget (Qt-based, in this case) using
``get_widget()`` and pack it into a Qt container along with a couple of
buttons to complete the viewer. 

Scanning down the code a bit, we can see that whether by dragging and
dropping or via the click to open, we ultimately call the load_file()
method to get the data into the viewer.  As shown, load_file creates 
an AstroImage object (the "model" part of our MVC design).  It then
passes this object to the viewer via the set_image() method.  
AstroImage objects have methods for ingesting data via a file path, an
``Astropy``/``pyfits`` HDU or a bare ``Numpy`` data array. 

Many of these sorts of examples are contained in the ``examples``
directory in the source distribution.  Look for files with names
matching example*_*.py

.. _sec-plotting:

Graphics plotting with Ginga
----------------------------

.. _fig2:
.. figure:: figures/example2_screenshot.png
   :scale: 100%
   :figclass: h

   An example of a ``ImageViewCanvas`` widget with graphical overlay. 

For each supported widget set there is a subclass of ImageViewZoom called
``ImageViewCanvas`` (an example is shown in Figure :ref:`fig2`).
This class adds scalable object plotting on top of the image view plane.
A variety of simple graphical shapes are available,
including lines, circles, rectangles, points, polygons, text, rulers,
compasses, etc.  Plotted objects scale, transform and rotate seamlessly
with the image. 

See the scripts prefaced with "example2" (under "examples") in the
package source for details.  

Rendering into Matplotlib Figures
---------------------------------

Ginga can also render directly into a Matplotlib Figure, which opens up
interesting possibilities for overplotting beyond the limited
capabilities of the ``ImageViewCanvas`` class.  

========================================
Writing plugins for the reference viewer
========================================

We now turn our attention to the other approach to developing with
Ginga: modifying the reference viewer.
The philosophy behind the design of the reference viewer distributed
with the Ginga is that it is simply a flexible layout shell for
instantiating instances of the viewing widget described in the earlier
section.  All of the other important pieces of a modern FITS viewer--a
panning widget, information panels, zoom widget, analysis panes--are
implemented as plugins: encapsulated modules that interface with the
viewing shell using a standardized API.  This makes it easy to customize
and to add, change or remove functionality in a very modular, flexible way.

The Ginga viewer divides the application window GUI into containers that
hold either viewing widgets or plugins.  The view widgets are called
"channels" in the viewer nomenclature, and are a means of organizing
images in the viewer, functioning much like "frames" in other viewers.
A channel has a name and maintains its own history of images that have
cycled through it.  The user can create new channels as needed.  For
example, they might use different channels for different kinds of
images: camera vs. spectrograph, or channels organized by CCD, or by
target, or raw data vs. quick look, etc.  In the default layout, shown
in :ref:`fig2` the channel tabs are in the large middle pane, while the
plugins occupy the left and right panes.  Other layouts are possible, by
simply changing a table used in the startup script.

Ginga distinguishes between two types of plugin: *global* and *local*.  
Global plugins are used where the functionality is generally enabled
during the entire session with the viewer and where the plugin is active
no matter which channel is currenly under interaction with the user.
Examples of global plugins include a panning view (a small, bird's-eye
view of the image that shows a panning rectangle and allows graphical
positioning of the pan region), a zoomed view (that shows an enlarged
cutout of the area currently under the cursor), informational displays
about world coordinates, FITS headers, thumbnails, etc.  Figure
:ref:`fig4` shows an example of two global plugins occupying a notebook tab.

.. _fig4:
.. figure:: figures/global_plugin1.png
   :scale: 100%
   :figclass: h

   Two global plugins: ``Pan`` (top) and ``Info`` (bottom), shown sharing a tab.

Local plugins are used for modal operations with images in specific
channels.  For example, the Pick plugin is used to perform stellar
evaluation of objects, finding the center of the object and giving
informational readings of the exact celestial coordinates, image
quality, etc.  The Pick plugin is only visible while the user has it
open, and does not capture the mouse actions unless the channel it is
operating on is selected.  Thus one can have two different Pick
operations going on concurrently on two different channels, for example,
or a Pick operation in a camera channel, and a Cuts (line cuts)
operation on a spectrograph channel. 
Figure :ref:`fig5` shows an example of the Pick local plugin occupying a
notebook tab. 

.. _fig5:
.. figure:: figures/local_plugin1.png
   :scale: 100%
   :figclass: thb

   The ``Pick`` local plugin, shown occupying a tab.

.. _sec-writing-local-plugins:

Anatomy of a Local Ginga Plugin
-------------------------------

Let's take a look at a local plugin to understand the API for
interfacing to the Ginga shell.  In Listing 2, we show a stub for a
local plugin.  

.. code-block:: python

    from ginga import GingaPlugin

    class MyPlugin(GingaPlugin.LocalPlugin):

	def __init__(self, fv, fitsimage):
	    super(MyPlugin, self).__init__(fv, fitsimage)

	def build_gui(self, container):
	    pass

	def start(self):
	    pass

	def stop(self):
            pass

	def pause(self):
	    pass

	def resume(self):
	    pass

	def redo(self):
	    pass

	def __str__(self):
	    return 'myplugin'


The purpose of each method is as follows.

``__init__(self, fv, fitsimage)``:
This method is called when the plugin is loaded for the  first time.
``fv`` is a reference to the Ginga shell and ``fitsimage`` is a reference to
the ImageViewCanvas object associated with the channel on which the
plugin is being invoked.  You need to call the superclass initializer
and then do any local initialization. 

``build_gui(self, container)``:
This method is called when the plugin is invoked.  It builds the GUI
used by the plugin into the widget layout passed as ``container``.
This method may be called many times as the plugin is opened and closed
for modal operations.  The method may be omitted if there is no GUI for
the plugin.

``start(self)``:
This method is called just after ``build_gui()`` when the plugin is invoked.
This method may be called many times as the plugin is opened and closed
for modal operations.  This method may be omitted.

``stop(self)``: This method is called when the plugin is stopped. 
It should perform any special clean up necessary to terminate the
operation.  The GUI will be destroyed by the plugin manager so there is
no need for the stop method to do that.  This method may be called many 
times as the plugin is opened and closed for modal operations.
This method may be omitted if there is no special cleanup required when
stopping.

``pause(self)``: This method is called when the plugin loses focus.
It should take any actions necessary to stop handling user interaction
events that were initiated in ``start()`` or ``resume()``.
This method may be called many times as the plugin is focused or defocused.
The method may be omitted if there is no user event handling to disable.

``resume(self)``: This method is called when the plugin gets focus.
It should take any actions necessary to start handling user interaction
events for the operations that it does.  This method may be called many
times as the plugin is focused or defocused.  The method may be omitted
if there is no user event handling to enable.

``redo(self)``: This method is called when the plugin is active and a new
image is loaded into the associated channel.  It can optionally redo the
current operation on the new image.  This method may be called many
times as new images are loaded while the plugin is active.
This method may be omitted.

Putting it All Together: The ``Ruler`` Plugin
---------------------------------------------

Finally, in Listing 3 we show a completed plugin for ``Ruler``.  The
purpose of this plugin to draw triangulation (distance measurement)
rulers on the image.  For reference, you may want to refer to the ruler
shown on the canvas in Figure :ref:`fig2` and the plugin GUI shown in
Figure :ref:`fig6`.   

.. _fig6:
.. figure:: figures/ruler_plugin.png
   :scale: 100%
   :figclass: thb

   The ``Ruler`` local plugin GUI, shown occupying a tab.

.. code-block:: python

    from ginga.qtw.QtHelp import QtGui, QtCore
    from ginga.qtw import QtHelp

    from ginga import GingaPlugin

    class Ruler(GingaPlugin.LocalPlugin):

	def __init__(self, fv, fitsimage):
	    # superclass saves and defines some variables
            # for us, like logger
	    super(Ruler, self).__init__(fv, fitsimage)

	    self.rulecolor = 'lightgreen'
	    self.layertag = 'ruler-canvas'
	    self.ruletag = None

	    self.dc = fv.getDrawClasses()
	    canvas = self.dc.DrawingCanvas()
	    canvas.enable_draw(True)
	    canvas.set_drawtype('ruler', color='cyan')
	    canvas.set_callback('draw-event',
                                self.wcsruler)
	    canvas.set_callback('draw-down', self.clear)
	    canvas.setSurface(self.fitsimage)
	    self.canvas = canvas

	    self.w = None
	    self.unittypes = ('arcmin', 'pixels')
	    self.units = 'arcmin'

	def build_gui(self, container):
	    sw = QtGui.QScrollArea()

	    twidget = QtHelp.VBox()
	    sp = QtGui.QSizePolicy(
                     QtGui.QSizePolicy.MinimumExpanding,
		     QtGui.QSizePolicy.Fixed)
	    twidget.setSizePolicy(sp)
	    vbox1 = twidget.layout()
	    vbox1.setContentsMargins(4, 4, 4, 4)
	    vbox1.setSpacing(2)
	    sw.setWidgetResizable(True)
	    sw.setWidget(twidget)

	    msgFont = QtGui.QFont("Sans", 14)
	    tw = QtGui.QLabel()
	    tw.setFont(msgFont)
	    tw.setWordWrap(True)
	    self.tw = tw

	    fr = QtHelp.Frame("Instructions")
	    fr.layout().addWidget(tw, stretch=1,
                            alignment=QtCore.Qt.AlignTop)
	    vbox1.addWidget(fr, stretch=0,
                            alignment=QtCore.Qt.AlignTop)

	    fr = QtHelp.Frame("Ruler")

	    captions = (('Units', 'combobox'),)
	    w, b = QtHelp.build_info(captions)
	    self.w = b

	    combobox = b.units
	    for name in self.unittypes:
		combobox.addItem(name)
	    index = self.unittypes.index(self.units)
	    combobox.setCurrentIndex(index)
	    combobox.activated.connect(self.set_units)

	    fr.layout().addWidget(w, stretch=1,
                          alignment=QtCore.Qt.AlignLeft)
	    vbox1.addWidget(fr, stretch=0,
                          alignment=QtCore.Qt.AlignTop)

	    btns = QtHelp.HBox()
	    layout = btns.layout()
	    layout.setSpacing(3)
	    #btns.set_child_size(15, -1)

	    btn = QtGui.QPushButton("Close")
	    btn.clicked.connect(self.close)
	    layout.addWidget(btn, stretch=0,
                        alignment=QtCore.Qt.AlignLeft)
	    vbox1.addWidget(btns, stretch=0,
                        alignment=QtCore.Qt.AlignLeft)

	    container.addWidget(sw, stretch=1)

	def set_units(self):
	    index = self.w.units.currentIndex()
	    units = self.unittypes[index]
	    self.canvas.set_drawtype('ruler',
	                             color='cyan',
                                     units=units)
	    self.redo()
	    return True

	def close(self):
	    chname = self.fv.get_channelName(
                                     self.fitsimage)
	    self.fv.stop_operation_channel(chname,
                                     str(self))
	    return True

	def instructions(self):
	    self.tw.setText("Draw (or redraw) a line "
                            "with the right mouse "
                            "button.  Display the "
                            "Zoom tab to precisely "
                            "see detail.")
	    self.tw.show()

	def start(self):
	    self.instructions()
	    # start ruler drawing operation
	    try:
		obj = self.fitsimage.getObjectByTag(
                                 self.layertag)

	    except KeyError:
		# Add ruler layer
		self.fitsimage.add(self.canvas,
                                  tag=self.layertag)

	    self.canvas.deleteAllObjects()
	    self.resume()

	def pause(self):
	    self.canvas.ui_setActive(False)

	def resume(self):
	    self.canvas.ui_setActive(True)
	    self.fv.showStatus("Draw a ruler with "
                               "the right mouse button")

	def stop(self):
	    # remove the canvas from the image,
            # this prevents us from getting draw events
            # when we are inactive
	    try:
		self.fitsimage.deleteObjectByTag(
                                       self.layertag)
	    except:
		pass
	    self.fv.showStatus("")

	def redo(self):
	    # get the ruler object on the canvas
	    obj = self.canvas.getObjectByTag(
                                        self.ruletag)
	    if obj.kind != 'ruler':
		return True

	    # calculate and assign distances
	    text_x, text_y, text_h = \
              self.canvas.get_ruler_distances(obj.x1,
                                              obj.y1,
                                              obj.x2,
                                              obj.y2)
	    obj.text_x = text_x
	    obj.text_y = text_y
	    obj.text_h = text_h
	    self.canvas.redraw(whence=3)

	def clear(self, canvas, button, data_x, data_y):
	    self.canvas.deleteAllObjects()
	    return False

	def wcsruler(self, surface, tag):
	    # drawing callback.  The newly drawn object
            # on the canvas is tagged
	    obj = self.canvas.getObjectByTag(tag)
	    if obj.kind != 'ruler':
		return True

	    # remove the old ruler
	    try:
		self.canvas.deleteObjectByTag(
                                        self.ruletag,
                                           redraw=False)
	    except:
		pass

	    # change some characteristics of the
            # drawn image and save as the new ruler
	    self.ruletag = tag
	    obj.color = self.rulecolor
	    obj.cap = 'ball'
	    self.canvas.redraw(whence=3)

	def __str__(self):
	    return 'ruler'

This plugin shows a standard design pattern typical to local plugins.
Often one is wanting to draw or plot something on top of the image
below.  The ``ImageViewCanvas`` widget used by Ginga allows this to be
done very cleanly and conveniently by adding a ``DrawingCanvas`` 
object to the image and drawing on that.  Canvases can be layered on top
of each other in a manner analogous to "layers" in an image editing
program.  Since each local plugin maintains it's own canvas, it is very
easy to encapsulate the logic for drawing on and dealing with the
objects associated with that plugin.  We use this technique in the Ruler
plugin. When the plugin is loaded (refer to ``__init__()`` method), it
creates a canvas, enables drawing on it, sets the draw type and registers a
callback for drawing events.  When ``start()`` is called it adds that canvas
to the widget.  When ``stop()`` is called it removes the canvas from the
widget (but does not destroy the canvas).  ``pause()`` disables user
interaction on the canvas and ``resume()`` reenables that interaction.
``redo()`` simply redraws the ruler with new measurements taken from any new
image that may have been loaded.  In the ``__init__()`` method you will
notice a ``setSurface()`` call that associates this canvas with a
``ImageView``-based widget--this is the key for the canvas to utilize WCS
information for correct plotting.
All the other methods shown are support methods for doing the ruler
drawing operation and interacting with the plugin GUI. 

The Ginga package includes a rich set of classes and there are also many
methods that can be called in the shell or in the ``ImageViewCanvas``
object for plotting or manipulating the view.  
The best way to get a feel for these APIs is to look at the source of
one of the many plugins distributed with Ginga.  Most of them are not
very long or complex.  In general, a plugin can include any Python
packages or modules that it wants and programming one is essentially
similar to writing any other Python program.

.. _sec-writing-global-plugins:

Writing a Global Plugin
-----------------------
The last example was focused on writing a local plugin.  Global plugins 
employ a nearly identical API to that shown in Listing 2, except that
the constructor does not take a ``fitsimage`` parameter, because the
plugin is expected to be active across the entire session, and is not
associated with any particular channel.  ``build_gui()`` and ``start()`` are
called when the Ginga shell starts up, and ``stop()`` is never called until
the program terminates [#f1]_.  ``pause()`` and ``resume()`` can safely be
omitted because they should never be called.  Like local plugins, 
``build_gui()`` can be omitted if there is no GUI associated with the plugin.
Take a look at some of the global plugins distributed with the viewer
for more information and further examples.  The ``IRAF`` plugin,
which handles IRAF/ginga interaction similarly to IRAF/ds9, is an
example of a plugin without a GUI.

.. rubric:: Footnotes

.. [#f1] Unless the user reloads the plugin.  Most plugins in Ginga can be
         dynamically reloaded using the ``Debug`` plugin, which facilitates
         debugging tremendously, since Ginga itself does not have to be
         restarted, data does not have to be reloaded, etc.

