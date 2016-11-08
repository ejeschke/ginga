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
from __future__ import print_function
import sys, os
import math
import logging
import threading

import tornado.web
import tornado.ioloop

from ginga import AstroImage, colors
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc import log, Task
from ginga.util import catalog, iohelper
from ginga.Bindings import ImageViewBindings
from ginga.misc.Settings import SettingGroup
from ginga.util.paths import ginga_home

from ginga.web.pgw import templates, js, PgHelp, Widgets, Viewers


class EnhancedCanvasView(Viewers.CanvasView):

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

    def show(self):
        """
        Capture the window of a viewer.
        """
        # force any delayed redraws
        # TODO: this really needs to be addressed in get_rgb_image_as_bytes()
        # of the various superclasses, as it affects other backends as well
        self.redraw_now()

        from IPython.display import Image
        return Image(data=bytes(self.get_rgb_image_as_bytes(format='png')),
                     format='png', embed=True)

    def load_fits(self, filepath):
        """
        Load a FITS file into the viewer.
        """
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

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
        canvas.ui_setActive(True)
        canvas.set_surface(self)
        canvas.register_for_cursor_drawing(self)
        # add the canvas to the view.
        my_canvas.add(canvas, tag=tag)

        return canvas

class ImageViewer(object):

    def __init__(self, logger, window, viewer_class=None, width=512, height=512):
        if viewer_class is None:
            viewer_class = EnhancedCanvasView
        self.logger = logger
        self.url = window.url
        self.dc = get_canvas_types()
        self.pixel_base = 1.0

        self.top = window
        self.top.add_callback('close', self.closed)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        # load binding preferences if available
        cfgfile = os.path.join(ginga_home, "ipg_bindings.cfg")
        bindprefs = SettingGroup(name='bindings', logger=logger,
                                 preffile=cfgfile)
        bindprefs.load(onError='silent')

        bd = ImageViewBindings(logger, settings=bindprefs)

        fi = viewer_class(logger, bindings=bd)
        fi.url = self.url
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.1)
        fi.enable_autozoom('on')
        #fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi
        fi.ipg_parent = self

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.set_surface(fi)
        self.canvas = canvas
        # add canvas to view
        private_canvas = fi.get_canvas()
        private_canvas.add(canvas)
        canvas.ui_setActive(True)
        fi.set_canvas(canvas)

        fi.set_desired_size(width, height)
        # force allocation of a surface--may be resized later
        fi.configure_surface(width, height)

        # add little mode indicator that shows modal states in
        # the corner
        fi.show_mode_indicator(True)

        w = Viewers.GingaViewerWidget(viewer=fi)
        vbox.add_widget(w, stretch=1)

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        hbox = Widgets.HBox()
        hbox.add_widget(Widgets.Label('Zoom sensitivity: '))
        slider = Widgets.Slider(orientation='horizontal', dtype=float)
        slider.add_callback('value-changed',
                            lambda w, val: self.adjust_scrolling_accel_cb(val))
        slider.set_limits(1.0, 9.5, 0.1)
        val = 4.0
        slider.set_value(val)
        self.adjust_scrolling_accel_cb(val)
        hbox.add_widget(slider, stretch=1)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        # need to put this in an hbox with an expanding label or the
        # browser wants to resize the canvas, distorting it
        hbox = Widgets.HBox()
        hbox.add_widget(vbox, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        self.top.set_widget(hbox)

    def load_file(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.fitsimage.set_image(image)
        self.top.set_title(filepath)

    def drop_file(self, fitsimage, paths):
        fileName = paths[0]
        self.load_file(fileName)

    def motion(self, viewer, button, data_x, data_y):

        # Get the value under the data coordinates
        try:
            #value = viewer.get_data(data_x, data_y)
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x+0.5), int(data_y+0.5))

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
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def set_readout_text(self, text):
        self.readout.set_text(text)

    def adjust_scrolling_accel_cb(self, val):
        def f(x):
            return (math.log10(x) / (10 - x) * x/12) + 1.0001
        val2 = f(val)
        self.logger.debug("slider value is %f, setting will be %f" % (val, val2))
        # save scale
        scale_x, scale_y = self.fitsimage.get_scale_xy()
        self.fitsimage.set_zoomrate(val2)
        # restore scale
        self.fitsimage.scale_to(scale_x, scale_y)
        return True

    def closed(self, w):
        self.logger.info("Top window closed.")
        self.top = None
        sys.exit()


class FileHandler(tornado.web.RequestHandler):

    def initialize(self, name, factory):
        self.name = name
        self.viewer_factory = factory
        self.logger = factory.logger
        self.logger.info("filehandler initialize")

    def get(self):
        self.logger.info("filehandler get")
        # Collect arguments
        wid = self.get_argument('id', None)

        # Get window with this id
        window = self.app.get_window(wid)

        output = window.render()
        self.write(output)

