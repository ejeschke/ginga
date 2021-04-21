#
# plots.py -- classes for plots added to Ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import numpy as np
have_npi = False
try:
    # NOTE: $ pip install numpy-indexed
    import numpy_indexed as npi
    have_npi = True

except ImportError:
    pass

from ginga.canvas.CanvasObject import (CanvasObjectBase, _color,
                                       register_canvas_types,
                                       colors_plus_none)
from ginga.misc import Bunch
from ginga.canvas.types.layer import CompoundObject

from .basic import Path
from ginga.misc.ParamSet import Param


class XYPlot(CanvasObjectBase):
    """
    Plotable object that defines a single path representing an X/Y line plot.

    Like a Path, but has some optimization to reduce the actual numbers of
    points in the path, depending on the scale and pan of the viewer.
    """

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

    def __init__(self, name=None, color='black',
                 linewidth=1, linestyle='solid',
                 alpha=1.0, x_acc=None, y_acc=None, **kwargs):
        super(XYPlot, self).__init__(color=color, linewidth=linewidth,
                                     linestyle=linestyle, alpha=alpha,
                                     **kwargs)
        self.name = name
        self.kind = 'xyplot'
        self.x_func = None
        nul_arr = np.array([])
        if x_acc is not None:
            self.x_func = lambda arr: nul_arr if arr.size == 0 else x_acc(arr)
        if y_acc is None:
            y_acc = np.mean
        self.y_func = lambda arr: nul_arr if arr.size == 0 else y_acc(arr)

        self.points = np.copy(nul_arr)
        self.limits = np.array([(0.0, 0.0), (0.0, 0.0)])
        self.plot_xlim = (None, None)

        self.path = Path([], color=color, linewidth=linewidth,
                         linestyle=linestyle, alpha=alpha, coord='data')
        self.path.get_cpoints = self.get_cpoints

    def plot_xy(self, xpts, ypts):
        """Convenience function for plotting X and Y points that are in
        separate arrays.
        """
        self.plot(np.asarray((xpts, ypts)).T)

    def plot(self, points, limits=None):
        """Plot `points`, a list, tuple or array of (x, y) points.

        Parameter
        ---------
        points : array-like
            list, tuple or array of (x, y) points

        limits : array-like, optional
            array of (xmin, ymin), (xmax, ymax)

        Limits will be calculated if not passed in.
        """
        self.points = np.asarray(points)
        self.plot_xlim = (None, None)

        # path starts out by default with the full set of data points
        # corresponding to the plotted X/Y data
        #self.path.points = self.get_data_points(points=self.points)

        # set or calculate limits
        if limits is not None:
            # passing limits saves costly min/max calculation
            self.limits = np.asarray(limits)
        else:
            self._calc_limits(self.points)

    def _calc_limits(self, points):
        """Internal routine to calculate the limits of `points`.
        """
        # TODO: what should limits be if there are no points?
        if len(points) == 0:
            self.limits = np.array([[0.0, 0.0], [0.0, 0.0]])
        else:
            x_vals, y_vals = points.T
            self.limits = np.array([(x_vals.min(), y_vals.min()),
                                    (x_vals.max(), y_vals.max())])

    def calc_points(self, viewer, start_x, stop_x):
        """Called when recalculating our path's points.
        """
        # in case X axis is flipped
        start_x, stop_x = min(start_x, stop_x), max(start_x, stop_x)

        new_xlim = (start_x, stop_x)
        if new_xlim == self.plot_xlim:
            # X limits are the same, no need to recalculate points
            return

        self.plot_xlim = new_xlim

        points = self.get_data_points(points=self.points)
        if len(points) == 0:
            self.path.points = points
            return

        x_data, y_data = points.T

        # if we can determine the visible region shown on the plot
        # limit the points to those within the region
        if np.all(np.isfinite([start_x, stop_x])):
            idx = np.logical_and(x_data >= start_x, x_data <= stop_x)
            points = points[idx]

        if have_npi and self.x_func is not None:
            # now find all points position in canvas X coord
            cpoints = self.get_cpoints(viewer, points=points)
            cx, cy = cpoints.T

            # Reduce each group of Y points that map to a unique X via a
            # function that reduces to a single value.  The desirable function
            # will depend on the function of the plot, but mean() would be a
            # sensible default
            gr = npi.group_by(cx)
            gr_pts = gr.split(points)
            x_data = np.array([self.x_func(a.T[0]) for a in gr_pts])
            y_data = np.array([self.y_func(a.T[1]) for a in gr_pts])
            assert len(x_data) == len(y_data)

            points = np.array((x_data, y_data)).T

        self.path.points = points

    def recalc(self, viewer):
        """Called when recalculating our path's points.
        """
        # select only points within range of the current pan/zoom
        bbox = viewer.get_pan_rect()
        if bbox is None:
            self.path.points = []
            return

        start_x, stop_x = bbox[0][0], bbox[2][0]

        self.calc_points(viewer, start_x, stop_x)

    def get_cpoints(self, viewer, points=None, no_rotate=False):
        """Mostly internal routine used to calculate the native positions
        to draw the plot.
        """
        # If points are passed, they are assumed to be in data space
        if points is None:
            points = self.path.get_points()

        return viewer.tform['data_to_plot'].to_(points)

    def update_resize(self, viewer, dims):
        """Called when the viewer is resized."""
        self.recalc(viewer)

    def update_elements(self, viewer):
        """This method is called if the plot is set with new points,
        or is scaled or panned with existing points.
        """
        #self.recalc(viewer)
        pass

    def get_latest(self):
        """Get the latest (last) point on the plot.  Returns None if there
        are no points.
        """
        if len(self.points) == 0:
            return None
        return self.points[-1]

    def get_limits(self, lim_type):
        """Get the limits of the data or the visible part of the plot.

        If `lim_type` == 'data' returns the limits of all the data points.
        Otherwise returns the limits of the visibly plotted area.  Limits
        are returned in the form ((xmin, ymin), (xmax, ymax)), as an array.
        """
        if lim_type == 'data':
            # data limits
            return np.asarray(self.limits)

        # plot limits
        self.path.crdmap = self.crdmap
        if len(self.path.points) > 0:
            llur = self.path.get_llur()
            llur = [llur[0:2], llur[2:4]]
        else:
            llur = [(0.0, 0.0), (0.0, 0.0)]
        return np.asarray(llur)

    def draw(self, viewer):
        """Draw the plot.  Normally not called by the user, but by the viewer
        as needed.
        """
        self.path.crdmap = self.crdmap

        self.recalc(viewer)

        if len(self.path.points) > 0:
            self.path.draw(viewer)


