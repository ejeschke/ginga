#
# PlotTable.py -- Table plotting plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets, Plot
from ginga.table.AstroTable import AstroTable
from ginga.util import plots


class PlotTable(LocalPlugin):
    """A plugin to display basic plot for any two selected columns
    in a table.

    """
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(PlotTable, self).__init__(fv, fitsimage)
        self._idxname = '_idx'

        # To store all active table info
        self.tab = None
        self.cols = []
        self._idx = []

        # To store selected columns names of active table
        self.x_col = ''
        self.y_col = ''

        # Plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_PlotTable')
        self.settings.addDefaults(linewidth=1,
                                  linestyle='-',
                                  linecolor='blue',
                                  markersize=6,
                                  markerwidth=0.5,
                                  markerstyle='o',
                                  markercolor='red',
                                  show_marker=True,
                                  x_index=1,
                                  y_index=2,
                                  file_suffix='.png')
        self.settings.load(onError='silent')

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        # Make the cuts plot
        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_margins(4, 4, 4, 4)
        vbox.set_spacing(2)

        msg_font = self.fv.get_font('sansFont', 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(msg_font)
        self.tw = tw

        fr = Widgets.Expander('Instructions')
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        # Add Tab Widget
        nb = Widgets.TabWidget(tabpos='top')
        vbox.add_widget(nb, stretch=1)

        self.tab_plot = plots.Plot(logger=self.logger,
                                   width=400, height=400)
        self.plot = Plot.PlotWidget(self.tab_plot)
        self.plot.resize(400, 400)
        ax = self.tab_plot.add_axis()
        ax.grid(True)

        # Add plot to its tab
        vbox_plot = Widgets.VBox()
        vbox_plot.add_widget(self.plot, stretch=1)
        nb.add_widget(vbox_plot, title='Plot')

        captions = (('X:', 'label', 'x_combo', 'combobox'),
                    ('Y:', 'label', 'y_combo', 'combobox'),
                    ('Log X', 'checkbutton', 'Log Y', 'checkbutton',
                     'Show Marker', 'checkbutton'),
                    ('X Low:', 'label', 'x_lo', 'entry'),
                    ('X High:', 'label', 'x_hi', 'entry'),
                    ('Y Low:', 'label', 'y_lo', 'entry'),
                    ('Y High:', 'label', 'y_hi', 'entry'),
                    ('Save', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        # Controls for X-axis column listing
        combobox = b.x_combo
        combobox.add_callback('activated', self.x_select_cb)
        self.w.xcombo = combobox
        combobox.set_tooltip('Select a column to plot on X-axis')

        # Controls for Y-axis column listing
        combobox = b.y_combo
        combobox.add_callback('activated', self.y_select_cb)
        self.w.ycombo = combobox
        combobox.set_tooltip('Select a column to plot on Y-axis')

        b.log_x.set_state(self.tab_plot.logx)
        b.log_x.add_callback('activated', self.log_x_cb)
        b.log_x.set_tooltip('Plot X-axis in log scale')

        b.log_y.set_state(self.tab_plot.logy)
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

        b.show_marker.set_state(self.settings.get('show_marker', True))
        b.show_marker.add_callback('activated', self.set_marker_cb)
        b.show_marker.set_tooltip('Mark data points')

        # Button to save plot
        self.save_plot = b.save
        self.save_plot.set_tooltip('Save table plot')
        self.save_plot.add_callback('activated', lambda w: self.save_cb())
        self.save_plot.set_enabled(False)

        vbox2 = Widgets.VBox()
        vbox2.add_widget(w, stretch=0)
        vbox.add_widget(vbox2, stretch=0)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)
        self.gui_up = True

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

    def instructions(self):
        self.tw.set_text("""Select columns from drop-down menus to plot. Click Save to save plot out to file.""")  # noqa

    def redo(self):
        """This is called when a new image arrives or the data in the
        existing image changes.
        """
        self.clear()

        tab = self.channel.get_current_image()
        if not isinstance(tab, AstroTable):
            return

        # Generate column indices
        self.tab = tab.get_data()
        self._idx = np.arange(len(self.tab))

        # Populate combobox with table column names
        self.cols = [self._idxname] + self.tab.colnames
        self.x_col = self._set_combobox(
            'xcombo', self.cols, default=self.settings.get('x_index', 1))
        self.y_col = self._set_combobox(
            'ycombo', self.cols, default=self.settings.get('y_index', 2))

        # Automatically plot first two columns
        self.plot_two_columns(reset_xlimits=True, reset_ylimits=True)

    def clear(self):
        """Clear plot and combo boxes."""
        self.clear_data()
        self.clear_plot()

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
        self.tab_plot.clear()
        self.tab_plot.draw()
        self.save_plot.set_enabled(False)

    def plot_two_columns(self, reset_xlimits=False, reset_ylimits=False):
        """Simple line plot for two selected columns."""
        self.clear_plot()

        if self.tab is None:  # No table data to plot
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
            x_data, y_data, marker = self._get_plot_data()

            self.tab_plot.plot(
                x_data, y_data,
                xtitle=self._get_label('x'), ytitle=self._get_label('y'),
                marker=marker, **plt_kw)

            if reset_xlimits:
                self.set_ylim_cb()
                self.set_xlimits_widgets()
            if reset_ylimits:
                self.set_xlim_cb()
                self.set_ylimits_widgets()
            if not (reset_xlimits or reset_ylimits):
                self.set_xlim_cb(redraw=False)
                self.set_ylim_cb()

        except Exception as e:
            self.logger.error(str(e))
        else:
            self.save_plot.set_enabled(True)

    def set_xlimits_widgets(self, set_min=True, set_max=True):
        """Populate axis limits GUI with current plot values."""
        xmin, xmax = self.tab_plot.ax.get_xlim()
        if set_min:
            self.w.x_lo.set_text('{0}'.format(xmin))
        if set_max:
            self.w.x_hi.set_text('{0}'.format(xmax))

    def set_ylimits_widgets(self, set_min=True, set_max=True):
        """Populate axis limits GUI with current plot values."""
        ymin, ymax = self.tab_plot.ax.get_ylim()
        if set_min:
            self.w.y_lo.set_text('{0}'.format(ymin))
        if set_max:
            self.w.y_hi.set_text('{0}'.format(ymax))

    def _get_plot_data(self):
        """Extract only good data point for plotting."""
        _marker_type = self.settings.get('markerstyle', 'o')

        if self.x_col == self._idxname:
            x_data = self._idx
        else:
            x_data = self.tab[self.x_col].data

        if self.y_col == self._idxname:
            y_data = self._idx
        else:
            y_data = self.tab[self.y_col].data

        if self.tab.masked:
            if self.x_col == self._idxname:
                x_mask = np.ones_like(self._idx, dtype=np.bool)
            else:
                x_mask = ~self.tab[self.x_col].mask

            if self.y_col == self._idxname:
                y_mask = np.ones_like(self._idx, dtype=np.bool)
            else:
                y_mask = ~self.tab[self.y_col].mask

            mask = x_mask & y_mask
            x_data = x_data[mask]
            y_data = y_data[mask]

        if len(x_data) > 1:
            i = np.argsort(x_data)  # Sort X-axis to avoid messy line plot
            x_data = x_data[i]
            y_data = y_data[i]

            if not self.w.show_marker.get_state():
                _marker_type = None

        return x_data, y_data, _marker_type

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

    def x_select_cb(self, w, index):
        """Callback to set X-axis column."""
        try:
            self.x_col = self.cols[index]
        except IndexError as e:
            self.logger.error(str(e))
        else:
            self.plot_two_columns(reset_xlimits=True)

    def y_select_cb(self, w, index):
        """Callback to set Y-axis column."""
        try:
            self.y_col = self.cols[index]
        except IndexError as e:
            self.logger.error(str(e))
        else:
            self.plot_two_columns(reset_ylimits=True)

    def log_x_cb(self, w, val):
        """Toggle linear/log scale for X-axis."""
        self.tab_plot.logx = val
        self.plot_two_columns()

    def log_y_cb(self, w, val):
        """Toggle linear/log scale for Y-axis."""
        self.tab_plot.logy = val
        self.plot_two_columns()

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
            self.tab_plot.draw()
            self.set_xlimits_widgets(set_min=set_min, set_max=set_max)

        if not (set_min and set_max):
            self.tab_plot.ax.set_xlim(xmin, xmax)
            if redraw:
                self.tab_plot.draw()

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
            self.tab_plot.draw()
            self.set_ylimits_widgets(set_min=set_min, set_max=set_max)

        if not (set_min and set_max):
            self.tab_plot.ax.set_ylim(ymin, ymax)
            if redraw:
                self.tab_plot.draw()

    def set_marker_cb(self, w, val):
        """Toggle show/hide data point markers."""
        self.plot_two_columns()

    def save_cb(self):
        """Save plot to file."""

        # This just defines the basename.
        # Extension has to be explicitly defined or things can get messy.
        target = Widgets.SaveDialog(title='Save plot').get_path()
        plot_ext = self.settings.get('file_suffix', '.png')

        # Save cancelled
        if not target:
            return

        if not target.endswith(plot_ext):
            target += plot_ext

        # TODO: This can be a user preference?
        fig_dpi = 100

        try:
            fig = self.tab_plot.get_figure()
            fig.savefig(target, dpi=fig_dpi)
        except Exception as e:
            self.logger.error(str(e))
        else:
            self.logger.info('Table plot saved as {0}'.format(target))

    def start(self):
        self.instructions()
        self.resume()

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.redo()

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        self.gui_up = False
        return True

    def __str__(self):
        return 'plottable'


# Replace module docstring with config doc for auto insert by Sphinx.
# In the future, if we need the real docstring, we can append instead of
# overwrite.
from ginga.util.toolbox import generate_cfg_example  # noqa
__doc__ = generate_cfg_example('plugin_PlotTable', package='ginga')
