#
# Plot.py -- Plotting function for Ginga FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# GUI imports
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

import matplotlib
matplotlib.rcParams.update(matplotlib.rcParamsDefault)
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from ginga.base.PlotBase import PlotBase, HistogramMixin, CutsMixin

class Plot(PlotBase):

    def __init__(self, logger, width=300, height=300, dpi=100):
        PlotBase.__init__(self, logger, FigureCanvas,
                          width=width, height=height, dpi=dpi)

class Histogram(Plot, HistogramMixin):
    pass

class Cuts(Plot, CutsMixin):
    pass

#END
