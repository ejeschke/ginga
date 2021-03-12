#
# plots.py -- classes for plots added to Ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

import numpy as np
# NOTE: $ pip install numpy-indexed
import numpy_indexed as npi

from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       register_canvas_types,
                                       colors_plus_none, coord_names)
from ginga.misc import Bunch
from ginga.canvas.types.layer import CompoundObject
#from ginga.canvas.CanvasObject import get_canvas_types

from .basic import Path
from ginga.misc.ParamSet import Param


class XYPlot(CanvasObjectBase):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='linewidth', type=int, default=2,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='black',
                  description="Color of text"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
        ]

    def __init__(self, points, color='black', linewidth=1, linestyle='solid',
                 alpha=1.0, x_acc=None, y_acc=None, **kwdargs):
        super(XYPlot, self).__init__(color=color, linewidth=linewidth,
                                     linestyle=linestyle, alpha=alpha,
                                     **kwdargs)
        self.kind = 'xyplot'
        self.points = points
        if x_acc is None:
            x_acc = np.mean
        nul_arr = np.array([])
        self.x_func = lambda arr: nul_arr if arr.size == 0 else x_acc(arr)
        if y_acc is None:
            y_acc = np.mean
        self.y_func = lambda arr: nul_arr if arr.size == 0 else y_acc(arr)

        self.limits = np.array([(0.0, 0.0), (0.0, 0.0)])

        self.path = Path(points, color=color, linewidth=linewidth,
                         linestyle=linestyle, alpha=alpha, coord='data')

    def plot_xy(self, xpts, ypts):
        self.plot(np.asarray((xpts, ypts)).T)

    def plot(self, points):
        self.points = np.asarray(points)

        self.path.points = self.get_data_points(points=self.points)
        self.path.color = self.color
        self.path.linewidth = self.linewidth
        self.path.linestyle = self.linestyle
        self.path.alpha = self.alpha

        self._calc_limits(points)

    def _calc_limits(self, points):
        if len(points) > 0:
            x_data, y_data = points.T
            self.limits = np.array([(x_data.min(), y_data.min()),
                                    (x_data.max(), y_data.max())])

    def recalc(self, viewer):
        bbox = viewer.get_pan_rect()
        start_x, stop_x = bbox[0][0], bbox[2][0]

        # select only points within range of the current pan/zoom
        points = self.get_data_points(points=self.points)
        if len(points) == 0:
            self.path.points = points
            return
        x, y = points.T

        # if we can determine the visible region shown on the plot
        # limit the points to those within the region
        if np.all(np.isfinite([start_x, stop_x])):
            idx = np.logical_and(x >= start_x, x <= stop_x)
            points = points[idx]
            x, y = points.T

        # now find all points position in canvas X coord
        cpoints = self.path.get_cpoints(viewer, points=points)
        cx, cy = cpoints.T

        # Reduce each group of Y points that map to a unique X via a
        # function that reduces to a single value.  The desirable function
        # will depend on the function of the plot, but mean() would be a
        # reliable default
        #x_uniq, idx = np.unique(cx, return_index=True)
        gr = npi.group_by(cx)
        gr_pts = gr.split(points)
        ## points = np.array([(self.x_func(a.T[0]), self.y_func(a.T[1]))
        ##                    for a in gr_pts])
        #x_data, y_data = points.T
        x_data = np.array([self.x_func(a.T[0]) for a in gr_pts])
        y_data = np.array([self.y_func(a.T[1]) for a in gr_pts])
        assert len(x_data) == len(y_data)

        points = np.array((x_data, y_data)).T
        if len(points) == 0:
            self.path.points = points
            return

        if x_data.size > 0 and y_data.size > 0:
            self._calc_limits(points)

        self.path.points = points

    def draw(self, viewer):
        self.path.crdmap = self.crdmap

        self.recalc(viewer)

        if len(self.path.points) > 0:
            self.path.draw(viewer)


