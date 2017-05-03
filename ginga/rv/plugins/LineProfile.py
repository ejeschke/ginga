#
# LineProfile.py -- LineProfile plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.gw import Widgets, Plot
from ginga.util import plots

import numpy as np


class LineProfile(GingaPlugin.LocalPlugin):
    """
    LineProfile
    ===========
    A plugin to graph the flux along a straight line bisecting a cube.

    Plugin Type: Local
    ------------------
    LineProfile is a local plugin, which means it is associated with a
    channel.  An instance can be opened for each channel.

    Usage
    -----
    1. Select an axis and pick a point using the cursor.
    2. Left-click to mark position.
    3. Use MultiDim to change step values of axes.
    """
    def __init__(self, fv, fitsimage):
        super(LineProfile, self).__init__(fv, fitsimage)

        self.image = None
        self.layertag = 'lineprofile-canvas'
        self.raster_file = False
        self.pan2mark = False
        self.wd = None
        self.ht = None
        self.selected_axis = None
        self.hbox_axes = None

        self.dc = self.fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.set_callback('cursor-down', self.btndown_cb)
        canvas.set_callback('cursor-up', self.update)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        # For "marks" feature
        self.mark_radius = 10
        self.mark_style = 'cross'
        self.mark_color = 'purple'
        self.select_color = 'cyan'
        self.marks = ['None']
        self.mark_index = 0
        self.mark_selected = None
        self.tw = None
        self.mark_data_x = [None]
        self.mark_data_y = [None]
        self.y_lbl = ''
        self.x_lbl = ''

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_margins(4, 4, 4, 4)
        vbox.set_spacing(2)

        self.plot = plots.Plot(logger=self.logger,
                               width=400, height=300)
        ax = self.plot.add_axis()
        ax.grid(False)
        self._ax2 = self.plot.ax.twiny()

        w = Plot.PlotWidget(self.plot)
        w.resize(400, 300)
        vbox.add_widget(w, stretch=0)

        fr = Widgets.Frame("Axes controls")
        self.hbox_axes = Widgets.HBox()
        self.hbox_axes.set_border_width(4)
        self.hbox_axes.set_spacing(1)
        fr.set_widget(self.hbox_axes)

        vbox.add_widget(fr, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        # control for selecting a mark
        cbox2 = Widgets.ComboBox()
        for tag in self.marks:
            cbox2.append_text(tag)
        if self.mark_selected is None:
            cbox2.set_index(0)
        else:
            cbox2.show_text(self.mark_selected)
        cbox2.add_callback('activated', self.mark_select_cb)
        self.w.marks = cbox2
        cbox2.set_tooltip("Select a mark")
        btns.add_widget(cbox2, stretch=0)

        btn1 = Widgets.CheckBox("Pan to mark")
        btn1.set_state(self.pan2mark)
        btn1.add_callback('activated', self.pan2mark_cb)
        btn1.set_tooltip("Pan follows selected mark")
        btns.add_widget(btn1)
        btns.add_widget(Widgets.Label(''), stretch=1)

        btn2 = Widgets.Button("Delete")
        self.del_btn = btn2
        btn2.add_callback('activated', lambda w: self.clear_mark_cb())
        btn2.set_tooltip("Delete selected mark")
        btn2.set_enabled(False)
        btns.add_widget(btn2, stretch=0)

        btn3 = Widgets.Button("Delete All")
        self.del_all_btn = btn3
        btn3.add_callback('activated', lambda w: self.clear_all())
        btn3.set_tooltip("Clear all marks")
        btn3.set_enabled(False)
        btns.add_widget(btn3, stretch=0)

        vbox2 = Widgets.VBox()
        vbox2.add_widget(btns, stretch=0)
        vbox2.add_widget(Widgets.Label(''), stretch=1)

        fr = Widgets.Frame("Mark controls")
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=1)

        # scroll bars will allow lots of content to be accessed
        top.add_widget(sw, stretch=1)

        # A button box that is always visible at the bottom
        btns = Widgets.HBox()
        btns.set_spacing(3)

        # Add a close button for the convenience of the user
        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        # Add our GUI to the container
        container.add_widget(top, stretch=1)
        self.gui_up = True

        self.build_axes()

    def build_axes(self):
        if (not self.gui_up) or (self.hbox_axes is None):
            return
        self.hbox_axes.remove_all()
        self.selected_axis = None
        self.clear_plot()

        image = self.fitsimage.get_image()
        if image is not None:
            # Add Checkbox widgets
            # `image.naxispath` returns only mdim axes
            maxi = len(image.naxispath) + 2
            for i in range(1, maxi + 1):
                chkbox = Widgets.CheckBox('NAXIS{}'.format(i))
                self.hbox_axes.add_widget(chkbox)

                # Disable axes for 2D images
                if len(image.naxispath) <= 0:
                    chkbox.set_enabled(False)
                else:
                    # Add callback
                    self.axes_callback_handler(chkbox, i)

                    # Auto-check a default box to prevent error messages
                    if i == maxi:
                        chkbox.set_state(True)
            # Add filler
            self.hbox_axes.add_widget(Widgets.Label(''), stretch=1)
        else:
            self.hbox_axes.add_widget(Widgets.Label('No NAXIS info'))

    def axes_callback_handler(self, chkbox, pos):
        chkbox.add_callback('activated',
                            lambda w, tf: self.axis_toggle_cb(w, tf, pos))

    def axis_toggle_cb(self, w, tf, pos):
        children = self.hbox_axes.get_children()

        # Deactivate previously selected axis
        if self.selected_axis is not None:
            children[self.selected_axis-1].set_state(False)

        # Check if the old axis has been clicked
        if pos == self.selected_axis:
            self.selected_axis = None
            self.clear_plot()
        else:
            self.selected_axis = pos
            children[pos-1].set_state(tf)
            self.redraw_mark()

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        self.gui_up = False
        return True

    def start(self):
        # insert layer if it is not already
        try:
            self.fitsimage.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        self.canvas.ui_set_active(True)
        self.redo()

    def stop(self):
        # Don't hang on to current image
        self.image = None
        self.canvas.ui_set_active(False)
        try:
            self.fitsimage.delete_object_by_tag(self.layertag)
        except:
            pass

    def redo(self):
        # Get image being shown
        self.image = self.fitsimage.get_image()
        if self.image is None:
            return

        self.build_axes()

        self.wd, self.ht = self.image.get_size()

        self.redraw_mark()

    def _plot(self, mark=None):
        # Transpose array for easier slicing
        mddata = self.image.get_mddata().T
        naxes = mddata.ndim

        if not self.selected_axis:
            return

        plot_x_axis_data = self.get_axis(self.selected_axis)
        if plot_x_axis_data is None:
            # image may lack the required keywords, or some trouble
            # building the axis
            return
        slice_obj = self._slice(naxes, mk=mark)
        plot_y_axis_data = mddata[slice_obj]

        # If few enough data points, add marker
        if len(plot_y_axis_data) <= 10:
            marker = 'o'
        else:
            marker = None

        # https://github.com/matplotlib/matplotlib/issues/3633/
        ax2 = self._ax2
        ax2.patch.set_visible(False)

        self.clear_plot()
        self.plot.plot(plot_x_axis_data, plot_y_axis_data,
                       xtitle=self.x_lbl, ytitle=self.y_lbl, marker=marker)

        # Top axis to show pixel location across X
        ax2.cla()
        xx1, xx2 = self.plot.ax.get_xlim()
        ax2.set_xlim((xx1 - self._crval) / self._cdelt,
                     (xx2 - self._crval) / self._cdelt)
        ax2.set_xlabel('Index')
        self.plot.draw()

    def _slice(self, naxes, mk):
        # Build N-dim slice
        slice_obj = [0] * naxes
        i_sel = self.selected_axis - 1

        # For axes 1 and 2
        if mk is not None:
            slice_obj[0] = int(round(self.mark_data_x[mk]))
            slice_obj[1] = int(round(self.mark_data_y[mk]))

        # For axis > 3
        for i in range(2, naxes):
            if i != i_sel:
                slice_obj[i] = 0  # int(round(self.image.revnaxis[i-2] + 1))

        # Slice selected axis
        slice_obj[i_sel] = slice(None, None, None)

        return slice_obj

    def get_axis(self, i):
        try:
            naxis_s = 'NAXIS{}'.format(i)
            naxis_i = self.image.get_keyword(naxis_s)
            self.x_lbl = self.image.get_keyword('CTYPE{}'.format(i), naxis_s)

            try:
                kwds = ['CRVAL{}'.format(i), 'CDELT{}'.format(i)]
                crval_i, cdelt_i = self.image.get_keywords_list(*kwds)
            except KeyError as e:
                self.logger.error("Missing FITS keyword: {}".format(str(e)))
                crval_i = 0
                cdelt_i = 1

            axis = crval_i + np.arange(naxis_i) * cdelt_i
            self._crval = crval_i
            self._cdelt = cdelt_i

            units = self.image.get_keyword('CUNIT{}'.format(i), None)
            if units is not None:
                self.x_lbl += (' ({})'.format(units))

            # Get pixel value info from header
            self.y_lbl = self.image.get_keyword('BTYPE', 'Flux')
            bunit = self.image.get_keyword('BUNIT', None)
            if bunit is not None:
                self.y_lbl += (' ({})'.format(bunit))

        except Exception as e:
            errmsg = "Error loading axis {}: {}".format(i, str(e))
            self.logger.error(errmsg)
            self.fv.show_error(errmsg)

        else:
            return axis

    def clear_plot(self):
        self.plot.clear()
        self.plot.fig.canvas.draw()

    # MARK FEATURE LOGIC #

    def btndown_cb(self, canvas, event, data_x, data_y):
        # Disable plotting for 2D images
        image = self.fitsimage.get_image()
        if len(image.naxispath) <= 0:
            return

        # Exclude points outside boundaries
        if not 0 <= data_x < self.wd or not 0 <= data_y < self.ht:
            self.clear_plot()
            return

        if not self.mark_selected:
            self.mark_data_x.append(data_x)
            self.mark_data_y.append(data_y)
            self.add_mark(data_x, data_y)

            self.del_btn.set_enabled(True)
            self.del_all_btn.set_enabled(True)
        return True

    def update(self, canvas, event, data_x, data_y):
        tag = self.mark_selected
        if tag is None:
            return
        idx = int(tag.strip('mark'))
        obj = self.canvas.get_object_by_tag(tag)
        obj.move_to(data_x+5, data_y)

        canvas.redraw(whence=3)

        # Exclude points outside boundaries
        if not 0 <= data_x < self.wd or not 0 <= data_y < self.ht:
            self.clear_plot()
            # Clear mark data
            self.mark_data_x[idx] = None
            self.mark_data_y[idx] = None
            return

        self.mark_data_x[idx] = data_x
        self.mark_data_y[idx] = data_y

        self.redraw_mark()
        return True

    def add_mark(self, data_x, data_y, radius=None, color=None, style=None):
        if not radius:
            radius = self.mark_radius
        if not color:
            color = self.mark_color
        if not style:
            style = self.mark_style

        self.logger.debug("Setting mark at {},{}".format(data_x, data_y))
        self.mark_index += 1
        tag = 'mark{}'.format(self.mark_index)
        tag = self.canvas.add(self.dc.CompoundObject(
            self.dc.Point(data_x, data_y, self.mark_radius,
                          style=style, color=color,
                          linestyle='solid'),
            self.dc.Text(data_x + 10, data_y, "{}".format(self.mark_index),
                         color=color)),
                              tag=tag)
        self.marks.append(tag)
        self.w.marks.append_text(tag)
        self.select_mark(tag, pan=False)

    def select_mark(self, tag, pan=True):
        # deselect the current selected mark, if there is one
        if self.mark_selected is not None:
            try:
                obj = self.canvas.get_object_by_tag(self.mark_selected)
                obj.setAttrAll(color=self.mark_color)
            except:
                # old object may have been deleted
                pass

        self.mark_selected = tag
        if tag is None:
            self.w.marks.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.marks.show_text(tag)
        obj = self.canvas.get_object_by_tag(tag)
        obj.setAttrAll(color=self.select_color)
        if self.pan2mark and pan:
            self.fitsimage.panset_xy(obj.objects[0].x, obj.objects[0].y)
        self.canvas.redraw(whence=3)

        self.redraw_mark()

    def redraw_mark(self):
        if self.mark_selected is None:
            return
        idx = int(self.mark_selected.strip('mark'))
        self._plot(mark=idx)

    def mark_select_cb(self, w, index):
        tag = self.marks[index]
        if index == 0:
            tag = None
            self.clear_plot()
            self.del_btn.set_enabled(False)
        else:
            self.del_btn.set_enabled(True)

        self.select_mark(tag)

    def pan2mark_cb(self, w, val):
        self.pan2mark = val

    def clear_mark_cb(self):
        tag = self.mark_selected
        if tag is None:
            return
        idx = int(tag.strip('mark'))
        self.canvas.delete_object_by_tag(tag)
        self.w.marks.delete_alpha(tag)
        self.marks.remove(tag)
        self.w.marks.set_index(0)
        self.mark_selected = None

        self.clear_plot()

        self.mark_data_x[idx] = None
        self.mark_data_y[idx] = None
        self.del_btn.set_enabled(False)
        if len(self.marks) == 1:
            self.del_all_btn.set_enabled(False)

    def clear_all(self):
        self.canvas.delete_all_objects()
        for name in self.marks:
            self.w.marks.delete_alpha(name)
        self.marks = ['None']
        self.w.marks.append_text('None')
        self.w.marks.set_index(0)
        self.mark_index = 0
        self.mark_selected = None
        self.mark_data_x = [None]
        self.mark_data_y = [None]

        self.clear_plot()

        self.del_btn.set_enabled(False)
        self.del_all_btn.set_enabled(False)

    def __str__(self):
        return 'lineprofile'
