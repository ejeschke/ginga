#! /usr/bin/env python
#
# ipg.py -- Module for simple FITS viewer in an HTML5 canvas web browser.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This example illustrates using a Ginga widget in a web browser,  All the
rendering is done on the server side and the browser only acts as a display
front end.  Using this you could create an analysis type environment on a
server and view it via a browser.

See example usage with an ipython notebook at:

    http://nbviewer.ipython.org/gist/ejeschke/6067409

You will need a reasonably modern web browser with HTML5 canvas support.
Tested with Chromium 41.0.2272.76, Firefox 37.0.2, Safari 7.1.6
"""
from __future__ import print_function
import sys, os
import logging
import threading

import tornado.web
import tornado.ioloop

from ginga import AstroImage, colors
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc import log, Task
from ginga.util import catalog, iohelper

from ginga.web.pgw import templates, js, PgHelp, Widgets, Viewers


class EnhancedCanvasView(Viewers.CanvasView):

    def show(self):
        from IPython.display import Image
        return Image(data=bytes(self.get_rgb_image_as_bytes(format='png')),
                     format='png', embed=True)

    def load(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.set_image(image)

    def add_canvas(self, tag=None):
        # add a canvas to the view
        my_canvas = self.get_canvas()
        DrawingCanvas = my_canvas.get_draw_class('drawingcanvas')
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        #canvas.enable_edit(True)
        canvas.ui_setActive(True)
        canvas.set_surface(self)
        # add the canvas to the view.
        my_canvas.add(canvas, tag=tag)

        return canvas


class ImageViewer(object):

    def __init__(self, logger, window):
        self.logger = logger
        self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()

        self.top = window
        self.top.add_callback('closed', self.closed)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        fi = EnhancedCanvasView(logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.4)
        fi.show_pan_mark(True)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.setSurface(fi)
        self.canvas = canvas
        # add canvas to view
        private_canvas = fi.get_canvas()
        private_canvas.add(canvas)
        canvas.ui_setActive(True)
        canvas.register_for_cursor_drawing(fi)
        ## self.drawtypes = canvas.get_drawtypes()
        ## self.drawtypes.sort()

        # add a color bar
        private_canvas.add(self.dc.ColorBar(side='bottom', offset=10))

        # add little mode indicator that shows modal states in
        # the corner
        private_canvas.add(self.dc.ModeIndicator(corner='ur', fontsize=14))
        # little hack necessary to get correct operation of the mode indicator
        # in all circumstances
        bm = fi.get_bindmap()
        bm.add_callback('mode-set', lambda *args: fi.redraw(whence=3))

        fi.set_desired_size(512, 512)
        w = Viewers.GingaViewer(viewer=fi)
        vbox.add_widget(w, stretch=1)

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        hbox = Widgets.HBox()
        btn3 = Widgets.CheckBox("I'm using a trackpad")
        btn3.add_callback('activated', lambda w, tf: self.use_trackpad_cb(tf))
        hbox.add_widget(btn3)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        self.top.set_widget(vbox)

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

        fits_x, fits_y = data_x + 1, data_y + 1

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
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def use_trackpad_cb(self, state):
        settings = self.fitsimage.get_bindings().get_settings()
        val = 1.0
        if state:
            val = 0.1
        settings.set(scroll_zoom_acceleration=val)

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

    def get_viewer(self, v_id):
        """
        Get an existing viewer by viewer id.  If the viewer does not yet
        exist, make a new one.
        """
        try:
            return self.viewers[v_id]
        except KeyError:
            pass

        #  create top level window
        window = self.app.make_window("Viewer %s" % v_id)

        # our own viewer object, customized with methods (see above)
        viewer = ImageViewer(self.logger, window)

        self.viewers[v_id] = viewer
        return viewer


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

        self.server.listen(self.port, self.host)

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
        if not self.t_ioloop is None:
            self.t_ioloop.stop()

        self.thread_pool.stopall()
        self.ev_quit.set()

    def get_viewer(self, v_id):
        from IPython.display import display, HTML
        v = self.factory.get_viewer(v_id)
        url = v.top.url
        display(HTML('<a href="%s">link to viewer</a>' % url))
        return v.fitsimage


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
            logger.warn("Error using opencv: %s" % str(e))

    thread_pool = Task.ThreadPool(numthreads, logger,
                                  ev_quit=ev_quit)

    base_url = "http://%s:%d/app" % (host, port)
    app = Widgets.Application(logger=logger, base_url=base_url)

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