class XAxis(CompoundObject):
    """
    Plotable object that defines X axis labels and grid lines.
    """
    def __init__(self, aide, title=None, num_labels=4, font='sans',
                 fontsize=10.0):
        super(XAxis, self).__init__()

        self.aide = aide
        self.num_labels = num_labels
        self.title = title
        self.kind = 'axis_x'
        self.font = font
        self.fontsize = fontsize
        self.txt_ht = 0
        self.title_wd = 0
        self.grid_alpha = 1.0
        self.format_value = self._format_value
        self.pad_px = 5

        # add X grid
        self.x_grid = Bunch.Bunch()
        for i in range(self.num_labels):
            self.x_grid[i] = aide.dc.Line(0, 0, 0, 0, color=aide.grid_fg,
                                          linestyle='dash', linewidth=1,
                                          alpha=self.grid_alpha,
                                          coord='window')
            self.objects.append(self.x_grid[i])

        self.x_axis_bg = aide.dc.Rectangle(0, 0, 100, 100, color=aide.norm_bg,
                                           fill=True, fillcolor=aide.axis_bg,
                                           coord='window')
        self.objects.append(self.x_axis_bg)

        self.x_lbls = Bunch.Bunch()
        for i in range(self.num_labels):
            self.x_lbls[i] = aide.dc.Text(0, 0, text='', color='black',
                                          font=self.font,
                                          fontsize=self.fontsize,
                                          coord='window')
            self.objects.append(self.x_lbls[i])

        if self.title is not None:
            self.x_title = aide.dc.Text(0, 0, text=self.title, color='black',
                                        font=self.font, fontsize=self.fontsize,
                                        coord='window')
            self.objects.append(self.x_title)

    def _format_value(self, v):
        """Default formatter for XAxis labels.
        """
        return "%.4g" % v

    def update_elements(self, viewer):
        """This method is called if the plot is set with new points,
        or is scaled or panned with existing points.

        Update the XAxis labels to reflect the new values and/or pan/scale.
        """
        for i in range(self.num_labels):
            lbl = self.x_lbls[i]
            # get data coord equivalents
            x, y = self.get_data_xy(viewer, (lbl.x, lbl.y))
            # format according to user's preference
            lbl.text = self.format_value(x)

    def update_bbox(self, viewer, dims):
        """This method is called if the viewer's window is resized.

        Update all the XAxis elements to reflect the new dimensions.
        """
        wd, ht = dims[:2]
        if self.txt_ht == 0:
            Text = self.x_lbls[0].__class__
            t = Text(0, 0, text=self.title if self.title is not None else '555.55',
                     fontsize=self.fontsize, font=self.font)
            self.title_wd, self.txt_ht = viewer.renderer.get_dimensions(t)

        y_hi = ht
        if self.title is not None:
            # remove Y space for X axis title
            y_hi -= self.txt_ht + 4
        # remove Y space for X axis labels
        y_hi -= self.txt_ht + self.pad_px

        self.aide.update_plot_bbox(y_hi=y_hi)

    def update_resize(self, viewer, dims, xy_lim):
        """This method is called if the viewer's window is resized.

        Update all the XAxis elements to reflect the new dimensions.
        """
        x_lo, y_lo, x_hi, y_hi = xy_lim
        wd, ht = dims[:2]

        # position axis title
        cx, cy = wd // 2 - self.title_wd // 2, ht - 4
        if self.title is not None:
            self.x_title.x = cx
            self.x_title.y = cy
            cy = cy - self.txt_ht

        # set X labels/grid as needed
        # calculate evenly spaced interval on X axis in window coords
        a = (x_hi - x_lo) // self.num_labels
        cx = x_lo
        for i in range(self.num_labels):
            lbl = self.x_lbls[i]
            lbl.x, lbl.y = cx, cy
            # get data coord equivalents
            x, y = self.get_data_xy(viewer, (cx, cy))
            # convert to formatted label
            lbl.text = self.format_value(x)
            grid = self.x_grid[i]
            grid.x1 = grid.x2 = cx
            grid.y1, grid.y2 = y_lo, y_hi
            cx += a

        self.x_axis_bg.x1, self.x_axis_bg.x2 = 0, wd
        self.x_axis_bg.y1, self.x_axis_bg.y2 = y_hi, ht

    def add_plot(self, viewer, plot_src):
        pass

    def delete_plot(self, viewer, plot_src):
        pass

    def set_grid_alpha(self, alpha):
        """Set the transparency (alpha) of the XAxis grid lines.
        `alpha` should be between 0.0 and 1.0
        """
        for i in range(self.num_labels):
            grid = self.x_grid[i]
            grid.alpha = alpha

    def get_data_xy(self, viewer, pt):
        arr_pts = np.asarray(pt)
        return viewer.tform['data_to_plot'].from_(arr_pts).T[:2]


