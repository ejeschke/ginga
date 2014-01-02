#
# Plot.py -- Plotting function for Gen2 FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# GUI imports
import gtk

import matplotlib
matplotlib.use('GTKCairo')
from  matplotlib.backends.backend_gtkcairo import FigureCanvasGTKCairo \
     as FigureCanvas
import pango

from ginga.base.PlotBase import PlotBase, HistogramMixin, CutsMixin

class Plot(PlotBase):

    def __init__(self, logger, width=300, height=300, dpi=100):
        PlotBase.__init__(self, logger, FigureCanvas,
                          width=width, height=height, dpi=dpi)

        self.canvas.set_size_request(width*dpi, height*dpi)
        self.canvas.show_all()

class Histogram(Plot, HistogramMixin):
    pass

class Cuts(Plot, CutsMixin):
    pass

#END
