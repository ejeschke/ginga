#
# Plot.py -- Plotting widget canvas wrapper.
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from ginga.web.pgw import Widgets

class PlotWidget(Widgets.Canvas):
    """
    This class implements the server-side backend of the surface for a
    web-based plot viewer.  It uses a web socket to connect to an HTML5
    canvas with javascript callbacks in a web browser on the client.

    The viewer is created separately on the backend and connects to this
    surface via the set_viewer() method.
    """

    def __init__(self, plot, width=500, height=500):
        super(PlotWidget, self).__init__(width=width, height=height)

        self.widget = FigureCanvas(plot.get_figure())
        self.logger = plot.logger

        self._configured = False
        self.refresh_delay = 0.010

        self.set_plot(plot)

    def set_plot(self, plot):
        self.logger.debug("set_plot called")
        self.plot = plot

        self._dispatch_event_table = {
            "activate": self.ignore_event,
            "setbounds": self.map_event_cb,
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
            "resize": self.resize_event,
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

        self.plot.add_callback('draw-canvas', self.draw_cb)

        self.add_timer('refresh', self.refresh_cb)

    def get_plot(self):
        return self.plot

    def ignore_event(self, event):
        pass

    def refresh_cb(self):
        app = self.get_app()
        app.do_operation('refresh_canvas', id=self.id)
        self.reset_timer('refresh', self.refresh_delay)

    def get_rgb_buffer(self, plot):
        buf = BytesIO()
        fig = plot.get_figure()
        fig.canvas.print_figure(buf, format='png')
        wd, ht = self.width, self.height
        return (wd, ht, buf.getvalue())

    def draw_cb(self, plot):
        self.logger.debug("getting RGB buffer")
        wd, ht, buf = self.get_rgb_buffer(plot)

        #self.logger.debug("clear_rect")
        #self.clear_rect(0, 0, wd, ht)

        self.logger.debug("drawing %dx%d image" % (wd, ht))
        self.draw_image(buf, 0, 0, wd, ht)

        self.reset_timer('refresh', self.refresh_delay)

    def configure_window(self, wd, ht):
        self.logger.debug("canvas resized to %dx%d" % (wd, ht))
        fig = self.plot.get_figure()
        fig.set_size_inches(float(wd) / fig.dpi, float(ht) / fig.dpi)

    def map_event_cb(self, event):
        wd, ht = event.width, event.height
        self.configure_window(wd, ht)

        self.plot.draw()

    def resize_event(self, event):
        wd, ht = event.width, event.height
        self.configure_window(wd, ht)

        self.plot.draw()

    def _cb_redirect(self, event):
        method = self._dispatch_event_table[event.type]
        try:
            method(event)

        except Exception as e:
            self.logger.error("error redirecting '%s' event: %s" % (
                event.type, str(e)))
            # TODO: dump traceback to debug log


#END
