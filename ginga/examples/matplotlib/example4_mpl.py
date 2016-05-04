#! /usr/bin/env python
#
# example4_mpl.py -- Load a fits file into a Ginga widget with a
#          matplotlib backend.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
#
"""
   $ ./example4_mpl.py [fits file]

A Ginga object rendering to a generic matplotlib Figure.  In short,
this allows you to have all the interactive UI goodness of a Ginga widget
window in a matplotlib figure.  You can interactively flip, rotate, pan, zoom,
set cut levels and color map warp a FITS image.  Furthermore, you can plot
using matplotlib plotting on top of the image and the plots will follow all
the transformations.

See the Ginga quick reference
(http://ginga.readthedocs.io/en/latest/quickref.html)
for a list of the interactive features in the standard ginga widget.

example4 produces a simple matplotlib fits view with a couple of overplots.
This shows how you can use the functionality with straight python/matplotlib
sessions.  Run this by supplying a single FITS file on the command line.
"""
from __future__ import print_function
import sys, os
import platform
# just in case you want to use qt
os.environ['QT_API'] = 'pyqt'

import matplotlib
options = ['Qt4Agg', 'GTK', 'GTKAgg', 'MacOSX', 'GTKCairo', 'WXAgg',
           'TkAgg', 'QtAgg', 'FltkAgg', 'WX']
# Force a specific toolkit on mac
macos_ver = platform.mac_ver()[0]
if len(macos_ver) > 0:
    # change this to "pass" if you want to force a different backend
    # On Mac OS X I found the default choice for matplotlib is not stable
    # with ginga
    matplotlib.use('Qt4Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from ginga.mplw.ImageViewCanvasMpl import ImageViewCanvas
from ginga.misc import log
from ginga.AstroImage import AstroImage
from ginga import cmap
# add matplotlib colormaps to ginga's own set
cmap.add_matplotlib_cmaps()

# Set to True to get diagnostic logging output
use_logger = False
logger = log.get_logger(null=not use_logger, log_stderr=True)

# create a regular matplotlib figure
fig = plt.figure()

# create a ginga object, initialize some defaults and
# tell it about the figure
fi = ImageViewCanvas(logger)
fi.enable_autocuts('on')
fi.set_autocut_params('zscale')
#fi.set_cmap(cmap.get_cmap('rainbow3'))
fi.set_figure(fig)

# enable all interactive ginga features
fi.get_bindings().enable_all(True)

# load an image
if len(sys.argv) < 2:
    print("Please provide a FITS file on the command line")
    sys.exit(1)

image = AstroImage(logger)
image.load_file(sys.argv[1])
fi.set_image(image)
#fi.rotate(45)

# plot some example graphics via matplotlib

# Note adding axis from ginga (mpl backend) object
ax = fi.add_axes()
ax.hold(True)

wd, ht = image.get_size()

# plot a line
l = ax.plot((wd*0.33, wd*0.75), (ht*0.5, ht*0.75), 'go-',
            c="g",
            label='line1')
# a rect
r = patches.Rectangle((wd*0.10, ht*0.10), wd*0.6, ht*0.5, ec='b',
                      fill=False)
ax.add_patch(r)

# if you rotate, flip, zoom or pan the the ginga image the graphics
# stay properly plotted.  See quickref of interactive ginga commands here:
#    http://ginga.readthedocs.io/en/latest/quickref.html
plt.show()
