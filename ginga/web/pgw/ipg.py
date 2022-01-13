#! /usr/bin/env python
#
# ipg.py -- Module for simple FITS viewer in an HTML5 canvas web browser.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This example illustrates using a Ginga widget in a web browser,  All the
rendering is done on the server side and the browser only acts as a display
front end.  Using this you could create an analysis type environment on a
server and view it via a browser.

See example usage with an ipython notebook at:

    https://gist.github.com/ejeschke/6067409

You will need a reasonably modern web browser with HTML5 canvas support.
Tested with Chromium 41.0.2272.76, Firefox 37.0.2, Safari 7.1.6
"""

import sys
import os
import logging
import threading
import asyncio

import tornado.web

from ginga import AstroImage
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc import log, Bunch
from ginga.Bindings import ImageViewBindings
from ginga.misc.Settings import SettingGroup
from ginga.util.paths import ginga_home
from ginga.util import loader

from ginga.web.pgw import js, PgHelp, Widgets, Viewers


class BasicCanvasView(Viewers.CanvasView):

    def build_gui(self, container):
        """
        This is responsible for building the viewer's UI.  It should
        place the UI in `container`.  Override this to make a custom
        UI.
        """
        vbox = Widgets.VBox()
        vbox.set_border_width(0)

        w = Viewers.GingaViewerWidget(viewer=self)
        vbox.add_widget(w, stretch=1)

        # need to put this in an hbox with an expanding label or the
        # browser wants to resize the canvas, distorting it
        hbox = Widgets.HBox()
        hbox.add_widget(vbox, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        container.set_widget(hbox)

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

        w = Viewers.GingaViewerWidget(viewer=self)
        vbox.add_widget(w, stretch=1)

        # set up to capture cursor movement for reading out coordinates

        # coordinates reported in base 1 or 0?
        self.pixel_base = 1.0

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        #self.set_callback('none-move', self.motion_cb)
        self.set_callback('cursor-changed', self.motion_cb)

        # need to put this in an hbox with an expanding label or the
        # browser wants to resize the canvas, distorting it
        hbox = Widgets.HBox()
        hbox.add_widget(vbox, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        container.set_widget(hbox)

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


class ViewerFactory(object):
    """
    This is a factory class that churns out web viewers for a web
    application.

    The most important method of interest is get_viewer().
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

    def make_viewer(self, window, viewer_class=None,
                    width=512, height=512):
        if viewer_class is None:
            viewer_class = EnhancedCanvasView

        # load binding preferences if available
        cfgfile = os.path.join(ginga_home, "ipg_bindings.cfg")
        bindprefs = SettingGroup(name='bindings', logger=self.logger,
                                 preffile=cfgfile)
        bindprefs.load(onError='silent')

        bd = ImageViewBindings(self.logger, settings=bindprefs)

        fi = viewer_class(self.logger, bindings=bd)
        fi.url = window.url
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

        # Have the viewer build it's UI into the container
        fi.build_gui(window)

        v_info = Bunch.Bunch(url=window.url, viewer=fi,
                             top=window)
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

        #  create top level window
        window = self.app.make_window("Viewer %s" % v_id, wid=v_id)

        # We get back a record with information about the viewer
        v_info = self.make_viewer(window, viewer_class=viewer_class,
                                  width=width, height=height)

        # Save it under this viewer id
        self.viewers[v_id] = v_info
        return v_info

    def delete_viewer(self, v_id):
        del self.viewers[v_id]

    def delete_all_viewers(self):
        self.viewers = {}


class FileHandler(tornado.web.RequestHandler):
    """
    This is a handler that is started to allow a REST-type web API to
    create and manipulate viewers.

    Currently it only allows the following commands:
        .../viewer?id=v1&cmd=get           Create/access a viewer
        .../viewer?id=v1&cmd=load&path=... Load the viewer
    """

    def initialize(self, name, factory):
        self.name = name
        self.factory = factory
        self.logger = factory.logger
        self.logger.debug("filehandler initialize")

    def get(self):
        self.logger.debug("filehandler get")
        # Collect arguments
        # TODO: width, height?
        cmd = self.get_argument('cmd', 'get')
        v_id = self.get_argument('id', 'v1')

        v_info = self.factory.get_viewer(v_id)

        if cmd == 'get':
            self._do_get(v_info)

        elif cmd == 'load':
            self._do_load(v_info)

    def _do_get(self, v_info):
        # Get window
        window = v_info.top

        # render back to caller
        output = window.render()
        self.write(output)

    def _do_load(self, v_info):
        path = self.get_argument('path', None)
        if path is not None:
            v_info.viewer.load_fits(path)


