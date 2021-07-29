# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``Crosshair`` is a simple plugin to draw crosshairs labeled with the
position of the cross in pixels coordinates, WCS coordinates, or
data value at the cross position.

**Plugin Type: Local**

``Crosshair`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

Select the appropriate type of output in the "Format" drop-down
box in the UI: "xy" for pixel coordinates, "coords" for the WCS
coordinates, and "value" for the value at the crosshair position.

If "Drag only" is checked, then the crosshair is only updated when the
cursor is clicked or dragged in the window.  If unchecked the crosshair
is positioned by simply moving the cursor around the channel viewer window.

The "Cuts" tab contains a profile plot for the vertical and horizontal
cuts represented by the visible box boundary present when "Quick Cuts"
is checked.  This plot is updated in real time as the crosshair is moved.
When "Quick Cuts" is unchecked, the plot is not updated.

The size of the box is determined by the "radius" parameter.

The "Warn Level" control can be used to set a flux level above which a
warning is indicated in the Cuts plot by a yellow line and the background
turning yellow.  The warning is triggered if any value along either
the X or Y cut exceeds the warn level threshold.

The "Alert Level" control is similar, but represented by a red line and the
background turning pink.  The warning is triggered if any value along either
the X or Y cut exceeds the alert level threshold.  Alerts take precedence
over warnings.

Both the "Warn" and "Alert" features can be turned off by simply setting
a blank value.  They are turned off by default.

The cuts plot is interactive, but it really only makes sense to use that
if "Drag only" is checked.  You can press 'x' or 'y' in the plot window
to toggle on and off the autoaxis scaling feature for either axis, and
scroll in the plot to zoom in the X axis (hold Ctrl down while scrolling
to zoom the Y axis).

Crosshair provides a Pick plugin interaction feature: when the crosshair
is over an object you can press 'r' in the channel viewer window to have
the Pick plugin invoked on that particular location.  If a Pick is not
open already on that channel, it will be opened first.

**User Configuration**

"""
import numpy as np

from ginga import GingaPlugin
from ginga.gw import Widgets, Viewers
from ginga.canvas.types import plots as gplots
from ginga.plot.plotaide import PlotAide

__all__ = ['Crosshair']


class Crosshair(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Crosshair, self).__init__(fv, fitsimage)

        # get Crosshair preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Crosshair')
        self.settings.add_defaults(color='green', orientation=None,
                                   text_color='skyblue',
                                   box_color='aquamarine',
                                   quick_h_cross_color='#7570b3',
                                   quick_v_cross_color='#1b9e77',
                                   quick_cuts=False,
                                   drag_only=False,
                                   warn_level=None,
                                   alert_level=None,
                                   cuts_radius=15)
        self.settings.load(onError='silent')

        self.layertag = 'crosshair-canvas'
        self.xhtag = None

        self.quick_cuts = self.settings.get('quick_cuts', False)
        self.drag_only = self.settings.get('drag_only', False)

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.name = 'crosshair-canvas'
        canvas.enable_draw(True)
        canvas.set_drawtype('squarebox', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.add_draw_mode('move', down=self.cur_down,
                             move=self.cur_drag, up=self.cur_drag,
                             hover=self.cur_hover, key=self.key_down)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_draw_mode('move')
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        # create crosshair
        self.xh = self.dc.Crosshair(0, 0,
                                    color=self.settings.get('color'),
                                    textcolor=self.settings.get('text_color'),
                                    coord='data', format='xy')
        self.canvas.add(self.xh, redraw=False)

        self.cuts_radius = self.settings.get('cuts_radius', 15)
        alpha = 1.0 if self.quick_cuts else 0.0
        self.cuts_box = self.dc.SquareBox(0, 0, self.cuts_radius,
                                          color=self.settings.get('box_color'),
                                          alpha=alpha,
                                          coord='data')
        self.canvas.add(self.cuts_box, redraw=False)

        self.formats = ('xy', 'value', 'coords')
        self.format = 'xy'
        self._wd, self._ht = 400, 300
        self._split_sizes = [self._ht, self._ht]
        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        box, sw, orientation = Widgets.get_oriented_box(container,
                                                        orientation=self.settings.get('orientation', None))
        box.set_border_width(4)
        box.set_spacing(2)

        paned = Widgets.Splitter(orientation=orientation)
        self.w.splitter = paned

        nb = Widgets.TabWidget(tabpos='bottom')
        self.w.nb1 = nb
        paned.add_widget(Widgets.hadjust(nb, orientation))

        # Cuts profile plot
        ci = Viewers.CanvasView(logger=self.logger)
        width, height = self._wd, self._ht
        ci.set_desired_size(width, height)
        ci.set_background('white')
        ci.set_foreground('black')
        # for debugging
        ci.set_name('cuts_plot')

        # prepare this viewer as a plot viewer
        self.cuts_view = PlotAide(ci)
        self.cuts_view.setup_standard_frame(title="Cuts",
                                            x_title="Line index",
                                            y_title="Pixel value",
                                            warn_y=None, alert_y=None)
        title = self.cuts_view.get_plot_decor('plot_title')
        title.format_label = self._format_cuts_label

        warn_y = self.settings.get('warn_level', None)
        alert_y = self.settings.get('alert_level', None)
        plot_bg = self.cuts_view.get_plot_decor('plot_bg')
        plot_bg.warn_y = warn_y
        plot_bg.alert_y = alert_y

        # add X and Y data sources. Hereafter, we can just update the data
        # sources and call update_plots() whenever we have new X and Y arms
        cname1 = self.settings.get('quick_h_cross_color', '#7570b3')
        self.cuts_xsrc = gplots.XYPlot(name='X', color=cname1, linewidth=2,
                                       x_acc=np.mean, y_acc=np.nanmax)
        cname2 = self.settings.get('quick_v_cross_color', '#1b9e77')
        self.cuts_ysrc = gplots.XYPlot(name='Y', color=cname2, linewidth=2,
                                       x_acc=np.mean, y_acc=np.nanmax)
        self.cuts_view.add_plot(self.cuts_xsrc)
        self.cuts_view.add_plot(self.cuts_ysrc)

        ciw = Viewers.GingaScrolledViewerWidget(viewer=ci)
        ciw.resize(width, height)
        self.cuts_view.configure_scrollbars(ciw)

        nb.add_widget(ciw, title="Cuts")

        fr = Widgets.Frame("Crosshair")

        captions = (('Format:', 'label', 'format', 'combobox'),
                    ('Drag only', 'checkbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        combobox = b.format
        for name in self.formats:
            combobox.append_text(name)
        index = self.formats.index(self.format)
        combobox.set_index(index)
        combobox.add_callback('activated', lambda w, idx: self.set_format())

        b.drag_only.set_tooltip("Must click and drag to update")
        b.drag_only.add_callback('activated', self.drag_only_cb)
        b.drag_only.set_state(self.drag_only)

        fr.set_widget(w)
        box.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Quick Cuts")

        captions = (('Quick Cuts', 'checkbutton'),
                    ('Radius:', 'label', 'radius', 'entryset'),
                    ('Warn Level:', 'label', 'warn_y', 'entryset'),
                    ('Alert Level:', 'label', 'alert_y', 'entryset'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.quick_cuts.set_tooltip("Do quick cuts plots")
        b.quick_cuts.add_callback('activated', self.quick_cuts_cb)
        b.quick_cuts.set_state(self.quick_cuts)

        b.radius.set_text(str(self.cuts_radius))
        b.radius.set_tooltip("Pixel radius for quick mode cuts")
        b.radius.add_callback('activated', self.set_radius_cb)

        b.warn_y.set_tooltip("Warning level for quick mode cuts")
        b.alert_y.set_tooltip("Alert level for quick mode cuts")
        b.warn_y.set_text('' if warn_y is None else str(warn_y))
        b.alert_y.set_text('' if alert_y is None else str(alert_y))
        b.warn_y.add_callback('activated', self.set_quick_warn_cb)
        b.alert_y.add_callback('activated', self.set_quick_alert_cb)

        fr.set_widget(w)
        box.add_widget(fr, stretch=0)

        spacer = Widgets.Label('')
        box.add_widget(spacer, stretch=1)

        paned.add_widget(sw)
        paned.set_sizes(self._split_sizes)

        top.add_widget(paned, stretch=5)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.gui_up = True

    def set_format(self):
        index = self.w.format.get_index()
        self.format = self.formats[index]
        self.xh.format = self.format

        self.canvas.redraw(whence=3)
        return True

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # start crosshair operation
        p_canvas = self.fitsimage.get_canvas()
        if not p_canvas.has_object(self.canvas):
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.fv.show_status("Click and drag to position crosshair")

    def stop(self):
        self.gui_up = False
        self._split_sizes = self.w.splitter.get_sizes()
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        self.canvas.ui_set_active(False)
        self.fv.show_status("")

    def cuts_quick(self, data_x, data_y, radius):
        vip_img = self.fitsimage.get_vip()

        # Get points on the lines
        x0, y0, xarr, yarr = vip_img.cutout_cross(data_x, data_y, radius)

        # plot horizontal cut
        xpts = np.arange(len(xarr))
        points = np.array((xpts, xarr)).T
        self.cuts_xsrc.plot(points)

        # plot vertical cut
        ypts = np.arange(len(yarr))
        points = np.array((ypts, yarr)).T
        self.cuts_ysrc.plot(points)

        self.cuts_view.update_plots()

    def redo(self):
        data_x, data_y = self.xh.x, self.xh.y
        self.cuts_quick(data_x, data_y, self.cuts_radius)

    def move_crosshair(self, viewer, data_x, data_y):
        self.logger.debug("move crosshair data x,y=%f,%f" % (data_x, data_y))
        self.xh.move_to(data_x, data_y)

        if self.quick_cuts:
            self.cuts_box.move_to(data_x, data_y)
            self.cuts_quick(data_x, data_y, self.cuts_radius)

        self.canvas.update_canvas(whence=3)

    def cur_down(self, canvas, event, data_x, data_y, viewer):
        self.move_crosshair(self.fitsimage, data_x, data_y)

    def cur_drag(self, canvas, event, data_x, data_y, viewer):
        self.move_crosshair(self.fitsimage, data_x, data_y)

    def cur_hover(self, canvas, event, data_x, data_y, viewer):
        if not self.drag_only:
            self.move_crosshair(self.fitsimage, data_x, data_y)

    def key_down(self, canvas, event, data_x, data_y, viewer):

        if event.key != 'r':
            return False

        # start Pick plugin on this channel if it hasn't been yet
        opmon = self.channel.opmon
        opname = 'Pick'
        obj = opmon.get_plugin(opname)
        if not opmon.is_active(opname):
            opmon.start_plugin(self.chname, opname)

        # simulate a button down/up in Pick
        self.fv.gui_do(obj.btn_down, canvas, event, data_x, data_y, viewer)
        self.fv.gui_do(obj.btn_up, canvas, event, data_x, data_y, viewer)
        return True

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        canvas.delete_object_by_tag(tag)

        self.cuts_radius = int(round(obj.radius))
        self.cuts_box.radius = self.cuts_radius
        # set entry widget to match drawn radius
        self.w.radius.set_text(str(self.cuts_radius))

        self.move_crosshair(self.fitsimage, obj.x, obj.y)

    def drag_only_cb(self, w, tf):
        self.drag_only = tf
        return True

    def quick_cuts_cb(self, w, tf):
        self.quick_cuts = tf
        self.cuts_box.alpha = 1.0 if self.quick_cuts else 0.0
        self.canvas.update_canvas(whence=3)
        return True

    def set_quick_warn_cb(self, w):
        bg = self.cuts_view.get_plot_decor('plot_bg')
        val_s = w.get_text().strip()
        bg.warn_y = None if len(val_s) == 0 else float(val_s)
        # note: necessary to get the warning line updated correctly
        self.cuts_view.update_resize()
        return True

    def set_quick_alert_cb(self, w):
        bg = self.cuts_view.get_plot_decor('plot_bg')
        val_s = w.get_text().strip()
        bg.alert_y = None if len(val_s) == 0 else float(val_s)
        # note: necessary to get the warning line updated correctly
        self.cuts_view.update_resize()
        return True

    def set_radius_cb(self, w):
        radius = float(w.get_text())
        self.cuts_radius = int(round(radius))
        self.cuts_box.radius = self.cuts_radius

        self.move_crosshair(self.fitsimage, self.cuts_box.x, self.cuts_box.y)
        return True

    def _format_cuts_label(self, lbl, plot_src):
        lim = plot_src.get_limits('data')
        y_max = lim[1][1]
        lbl.text = "{0:}: {1: .4g}".format(plot_src.name, y_max)

    def __str__(self):
        return 'crosshair'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Crosshair', package='ginga')
