#
# plotaide.py -- Utility functions for plotting using Ginga widgets.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
from collections import deque

import numpy as np

from ginga.misc import Bunch, Callback


class PlotAide(Callback.Callbacks):
    """
    TODO:
    [X] command to set X pan position to use full range of window
    [X] autoscroll (keep up with new points)
    [ ] show gaps in status
    [X] get it to start in "plot" keyboard mode
    [X] start off showing a reasonable view
    [X] Ability to gang plot controls or synchronize all plots
    """

    def __init__(self, viewer, share_cb=None):
        super(PlotAide, self).__init__()

        self.logger = viewer.get_logger()
        if share_cb is None:
            share_cb = Callback.Callbacks()
        self.share_cb = share_cb

        self.norm_bg = viewer.get_bg()
        self.norm_fg = viewer.get_fg()
        self.axis_bg = 'gray90'
        self.grid_fg = 'gray30'
        self.y_range = (0.0, 0.0)

        self.do = Bunch.Bunch(autoscale_y=True, autoscale_x=True,
                              autopan_x=True)
        self._panning_x = False
        self._scaling_y = False
        self._scaling_x = False
        self._yloscl = 0.80 #0.90
        self._yhiscl = 1.20 #1.05

        self.viewer = viewer
        fi = viewer
        # configure the ginga viewer for a plot
        fi.enable_autozoom('off')
        fi.ui_set_active(True)
        fi.add_callback('configure', lambda *args: self.adjust_resize())

        # disable normal user interaction
        bd = fi.get_bindings()
        bd.enable_all(False)
        self.bd = bd

        bm = fi.get_bindmap()
        # add a new "plot" mode
        bm.add_mode('__p', 'plot', mode_type='locked', msg=None)
        bm.set_mode('plot', mode_type='locked')
        # scrolling in this mode creates activity under event 'plot-zoom'
        bm.map_event('plot', [], 'sc_scroll', 'plot-zoom')
        bm.map_event('plot', ['ctrl'], 'sc_scroll', 'plot-zoom')
        fi.set_callback('plot-zoom-scroll', self.scroll_cb)
        bm.map_event('plot', [], 'pa_pan', 'plot-zoom')
        bm.map_event('plot', ['ctrl'], 'pa_pan', 'plot-zoom')
        fi.set_callback('plot-zoom-pan', self.scroll_by_pan_cb)

        bm.map_event('plot', [], 'kp_y', 'plot-autoscale-y')
        fi.set_callback('keydown-plot-autoscale-y', self._y_press_cb)
        bm.map_event('plot', [], 'kp_f', 'plot-fullscale-y')
        fi.set_callback('keydown-plot-fullscale-y', self.scale_y_full_cb)
        bm.map_event('plot', [], 'kp_x', 'plot-position-x')
        fi.set_callback('keydown-plot-position-x', self._x_press_cb)

        for name in ['plot-zoom-x', 'plot-zoom-y', 'pan',
                     'autopan-x', 'autoscale-y']:
            self.enable_callback(name)
        self.add_callback('plot-zoom-x', self.plot_zoom_x_cb)
        self.add_callback('plot-zoom-y', self.plot_zoom_y_cb)
        self.add_callback('autopan-x', self.toggle_autopan_x_cb)
        self.add_callback('autoscale-y', self.toggle_autoscale_y_cb)
        self.add_callback('pan', self.pan_cb)

        settings = fi.get_settings()
        settings.get_setting('pan').add_callback('set', self._pan_cb)

        # get our canvas
        canvas = fi.get_canvas()
        self.dc = canvas.get_draw_classes()
        self.canvas = self.dc.DrawingCanvas()
        canvas.add(self.canvas)

        # holds our individual XY plots
        self.plots = Bunch.Bunch()
        # holds other plot elements like PlotBG, XAxis, YAxis, PlotTitle, etc.
        self.plot_etc_l = []
        self.plot_etc_d = {}

    def get_widget(self):
        return self.viewer.get_widget()

    def set_y_range(self, y_lo, y_hi):
        self.y_range = (y_lo, y_hi)

    def get_y_range(self):
        return self.y_range

    def add_plot_etc(self, plotable):
        self.plot_etc_d[plotable.kind] = plotable
        self.plot_etc_l.append(plotable)
        self.canvas.add(plotable)

    def add_source(self, src, name=None):
        if name is None:
            name = src.name
        self.plots[name] = src

        self.canvas.add(src, tag=name)
        plot_bg = self.plot_etc_d.get('plot_bg', None)
        self.canvas.raise_object(src, aboveThis=plot_bg)

        src.plot()

        x1, x2 = src.get_data_x_limits()
        y1, y2 = self.get_y_range()
        limits = [(x1, y1), (x2, y2)]

        self.viewer.set_limits(limits)
        self.viewer.set_pan((x1 + x2) * 0.5, (y1 + y2) * 0.5)

    def update_plot(self):
        st = time.time()
        src = None
        for name, src in self.plots.items():
            src.plot()

        self.logger.info("%.5f sec partial 1" % (time.time() - st))
        x1, x2 = src.get_data_x_limits()
        xy1, xy2 = self.viewer.get_limits()
        y1, y2 = xy1[1], xy2[1]
        self.viewer.set_limits([(x1, y1), (x2, y2)])

        self.logger.info("%.5f sec partial 2" % (time.time() - st))
        self.adjust_view()

        et = time.time()
        self.logger.info("%.5f sec to update plot" % (et - st))

    def update_elements(self):
        for plotable in self.plot_etc_l:
            plotable.update_elements(self.viewer)

        self.viewer.redraw(whence=3)

    def update_resize(self):
        for plotable in self.plot_etc_l:
            plotable.update_resize(self.viewer)

        self.viewer.redraw(whence=3)

    def scale_y(self, y_lo, y_hi):
        """Scale the plot in the Y direction so that `y_lo` and `y_hi`
        are both visible.
        """
        self._scaling_y = True
        try:
            # expand Y range a little so that line is clearly visible
            y_lo, y_hi = y_lo * self._yloscl, y_hi * self._yhiscl

            # get current viewer limits for X
            vl = self.viewer.get_limits()
            x_lo, x_hi = vl[0][0], vl[1][0]

            self.viewer.set_limits([(x_lo, y_lo), (x_hi, y_hi)])
            self.viewer.zoom_fit(axis='y')

        finally:
            self._scaling_y = False

    def autoscale_y(self):
        # establish range of current Y plot
        pl = self.get_plot_limits()
        y_lo, y_hi = pl[0][1], pl[1][1]

        self.scale_y(y_lo, y_hi)

    def scale_y_full(self):
        # establish full range of Y
        y_lo, y_hi = self.get_y_range()

        self.scale_y(y_lo, y_hi)

    def scale_x(self, x_lo, x_hi):
        """Scale the plot in the X direction so that `x_lo` and `x_hi`
        are both visible.
        """
        self._scaling_x = True
        try:
            # expand Y range a little so that line is clearly visible
            #x_lo, x_hi = x_lo * self._xloscl, x_hi * self._xhiscl

            # get current viewer limits for Y
            vl = self.viewer.get_limits()
            y_lo, y_hi = vl[0][1], vl[1][1]

            self.viewer.set_limits([(x_lo, y_lo), (x_hi, y_hi)])
            self.viewer.zoom_fit(axis='x')

        finally:
            self._scaling_x = False

    def autoscale_x(self):
        # establish range of current X plot
        pl = self.get_plot_limits()
        x_lo, x_hi = pl[0][0], pl[1][0]

        self.scale_x(x_lo, x_hi)

    def scale_x_full(self):
        # establish full range of X
        x_lo, x_hi = self.get_x_range()

        self.scale_x(x_lo, x_hi)

    def autopan_x(self):
        """Pan the plot so that the most recent data is visible at
        the right side of the plot. i.e. "keep up with the plot"
        """
        self._panning_x = True
        try:
            wd, ht = self.viewer.get_window_size()
            px = 0
            y_axis = self.plot_etc_d.get('axis_y', None)
            if y_axis is not None:
                px = y_axis.width
            cx, cy = wd - px, ht // 2

            pl = self.get_data_limits()
            x_lo, x_hi = pl[0][0], pl[1][0]
            _, pan_y = self.viewer.get_pan()[:2]

            self.viewer.position_at_canvas_xy((x_hi, pan_y), (cx, cy))

        finally:
            self._panning_x = False

    def _y_press_cb(self, *args):
        """Called when the user presses 'y'.
        """
        autoscale_y = not self.do.autoscale_y
        self.make_callback('autoscale-y', autoscale_y)

    def toggle_autoscale_y_cb(self, plot, autoscale_y):
        """Called when the user toggles the 'autoscale Y' feature on or off.
        """
        self.do.autoscale_y = autoscale_y
        if not self.do.autoscale_y:
            msg = "Autoscale Y OFF"
        else:
            msg = "Autoscale Y ON"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def scale_y_full_cb(self, *args):
        self.do.autoscale_y = False
        self.scale_y_full()
        self.viewer.onscreen_message("Autoscale Y OFF", delay=1.0)
        self.adjust_view()

    def _x_press_cb(self, *args):
        """Called when the user presses 'x'.
        """
        autopan_x = not self.do.autopan_x
        self.make_callback('autopan-x', autopan_x)
        ## autoscale_x = not self.do.autoscale_x
        ## self.make_callback('autoscale-x', autoscale_x)

    def toggle_autopan_x_cb(self, plot, autopan_x):
        """Called when the user toggles the 'autopan X' feature on or off.
        """
        self.do.autopan_x = autopan_x
        if not self.do.autopan_x:
            msg = "Autopan X OFF"
        else:
            msg = "Autopan X ON"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def adjust_view(self):
        with self.viewer.suppress_redraw:
            if not self._scaling_x and self.do.autoscale_x:
                self.autoscale_x()
            elif not self._panning_x and self.do.autopan_x:
                self.autopan_x()
            if not self._scaling_y and self.do.autoscale_y:
                self.autoscale_y()

            self.update_elements()

    def adjust_resize(self):
        with self.viewer.suppress_redraw:
            self.update_resize()
            self.adjust_view()

    def pan_cb(self, plot, pan_pos):
        """Called when the user pans the plot viewer."""
        if self._panning_x:
            return
        t = pan_pos[0]
        _t, y = self.viewer.get_pan()[:2]
        self.viewer.set_pan(t, y)
        self.adjust_view()

    def _pan_cb(self, settings, pan_pos):
        """Called when the user pans our particular plot viewer."""
        self.adjust_view()

    def scroll_cb(self, viewer, event):
        direction = self.bd.get_direction(event.direction)
        zoom_direction = 'in' if direction == 'up' else 'out'
        zoom_axis = 'y' if 'ctrl' in event.modifiers else 'x'
        event = 'plot-zoom-{}'.format(zoom_axis)
        self.make_callback(event, zoom_direction)
        return True

    def scroll_by_pan_cb(self, viewer, event):
        bd = self.viewer.get_bindings()
        event = bd._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False
        self.scroll_cb(viewer, event)
        return True

    def plot_zoom_x_cb(self, plot, direction):
        scale_x, scale_y = self.viewer.get_scale_xy()
        zoomrate = self.viewer.get_zoomrate()

        with self.viewer.suppress_redraw:
            # zoom X axis
            if direction == 'in':
                scale_x *= zoomrate
            elif direction == 'out':
                scale_x *= 1.0 / zoomrate

            self.viewer.scale_to(scale_x, scale_y)
            if self.do.autopan_x:
                self.autopan_x()
            if self.do.autoscale_y:
                self.autoscale_y()

            self.update_elements()
        return True

    def plot_zoom_y_cb(self, plot, direction):
        scale_x, scale_y = self.viewer.get_scale_xy()
        zoomrate = self.viewer.get_zoomrate()

        with self.viewer.suppress_redraw:
            # zoom Y axis
            if direction == 'in':
                scale_y *= 1.1
            elif direction == 'out':
                scale_y *= 0.9

            self.viewer.scale_to(scale_x, scale_y)
            # turn off Y autoscaling, since user overrode it
            if self.do.autoscale_y:
                self.viewer.onscreen_message("Autoscale Y OFF", delay=1.0)
            self.do.autoscale_y = False

            self.update_elements()
        return True

    def get_plot_limits(self):
        x_vals = []
        y_vals = []
        for key, src in self.plots.items():
            limits = src.get_plot_limits()
            x_vals.append(limits.T[0])
            y_vals.append(limits.T[1])
        x_vals = np.array(x_vals).flatten()
        y_vals = np.array(y_vals).flatten()
        return np.array([(x_vals.min(), y_vals.min()),
                         (x_vals.max(), y_vals.max())])

    def get_data_limits(self):
        x_vals = []
        y_vals = []
        for key, src in self.plots.items():
            limits = src.get_data_limits()
            x_vals.append(limits.T[0])
            y_vals.append(limits.T[1])
        x_vals = np.array(x_vals).flatten()
        y_vals = np.array(y_vals).flatten()
        return np.array([(x_vals.min(), y_vals.min()),
                         (x_vals.max(), y_vals.max())])
