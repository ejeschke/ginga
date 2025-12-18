#
# PlotView.py -- base class for plot viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from io import BytesIO
import numpy as np

from ginga import Mixins, colors
from ginga.util.viewer import ViewerBase
from ginga.misc import Bunch, Settings
from ginga.plot.Plotable import Plotable
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.cursors import cursor_info
from ginga import Bindings
from ginga.fonts import font_asst

try:
    from matplotlib.figure import Figure
    from matplotlib.backend_tools import Cursors
    from ginga.mplw import MplHelp

    from ginga.gw.Plot import PlotWidget
    have_mpl = True
except ImportError:
    have_mpl = False

__all__ = ['PlotViewBase', 'PlotViewEvent', 'PlotViewGw']


class PlotViewBase(ViewerBase):
    """A Ginga viewer for displaying 2D plots using matplotlib.
    """

    vname = 'Ginga Plot'
    vtypes = [Plotable]

    @classmethod
    def viewable(cls, dataobj):
        """Test whether `dataobj` is viewable by this viewer."""
        if isinstance(dataobj, Plotable):
            return True
        return False

    def __init__(self, logger=None, settings=None, figure=None):

        if not have_mpl:
            raise ImportError("Install 'matplotlib' to use this viewer")

        ViewerBase.__init__(self, logger=logger, settings=settings)
        self.needs_scrolledview = True

        self.t_ = self.settings
        self.t_.add_defaults(plot_bg='white',
                             plot_save_suffix='.png',
                             plot_dpi=100, plot_save_dpi=100,
                             plot_title_fontsize=14,
                             plot_axis_fontsize=14,
                             plot_limits=None,
                             plot_range=None,
                             plot_enter_focus=True,
                             plot_autozoom='override',
                             plot_zoom_rate=1.1)

        self.t_.get_setting('plot_range').add_callback('set', self.ranges_change_cb)

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

        # embedded profiles
        self.use_embedded_profile = True
        self.t_.add_defaults(profile_use_range=True)
        self.profile_keylist = ['plot_range']
        for name in self.profile_keylist:
            self.t_.get_setting(name).add_callback('set',
                                                   self._update_profile_cb)

        # viewer profile support
        self.default_viewer_profile = None
        self.t_.add_defaults(viewer_restore_range=True)
        self.capture_default_viewer_profile()

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
        # cursors
        self.cursor = {}

        self.plot_w = PlotWidget(self)

        self.artist_dct = dict()
        bg = self.settings.get('plot_bg', 'white')
        self.ax = self.figure.add_subplot(111, facecolor=bg)
        self.ax.grid(True)

        self.dc = get_canvas_types()
        self.private_canvas = self.dc.DrawingCanvas()

        # setup default fg color
        color = self.t_.get('color_fg', "#D0F0E0")
        r, g, b = colors.lookup_color(color)
        self.clr_fg = (r, g, b)

        # setup default bg color
        color = self.t_.get('color_bg', "#404040")
        r, g, b = colors.lookup_color(color)
        self.clr_bg = (r, g, b)

        self.timer = MplHelp.Timer(mplcanvas=self.figure.canvas)
        self.timer.add_callback('expired', self._timer_cb)
        # holds onscreen text object
        self._ost = None

        # For callbacks
        for name in ['image-set', 'image-unset',
                     'limits-set', 'range-set', 'redraw',
                     'configure']:
            self.enable_callback(name)

    def get_figure(self):
        return self.figure

    def get_widget(self):
        return self.figure.canvas

    def get_window_size(self):
        fig = self.get_figure()
        fig_wd_in, fig_ht_in = fig.get_size_inches()
        fig_dpi = fig.get_dpi()
        wd_px = int(fig_wd_in * fig_dpi)
        ht_px = int(fig_ht_in * fig_dpi)
        return (wd_px, ht_px)

    def add_axis(self, **kwdargs):
        self.ax = self.figure.add_subplot(111, **kwdargs)
        return self.ax

    def get_axis(self):
        return self.ax

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

        self.clear()

        self._dataobj = dataobj

        if isinstance(dataobj, Plotable):
            dataobj.add_callback('modified', self._dataobj_modified_cb)
            self.show_plotable(dataobj)

        self.make_callback('image-set', dataobj)

    def get_dataobj(self):
        return self._dataobj

    def get_data_size(self):
        # NOTE: used to determine widths needed in cursor readout
        (x_lo, y_lo), (x_hi, y_hi) = self.get_limits()
        return (x_hi, y_hi)

    def clear(self, redraw=True):
        """Clear plot display."""
        self.logger.debug('clearing viewer...')
        self._dataobj = None
        self.clear_data()
        if redraw:
            self.redraw()

    def clear_data(self):
        self.artist_dct = dict()
        self.ax.set_aspect('auto')
        #self.ax.set_aspect('equal', adjustable='box')
        self.ax.cla()
        self.t_.set(plot_limits=None, plot_range=None)
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
                           'mfc': color,
                           'mec': color})

        try:
            artists = self.artist_dct.setdefault(artist_category, [])
            line, = self.ax.plot(x_data, y_data, **plt_kw)
            artists.append(line)

            # adjust limits if necessary
            self._record_limits(x_data, y_data)

        except Exception as e:
            self.logger.error(str(e), exc_info=True)

    def _plot_text(self, x, y, text, artist_category='default', rot_deg=0,
                   linewidth=1, color='black', font='sans', fontsize=12,
                   bgcolor=None, bordercolor=None, borderlinewidth=0,
                   borderpadding=4):
        artists = self.artist_dct.setdefault(artist_category, [])
        fontdict = dict(color=color, family=font, size=fontsize)
        kwargs = dict()
        if bgcolor is not None:
            bbox = dict(facecolor=bgcolor)
            kwargs['bbox'] = bbox
        if bordercolor is not None:
            bbox = kwargs.get('bbox', dict())
            bbox['edgecolor'] = bordercolor
            bbox['linewidth'] = borderlinewidth
        bbox = kwargs.get('bbox', None)
        if bbox is not None:
            bbox['pad'] = borderpadding

        text = self.ax.text(x, y, text, color=color, rotation=rot_deg,
                            fontdict=fontdict, clip_on=True, **kwargs)
        artists.append(text)

        # adjust limits if necessary
        self._record_limits(x, y)

    def _plot_xrange(self, x_lo, x_hi, artist_category='default',
                     linewidth=0, fillcolor='aquamarine', fillalpha=0.5):
        artists = self.artist_dct.setdefault(artist_category, [])
        hex_color = colors.resolve_color(fillcolor, format='tuple')

        span = self.ax.axvspan(x_lo, x_hi, facecolor=hex_color, alpha=fillalpha)
        artists.append(span)

        # adjust limits if necessary
        # self._record_limits(x, y)

    def _plot_yrange(self, y_lo, y_hi, artist_category='default',
                     linewidth=0, fillcolor='aquamarine', fillalpha=0.5):
        artists = self.artist_dct.setdefault(artist_category, [])
        hex_color = colors.resolve_color(fillcolor, format='tuple')

        span = self.ax.ayvspan(y_lo, y_hi, facecolor=hex_color, alpha=fillalpha)
        artists.append(span)

        # adjust limits if necessary
        # self._record_limits(x, y)

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

        if y_range is not None:
            y_lo, y_hi = y_range
            ranges[1] = [y_lo, y_hi]
            adjusted = True

        if adjusted:
            self.t_.set(plot_range=ranges, callback=True)

    def ranges_change_cb(self, setting, ranges):
        adjusted = False
        if ranges is None:
            ranges = (None, None)
        x_range, y_range = ranges

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
            self.make_callback('range-set', ranges.copy())

            _pan_x, _pan_y = self.t_['plot_pan'][:2]
            pan_x, pan_y = (x_lo + x_hi) * 0.5, (y_lo + y_hi) * 0.5
            if not np.isclose(_pan_x, pan_x) or not np.isclose(_pan_y, pan_y):
                # need to set the pan position because range is changing
                # not according to pan position
                #self.t_['plot_pan'] = (pan_x, pan_y)
                self.set_pan(pan_x, pan_y)

            self.redraw()

    def get_ranges(self):
        ranges = self.settings['plot_range']
        if ranges is None:
            (x_lo, y_lo), (x_hi, y_hi) = self.get_limits()
            return [[x_lo, x_hi], [y_lo, y_hi]]

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
            Do not reset ``plot_autozoom`` setting.

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

        if not no_reset:
            if self.t_['plot_autozoom'] == 'once':
                self.t_.set(plot_autozoom='off')

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
                text_clr = colors.resolve_color(obj.color, obj.alpha,
                                                format='tuple')
                bg_clr = None
                if obj.bgcolor is not None:
                    bg_clr = colors.resolve_color(obj.bgcolor, obj.bgalpha,
                                                  format='tuple')
                bd_clr = None
                if obj.bordercolor is not None:
                    bd_clr = colors.resolve_color(obj.bordercolor, obj.borderalpha,
                                                  format='tuple')
                self._plot_text(obj.x, obj.y, text=obj.text,
                                rot_deg=obj.rot_deg,
                                color=text_clr, bgcolor=bg_clr,
                                bordercolor=bd_clr,
                                borderlinewidth=obj.borderlinewidth,
                                borderpadding=obj.borderpadding,
                                font=obj.font, fontsize=obj.fontsize)

            elif isinstance(obj, self.dc.Canvas):
                self.render_canvas(obj)

            elif isinstance(obj, self.dc.XRange):
                self._plot_xrange(obj.x1, obj.x2, fillcolor=obj.fillcolor,
                                  fillalpha=obj.fillalpha)

            elif isinstance(obj, self.dc.YRange):
                self._plot_xrange(obj.y1, obj.y2, fillcolor=obj.fillcolor,
                                  fillalpha=obj.fillalpha)

    def apply_profile_or_settings(self, dataobj):
        """Apply a profile to the viewer.

        Parameters
        ----------
        dataobj : `~ginga.plot.Plotable`
            Image object.

        This function is used to initialize the viewer when a new data object
        is loaded.  Either the embedded profile settings or the default
        settings are applied as specified in the channel preferences.
        """
        # 1. copy the current viewer settings
        tmpprof = Settings.SettingGroup()
        self.t_.copy_settings(tmpprof, include_callbacks=False,
                              keylist=self.profile_keylist,
                              callback=False)

        # 2. reset selected items in the copy to default profile
        # if there is one
        keylist1 = set([])
        if self.default_viewer_profile is not None:
            dvp = self.default_viewer_profile
            if self.t_['viewer_restore_range'] and 'plot_range' in dvp:
                keylist1.add('plot_range')

            # is this really needed if we restore the range?
            if self.t_['viewer_restore_pan'] and 'plot_pan' in dvp:
                keylist1.add('plot_pan')

            # TODO
            # if self.t_['viewer_restore_cuts'] and 'cuts' in dvp:
            #     keylist1.add('cuts')

            # if self.t_['viewer_restore_distribution'] and 'color_algorithm' in dvp:
            #     keylist1.add('color_algorithm')

            # if self.t_['viewer_restore_color_map'] and 'color_map' in dvp:
            #     keylist1.update({'color_map', 'color_map_invert',
            #                      'color_map_rot_pct'})

            dvp.copy_settings(tmpprof, keylist=list(keylist1), callback=False)

        # 3. apply embedded profile selected items to the copy
        keylist2 = set([])
        profile = dataobj.get('profile', None)
        if profile is not None:
            # is this really needed if we restore the range?
            if self.t_['profile_use_pan'] and 'plot_pan' in profile:
                keylist2.add('plot_pan')

            if self.t_['profile_use_range'] and 'plot_range' in profile:
                keylist2.add('plot_range')

            # TODO
            # if self.t_['profile_use_cuts'] and 'cuts' in profile:
            #     keylist2.add('cuts')

            # if self.t_['profile_use_distribution'] and 'color_algorithm' in profile:
            #     keylist2.add('color_algorithm')

            # if self.t_['profile_use_color_map'] and 'color_map' in profile:
            #     keylist2.update({'color_map', 'color_map_invert',
            #                      'color_map_rot_pct'})

            profile.copy_settings(tmpprof, keylist=list(keylist2),
                                  callback=False)

        # 4. update our settings from the copy
        keylist = list(keylist1.union(keylist2))
        self.apply_profile(tmpprof, keylist=keylist)

        # 5. proceed with initialization that is not in the profile
        # initialize scale
        if self.t_['plot_autozoom'] != 'off' and 'plot_range' not in keylist2:
            self.logger.debug("auto zoom (%s)" % (self.t_['plot_autozoom']))
            self.zoom_fit()

        # TODO
        # # initialize cuts
        # if self.t_['autocuts'] != 'off' and 'cuts' not in keylist2:
        #     self.logger.debug("auto cuts (%s)" % (self.t_['autocuts']))
        #     self.auto_levels()

        # save the profile in the image
        if self.use_embedded_profile:
            self.checkpoint_profile()

    def show_plotable(self, plotable):
        canvas = plotable.get_canvas()
        self.render_canvas(canvas)

        titles = plotable.titles
        self.set_titles(title=titles.title,
                        x_axis=titles.x_axis, y_axis=titles.y_axis,
                        redraw=False)
        self.set_grid(plotable.grid)

        self.apply_profile_or_settings(plotable)

        self.redraw()

    def replot(self):
        dataobj = self._dataobj
        if dataobj is None:
            return

        (x_lo, x_hi), (y_lo, y_hi) = self.get_ranges()

        self.clear_data()

        if isinstance(dataobj, Plotable):
            self.show_plotable(dataobj)

        self.set_ranges(x_range=(x_lo, x_hi), y_range=(y_lo, y_hi))

    def _dataobj_modified_cb(self, dataobj):
        """Called when a dataobj we have looked at before is modified."""
        _dataobj = self.get_dataobj()
        if _dataobj is None or _dataobj is not dataobj:
            # nothing to do or object being modified is not the one
            # we are displaying
            return

        self.replot()

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

    def pan_delta(self, x_delta, y_delta):
        """Pan by a delta in X and Y specified in data points.

        Parameters
        ----------
        x_delta : float
            Delta in X

        y_delta : float
            Delta in Y

        """
        pan_x, pan_y = self.get_pan(coord='data')[:2]
        pan_x += x_delta
        pan_y += y_delta
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
        if rng_x == 0.0:
            pct_x = 1.0
            xthm_pct = 1.0
        else:
            pct_x = min(max(0.0, abs(x_min) / rng_x), 1.0)
            xthm_pct = max(min_pct, min(vis_x / rng_x, max_pct))

        if rng_y == 0.0:
            pct_y = 1.0
            ythm_pct = 1.0
        else:
            pct_y = min(max(0.0, abs(y_min) / rng_y), 1.0)
            ythm_pct = max(min_pct, min(vis_y / rng_y, max_pct))

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

    def get_rgb_array(self):
        canvas = self.get_widget()
        # force a draw
        canvas.draw()
        return self.plot_w.get_rgb_array()

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

    def apply_profile(self, profile, keylist=None):
        """Apply a profile to the viewer.

        Parameters
        ----------
        profile : `~ginga.misc.Settings.SettingGroup`

        This function is used to initialize the viewer to a known state.
        The keylist, if given, will limit the items to be transferred
        from the profile to viewer settings, otherwise all items are
        copied.
        """
        profile.copy_settings(self.t_, keylist=keylist,
                              callback=True)

    def capture_profile(self, profile):
        self.t_.copy_settings(profile, keylist=self.profile_keylist,
                              callback=False)
        self.logger.debug("profile attributes set")

    def capture_default_viewer_profile(self):
        if self.default_viewer_profile is None:
            self.default_viewer_profile = Settings.SettingGroup()
        self.t_.copy_settings(self.default_viewer_profile,
                              keylist=self.profile_keylist,
                              callback=False)
        self.logger.info("captured default profile")

    def checkpoint_profile(self):
        profile = self.save_profile()
        if profile is None:
            # no dataobj in viewer
            return
        self.capture_profile(profile)
        return profile

    def save_profile(self, **params):
        """Save the given parameters into profile settings.

        Parameters
        ----------
        params : dict
            Keywords and values to be saved.

        """
        dataobj = self.get_dataobj()
        if dataobj is None:
            return

        profile = dataobj.save_profile(**params)
        return profile

    def _update_profile_cb(self, setting, value):
        key = setting.name
        if self.use_embedded_profile:
            kwargs = {key: value}
            self.save_profile(**kwargs)

    def set_foreground(self, fg):
        self.clr_fg = colors.resolve_color(fg)

    def set_background(self, bg):
        self.clr_bg = colors.resolve_color(bg)

    def onscreen_message(self, text, delay=None, redraw=True):
        if self._ost is not None:
            self._ost.remove()

        width, height = self.get_window_size()

        font = self.t_.get('onscreen_font', 'sans serif')
        font_size = self.t_.get('onscreen_font_size', None)
        if font_size is None:
            font_size = font_asst.calc_font_size(width)

        self._ost = self.figure.text(0.5, 0.5, text,
                                     transform=self.figure.transFigure,
                                     ha='center', va='center', fontsize=16,
                                     font='Sans', color=self.clr_fg,
                                     bbox={'facecolor': 'black',
                                           'alpha': 1.0, 'pad': 6})
        if redraw:
            self.redraw()

        if delay is not None:
            self.timer.set(delay)

    def onscreen_message_off(self):
        return self.onscreen_message('')

    def _timer_cb(self, timer):
        self.onscreen_message_off()


