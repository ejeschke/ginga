# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Info`` plugin provides a pane of commonly useful metadata about the
focused channel image.  Common information includes some metadata
header values, coordinates, dimensions of the image, minimum and
maximum values, etc.  As the cursor is moved around the image, the X, Y,
Value, RA, and DEC values are updated to reflect the value under the cursor.

**Plugin Type: Global**

``Info`` is a global plugin.  Only one instance can be opened.

**Usage**

At the bottom of the ``Info`` interface are the color distribution
and cut levels controls.  The selector above the cut levels boxes lets
you chose from several distribution algorithms that map the values in
the image to the color map.  Choices are "linear", "log", "power", "sqrt",
"squared", "asinh", "sinh", and "histeq" (histogram equalization).

Below this, the low and high cut levels are shown and can be adjusted.
Pressing the "Auto Levels" button will recalculate cut levels based on
the current auto cut levels algorithm and parameters defined in the channel
preferences.

Below the "Auto Levels" button, the status of the settings for
"Cut New", "Zoom New", and "Center New" are shown for the currently active
channel.  These indicate how new images that are added to the channel
will be affected by auto cut levels, fitting to the window and panning
to the center of the image.

The "Follow New" checkbox controls whether the viewer will automatically
display new images added to the channel.  The "Raise New" checkbox controls
whether an image viewer window is raised when a new image is added.  These
two controls can be useful, for example, if an external program is adding
images to the viewer, and you wish to prevent interruption of your work
examining a particular image.

As a global plugin, ``Info`` responds to a change of focus to a new channel
by displaying the metadata from the new channel.
It typically appears under the "Synopsis" tab in the user interface.

This plugin is not usually configured to be closeable, but the user can
make it so by setting the "closeable" setting to True in the configuration
file--then Close and Help buttons will be added to the bottom of the UI.

