#
# Plot.py -- Plotting widget canvas wrapper.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

# GUI imports
from ginga.qtw import Widgets
from ginga.toolkit import toolkit
# NOTE: imported here so available when importing ginga.gw.Plot
from ginga.mplw.EventMixin import PlotEventMixin  # noqa

if toolkit in ('qt6', 'pyside6'):
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
else:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class PlotWidget(Widgets.WidgetBase):

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__()

        self.widget = FigureCanvas(plot.get_figure())

        if plot is not None:
            self.set_plot(plot)

    def set_plot(self, plot):
        self.plot = plot
        self.logger = plot.logger
        self.logger.debug("set_plot called")

        plot.connect_ui(self.widget)