class PlotViewEvent(Mixins.UIMixin, PlotViewBase):

    def __init__(self, logger=None, settings=None, figure=None):
        PlotViewBase.__init__(self, logger=logger, settings=settings,
                              figure=figure)
        Mixins.UIMixin.__init__(self)

        # for matplotlib key handling
        self._keytbl = {
            'shift': 'shift_l',
            'control': 'control_l',
            'alt': 'alt_l',
            'win': 'meta_l',  # windows key
            'cmd': 'meta_l',  # Command key on Macs
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
        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'pan',  # 'swipe', 'tap'
                     ):
            self.enable_callback(name)

        self.last_data_x, self.last_data_y = 0, 0

        self.connect_ui()

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
        key = self._keytbl.get(key, key)
        return key

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
        self.last_data_x, self.last_data_y = event.xdata, event.ydata
        num_degrees = amount  # ???
        self.make_ui_callback_viewer(self, 'scroll', direction, num_degrees,
                                     self.last_data_x, self.last_data_y)

    def _plot_button_press(self, event):
        button = self.__get_button(event)
        modifiers = self.__get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        # self.last_data_x, self.last_data_y = event.xdata, event.ydata
        self.make_ui_callback_viewer(self, 'button-press', button,
                                     self.last_data_x, self.last_data_y)

    def _plot_button_release(self, event):
        button = self.__get_button(event)
        modifiers = self.__get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        # self.last_data_x, self.last_data_y = event.xdata, event.ydata
        self.make_ui_callback_viewer(self, 'button-release', button,
                                     self.last_data_x, self.last_data_y)

    def _plot_motion_notify(self, event):
        button = self.__get_button(event)
        modifiers = self.__get_modifiers(event)
        self.last_data_x, self.last_data_y = event.xdata, event.ydata
        self.make_ui_callback_viewer(self, 'motion', button,
                                     self.last_data_x, self.last_data_y)

    def _plot_key_press(self, event):
        key = self.__get_key(event)
        modifiers = self.__get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        # self.last_data_x, self.last_data_y = event.xdata, event.ydata
        self.make_ui_callback_viewer(self, 'key-press', key)

    def _plot_key_release(self, event):
        key = self.__get_key(event)
        modifiers = self.__get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        # self.last_data_x, self.last_data_y = event.xdata, event.ydata
        self.make_ui_callback_viewer(self, 'key-release', key)

    def _plot_resize(self, event):
        wd, ht = event.width, event.height
        self.make_callback('configure', wd, ht)

    def _plot_enter_cursor(self, event):
        if self.t_['plot_enter_focus']:
            self.take_focus()
        self.make_callback('enter')

    def _plot_leave_cursor(self, event):
        self.make_callback('leave')

    def take_focus(self):
        w = self.get_widget()
        if hasattr(w, 'setFocus'):
            # NOTE: this is a Qt call, not cross-backend
            # TODO: see if matplotlib has a backend independent way
            # to do this
            w.setFocus()
        elif hasattr(w, 'grab_focus'):
            # NOTE: this is a Gtk3 call, not cross-backend
            w.grab_focus()

    def get_last_data_xy(self):
        return (self.last_data_x, self.last_data_y)


