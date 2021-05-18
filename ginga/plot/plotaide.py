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
    PlotAide is a class to use a Ginga viewer as a speedy, interactive
    X/Y line plot viewer.
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
        # bbox for the plot area (a subset of the ginga viewer window)
        # is (LL, LR, UR, UL) in typical window coordinates. This will
        # be adjusted later in the resize callbacks
        self.bbox = np.array([(0, 0), (0, 0), (0, 0), (0, 0)])
        self.llur = (0, 0, 0, 0)

        if settings is None:
            settings = Settings.SettingGroup(name='plotaide',
                                             logger=self.logger)
        self.settings = settings
        self.settings.set_defaults(autoaxis_x='on', autoaxis_y='on')

        # internal flags used for synchronization
        self._panning_x = False
        self._scaling_y = False
        self._scaling_x = False
        self._adjusting = False

        self.viewer = viewer
        # configure the ginga viewer for a plot
        vi = viewer
        vi.set_background(self.norm_bg)

        # turn off sanity check on scaling, since scaling can get
        # wild with plots
        t_ = vi.get_settings()
        t_.set(sanity_check_scale=False)

        # add special plot transform, used for the plot area
        self.plot_tr = transform.ScaleOffsetTransform()
        self.plot_tr.set_plot_scaling(1.0, 1.0, 0, 0)
        vi.tform['data_to_plot'] = (vi.tform['data_to_native'] + self.plot_tr)

        vi.enable_autozoom('off')
        vi.ui_set_active(True)
        vi.set_enter_focus(True)
        vi.add_callback('configure', lambda *args: self.adjust_resize_cb())
        vi.add_callback('transform', lambda *args: self.adjust_resize_cb())

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
        bm.map_event('plot', [], 'kp_v', 'plot-visible-y')
        vi.set_callback('keydown-plot-visible-y', self._v_press_cb)
        bm.map_event('plot', [], 'kp_x', 'plot-autoaxis-x')
        vi.set_callback('keydown-plot-autoaxis-x', self._x_press_cb)
        bm.map_event('plot', [], 'kp_p', 'plot-position-x')
        vi.set_callback('keydown-plot-position-x', self._p_press_cb)

        for name in ['plot-zoom-x', 'plot-zoom-y', 'pan']:
            self.enable_callback(name)
        self.add_callback('plot-zoom-x', self.plot_zoom_x_cb)
        self.add_callback('plot-zoom-y', self.plot_zoom_y_cb)
        self.add_callback('pan', self.pan_cb)

        self.settings.get_setting('autoaxis_x').add_callback('set',
                                                             self._autoaxis_x_cb)
        self.settings.get_setting('autoaxis_y').add_callback('set',
                                                             self._autoaxis_y_cb)

        settings = vi.get_settings()
        settings.get_setting('pan').add_callback('set', self._pan_cb)

        # get our canvas
        canvas = vi.get_canvas()
        self.dc = canvas.get_draw_classes()
        self.canvas = self.dc.DrawingCanvas()
        canvas.add(self.canvas)
        self.canvas.register_for_cursor_drawing(vi)
        self.canvas.set_draw_mode('pick')
        self.canvas.ui_set_active(True, viewer=vi)

        # holds our individual XY plots
        self.plots = Bunch.Bunch()
        # holds other plot elements like PlotBG, XAxis, YAxis, PlotTitle, etc.
        self.plot_decor_l = []
        self.plot_decor_d = {}
        self.titles = [None, None]

    def get_settings(self):
        return self.settings

    def add_plot_decor(self, plotable):
        """Add a "plot accessory" (``PlotBG``, ``PlotTitle``, ``XAxis``, etc)

        Parameters
        ----------
        plotable : `~ginga.canvas.types.plots.CompoundObject` instance
            A plot accessory like a PlotBG, PlotTitle, XAxis, YAxis, etc.
        """
        plotable.register_decor(self)
        self.plot_decor_d[plotable.kind] = plotable
        self.plot_decor_l.append(plotable)
        self.canvas.add(plotable)

        # set callbacks for tool tips
        if plotable.kind == 'plot_bg':
            plotable.set_callback('pick-down', self.show_tt_cb, 'down')
            plotable.set_callback('pick-move', self.show_tt_cb, 'move')
            plotable.set_callback('pick-up', self.show_tt_cb, 'up')

    def get_plot_decor(self, kind):
        """Get a "plot accessory"

        Parameters
        ----------
        kind : str
            One of ('axis_x', 'axis_y', 'plot_bg', 'plot_title')

        Returns
        -------
        plotable : `~ginga.canvas.types.layer.CompoundObject` instance
            The plot accessory
        """
        return self.plot_decor_d[kind]

    def add_plot(self, plot):
        """Add a XY plot

        Parameters
        ----------
        plot : `~ginga.canvas.types.plots.XYPlot` instance
            A plot to add to the viewer
        """
        name = plot.name
        self.plots[name] = plot

        self.canvas.add(plot, tag=name)
        plot_bg = self.plot_decor_d.get('plot_bg', None)
        self.canvas.raise_object(plot, aboveThis=plot_bg)

        for plotable in self.plot_decor_l:
            plotable.add_plot(self.viewer, plot)

        limits = self.get_limits('data')
        x1, y1 = limits[0][:2]
        x2, y2 = limits[1][:2]

        self.viewer.set_limits(limits)
        self.viewer.set_pan((x1 + x2) * 0.5, (y1 + y2) * 0.5)

        self.update_plots()

    def delete_plot(self, plot):
        """Delete a XY plot

        Parameters
        ----------
        plot : `~ginga.canvas.types.plots.XYPlot` instance
            The plot to delete from the viewer
        """
        name = plot.name
        del self.plots[name]

        self.canvas.delete_object_by_tag(name)

        for plotable in self.plot_decor_l:
            plotable.delete_plot(self.viewer, plot)

        self.update_plots()

    def get_plot(self, name):
        """Get a XY plot

        Raises a `KeyError` if the requested plot is not present.

        Parameters
        ----------
        name : `str`
            The name of the plot

        Returns
        -------
        plot : `~ginga.canvas.types.plots.XYPlot` instance
            The requested plot
        """
        return self.plots[name]

    def update_plots(self):
        """Update the plots visibly after some activity, like plotting
        new data, or changing the data of a plot.
        """
        st = time.time()

        self.adjust_view()

        et = time.time()
        self.logger.debug("%.5f sec to update plot" % (et - st))

    def update_elements(self):
        """Mostly internal routine used to update the plot accessories
        after changes in region shown or data updates.
        """
        with self.viewer.suppress_redraw:
            for plotable in self.plot_decor_l:
                plotable.update_elements(self.viewer)

            self.viewer.redraw(whence=3)

    def update_resize(self):
        """Mostly internal routine called after the viewer's window size
        has changed.
        """
        # upon a resize, at first we redefine the plot bbox to encompass
        # the entire viewer area
        dims = self.viewer.get_window_size()
        wd, ht = dims[:2]
        # bbox is (LL, LR, UR, UL) in typical window coordinates
        self.bbox = np.array([(0, ht), (wd, ht), (wd, 0), (0, 0)])

        with self.viewer.suppress_redraw:
            # update all non-plot elements: axes, title, bg, etc
            # after this the plot bbox will have been redefined
            for plotable in self.plot_decor_l:
                plotable.update_bbox(self.viewer, dims)

            # update the plot transform based on the new plot bbox
            xy_lim = self.recalc_transform(dims)

            # second pass to allow non-plot elements to position their
            # components now that plox bbox is known
            for plotable in self.plot_decor_l:
                plotable.update_resize(self.viewer, dims, xy_lim)

            # now update all plots, due to the new transform
            for plot_src in self.plots.values():
                plot_src.update_resize(self.viewer, dims)

            # finally, redraw everything
            self.viewer.redraw(whence=3)

    def update_plot_bbox(self, x_lo=None, x_hi=None, y_lo=None, y_hi=None):
        """Mostly internal routine called by plot accessories to iteratively
        define the bounding box of the plot within the viewer plane.
        """
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
        """Mostly internal routine used to redefine the special transform
        that maps the data to the plot area.
        """
        x_lo, x_hi = self.bbox.T[0].min(), self.bbox.T[0].max()
        y_lo, y_hi = self.bbox.T[1].min(), self.bbox.T[1].max()

        wd, ht = dims[:2]

        x_pct = (x_hi - x_lo) / wd
        y_pct = (y_hi - y_lo) / ht

        self.plot_tr.set_plot_scaling(x_pct, y_pct, x_lo, y_lo)
        self.llur = (x_lo, y_lo, x_hi, y_hi)

        return self.llur

    def set_limits(self, limits):
        self.viewer.set_limits(limits)

    def get_limits(self, lim_type):
        """Return the limits of this plot.

        Parameters
        ----------
        lim_type : str
            'data' or 'plot'

        Returns
        -------
        limits : array of [(x_min, y_min), (x_max, y_max)]
            Limits of full data or visible part of plot, depending on `lim_type`

        """
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
        """A convenience function for setting up a typical plot.

        This includes a plot background, a title bar with keys, and X and Y
        axes.
        """
        from ginga.canvas.types import plots as gplots

        self.titles = [x_title, y_title]

        p_bg = gplots.PlotBG(linewidth=2, warn_y=warn_y, alert_y=alert_y)
        self.add_plot_decor(p_bg)

        p_title = gplots.PlotTitle(title=title)
        self.add_plot_decor(p_title)

        p_x_axis = gplots.XAxis(title=x_title, num_labels=num_x_labels)
        self.add_plot_decor(p_x_axis)

        p_y_axis = gplots.YAxis(title=y_title, num_labels=num_y_labels)
        self.add_plot_decor(p_y_axis)

    def get_axes_titles(self):
        """A function used by Axis subclasses to find their title.
        (title can shift depending on whether the viewer has swapped axes)
        """
        x, y = 0, 1
        flip = self.viewer.get_transforms()
        if flip[2]:
            x, y = y, x
        return dict(axis_x=self.titles[x], axis_y=self.titles[y])

    def configure_scrollbars(self, sw):
        """If a scroll widget is used with this plot viewer, then the
        widget can be passed to this method to configure the scrollbars
        to turn on and off as necessary depending on auto axis adjustments.
        """
        self.settings.get_setting('autoaxis_x').add_callback('set',
                                                             self.update_horz_scrollbar_cb, sw)
        self.settings.get_setting('autoaxis_y').add_callback('set',
                                                             self.update_vert_scrollbar_cb, sw)

        if self.settings['autoaxis_x'] in ('on', 'pan'):
            horz = 'off'
        else:
            horz = 'on'
        vert = 'off' if self.settings['autoaxis_y'] == 'on' else 'off'
        sw.scroll_bars(horizontal=horz, vertical=vert)

    def adjust_view(self):
        """Called after a pan, zoom or change of data, in order to
        autoscale X or Y axes, autopan the X axis and update the non-plot
        accessories (axes tick labels, etc).
        """
        if self._adjusting:
            return
        self._adjusting = True
        try:
            limits = self.get_limits('data')

            with self.viewer.suppress_redraw:
                # set limits to combined data limits of all plots in this
                # viewer
                self.viewer.set_limits(limits)

                # X limits may be adjusted by autoscaling X axis or
                # autopanning to most recent data
                if not self._scaling_x and self.settings['autoaxis_x'] == 'on':
                    self.zoom_fit_x()
                else:
                    if not self._panning_x and self.settings['autoaxis_x'] == 'pan':
                        self.autopan_x()

                # recalculate plots based on new X limits
                rect = self.viewer.get_pan_rect()
                x_lo, x_hi = rect[0][0], rect[2][0]

                for plot_src in self.plots.values():
                    plot_src.calc_points(self.viewer, x_lo, x_hi)

                # Y limits may be adjusted by autoscaling Y axis
                if not self._scaling_y and self.settings['autoaxis_y'] != 'off':
                    self.zoom_fit_y()

                # finally, update plot elements to match adjustments
                self.update_elements()

        finally:
            self._adjusting = False

    def zoom_limit_y(self, y_lo, y_hi):
        """Scale the plot in the Y direction so that `y_lo` and `y_hi`
        are both visible.

        Parameters
        ----------
        y_lo : `float` or `int`
            Low point of Y plot to show

        y_hi : `float` or `int`
            High point of Y plot to show
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

    def zoom_fit_y(self):
        """Scale the plot in the Y axis so that the plot takes up as
        much room vertically as shown in the visible area.
        """
        # establish range of current Y plot
        mode = self.settings['autoaxis_y']
        if mode == 'on':
            limits = self.get_limits('data')
        else:
            limits = self.get_limits('plot')

        y_lo, y_hi = limits[0][1], limits[1][1]
        self.zoom_limit_y(y_lo, y_hi)

    def zoom_fit_y_full(self):
        """Scale the plot in the Y axis so that the plot takes up as
        much room vertically as there is in the range of Y data.
        """
        # establish full range of Y
        limits = self.get_limits('data')
        y_lo, y_hi = limits[0][1], limits[1][1]

        self.zoom_limit_y(y_lo, y_hi)

    def zoom_limit_x(self, x_lo, x_hi):
        """Scale the plot in the X direction so that `x_lo` and `x_hi`
        are both visible.

        Parameters
        ----------
        x_lo : `float` or `int`
            Low point of X plot to show

        x_hi : `float` or `int`
            High point of X plot to show
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

    def zoom_fit_x(self):
        """Scale the plot in the X axis so that the plot takes up as
        much room horizontally as there is in the range of X data.
        """
        # establish full range of X
        limits = self.get_limits('data')
        x_lo, x_hi = limits[0][0], limits[1][0]

        self.zoom_limit_x(x_lo, x_hi)

    def autopan_x(self):
        """Pan the plot so that the most recent data is visible at
        the right side of the plot. i.e. "keep up with the plot"
        """
        self._panning_x = True
        try:
            wd, ht = self.viewer.get_window_size()

            pl = self.get_limits('data')
            x_lo, x_hi = pl[0][0], pl[1][0]
            pan_x, pan_y = self.viewer.get_pan()[:2]
            _, cy = self.viewer.get_canvas_xy(pan_x, pan_y)
            cx = wd

            self.viewer.position_at_canvas_xy((x_hi, pan_y), (cx, cy))

        finally:
            self._panning_x = False

    def _autoaxis_x_cb(self, setting, autoaxis_x):
        """Called when the user toggles the 'autoaxis X' feature on or off.
        """
        if autoaxis_x == 'on':
            msg = "Autoaxis X ON"
        elif autoaxis_x == 'pan':
            msg = "Autoaxis X PAN"
        else:
            msg = "Autoaxis X OFF"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def _autoaxis_y_cb(self, setting, autoaxis_y):
        """Called when the user toggles the 'autoaxis Y' feature on or off.
        """
        if autoaxis_y == 'on':
            msg = "Autoaxis Y ON"
        elif autoaxis_y == 'vis':
            msg = "Autoaxis Y VIS"
        else:
            msg = "Autoaxis Y OFF"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def _autopan_x_cb(self, setting, autopan_x):
        """Called when the user toggles the 'autopan X' feature on or off.
        """
        msg = "Autoaxis X PAN" if autopan_x == 'pan' else "Autoaxis X OFF"
        self.viewer.onscreen_message(msg, delay=1.0)
        self.adjust_view()

    def adjust_resize_cb(self):
        """Callback that is called when the viewer window is resized."""
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

    def scroll_cb(self, viewer, event):
        """Callback called when the user scrolls in the viewer window.
        From this we generate a 'plot-zoom-x' or a 'plot-zoom-y' event.
        """
        direction = self.bd.get_direction(event.direction)
        zoom_direction = 'in' if direction == 'up' else 'out'
        # default is to zoom the X axis unless CTRL is held down
        zoom_axis = 'y' if 'ctrl' in event.modifiers else 'x'
        event = 'plot-zoom-{}'.format(zoom_axis)
        # turn this into a zoom event for any callbacks registered for it
        self.make_callback(event, zoom_direction)
        return True

    def scroll_by_pan_cb(self, viewer, event):
        """Callback called when the user pans in the viewer window
        (i.e. touchpad pan event); we turn this into a zoom event.
        """
        bd = self.viewer.get_bindings()
        event = bd._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False
        self.scroll_cb(viewer, event)
        return True

    def plot_zoom_x_cb(self, plot, direction):
        """Default callback called when the user zooms the plot in X."""
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
            if self.settings['autoaxis_x'] == 'on':
                self.settings['autoaxis_x'] = 'off'

            self.adjust_view()

        return True

    def plot_zoom_y_cb(self, plot, direction):
        """Default callback called when the user zooms the plot in Y."""
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
                self.settings['autoaxis_y'] = 'off'

            self.adjust_view()

        return True

    def _y_press_cb(self, *args):
        """Callback invoked when the user presses 'y' in the viewer window.
        """
        autoaxis_y = self.settings['autoaxis_y'] == 'on'
        self.settings['autoaxis_y'] = 'off' if autoaxis_y else 'on'

    def _v_press_cb(self, *args):
        """Callback invoked when the user presses 'v' in the viewer window.
        """
        autoaxis_y = self.settings['autoaxis_y'] == 'vis'
        self.settings['autoaxis_y'] = 'off' if autoaxis_y else 'vis'

    def _x_press_cb(self, *args):
        """Callback invoked when the user presses 'x' in the viewer window.
        """
        autoaxis_x = self.settings['autoaxis_x'] == 'on'
        self.settings['autoaxis_x'] = 'off' if autoaxis_x else 'on'

    def _p_press_cb(self, *args):
        """Callback invoked when the user presses 'p' in the viewer window.
        """
        autopan_x = self.settings['autoaxis_x'] == 'pan'
        self.settings['autoaxis_x'] = 'off' if autopan_x else 'pan'

    def _pan_cb(self, settings, pan_pos):
        """Callback invoked by the viewer when a pan happens pans in our
        particular plot viewer. We use this to adjust the view if the pan is
        not a byproduct of an internal adjustment.
        """
        # check to avoid circular callback situation
        if not (self._panning_x or self._scaling_x or self._scaling_y or
                self._adjusting):
            self.adjust_view()

    def update_horz_scrollbar_cb(self, setting, autoaxis_x, sw):
        h = 'off' if autoaxis_x != 'off' else 'on'
        d = sw.get_scroll_bars_status()
        v = d['vertical']
        sw.scroll_bars(horizontal=h, vertical=v)

    def update_vert_scrollbar_cb(self, setting, autoaxis_y, sw):
        d = sw.get_scroll_bars_status()
        h = d['horizontal']
        v = 'off' if autoaxis_y != 'off' else 'on'
        sw.scroll_bars(horizontal=h, vertical=v)

    def make_tt(self, canvas, lines, pt, fontsize=10):
        # create the canvas object representing the tooltip
        # a Rectangle with some Text objects inside
        rect = canvas.dc.Rectangle(0, 0, 0, 0, color='black', fill=True,
                                   fillcolor='lightyellow', coord='window')

        l = [rect]
        for line in lines:
            text = canvas.dc.Text(0, 0, text=line, color='black',
                                  font='sans condensed', fontsize=fontsize,
                                  coord='window')
            l.append(text)

        tt_obj = canvas.dc.CompoundObject(*l)
        return tt_obj

    def update_tt(self, tt_obj, lines, pt, fontsize=10):
        # Determine pop-up position on canvas, offset a little from cursor.
        x, y = pt[:2]
        x, y = x + 15, y + 10
        mxwd = 0

        # quick check to make sure TT doesn't go out of plot area in Y
        text = tt_obj.objects[1]
        text.text = lines[0]
        txt_wd, txt_ht = self.viewer.renderer.get_dimensions(text)
        y_end = y + len(lines) * (txt_ht + 1)
        y_diff = y_end - self.llur[3]
        if y_diff > 0:
            y -= y_diff

        # assign background rect coords
        rect = tt_obj.objects[0]
        rect.x1, rect.y1 = x, y

        # assign text coords
        a, b = x + 2, y
        for i, text in enumerate(tt_obj.objects[1:]):
            text.x = a
            text.text = lines[i]
            txt_wd, txt_ht = self.viewer.renderer.get_dimensions(text)
            b += txt_ht + 1
            text.y = b
            mxwd = max(mxwd, txt_wd)
        rect.x2 = x + mxwd + 4
        rect.y2 = b + 4

    def show_tt_cb(self, plot_bg, canvas, event, pt, state, fontsize=10):
        """Internal callback routine to pop up a tooltip-like reading of
        X/Y values at the cursor.
        """
        # determine plot coordinates of cursor
        # double conversion needed because plot transform is different
        # from default data transform
        win_pt = self.viewer.tform['data_to_window'].to_(pt)
        plot_x, plot_y = self.viewer.tform['data_to_plot'].from_(win_pt)

        # format these values according to the axes formatters
        x_axis = self.get_plot_decor('axis_x')
        x_text = x_axis.format_value(plot_x)
        y_axis = self.get_plot_decor('axis_y')
        y_text = y_axis.format_value(plot_y)
        text = "X: {0:}\nY: {1:}".format(x_text, y_text)
        lines = text.split('\n')

        tag = '_$tooltip'
        if state == 'down':
            # pressed down, create and pop up tooltip with X/Y value
            # at point
            try:
                canvas.delete_object_by_tag(tag, redraw=False)
            except KeyError:
                pass
            tt = self.make_tt(canvas, lines, win_pt)
            canvas.add(tt, tag=tag, redraw=False)
            self.update_tt(tt, lines, win_pt, fontsize=fontsize)

        elif state == 'move':
            # cursor moved while pressed down; update the tooltip value
            tt = canvas.get_object_by_tag(tag)
            self.update_tt(tt, lines, win_pt)

        else:
            # up, or anything else, remove the tooltip
            try:
                canvas.delete_object_by_tag(tag, redraw=False)
            except KeyError:
                pass

        canvas.update_canvas()
        return True