"""
import time
import numpy as np

from ginga.gw import Widgets
from ginga import GingaPlugin, ColorDist, colors
from ginga.rv.plugins.Toolbar import Toolbar
from ginga.table.AstroTable import AstroTable
from ginga.plot.Plotable import Plotable
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.util.toolbox import calc_float_strings

__all__ = ['Info', 'Info_Ginga_Image',
           'Info_Ginga_Plot', 'Info_Ginga_Table']


class Info(Toolbar):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super().__init__(fv)

        self.opname_prefix = 'Info_'

    def __str__(self):
        return 'info'


class Info_Common(GingaPlugin.LocalPlugin):

    def __init__(self, fv, chviewer):
        # superclass defines some variables for us, like logger
        super().__init__(fv, chviewer)

        # truncate names after this size
        self.maxstr = 60

    def trunc(self, s):
        if len(s) > self.maxstr:
            return s[:self.maxstr - 3] + '...'
        else:
            return s


class Info_Ginga_Image(Info_Common):
    """Info sidebar for the Ginga Image viewer.
    """

    def __init__(self, fv, chviewer):
        # superclass defines some variables for us, like logger
        super().__init__(fv, chviewer)

        self.autozoom_options = ['on', 'override', 'once', 'off']
        self.autocut_options = self.autozoom_options
        self.autocenter_options = self.autozoom_options

        self.fv.add_callback('field-info', self.field_info_cb)

        self.gui_up = False

    def build_gui(self, container):
        sw = Widgets.ScrollArea()

        vbox = Widgets.VBox()
        sw.set_widget(vbox)

        captions = (('Channel:', 'label', 'Channel', 'llabel'),
                    ('Name:', 'label', 'Name', 'llabel'),
                    ('Object:', 'label', 'Object', 'llabel'),
                    ('X:', 'label', 'X', 'llabel'),
                    ('Y:', 'label', 'Y', 'llabel'),
                    ('Image-X:', 'label', 'Image_X', 'llabel'),
                    ('Image-Y:', 'label', 'Image_Y', 'llabel'),
                    ('Value:', 'label', 'Value', 'llabel'),
                    ('RA:', 'label', 'RA', 'llabel'),
                    ('DEC:', 'label', 'DEC', 'llabel'),
                    ('Equinox:', 'label', 'Equinox', 'llabel'),
                    ('Dimensions:', 'label', 'Dimensions', 'llabel'),
                    ('Min:', 'label', 'Min', 'llabel'),
                    ('Max:', 'label', 'Max', 'llabel'),
                    )
        w, b = Widgets.build_info(captions)
        self.w = b

        col = Widgets.VBox()
        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        col.add_widget(row, stretch=0)
        col.add_widget(Widgets.Label(''), stretch=1)
        sw2 = Widgets.ScrollArea()
        sw2.set_widget(col)
        vbox.add_widget(sw2, stretch=1)

        captions = (('Zoom:', 'label', 'Zoom', 'llabel',
                     'Color Dist', 'combobox'),
                    ('Cut Low:', 'label', 'Cut Low Value', 'llabel',
                     'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High Value', 'llabel',
                     'Cut High', 'entry'),
                    ('Auto Levels', 'button', 'spacer_1', 'spacer',
                     'Cut Levels', 'button'),
                    ('Cut New:', 'label', 'Cut New', 'combobox'),
                    ('Zoom New:', 'label', 'Zoom New', 'combobox',
                     'Follow New', 'checkbutton'),
                    ('Center New:', 'label', 'Center New', 'combobox',
                     'Raise New', 'checkbutton'),
                    )

        w, b = Widgets.build_info(captions)
        self.w.update(b)
        b.cut_levels.set_tooltip("Set cut levels manually")
        loval, hival = self.fitsimage.get_cut_levels()
        lo_str, hi_str = calc_float_strings(loval, hival)
        b.auto_levels.set_tooltip("Set cut levels by algorithm")
        b.cut_low.set_tooltip("Set low cut level (press Enter)")
        b.cut_low.set_length(9)
        b.cut_low.set_text(lo_str)
        b.cut_low_value.set_text(lo_str)
        b.cut_high.set_tooltip("Set high cut level (press Enter)")
        b.cut_high.set_length(9)
        b.cut_high.set_text(hi_str)
        b.cut_high_value.set_text(hi_str)

        combobox = b.color_dist
        for name in ColorDist.get_dist_names():
            combobox.append_text(name)
        b.color_dist.set_tooltip("Set distribution (stretching) algorithm")

        combobox = b.cut_new
        for name in self.autocut_options:
            combobox.append_text(name)
        b.cut_new.set_tooltip("Automatically set cut levels when switching images")

        combobox = b.zoom_new
        for name in self.autozoom_options:
            combobox.append_text(name)
        b.zoom_new.set_tooltip("Automatically fit image to window when switching images")

        combobox = b.center_new
        for name in self.autocenter_options:
            combobox.append_text(name)
        b.center_new.set_tooltip("Automatically center image in window when switching images")

        b.follow_new.set_tooltip("Automatically switch to new images in channel")
        b.raise_new.set_tooltip("Automatically raise channel viewer for new images")

        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(row, stretch=0)

        self.w.channel.set_text(self.channel.name)
        self.w.color_dist.add_callback('activated', self.set_color_dist)
        self.w.cut_low.add_callback('activated', self.cut_levels)
        self.w.cut_high.add_callback('activated', self.cut_levels)
        self.w.cut_levels.add_callback('activated', self.cut_levels)
        self.w.auto_levels.add_callback('activated', self.auto_levels)
        self.w.cut_new.add_callback('activated', self.set_autocuts_cb)
        self.w.zoom_new.add_callback('activated', self.set_autozoom_cb)
        self.w.center_new.add_callback('activated', self.set_autocenter_cb)
        self.w.follow_new.add_callback('activated', self.set_follow_cb)
        self.w.raise_new.add_callback('activated', self.set_raise_cb)

        fitssettings = self.fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.get_setting(name).add_callback('set',
                                                        self.cutset_cb)
        for name in ['scale']:
            fitssettings.get_setting(name).add_callback('set',
                                                        self.zoomset_cb)
        fitssettings.get_setting('color_algorithm').add_callback('set',
                                                                 self.cdistset_cb)
        fitssettings.get_setting('autocuts').add_callback('set',
                                                          self.autocuts_cb)
        fitssettings.get_setting('autozoom').add_callback('set',
                                                          self.autozoom_cb)
        fitssettings.get_setting('autocenter').add_callback('set',
                                                            self.autocenter_cb)
        fitssettings.get_setting('switchnew').add_callback('set',
                                                           self.follow_cb)
        fitssettings.get_setting('raisenew').add_callback('set',
                                                          self.raise_cb)

        container.add_widget(sw, stretch=1)
        self.gui_up = True

    def start(self):
        self.redo()

    def stop(self):
        self.gui_up = False

    def close(self):
        # NOTE: this shouldn't be called under normal usage
        self.fv.stop_local_plugin(self.chname, str(self))

    def redo(self):
        self.set_info()

    def zoomset_cb(self, setting, value):
        """This callback is called when the main window is zoomed.
        """
        if not self.gui_up:
            return
        #scale_x, scale_y = self.fitsimage.get_scale_xy()
        scale_x, scale_y = value

        # Set text showing zoom factor (1X, 2X, etc.)
        if scale_x == scale_y:
            text = self.fv.scale2text(scale_x)
        else:
            textx = self.fv.scale2text(scale_x)
            texty = self.fv.scale2text(scale_y)
            text = "X: %s  Y: %s" % (textx, texty)
        self.w.zoom.set_text(text)

    def cutset_cb(self, setting, value):
        if not self.gui_up:
            return
        loval, hival = value
        lo_str, hi_str = calc_float_strings(loval, hival)
        self.w.cut_low_value.set_text(lo_str)
        self.w.cut_high_value.set_text(hi_str)

    def cdistset_cb(self, setting, value):
        if not self.gui_up:
            return
        name = value
        self.w.color_dist.set_text(name)

    def autocuts_cb(self, setting, option):
        if not self.gui_up:
            return
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        self.w.cut_new.set_index(index)

    def autozoom_cb(self, setting, option):
        if not self.gui_up:
            return
        index = self.autozoom_options.index(option)
        self.w.zoom_new.set_index(index)

    def autocenter_cb(self, setting, option):
        if not self.gui_up:
            return
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = {True: 'on', False: 'off'}
            option = choice[option]
        index = self.autocenter_options.index(option)
        self.w.center_new.set_index(index)

    def follow_cb(self, setting, option):
        if not self.gui_up:
            return
        self.w.follow_new.set_state(option)

    def raise_cb(self, setting, option):
        if not self.gui_up:
            return
        self.w.raise_new.set_state(option)

    def set_autocuts_cb(self, w, index):
        if not self.gui_up:
            return
        option = self.autocut_options[index]
        self.fitsimage.enable_autocuts(option)

    def set_autozoom_cb(self, w, index):
        if not self.gui_up:
            return
        option = self.autozoom_options[index]
        self.fitsimage.enable_autozoom(option)

    def set_autocenter_cb(self, w, index):
        if not self.gui_up:
            return
        option = self.autocenter_options[index]
        self.fitsimage.enable_autocenter(option)

    def set_follow_cb(self, w, tf):
        if not self.gui_up:
            return
        self.fitsimage.get_settings().set(switchnew=tf)

    def set_raise_cb(self, w, tf):
        if not self.gui_up:
            return
        self.fitsimage.get_settings().set(raisenew=tf)

    # LOGIC

    def set_info(self):
        if not self.gui_up:
            return
        # Show cut levels
        loval, hival = self.fitsimage.get_cut_levels()
        lo_str, hi_str = calc_float_strings(loval, hival)
        self.w.cut_low_value.set_text(lo_str)
        self.w.cut_high_value.set_text(hi_str)

        # update zoom indicator
        scalefactor = self.fitsimage.get_scale()
        text = self.fv.scale2text(scalefactor)
        self.w.zoom.set_text(text)

        # update cut new/zoom new indicators
        t_ = self.fitsimage.get_settings()
        index = self.autocut_options.index(t_['autocuts'])
        self.w.cut_new.set_index(index)
        index = self.autozoom_options.index(t_['autozoom'])
        self.w.zoom_new.set_index(index)
        option = t_['autocenter']
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = {True: 'on', False: 'off'}
            option = choice[option]
        index = self.autocenter_options.index(option)
        self.w.center_new.set_index(index)
        self.w.follow_new.set_state(t_['switchnew'])
        self.w.raise_new.set_state(t_['raisenew'])

        # Set color distribution indicator
        name = t_['color_algorithm']
        self.w.color_dist.set_text(name)

        image = self.fitsimage.get_image()
        if image is None:
            return
        header = image.get_header()

        # Update info panel
        name = self.trunc(image.get('name', 'Noname'))
        self.w.name.set_text(name)
        objtext = self.trunc(header.get('OBJECT', 'UNKNOWN'))
        self.w.object.set_text(objtext)
        equinox = header.get('EQUINOX', '')
        self.w.equinox.set_text(str(equinox))

        # Show min, max values
        width, height = self.fitsimage.get_data_size()
        minval, maxval = image.get_minmax(noinf=False)
        self.w.max.set_text(str(maxval))
        self.w.min.set_text(str(minval))

        # Show dimensions
        dim_txt = "%dx%d" % (width, height)
        self.w.dimensions.set_text(dim_txt)

    def field_info_cb(self, fv, channel, info):
        if not self.gui_up:
            return
        self.w.x.set_text("%.3f" % info.x)
        self.w.y.set_text("%.3f" % info.y)
        if 'image_x' in info:
            self.w.image_x.set_text("%.3f" % info.image_x)
        else:
            self.w.image_x.set_text("")
        if 'image_y' in info:
            self.w.image_y.set_text("%.3f" % info.image_y)
        else:
            self.w.image_y.set_text("")
        self.w.value.set_text(str(info.value))
        if 'ra_txt' in info:
            self.w.ra.set_text(info.ra_txt)
            self.w.dec.set_text(info.dec_txt)
        if 'ra_lbl' in info:
            self.w.lbl_ra.set_text(info.ra_lbl + ':')
            self.w.lbl_dec.set_text(info.dec_lbl + ':')

    def cut_levels(self, w):
        loval, hival = self.fitsimage.get_cut_levels()
        try:
            lostr = self.w.cut_low.get_text().strip()
            if lostr != '':
                loval = float(lostr)

            histr = self.w.cut_high.get_text().strip()
            if histr != '':
                hival = float(histr)
            self.logger.debug("locut=%f hicut=%f" % (loval, hival))

            return self.fitsimage.cut_levels(loval, hival)
        except Exception as e:
            self.fv.show_error("Error cutting levels: %s" % (str(e)))

        return True

    def auto_levels(self, w):
        self.fitsimage.auto_levels()

    def set_color_dist(self, w, idx):
        name = w.get_text()
        self.fitsimage.set_color_algorithm(name)

    def __str__(self):
        return 'info_ginga_image'


class Info_Ginga_Plot(Info_Common):
    """Info sidebar for the Ginga Plot viewer.
    """

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super().__init__(fv, fitsimage)

        # Plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('info_Ginga_Plot')
        self.settings.add_defaults(linewidth=1,
                                   linestyle='-',
                                   linecolor='blue',
                                   markersize=6,
                                   markerwidth=0.5,
                                   markerstyle='o',
                                   markercolor='red',
                                   show_marker=False,
                                   file_suffix='.png')
        self.settings.load(onError='silent')

        viewer = self.channel.get_viewer('Ginga Plot')
        self.plot_viewer = viewer

        viewer.add_callback('range-set', self.range_set_cb)
        viewer.add_callback('motion', self.motion_cb)

        self.tab = None
        self.cols = []
        self._idx = []
        self._idxname = '_idx'
        self.line_count = 0
        self.colors = ['black', 'darkblue', 'forestgreen', 'purple4',
                       'orangered', 'magenta', 'cyan4']
        self._next_color = self.colors[0]
        self.color_count = 0
        # To store selected columns names of active table
        self.x_col = ''
        self.y_col = ''
        self.gui_up = False

    def build_gui(self, container):
        # if not have_mpl:
        #     raise ImportError('Install matplotlib to use this plugin')
        t_ = self.plot_viewer.get_settings()
        sw = Widgets.ScrollArea()

        vbox = Widgets.VBox()
        sw.set_widget(vbox)

        captions = (('Channel:', 'label', 'channel', 'llabel'),
                    ('Name:', 'label', 'name', 'llabel'),
                    ('X:', 'label', 'x_val', 'llabel'),
                    ('Y:', 'label', 'y_val', 'llabel'),
                    )
        w, b = Widgets.build_info(captions)
        self.w = b

        self.w.channel.set_text(self.channel.name)

        col = Widgets.VBox()
        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        col.add_widget(row, stretch=0)
        col.add_widget(Widgets.Label(''), stretch=1)
        sw2 = Widgets.ScrollArea()
        sw2.set_widget(col)
        vbox.add_widget(sw2, stretch=1)

        captions = (('spacer_11', 'spacer', 'X', 'llabel', 'Y', 'llabel'),
                    ('Col:', 'label', 'x_col', 'combobox', 'y_col', 'combobox'),
                    ('spacer_23', 'spacer',
                     "Color", 'button', "Add to plot", 'button'),
                    ('spacer_13', 'spacer',
                     "Clear Plot", 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        # Controls for X-axis column listing
        combobox = b.x_col
        combobox.set_enabled(False)
        for name in self.cols:
            combobox.append_text(name)
        if self.x_col in self.cols:
            combobox.set_text(self.x_col)
        combobox.add_callback('activated', self.x_select_cb)
        combobox.set_tooltip('Select a column to plot on X-axis')

        # Controls for Y-axis column listing
        combobox = b.y_col
        combobox.set_enabled(False)
        for name in self.cols:
            combobox.append_text(name)
        if self.y_col in self.cols:
            combobox.set_text(self.y_col)
        combobox.add_callback('activated', self.y_select_cb)
        combobox.set_tooltip('Select a column to plot on Y-axis')

        # Button and dialog to select color
        self.w.colorselect = Widgets.ColorDialog(parent=b.color,
                                                 title="Choose line color")
        self.w.colorselect.add_callback('activated', self.color_select_cb)
        hex_color = colors.lookup_color(self._next_color, format='hex')
        self.w.colorselect.set_color(hex_color)
        b.color.add_callback('activated', lambda w: self.w.colorselect.popup())
        b.color.set_tooltip("Set the color of the line to be added")
        b.color.set_color(bg=hex_color, fg='white')

        # Button to clear plot
        b.clear_plot.set_tooltip("Clear the current plot")
        b.clear_plot.add_callback('activated', self.clear_plot_cb)

        # Button to save plot
        b.add_to_plot.set_tooltip("Add selected columns to plot")
        b.add_to_plot.add_callback('activated', self.add_to_plot_cb)
        b.add_to_plot.set_enabled(False)

        fr = Widgets.Expander(title="Plot from Table")
        self.w.plot_tbl_expand = fr
        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(row)
        vbox.add_widget(fr, stretch=0)

        captions = (('spacer_21', 'spacer', 'X', 'llabel', 'Y', 'llabel'),
                    ('Dist:', 'label', 'x_dist', 'combobox',
                     'y_dist', 'combobox'),
                    ('Low:', 'label', 'x_lo', 'entry', 'y_lo', 'entry'),
                    ('High:', 'label', 'x_hi', 'entry', 'y_hi', 'entry'),
                    ('spacer_22', 'spacer', 'Show marker', 'checkbox',
                     'Save Plot', 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        # Controls for X-axis scaling
        combobox = b.x_dist
        for name in ['linear', 'log']:
            combobox.append_text(name)
        combobox.set_tooltip('Select a mapping to plot on X-axis')
        combobox.set_text(t_['plot_dist_axis'][0])
        combobox.add_callback('activated', self.x_dist_cb)

        # Controls for Y-axis column listing
        combobox = b.y_dist
        for name in ['linear', 'log']:
            combobox.append_text(name)
        combobox.set_tooltip('Select a mapping to plot on Y-axis')
        combobox.set_text(t_['plot_dist_axis'][1])
        combobox.add_callback('activated', self.y_dist_cb)

        self.set_xlimits_widgets()
        self.set_ylimits_widgets()

        b.x_lo.add_callback('activated', lambda w: self.set_xlim_lo_cb())
        b.x_lo.set_tooltip('Set X lower limit')

        b.x_hi.add_callback('activated', lambda w: self.set_xlim_hi_cb())
        b.x_hi.set_tooltip('Set X upper limit')

        b.y_lo.add_callback('activated', lambda w: self.set_ylim_lo_cb())
        b.y_lo.set_tooltip('Set Y lower limit')

        b.y_hi.add_callback('activated', lambda w: self.set_ylim_hi_cb())
        b.y_hi.set_tooltip('Set Y upper limit')

        b.show_marker.set_state(t_.get('plot_show_marker', False))
        b.show_marker.add_callback('activated', self.set_marker_cb)
        b.show_marker.set_tooltip('Mark data points')

        # Button to save plot
        b.save_plot.set_tooltip("Save plot to file")
        b.save_plot.add_callback('activated', lambda w: self.save_cb())
        b.save_plot.set_enabled(True)

        fr = Widgets.Expander(title="Plot Controls")
        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(row)
        vbox.add_widget(fr, stretch=0)
        fr.expand(True)

        container.add_widget(sw, stretch=1)
        self.gui_up = True

    def redo(self):
        """This is called when a new image arrives or the data in the
        existing image changes.
        """
        if not self.gui_up:
            return
        dataobj = self.plot_viewer.get_dataobj()
        table = dataobj.get('table', None)
        if table is not None:
            self.setup_table(table, dataobj)
        else:
            # clear table plotting stuff
            self.clear()

        name = self.trunc(dataobj.get('name', 'Noname'))
        self.w.name.set_text(name)

    def set_xlimits_widgets(self, set_min=True, set_max=True):
        """Populate axis limits GUI with current plot values."""
        ranges = self.plot_viewer.get_ranges()
        (x_lo, x_hi), (y_lo, y_hi) = ranges
        x_lo_str, x_hi_str = calc_float_strings(x_lo, x_hi)
        if set_min:
            self.w.x_lo.set_text(x_lo_str)
        if set_max:
            self.w.x_hi.set_text(x_hi_str)

    def set_ylimits_widgets(self, set_min=True, set_max=True):
        """Populate axis limits GUI with current plot values."""
        ranges = self.plot_viewer.get_ranges()
        (x_lo, x_hi), (y_lo, y_hi) = ranges
        y_lo_str, y_hi_str = calc_float_strings(y_lo, y_hi)
        if set_min:
            self.w.y_lo.set_text(y_lo_str)
        if set_max:
            self.w.y_hi.set_text(y_hi_str)

    def x_dist_cb(self, w, index):
        _dist = w.get_text().lower()
        self.plot_viewer.set_dist_axis(x_axis=_dist)

    def y_dist_cb(self, w, index):
        _dist = w.get_text().lower()
        self.plot_viewer.set_dist_axis(y_axis=_dist)

    def set_xlim_lo_cb(self, redraw=True):
        """Set plot limit based on user values."""
        ranges = self.plot_viewer.get_ranges()
        (x_lo, x_hi), (y_lo, y_hi) = ranges

        try:
            x_min = float(self.w.x_lo.get_text())
        except Exception as e:
            self.fv.show_error(f"error setting X low limit: {e}")
            return

        self.plot_viewer.set_ranges(x_range=(x_min, x_hi))

    def set_xlim_hi_cb(self, redraw=True):
        """Set plot limit based on user values."""
        ranges = self.plot_viewer.get_ranges()
        (x_lo, x_hi), (y_lo, y_hi) = ranges

        try:
            x_max = float(self.w.x_hi.get_text())
        except Exception as e:
            self.fv.show_error(f"error setting X high limit: {e}")
            return

        self.plot_viewer.set_ranges(x_range=(x_lo, x_max))

    def set_ylim_lo_cb(self, redraw=True):
        """Set plot limit based on user values."""
        ranges = self.plot_viewer.get_ranges()
        (x_lo, x_hi), (y_lo, y_hi) = ranges

        try:
            y_min = float(self.w.y_lo.get_text())
        except Exception as e:
            self.fv.show_error(f"error setting Y low limit: {e}")
            return

        self.plot_viewer.set_ranges(y_range=(y_min, y_hi))

    def set_ylim_hi_cb(self, redraw=True):
        """Set plot limit based on user values."""
        ranges = self.plot_viewer.get_ranges()
        (x_lo, x_hi), (y_lo, y_hi) = ranges

        try:
            y_max = float(self.w.y_hi.get_text())
        except Exception as e:
            self.fv.show_error(f"error setting Y high limit: {e}")
            return

        self.plot_viewer.set_ranges(y_range=(y_lo, y_max))

    def range_set_cb(self, viewer, ranges):
        (xmin, xmax), (ymin, ymax) = ranges

        if self.gui_up:
            self.set_xlimits_widgets()
            self.set_ylimits_widgets()

    def motion_cb(self, viewer, button, data_x, data_y):
        if not self.gui_up:
            return
        x_str = str(data_x)
        y_str = str(data_y)
        self.w.x_val.set_text(x_str)
        self.w.y_val.set_text(y_str)

    def set_marker_cb(self, w, tf):
        """Toggle show/hide data point markers."""
        settings = self.plot_viewer.get_settings()
        settings.set(plot_show_marker=tf)

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

        try:
            self.plot_viewer.save_rgb_image_as_file(target, format='png')

        except Exception as e:
            self.logger.error(str(e))
        else:
            self.logger.info('Table plot saved as {0}'.format(target))

    # --- TABLE METHODS ---

    def setup_table(self, table, plot):
        self.tab = table
        self.w.plot_tbl_expand.set_enabled(True)
        self.w.plot_tbl_expand.expand(True)
        # Generate column indices
        self.w.x_col.set_enabled(True)
        self.w.y_col.set_enabled(True)
        self.w.add_to_plot.set_enabled(True)
        # Generate column indices
        self._idx = np.arange(len(self.tab))

        # Populate combobox with table column names
        cols = [self._idxname] + self.tab.colnames
        if cols != self.cols:
            self.cols = cols
        x_col = plot.get('table_x_col', None)
        if x_col is None:
            x_col = cols[1] if len(cols) > 1 else cols[0]
        self.x_col = self._set_combobox(self.w.x_col, self.cols, x_col)
        y_col = plot.get('table_y_col', None)
        if y_col is None:
            y_col = cols[2] if len(cols) > 2 else cols[0]
        self.y_col = self._set_combobox(self.w.y_col, self.cols, y_col)

        # restore line and color counts
        self.line_count = plot.get('line_count', 0)
        self.color_count = plot.get('color_count', 0) - 1
        self._cycle_color()

    def clear(self):
        self.w.plot_tbl_expand.expand(False)
        self.w.plot_tbl_expand.set_enabled(False)
        self.w.add_to_plot.set_enabled(False)
        self.w.x_col.clear()
        self.w.y_col.clear()
        self.tab = None
        self.cols = []
        self._idx = []
        self._idxname = '_idx'
        self.x_col = ''
        self.y_col = ''

    def _set_combobox(self, combobox, vals, default):
        """Populate combobox with given list."""
        combobox.clear()
        for val in vals:
            combobox.append_text(val)
        combobox.show_text(default)
        return default

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

    def y_select_cb(self, w, index):
        """Callback to set Y-axis column."""
        try:
            self.y_col = self.cols[index]
        except IndexError as e:
            self.logger.error(str(e))

    def clear_plot_cb(self, w):
        plot = self.plot_viewer.get_dataobj()
        plot.set_titles(x_axis='', y_axis='')
        canvas = plot.get_canvas()
        objs = canvas.get_objects_by_tag_pfx('plot_')
        canvas.delete_objects(objs)
        self.line_count = 0
        self.color_count = len(self.colors) - 1
        self._cycle_color()
        plot.set(line_count=0, color_count=0)
        # plot.make_callback('modified')
        self.plot_viewer.replot()

    def add_to_plot_cb(self, w):
        plot = self.plot_viewer.get_dataobj()
        name = plot.get('name')

        if self.x_col == self._idxname:
            x_data = self._idx
        else:
            x_data = self.tab[self.x_col].data

        if self.y_col == self._idxname:
            y_data = self._idx
        else:
            y_data = self.tab[self.y_col].data

        x_label = self._get_label('x')
        y_label = self._get_label('y')
        title = name
        plot.set_titles(x_axis=x_label, y_axis=y_label, title=title)
        plot.set_grid(True)

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

        # pick a rotating color for the new plot
        color = self._next_color
        self._cycle_color()
        plot.set(color_count=self.color_count,
                 table_x_col=self.x_col, table_y_col=self.y_col)

        canvas = plot.get_canvas()
        dc = get_canvas_types()
        points = np.array((x_data, y_data)).T
        canvas.add(dc.Path(points, color=color, linewidth=1,
                           alpha=1.0),
                   tag=f"plot_{self.line_count}",
                   redraw=False)
        self.line_count += 1
        plot.set(line_count=self.line_count)

        # plot.make_callback('modified')
        self.plot_viewer.replot()
        self.plot_viewer.zoom_fit()

    def color_select_cb(self, w, color):
        hex_color = w.get_color(format='hex')
        self._next_color = hex_color
        self.w.color.set_color(bg=hex_color, fg='black')

    def _cycle_color(self):
        self.color_count = (self.color_count + 1) % len(self.colors)
        _next_color = self.colors[self.color_count]
        hex_color = colors.lookup_color(_next_color, format='hex')
        self.w.colorselect.set_color(hex_color)
        self.w.color.set_color(bg=hex_color, fg='white')
        self._next_color = hex_color

    def start(self):
        self.redo()

    def stop(self):
        self.tab = None
        self.gui_up = False

    def close(self):
        # NOTE: this shouldn't be called under normal usage
        self.fv.stop_local_plugin(self.chname, str(self))

    def __str__(self):
        return 'info_ginga_plot'


class Info_Ginga_Table(Info_Common):
    """Info sidebar for the Ginga Table viewer.
    """

    def __init__(self, fv, chviewer):
        # superclass defines some variables for us, like logger
        super().__init__(fv, chviewer)

        viewer = self.channel.get_viewer('Ginga Table')
        self.table_viewer = viewer

        self.gui_up = False

    def build_gui(self, container):
        sw = Widgets.ScrollArea()

        vbox = Widgets.VBox()
        sw.set_widget(vbox)

        captions = (('Channel:', 'label', 'channel', 'llabel'),
                    ('Name:', 'label', 'name', 'llabel'),
                    )
        w, b = Widgets.build_info(captions)
        self.w = b

        self.w.channel.set_text(self.channel.name)

        col = Widgets.VBox()
        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        col.add_widget(row, stretch=0)
        col.add_widget(Widgets.Label(''), stretch=1)
        sw2 = Widgets.ScrollArea()
        sw2.set_widget(col)
        vbox.add_widget(sw2, stretch=1)

        channel = self.channel
        self.w.channel.set_text(channel.name)

        captions = (('New Plot', 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.new_plot.set_tooltip("Create new plot for this table")
        b.new_plot.add_callback('activated', self.new_plot_cb)

        fr = Widgets.Frame("Plot")
        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(row)
        vbox.add_widget(fr, stretch=0)

        container.add_widget(sw, stretch=1)
        self.gui_up = True

    def start(self):
        self.redo()

    def stop(self):
        self.gui_up = False

    def close(self):
        # NOTE: this shouldn't be called under normal usage
        self.fv.stop_local_plugin(self.chname, str(self))

    def new_plot_cb(self, w):
        dataobj = self.table_viewer.get_dataobj()
        if dataobj is None:
            self.fv.show_error("No table loaded")
            return
        name = "plot_{}".format(time.time())
        plot = Plotable(logger=self.logger)
        plot.set_titles(x_axis='', y_axis='', title=name)
        plot.set_grid(True)

        table = dataobj.get_data()
        plot.set(name=name, path=None, nothumb=False, table=table)

        self.channel.add_image(plot)

    def redo(self):
        """This is called when a new image arrives or the data in the
        existing image changes.
        """
        if not self.gui_up:
            return
        dataobj = self.table_viewer.get_dataobj()
        if isinstance(dataobj, AstroTable):
            if self.gui_up:
                self.w.new_plot.set_enabled(True)

        else:
            if self.gui_up:
                self.w.new_plot.set_enabled(False)
            self.logger.info("not able to process this object")

        name = self.trunc(dataobj.get('name', 'Noname'))
        self.w.name.set_text(name)

    def __str__(self):
        return 'info_ginga_table'
