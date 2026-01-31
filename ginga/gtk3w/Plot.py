#
# Plot.py -- Plotting function for Ginga viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import matplotlib
matplotlib.use('GTK3Cairo')
from matplotlib.backends.backend_gtk3cairo import (FigureCanvasGTK3Cairo
                                                   as FigureCanvas)  # noqa
# NOTE: imported here so available when importing ginga.gw.Plot
from ginga.mplw.EventMixin import PlotEventMixin  # noqa
from ginga.gtk3w import Widgets  # noqa


class PlotWidget(Widgets.WidgetBase):

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__()

        self.widget = FigureCanvas(plot.get_figure())
        self.viewer = None

        if plot is not None:
            self.set_plot(plot)

        self.widget.set_size_request(width, height)
        self.widget.show_all()

    def set_plot(self, plot):
        self.plot = plot
        self.logger = plot.logger
        self.logger.debug("set_plot called")

        plot.connect_ui(self.widget)