class CanvasView(PlotViewEvent):

    # class variables for binding map and bindings can be set
    bindmapClass = Bindings.BindingMapper
    bindingsClass = Bindings.ImageViewBindings

    @classmethod
    def set_bindingsClass(cls, klass):
        cls.bindingsClass = klass

    @classmethod
    def set_bindmapClass(cls, klass):
        cls.bindmapClass = klass

    def __init__(self, logger=None, settings=None, figure=None,
                 bindmap=None, bindings=None):
        PlotViewEvent.__init__(self, logger=logger, settings=settings,
                               figure=figure)
        Mixins.UIMixin.__init__(self)

        #self.private_canvas.ui_set_active(True, viewer=self)
        self.ui_set_active(True, viewer=self)

        if bindmap is None:
            bindmap = CanvasView.bindmapClass(self.logger)
        self.bindmap = bindmap
        bindmap.register_for_events(self)

        if bindings is None:
            bindings = CanvasView.bindingsClass(self.logger)
        self.set_bindings(bindings)

        # TODO: defaults?
        bindings.enable(pan=True, zoom=True)

        self._mode = None
        self.modetbl = dict(locked='L', softlock='S', held='H', oneshot='O')
        self.bindmap.add_callback('mode-set', self._mode_set_cb)

        # TODO
        bindings.set_mode(self, 'plot2d', mode_type='locked')

        # Needed for UIMixin to propagate events correctly
        #self.objects = [self.private_canvas]

    def get_bindmap(self):
        return self.bindmap

    def get_bindings(self):
        return self.bindings

    def set_bindings(self, bindings):
        self.bindings = bindings
        bindings.set_bindings(self)

    def _mode_set_cb(self, bindmap, mode, mode_type):

        width, height = self.get_window_size()

        font = self.t_.get('onscreen_font', 'sans serif')
        font_size = self.t_.get('onscreen_font_size', None)
        if font_size is None:
            font_size = font_asst.calc_font_size(width * 0.33)
            # TEMP
            if self._mode is None:
                font_size = 12

        # show the little mode status window
        if self._mode is not None:
            self._mode.remove()
            self._mode = None
        if mode is not None:
            mode_txt = f"{mode} [{self.modetbl[mode_type]}]"
            self._mode = self.figure.text(0.92, 0.94, mode_txt,
                                          transform=self.figure.transFigure,
                                          ha='center', va='center',
                                          font=font, fontsize=font_size,
                                          color=self.clr_fg,
                                          bbox={'facecolor': 'black',
                                                'alpha': 1.0, 'pad': 6})
        self.redraw()

    # def set_canvas(self, canvas, private_canvas=None):
    #     super(CanvasView, self).set_canvas(canvas,
    #                                        private_canvas=private_canvas)

    #     self.objects[0] = self.private_canvas


PlotViewGw = CanvasView