class XAxis(CompoundObject):
    def __init__(self, plot, num_labels=4, font='sans', fontsize=10.0):
        super(XAxis, self).__init__()

        self.num_labels = num_labels
        self.font = font
        self.fontsize = fontsize
        self.txt_ht = None
        self.grid_alpha = 1.0
        self.axis_alpha = 1.0
        self.axis_bg_alpha = 0.8
        self.kind = 'axis_x'

        # add X grid
        self.x_grid = Bunch.Bunch()
        for i in range(self.num_labels):
            self.x_grid[i] = plot.dc.Line(0, 0, 0, 0, color=plot.grid_fg,
                                          linestyle='dash', linewidth=1,
                                          alpha=self.grid_alpha,
                                          coord='window')
            self.objects.append(self.x_grid[i])

        # add X (time) labels
        self.x_axis_bg = plot.dc.Rectangle(0, 0, 100, 100, color=plot.norm_bg,
                                           alpha=self.axis_bg_alpha,
                                           fill=True, fillcolor=plot.axis_bg,
                                           fillalpha=self.axis_bg_alpha,
                                           coord='window')
        self.objects.append(self.x_axis_bg)

        self.x_lbls = Bunch.Bunch()
        for i in range(self.num_labels):
            self.x_lbls[i] = plot.dc.Text(0, 0, text='', color='black',
                                          font=self.font,
                                          fontsize=self.fontsize,
                                          alpha=self.axis_alpha,
                                          coord='window')
            self.objects.append(self.x_lbls[i])

    def format_value(self, v):
        return "%.2f" % v

    def update_elements(self, viewer):
        wd, ht = viewer.get_window_size()
        a = wd // (self.num_labels + 1)

        for i in range(self.num_labels):
            lbl = self.x_lbls[i]
            # calculate evenly spaced interval on Y axis in window coords
            cx, cy = i * a + a, 0
            # get data coord equivalents
            x, y = viewer.get_data_xy(cx, cy)
            # convert to human-understandable time label
            lbl.text = self.format_value(x)

    def update_resize(self, viewer):
        wd, ht = viewer.get_window_size()
        if self.txt_ht is None:
            Text = self.x_lbls[0].__class__
            t = Text(0, 0, text='555.55',
                     fontsize=self.fontsize, font=self.font)
            _, self.txt_ht = viewer.renderer.get_dimensions(t)
        # set X labels/grid as needed
        a = wd // (self.num_labels + 1)

        for i in range(self.num_labels):
            lbl = self.x_lbls[i]
            # calculate evenly spaced interval on Y axis in window coords
            cx, cy = i * a + a, ht - 4
            lbl.x, lbl.y = cx, cy
            # get data coord equivalents
            x, y = viewer.get_data_xy(cx, cy)
            # convert to human-understandable time label
            lbl.text = self.format_value(x)
            grid = self.x_grid[i]
            grid.x1 = grid.x2 = cx
            grid.y1, grid.y2 = 0, ht

        self.x_axis_bg.x1, self.x_axis_bg.x2 = 0, wd
        self.x_axis_bg.y1, self.x_axis_bg.y2 = (ht - self.txt_ht - 4, ht)

    def set_grid_alpha(self, alpha):
        for i in range(self.num_labels):
            grid = self.x_grid[i]
            grid.alpha = alpha

    def set_axis_alpha(self, alpha, bg_alpha=None):
        if bg_alpha is None:
            bg_alpha = alpha
        for i in range(self.num_labels):
            lbl = self.x_lbls[i]
            lbl.alpha = alpha
        self.x_axis_bg.alpha = bg_alpha
        self.x_axis_bg.fillalpha = bg_alpha

    @property
    def height(self):
        return 0 if self.txt_ht is None else self.txt_ht


