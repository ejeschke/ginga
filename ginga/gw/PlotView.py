#
# PlotView.py -- base class for plot viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import logging
from io import BytesIO
import numpy as np

from ginga import Mixins
from ginga.misc import Callback, Settings, Bunch
from ginga.AstroImage import AstroImage
from ginga.plot.Plotable import Plotable
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.cursors import cursor_info
from ginga import events, AutoCuts

try:
    from matplotlib.figure import Figure
    from matplotlib.backend_tools import Cursors

    from ginga.gw.Plot import PlotWidget
    have_mpl = True
except ImportError:
    have_mpl = False

__all__ = ['PlotViewBase', 'PlotViewEvent', 'PlotViewGw']


class PlotViewBase(Callback.Callbacks):
    """A Ginga viewer for displaying 2D plots using matplotlib.
    """

    vname = 'Ginga Plot'
    vtypes = [AstroImage, Plotable]

    @classmethod
    def viewable(cls, dataobj):
        """Test whether `dataobj` is viewable by this viewer."""
        if isinstance(dataobj, Plotable):
            return True
        if not isinstance(dataobj, AstroImage):
            return False
        shp = list(dataobj.shape)
        # comment this check to be able to view 2D images with this viewer
        if 0 in shp or len(shp) != 1:
            return False
        return True

    def __init__(self, logger=None, settings=None, figure=None):
        Callback.Callbacks.__init__(self)

        if not have_mpl:
            raise ImportError("Install 'matplotlib' to use this viewer")

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('PlotView')
        self.needs_scrolledview = True

        # Create settings and set defaults
        # NOTE: typically inheriting channel settings
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings
        self.t_ = settings

        self.t_.add_defaults(plot_bg='white',
                             plot_save_suffix='.png',
                             plot_dpi=100, plot_save_dpi=100,
                             plot_title_fontsize=14,
                             plot_axis_fontsize=14,
                             plot_limits=None,
                             plot_range=None,
                             plot_enter_focus=True,
                             plot_zoom_rate=1.1)

        # pan position
        self.t_.add_defaults(plot_pan=(0.0, 0.0))
        self.t_.get_setting('plot_pan').add_callback('set', self.pan_change_cb)

        # for axis scaling
        self.t_.add_defaults(plot_dist_axis=('linear', 'linear'))
        for name in ['plot_dist_axis']:
            self.t_.get_setting(name).add_callback('set', self.axis_dist_change_cb)

        # plot markers
        self.t_.add_defaults(plot_show_marker=False, plot_marker_size=5,
                             plot_marker_width=0.35,
                             plot_marker_color='blue',
                             plot_marker_style='o')
        for name in ['plot_show_marker', 'plot_marker_size',
                     'plot_marker_width', 'plot_marker_color',
                     'plot_marker_style']:
            self.t_.get_setting(name).add_callback('set',
                                                   lambda setting, value: self.replot())

        # TODO
        width, height = 500, 500

        if figure is None:
            figure = Figure()
            dpi = figure.get_dpi()
            if dpi is None or dpi < 0.1:
                dpi = self.t_['plot_dpi']
            wd_in, ht_in = float(width) / dpi, float(height) / dpi
            figure.set_size_inches(wd_in, ht_in)
        self.figure = figure
        if hasattr(self.figure, 'set_tight_layout'):
            self.figure.set_tight_layout(True)

        self._dataobj = None
        self._data_limits = None
        self.rgb_order = 'RGBA'

        # for debugging
        self.name = str(self)
        # cursors
        self.cursor = {}

        self.plot_w = PlotWidget(self)

        self.artist_dct = dict()
        bg = self.settings.get('plot_bg', 'white')
        self.ax = self.figure.add_subplot(111, facecolor=bg)
        self.ax.grid(True)

        self.dc = get_canvas_types()
        klass = AutoCuts.get_autocuts('zscale')
        self.autocuts = klass(self.logger)

        # For callbacks
        for name in ['image-set', 'image-unset',
                     'limits-set', 'range-set', 'redraw',
                     'configure']:
            self.enable_callback(name)

    def get_figure(self):
        return self.figure

    def get_widget(self):
        # same as self.plot_w
        return self.figure.canvas

    def add_axis(self, **kwdargs):
        self.ax = self.figure.add_subplot(111, **kwdargs)
        return self.ax

    def get_axis(self):
        return self.ax

    def get_settings(self):
        return self.settings

    def get_logger(self):
        return self.logger

    def initialize_channel(self, fv, channel):
        # no housekeeping to do (for now) on our part, just override to
        # suppress the logger warning
        pass

    def set_dataobj(self, dataobj):
        """Set 1D data to be displayed.

        If there is no error, the ``'image-unset'`` and ``'image-set'``
        callbacks will be invoked.

        Parameters
        ----------
        dataobj : `~ginga.AstroImage.AstroImage` or `~ginga.plot.Plotable.Plotable`
            AstroImage object or Plotable.

        """
        if not self.viewable(dataobj):
            raise ValueError("Wrong type of object to load: %s" % (
                str(type(dataobj))))

        old_dataobj = self._dataobj
        if old_dataobj is not None:
            self.make_callback('image-unset', old_dataobj)
        self._dataobj = dataobj

        self.clear()

        if isinstance(dataobj, AstroImage):
            dataobj.add_callback('modified', lambda dataobj: self.replot())
            self.show_image(dataobj)

        elif isinstance(dataobj, Plotable):
            dataobj.add_callback('modified', lambda dataobj: self.replot())
            self.show_plotable(dataobj)

        self.zoom_fit()

        self.make_callback('image-set', dataobj)

    def get_dataobj(self):
        return self._dataobj

    def clear(self, redraw=True):
        """Clear plot display."""
        self.clear_data()
        self.t_['plot_range'] = None
        if redraw:
            self.redraw()

    def clear_data(self):
        self.logger.debug('clearing viewer...')
        self.artist_dct = dict()
        self.ax.set_aspect('auto')
        self.ax.cla()
        self.t_['plot_limits'] = None
        self._data_limits = None

    def remove_artist_category(self, artist_category, redraw=True):
        artists = self.artist_dct.setdefault(artist_category, [])
        for artist in artists:
            try:
                artist.remove()
            except Exception as e:
                pass
        if redraw:
            self.redraw()

    def set_titles(self, title=None, x_axis=None, y_axis=None, redraw=True):
        if x_axis is not None:
            self.ax.set_xlabel(x_axis)
        if y_axis is not None:
            self.ax.set_ylabel(y_axis)
        if title is not None:
            self.ax.set_title(title)
        ax = self.ax
        ax.title.set_fontsize(self.t_['plot_title_fontsize'])
        for item in ([ax.xaxis.label, ax.yaxis.label] +
                     ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(self.t_['plot_axis_fontsize'])

        # Make x axis labels a little more readable
        lbls = self.ax.xaxis.get_ticklabels()
        for lbl in lbls:
            lbl.set(rotation=45, horizontalalignment='right')

        if redraw:
            self.redraw()

    def set_grid(self, tf):
        self.ax.grid(tf)

    def _record_limits(self, x_data, y_data):
        x_min, x_max = np.nanmin(x_data), np.nanmax(x_data)
        y_min, y_max = np.nanmin(y_data), np.nanmax(y_data)

        adjusted = False
        if self._data_limits is None:
            x_lo, y_lo, x_hi, y_hi = x_min, y_min, x_max, y_max
            adjusted = True
        else:
            (x_lo, y_lo), (x_hi, y_hi) = self._data_limits
            if x_min < x_lo:
                x_lo, adjusted = x_min, True
            if x_max > x_hi:
                x_hi, adjusted = x_max, True
            if y_min < y_lo:
                y_lo, adjusted = y_min, True
            if y_max > y_hi:
                y_hi, adjusted = y_max, True

        if adjusted:
            self._data_limits = [(x_lo, y_lo), (x_hi, y_hi)]

    def _plot_line(self, x_data, y_data, artist_category='default', name=None,
                   linewidth=1, linestyle='-', color='black',
                   alpha=1.0):
        """Simple line plot."""

        plt_kw = {'lw': linewidth,
                  'ls': linestyle,
                  'color': color,
                  'alpha': alpha,
                  'antialiased': True,
                  }
        if self.t_['plot_show_marker']:
            plt_kw.update({'marker': self.t_['plot_marker_style'],
                           'ms': self.t_['plot_marker_size'],
                           'mew': self.t_['plot_marker_width'],
                           'mfc': self.t_['plot_marker_color'],
                           'mec': self.t_['plot_marker_color']})

        try:
            artists = self.artist_dct.setdefault(artist_category, [])
            line, = self.ax.plot(x_data, y_data, **plt_kw)
            artists.append(line)

            # adjust limits if necessary
            self._record_limits(x_data, y_data)

        except Exception as e:
            self.logger.error(str(e), exc_info=True)

    def _plot_text(self, x, y, text, artist_category='default', rot_deg=0,
                   linewidth=1, color='black', alpha=1.0,
                   font='sans', fontsize=12):
        artists = self.artist_dct.setdefault(artist_category, [])
        fontdict = dict(color=color, family=font, size=fontsize)
        text = self.ax.text(x, y, text, color=color, rotation=rot_deg,
                            fontdict=fontdict, clip_on=True)
        artists.append(text)

        # adjust limits if necessary
        self._record_limits(x, y)

    def _plot_normimage(self, dataobj, artist_category='default', rot_deg=0):
        artists = self.artist_dct.setdefault(artist_category, [])
        # Get the data extents
        x0, y0 = 0, 0
        data_np = dataobj.get_data()
        y1, x1 = data_np.shape[:2]
        # flipx, flipy, swapxy = self.get_transforms()
        # if swapxy:
        #     x0, x1, y0, y1 = y0, y1, x0, x1

        locut, hicut = self.autocuts.calc_cut_levels_data(data_np)

        extent = (x0, x1, y0, y1)
        img = self.ax.imshow(data_np, origin='lower',
                             interpolation='none',
                             norm='linear',  # also 'log',
                             vmin=locut, vmax=hicut,
                             cmap='gray',
                             extent=extent)
        artists.append(img)

        # adjust limits if necessary
        self._record_limits(np.array((x0, x1)), np.array((y0, y1)))

    def set_limits(self, limits):
        self.settings.set(plot_limits=limits)

        # NOTE: make compatible callback to image viewer
        self.make_callback('limits-set', limits)

    def get_limits(self):
        limits = self.settings['plot_limits']

        if limits is None:
            # No user defined limits. Return limits set from data points.
            if self._data_limits is None:
                return [[0.0, 0.0], [0.0, 0.0]]

            limits = self._data_limits.copy()

        return limits

    def reset_limits(self):
        """Reset the bounding box of the viewer extents.

        Parameters
        ----------
        None
        """
        self.t_.set(plot_limits=None)

    def get_pan_bbox(self):
        """Get the coordinates in the actual data corresponding to the
        area shown in the display for the current zoom level and pan.

        Returns
        -------
        points : list
            Coordinates in the form of
            ``[(x0, y0), (x1, y1), (x2, y2), (x3, y3)]``
            from lower-left to lower-right.

        """
        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()
        return [(x_lo, y_lo), (x_hi, y_lo), (x_hi, y_hi), (x_lo, y_hi)]

    def set_ranges(self, x_range=None, y_range=None):
        adjusted = False
        ranges = self.get_ranges()
        (x_lo, x_hi), (y_lo, y_hi) = ranges

        if x_range is not None:
            x_lo, x_hi = x_range
            ranges[0] = [x_lo, x_hi]
            adjusted = True
            self.ax.set_xlim(x_lo, x_hi)

        if y_range is not None:
            y_lo, y_hi = y_range
            ranges[1] = [y_lo, y_hi]
            adjusted = True
            self.ax.set_ylim(y_lo, y_hi)

        if adjusted:
            self.t_['plot_range'] = ranges
            self.make_callback('range-set', ranges.copy())

            _pan_x, _pan_y = self.t_['plot_pan'][:2]
            pan_x, pan_y = (x_lo + x_hi) * 0.5, (y_lo + y_hi) * 0.5
            if not np.isclose(_pan_x, pan_x) or not np.isclose(_pan_y, pan_y):
                # need to set the pan position because range is changing
                # not according to pan position
                #self.t_['plot_pan'] = (pan_x, pan_y)
                self.set_pan(pan_x, pan_y)

            #self.make_callback('range-set', ranges.copy())

            self.redraw()

    def get_ranges(self):
        ranges = self.settings['plot_range']
        if ranges is None:
            (x_lo, y_lo), (x_hi, y_hi) = self.get_limits()
            return [[x_lo, x_hi], [y_lo, y_hi]]

        #return [(x_lo, x_hi), (y_lo, y_hi)]
        return ranges.copy()

    def zoom_fit(self, axis='xy', no_reset=False):
        """Zoom to fit display window.
        Pan the image and scale the view to fit the size of the set
        limits (usually set to the image size).  Parameter `axis` can
        be used to set which axes are allowed to be scaled;
        Also see :meth:`zoom_to`.

        Parameters
        ----------
        axis : str
            One of: 'x', 'y', or 'xy' (default).

        no_reset : bool
            Do not reset ``autozoom`` setting.

        """
        # calculate actual width of the limits/image, considering rotation
        (x_min, y_min), (x_max, y_max) = self.get_limits()
        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()

        # account for t_[scale_x/y_base]
        if axis in ['x', 'xy']:
            x_lo, x_hi = x_min, x_max
        if axis in ['y', 'xy']:
            y_lo, y_hi = y_min, y_max

        self.set_ranges(x_range=(x_lo, x_hi), y_range=(y_lo, y_hi))

        if self.t_['autozoom'] == 'once':
            self.t_.set(autozoom='off')

    def set_dist_axis(self, x_axis=None, y_axis=None):
        if x_axis is None:
            x_axis = self.t_['plot_dist_axis'][0]
        if y_axis is None:
            y_axis = self.t_['plot_dist_axis'][1]

        self.t_.set(plot_dist_axis=(x_axis, y_axis))

    def axis_dist_change_cb(self, setting, value):
        x_axis, y_axis = value
        if x_axis is not None:
            self.ax.set_xscale(x_axis)
        if y_axis is not None:
            self.ax.set_yscale(y_axis)

        self.redraw()

    def redraw_now(self, whence=0):
        self.figure.canvas.draw()

        self.make_callback('redraw', whence)

    def redraw(self, whence=0):
        self.redraw_now(whence=whence)

    def render_canvas(self, canvas):
        for obj in canvas.objects:
            if isinstance(obj, self.dc.Path):
                data_x, data_y = obj.points.T
                self._plot_line(data_x, data_y, linewidth=obj.linewidth,
                                linestyle=obj.linestyle, color=obj.color,
                                alpha=obj.alpha)

            elif isinstance(obj, self.dc.Line):
                data_x, data_y = [obj.x1, obj.x2], [obj.y1, obj.y2]
                self._plot_line(data_x, data_y, linewidth=obj.linewidth,
                                linestyle=obj.linestyle, color=obj.color,
                                alpha=obj.alpha)

            elif isinstance(obj, self.dc.Text):
                self._plot_text(obj.x, obj.y, text=obj.text,
                                rot_deg=obj.rot_deg,
                                color=obj.color, fontsize=obj.fontsize)

            elif isinstance(obj, self.dc.NormImage):
                image = obj.get_image()
                self._plot_normimage(image, rot_deg=obj.rot_deg)

            elif isinstance(obj, self.dc.Canvas):
                self.render_canvas(obj)

    def show_plotable(self, plotable):
        canvas = plotable.get_canvas()
        self.render_canvas(canvas)

        titles = plotable.titles
        self.set_titles(title=titles.title,
                        x_axis=titles.x_axis, y_axis=titles.y_axis,
                        redraw=False)
        self.set_grid(plotable.grid)

        self.redraw()

    def show_image(self, image):
        data_np = image.get_data()

        self.set_grid(False)
        if len(data_np.shape) == 1:
            x_data = np.arange(len(data_np))
            self.set_titles(title=image.get('name', "NoName 1D data"),
                            x_axis="Index", y_axis="Value",
                            redraw=False)
            self._plot_line(x_data, data_np)

        elif len(data_np.shape) == 2:
            self.set_titles(title=image.get('name', "NoName 2D data"),
                            x_axis="X", y_axis="Y",
                            redraw=False)
            self._plot_normimage(image)

        self.redraw()

    def replot(self):
        dataobj = self._dataobj
        if dataobj is None:
            return

        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()
        self.clear_data()

        if isinstance(dataobj, AstroImage):
            self.show_image(dataobj)

        elif isinstance(dataobj, Plotable):
            self.show_plotable(dataobj)

        self.set_ranges(x_range=(x_lo, x_hi), y_range=(y_lo, y_hi))

    def get_pan(self, coord='data'):
        """Get pan positions.

        Parameters
        ----------
        coord : {'data'}
            For compatibility with the image viewer.

        Returns
        -------
        positions : tuple
            X and Y positions, in that order.

        """
        if coord != 'data':
            raise ValueError("`coord` must be 'data' with this viewer")
        return self.t_['plot_pan']

    def set_pan(self, pan_x, pan_y, coord='data', no_reset=False):
        """Set pan position.

        Parameters
        ----------
        pan_x, pan_y : float
            Pan positions in X and Y.

        coord : {'data', 'wcs'}
            Indicates whether the given pan positions are in data or WCS space.

        no_reset : bool
            Do not reset ``autocenter`` setting.

        """
        self.t_.set(plot_pan=(pan_x, pan_y))

    def pan_change_cb(self, setting, value):
        pan_x, pan_y = value

        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()
        x_delta, y_delta = (x_hi - x_lo) * 0.5, (y_hi - y_lo) * 0.5
        x1, x2 = pan_x - x_delta, pan_x + x_delta
        y1, y2 = pan_y - y_delta, pan_y + y_delta

        self.set_ranges(x_range=(x1, x2), y_range=(y1, y2))

    def panset_xy(self, data_x, data_y, no_reset=False):
        """Similar to :meth:`set_pan`, except that input pan positions
        are always in data space.

        """
        self.set_pan(data_x, data_y, coord='data', no_reset=no_reset)

    def pan_delta_px(self, x_delta_px, y_delta_px):
        """Pan by a delta in X and Y specified in pixels.

        Parameters
        ----------
        x_delta_px : float
            Delta pixels in X

        y_delta_px : float
            Delta pixels in Y

        """
        pan_x, pan_y = self.get_pan(coord='data')[:2]
        pan_x += x_delta_px
        pan_y += y_delta_px
        self.panset_xy(pan_x, pan_y)

    def panset_pct(self, pct_x, pct_y):
        """Similar to :meth:`set_pan`, except that pan positions
        are determined by multiplying data dimensions with the given
        scale factors, where 1 is 100%.

        """
        xy_mn, xy_mx = self.get_limits()
        pan_x, pan_y = self.get_pan()[:2]

        if pct_x is not None:
            pan_x = (xy_mn[0] + xy_mx[0]) * pct_x
        if pct_y is not None:
            pan_y = (xy_mn[1] + xy_mx[1]) * pct_y

        self.panset_xy(pan_x, pan_y)

    def calc_pan_pct(self, pad=0, min_pct=0.0, max_pct=0.9):
        """Calculate values for vertical/horizontal panning by percentages
        from the current pan position.  Mostly used by scrollbar callbacks.

        Parameters
        ----------
        pad : int (optional, defaults to 0)
            a padding amount in pixels to add to the limits when calculating

        min_pct : float (optional, range 0.0:1.0, defaults to 0.0)
        max_pct : float (optional, range 0.0:1.0, defaults to 0.9)

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            calculation results, which include the following attributes:
            - rng_x : the range of X of the limits (including padding)
            - rng_y : the range of Y of the limits (including padding)
            - vis_x : the visually shown range of X in the viewer
            - vis_y : the visually shown range of Y in the viewer
            - thm_pct_x : the length of a X scrollbar arm as a ratio
            - thm_pct_y : the length of a Y scrollbar arm as a ratio
            - pan_pct_x : the pan position of X as a ratio
            - pan_pct_y : the pan position of Y as a ratio

        """
        limits = self.get_limits()
        pan_x, pan_y = self.get_pan()[:2]

        # calculate the corners of the entire image in unscaled cartesian
        mxwd, mxht = limits[1][:2]
        mxwd, mxht = mxwd + pad, mxht + pad
        mnwd, mnht = limits[0][:2]
        mnwd, mnht = mnwd - pad, mnht - pad

        arr = np.array([(mnwd, mnht), (mxwd, mnht),
                        (mxwd, mxht), (mnwd, mxht)],
                       dtype=float)
        x, y = arr.T
        x, y = x - pan_x, y - pan_y
        x_min, x_max = np.min(x), np.max(x)
        y_min, y_max = np.min(y), np.max(y)

        # this is the range of X and Y of the entire image
        # in the viewer (unscaled)
        rng_x, rng_y = abs(x_max - x_min), abs(y_max - y_min)

        # this is the *visually shown* range of X and Y
        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()
        vis_x, vis_y = x_hi - x_lo, y_hi - y_lo
        arr = np.array([(x_lo, y_lo), (x_hi, y_hi)])
        x, y = arr.T
        x, y = x - pan_x, y - pan_y

        # calculate the length of the slider arms as a ratio
        xthm_pct = max(min_pct, min(vis_x / rng_x, max_pct))
        ythm_pct = max(min_pct, min(vis_y / rng_y, max_pct))

        # calculate the pan position as a ratio
        pct_x = min(max(0.0, abs(x_min) / rng_x), 1.0)
        pct_y = min(max(0.0, abs(y_min) / rng_y), 1.0)

        bnch = Bunch.Bunch(rng_x=rng_x, rng_y=rng_y, vis_x=vis_x, vis_y=vis_y,
                           thm_pct_x=xthm_pct, thm_pct_y=ythm_pct,
                           pan_pct_x=pct_x, pan_pct_y=pct_y)
        return bnch

    def pan_by_pct(self, pct_x, pct_y, pad=0):
        """Pan by a percentage of the data space. This method is designed
        to be called by scrollbar callbacks.

        Parameters
        ----------
        pct_x : float (range 0.0 : 1.0)
            Percentage in the X range to pan

        pct_y : float (range 0.0 : 1.0)
            Percentage in the Y range to pan

        pad : int (optional, defaults to 0)
            a padding amount in pixels to add to the limits when calculating

        """
        # Sanity check on inputs
        pct_x = np.clip(pct_x, 0.0, 1.0)
        pct_y = np.clip(pct_y, 0.0, 1.0)

        limits = self.get_limits()

        mxwd, mxht = limits[1][:2]
        mxwd, mxht = mxwd + pad, mxht + pad
        mnwd, mnht = limits[0][:2]
        mnwd, mnht = mnwd - pad, mnht - pad

        arr = np.array([(mnwd, mnht), (mxwd, mnht),
                        (mxwd, mxht), (mnwd, mxht)],
                       dtype=float)
        x, y = arr.T
        x_min, x_max = np.min(x), np.max(x)
        y_min, y_max = np.min(y), np.max(y)

        crd_x = x_min + (pct_x * (x_max - x_min))
        crd_y = y_min + (pct_y * (y_max - y_min))

        pan_x, pan_y = crd_x, crd_y
        self.logger.debug("crd=%f,%f pan=%f,%f" % (
            crd_x, crd_y, pan_x, pan_y))

        self.panset_xy(pan_x, pan_y)

    def zoom_plot(self, pct_x, pct_y, redraw=True):
        """Zoom the plot, keeping the pan position."""
        set_range = False
        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()
        pan_x, pan_y = self.get_pan()[:2]

        if pct_x is not None:
            xrng = x_hi - x_lo
            xinc = (xrng * 0.5) * pct_x
            x_lo, x_hi = pan_x - xinc, pan_x + xinc
            set_range = True

        if pct_y is not None:
            yrng = y_hi - y_lo
            yinc = (yrng * 0.5) * pct_y
            y_lo, y_hi = pan_y - yinc, pan_y + yinc
            set_range = True

        if set_range:
            self.set_ranges(x_range=(x_lo, x_hi), y_range=(y_lo, y_hi))

    def zoom_plot_at_cursor(self, cur_x, cur_y, pct_x, pct_y):
        """Zoom the plot, keeping the position under the cursor."""
        set_range = False
        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()

        if pct_x is not None:
            x_lo, x_hi = (cur_x - (cur_x - x_lo) * pct_x,
                          cur_x + (x_hi - cur_x) * pct_x)
            set_range = True

        if pct_y is not None:
            y_lo, y_hi = (cur_y - (cur_y - y_lo) * pct_y,
                          cur_y + (y_hi - cur_y) * pct_y)
            set_range = True

        if set_range:
            self.set_ranges(x_range=(x_lo, x_hi), y_range=(y_lo, y_hi))

    def get_axes_size_in_px(self):
        bbox = self.ax.get_window_extent().transformed(self.figure.dpi_scale_trans.inverted())
        width, height = bbox.width, bbox.height
        width *= self.figure.dpi
        height *= self.figure.dpi
        return (width, height)

    def get_rgb_image_as_buffer(self, output=None, format='png',
                                quality=90):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in a file IO-like object encoded as a bitmap graphics
        file.

        This can be overridden by subclasses.

        Parameters
        ----------
        output : a file IO-like object or None
            open python IO descriptor or None to have one created

        format : str
            A string defining the format to save the image.  Typically
            at least 'jpeg' and 'png' are supported. (default: 'png')

        quality: int
            The quality metric for saving lossy compressed formats.

        Returns
        -------
        buffer : file IO-like object
            This will be the one passed in, unless `output` is None
            in which case a BytesIO obejct is returned

        """
        obuf = output
        if obuf is None:
            obuf = BytesIO()

        fig_dpi = self.settings.get('plot_save_dpi', 100)
        fig = self.get_figure()
        fig.savefig(obuf, dpi=fig_dpi)

        return obuf

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        """Save the current image shown in the viewer, with any overlaid
        graphics, in a file with the specified format and quality.
        This can be overridden by subclasses.

        Parameters
        ----------
        filepath : str
            path of the file to write

        format : str
            See :meth:`get_rgb_image_as_buffer`.

        quality: int
            See :meth:`get_rgb_image_as_buffer`.

        """
        plot_ext = self.settings.get('plot_save_suffix', f'.{format}')
        if not filepath.endswith(plot_ext):
            filepath = filepath + plot_ext

        fig_dpi = self.settings.get('plot_save_dpi', 100)
        fig = self.get_figure()
        fig.savefig(filepath, dpi=fig_dpi)

    def get_cursor(self, cname):
        """Get the cursor stored under the name.
        This can be overridden by subclasses, if necessary.

        Parameters
        ----------
        cname : str
            name of the cursor to return.

        """
        return self.cursor[cname]

    def define_cursor(self, cname, cursor):
        """Define a viewer cursor under a name.  Does not change the
        current cursor.

        Parameters
        ----------
        cname : str
            name of the cursor to define.

        cursor : object
            a cursor object in the back end's toolkit

        `cursor` is usually constructed from `make_cursor`.
        """
        self.cursor[cname] = cursor

    def switch_cursor(self, cname):
        """Switch the viewer's cursor to the one defined under a name.

        Parameters
        ----------
        cname : str
            name of the cursor to switch to.

        """
        cursor = self.get_cursor(cname)
        self.figure.canvas.set_cursor(cursor)

    def __str__(self):
        return "PlotViewBase"


class PlotViewEvent(Mixins.UIMixin, PlotViewBase):

    def __init__(self, logger=None, settings=None, figure=None):
        PlotViewBase.__init__(self, logger=logger, settings=settings,
                              figure=figure)
        Mixins.UIMixin.__init__(self)

        # for interactive features
        self.can = Bunch.Bunch(zoom=False, pan=False)

        # for qt key handling
        self._keytbl = {
            'shift': 'shift_l',
            'control': 'control_l',
            'alt': 'alt_l',
            'win': 'super_l',
            'meta': 'meta_right',
            '`': 'backquote',
            '"': 'doublequote',
            "'": 'singlequote',
            '\\': 'backslash',
            ' ': 'space',
            'enter': 'return',
            'pageup': 'page_up',
            'pagedown': 'page_down',
        }
        # For callbacks
        #for name in []:
        #    self.enable_callback(name)

        self.last_data_x, self.last_data_y = 0, 0
        self.connect_ui()

        # enable interactivity in the plot
        self.__enable(zoom=True, pan=True)

    def __enable(self, pan=False, zoom=False):
        # NOTE: don't use this interface!  Likely to change!!!
        """If `pan` is True, enable interactive panning in the plot by a
        middle click.  If `zoom` is True , enable interactive zooming in
        the plot by scrolling.
        """
        self.can.update(dict(pan=pan, zoom=zoom))
        self.ui_set_active(True, viewer=self)
        if pan or zoom:
            if pan:
                self.add_callback('button-press', self.plot_do_pan)
            if zoom:
                self.add_callback('scroll', self.plot_do_zoom)

    def plot_do_zoom(self, cb_obj, event):
        """Can be set as the callback function for the 'scroll'
        event to zoom the plot.
        """
        if not self.can.zoom:
            return

        # Matplotlib only gives us the number of steps of the scroll,
        # positive for up and negative for down.
        if event.amount > 0:
            delta = self.t_['plot_zoom_rate'] ** -2
        elif event.amount < 0:
            delta = self.t_['plot_zoom_rate'] ** 2

        delta_x = delta_y = delta
        if 'ctrl' in event.modifiers:
            # only horizontal
            delta_y = 1.0
        elif 'shift' in event.modifiers:
            # only horizontal
            delta_x = 1.0

        if 'meta' in event.modifiers:
            # cursor position
            cur_x, cur_y = event.data_x, event.data_y
            if None not in [cur_x, cur_y]:
                self.zoom_plot_at_cursor(cur_x, cur_y, delta_x, delta_y)
        else:
            self.zoom_plot(delta_x, delta_y)

        return True

    def plot_do_pan(self, cb_obj, event):
        """Can be set as the callback function for the 'button-press'
        event to pan the plot with middle-click.
        """
        if event.button == 0x2:
            if not self.can.pan:
                return
            cur_x, cur_y = event.data_x, event.data_y
            if None not in [cur_x, cur_y]:
                self.set_pan(cur_x, cur_y)

        return True

    def connect_ui(self):
        canvas = self.figure.canvas
        if canvas is None:
            raise ValueError("matplotlib canvas is not yet created")
        connect = canvas.mpl_connect
        connect("motion_notify_event", self._plot_motion_notify)
        connect("button_press_event", self._plot_button_press)
        connect("button_release_event", self._plot_button_release)
        connect("scroll_event", self._plot_scroll)
        canvas.capture_scroll = True
        connect("figure_enter_event", self._plot_enter_cursor)
        connect("figure_leave_event", self._plot_leave_cursor)
        connect("key_press_event", self._plot_key_press)
        connect("key_release_event", self._plot_key_release)
        connect("resize_event", self._plot_resize)

        # Define cursors
        cursor_names = cursor_info.get_cursor_names()
        # TODO: handle other cursor types
        cross = Cursors.POINTER
        for curname in cursor_names:
            curinfo = cursor_info.get_cursor_info(curname)
            self.define_cursor(curinfo.name, cross)
        self.switch_cursor('pick')

    def __get_modifiers(self, event):
        return event.modifiers

    def __get_button(self, event):
        try:
            btn = 0x1 << (event.button.value - 1)
        except Exception:
            btn = 0
        return btn

    def transkey(self, keyname):
        self.logger.debug("matplotlib keyname='%s'" % (keyname))
        if keyname is None:
            return keyname
        key = keyname
        if 'shift+' in key:
            key = key.replace('shift+', '')
        if 'ctrl+' in key:
            key = key.replace('ctrl+', '')
        if 'alt+' in key:
            key = key.replace('alt+', '')
        if 'meta+' in key:
            key = key.replace('meta+', '')
        return self._keytbl.get(key, key)

    def get_key_table(self):
        return self._keytbl

    def __get_key(self, event):
        keyval = self.transkey(event.key)
        self.logger.debug("key event, mpl={}, key={}".format(event.key,
                                                             keyval))
        return keyval

    def _plot_scroll(self, event):
        button = self.__get_button(event)
        if event.button == 'up':
            direction = 0.0
        elif event.button == 'down':
            direction = 180.0
        amount = event.step
        modifiers = self.__get_modifiers(event)
        evt = events.ScrollEvent(viewer=self, button=button, state='scroll',
                                 mode=None, modifiers=modifiers,
                                 direction=direction, amount=amount,
                                 data_x=event.xdata, data_y=event.ydata)
        self.make_ui_callback('scroll', evt)

    def _plot_button_press(self, event):
        button = self.__get_button(event)
        modifiers = self.__get_modifiers(event)
        self.last_data_x, self.last_data_y = event.xdata, event.ydata
        evt = events.PointEvent(viewer=self, button=button, state='down',
                                mode=None, modifiers=modifiers,
                                data_x=event.xdata, data_y=event.ydata)
        self.make_ui_callback('button-press', evt)

    def _plot_button_release(self, event):
        button = self.__get_button(event)
        modifiers = self.__get_modifiers(event)
        self.last_data_x, self.last_data_y = event.xdata, event.ydata
        evt = events.PointEvent(viewer=self, button=button, state='up',
                                mode=None, modifiers=modifiers,
                                data_x=event.xdata, data_y=event.ydata)
        self.make_ui_callback('button-release', evt)

    def _plot_motion_notify(self, event):
        button = self.__get_button(event)
        modifiers = self.__get_modifiers(event)
        self.last_data_x, self.last_data_y = event.xdata, event.ydata
        evt = events.PointEvent(viewer=self, button=button, state='move',
                                mode=None, modifiers=modifiers,
                                data_x=event.xdata, data_y=event.ydata)
        self.make_ui_callback('motion', evt)

    def _plot_key_press(self, event):
        key = self.__get_key(event)
        modifiers = self.__get_modifiers(event)
        self.last_data_x, self.last_data_y = event.xdata, event.ydata
        evt = events.KeyEvent(viewer=self, key=key, state='down',
                              mode=None, modifiers=modifiers,
                              data_x=event.xdata, data_y=event.ydata)
        self.make_ui_callback('key-press', evt)

    def _plot_key_release(self, event):
        key = self.__get_key(event)
        modifiers = self.__get_modifiers(event)
        self.last_data_x, self.last_data_y = event.xdata, event.ydata
        evt = events.KeyEvent(viewer=self, key=key, state='up',
                              mode=None, modifiers=modifiers,
                              data_x=event.xdata, data_y=event.ydata)
        self.make_ui_callback('key-release', evt)

    def _plot_resize(self, event):
        wd, ht = event.width, event.height
        self.make_callback('configure', wd, ht)

    def _plot_enter_cursor(self, event):
        if self.t_['plot_enter_focus']:
            w = self.get_widget()
            w.setFocus()

        self.make_ui_callback('enter')

    def _plot_leave_cursor(self, event):
        self.make_ui_callback('leave')

    def __str__(self):
        return "PlotViewEvent"


PlotViewGw = PlotViewEvent
