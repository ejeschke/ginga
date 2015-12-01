#
# Plot.py -- Plotting widget canvas wrapper.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# GUI imports
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp, Widgets
from ginga.toolkit import toolkit

if toolkit == 'qt5':
    # qt5 backend is not yet released in matplotlib stable
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg \
         as FigureCanvas
else:
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg \
         as FigureCanvas

class PlotWidget(Widgets.WidgetBase):

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__()

        self.widget = FigureCanvas(plot.fig)
        #self.widget.resizeEvent = self.resize_event
        self.plot = plot

    def configure_window(self, wd, ht):
        self.logger.debug("canvas resized to %dx%d" % (wd, ht))
        fig = self.plot.fig
        fig.set_size_inches(float(wd) / fig.dpi, float(ht) / fig.dpi)

    def resize_event(self, *args):
        rect = self.widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        self.configure_window(width, height)
#END
