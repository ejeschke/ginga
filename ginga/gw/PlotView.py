#
# PlotView.py -- base class for plot viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import logging
import numpy as np

from ginga.misc import Callback, Settings, Bunch
from ginga import AstroImage
from ginga.table import AstroTable

from ginga.gw import Widgets
try:
    from ginga.gw import Plot
    from ginga.util import plots
    have_mpl = True
except ImportError:
    have_mpl = False


class PlotViewGw(Callback.Callbacks):
    """A Ginga viewer for displaying 2D plots using matplotlib.
    """

    vname = 'Ginga Plot'
    vtypes = [AstroImage.AstroImage, AstroTable.AstroTable]

    @classmethod
    def viewable(cls, dataobj):
        """Test whether `dataobj` is viewable by this viewer."""
        if isinstance(dataobj, AstroTable.AstroTable):
            # TODO: check for at least 2 columns?
            return True
        if not isinstance(dataobj, AstroImage.AstroImage):
            return False
        shp = list(dataobj.shape)
        if 0 in shp or len(shp) != 1:
            return False
        return True

    def __init__(self, logger=None, settings=None):
        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('PlotView')

        self._dataobj = None
        # To store all active table info
        self.tab = None
        self.cols = []
        self._idx = []
        self._idxname = '_idx'
        # To store selected columns names of active table
        self.x_col = ''
        self.y_col = ''

        # Create settings and set defaults
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings
        self.settings.add_defaults(plot_bg='white', show_marker=False,
                                   x_index=1, y_index=2,
                                   linewidth=1, linestyle='-',
                                   linecolor='blue', markersize=6,
                                   markerwidth=0.5, markercolor='red',
                                   markerstyle='o', file_suffix='.png')

        # for debugging
        self.name = str(self)

        if not have_mpl:
            raise ImportError('Install matplotlib to use this plugin')

        top = Widgets.VBox()
        top.set_border_width(4)

        self.line_plot = plots.Plot(logger=self.logger,
                                    width=400, height=400)
        bg = self.settings.get('plot_bg', 'white')
        self.line_plot.add_axis(facecolor=bg)
        self.plot_w = Plot.PlotWidget(self.line_plot)
        self.plot_w.resize(400, 400)

        # enable interactivity in the plot
        self.line_plot.connect_ui()
        self.line_plot.enable(zoom=True, pan=True)
        self.line_plot.add_callback('limits-set', self.limits_cb)

        ax = self.line_plot.ax
        ax.grid(True)

        top.add_widget(self.plot_w, stretch=1)

        captions = (('X:', 'label', 'x_combo', 'combobox',
                     'Y:', 'label', 'y_combo', 'combobox'),
                    ('Log X', 'checkbutton', 'Log Y', 'checkbutton',
                     'Show Marker', 'checkbutton'),
                    ('X Low:', 'label', 'x_lo', 'entry',
                     'X High:', 'label', 'x_hi', 'entry',
                     'Reset X', 'button'),
                    ('Y Low:', 'label', 'y_lo', 'entry',
                     'Y High:', 'label', 'y_hi', 'entry',
                     'Reset Y', 'button'),
                    ('Save', 'button'))
        # for now...
        orientation = 'vertical'
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w = b

        top.add_widget(w, stretch=0)

        # Controls for X-axis column listing
        combobox = b.x_combo
        combobox.add_callback('activated', self.x_select_cb)
        self.w.xcombo = combobox
        combobox.set_enabled(False)
        combobox.set_tooltip('Select a column to plot on X-axis')

        # Controls for Y-axis column listing
        combobox = b.y_combo
        combobox.add_callback('activated', self.y_select_cb)
        self.w.ycombo = combobox
        combobox.set_enabled(False)
        combobox.set_tooltip('Select a column to plot on Y-axis')

        b.log_x.set_state(self.line_plot.logx)
        b.log_x.add_callback('activated', self.log_x_cb)
        b.log_x.set_tooltip('Plot X-axis in log scale')

        b.log_y.set_state(self.line_plot.logy)
        b.log_y.add_callback('activated', self.log_y_cb)
        b.log_y.set_tooltip('Plot Y-axis in log scale')

        b.x_lo.add_callback('activated', lambda w: self.set_xlim_cb())
        b.x_lo.set_tooltip('Set X lower limit')

        b.x_hi.add_callback('activated', lambda w: self.set_xlim_cb())
        b.x_hi.set_tooltip('Set X upper limit')

        b.y_lo.add_callback('activated', lambda w: self.set_ylim_cb())
        b.y_lo.set_tooltip('Set Y lower limit')

        b.y_hi.add_callback('activated', lambda w: self.set_ylim_cb())
        b.y_hi.set_tooltip('Set Y upper limit')

        b.reset_x.add_callback('activated', lambda w: self.reset_xlim_cb())
        b.reset_x.set_tooltip('Autoscale X limits')

        b.reset_y.add_callback('activated', lambda w: self.reset_ylim_cb())
        b.reset_y.set_tooltip('Autoscale Y limits')

        b.show_marker.set_state(self.settings.get('show_marker', False))
        b.show_marker.add_callback('activated', self.set_marker_cb)
        b.show_marker.set_tooltip('Mark data points')

        # Button to save plot
        self.save_plot = b.save
        self.save_plot.set_tooltip('Save table plot')
        self.save_plot.add_callback('activated', lambda w: self.save_cb())
        self.save_plot.set_enabled(False)

        self.widget = top

        # For callbacks
        for name in ['image-set']:
            self.enable_callback(name)

    def get_widget(self):
        return self.widget

    def get_settings(self):
        return self.settings

    def get_logger(self):
        return self.logger

    # def clear(self):
    #     self.widget.clear()

    def initialize_channel(self, fv, channel):
        # no housekeeping to do (for now) on our part, just override to
        # suppress the logger warning
        pass

    def set_dataobj(self, dataobj):
        if not self.viewable(dataobj):
            raise ValueError("Can't display this data object")

        self._dataobj = dataobj

        if isinstance(self._dataobj, AstroTable.AstroTable):
            # <-- dealing with a table
            self.clear_data()
            self.w.x_combo.set_enabled(True)
            self.w.y_combo.set_enabled(True)
            # Generate column indices
            self.tab = dataobj.get_data()
            self._idx = np.arange(len(self.tab))

            # Populate combobox with table column names
            self.cols = [self._idxname] + self.tab.colnames
            self.x_col = self._set_combobox('xcombo', self.cols,
                                            default=self.settings.get('x_index', 1))
            self.y_col = self._set_combobox('ycombo', self.cols,
                                            default=self.settings.get('y_index', 2))

        elif isinstance(self._dataobj, AstroImage.AstroImage):
            # <-- dealing with a 1D image
            self.clear_data()
            self.w.x_combo.set_enabled(False)
            self.w.y_combo.set_enabled(False)

        else:
            raise ValueError("I don't know how to handle type '{}'".format(type(self._dataobj)))

        self.do_plot(reset_xlimits=True, reset_ylimits=True)

        self.make_callback('image-set', dataobj)

    def get_dataobj(self):
        return self._dataobj

    def clear_data(self):
        """Clear comboboxes and columns."""
        self.tab = None
        self.cols = []
        self._idx = []
        self.x_col = ''
        self.y_col = ''
        self.w.xcombo.clear()
        self.w.ycombo.clear()
        self.w.x_lo.set_text('')
        self.w.x_hi.set_text('')
        self.w.y_lo.set_text('')
        self.w.y_hi.set_text('')

    def clear_plot(self):
        """Clear plot display."""
        self.line_plot.clear()
        self.line_plot.draw()
        self.save_plot.set_enabled(False)

    def plot_line(self, p_dat, reset_xlimits=True, reset_ylimits=True,
                  linewidth=1, linestyle='-', linecolor='blue'):
        """Simple line plot."""

        plt_kw = {'lw': linewidth,
                  'ls': linestyle,
                  'color': linecolor,
                  }
        self.w.x_combo.set_enabled(False)
        self.w.y_combo.set_enabled(False)

        try:
            self.line_plot.plot(
                p_dat.x_data, p_dat.y_data,
                xtitle=p_dat.x_label, ytitle=p_dat.y_label,
                marker=p_dat.marker, **plt_kw)

            if not reset_xlimits:
                self.set_xlim_cb()
            self.set_xlimits_widgets()

            if not reset_ylimits:
                self.set_ylim_cb()
            self.set_ylimits_widgets()

        except Exception as e:
            self.logger.error(str(e), exc_info=True)

    def do_plot(self, reset_xlimits=True, reset_ylimits=True):
        """Simple line plot."""
        self.clear_plot()

        if self._dataobj is None:  # No data to plot
            return

        plt_kw = {
            'lw': self.settings.get('linewidth', 1),
            'ls': self.settings.get('linestyle', '-'),
            'color': self.settings.get('linecolor', 'blue'),
            'ms': self.settings.get('markersize', 6),
            'mew': self.settings.get('markerwidth', 0.5),
            'mfc': self.settings.get('markercolor', 'red')}
        plt_kw['mec'] = plt_kw['mfc']

        try:
            p_dat = self.get_plot_data()

            self.line_plot.plot(
                p_dat.x_data, p_dat.y_data,
                xtitle=p_dat.x_label, ytitle=p_dat.y_label,
                marker=p_dat.marker, **plt_kw)

            if not reset_xlimits:
                self.set_xlim_cb()
            self.set_xlimits_widgets()

            if not reset_ylimits:
                self.set_ylim_cb()
            self.set_ylimits_widgets()

        except Exception as e:
            self.logger.error(str(e), exc_info=True)
        else:
            self.save_plot.set_enabled(True)

    def _set_combobox(self, attrname, vals, default=0):
        """Populate combobox with given list."""
        combobox = getattr(self.w, attrname)
        for val in vals:
            combobox.append_text(val)
        if default > len(vals):
            default = 0
        val = vals[default]
        combobox.show_text(val)
        return val

    def set_xlimits_widgets(self, set_min=True, set_max=True):
        """Populate axis limits GUI with current plot values."""
        xmin, xmax = self.line_plot.ax.get_xlim()
        if set_min:
            self.w.x_lo.set_text('{0}'.format(xmin))
        if set_max:
            self.w.x_hi.set_text('{0}'.format(xmax))

    def set_ylimits_widgets(self, set_min=True, set_max=True):
        """Populate axis limits GUI with current plot values."""
        ymin, ymax = self.line_plot.ax.get_ylim()
        if set_min:
            self.w.y_lo.set_text('{0}'.format(ymin))
        if set_max:
            self.w.y_hi.set_text('{0}'.format(ymax))

    def limits_cb(self, plot, dct):
        """Callback that is called when the limits are set by the
        plot object.
        """
        self.set_xlimits_widgets()
        self.set_ylimits_widgets()

    def get_plot_data(self):
        """Extract only good data point for plotting."""
        if isinstance(self._dataobj, AstroImage.AstroImage):
            y_data = self._dataobj.get_data()
            x_data = np.arange(len(y_data))
            x_label = 'Index'
            y_label = 'Value'

        elif isinstance(self._dataobj, AstroTable.AstroTable):
            if self.x_col == self._idxname:
                x_data = self._idx
            else:
                x_data = self.tab[self.x_col].data
            x_label = self._get_label('x')

            if self.y_col == self._idxname:
                y_data = self._idx
            else:
                y_data = self.tab[self.y_col].data
            y_label = self._get_label('y')

            if self.tab.masked:
                if self.x_col == self._idxname:
                    x_mask = np.ones_like(self._idx, dtype=bool)
                else:
                    x_mask = ~self.tab[self.x_col].mask

                if self.y_col == self._idxname:
                    y_mask = np.ones_like(self._idx, dtype=bool)
                else:
                    y_mask = ~self.tab[self.y_col].mask

                mask = x_mask & y_mask
                x_data = x_data[mask]
                y_data = y_data[mask]

            if len(x_data) > 1:
                i = np.argsort(x_data)  # Sort X-axis to avoid messy line plot
                x_data = x_data[i]
                y_data = y_data[i]

        else:
            raise ValueError("I don't know how to get plot data from type '{}'".format(type(self._dataobj)))

        marker = self.get_marker()

        return Bunch.Bunch(x_data=x_data, y_data=y_data, marker=marker,
                           x_label=x_label, y_label=y_label)

    def _get_label(self, axis):
        """Return plot label for column for the given axis."""

        if axis == 'x':
            colname = self.x_col
        else:  # y
            colname = self.y_col

        if colname == self._idxname:
            label = 'Index'
        else:
            col = self.tab[colname]
            if col.unit:
                label = '{0} ({1})'.format(col.name, col.unit)
            else:
                label = col.name

        return label

    def get_marker(self):
        _marker_type = self.settings.get('markerstyle', 'o')

        if not self.w.show_marker.get_state():
            _marker_type = None

        return _marker_type

    def x_select_cb(self, w, index):
        """Callback to set X-axis column."""
        try:
            self.x_col = self.cols[index]
        except IndexError as e:
            self.logger.error(str(e))
        else:
            self.do_plot(reset_xlimits=True, reset_ylimits=False)

    def y_select_cb(self, w, index):
        """Callback to set Y-axis column."""
        try:
            self.y_col = self.cols[index]
        except IndexError as e:
            self.logger.error(str(e))
        else:
            self.do_plot(reset_xlimits=False, reset_ylimits=True)

    def log_x_cb(self, w, val):
        """Toggle linear/log scale for X-axis."""
        self.line_plot.logx = val
        self.do_plot()

    def log_y_cb(self, w, val):
        """Toggle linear/log scale for Y-axis."""
        self.line_plot.logy = val
        self.do_plot()

    def set_xlim_cb(self, redraw=True):
        """Set plot limit based on user values."""
        try:
            xmin = float(self.w.x_lo.get_text())
        except Exception:
            set_min = True
        else:
            set_min = False

        try:
            xmax = float(self.w.x_hi.get_text())
        except Exception:
            set_max = True
        else:
            set_max = False

        if set_min or set_max:
            self.line_plot.draw()
            self.set_xlimits_widgets(set_min=set_min, set_max=set_max)

        if not (set_min and set_max):
            self.line_plot.ax.set_xlim(xmin, xmax)
            if redraw:
                self.line_plot.draw()

    def set_ylim_cb(self, redraw=True):
        """Set plot limit based on user values."""
        try:
            ymin = float(self.w.y_lo.get_text())
        except Exception:
            set_min = True
        else:
            set_min = False

        try:
            ymax = float(self.w.y_hi.get_text())
        except Exception:
            set_max = True
        else:
            set_max = False

        if set_min or set_max:
            self.line_plot.draw()
            self.set_ylimits_widgets(set_min=set_min, set_max=set_max)

        if not (set_min and set_max):
            self.line_plot.ax.set_ylim(ymin, ymax)
            if redraw:
                self.line_plot.draw()

    def reset_xlim_cb(self):
        self.line_plot.autoscale('x')

    def reset_ylim_cb(self):
        self.line_plot.autoscale('y')

    def set_marker_cb(self, w, val):
        """Toggle show/hide data point markers."""
        self.do_plot()

    def save_cb(self):
        """Save plot to file."""

        # This just defines the basename.
        # Extension has to be explicitly defined or things can get messy.
        w = Widgets.SaveDialog(title='Save plot')
        target = w.get_path()
        if target is None:
            # Save canceled
            return

        plot_ext = self.settings.get('file_suffix', '.png')

        if not target.endswith(plot_ext):
            target += plot_ext

        # TODO: This can be a user preference?
        fig_dpi = 100

        try:
            fig = self.line_plot.get_figure()
            fig.savefig(target, dpi=fig_dpi)

        except Exception as e:
            self.logger.error(str(e))
        else:
            self.logger.info('Table plot saved as {0}'.format(target))

    def __str__(self):
        return "PlotViewer"
