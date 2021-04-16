#
# plotaide.py -- Utility class for plotting using Ginga widgets.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

import numpy as np

from ginga.misc import Bunch, Callback, Settings
from ginga.canvas import transform


class PlotAide(Callback.Callbacks):
    """
    PlotAide is a class to use a Ginga viewer as a high-performance
    interactive X/Y line plot viewer.
    """

    def __init__(self, viewer, settings=None):
        """PlotAide constructor.

        Parameters
        ----------
        viewer : subclass instance of `~ginga.ImageView.ImageViewBase`
            The ginga viewer that will be used to view the plot

        settings : `~ginga.misc.Settings.SettingGroup` or `None`
            Settings for the PlotAide.  If None, then a new SettingGroup
            will be created internally.
        """
        super(PlotAide, self).__init__()

        self.logger = viewer.get_logger()

        self.norm_bg = viewer.get_bg()
        self.norm_fg = viewer.get_fg()
        self.axis_bg = 'gray90'
        self.grid_fg = 'gray30'
        self.bbox = np.array([(0, 0), (0, 0), (0, 0), (0, 0)])

        if settings is None:
            settings = Settings.SettingGroup()
        self.settings = settings
        self.settings.set_defaults(autoaxis_x='on', autoaxis_y='on',
                                   autopan_x='off',
                                   autoaxis_y_mode='data')

        # internal flags used for synchronization
        self._panning_x = False
        self._scaling_y = False
        self._scaling_x = False

        self.viewer = viewer
        # configure the ginga viewer for a plot
        vi = viewer
        vi.set_background(self.norm_bg)

        # turn off sanity check on scaling, since scaling can get
        # wild with plots
        t_ = vi.get_settings()
        t_.set(sanity_check_scale=False)

        # add special plot transform
        self.plot_tr = transform.ScaleOffsetTransform()
        self.plot_tr.set_plot_scaling(1.0, 1.0, 0, 0)
        self.clip_tr = transform.ClipWindowTransform()
        vi.tform['data_to_plot'] = (vi.tform['data_to_native'] + self.plot_tr
                                    + self.clip_tr)

        vi.enable_autozoom('off')
        vi.ui_set_active(True)
        vi.set_enter_focus(True)
        vi.add_callback('configure', lambda *args: self.adjust_resize())
        vi.add_callback('transform', lambda *args: self.adjust_resize())

        # disable normal user interaction, except flip
        bd = vi.get_bindings()
        bd.enable_all(False)
        bd.enable_flip(True)
        self.bd = bd

        bm = vi.get_bindmap()
        # add a new "plot" mode
        bm.add_mode('__p', 'plot', mode_type='locked', msg=None)
        bm.set_mode('plot', mode_type='locked')
        # scrolling in this mode creates activity under event 'plot-zoom'
        bm.map_event('plot', [], 'sc_scroll', 'plot-zoom')
        bm.map_event('plot', ['ctrl'], 'sc_scroll', 'plot-zoom')
        vi.set_callback('plot-zoom-scroll', self.scroll_cb)
        bm.map_event('plot', [], 'pa_pan', 'plot-zoom')
        bm.map_event('plot', ['ctrl'], 'pa_pan', 'plot-zoom')
        vi.set_callback('plot-zoom-pan', self.scroll_by_pan_cb)

        bm.map_event('plot', [], 'kp_y', 'plot-autoaxis-y')
        vi.set_callback('keydown-plot-autoaxis-y', self._y_press_cb)
        bm.map_event('plot', [], 'kp_f', 'plot-fullscale-y')
        vi.set_callback('keydown-plot-fullscale-y', self.scale_y_full_cb)
        bm.map_event('plot', [], 'kp_x', 'plot-autoaxis-x')
        vi.set_callback('keydown-plot-autoaxis-x', self._x_press_cb)
        bm.map_event('plot', [], 'kp_p', 'plot-position-x')
        vi.set_callback('keydown-plot-position-x', self._p_press_cb)

        for name in ['plot-zoom-x', 'plot-zoom-y', 'pan',
                     'autopan-x', 'autoaxis-x', 'autoaxis-y']:
            self.enable_callback(name)
        self.add_callback('plot-zoom-x', self.plot_zoom_x_cb)
        self.add_callback('plot-zoom-y', self.plot_zoom_y_cb)
        self.add_callback('autopan-x', self.toggle_autopan_x_cb)
        self.add_callback('autoaxis-x', self.toggle_autoaxis_x_cb)
        self.add_callback('autoaxis-y', self.toggle_autoaxis_y_cb)
        self.add_callback('pan', self.pan_cb)

        settings = vi.get_settings()
        settings.get_setting('pan').add_callback('set', self._pan_cb)

        # get our canvas
        canvas = vi.get_canvas()
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

    def add_plot_etc(self, plotable):
        self.plot_etc_d[plotable.kind] = plotable
        self.plot_etc_l.append(plotable)
        self.canvas.add(plotable)

    def get_plot_etc(self, kind):
        return self.plot_etc_d[kind]

    def add_plot(self, plot):
        name = plot.name
        self.plots[name] = plot

        self.canvas.add(plot, tag=name)
        plot_bg = self.plot_etc_d.get('plot_bg', None)
        self.canvas.raise_object(plot, aboveThis=plot_bg)

        limits = self.get_limits('data')
        x1, y1 = limits[0][:2]
        x2, y2 = limits[1][:2]

        self.viewer.set_limits(limits)
        self.viewer.set_pan((x1 + x2) * 0.5, (y1 + y2) * 0.5)
        self.update_plots()

    def delete_plot(self, plot):
        name = plot.name
        del self.plots[name]

        self.canvas.delete_object_by_tag(name)
        self.update_plots()

    def get_plot(self, name):
        return self.plots[name]

    def update_plots(self):
        st = time.time()

        self.adjust_view()

        et = time.time()
        self.logger.debug("%.5f sec to update plot" % (et - st))

    def update_elements(self):
        for plotable in self.plot_etc_l:
            plotable.update_elements(self.viewer)

        ## for plotable in self.plots.values():
        ##     plotable.recalc(self.viewer)

        self.viewer.redraw(whence=3)

    def update_resize(self):
        # upon a resize, at first we redefine the plot bbox to encompass
        # the entire viewer area
        dims = self.viewer.get_window_size()
        wd, ht = dims[:2]
        # bbox is (LL, LR, UR, UL) in typical window coordinates
        self.bbox = np.array([(0, ht), (wd, ht), (wd, 0), (0, 0)])

        with self.viewer.suppress_redraw:
            # update all non-plot elements: axes, title, bg, etc
            # after this the plot bbox will have been redefined
            for plotable in self.plot_etc_l:
                plotable.update_bbox(self.viewer, dims)

            # update the plot transform based on the new plot bbox
            xy_lim = self.recalc_transform(dims)

            # second pass to allow non-plot elements to position their
            # components now that plox bbox is known
            for plotable in self.plot_etc_l:
                plotable.update_resize(self.viewer, dims, xy_lim)

            # now update all plots, due to the new transform
            for plot_src in self.plots.values():
                plot_src.update_resize(self.viewer, dims)

            # finally, redraw everything
            self.viewer.redraw(whence=3)

    def update_plot_bbox(self, x_lo=None, x_hi=None, y_lo=None, y_hi=None):
        _x_lo, _x_hi = self.bbox.T[0].min(), self.bbox.T[0].max()
        _y_lo, _y_hi = self.bbox.T[1].min(), self.bbox.T[1].max()

        if x_lo is not None:
            _x_lo = x_lo
        if x_hi is not None:
            _x_hi = x_hi
        if y_lo is not None:
            _y_lo = y_lo
        if y_hi is not None:
            _y_hi = y_hi

        # just in case caller got any of these mixed up
        x_lo, x_hi = min(_x_lo, _x_hi), max(_x_lo, _x_hi)
        y_lo, y_hi = min(_y_lo, _y_hi), max(_y_lo, _y_hi)

        self.bbox = np.array([(_x_lo, _y_hi), (_x_hi, _y_hi),
                              (_x_hi, _y_lo), (_x_lo, _y_lo)])

    def recalc_transform(self, dims):
        x_lo, x_hi = self.bbox.T[0].min(), self.bbox.T[0].max()
        y_lo, y_hi = self.bbox.T[1].min(), self.bbox.T[1].max()

        wd, ht = dims[:2]
        self.clip_tr.set_clip_window(x_lo, y_lo, x_hi, y_hi)

        x_pct = (x_hi - x_lo) / wd
        y_pct = (y_hi - y_lo) / ht

        self.plot_tr.set_plot_scaling(x_pct, y_pct, x_lo, y_lo)

        return (x_lo, y_lo, x_hi, y_hi)

    def set_limits(self, limits):
        self.viewer.set_limits(limits)

    def scale_y(self, y_lo, y_hi):
        """Scale the plot in the Y direction so that `y_lo` and `y_hi`
        are both visible.
        """
        self._scaling_y = True
        try:
            # get current viewer limits for X
            vl = self.viewer.get_limits()
            x_lo, x_hi = vl[0][0], vl[1][0]

            self.viewer.set_limits([(x_lo, y_lo), (x_hi, y_hi)])
            self.viewer.zoom_fit(axis='y')

        finally:
            self._scaling_y = False

    def autoscale_y(self):
        # establish range of current Y plot
        pl = self.get_limits(self.settings['autoaxis_y_mode'])

        y_lo, y_hi = pl[0][1], pl[1][1]

        self.scale_y(y_lo, y_hi)

    def scale_y_full(self):
        # establish full range of Y
        limits = self.get_limits('data')
        y_lo, y_hi = limits[0][1], limits[1][1]

        self.scale_y(y_lo, y_hi)

    def scale_x(self, x_lo, x_hi):
        """Scale the plot in the X direction so that `x_lo` and `x_hi`
        are both visible.
        """
        self._scaling_x = True
        try:
            # get current viewer limits for Y
            vl = self.viewer.get_limits()
            y_lo, y_hi = vl[0][1], vl[1][1]

            self.viewer.set_limits([(x_lo, y_lo), (x_hi, y_hi)])
            self.viewer.zoom_fit(axis='x')

        finally:
            self._scaling_x = False

    def autoscale_x(self):
        # establish range of current X plot
        pl = self.get_limits('data')
        #pl = self.get_limits('plot')
        x_lo, x_hi = pl[0][0], pl[1][0]

        self.scale_x(x_lo, x_hi)

    def scale_x_full(self):
        # establish full range of X
        limits = self.get_limits('data')
        x_lo, x_hi = limits[0][0], limits[1][0]

        self.scale_x(x_lo, x_hi)

    def autopan_x(self):
        """Pan the plot so that the most recent data is visible at
        the right side of the plot. i.e. "keep up with the plot"
        """
        self._panning_x = True
        try:
            wd, ht = self.viewer.get_window_size()
            cx, cy = wd, ht // 2

            pl = self.get_limits('data')
            x_lo, x_hi = pl[0][0], pl[1][0]
            _, pan_y = self.viewer.get_pan()[:2]

            self.viewer.position_at_canvas_xy((x_hi, pan_y), (cx, cy))

        finally:
            self._panning_x = False

    def _y_press_cb(self, *args):
        """Called when the user presses 'y'.
        """
        autoscale_y = self.settings['autoaxis_y'] == 'off'
        self.make_callback('autoaxis-y', autoscale_y)

    def toggle_autoaxis_x_cb(self, plot, autoaxis_x):
        """Called when the user toggles the 'autoscale X' feature on or off.
        """
        self.settings['autoaxis_x'] = 'on' if autoaxis_x else 'off'
        if self.settings['autoaxis_x'] == 'off':
            msg = "Autoscale X OFF"
        else:
            msg = "Autoscale X ON"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def toggle_autoaxis_y_cb(self, plot, autoaxis_y):
        """Called when the user toggles the 'autoscale Y' feature on or off.
        """
        self.settings['autoaxis_y'] = 'on' if autoaxis_y else 'off'
        if self.settings['autoaxis_y'] == 'off':
            msg = "Autoscale Y OFF"
        else:
            msg = "Autoscale Y ON"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def scale_y_full_cb(self, *args):
        self.settings['autoaxis_y'] = 'off'
        self.scale_y_full()
        self.viewer.onscreen_message("Autoscale Y OFF", delay=1.0)
        self.adjust_view()

    def _x_press_cb(self, *args):
        """Called when the user presses 'x'.
        """
        autoscale_x = self.settings['autoaxis_x'] == 'off'
        self.make_callback('autoaxis-x', autoscale_x)

    def _p_press_cb(self, *args):
        """Called when the user presses 'p'.
        """
        autopan_x = self.settings['autopan_x'] == 'off'
        self.make_callback('autopan-x', autopan_x)

    def toggle_autopan_x_cb(self, plot, autopan_x):
        """Called when the user toggles the 'autopan X' feature on or off.
        """
        self.settings['autopan_x'] = 'on' if autopan_x else 'off'
        if self.settings['autopan_x'] == 'off':
            msg = "Autopan X OFF"
        else:
            msg = "Autopan X ON"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def adjust_view(self):
        with self.viewer.suppress_redraw:
            if not self._scaling_x and self.settings['autoaxis_x'] == 'on':
                self.autoscale_x()
            elif not self._panning_x and self.settings['autopan_x'] == 'on':
                self.autopan_x()
            if not self._scaling_y and self.settings['autoaxis_y'] == 'on':
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
                scale_x *= (1.0 / zoomrate)

            self.viewer.scale_to(scale_x, scale_y)
            # turn off X autoscaling, since user overrode it
            if self.settings['autoaxis_x'] != 'off':
                self.viewer.onscreen_message("Autoscale X OFF", delay=1.0)
            self.settings['autoaxis_x'] = 'off'

            if self.settings['autopan_x'] == 'on':
                self.autopan_x()
            if self.settings['autoaxis_y'] != 'off':
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
            if self.settings['autoaxis_y'] != 'off':
                self.viewer.onscreen_message("Autoscale Y OFF", delay=1.0)
            self.settings['autoaxis_y'] = 'off'

            self.update_elements()

        return True

    def get_limits(self, lim_type):
        x_vals = []
        y_vals = []
        for key, src in self.plots.items():
            limits = src.get_limits(lim_type)
            x_vals.append(limits.T[0])
            y_vals.append(limits.T[1])
        x_vals = np.array(x_vals).flatten()
        y_vals = np.array(y_vals).flatten()
        if len(x_vals) == 0:
            return np.array([(0.0, 0.0), (0.0, 0.0)])

        return np.array([(x_vals.min(), y_vals.min()),
                         (x_vals.max(), y_vals.max())])

    def setup_standard_frame(self, title='', x_title=None, y_title=None,
                             num_x_labels=4, num_y_labels=4,
                             warn_y=None, alert_y=None):
        from ginga.canvas.types import plots as gplots

        p_bg = gplots.PlotBG(self, linewidth=2, warn_y=warn_y, alert_y=alert_y)
        self.add_plot_etc(p_bg)

        p_x_axis = gplots.XAxis(self, title=x_title, num_labels=num_x_labels)
        self.add_plot_etc(p_x_axis)

        p_y_axis = gplots.YAxis(self, title=y_title, num_labels=num_y_labels)
        self.add_plot_etc(p_y_axis)

        p_title = gplots.PlotTitle(self, title=title)
        self.add_plot_etc(p_title)
