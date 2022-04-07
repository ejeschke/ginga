#
# Plot.py -- Plotting widget canvas wrapper.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

# GUI imports
from ginga.qtw import Widgets
from ginga.toolkit import toolkit

if toolkit in ('qt6', 'pyside6'):
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
else:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class PlotWidget(Widgets.WidgetBase):

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__()

        self.widget = FigureCanvas(plot.get_figure())
        self.widget._resizeEvent = self.widget.resizeEvent
        self.widget.resizeEvent = self.resize_event
        self.plot = plot
        self.logger = plot.logger

    def set_plot(self, plot):
        self.plot = plot
        self.logger = plot.logger
        self.logger.debug("set_plot called")

    def configure_window(self, wd, ht):
        fig = self.plot.get_figure()
        fig.set_size_inches(float(wd) / fig.dpi, float(ht) / fig.dpi)

    def resize_event(self, event):
        rect = self.widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        if width > 0 and height > 0:
            self.configure_window(width, height)
            self.widget._resizeEvent(event)

#END