class YAxis(CompoundObject):
    """
    Plotable object that defines Y axis labels and grid lines.
    """
    def __init__(self, aide, title=None, side='right', num_labels=4,
                 font='sans', fontsize=10.0):
        super(YAxis, self).__init__()

        self.aide = aide
        self.title = title
        self.side = side
        self.num_labels = num_labels
        self.kind = 'axis_y'
        self.font = font
        self.fontsize = fontsize
        self.title_wd = 0
        self.txt_wd = 0
        self.txt_ht = 0
        self.grid_alpha = 1.0
        self.format_value = self._format_value
        self.pad_px = 4

        # add Y grid
        self.y_grid = Bunch.Bunch()
        for i in range(self.num_labels):
            self.y_grid[i] = aide.dc.Line(0, 0, 0, 0, color=aide.grid_fg,
                                          linestyle='dash', linewidth=1,
                                          alpha=self.grid_alpha,
                                          coord='window')
            self.objects.append(self.y_grid[i])

        # bg for RHS Y axis labels
        self.y_axis_bg = aide.dc.Rectangle(0, 0, 100, 100, color=aide.norm_bg,
                                           fill=True, fillcolor=aide.axis_bg,
                                           coord='window')
        self.objects.append(self.y_axis_bg)

        # bg for LHS Y axis title
        self.y_axis_bg2 = aide.dc.Rectangle(0, 0, 100, 100, color=aide.norm_bg,
                                            fill=True, fillcolor=aide.axis_bg,
                                            coord='window')
        self.objects.append(self.y_axis_bg2)

        # Y grid (tick) labels
        self.y_lbls = Bunch.Bunch()
        for i in range(self.num_labels):
            self.y_lbls[i] = aide.dc.Text(0, 0, text='', color='black',
                                          font=self.font,
                                          fontsize=self.fontsize,
                                          coord='window')
            self.objects.append(self.y_lbls[i])

        # Y title
        if self.title is not None:
            self.y_title = aide.dc.Text(0, 0, text=self.title, color='black',
                                        font=self.font,
                                        fontsize=self.fontsize,
                                        rot_deg=90.0,
                                        coord='window')
            self.objects.append(self.y_title)

    def _format_value(self, v):
        """Default formatter for YAxis labels.
        """
        return "%.4g" % v

    def update_elements(self, viewer):
        """This method is called if the plot is set with new points,
        or is scaled or panned with existing points.

        Update the YAxis labels to reflect the new values and/or pan/scale.
        """
        # set Y labels/grid as needed
        for i in range(self.num_labels):
            lbl = self.y_lbls[i]
            # get data coord equivalents
            x, y = self.get_data_xy(viewer, (lbl.x, lbl.y))
            lbl.text = self.format_value(y)

    def update_bbox(self, viewer, dims):
        """This method is called if the viewer's window is resized.

        Update all the YAxis elements to reflect the new dimensions.
        """
        wd, ht = dims[:2]
        if self.txt_wd == 0:
            Text = self.y_lbls[0].__class__
            t = Text(0, 0, text=self.title if self.title is not None else '555.55',
                     fontsize=self.fontsize, font=self.font)
            self.title_wd, self.txt_ht = viewer.renderer.get_dimensions(t)
            # TODO: not sure this will give us the maximum length of number
            t.text = self.format_value(sys.float_info.max)
            self.txt_wd, _ = viewer.renderer.get_dimensions(t)

        if self.title is not None:
            x_lo = self.txt_ht + 2 + self.pad_px
        else:
            x_lo = 0
        x_hi = wd - (self.txt_wd + 4) - self.pad_px

        self.aide.update_plot_bbox(x_lo=x_lo, x_hi=x_hi)

    def update_resize(self, viewer, dims, xy_lim):
        """This method is called if the viewer's window is resized.

        Update all the YAxis elements to reflect the new dimensions.
        """
        x_lo, y_lo, x_hi, y_hi = xy_lim
        wd, ht = dims[:2]

        # position axis title
        cx = self.txt_ht + 2
        cy = ht // 2 + self.title_wd // 2
        if self.title is not None:
            self.y_title.x = cx
            self.y_title.y = cy

        cx = x_hi + self.pad_px
        cy = y_hi
        # set Y labels/grid as needed
        a = (y_hi - y_lo) // self.num_labels
        for i in range(self.num_labels):
            lbl = self.y_lbls[i]
            # calculate evenly spaced interval on Y axis in window coords
            lbl.x, lbl.y = cx, cy
            # get data coord equivalents
            x, y = self.get_data_xy(viewer, (cx, cy))
            lbl.text = self.format_value(y)
            grid = self.y_grid[i]
            grid.x1, grid.x2 = x_lo, x_hi
            grid.y1 = grid.y2 = cy
            cy -= a

        self.y_axis_bg.x1, self.y_axis_bg.x2 = x_hi, wd
        self.y_axis_bg.y1, self.y_axis_bg.y2 = y_lo, y_hi
        self.y_axis_bg2.x1, self.y_axis_bg2.x2 = 0, x_lo
        self.y_axis_bg2.y1, self.y_axis_bg2.y2 = y_lo, y_hi

    def add_plot(self, viewer, plot_src):
        pass

    def delete_plot(self, viewer, plot_src):
        pass

    def set_grid_alpha(self, alpha):
        """Set the transparency (alpha) of the XAxis grid lines.
        `alpha` should be between 0.0 and 1.0
        """
        for i in range(self.num_labels):
            grid = self.y_grid[i]
            grid.alpha = alpha

    def get_data_xy(self, viewer, pt):
        arr_pts = np.asarray(pt)
        return viewer.tform['data_to_plot'].from_(arr_pts).T[:2]


