#! /usr/bin/env python
#
# example4_mpl.py -- Load a fits file into a Ginga widget with a
#          matplotlib backend.  Simple
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
#
"""
   $ ./example4_mpl.py <fitsfile>
"""
import sys
import logging
import matplotlib
options = ['Qt4Agg', 'GTK', 'GTKAgg', 'MacOSX', 'GTKCairo', 'WXAgg',
           'TkAgg', 'QtAgg', 'FltkAgg', 'WX']
# Try whatever toolkit you have installed
matplotlib.use('TkAgg')
import numpy as np
import matplotlib.pyplot as plt

from ginga.mplw.FitsImageCanvasMpl import FitsImageCanvas
from ginga.misc.NullLogger import NullLogger
from ginga.AstroImage import AstroImage
from ginga import cmap

use_logger = False

if use_logger:
    logger = logging.getLogger("example4")
    stderrHdlr = logging.StreamHandler()
    stderrHdlr.setLevel(logging.WARN)
    logger.addHandler(stderrHdlr)
else:
    logger = NullLogger()

fig = plt.figure()
fi = FitsImageCanvas(logger)
w = fig.canvas
fi.set_widget(w)
fi.set_figure(fig)

# Set up some defaults for the viewer
fi.enable_autocuts('on')
fi.set_autocut_params('zscale')
fi.enable_autozoom('on')
#fi.set_bg(0.2, 0.2, 0.2)
#fi.ui_setActive(True)
#fi.set_cmap(cmap.get_cmap('rainbow3'))

# Enable user interactive controls
bd = fi.get_bindings()
bd.enable_pan(True)
bd.enable_zoom(True)
bd.enable_cuts(True)
bd.enable_flip(True)
bd.enable_rotate(True)
bd.enable_cmap(True)

# Load a FITS file from the command line (if provided)
image = AstroImage(logger)
if len(sys.argv) > 1:
    image.load_file(sys.argv[1])
fi.set_image(image)

plt.show()


