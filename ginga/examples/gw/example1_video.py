#! /usr/bin/env python
#
# video_play.py -- video playback example with Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This example shows how Ginga has a fast enough refresh rate to play smooth
video.  I was able to play HD video at 30 fps on 2010 era computer with no
skips.

Caveats:
    1. There is no sound.  This is due to the lack of a decent python module
    that can read video files and provide _both_ audio and video streams.

    2. Currently, it expects an AVI file as a command line parameter.
    Only AVI formats supported by OpenCV can be used (typically JPEG encoded).

    Requirements:
    To run this example you will need the OpenCV bindings for Python installed.
    This module lets us access the video stream of an AVI file frame-by-frame.

Usage:
    $ example1_video.py [log options] <AVI file>

"""
from __future__ import print_function
import sys, os
import time
import logging, logging.handlers
import threading
import numpy
import ginga.util.six as six
if six.PY2:
    import Queue
else:
    import queue as Queue

import ginga.toolkit as ginga_toolkit
from ginga import AstroImage
from ginga import RGBImage
from ginga import AutoCuts, RGBMap
from ginga.misc import log, Task

try:
    import cv, cv2
except ImportError:
    print("You need to install the OpenCV python module to run this example")
    sys.exit(1)

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class GingaVision(object):

    def __init__(self, logger, ev_quit, options):
        super(GingaVision, self).__init__()
        self.logger = logger
        self.ev_quit = ev_quit

        from ginga.gw import Widgets, Viewers, GwHelp, GwMain

        self.card = 'default'
        # playback rate; changed when we know the actual rate
        self.fps = 30
        self.playback_rate = 1.0 / self.fps

        # Use an AstroImage, not RGBImage for now because we get a
        # different default (faster) scaling algorithm
        self.pimage = AstroImage.AstroImage()
        self.pdata = None

        self.app = Widgets.Application(logger=logger)
        self.app.add_callback('shutdown', self.quit)
        self.top = self.app.make_window("Ginga example2")
        self.top.add_callback('close', lambda *args: self.quit())

        thread_pool = Task.ThreadPool(2, logger, ev_quit=ev_quit)
        thread_pool.startall()
        self.main = GwMain.GwMain(logger=logger, ev_quit=ev_quit,
                                  app=self.app, thread_pool=thread_pool)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        fi = Viewers.CanvasView(logger=logger)
        fi.enable_autocuts('off')
        fi.set_autocut_params('histogram')
        fi.enable_autozoom('off')
        fi.cut_levels(0, 255)
        fi.defer_redraw = False
        fi.set_bg(0.2, 0.2, 0.2)
        # flip y
        fi.transform(False, False, False)
        fi.ui_setActive(True)
        self.fitsimage = fi

        # Some optomizations to smooth playback at decent FPS
        fi.set_redraw_lag(self.playback_rate)
        #fi.set_redraw_lag(0.0)
        fi._invertY = False
        # PassThruRGBMapper doesn't color map data--data is already colored
        rgbmap = RGBMap.PassThruRGBMapper(self.logger)
        fi.set_rgbmap(rgbmap)
        # Clip cuts assumes data does not need to be scaled in cut levels--
        # only clipped
        fi.set_autocuts(AutoCuts.Clip(logger=self.logger))

        bd = fi.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)
        bd.enable_flip(True)
        bd.enable_cmap(True)

        fi.set_desired_size(512, 512)
        iw = Viewers.GingaViewerWidget(viewer=fi)
        vbox.add_widget(iw, stretch=1)

        hbox = Widgets.HBox()
        hbox.set_margins(4, 2, 4, 2)

        wopen = Widgets.Button("Open File")
        #wopen.clicked.connect(self.open_file)
        wquit = Widgets.Button("Quit")
        wquit.add_callback('activated', lambda *args: self.quit())

        for w in (wopen, wquit):
            hbox.add_widget(w, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        vbox.add_widget(hbox, stretch=0)

        self.top.set_widget(vbox)
        self.top.set_title("Video Example Viewer")

    def quit(self):
        self.logger.info("quit called")
        self.top.delete()
        self.ev_quit.set()

    def set_playback_rate(self, fps):
        self.fps = fps
        self.playback_rate = 1.0 / self.fps
        self.fitsimage.set_redraw_lag(self.playback_rate)

    def show_frame(self, img):
        self.logger.debug("updating image")
        try:
            if (self.pdata is None) or (img.shape != self.pdata.shape):
                self.pdata = numpy.copy(img)
                self.pimage.set_data(self.pdata)
                self.main.gui_call(self.fitsimage.set_image, self.pimage)
            else:
                #self.pimage.set_data(img)
                self.pdata[::] = img[::]
                self.main.gui_call(self.fitsimage.redraw)

        except Exception as e:
            self.logger.error("Error unpacking packet: %s" % (
                str(e)))

    def capture_video(self, device):

        self.logger.info("capture video loop starting...")
        cap = cv2.VideoCapture(device)

        # Get width and height of frames and resize window
        width = cap.get(cv.CV_CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv.CV_CAP_PROP_FRAME_HEIGHT)
        self.logger.info("Video is %dx%d resolution" % (width, height))
        bd = 50
        self.main.gui_do(self.top.resize, width+bd, height+bd)

        # Get the frame rate
        fps = cap.get(cv.CV_CAP_PROP_FPS)
        if fps is not None:
            if not numpy.isnan(fps) and float(fps) >= 1.0:
                self.logger.info("Video rate is %d fps" % (fps))
                self.set_playback_rate(fps)

        # Get the frame count
        num_frames = cap.get(cv.CV_CAP_PROP_FRAME_COUNT)
        self.logger.info("There are %d frames" % (num_frames))

        # video frames seem to be returned with blue channel in LSByte
        self.pimage.set_order('BGR')

        frame = 0
        while not self.ev_quit.isSet():
            start_time = time.time()
            self.logger.debug("capture frame")
            frame += 1
            f, img = cap.read()
            self.logger.debug("frame %d: capture time: %.4f" % (
                frame, time.time() - start_time))

            split_time = time.time()
            if img is not None:
                self.show_frame(img)

            end_time = time.time()
            self.logger.debug("redraw time %.4f sec" % (end_time-split_time))
            elapsed_time = end_time - start_time
            sleep_time = self.playback_rate - elapsed_time
            if sleep_time < 0:
                self.logger.warning("underrun %.4f sec" % (-sleep_time))

            else:
                sleep_time = max(sleep_time, 0.0)
                self.logger.debug("sleeping for %.4f sec" % (sleep_time))
                time.sleep(sleep_time)
            #cv2.waitKey(1)

        self.logger.info("capture video loop terminating...")


def main(options, args):

    logger = log.get_logger("example2", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    # event for synchronizing exit of all threads
    ev_quit = threading.Event()

    gv = GingaVision(logger, ev_quit, options)
    gv.top.resize(670, 540)
    gv.top.show()
    gv.top.raise_()

    # start video capture thread
    if len(args) > 0:
        filename = args[0]
    else:
        # default video input device
        filename = 0

    gv.main.nongui_do(gv.capture_video, filename)

    gv.main.mainloop()
    logger.info("program terminating...")
    sys.exit(0)

if __name__ == '__main__':
    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))

    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--port", dest="port", metavar="NUM",
                      type='int', default=23099,
                      help="Port to use for receiving data")
    optprs.add_option("--other", dest="other", metavar="HOST",
                      help="Host to communicate with")
    optprs.add_option("-t", "--toolkit", dest="toolkit", metavar="NAME",
                      default='qt',
                      help="Choose GUI toolkit (gtk|qt)")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")
    log.addlogopts(optprs)

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


#END
