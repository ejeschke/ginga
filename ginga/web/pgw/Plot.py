#
# Plot.py -- Plotting function for Ginga scientific viewer.
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from ginga.base.PlotBase import PlotBase, HistogramMixin, CutsMixin
from ginga.web.pgw import Widgets

class Plot(PlotBase):

    def __init__(self, logger, width=5, height=5, dpi=100):
        PlotBase.__init__(self, logger, FigureCanvas,
                          width=width, height=height, dpi=dpi)

        self.viewer = None

    def set_widget(self, viewer):
        self.viewer = viewer

    def get_rgb_buffer(self):
        buf = BytesIO()
        self.fig.canvas.print_figure(buf, format='png')
        return buf.getvalue()

    def _draw(self):
        super(Plot, self)._draw()

        if self.viewer is not None:
            self.logger.debug("getting RGB buffer")
            buf = self.get_rgb_buffer()

            self.logger.debug("sending buffer")
            self.viewer.do_update(buf)

            self.logger.debug("sent buffer")

    def configure_window(self, wd, ht):
        self.logger.debug("canvas resized to %dx%d" % (wd, ht))

    def map_event(self, event):
        wd, ht = event.width, event.height
        self.configure_window(wd, ht)

        self._draw()

    def resize_event(self, event):
        wd, ht = event.x, event.y
        # Not yet ready for prime-time--browser seems to mess with the
        # aspect ratio
        self.configure_window(wd, ht)

        self._draw()


class Histogram(Plot, HistogramMixin):
    pass

class Cuts(Plot, CutsMixin):
    pass

class PlotViewer(Widgets.Canvas):
    """
    This class implements the server-side backend of the surface for a
    web-based Ginga viewer.  It uses a web socket to connect to an HTML5
    canvas with javascript callbacks in a web browser on the client.

    The viewer is created separately on the backend and connects to this
    surface via the set_viewer() method.
    """

    def __init__(self, plot=None, width=500, height=500):
        super(PlotViewer, self).__init__(width=width, height=height)

        if plot is None:
            plot = Plot(logger)
        self.logger = plot.logger

        self._configured = False

        self.set_plot(plot)

    def set_plot(self, plot):
        self.logger.debug("set_plot called")
        self.plot = plot
        #self.logger = plot.get_logger()

        self._dispatch_event_table = {
            "activate": self.ignore_event,
            "setbounds": plot.map_event,
            "mousedown": self.ignore_event,
            "mouseup": self.ignore_event,
            "mousemove": self.ignore_event,
            "mouseout": self.ignore_event,
            "mouseover": self.ignore_event,
            "mousewheel": self.ignore_event,
            "wheel": self.ignore_event,
            "click": self.ignore_event,
            "dblclick": self.ignore_event,
            "keydown": self.ignore_event,
            "keyup": self.ignore_event,
            "keypress": self.ignore_event,
            "resize": plot.resize_event,
            "focus": self.ignore_event,
            "focusout": self.ignore_event,
            "blur": self.ignore_event,
            "drop": self.ignore_event,
            "paste": self.ignore_event,
            # Hammer.js events
            "pinch": self.ignore_event,
            "pinchstart": self.ignore_event,
            "pinchend": self.ignore_event,
            "rotate": self.ignore_event,
            "rotatestart": self.ignore_event,
            "rotateend": self.ignore_event,
            "tap": self.ignore_event,
            "pan": self.ignore_event,
            "panstart": self.ignore_event,
            "panend": self.ignore_event,
            "swipe": self.ignore_event,
            }

        self.plot.set_widget(self)

    def get_plot(self):
        return self.plot

    def ignore_event(self, event):
        pass

    def refresh(self):
        app = self.get_app()
        app.do_operation('refresh_canvas', id=self.id)
        self.logger.debug("did refresh")

    def do_update(self, buf):
        #self.logger.debug("clear_rect")
        #self.clear_rect(0, 0, self.width, self.height)

        self.logger.debug("drawing %dx%d image" % (self.width, self.height))
        self.draw_image(buf, 0, 0, self.width, self.height)
        self.logger.debug("drew image")

        self.refresh()

    def _cb_redirect(self, event):
        method = self._dispatch_event_table[event.type]
        try:
            method(event)

        except Exception as e:
            self.logger.error("error redirecting '%s' event: %s" % (
                event.type, str(e)))
            # TODO: dump traceback to debug log


#END