class WebServer(object):

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

        self.server = None
        self.http_server = None

    def start(self, use_thread=True, no_ioloop=False):

        js_path = os.path.dirname(js.__file__)

        self.server = tornado.web.Application([
            (r"/js/(.*\.js)", tornado.web.StaticFileHandler,
             {"path": js_path}),
            (r"/viewer", FileHandler,
             dict(name='Ginga', factory=self.factory)),
            (r"/app", PgHelp.WindowHandler,
             dict(name='Application', url='/app', app=self.app)),
            (r"/app/socket", PgHelp.ApplicationHandler,
             dict(name='Ginga', app=self.app)),
        ], factory=self.factory, logger=self.logger)

        self.http_server = self.server.listen(self.port, self.host)

        if no_ioloop:
            self.t_ioloop = None
        else:
            try:
                # NOTE: tornado now uses the asyncio event loop
                self.t_ioloop = asyncio.get_running_loop()

            except RuntimeError as ex:
                self.t_ioloop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.t_ioloop)

    def stop(self):
        # how to stop tornado server?
        if self.t_ioloop is not None:
            self.t_ioloop.stop()

        self.ev_quit.set()
        # stop and dereference the tornado server
        if self.http_server is not None:
            self.http_server.stop()
            self.http_server = None
        self.server = None

    def get_viewer(self, v_id, viewer_class=None, width=512, height=512,
                   force_new=False):

        if viewer_class is None:
            viewer_class = self.default_viewer_class

        v_info = self.factory.get_viewer(v_id, viewer_class=viewer_class,
                                         width=width, height=height,
                                         force_new=force_new)
        return v_info.viewer


def make_server(logger=None, basedir='.', numthreads=5,
                host='localhost', port=9909, viewer_class=None,
                use_opencv=None):

    if logger is None:
        logger = log.get_logger("ipg", null=True)
    ev_quit = threading.Event()

    if use_opencv is not None:
        logger.warning("use_opencv parameter is deprecated, OpenCv will be used if installed")

    base_url = "http://%s:%d/app" % (host, port)
    app = Widgets.Application(logger=logger, base_url=base_url,
                              host=host, port=port)

    factory = ViewerFactory(logger, app)

    server = WebServer(app, factory,
                       host=host, port=port, viewer_class=viewer_class)

    return server


def main(options, args):

    logger = log.get_logger("ipg", options=options)

    server = make_server(logger=logger, basedir=options.basedir,
                         numthreads=options.numthreads, host=options.host,
                         port=options.port)
    viewer = server.get_viewer('v1')

    logger.info("Starting server with one viewer, connect at %s" % viewer.url)
    try:
        server.start(use_thread=False)

    except KeyboardInterrupt:
        logger.info("Interrupted!")
        server.stop()

    logger.info("Server terminating ...")


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("-d", "--basedir", dest="basedir", metavar="DIR",
                        default=".",
                        help="Directory which is at the base of file open requests")
    argprs.add_argument("--debug", dest="debug", default=False, action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--host", dest="host", metavar="HOST",
                        default="localhost",
                        help="HOST used to decide which interfaces to listen on")
    argprs.add_argument("--log", dest="logfile", metavar="FILE",
                        help="Write logging output to FILE")
    argprs.add_argument("--loglevel", dest="loglevel", metavar="LEVEL",
                        type=int, default=logging.INFO,
                        help="Set logging level to LEVEL")
    argprs.add_argument("--numthreads", dest="numthreads", type=int,
                        default=5, metavar="NUM",
                        help="Start NUM threads in thread pool")
    argprs.add_argument("--stderr", dest="logstderr", default=False,
                        action="store_true",
                        help="Copy logging also to stderr")
    argprs.add_argument("-p", "--port", dest="port",
                        type=int, default=9909, metavar="PORT",
                        help="Default PORT to use for the web socket")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys.argv[0]))
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
