#
# ipg.py -- Module for simple FITS viewer in an HTML5 canvas web browser.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This module makes it easy to open a Ginga viewer in a web browser (or
embedded in a Jupyter notebook cell).  All the rendering is done on the
server side and the browser only acts as a display front end, connected
over a WebSocket.  Using this you could create an analysis-type
environment on a server and view it via a browser.

It is built on the ``pgwidgets`` backend (``ginga.web.pgw``), which runs
its WebSocket and HTTP servers in their own background threads.  Because
of that, it coexists cleanly with the Jupyter kernel's own event loop --
there is no need to surrender the kernel's IOLoop.  For browser-initiated
viewer interactions (cursor readout, drawing, pan/zoom) the server pumps
queued callbacks onto the running kernel asyncio loop, so they execute on
the kernel thread, in step with the code you run in cells.

Typical notebook usage::

    from ginga.web.pgw import ipg
    server = ipg.make_server(host='localhost', port=9914)
    server.start(no_ioloop=True)
    v1 = server.get_viewer('v1')
    v1.open()              # open in a new browser tab/window
    v1.embed(height=650)   # ...or embed in the notebook cell
    v1.load('/path/to/image.fits')

You will need a reasonably modern web browser with HTML5 canvas support.
"""

import os
import logging
import threading
import asyncio

from ginga import AstroImage
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc import log, Bunch
from ginga.Bindings import ImageViewBindings
from ginga.misc.Settings import SettingGroup
from ginga.util.paths import ginga_home
from ginga.util import loader

from ginga.web.pgw import Widgets, Viewers


class BasicCanvasView(Viewers.CanvasView):

    def build_gui(self, container):
        """
        This is responsible for building the viewer's UI.  It should
        place the UI in `container`.  Override this to make a custom
        UI.
        """
        vbox = Widgets.VBox()
        vbox.set_border_width(0)
        # fill the window in both directions
        vbox.set_expanding(True, True)

        w = Viewers.GingaViewerWidget(viewer=self)
        vbox.add_widget(w, stretch=1)

        container.set_widget(vbox)

    def embed(self, width=600, height=650):
        """
        Embed a viewer into a Jupyter notebook.
        """
        from IPython.display import IFrame
        return IFrame(self.url, width, height)

    def open(self, new=1):
        """
        Open this viewer in a new browser window or tab.
        (requires `webbrowser` module)
        """
        import webbrowser
        webbrowser.open(self.url, new=new)

    def show(self, fmt=None):
        """
        Capture the window of a viewer.
        """
        # force any delayed redraws
        # TODO: this really needs to be addressed in get_rgb_image_as_bytes()
        # of the various superclasses, as it affects other backends as well
        self.redraw_now()

        from IPython.display import Image

        if fmt is None:
            # what format are we using for the HTML5 canvas--use that
            settings = self.get_settings()
            fmt = settings.get('html5_canvas_format', 'png')

        return Image(data=bytes(self.get_rgb_image_as_bytes(format=fmt)),
                     format=fmt, embed=True)

    def load_fits(self, filepath):
        """
        Load a FITS file into the viewer.
        """
        image = loader.load_data(filepath, logger=self.logger)
        self.set_image(image)

    load = load_fits

    def load_hdu(self, hdu):
        """
        Load an HDU into the viewer.
        """
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_hdu(hdu)

        self.set_image(image)

    def load_data(self, data_np):
        """
        Load raw numpy data into the viewer.
        """
        image = AstroImage.AstroImage(logger=self.logger)
        image.set_data(data_np)

        self.set_image(image)

    def add_canvas(self, tag=None):
        # add a canvas to the view
        my_canvas = self.get_canvas()
        DrawingCanvas = my_canvas.get_draw_class('drawingcanvas')
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype(None)
        canvas.ui_set_active(True)
        canvas.set_surface(self)
        canvas.register_for_cursor_drawing(self)
        # add the canvas to the view.
        my_canvas.add(canvas, tag=tag)
        canvas.set_draw_mode(None)

        return canvas

    def set_html5_canvas_format(self, fmt):
        """
        Sets the format used for rendering to the HTML5 canvas.
        'png' offers greater clarity, especially for small text, but
        does not have as good of performance as 'jpeg'.
        """
        fmt = fmt.lower()
        if fmt not in ('jpeg', 'png'):
            raise ValueError("Format must be one of {jpeg|png} not '%s'" % (
                fmt))

        settings = self.get_settings()
        settings.set(html5_canvas_format=fmt)

    def get_html5_canvas_format(self):
        settings = self.get_settings()
        return settings.get('html5_canvas_format')


class EnhancedCanvasView(BasicCanvasView):
    """
    Like BasicCanvasView, but includes a readout widget for when the
    cursor is moved over the canvas to display the coordinates.
    """

    def build_gui(self, container):
        """
        This is responsible for building the viewer's UI.  It should
        place the UI in `container`.
        """
        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)
        # fill the window in both directions
        vbox.set_expanding(True, True)

        w = Viewers.GingaViewerWidget(viewer=self)
        vbox.add_widget(w, stretch=1)

        # set up to capture cursor movement for reading out coordinates

        # coordinates reported in base 1 or 0?
        self.pixel_base = 1.0

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        #self.set_callback('none-move', self.motion_cb)
        self.set_callback('cursor-changed', self.motion_cb)

        container.set_widget(vbox)

    def motion_cb(self, viewer, button, data_x, data_y):

        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x + 0.5), int(data_y + 0.5))

        except Exception:
            value = None

        pb = self.pixel_base
        fits_x, fits_y = data_x + pb, data_y + pb

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = viewer.get_image()
            if image is None:
                # No image loaded
                return
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception as e:
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def set_readout_text(self, text):
        self.readout.set_text(text)


class ViewerFactory:
    """
    This is a factory class that churns out web viewers for a web
    application.

    The most important method of interest is get_viewer().

    Each viewer is built in its own pgwidgets *session* so that it has an
    independent URL that can be opened in a browser tab or embedded in a
    notebook cell without interfering with any other viewer.  The first
    viewer reuses the application's default session.
    """

    def __init__(self, logger, app):
        """
        Parameters
        ----------
        logger : python compatible logger
            a logging-module compatible logger object
        app : ginga pgw web application object
        """
        self.logger = logger
        self.app = app
        self.dc = get_canvas_types()
        # dict of viewers
        self.viewers = {}
        # whether the application's default session has been claimed yet
        self._used_default = False

    def _get_session(self):
        # The first viewer reuses the application's default session; each
        # additional viewer gets its own session so it has an isolated
        # URL (a browser tab or embedded iframe shows only that viewer).
        if not self._used_default:
            self._used_default = True
            return self.app.default_session
        return self.app.create_session()

    def _session_url(self, session):
        return "http://%s:%d/?session=%s&token=%s" % (
            self.app._host, self.app._http_port, session.id, session.token)

    def make_viewer(self, v_id, viewer_class=None, width=512, height=512):
        if viewer_class is None:
            viewer_class = EnhancedCanvasView

        session = self._get_session()
        url = self._session_url(session)

        # Build this viewer's widgets (window, canvas surface, timers) in
        # its own session.  The pgwidgets widgets pick up the active
        # session from the module-level ``Widgets._session`` at creation
        # time, so swap it in for the duration of the build and restore
        # the default afterwards.
        prev_session = Widgets._session
        Widgets._session = session
        try:
            # create the top level window in this session
            window = self.app.make_window("Viewer %s" % v_id)

            # load binding preferences if available
            cfgfile = os.path.join(ginga_home, "ipg_bindings.cfg")
            bindprefs = SettingGroup(name='bindings', logger=self.logger,
                                     preffile=cfgfile)
            bindprefs.load(onError='silent')

            bd = ImageViewBindings(self.logger, settings=bindprefs)

            fi = viewer_class(self.logger, bindings=bd)
            fi.url = url
            # set up some reasonable defaults--user can change these later
            # if desired
            fi.set_autocut_params('zscale')
            fi.enable_autocuts('on')
            fi.enable_autozoom('on')
            fi.set_bg(0.2, 0.2, 0.2)
            fi.ui_set_active(True)
            fi.ipg_parent = self

            # enable most key/mouse operations
            bd = fi.get_bindings()
            bd.enable_all(True)

            # set up a non-private canvas for drawing
            canvas = self.dc.DrawingCanvas()
            canvas.set_surface(fi)
            # add canvas to view
            private_canvas = fi.get_canvas()
            private_canvas.add(canvas)
            canvas.ui_set_active(True)
            fi.set_canvas(canvas)

            fi.set_desired_size(width, height)
            # force allocation of a surface--may be resized later
            fi.configure_surface(width, height)

            # add little mode indicator that shows modal states in
            # the corner
            fi.show_mode_indicator(True)

            # Have the viewer build its UI into the container
            fi.build_gui(window)

            window.resize(width, height)
            window.show()

            # Attaching the viewer widget above resizes the offscreen
            # surface to the (as yet unknown) browser canvas size.  Re-
            # establish the desired size so that ``show()`` produces a
            # correctly-sized snapshot even before a browser has connected
            # to report its real canvas dimensions (a connected browser
            # will reconfigure this on resize).
            fi.configure_surface(width, height)

        finally:
            Widgets._session = prev_session

        v_info = Bunch.Bunch(url=url, viewer=fi, top=window, session=session)
        return v_info

    def get_viewer(self, v_id, viewer_class=None, width=512, height=512,
                   force_new=False):
        """
        Get an existing viewer by viewer id.  If the viewer does not yet
        exist, make a new one.
        """
        if not force_new:
            try:
                return self.viewers[v_id]
            except KeyError:
                pass

        # We get back a record with information about the viewer
        v_info = self.make_viewer(v_id, viewer_class=viewer_class,
                                  width=width, height=height)

        # Save it under this viewer id
        self.viewers[v_id] = v_info
        return v_info

    def delete_viewer(self, v_id):
        del self.viewers[v_id]

    def delete_all_viewers(self):
        self.viewers = {}


class WebServer:
    """
    Manages the lifetime of the pgwidgets web application that hosts the
    viewers.

    The pgwidgets ``Application`` runs its WebSocket and HTTP servers in
    their own background threads, so :meth:`start` does not block and does
    not take over the calling thread's event loop.  When a running asyncio
    loop is found (e.g. inside a Jupyter kernel), browser-initiated viewer
    callbacks are pumped onto that loop so they run on the kernel thread.
    Otherwise they are pumped from a private daemon thread.
    """

    def __init__(self, app, factory,
                 host='localhost', port=9909, ev_quit=None,
                 viewer_class=None):

        self.host = host
        self.port = port
        self.app = app
        self.logger = app.logger
        self.factory = factory
        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit
        self.default_viewer_class = viewer_class

        # callback-pump state
        self._pump_loop = None
        self._pump_handle = None
        self._pump_thread = None
        self._pump_interval = 0.05
        self._pump_stop = threading.Event()

    def start(self, use_thread=True, no_ioloop=True):
        """Start the web application servers.

        Parameters
        ----------
        use_thread : bool
            Unused; retained for backward compatibility.
        no_ioloop : bool
            Retained for backward compatibility.  The servers always run
            in their own background threads now, so this is effectively a
            no-op (kept so existing notebooks calling
            ``server.start(no_ioloop=True)`` keep working).
        """
        # starts the WebSocket server (background thread) and the HTTP
        # file server (background thread)
        self.app.start()

        # keep browser-initiated viewer callbacks flowing
        self._install_pump()

        self.logger.info("Open %s in a browser to view a viewer." %
                         (self.app.get_url(),))

    def _install_pump(self):
        # Find a running event loop to attach the pump to (the Jupyter
        # kernel keeps one running).  If found, callbacks run on that
        # loop's thread; otherwise fall back to a private daemon thread.
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

        self._pump_stop.clear()

        if loop is not None and loop.is_running():
            self._pump_loop = loop
            loop.call_soon_threadsafe(self._pump_once)
            self.logger.debug("pumping viewer events on the running "
                              "asyncio loop")
        else:
            self._pump_loop = None
            self._pump_thread = threading.Thread(target=self._pump_thread_loop,
                                                 daemon=True)
            self._pump_thread.start()
            self.logger.debug("pumping viewer events on a daemon thread")

    def _pump_once(self):
        # runs on the asyncio loop thread; drain pending callbacks without
        # blocking, then reschedule
        if self._pump_stop.is_set():
            return
        try:
            self.app.process_events(0)
        except Exception:
            self.logger.error("error processing viewer events",
                              exc_info=True)
        if self._pump_loop is not None and not self._pump_stop.is_set():
            self._pump_handle = self._pump_loop.call_later(
                self._pump_interval, self._pump_once)

    def _pump_thread_loop(self):
        while not self._pump_stop.is_set():
            try:
                self.app.process_events(self._pump_interval)
            except Exception:
                self.logger.error("error processing viewer events",
                                  exc_info=True)

    def stop(self):
        # stop the callback pump
        self._pump_stop.set()
        if self._pump_loop is not None and self._pump_handle is not None:
            try:
                self._pump_loop.call_soon_threadsafe(self._pump_handle.cancel)
            except Exception:
                pass
        self._pump_loop = None

        # close all sessions and stop the servers
        try:
            self.app.close()
        except Exception:
            self.logger.error("error closing application", exc_info=True)

        self.ev_quit.set()

    def get_viewer(self, v_id, viewer_class=None, width=512, height=512,
                   force_new=False):

        if viewer_class is None:
            viewer_class = self.default_viewer_class

        v_info = self.factory.get_viewer(v_id, viewer_class=viewer_class,
                                         width=width, height=height,
                                         force_new=force_new)
        return v_info.viewer


def make_server(host='localhost', port=9909, ev_quit=None,
                viewer_class=None, logger=None, numthreads=5,
                max_sessions=None, use_opencv=False):
    """Create and return a :class:`WebServer` hosting Ginga web viewers.

    Parameters
    ----------
    host : str
        Interface to bind to (default ``'localhost'``).
    port : int
        HTTP port to serve the viewer pages on (default ``9909``).  The
        WebSocket server uses ``port + 1``.
    ev_quit : threading.Event or None
        Optional shared quit event.
    viewer_class : class or None
        Default viewer class for :meth:`WebServer.get_viewer`
        (defaults to :class:`EnhancedCanvasView`).
    logger : logging-compatible logger or None
        If None, a simple stderr logger is created so the connect URL is
        printed.
    numthreads : int
        Unused; retained for backward compatibility.
    max_sessions : int or None
        Maximum number of concurrent browser sessions.  ``None`` (the
        default) means unlimited, which allows several independent
        viewers.
    use_opencv : bool
        Unused; retained for backward compatibility.

    Returns
    -------
    server : WebServer
        The (not-yet-started) web server.  Call :meth:`WebServer.start`.
    """
    if logger is None:
        logger = log.get_logger("ipg", level=logging.INFO, log_stderr=True)

    # The Ginga pgw Application starts both the WebSocket server and a
    # built-in HTTP server (serving the pgwidgets JS/CSS) -- enable the
    # latter so a browser can load the viewer page.
    app = Widgets.Application(logger=logger, host=host, port=port,
                              http_server=True, max_sessions=max_sessions)

    factory = ViewerFactory(logger, app)

    server = WebServer(app, factory, host=host, port=port,
                       ev_quit=ev_quit, viewer_class=viewer_class)
    return server
