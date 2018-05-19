#
# Plot.py -- Plotting function for Gen2 FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import matplotlib
# GTKCairo backend is slow to redraw compared to GTKAgg!
## matplotlib.use('GTKCairo')
## from matplotlib.backends.backend_gtkcairo import (FigureCanvasGTKCairo
##                                                   as FigureCanvas)  # noqa
matplotlib.use('GTKAgg')
from matplotlib.backends.backend_gtkagg import (FigureCanvasGTKAgg
                                                 as FigureCanvas)  # noqa
from ginga.gtkw import Widgets  # noqa


class PlotWidget(Widgets.WidgetBase):

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__()

        self.widget = FigureCanvas(plot.get_figure())
        self.plot = plot
        self.logger = plot.logger

        self.widget.set_size_request(width, height)
        self.widget.show_all()

    def set_plot(self, plot):
        self.plot = plot
        self.logger = plot.logger
        self.logger.debug("set_plot called")

    def configure_window(self, wd, ht):
        self.logger.debug("canvas resized to %dx%d" % (wd, ht))
        fig = self.plot.get_figure()
        fig.set_size_inches(float(wd) / fig.dpi, float(ht) / fig.dpi)

# END