class ViewerFactory(object):

    def __init__(self, logger, basedir, app, thread_pool):
        """
        Constructor parameters:
          `logger` : a logging-module compatible logger object
          `basedir`: directory to which paths requested on the viewer
                        are considered relative to.
        """
        self.logger = logger
        self.basedir = basedir
        self.app = app
        self.thread_pool = thread_pool
        # dict of viewers
        self.viewers = {}

    def get_basedir(self):
        return self.basedir

    def get_threadpool(self):
        return self.thread_pool

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

        # our own viewer object, customized with methods (see above)
        viewer = ImageViewer(self.logger, window,
                             viewer_class=viewer_class, width=width, height=height)
        #viewer.url = window.url

        self.viewers[v_id] = viewer
        return viewer

    def delete_viewer(self, v_id):
        del self.viewers[v_id]

    def delete_all_viewers(self):
        self.viewers = {}

class WebServer(object):

    def __init__(self, app, thread_pool, factory,
                 host='localhost', port=9909, ev_quit=None):

        self.host = host
        self.port = port
        self.app = app
        self.logger = app.logger
        self.thread_pool = thread_pool
        self.factory = factory
        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit

        self.server = None
        self.http_server = None

    def start(self, use_thread=True, no_ioloop=False):
        self.thread_pool.startall()

        js_path = os.path.dirname(js.__file__)

        self.server = tornado.web.Application([
            (r"/js/(.*\.js)", tornado.web.StaticFileHandler,
             {"path":  js_path}),
            (r"/viewer", FileHandler,
              dict(name='Ginga', factory=self.factory)),
            (r"/app", PgHelp.WindowHandler,
              dict(name='Application', url='/app', app=self.app)),
            (r"/app/socket", PgHelp.ApplicationHandler,
              dict(name='Ginga', app=self.app)),
            ## ("/viewer/socket", ViewerWidget,
            ##  dict(name='Ginga', factory=self.factory)),
            ],
               factory=self.factory, logger=self.logger)

        self.http_server = self.server.listen(self.port, self.host)

        if no_ioloop:
            self.t_ioloop = None
        else:
            self.t_ioloop = tornado.ioloop.IOLoop.instance()
            if use_thread:
                task = Task.FuncTask2(self.t_ioloop.start)
                self.thread_pool.addTask(task)
            else:
                self.t_ioloop.start()

    def stop(self):
        # how to stop tornado server?
        if self.t_ioloop is not None:
            self.t_ioloop.stop()

        self.thread_pool.stopall()
        self.ev_quit.set()
        # stop and dereference the tornado server
        if self.http_server is not None:
            self.http_server.stop()
            self.http_server = None
        self.server = None

    def get_viewer(self, v_id, viewer_class=None, width=512, height=512,
                   force_new=False):
        from IPython.display import display, HTML
        v = self.factory.get_viewer(v_id, viewer_class=viewer_class,
                                    width=width, height=height,
                                    force_new=force_new)
        url = v.top.url
        viewer = v.fitsimage
        viewer.url = url
        #display(HTML('<a href="%s">link to viewer</a>' % url))
        return viewer


def make_server(logger=None, basedir='.', numthreads=5,
                host='localhost', port=9909, use_opencv=False):

    if logger is None:
        logger = log.get_logger("ipg", null=True)
    ev_quit = threading.Event()

    if use_opencv:
        from ginga import trcalc
        try:
            trcalc.use('opencv')
        except Exception as e:
            logger.warning("Error using opencv: %s" % str(e))

    thread_pool = Task.ThreadPool(numthreads, logger,
                                  ev_quit=ev_quit)

    base_url = "http://%s:%d/app" % (host, port)
    app = Widgets.Application(logger=logger, base_url=base_url,
                              host=host, port=port)

    factory = ViewerFactory(logger, basedir, app, thread_pool)

    server = WebServer(app, thread_pool, factory,
                       host=host, port=port)

    return server


def main(options, args):

    logger = log.get_logger("ipg", options=options)

    server = make_server(logger=logger, basedir=options.basedir,
                         numthreads=options.numthreads, host=options.host,
                         port=options.port, use_opencv=options.use_opencv)

    try:
        server.start(use_thread=False)

    except KeyboardInterrupt:
        logger.info("Interrupted!")
        server.stop()

    logger.info("Server terminating...")


if __name__ == "__main__":

    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))

    optprs.add_option("-d", "--basedir", dest="basedir", metavar="DIR",
                      default=".",
                      help="Directory which is at the base of file open requests")
    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--host", dest="host", metavar="HOST",
                      default="localhost",
                      help="HOST used to decide which interfaces to listen on")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type='int', default=logging.INFO,
                      help="Set logging level to LEVEL")
    optprs.add_option("--numthreads", dest="numthreads", type="int",
                      default=5, metavar="NUM",
                      help="Start NUM threads in thread pool")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
    optprs.add_option("--opencv", dest="use_opencv", default=False,
                      action="store_true",
                      help="Use OpenCv acceleration")
    optprs.add_option("-p", "--port", dest="port",
                      type='int', default=9909, metavar="PORT",
                      help="Default PORT to use for the web socket")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")

    (options, args) = optprs.parse_args(sys.argv[1:])

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