class YAxis(CompoundObject):
    def __init__(self, plot, num_labels=4, font='sans', fontsize=10.0):
        super(YAxis, self).__init__()

        self.kind = 'axis_y'
        self.num_labels = num_labels
        self.font = font
        self.fontsize = fontsize
        self.txt_wd = None
        self.grid_alpha = 1.0
        self.axis_alpha = 1.0
        self.axis_bg_alpha = 0.8

        # add Y grid
        self.y_grid = Bunch.Bunch()
        for i in range(self.num_labels):
            self.y_grid[i] = plot.dc.Line(0, 0, 0, 0, color=plot.grid_fg,
                                          linestyle='dash', linewidth=1,
                                          alpha=self.grid_alpha,
                                          coord='window')
            self.objects.append(self.y_grid[i])

        # add Y axis
        self.y_axis_bg = plot.dc.Rectangle(0, 0, 100, 100, color=plot.norm_bg,
                                           alpha=self.axis_bg_alpha,
                                           fill=True, fillcolor=plot.axis_bg,
                                           fillalpha=self.axis_bg_alpha,
                                           coord='window')
        self.objects.append(self.y_axis_bg)

        self.y_lbls = Bunch.Bunch()
        for i in range(self.num_labels):
            self.y_lbls[i] = plot.dc.Text(0, 0, text='', color='black',
                                          font=self.font,
                                          fontsize=self.fontsize,
                                          alpha=self.axis_alpha,
                                          coord='window')
            self.objects.append(self.y_lbls[i])

    def format_value(self, v):
        return "%.2f" % v

    def update_elements(self, viewer):
        # set Y labels/grid as needed
        wd, ht = viewer.get_window_size()
        a = ht // (self.num_labels + 1)

        for i in range(self.num_labels):
            lbl = self.y_lbls[i]
            # calculate evenly spaced interval on Y axis in window coords
            cx, cy = 0, i * a + a
            # get data coord equivalents
            t, y = viewer.get_data_xy(cx, cy)
            # now round data Y to nearest int
            ## y = round(y)
            ## # and convert back to canvas coord--that is our line/label cx/cy
            ## _, cy = viewer.get_canvas_xy(0, y)
            #lbl.text = "%.0f%%" % y
            lbl.text = "%.2f" % y

    def update_resize(self, viewer):
        wd, ht = viewer.get_window_size()
        if self.txt_wd is None:
            Text = self.y_lbls[0].__class__
            t = Text(0, 0, text='555.55',
                     fontsize=self.fontsize, font=self.font)
            self.txt_wd, _ = viewer.renderer.get_dimensions(t)
        # set Y labels/grid as needed
        a = ht // (self.num_labels + 1)

        for i in range(self.num_labels):
            lbl = self.y_lbls[i]
            # calculate evenly spaced interval on Y axis in window coords
            cx, cy = wd - self.txt_wd, i * a + a
            # get data coord equivalents
            x, y = viewer.get_data_xy(cx, cy)
            # now round data Y to nearest int
            ## y = round(y)
            ## # and convert back to canvas coord--that is our line/label cx/cy
            ## _, cy = viewer.get_canvas_xy(0, y)
            lbl.x, lbl.y = cx, cy
            #lbl.text = "%.0f%%" % y
            lbl.text = self.format_value(y)
            grid = self.y_grid[i]
            grid.x1, grid.x2 = 0, wd
            grid.y1 = grid.y2 = cy

        self.y_axis_bg.x1, self.y_axis_bg.x2 = wd - self.txt_wd, wd
        self.y_axis_bg.y1, self.y_axis_bg.y2 = 0, ht

    @property
    def width(self):
        return 0 if self.txt_wd is None else self.txt_wd


