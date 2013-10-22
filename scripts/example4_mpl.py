#! /usr/bin/env python
#
# example4_mpl.py -- Load a fits file into a Ginga widget with a
#          matplotlib backend.
#
# Eric Jeschke (eric@naoj.org)
#
"""
   $ ./example4_mpl.py <fitsfile>
"""
import sys
import matplotlib
options = ['Qt4Agg', 'GTK', 'GTKAgg', 'MacOSX', 'GTKCairo', 'WXAgg',
           'TkAgg', 'QtAgg', 'FltkAgg', 'WX']
# Force a specific toolkit, if you leave commented matplotlib will choose
# an appropriate one for your system
#matplotlib.use('QtAgg')
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from ginga.mplw.FitsImageCanvasMpl import FitsImageCanvas
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
fi = FitsImageCanvas(logger)
fi.enable_autocuts('on')
fi.set_autocut_params('zscale')
#fi.set_cmap(cmap.get_cmap('rainbow3'))
fi.set_figure(fig)

# enable all interactive ginga features
fi.get_bindings().enable_all(True)

# load an image
if len(sys.argv) < 2:
    print "Please provide a FITS file on the command line"
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
#    http://ginga.readthedocs.org/en/latest/quickref.html
plt.show()