class PlotBG(CompoundObject):
    """
    Plotable object that defines the plot background.

    Can include a warning line and an alert line.  If the last Y value
    plotted exceeds the warning line then the background changes color.
    For example, you might be plotting detector values and want to set
    a warning if a certain threshold is crossed and an alert if the
    detector has saturated (alerts are higher than warnings).
    """
    def __init__(self, aide, warn_y=None, alert_y=None, linewidth=1):
        super(PlotBG, self).__init__()

        self.aide = aide
        self.y_lbl_info = [warn_y, alert_y]
        self.warn_y = warn_y
        self.alert_y = alert_y
        # default warning check
        self.check_warning = self._check_warning

        self.norm_bg = 'white'
        self.warn_bg = 'lightyellow'
        self.alert_bg = 'mistyrose2'
        self.kind = 'plot_bg'

        # add a backdrop that we can change color for visual warnings
        self.bg = aide.dc.Rectangle(0, 0, 100, 100, color=aide.norm_bg,
                                    fill=True, fillcolor=aide.norm_bg,
                                    fillalpha=1.0,
                                    coord='window')
        self.objects.append(self.bg)

        # add warning and alert lines
        if self.warn_y is not None:
            self.ln_warn = aide.dc.Line(0, self.warn_y, 1, self.warn_y,
                                        color='gold3', linewidth=linewidth,
                                        coord='window')
            self.objects.append(self.ln_warn)

        if self.alert_y is not None:
            self.ln_alert = aide.dc.Line(0, self.alert_y, 1, self.alert_y,
                                         color='red', linewidth=linewidth,
                                         coord='window')
            self.objects.append(self.ln_alert)

    def warning(self):
        self.bg.fillcolor = self.warn_bg

    def alert(self):
        self.bg.fillcolor = self.alert_bg

    def normal(self):
        self.bg.fillcolor = self.norm_bg

    def _check_warning(self):
        max_y = None
        for i, plot_src in enumerate(self.aide.plots.values()):
            # Hmmm...should this be 'data' limits?
            limits = plot_src.get_limits('plot')
            y = limits[1][1]
            max_y = y if max_y is None else max(max_y, y)

        if max_y is not None:
            if self.alert_y is not None and max_y > self.alert_y:
                self.alert()
            elif self.warn_y is not None and max_y > self.warn_y:
                self.warning()
            else:
                self.normal()

    def update_elements(self, viewer):
        """This method is called if the plot is set with new points,
        or is scaled or panned with existing points.

        Update the XAxis labels to reflect the new values and/or pan/scale.
        """
        y_lo, y_hi = self.aide.bbox.T[1].min(), self.aide.bbox.T[1].max()
        # adjust warning/alert lines
        if self.warn_y is not None:
            x, y = self.get_canvas_xy(viewer, (0, self.warn_y))
            if y_lo <= y <= y_hi:
                self.ln_warn.alpha = 1.0
            else:
                # y out of range of plot area, so make it invisible
                self.ln_warn.alpha = 0.0

            self.ln_warn.y1 = self.ln_warn.y2 = y

        if self.alert_y is not None:
            x, y = self.get_canvas_xy(viewer, (0, self.alert_y))
            if y_lo <= y <= y_hi:
                self.ln_alert.alpha = 1.0
            else:
                # y out of range of plot area, so make it invisible
                self.ln_alert.alpha = 0.0

            self.ln_alert.y1 = self.ln_alert.y2 = y

        self.check_warning()

    def update_bbox(self, viewer, dims):
        # this object does not adjust the plot bbox at all
        pass

    def update_resize(self, viewer, dims, xy_lim):
        """This method is called if the viewer's window is resized.

        Update all the PlotBG elements to reflect the new dimensions.
        """
        # adjust bg to window size, in case it changed
        x_lo, y_lo, x_hi, y_hi = xy_lim
        wd, ht = dims[:2]

        self.bg.x1, self.bg.y1 = x_lo, y_lo
        self.bg.x2, self.bg.y2 = x_hi, y_hi

        # adjust warning/alert lines
        if self.warn_y is not None:
            x, y = self.get_canvas_xy(viewer, (0, self.warn_y))
            self.ln_warn.x1, self.ln_warn.x2 = x_lo, x_hi
            self.ln_warn.y1 = self.ln_warn.y2 = y

        if self.alert_y is not None:
            x, y = self.get_canvas_xy(viewer, (0, self.alert_y))
            self.ln_alert.x1, self.ln_alert.x2 = x_lo, x_hi
            self.ln_alert.y1 = self.ln_alert.y2 = y

    def add_plot(self, viewer, plot_src):
        pass

    def delete_plot(self, viewer, plot_src):
        pass

    def get_canvas_xy(self, viewer, pt):
        arr_pts = np.asarray(pt)
        return viewer.tform['data_to_plot'].to_(arr_pts).T[:2]


