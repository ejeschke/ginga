#
# Plot.py -- Plotting function for Ginga viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import matplotlib
matplotlib.use('GTK4Cairo')
from matplotlib.backends.backend_gtk4cairo import (FigureCanvasGTK4Cairo
                                                   as FigureCanvas)  # noqa
# NOTE: imported here so available when importing ginga.gw.Plot
from ginga.mplw.EventMixin import PlotEventMixin as MplPlotMixin
from ginga.gtk4w import Widgets  # noqa


class PlotWidget(Widgets.WidgetBase):

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__()

        self.widget = FigureCanvas(plot.get_figure())

        if plot is not None:
            self.set_plot(plot)

        self.widget.set_size_request(width, height)

    def set_plot(self, plot):
        self.plot = plot
        self.logger = plot.logger
        self.logger.debug("set_plot called")

        plot.connect_ui(self.widget)


class PlotEventMixin(MplPlotMixin):

    def scroll_event(self, event):
        button = self._get_button(event)
        # NOTE: gtk4 changed the orientation of the up and down direction
        # from Gtk3 so we have to override it here
        if event.button == 'up':
            direction = 180.0
        elif event.button == 'down':
            direction = 0.0
        amount = event.step
        modifiers = self._get_modifiers(event)

        data_x, data_y = event.xdata, event.ydata
        self.set_last_data_xy(data_x, data_y)

        num_degrees = amount  # ???
        self.make_ui_callback_viewer(self, 'scroll',
                                     direction, num_degrees,
                                     data_x, data_y)
