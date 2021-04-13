# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``Histogram`` plots a histogram for a region drawn in the image, or for the
entire image.

**Plugin Type: Local**

``Histogram`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

Click and drag to define a region within the image that will be used to
calculate the histogram.  To take the histogram of the full image, click
the button in the UI labeled "Full Image".

.. note:: Depending on the size of the image, calculating the
          full histogram may take time.

If a new image is selected for the channel, the histogram plot will be
recalculated based on the current parameters with the new data.

Unless disabled in the settings file for the histogram plugin, a line of
simple statistics for the box is calculated and shown in a line below the
plot.

**UI Controls**

Three radio buttons at the bottom of the UI are used to control the
effects of the click/drag action:

* select "Move" to drag the region to a different location
* select "Draw" to draw a new region
* select "Edit" to edit the region

To make a log plot of the histogram, check the "Log Histogram" checkbox.
To plot by the full range of values in the image instead of by the range
within the cut values, uncheck the "Plot By Cuts" checkbox.

The "NumBins" parameter determines how many bins are used in calculating
the histogram.  Type a number in the box and press "Enter" to change the
default value.

**Cut Levels Convenience Controls**

Because a histogram is useful feedback for setting the cut levels,
controls are provided in the UI for setting the low and high cut levels
in the image, as well as for performing an auto cut levels, according to
the auto cut levels settings in the channel preferences.

You can set cut levels by clicking in the histogram plot:

* left click: set low cut
* middle click: reset (auto cut levels)
* right click: set high cut

In addition, you can dynamically adjust the gap between low and high cuts
by scrolling the wheel in the plot (i.e. the "width" of the histogram plot
curve).  This has the effect of increasing or decreasing the contrast
within the image.  The amount that is changed for each wheel click is set
by the plugin configuration file setting ``scroll_pct``.  The default is 10%.

**User Configuration**

"""
import numpy as np

from ginga.gw import Widgets
from ginga import GingaPlugin
from ginga import AutoCuts

try:
    from ginga.gw import Plot
    from ginga.util import plots
    have_mpl = True
except ImportError:
    have_mpl = False

__all__ = ['Histogram']


class Histogram(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Histogram, self).__init__(fv, fitsimage)

        self.layertag = 'histogram-canvas'
        self.histtag = None
        # If True, limits X axis to lo/hi cut levels
        self.xlimbycuts = True
        # percentage to adjust plotting X limits when xlimbycuts is True
        self.lim_adj_pct = 0.03
        self._split_sizes = [400, 500]

        # get Histogram preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Histogram')
        self.settings.add_defaults(draw_then_move=True, num_bins=2048,
                                   hist_color='aquamarine', show_stats=True,
                                   maxdigits=7, scroll_pct=0.10)
        self.settings.load(onError='silent')

        # Set up histogram control parameters
        self.histcolor = self.settings.get('hist_color', 'aquamarine')
        self.numbins = self.settings.get('num_bins', 2048)
        self.autocuts = AutoCuts.Histogram(self.logger)
        # percentage to adjust cuts gap when scrolling in histogram
        self.scroll_pct = self.settings.get('scroll_pct', 0.10)

        # for formatting statistics line
        self.show_stats = self.settings.get('show_stats', True)
        maxdigits = self.settings.get('maxdigits', 7)
        self.fmt_cell = '{:< %d.%dg}' % (maxdigits - 1, maxdigits // 2)

        self.dc = self.fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='cyan', linestyle='dash',
                            drawdims=True)
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.add_draw_mode('move', down=self.drag,
                             move=self.drag, up=self.update)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_surface(self.fitsimage)
        canvas.set_draw_mode('draw')
        self.canvas = canvas

        fitssettings = fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.get_setting(name).add_callback(
                'set', self.cutset_ext_cb, fitsimage)
        self.gui_up = False

    def build_gui(self, container):
        if not have_mpl:
            raise ImportError('Install matplotlib to use this plugin')

        top = Widgets.VBox()
        top.set_border_width(4)

        # Make the cuts plot
        box, sw, orientation = Widgets.get_oriented_box(container,
                                                        orientation=self.settings.get('orientation', None))
        box.set_border_width(4)
        box.set_spacing(2)

        paned = Widgets.Splitter(orientation=orientation)
        self.w.splitter = paned

        self.plot = plots.Plot(logger=self.logger,
                               width=400, height=400)
        ax = self.plot.add_axis()
        ax.grid(True)
        self.plot.add_callback('button-press', self.set_cut_by_click)
        self.plot.add_callback('scroll', self.adjust_cuts_scroll)
        w = Plot.PlotWidget(self.plot)
        self.plot.connect_ui()
        w.resize(400, 400)
        paned.add_widget(Widgets.hadjust(w, orientation))

        vbox = Widgets.VBox()
        vbox.set_border_width(2)

        # for statistics line
        self.w.stats1 = Widgets.Label('')
        vbox.add_widget(self.w.stats1)

        captions = (('Cut Low:', 'label', 'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High', 'entry',
                     'Cut Levels', 'button'),
                    ('Auto Levels', 'button'),
                    ('Log Histogram', 'checkbutton',
                     'Plot By Cuts', 'checkbutton'),
                    ('NumBins:', 'label', 'NumBins', 'entry'),
                    ('Full Image', 'button'),
                    )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.cut_levels.set_tooltip("Set cut levels manually")
        b.auto_levels.set_tooltip("Set cut levels by algorithm")
        b.cut_low.set_tooltip("Set low cut level (press Enter)")
        b.cut_high.set_tooltip("Set high cut level (press Enter)")
        b.log_histogram.set_tooltip("Use the log of the pixel values for the "
                                    "histogram (empty bins map to 10^-1)")
        b.plot_by_cuts.set_tooltip("Only show the part of the histogram "
                                   "between the cuts")
        b.numbins.set_tooltip("Number of bins for the histogram")
        b.full_image.set_tooltip("Use the full image for calculating the "
                                 "histogram")
        b.numbins.set_text(str(self.numbins))
        b.cut_low.add_callback('activated', lambda w: self.cut_levels())
        b.cut_high.add_callback('activated', lambda w: self.cut_levels())
        b.cut_levels.add_callback('activated', lambda w: self.cut_levels())
        b.auto_levels.add_callback('activated', lambda w: self.auto_levels())

        b.log_histogram.set_state(self.plot.logy)
        b.log_histogram.add_callback('activated', self.log_histogram_cb)
        b.plot_by_cuts.set_state(self.xlimbycuts)
        b.plot_by_cuts.add_callback('activated', self.plot_by_cuts_cb)
        b.numbins.add_callback('activated', lambda w: self.set_numbins_cb())
        b.full_image.add_callback('activated', lambda w: self.full_image_cb())

        fr = Widgets.Frame("Histogram")
        vbox.add_widget(w)
        fr.set_widget(vbox)
        box.add_widget(fr, stretch=0)
        paned.add_widget(sw)
        paned.set_sizes(self._split_sizes)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Move")
        btn1.set_state(mode == 'move')
        btn1.add_callback('activated',
                          lambda w, val: self.set_mode_cb('move', val))
        btn1.set_tooltip("Choose this to position box")
        self.w.btn_move = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback('activated',
                          lambda w, val: self.set_mode_cb('draw', val))
        btn2.set_tooltip("Choose this to draw a replacement box")
        self.w.btn_draw = btn2
        hbox.add_widget(btn2)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback('activated',
                          lambda w, val: self.set_mode_cb('edit', val))
        btn3.set_tooltip("Choose this to edit a box")
        self.w.btn_edit = btn3
        hbox.add_widget(btn3)

        if self.histtag is None:
            self.w.btn_move.set_enabled(False)
            self.w.btn_edit.set_enabled(False)

        hbox.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(paned, stretch=5)
        top.add_widget(hbox, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
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

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        self.plot.set_titles(rtitle="Histogram")

        # insert canvas, if not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add ruler layer
            p_canvas.add(self.canvas, tag=self.layertag)

        #self.canvas.delete_all_objects()
        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.fv.show_status("Draw a rectangle with the right mouse button")

    def stop(self):
        self.gui_up = False
        self._split_sizes = self.w.splitter.get_sizes()
        # remove the rect from the canvas
        ## try:
        ##     self.canvas.delete_object_by_tag(self.histtag)
        ## except Exception:
        ##     pass
        ##self.histtag = None

        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        self.fv.show_status("")

    def full_image_cb(self):
        canvas = self.canvas
        try:
            canvas.delete_object_by_tag(self.histtag)
        except Exception:
            pass

        image = self.fitsimage.get_vip()
        width, height = image.get_size()
        x1, y1, x2, y2 = 0, 0, width - 1, height - 1
        tag = canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                           color='cyan',
                                           linestyle='dash'))
        self.draw_cb(canvas, tag)

    def get_data(self, image, x1, y1, x2, y2, z=0):
        tup = image.cutout_adjust(x1, y1, x2 + 1, y2 + 1, z=z)
        return tup[0]

    def histogram(self, image, x1, y1, x2, y2, z=None, pct=1.0, numbins=2048):
        self.logger.warning("This call will be deprecated soon. "
                            "Use get_data() and histogram_data().")
        data_np = self.get_data(image, x1, y1, x2, y2, z=z)
        return self.histogram_data(data_np, pct=pct, numbins=numbins)

    def histogram_data(self, data, pct=1.0, numbins=2048):
        return self.autocuts.calc_histogram(data, pct=pct, numbins=numbins)

    def redo(self):
        if self.histtag is None:
            return

        obj = self.canvas.get_object_by_tag(self.histtag)
        if obj.kind != 'compound':
            return True
        bbox = obj.objects[0]

        # Do histogram on the points within the rect
        image = self.fitsimage.get_vip()
        self.plot.clear()

        numbins = self.numbins

        depth = image.get_depth()
        if depth != 3:
            data_np = self.get_data(image, int(bbox.x1), int(bbox.y1),
                                    int(bbox.x2), int(bbox.y2))
            res = self.histogram_data(data_np, pct=1.0, numbins=numbins)
            # used with 'steps-post' drawstyle, this x and y assignment
            # gives correct histogram-steps
            x = res.bins
            y = np.append(res.dist, res.dist[-1])
            ymax = y.max()
            if self.plot.logy:
                y = np.choose(y > 0, (.1, y))
            self.plot.plot(x, y, xtitle="Pixel value", ytitle="Number",
                           title="Pixel Value Distribution",
                           color='blue', alpha=1.0, drawstyle='steps-post')
        else:
            colors = ('red', 'green', 'blue')
            ymax = 0
            for z in range(depth):
                data_np = self.get_data(image, int(bbox.x1), int(bbox.y1),
                                        int(bbox.x2), int(bbox.y2), z=z)
                res = self.histogram_data(data_np, pct=1.0, numbins=numbins)
                # used with 'steps-post' drawstyle, this x and y assignment
                # gives correct histogram-steps
                x = res.bins
                y = np.append(res.dist, res.dist[-1])
                ymax = max(ymax, y.max())
                if self.plot.logy:
                    y = np.choose(y > 0, (.1, y))
                self.plot.plot(x, y, xtitle="Pixel value", ytitle="Number",
                               title="Pixel Value Distribution",
                               color=colors[z], alpha=0.33,
                               drawstyle='steps-post')

        # show cut levels
        loval, hival = self.fitsimage.get_cut_levels()
        self.loline = self.plot.ax.axvline(loval, 0.0, 0.99,
                                           linestyle='-', color='brown')
        self.hiline = self.plot.ax.axvline(hival, 0.0, 0.99,
                                           linestyle='-', color='green')
        if self.xlimbycuts:
            # user wants "plot by cuts"--adjust plot limits to show only area
            # between locut and high cut "plus a little" so that lo and hi cut
            # markers are shown
            incr = np.fabs(self.lim_adj_pct * (hival - loval))
            self.plot.ax.set_xlim(loval - incr, hival + incr)

        # Make x axis labels a little more readable
        ## lbls = self.plot.ax.xaxis.get_ticklabels()
        ## for lbl in lbls:
        ##     lbl.set(rotation=45, horizontalalignment='right')

        self.w.cut_low.set_text(str(loval))
        self.w.cut_high.set_text(str(hival))
        self.plot.fig.canvas.draw()

        if self.show_stats:
            # calculate statistics on finite elements in box
            i = np.isfinite(data_np)
            if np.any(i):
                maxval = np.max(data_np[i])
                minval = np.min(data_np[i])
                meanval = np.mean(data_np[i])
                rmsval = np.sqrt(np.mean(np.square(data_np[i])))
                fmt_stat = "  Min: %s  Max: %s  Mean: %s  Rms: %s" % (
                    self.fmt_cell, self.fmt_cell, self.fmt_cell, self.fmt_cell)
                sum_text = fmt_stat.format(minval, maxval, meanval, rmsval)
            else:
                sum_text = "No finite data elements in cutout"
            self.w.stats1.set_text(sum_text)

        self.fv.show_status("Click or drag left mouse button to move region")
        return True

    def update(self, canvas, event, data_x, data_y, viewer):

        obj = self.canvas.get_object_by_tag(self.histtag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = bbox.x1 + dx, bbox.y1 + dy, bbox.x2 + dx, bbox.y2 + dy

        try:
            canvas.delete_object_by_tag(self.histtag)
        except Exception:
            pass

        tag = canvas.add(self.dc.Rectangle(
            x1, y1, x2, y2, color='cyan', linestyle='dash'))

        self.draw_cb(canvas, tag)
        return True

    def drag(self, canvas, event, data_x, data_y, viewer):

        obj = self.canvas.get_object_by_tag(self.histtag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = bbox.x1 + dx, bbox.y1 + dy, bbox.x2 + dx, bbox.y2 + dy

        if obj.kind == 'compound':
            try:
                canvas.delete_object_by_tag(self.histtag)
            except Exception:
                pass

            self.histtag = canvas.add(self.dc.Rectangle(
                x1, y1, x2, y2, color='cyan', linestyle='dash'))
        else:
            bbox.x1, bbox.y1, bbox.x2, bbox.y2 = x1, y1, x2, y2
            canvas.redraw(whence=3)

        return True

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        if obj.kind != 'rectangle':
            return True
        canvas.delete_object_by_tag(tag)

        if self.histtag:
            try:
                canvas.delete_object_by_tag(self.histtag)
            except Exception:
                pass

        x1, y1, x2, y2 = obj.get_llur()

        tag = canvas.add(self.dc.CompoundObject(
            self.dc.Rectangle(x1, y1, x2, y2,
                              color=self.histcolor),
            self.dc.Text(x1, y2, "Histogram",
                         color=self.histcolor)))
        self.histtag = tag

        self.w.btn_move.set_enabled(True)
        self.w.btn_edit.set_enabled(True)

        move_flag = self.settings.get('draw_then_move', True)
        if move_flag:
            self.set_mode('move')

        return self.redo()

    def edit_cb(self, canvas, obj):
        if obj.kind != 'rectangle':
            return True

        # Get the compound object that sits on the canvas.
        # Make sure edited rectangle was our histogram rectangle.
        c_obj = self.canvas.get_object_by_tag(self.histtag)
        if ((c_obj.kind != 'compound') or (len(c_obj.objects) < 2) or
                (c_obj.objects[0] != obj)):
            return False

        # reposition other elements to match
        x1, y1, x2, y2 = obj.get_llur()
        text = c_obj.objects[1]
        text.x, text.y = x1, y2 + 4
        self.fitsimage.redraw(whence=3)

        return self.redo()

    def cut_levels(self):
        reslvls = None

        try:
            loval = float(self.w.cut_low.get_text())
            hival = float(self.w.cut_high.get_text())

            reslvls = self.fitsimage.cut_levels(loval, hival)

        except Exception as e:
            errmsg = 'Error cutting levels: {0}'.format(str(e))
            self.fv.show_status(errmsg)
            self.logger.error(errmsg)

        else:
            if self.xlimbycuts:
                self.redo()

        return reslvls

    def auto_levels(self):
        self.fitsimage.auto_levels()

    def set_cut_by_click(self, plot, event):
        """Set cut levels by a mouse click in the histogram plot:
        left: set low cut
        middle: reset (auto cuts)
        right: set high cut
        """
        data_x = event.xdata
        lo, hi = self.fitsimage.get_cut_levels()
        if event.button == 1:
            lo = data_x
            self.fitsimage.cut_levels(lo, hi)
        elif event.button == 2:
            self.fitsimage.auto_levels()
        elif event.button == 3:
            hi = data_x
            self.fitsimage.cut_levels(lo, hi)

    def adjust_cuts_scroll(self, plot, event):
        """Adjust the width of the histogram by scrolling.
        """
        bm = self.fitsimage.get_bindings()
        pct = -self.scroll_pct
        if event.step > 0:
            pct = -pct
        bm.cut_pct(self.fitsimage, pct)

    def cutset_ext_cb(self, setting, value, fitsimage):
        if not self.gui_up:
            return

        t_ = fitsimage.get_settings()
        loval, hival = t_['cuts']

        try:
            self.loline.remove()
            self.hiline.remove()
        except Exception:
            pass
        self.loline = self.plot.ax.axvline(loval, 0.0, 0.99,
                                           linestyle='-', color='black')
        self.hiline = self.plot.ax.axvline(hival, 0.0, 0.99,
                                           linestyle='-', color='black')
        self.w.cut_low.set_text(str(loval))
        self.w.cut_high.set_text(str(hival))
        #self.plot.fig.canvas.draw()
        self.redo()

    def set_numbins_cb(self):
        self.numbins = int(self.w.numbins.get_text())
        self.redo()

    def log_histogram_cb(self, w, val):
        self.plot.logy = val
        if (self.histtag is not None) and self.gui_up:
            # self.histtag is None means no data is loaded yet
            self.redo()

    def plot_by_cuts_cb(self, w, val):
        self.xlimbycuts = val
        if (self.histtag is not None) and self.gui_up:
            # self.histtag is None means no data is loaded yet
            self.redo()

    def edit_select_box(self):
        if self.histtag is not None:
            obj = self.canvas.get_object_by_tag(self.histtag)
            if obj.kind != 'compound':
                return True
            # drill down to reference shape
            bbox = obj.objects[0]
            self.canvas.edit_select(bbox)
        else:
            self.canvas.clear_selected()
        self.canvas.update_canvas()

    def set_mode_cb(self, mode, tf):
        """Called when one of the Move/Draw/Edit radio buttons is selected."""
        if tf:
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_select_box()
        return True

    def set_mode(self, mode):
        self.canvas.set_draw_mode(mode)
        self.w.btn_move.set_state(mode == 'move')
        self.w.btn_draw.set_state(mode == 'draw')
        self.w.btn_edit.set_state(mode == 'edit')

    def __str__(self):
        return 'histogram'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Histogram', package='ginga')

# END
