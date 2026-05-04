#
# Plot.py -- Plotting widget canvas wrapper.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from io import BytesIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.transforms import Bbox

from ginga.web.pgw import Widgets
# NOTE: imported here so available when importing ginga.gw.Plot
from ginga.web.pgw.ImageViewPg import PgEventMixin as PlotEventMixin  # noqa
from ginga.web.pgw.ImageViewPg import ScrolledView


#class PlotWidget(Widgets.Image):
class PlotWidget(ScrolledView):
    """
    This class implements the server-side backend of the surface for a
    web-based plot viewer.  It uses a web socket to connect to an HTML5
    canvas with javascript callbacks in a web browser on the client.

    The viewer is created separately on the backend and connects to this
    surface via the set_viewer() method.
    """
    def __init__(self, plot, width=500, height=500):
        #super().__init__(interactive=True, use_animation_frame=True)
        #super().__init__(interactive=True)

        self._widget = FigureCanvas(plot.get_figure())
        self.image_format = 'png'

        super().__init__(plot)
        self.set_scroll_bar_visibility('auto', 'auto')
        if plot is not None:
            self.logger = plot.logger
            self.set_plot(plot)

    def set_plot(self, plot):
        self.logger.debug("set_plot called")
        self.plot = plot
        self.viewer = plot
        self.logger = plot.logger

        self.viewer.add_callback('redraw', self.redraw_cb)
        self.viewer.set_widget(self)

    def get_plot(self):
        return self.viewer

    def get_rgb_buffer(self, plot):
        buf = BytesIO()
        #wd, ht = plot.get_window_size()
        wd, ht = self.viewer_w.get_size()
        fig = plot.get_figure()
        # desired width x height in inches
        wd_in, ht_in = max(0.01, wd / fig.dpi), max(0.01, ht / fig.dpi)
        # figure width x height in inches
        _wd_in, _ht_in = fig.get_size_inches()
        _wd_px, _ht_px = int(_wd_in / fig.dpi), int(_ht_in / fig.dpi)

        if wd != _wd_px or ht != _ht_px:
            #print(f"FIGURE SIZE ({_wd_px}x{_ht_px}) DOES NOT MATCH WIDGET SIZE ({wd}x{ht})")
            fig.set_size_inches(wd_in, ht_in)
            fig.canvas.draw()
        else:
            #print(f"FIGURE SIZE ({_wd_px}x{_ht_px}) MATCHES WIDGET SIZE ({wd}x{ht})")
            pass

        # fig.canvas.print_figure(buf, format=self.image_format)
        bbox_in = Bbox([[0, 0], [wd_in, ht_in]])
        fig.savefig(buf, format=self.image_format, dpi='figure',
                    bbox_inches=bbox_in)
        buf.seek(0)
        # img = Image.open(buf)
        # img_wd, img_ht = img.size
        # if img_wd != wd or img_ht != ht:
        #     print(f"IMAGE SIZE ({img_wd}x{img_ht}) DOES NOT MATCH WIDGET SIZE ({wd}x{ht}")

        return (wd, ht, buf.getvalue())

    def redraw_cb(self, plot, whence):
        self.logger.debug("getting RGB buffer")
        wd, ht, buf = self.get_rgb_buffer(plot)

        self.logger.debug("drawing %dx%d image" % (wd, ht))
        #self.set_binary_image(buf, self.image_format)
        self.viewer_w.set_binary_image(buf, self.image_format)


#END
