#! /usr/bin/env python
#
# video_play.py -- video playback example with Ginga
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
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

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtMain
from ginga.qtw.ImageViewCanvasQt import ImageViewCanvas
from ginga import AstroImage
from ginga import RGBImage
from ginga import AutoCuts, RGBMap

try:
    import cv, cv2
except ImportError:
    print("You need to install the OpenCV python module to run this example")
    sys.exit(1)
    
STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class GingaVision(QtGui.QMainWindow):

    def __init__(self, qtmain, logger, ev_quit, options):
        super(GingaVision, self).__init__()
        self.qtmain = qtmain
        self.logger = logger
        self.ev_quit = ev_quit

        self.card = 'default'
        # playback rate; changed when we know the actual rate
        self.fps = 30
        self.playback_rate = 1.0 / self.fps

        # Use an AstroImage, not RGBImage for now because we get a
        # different default (faster) scaling algorithm
        self.pimage = AstroImage.AstroImage()
        self.pdata = None

        fi = ImageViewCanvas(self.logger, render='widget')
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

        w = fi.get_widget()
        w.resize(512, 512)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)
        vbox.addWidget(w, stretch=1)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wopen = QtGui.QPushButton("Open File")
        #wopen.clicked.connect(self.open_file)
        wquit = QtGui.QPushButton("Quit")
        wquit.clicked.connect(self.quit)

        hbox.addStretch(1)
        for w in (wopen, wquit):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        vw = QtGui.QWidget()
        self.setCentralWidget(vw)
        vw.setLayout(vbox)

        self.setWindowTitle("Video Example Viewer")

    def quit(self):
        self.logger.info("quit called")
        self.deleteLater()
        self.ev_quit.set()

    def closeEvent(self, event):
        self.quit()

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
                self.qtmain.gui_call(self.fitsimage.set_image, self.pimage)
            else:
                #self.pimage.set_data(img)
                self.pdata[::] = img[::]
                self.qtmain.gui_call(self.fitsimage.redraw)

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
        self.resize(width+bd, height+bd)

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
                self.logger.warn("underrun %.4f sec" % (-sleep_time))

            else:
                sleep_time = max(sleep_time, 0.0)
                self.logger.debug("sleeping for %.4f sec" % (sleep_time))
                time.sleep(sleep_time)
            #cv2.waitKey(1)

        self.logger.info("capture video loop terminating...")


def main(options, args):

    # Set up the logger
    logger = logging.getLogger("video_play")
    logger.setLevel(options.loglevel)
    fmt = logging.Formatter(STD_FORMAT)
    if options.logfile:
        fileHdlr  = logging.handlers.RotatingFileHandler(options.logfile)
        fileHdlr.setLevel(options.loglevel)
        fileHdlr.setFormatter(fmt)
        logger.addHandler(fileHdlr)

    if options.logstderr:
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setLevel(options.loglevel)
        stderrHdlr.setFormatter(fmt)
        logger.addHandler(stderrHdlr)

    # event for synchronizing exit of all threads
    ev_quit = threading.Event()

    # Create top level of Qt application w/custom event loop
    myqt = QtMain.QtMain(logger=logger, ev_quit=ev_quit)

    gv = GingaVision(myqt, logger, ev_quit, options)
    gv.resize(670, 540)
    gv.show()

    # start video capture thread
    if len(args) > 0:
        filename = args[0]
    else:
        # default video input device
        filename = 0
        
    t = threading.Thread(target=gv.capture_video, args=[filename])
    t.start()

    myqt.mainloop()
    logger.info("program terminating...")
    sys.exit(0)

if __name__ == '__main__':
    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))
    
    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type='int', default=logging.INFO,
                      help="Set logging level to LEVEL")
    optprs.add_option("--port", dest="port", metavar="NUM",
                      type='int', default=23099,
                      help="Port to use for receiving data")
    optprs.add_option("--other", dest="other", metavar="HOST",
                      help="Host to communicate with")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
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

    
#END