class PlotBG(CompoundObject):
    def __init__(self, plot, warn_y=None, alert_y=None, linewidth=1):
        super(PlotBG, self).__init__()

        self.y_lbl_info = [warn_y, alert_y]
        self.warn_y = warn_y
        self.alert_y = alert_y

        self.norm_bg = 'white'
        self.warn_bg = 'lightyellow'
        self.alert_bg = 'mistyrose2'
        self.kind = 'plot_bg'

        # add a backdrop that we can change color for visual warnings
        self.bg = plot.dc.Rectangle(0, 0, 100, 100, color=plot.norm_bg,
                                    fill=True, fillcolor=plot.norm_bg,
                                    fillalpha=0.8,
                                    coord='window')
        self.objects.append(self.bg)

        # add warning and alert lines
        if self.warn_y is not None:
            self.ln_warn = plot.dc.Line(0, self.warn_y, 1, self.warn_y,
                                        color='gold3', linewidth=linewidth,
                                        coord='window')
            self.objects.append(self.ln_warn)

        if self.alert_y is not None:
            self.ln_alert = plot.dc.Line(0, self.alert_y, 1, self.alert_y,
                                         color='red', linewidth=linewidth,
                                         coord='window')
            self.objects.append(self.ln_alert)

    def warning(self):
        self.bg.fillcolor = self.warn_bg

    def alert(self):
        self.bg.fillcolor = self.alert_bg

    def normal(self):
        self.bg.fillcolor = self.norm_bg

    def update_elements(self, viewer):
        # adjust warning/alert lines
        if self.warn_y is not None:
            x, y = viewer.get_canvas_xy(0, self.warn_y)
            self.ln_warn.y1 = self.ln_warn.y2 = y

        if self.alert_y is not None:
            x, y = viewer.get_canvas_xy(0, self.alert_y)
            self.ln_alert.y1 = self.ln_alert.y2 = y

    def update_resize(self, viewer):
        # adjust bg to window size, in case it changed
        wd, ht = viewer.get_window_size()
        self.bg.x2, self.bg.y2 = wd, ht

        # adjust warning/alert lines
        if self.warn_y is not None:
            x, y = viewer.get_canvas_xy(0, self.warn_y)
            self.ln_warn.x1, self.ln_warn.x2 = 0, wd
            self.ln_warn.y1 = self.ln_warn.y2 = y

        if self.alert_y is not None:
            x, y = viewer.get_canvas_xy(0, self.alert_y)
            self.ln_alert.x1, self.ln_alert.x2 = 0, wd
            self.ln_alert.y1 = self.ln_alert.y2 = y


class PlotTitle(CompoundObject):
    def __init__(self, plot, title='', font='sans', fontsize=12.0):
        super(PlotTitle, self).__init__()

        self.plot = plot
        self.font = font
        self.fontsize = fontsize
        self.title = title
        self.txt_ht = None
        self.title_alpha = 1.0
        self.title_bg_alpha = 0.8
        self.kind = 'plot_title'

        # add X (time) labels
        self.title_bg = plot.dc.Rectangle(0, 0, 100, 100, color=plot.norm_bg,
                                          alpha=self.title_bg_alpha,
                                          fill=True, fillcolor=plot.axis_bg,
                                          fillalpha=self.title_bg_alpha,
                                          coord='window')
        self.objects.append(self.title_bg)

        self.lbls = Bunch.Bunch()
        self.lbls[0] = plot.dc.Text(0, 0, text=title, color='black',
                                    font=self.font,
                                    fontsize=self.fontsize,
                                    alpha=self.title_alpha,
                                    coord='window')
        self.objects.append(self.lbls[0])

    def update_elements(self, viewer):
        pass

    def update_resize(self, viewer):
        if self.txt_ht is None:
            _, self.txt_ht = viewer.renderer.get_dimensions(self.lbls[0])
            #self.title.x, self.title.y = 20, 10 + self.txt_ht

        nplots = len(list(self.plot.plots.keys())) + 1
        wd, ht = viewer.get_window_size()

        # set X labels/grid as needed
        a = wd // (nplots + 1)

        cx, cy = 4, self.txt_ht
        lbl = self.lbls[0]
        lbl.x, lbl.y = cx, cy

        for i, plot_src in enumerate(self.plot.plots.values()):
            j = i + 1
            cx, cy = j * a + 4, self.txt_ht
            if j in self.lbls:
                lbl = self.lbls[j]
                lbl.x, lbl.y = cx, cy
            else:
                text = plot_src.name
                color = plot_src.color
                Text = self.lbls[0].__class__
                lbl = Text(cx, cy, text=text, color=color,
                           font=self.font,
                           fontsize=self.fontsize,
                           alpha=self.title_alpha,
                           coord='window')
                self.lbls[j] = lbl
                self.objects.append(lbl)
                lbl.crdmap = self.lbls[0].crdmap

        self.title_bg.x1, self.title_bg.x2 = 0, wd
        self.title_bg.y1, self.title_bg.y2 = (0, self.txt_ht + 4)

    @property
    def height(self):
        return 0 if self.txt_ht is None else self.txt_ht


