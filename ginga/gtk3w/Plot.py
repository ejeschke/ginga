#
# Plot.py -- Plotting function for Ginga viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import matplotlib
matplotlib.use('GTK3Cairo')
from  matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo \
     as FigureCanvas
## matplotlib.use('GTK3Agg')
## from  matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg \
##      as FigureCanvas

from ginga.gtk3w import Widgets

class PlotWidget(Widgets.WidgetBase):

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__()

        self.widget = FigureCanvas(plot.get_figure())
        self.plot = plot

        self.widget.set_size_request(width, height)
        self.widget.show_all()

    def configure_window(self, wd, ht):
        self.logger.debug("canvas resized to %dx%d" % (wd, ht))
        fig = self.plot.get_figure()
        fig.set_size_inches(float(wd) / fig.dpi, float(ht) / fig.dpi)

#END
