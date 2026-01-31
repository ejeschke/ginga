#
# Plot.py -- Plotting widget canvas wrapper.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from ginga.web.pgw import Widgets
# NOTE: imported here so available when importing ginga.gw.Plot
from ginga.web.pgw.EventMixin import PlotEventMixin  # noqa


class PlotWidget(Widgets.Canvas):
    """
    This class implements the server-side backend of the surface for a
    web-based plot viewer.  It uses a web socket to connect to an HTML5
    canvas with javascript callbacks in a web browser on the client.

    The viewer is created separately on the backend and connects to this
    surface via the set_viewer() method.
    """

    def __init__(self, plot, width=500, height=500):
        super().__init__(width=width, height=height)

        self.widget = FigureCanvas(plot.get_figure())
        self.logger = plot.logger

        # self._configured = False

        if plot is not None:
            self.set_plot(plot)

    def set_plot(self, plot):
        self.plot = plot
        self.viewer = plot
        self.logger = plot.logger
        self.logger.debug("set_plot called")

        viewer = self.plot
        self._dispatch_event_table = {
            "activate": self.ignore_event,
            "setbounds": self.map_event_cb,
            "pointerdown": viewer.button_press_event,
            "pointerup": viewer.button_release_event,
            "pointermove": viewer.motion_notify_event,
            "pointerout": viewer.leave_notify_event,
            "pointerover": viewer.enter_notify_event,
            "wheel": viewer.scroll_event,
            "click": self.ignore_event,
            "dblclick": self.ignore_event,
            "keydown": viewer.key_down_event,
            "keyup": viewer.key_up_event,
            "keypress": viewer.key_press_event,
            "resize": viewer.resize_event,
            "focus": lambda event: viewer.focus_event(event, True),
            "focusout": lambda event: viewer.focus_event(event, False),
            "blur": lambda event: viewer.focus_event(event, False),
            #"drop": viewer.drop_event,
            "paste": self.ignore_event,
            # Gesture events
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

        self.viewer.add_callback('redraw', self.redraw_cb)
        self.viewer.set_widget(self)

    def get_plot(self):
        return self.viewer

    def ignore_event(self, event):
        pass

    def do_refresh(self):
        app = self.get_app()
        app.do_operation('refresh_canvas', id=self.id)

    def get_rgb_buffer(self, plot):
        buf = BytesIO()
        fig = plot.get_figure()
        fig.canvas.print_figure(buf, format='png')
        wd, ht = plot.get_window_size()
        return (wd, ht, buf.getvalue())

    def redraw_cb(self, plot, whence):
        self.logger.debug("getting RGB buffer")
        wd, ht, buf = self.get_rgb_buffer(plot)

        self.logger.debug("drawing %dx%d image" % (wd, ht))
        self.draw_image(buf, 0, 0, wd, ht)

    def map_event_cb(self, event):
        wd, ht = event.width, event.height
        self.viewer.set_window_size(wd, ht)

        self.do_refresh()

    def _cb_redirect(self, event):
        method = self._dispatch_event_table[event.type]
        try:
            method(event)

        except Exception as e:
            self.logger.error("error redirecting '%s' event: %s" % (
                event.type, str(e)))
            # TODO: dump traceback to debug log


#END