class PlotTitle(CompoundObject):
    """
    Plotable object that defines the plot title and keys.
    """
    def __init__(self, aide, title='', font='sans', fontsize=12.0):
        super(PlotTitle, self).__init__()

        self.aide = aide
        self.font = font
        self.fontsize = fontsize
        self.title = title
        self.txt_ht = 0
        self.kind = 'plot_title'
        self.format_label = self._format_label
        self.pad_px = 5

        self.title_bg = aide.dc.Rectangle(0, 0, 100, 100, color=aide.norm_bg,
                                          fill=True, fillcolor=aide.axis_bg,
                                          coord='window')
        self.objects.append(self.title_bg)

        self.lbls = dict()
        self.lbls[0] = aide.dc.Text(0, 0, text=title, color='black',
                                    font=self.font,
                                    fontsize=self.fontsize,
                                    coord='window')
        self.objects.append(self.lbls[0])

    def _format_label(self, lbl, plot_src):
        """Default formatter for PlotTitle labels.
        """
        lbl.text = "{0:}".format(plot_src.name)

    def update_elements(self, viewer):
        """This method is called if the plot is set with new points,
        or is scaled or panned with existing points.

        Update the PlotTitle labels to reflect the new values.
        """
        for i, plot_src in enumerate(self.aide.plots.values()):
            lbl = self.lbls[plot_src]
            self.format_label(lbl, plot_src)

    def update_bbox(self, viewer, dims):
        """This method is called if the viewer's window is resized.

        Update all the PlotTitle elements to reflect the new dimensions.
        """
        wd, ht = dims[:2]
        if self.txt_ht == 0:
            _, self.txt_ht = viewer.renderer.get_dimensions(self.lbls[0])

        y_lo = self.txt_ht + self.pad_px

        self.aide.update_plot_bbox(y_lo=y_lo)

    def update_resize(self, viewer, dims, xy_lim):
        """This method is called if the viewer's window is resized.

        Update all the PlotTitle elements to reflect the new dimensions.
        """
        x_lo, y_lo, x_hi, y_hi = xy_lim
        wd, ht = dims[:2]

        nplots = len(list(self.aide.plots.keys())) + 1

        # set title labels as needed
        a = wd // (nplots + 1)

        cx, cy = 4, self.txt_ht
        lbl = self.lbls[0]
        lbl.x, lbl.y = cx, cy

        for i, plot_src in enumerate(self.aide.plots.values()):
            cx += a
            lbl = self.lbls[plot_src]
            lbl.x, lbl.y = cx, cy
            self.format_label(lbl, plot_src)

        self.title_bg.x1, self.title_bg.x2 = 0, wd
        self.title_bg.y1, self.title_bg.y2 = 0, y_lo

    def add_plot(self, viewer, plot_src):
        text = plot_src.name
        color = plot_src.color
        Text = self.lbls[0].__class__
        lbl = Text(0, 0, text=text, color=color,
                   font=self.font,
                   fontsize=self.fontsize,
                   coord='window')
        self.lbls[plot_src] = lbl
        self.objects.append(lbl)
        lbl.crdmap = self.lbls[0].crdmap
        self.format_label(lbl, plot_src)

        # reorder and place labels
        dims = viewer.get_window_size()
        self.update_resize(viewer, dims, self.aide.llur)

    def delete_plot(self, viewer, plot_src):
        lbl = self.lbls[plot_src]
        del self.lbls[plot_src]
        self.objects.remove(lbl)

        # reorder and place labels
        dims = viewer.get_window_size()
        self.update_resize(viewer, dims, self.aide.llur)

class CalcPlot(XYPlot):

    def __init__(self, name=None, fn=np.sin, color='black',
                 linewidth=1, linestyle='solid', alpha=1.0, **kwdargs):
        super(CalcPlot, self).__init__(name=name,
                                       color=color, linewidth=linewidth,
                                       linestyle=linestyle, alpha=alpha,
                                       **kwdargs)
        self.kind = 'calcplot'
        self.fn = fn

    def plot(self, points):
        pass

    def calc_points(self, xpts):
        ypts = self.fn(xpts)
        return np.array((xpts, ypts)).T

    def get_limits(self, lim_type):
        try:
            llur = self.path.get_llur()
            limits = [llur[0:2], llur[2:4]]
            return np.array(limits)
        except Exception:
            return np.array(((0.0, 0.0), (0.0, 0.0)))

    def recalc(self, viewer):
        bbox = viewer.get_pan_rect()
        start_x, stop_x = bbox[0][0], bbox[2][0]
        wd, ht = viewer.get_window_size()
        xpts = np.linspace(start_x, stop_x, wd, dtype=np.float)
        self.path.points = self.calc_points(xpts)


# register our types
register_canvas_types(dict(xyplot=XYPlot, calcplot=CalcPlot))