class PlotSource(CompoundObject):
    """A Ginga canvas object which can contain several segments of a plot,
    segments separated by outages of the source.
    """
    def __init__(self, name, color, data_src):
        super(PlotSource, self).__init__()
        self.name = name
        self.color = color
        self.linewidth = 2.0
        self.data_src = data_src

    def plot(self):
        arr_l = self.data_src.get_arrays()
        self.objects = []
        for points in arr_l:
            plot = XYPlot(points, color=self.color, linewidth=self.linewidth,
                          y_acc=np.nanmax)
            plot.crdmap = self.crdmap
            self.objects.append(plot)
            plot.plot(points)

    def get_data_limits(self):
        return self.data_src.get_limits()

    def get_data_x_limits(self):
        return self.get_data_limits().T[0]

    def get_plot_limits(self):
        """Find the aggregate limits of all the separate paths
        that we hold.
        """
        x_vals = []
        y_vals = []
        for plot in self.objects:
            x_vals.append(plot.limits.T[0])
            y_vals.append(plot.limits.T[1])
        x_vals = np.array(x_vals).flatten()
        y_vals = np.array(y_vals).flatten()
        return np.array([(x_vals.min(), y_vals.min()),
                         (x_vals.max(), y_vals.max())])


class DataSource:
    """A data source that can contain sequences of data for a particular
    source, separated by periods of not receiving data.
    """

    def __init__(self, points=[], name=None):
        self.name = name

        self.limits = np.array([[0.0, 0.0], [0.0, 0.0]])

        self.set_points(points)

    def get_limits(self):
        return np.copy(self.limits)

    def update_limits(self):
        if len(self.points) == 0:
            self.limits = np.array([[0.0, 0.0], [0.0, 0.0]])
        else:
            x_vals, y_vals = self.points.T
            self.limits = np.array([(x_vals.min(), y_vals.min()),
                                    (x_vals.max(), y_vals.max())])

    def set_points(self, points):
        self.points = np.array(points)
        self.update_limits()

    def get_arrays(self):
        return [self.points]


class CalcPlot(XYPlot):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='linewidth', type=int, default=1,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='black',
                  description="Color of text"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
        ]

    def __init__(self, points, color='black', linewidth=1, linestyle='solid',
                 alpha=1.0, **kwdargs):
        super(CalcPlot, self).__init__(points, color=color, linewidth=linewidth,
                                       linestyle=linestyle, alpha=alpha,
                                       **kwdargs)
        self.kind = 'calcplot'

    def calc_points(self, xpts):
        ypts = np.sin(xpts)
        return np.array((xpts, ypts)).T

    def draw(self, viewer):
        bbox = viewer.get_pan_rect()
        wd, ht = viewer.get_window_size()
        start_x, stop_x = bbox[0][0], bbox[2][0]
        incr_x = abs(stop_x - start_x) / wd
        xrng = np.arange(start_x, stop_x, incr_x)
        self.plot(self.calc_points(xrng))

        super(CalcPlot, self).draw(viewer)

# register our types
register_canvas_types(dict(xyplot=XYPlot, calcplot=CalcPlot))
