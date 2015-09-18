#! /usr/bin/env python
#
# ipg.py -- Simple FITS viewer in an HTML5 canvas web browser.
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

Usage:
(server side)
    ./example1_pg.py -p 6500 --host='' -d /path/to/root/of/fits/files \
        --loglevel=20

Use --host='' if you want to listen on all network interfaces.

(client side)
From the browser, type in a URL based on the port that you chose above, e.g.:

    http://servername:6500/viewer?id=v1&width=600&height=600&path=some/file.fits

The `path` should be to a file *on the server side, relative to the directory
specified using -d.

If `width` and `height` are omitted they default to the browser's page size.
NOTE that because all rendering is done on the server side, you will achieve
better performance if you choose a smaller rendering size.

`id` is an identifier that will identify the same viewer each time you
request it.

You will need a reasonably modern web browser with HTML5 canvas support.
Tested with Chromium 41.0.2272.76, Firefox 37.0.2, Safari 7.1.6
"""
from __future__ import print_function
import sys, os
import logging
import threading

import tornado.web
import tornado.template
import tornado.ioloop

from ginga.web.pgw.ImageViewPg import ImageViewCanvas, RenderWidgetZoom
from ginga import AstroImage, colors
from ginga.misc import log, Task
from ginga.util import catalog, iohelper

from ginga.web.pgw import templates, js


STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

LOADER = tornado.template.Loader(os.path.dirname(templates.__file__))


class ViewerWidget(RenderWidgetZoom):

    def initialize(self, name, factory):
        self.logger = factory.logger
        self.logger.info("fitsviewer intialize")
        self.viewer_factory = factory
        self.thread_pool = factory.get_threadpool()

        super(ViewerWidget, self).initialize(name)
        self.logger.info("Interval is %f" % (self.interval))
        self.interval = 10

    def get(self):
        self.logger.info("fitsviewer get")
        # Collect arguments
        v_id = self.get_argument('id', '0')
        path = self.get_argument('path', None)

        # Get a viewer with this id
        viewer = self.viewer_factory.get_viewer(v_id)
        self.set_viewer(viewer)

        # Anything we need to customize about this viewer
        viewer.set_callback('drag-drop', self.drop_file)
        ## viewer.set_callback('none-move', self.motion)

        if (path is not None) and (len(path) > 0):
            #self.load_file(path)
            task = Task.FuncTask2(self.load_file, path)
            self.thread_pool.addTask(task)

    def get_fileinfo(self, filespec, dldir='/tmp'):

        # Get information about this file/URL
        info = iohelper.get_fileinfo(filespec, cache_dir=dldir)

        if (not info.ondisk) and (info.url is not None) and \
               (not info.url.startswith('file:')):
            # Download the file if a URL was passed
            def  _dl_indicator(count, blksize, totalsize):
                pct = float(count * blksize) / float(totalsize)
                msg = "Downloading: %%%.2f complete" % (pct*100.0)
                self.viewer.onscreen_message(msg, delay=1.0)

            # Try to download the URL.  We press our generic URL server
            # into use as a generic file downloader.
            try:
                dl = catalog.URLServer(self.logger, "downloader", "dl",
                                       info.url, "")
                filepath = dl.retrieve(info.url, filepath=info.filepath,
                                       cb_fn=_dl_indicator)
            finally:
                self.viewer.clear_onscreen_message()

        return info

    def load_file(self, path):
        image = AstroImage.AstroImage(logger=self.logger)

        try:
            info = self.get_fileinfo(path)
            if info.url.startswith('file:'):
                basedir = self.viewer_factory.get_basedir()
                fullpath = os.path.join(basedir, info.filepath)
            else:
                fullpath = info.filepath

            image.load_file(fullpath)

            self.viewer.set_image(image)
        except Exception as e:
            self.logger.error("Error loading uri (%s): %s" % (
                path, str(e)))
            # TODO: include traceback, error message to browser

        ## self.setWindowTitle(filepath)

    def drop_file(self, viewer, paths):
        path = paths[0]
        self.load_file(path)


class FileHandler(tornado.web.RequestHandler):

    v_count = 0

    @classmethod
    def get_vid(cls):
        v_id = "vcanvas-%d" % (cls.v_count)
        cls.v_count += 1
        return v_id

    def initialize(self, name, url, factory):
        self.viewer_factory = factory
        self.logger = factory.logger
        self.logger.info("filehandler initialize")
        self.name = name
        self.url = url

    def get(self):
        self.logger.info("filehandler get")
        # Collect arguments
        v_id = self.get_argument('id', None)
        if v_id is None:
            v_id = FileHandler.get_vid()
        width = self.get_argument('width', None)
        if width is None:
            width = 'fullWidth'
        else:
            width = int(width)
        height = self.get_argument('height', None)
        if height is None:
            height = 'fullHeight'
        else:
            height = int(height)
        path = self.get_argument('path', None)

        # Get a viewer with this id
        viewer = self.viewer_factory.get_viewer(v_id)

        # Return the data for this page
        t = LOADER.load("index.html")

        ws_url = os.path.join(self.url, "socket?id=%s" % (v_id))
        if path is not None:
            ws_url += ("&path=%s" % (path))

        self.write(t.generate(
            title=self.name, url=self.url, ws_url=ws_url,
            width=width, height=height, v_id=v_id))


class ImageViewer(ImageViewCanvas):

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
        DrawingCanvas = self.get_canvas().get_draw_class('drawingcanvas')
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        canvas.ui_setActive(True)
        canvas.set_surface(self)
        # add the canvas to the view.
        self.add(canvas, tag=tag)
        return canvas


class ViewerFactory(object):

    def __init__(self, logger, basedir, thread_pool):
        """
        Constructor parameters:
          `logger` : a logging-module compatible logger object
          `basedir`: directory to which paths requested on the viewer
                        are considered relative to.
        """
        self.logger = logger
        self.basedir = basedir
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

        viewer = ImageViewer(self.logger)
        # configuring surface allows drawing before viewer canvas is
        # realized in browser
        viewer.configure_surface(600, 600)

        # customize this viewer
        viewer.enable_autocuts('on')
        viewer.set_autocut_params('zscale')
        viewer.enable_autozoom('on')
        viewer.set_zoom_algorithm('rate')
        viewer.set_zoomrate(1.4)
        viewer.show_pan_mark(True)
        viewer.enable_draw(False)
        viewer.set_bg(0.2, 0.2, 0.2)
        viewer.ui_setActive(True)

        bd = viewer.get_bindings()
        bd.enable_all(True)

        self.viewers[v_id] = viewer
        return viewer


class WebServer(object):

    def __init__(self, logger, thread_pool, factory,
                 host='localhost', port=9909, ev_quit=None):

        self.host = host
        self.port = port
        self.logger = logger
        self.thread_pool = thread_pool
        self.factory = factory
        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit

        self.app = None

    def start(self, use_thread=True, no_ioloop=False):
        self.thread_pool.startall()

        js_path = os.path.dirname(js.__file__)

        # create and run the app
        self.app = tornado.web.Application([
            (r"/js/(.*\.js)", tornado.web.StaticFileHandler,
             {"path":  js_path}),
            (r"/viewer", FileHandler,
              dict(name='Ginga', url='/viewer', factory=self.factory)),
             ("/viewer/socket", ViewerWidget,
              dict(name='Ginga', factory=self.factory)),
            ],
               factory=self.factory, logger=self.logger)

        self.app.listen(self.port, self.host)
        self.url_base = "http://%s:%d/viewer" % (self.host, self.port)
        self.logger.info("ginga web now running at " + self.url_base)

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
        url = "%s?id=%s" % (self.url_base, v_id)
        display(HTML('<a href="%s">link to viewer</a>' % url))
        return v


def showplt():
    from io import BytesIO
    import matplotlib
    # Hack to force matplotlib to not use any Xwindows backend.
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from IPython.display import Image

    buf = BytesIO()
    plt.savefig(buf, bbox_inches=0)
    img = Image(data=bytes(buf.getvalue()),
                   format='png', embed=True)
    buf.close()
    return img


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
    factory = ViewerFactory(logger, basedir, thread_pool)
    server = WebServer(logger, thread_pool, factory,
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
