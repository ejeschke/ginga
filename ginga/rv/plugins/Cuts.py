# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
A plugin for generating a plot of the values along a line or path.

**Plugin Type: Local**

``Cuts`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**

``Cuts`` plots a simple graph of pixel values vs. index for a line drawn
through the image. Multiple cuts can be plotted.

There are four kinds of cuts available: line, path, freepath and
beziercurve:

* The "line" cut is a straight line between two points.
* The "path" cut is drawn like an open polygon, with straight segments
  in-between.
* The "freepath" cut is like a path cut, but drawn using a free-form
  stroke following the cursor movement.
* The "beziercurve" path is a cubic Bezier curve.

If a new image is added to the channel while the plugin is active, it
will update with the new calculated cuts on the new image.

If the "enable slit" setting is enabled, this plugin will also allow
slit image functionality (for multidimensional images) via a "Slit" tab.
In the tab UI, select one axis from the "Axes" list and draw a line.
This will create a 2D image that assumes the first two axes are
spatial and index the data along the selected axis.
Much like ``Cuts``, you can view the other slit images using the cut
selection drop down box.

**Drawing Cuts**

The "New Cut Type" menu let you choose what kind of cut you are going to draw.

Choose "New Cut" from the "Cut" dropdown menu if you want to draw a
new cut. Otherwise, if a particular named cut is selected then that
will be replaced by any newly drawn cut.

While drawing a path or beziercurve cut, press 'v' to add a vertex,
or 'z' to remove the last vertex added.

**Keyboard Shortcuts**

While hovering the cursor, press 'h' for a full horizontal cut and
'j' for a full vertical cut.

**Deleting Cuts**

To delete a cut, select its name from the "Cut" dropdown and click the
"Delete" button.  To delete all cuts, press "Delete All".

**Editing Cuts**

Using the edit canvas function, it is possible to add new vertices to
an existing path and to move vertices around.   Click the "Edit"
radio button to put the canvas in edit mode.  If a cut is not
automatically selected, you can now select the line, path, or curve by
clicking on it, which should enable the control points at the ends or
vertices -- you can drag these around.  To add a new vertex to a path,
hover the cursor carefully on the line where you want the new vertex
and press 'v'.  To get rid of a vertex, hover the cursor over it and
press 'z'.

You will notice one extra control point for most objects, which has
a center of a different color -- this is a movement control point for
moving the entire object around the image when in edit mode.

You can also select "Move" to just move a cut unchanged.

**Changing Width of Cuts**

The width of 'line' cuts can be changed using the "Width Type" menu:

* "none" indicates a cut of zero radius; i.e., only showing the pixel
  values along the line
* "x" will plot the sum of values along the X axis orthogonal to the cut.
* "y" will plot the sum of values along the Y axis orthogonal to the cut.
* "perpendicular" will plot the sum of values along an axis perpendicular
  to the cut.

The "Width radius" controls the width of the orthogonal summation by
an amount on either side of the cut -- 1 would be 3 pixels, 2 would be 5
pixels, etc.

**Saving Cuts**

Use the "Save" button to save the ``Cuts`` plot as as image and
data as a Numpy compressed archive.

**Copying Cuts**

To copy a cut, select its name from the "Cut" dropdown and click the
"Copy Cut" button. A new cut will be created from it. You can then manipulate
the new cut independently.

**User Configuration**

"""
import numpy as np

from ginga.gw import Widgets
from ginga import GingaPlugin, colors
from ginga.canvas.coordmap import OffsetMapper

try:
    from ginga.gw import Plot
    from ginga.util import plots
    have_mpl = True
except ImportError:
    have_mpl = False

__all__ = ['Cuts']

# default cut colors
cut_colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink',
              'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']


class Cuts(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Cuts, self).__init__(fv, fitsimage)

        self.layertag = 'cuts-canvas'
        self._new_cut = 'New Cut'
        self.cutstag = self._new_cut
        self.tags = [self._new_cut]
        self.count = 0
        self.cuttypes = ['line', 'path', 'freepath', 'beziercurve']
        self.cuttype = 'line'
        self.save_enabled = False
        # for 3D Slit functionality
        self.transpose_enabled = False
        self.selected_axis = None
        self.hbox_axes = None
        self._split_sizes = [400, 500]

        # For collecting data orthogonal to the cut
        self.widthtypes = ['none', 'x', 'y', 'perpendicular']
        self.widthtype = 'none'
        self.width_radius = 5
        self.tine_spacing_px = 100

        # get Cuts preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Cuts')
        self.settings.add_defaults(select_new_cut=True, draw_then_move=True,
                                   label_cuts=True, colors=cut_colors,
                                   drag_update=False,
                                   show_cuts_legend=False, enable_slit=False)
        self.settings.load(onError='silent')
        self.colors = self.settings.get('colors', cut_colors)

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('line', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.add_draw_mode('move', down=self.buttondown_cb,
                             move=self.motion_cb, up=self.buttonup_cb,
                             key=self.keydown)
        canvas.set_draw_mode('draw')
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        self.use_slit = self.settings.get('enable_slit', False)
        self.cuts_image = None

        self.gui_up = False

    def build_gui(self, container):
        if not have_mpl:
            raise ImportError('Install matplotlib to use this plugin')

        top = Widgets.VBox()
        top.set_border_width(4)

        # Make the cuts plot
        box, sw, orientation = Widgets.get_oriented_box(container,
                                                        orientation=self.settings.get('orientation', None))
        box.set_margins(4, 4, 4, 4)
        box.set_spacing(2)

        paned = Widgets.Splitter(orientation=orientation)
        self.w.splitter = paned

        # Add Tab Widget
        nb = Widgets.TabWidget(tabpos='top')
        paned.add_widget(Widgets.hadjust(nb, orientation))

        self.cuts_plot = plots.CutsPlot(logger=self.logger,
                                        width=400, height=400)
        self.plot = Plot.PlotWidget(self.cuts_plot)
        self.plot.resize(400, 400)
        ax = self.cuts_plot.add_axis()
        ax.grid(True)

        self.slit_plot = plots.Plot(logger=self.logger,
                                    width=400, height=400)
        self.slit_plot.add_axis(facecolor='black')
        self.plot2 = Plot.PlotWidget(self.slit_plot)
        self.plot2.resize(400, 400)

        captions = (('Cut:', 'label', 'Cut', 'combobox',
                     'New Cut Type:', 'label', 'Cut Type', 'combobox'),
                    ('Delete Cut', 'button', 'Delete All', 'button'),
                    ('Save', 'button', 'Copy Cut', 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        # control for selecting a cut
        combobox = b.cut
        for tag in self.tags:
            combobox.append_text(tag)
        combobox.show_text(self.cutstag)
        combobox.add_callback('activated', self.cut_select_cb)
        self.w.cuts = combobox
        combobox.set_tooltip("Select a cut to redraw or delete")

        # control for selecting cut type
        combobox = b.cut_type
        for cuttype in self.cuttypes:
            combobox.append_text(cuttype)
        self.w.cuts_type = combobox
        index = self.cuttypes.index(self.cuttype)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_cutsdrawtype_cb)
        combobox.set_tooltip("Choose the cut type to draw")

        self.save_cuts = b.save
        self.save_cuts.set_tooltip("Save cuts plot and data")
        self.save_cuts.add_callback('activated',
                                    lambda w: self.save_cb(mode='cuts'))
        self.save_cuts.set_enabled(self.save_enabled)

        btn = b.copy_cut
        btn.add_callback('activated', self.copy_cut_cb)
        btn.set_tooltip("Copy selected cut")

        btn = b.delete_cut
        btn.add_callback('activated', self.delete_cut_cb)
        btn.set_tooltip("Delete selected cut")

        btn = b.delete_all
        btn.add_callback('activated', self.delete_all_cb)
        btn.set_tooltip("Clear all cuts")

        fr = Widgets.Frame("Cuts")
        fr.set_widget(w)

        box.add_widget(fr, stretch=0)

        exp = Widgets.Expander("Cut Width")

        captions = (('Width Type:', 'label', 'Width Type', 'combobox',
                     'Width radius:', 'label', 'Width radius', 'spinbutton'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        # control for selecting width cut type
        combobox = b.width_type
        for atype in self.widthtypes:
            combobox.append_text(atype)
        index = self.widthtypes.index(self.widthtype)
        combobox.set_index(index)
        combobox.add_callback('activated', self.set_width_type_cb)
        combobox.set_tooltip("Direction of summation orthogonal to cut")

        sb = b.width_radius
        sb.add_callback('value-changed', self.width_radius_changed_cb)
        sb.set_tooltip("Radius of cut width")
        sb.set_limits(1, 100)
        sb.set_value(self.width_radius)

        fr = Widgets.Frame()
        fr.set_widget(w)
        exp.set_widget(fr)

        box.add_widget(exp, stretch=0)
        box.add_widget(Widgets.Label(''), stretch=1)
        paned.add_widget(sw)
        paned.set_sizes(self._split_sizes)

        top.add_widget(paned, stretch=5)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Move")
        btn1.set_state(mode == 'move')
        btn1.add_callback('activated',
                          lambda w, val: self.set_mode_cb('move', val))
        btn1.set_tooltip("Choose this to position cuts")
        self.w.btn_move = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback('activated',
                          lambda w, val: self.set_mode_cb('draw', val))
        btn2.set_tooltip("Choose this to draw a new or replacement cut")
        self.w.btn_draw = btn2
        hbox.add_widget(btn2)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback('activated',
                          lambda w, val: self.set_mode_cb('edit', val))
        btn3.set_tooltip("Choose this to edit a cut")
        self.w.btn_edit = btn3
        hbox.add_widget(btn3)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(hbox, stretch=0)

        # Add Cuts plot to its tab
        vbox_cuts = Widgets.VBox()
        vbox_cuts.add_widget(self.plot, stretch=1)
        nb.add_widget(vbox_cuts, title="Cuts")

        captions = (("Enable Slit", 'checkbutton',
                     "Transpose Plot", 'checkbutton', "Save", 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        def chg_enable_slit(w, val):
            self.use_slit = val
            if val:
                self.build_axes()
            return True
        b.enable_slit.set_state(self.use_slit)
        b.enable_slit.set_tooltip("Enable the slit function")
        b.enable_slit.add_callback('activated', chg_enable_slit)

        self.t_btn = b.transpose_plot
        self.t_btn.set_tooltip("Flip the plot")
        self.t_btn.set_state(self.transpose_enabled)
        self.t_btn.add_callback('activated', self.transpose_plot)

        self.save_slit = b.save
        self.save_slit.set_tooltip("Save slit plot and data")
        self.save_slit.add_callback('activated',
                                    lambda w: self.save_cb(mode='slit'))
        self.save_slit.set_enabled(self.save_enabled)

        # Add frame to hold the slit controls
        fr = Widgets.Frame("Axes controls")
        self.hbox_axes = Widgets.HBox()
        self.hbox_axes.set_border_width(4)
        self.hbox_axes.set_spacing(1)
        fr.set_widget(self.hbox_axes)

        # Add Slit plot and controls to its tab
        vbox_slit = Widgets.VBox()
        vbox_slit.add_widget(self.plot2, stretch=1)
        vbox_slit.add_widget(w)
        vbox_slit.add_widget(fr)
        nb.add_widget(vbox_slit, title="Slit")

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

        self.select_cut(self.cutstag)
        self.gui_up = True

        if self.use_slit:
            self.build_axes()

    def build_axes(self):
        self.selected_axis = None
        if (not self.gui_up) or (self.hbox_axes is None):
            return
        self.hbox_axes.remove_all()
        image = self.fitsimage.get_image()
        if image is not None:
            # Add Checkbox widgets
            # `image.naxispath` returns only mdim axes
            for i in range(1, len(image.naxispath) + 3):
                chkbox = Widgets.CheckBox('NAXIS%d' % i)
                self.hbox_axes.add_widget(chkbox)

                # Disable axes 1,2
                if i < 3:
                    chkbox.set_enabled(False)
                    continue

                # Add callback
                self.axes_callback_handler(chkbox, i)

            self.redraw_slit('clear')

    def axes_callback_handler(self, chkbox, pos):
        chkbox.add_callback('activated',
                            lambda w, tf: self.axis_toggle_cb(w, tf, pos))

    def select_cut(self, tag):
        self.cutstag = tag
        self.w.cuts.show_text(tag)

        if (tag == self._new_cut) or len(self.tags) < 2:
            self.w.copy_cut.set_enabled(False)
            self.w.delete_cut.set_enabled(False)

            self.w.btn_move.set_enabled(False)
            self.w.btn_edit.set_enabled(False)
            self.set_mode('draw')

            if self.use_slit:
                self.redraw_slit('clear')
        else:
            self.w.copy_cut.set_enabled(True)
            self.w.delete_cut.set_enabled(True)

            self.w.btn_move.set_enabled(True)
            self.w.btn_edit.set_enabled(True)

            if self.w.btn_edit.get_state():
                self.edit_select_cuts()

            if self.use_slit:
                self._plot_slit()

    def cut_select_cb(self, w, index):
        tag = self.tags[index]
        self.select_cut(tag)

    def set_cutsdrawtype_cb(self, w, index):
        self.cuttype = self.cuttypes[index]
        self.canvas.set_drawtype(self.cuttype, color='cyan', linestyle='dash')

    def copy_cut_cb(self, w):
        old_tag = self.cutstag
        if old_tag == self._new_cut:  # Can only copy existing cut
            return

        old_obj = self.canvas.get_object_by_tag(old_tag)

        new_index = self._get_new_count()
        new_tag = "cuts{}".format(new_index)
        new_obj = old_obj.objects[0].copy()
        new_obj.move_delta_pt((20, 20))
        new_cut = self._create_cut_obj(new_index, new_obj, color='cyan')
        new_cut.set_data(count=new_index)
        self._update_tines(new_cut)

        self.logger.debug("adding new cut {} from {}".format(new_tag, old_tag))
        self.canvas.add(new_cut, tag=new_tag)
        self.add_cuts_tag(new_tag)

        self.logger.debug("redoing cut plots")
        return self.replot_all()

    def delete_cut_cb(self, w):
        tag = self.cutstag
        if tag == self._new_cut:
            return
        index = self.tags.index(tag)  # noqa
        self.canvas.delete_object_by_tag(tag)
        self.w.cuts.delete_alpha(tag)
        self.tags.remove(tag)
        idx = len(self.tags) - 1
        tag = self.tags[idx]
        self.select_cut(tag)
        if tag == self._new_cut:
            self.save_cuts.set_enabled(False)
            if self.use_slit and self.gui_up:
                self.save_slit.set_enabled(False)
        # plot cleared in replot_all() if no more cuts
        self.replot_all()

    def delete_all_cb(self, w):
        self.canvas.delete_all_objects()
        self.w.cuts.clear()
        self.tags = [self._new_cut]
        self.cutstag = self._new_cut
        self.w.cuts.append_text(self._new_cut)
        self.select_cut(self._new_cut)
        self.save_cuts.set_enabled(False)
        if self.use_slit and self.gui_up:
            self.save_slit.set_enabled(False)
        # plot cleared in replot_all() if no more cuts
        self.replot_all()

    def add_cuts_tag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)
            self.w.cuts.append_text(tag)

        select_flag = self.settings.get('select_new_cut', True)
        if select_flag:
            self.select_cut(tag)
            move_flag = self.settings.get('draw_then_move', True)
            if move_flag:
                self.set_mode('move')

    def close(self):
        #self.set_mode('move')
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # start line cuts operation
        self.cuts_plot.set_titles(rtitle="Cuts")

        self.drag_update = self.settings.get('drag_update', False)

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
        self.fv.show_status("Draw a line with the right mouse button")
        self.replot_all()
        if self.use_slit:
            self.cuts_image = self.fitsimage.get_image()

    def stop(self):
        self.gui_up = False
        self._split_sizes = self.w.splitter.get_sizes()
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        p_canvas.delete_object_by_tag(self.layertag)
        self.fv.show_status("")

    def redo(self):
        """This is called when a new image arrives or the data in the
        existing image changes.
        """
        if self.use_slit:
            image = self.fitsimage.get_image()
            if image != self.cuts_image:
                self.cuts_image = image
                self.build_axes()

        self.replot_all()

    def _get_perpendicular_points(self, obj, x, y, r):
        dx = float(obj.x1 - obj.x2)
        dy = float(obj.y1 - obj.y2)
        dist = np.sqrt(dx * dx + dy * dy)
        dx /= dist
        dy /= dist
        x3 = x + r * dy
        y3 = y - r * dx
        x4 = x - r * dy
        y4 = y + r * dx
        return (x3, y3, x4, y4)

    def _get_width_points(self, obj, x, y, rx, ry):
        x3, y3 = x - rx, y - ry
        x4, y4 = x + rx, y + ry
        return (x3, y3, x4, y4)

    def get_orthogonal_points(self, obj, x, y, r):
        if self.widthtype == 'x':
            return self._get_width_points(obj, x, y, r, 0)
        elif self.widthtype == 'y':
            return self._get_width_points(obj, x, y, 0, r)
        else:
            return self._get_perpendicular_points(obj, x, y, r)

    def get_orthogonal_array(self, image, obj, x, y, r):
        x1, y1, x2, y2 = self.get_orthogonal_points(obj, x, y, r)
        values = image.get_pixels_on_line(int(x1), int(y1),
                                          int(x2), int(y2))
        return np.array(values)

    def _plotpoints(self, obj, color):

        image = self.fitsimage.get_vip()

        # Get points on the line
        if obj.kind == 'line':
            if self.widthtype == 'none':
                points = image.get_pixels_on_line(int(obj.x1), int(obj.y1),
                                                  int(obj.x2), int(obj.y2))
            else:
                coords = image.get_pixels_on_line(int(obj.x1), int(obj.y1),
                                                  int(obj.x2), int(obj.y2),
                                                  getvalues=False)

                points = []
                for x, y in coords:
                    arr = self.get_orthogonal_array(image, obj, x, y,
                                                    self.width_radius)
                    val = np.nansum(arr)
                    points.append(val)

        elif obj.kind in ('path', 'freepath'):
            points = []
            x1, y1 = obj.points[0]
            for x2, y2 in obj.points[1:]:
                pts = image.get_pixels_on_line(int(x1), int(y1),
                                               int(x2), int(y2))
                # don't repeat last point when adding next segment
                points.extend(pts[:-1])
                x1, y1 = x2, y2

        elif obj.kind == 'beziercurve':
            points = image.get_pixels_on_curve(obj)

        points = np.array(points)

        rgb = colors.lookup_color(color)
        self.cuts_plot.cuts(points, xtitle="Line Index", ytitle="Pixel Value",
                            color=rgb)

        if self.settings.get('show_cuts_legend', False):
            self.add_legend()

    def add_legend(self):
        """Add or update Cuts plot legend."""
        cuts = [tag for tag in self.tags if tag is not self._new_cut]
        self.cuts_plot.ax.legend(cuts, loc='best',
                                 shadow=True, fancybox=True,
                                 prop={'size': 8}, labelspacing=0.2)

    def get_coords(self, obj):
        image = self.fitsimage.get_image()

        # Check whether multidimensional
        if len(image.naxispath) <= 0:
            return

        # Get points on the line
        if obj.kind == 'line':
            coords = image.get_pixels_on_line(int(obj.x1), int(obj.y1),
                                              int(obj.x2), int(obj.y2),
                                              getvalues=False)

        elif obj.kind in ('path', 'freepath'):
            coords = []
            x1, y1 = obj.points[0]
            for x2, y2 in obj.points[1:]:
                pts = image.get_pixels_on_line(int(x1), int(y1),
                                               int(x2), int(y2),
                                               getvalues=False)
                # don't repeat last point when adding next segment
                coords.extend(pts[:-1])
                x1, y1 = x2, y2

        elif obj.kind == 'beziercurve':
            coords = obj.get_pixels_on_curve(image, getvalues=False)
            # Exclude NaNs
            coords = [c for c in coords if not np.any(np.isnan(c))]

        shape = image.shape
        # Exclude points outside boundaries
        coords = [(coord[0], coord[1]) for coord in coords
                  if (0 <= coord[0] < shape[1] and 0 <= coord[1] < shape[0])]
        if not coords:
            self.redraw_slit('clear')
            return

        return np.array(coords)

    def get_slit_data(self, coords):
        image = self.fitsimage.get_image()
        data = image.get_mddata()
        naxes = data.ndim

        # Small correction
        selected_axis = abs(self.selected_axis - naxes)

        spatial_axes = [naxes - 1, naxes - 2]

        # Build N-dim slice
        axes_slice = image.revnaxis + [0, 0]

        # Slice data according to axis
        for i, sa in enumerate(spatial_axes):
            axes_slice[sa] = coords[:, i]
        axes_slice[selected_axis] = slice(None, None, None)

        self.slit_data = data[tuple(axes_slice)]

    def _plot_slit(self):
        if not self.selected_axis:
            return

        obj = self.canvas.get_object_by_tag(self.cutstag)
        line = self._getlines(obj)

        coords = self.get_coords(line[0])
        self.get_slit_data(coords)

        if self.transpose_enabled:
            self.redraw_slit('transpose')

        else:
            self.slit_plot.ax.imshow(
                self.slit_data, interpolation='nearest',
                origin='lower', aspect='auto').set_cmap('gray')
            self.set_labels()
            self.slit_plot.draw()

    def _replot(self, lines, colors):
        for idx in range(len(lines)):
            line, color = lines[idx], colors[idx]
            line.color = color
            self._plotpoints(line, color)

        return True

    def replot_all(self):
        self.cuts_plot.clear()
        self.w.delete_all.set_enabled(False)
        self.save_cuts.set_enabled(False)
        if self.use_slit and self.gui_up:
            self.save_slit.set_enabled(False)

        idx = 0
        for cutstag in self.tags:
            if cutstag == self._new_cut:
                continue
            obj = self.canvas.get_object_by_tag(cutstag)
            if obj.kind != 'compound':
                continue
            lines = self._getlines(obj)
            n = len(lines)
            count = obj.get_data('count', self.count)
            idx = (count + n) % len(self.colors)
            colors = self.colors[idx:idx + n]
            # text should take same color as first line in line set
            text = obj.objects[1]
            if text.kind == 'text':
                text.color = colors[0]
            #text.color = color
            self._replot(lines, colors)
            self.save_cuts.set_enabled(True)
            self.w.delete_all.set_enabled(True)

        # Redraw slit image for selected cut
        if self.use_slit:
            if self.cutstag != self._new_cut:
                self._plot_slit()
                if self.selected_axis and self.gui_up:
                    self.save_slit.set_enabled(True)

        # force mpl redraw
        self.cuts_plot.draw()

        self.canvas.redraw(whence=3)
        self.fv.show_status(
            "Click or drag left mouse button to reposition cuts")
        return True

    def _create_cut(self, x, y, count, x1, y1, x2, y2, color='cyan'):
        text = "cuts%d" % (count)
        if not self.settings.get('label_cuts', False):
            text = ''
        line_obj = self.dc.Line(x1, y1, x2, y2, color=color,
                                showcap=False)
        text_obj = self.dc.Text(0, 0, text, color=color, coord='offset',
                                ref_obj=line_obj)
        obj = self.dc.CompoundObject(line_obj, text_obj)
        # this is necessary for drawing cuts with width feature
        obj.initialize(self.canvas, self.fitsimage, self.logger)
        obj.set_data(cuts=True)
        return obj

    def _update_tines(self, obj):
        if obj.objects[0].kind != 'line':
            # right now we only know how to adjust lines
            return

        # Remove previous tines, if any
        if len(obj.objects) > 2:
            obj.objects = obj.objects[:2]

        if self.widthtype == 'none':
            return

        image = self.fitsimage.get_image()
        line = obj.objects[0]
        coords = image.get_pixels_on_line(int(line.x1), int(line.y1),
                                          int(line.x2), int(line.y2),
                                          getvalues=False)
        crdmap = OffsetMapper(self.fitsimage, line)
        num_ticks = max(len(coords) // self.tine_spacing_px, 3)
        interval = max(1, len(coords) // num_ticks)
        for i in range(0, len(coords), interval):
            x, y = coords[i]
            x1, y1, x2, y2 = self.get_orthogonal_points(line, x, y,
                                                        self.width_radius)
            (x1, y1), (x2, y2) = crdmap.calc_offsets([(x1, y1), (x2, y2)])
            aline = self.dc.Line(x1, y1, x2, y2)
            aline.crdmap = crdmap
            aline.editable = False
            obj.objects.append(aline)

    def _create_cut_obj(self, count, cuts_obj, color='cyan'):
        text = "cuts%d" % (count)
        if not self.settings.get('label_cuts', False):
            text = ''
        cuts_obj.showcap = False
        cuts_obj.linestyle = 'solid'
        #cuts_obj.color = color
        color = cuts_obj.color
        args = [cuts_obj]
        text_obj = self.dc.Text(0, 0, text, color=color, coord='offset',
                                ref_obj=cuts_obj)
        args.append(text_obj)

        obj = self.dc.CompoundObject(*args)
        obj.set_data(cuts=True)

        if (self.widthtype != 'none') and (self.width_radius > 0):
            self._update_tines(obj)
        return obj

    def _combine_cuts(self, *args):
        return self.dc.CompoundObject(*args)

    def _append_lists(self, l):
        if len(l) == 0:
            return []
        elif len(l) == 1:
            return l[0]
        else:
            res = l[0]
            res.extend(self._append_lists(l[1:]))
            return res

    def _getlines(self, obj):
        if obj.kind == 'compound':
            #return self._append_lists(list(map(self._getlines, obj.objects)))
            return [obj.objects[0]]
        elif obj.kind in self.cuttypes:
            return [obj]
        else:
            return []

    def buttondown_cb(self, canvas, event, data_x, data_y, viewer):
        return self.motion_cb(canvas, event, data_x, data_y, viewer)

    def motion_cb(self, canvas, event, data_x, data_y, viewer):
        if self.cutstag == self._new_cut:
            return True
        obj = self.canvas.get_object_by_tag(self.cutstag)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)
        canvas.redraw(whence=3)

        if self.drag_update:
            self.replot_all()
        return True

    def buttonup_cb(self, canvas, event, data_x, data_y, viewer):
        if self.cutstag == self._new_cut:
            return True
        obj = self.canvas.get_object_by_tag(self.cutstag)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)

        self.replot_all()
        return True

    def keydown(self, canvas, event, data_x, data_y, viewer):
        if event.key == 'n':
            self.select_cut(self._new_cut)
            return True
        elif event.key == 'h':
            self.cut_at('horizontal')
            return True
        elif event.key == 'j':
            self.cut_at('vertical')
            return True
        return False

    def _get_new_count(self):
        counts = set([])
        for cutstag in self.tags:
            try:
                obj = self.canvas.get_object_by_tag(cutstag)
            except KeyError:
                continue
            counts.add(obj.get_data('count', 0))
        ncounts = set(range(len(self.colors)))
        avail = list(ncounts.difference(counts))
        avail.sort()
        if len(avail) > 0:
            count = avail[0]
        else:
            self.count += 1
            count = self.count
        return count

    def _get_cut_index(self):
        if self.cutstag != self._new_cut:
            # Replacing a cut
            self.logger.debug("replacing cut position")
            try:
                cutobj = self.canvas.get_object_by_tag(self.cutstag)
                self.canvas.delete_object_by_tag(self.cutstag)
                count = cutobj.get_data('count')
            except KeyError:
                count = self._get_new_count()
        else:
            self.logger.debug("adding cut position")
            count = self._get_new_count()
        return count

    def cut_at(self, cuttype):
        """Perform a cut at the last mouse position in the image.
        `cuttype` determines the type of cut made.
        """
        data_x, data_y = self.fitsimage.get_last_data_xy()
        image = self.fitsimage.get_image()
        wd, ht = image.get_size()

        coords = []
        if cuttype == 'horizontal':
            coords.append((0, data_y, wd - 1, data_y))
        elif cuttype == 'vertical':
            coords.append((data_x, 0, data_x, ht - 1))

        count = self._get_cut_index()
        tag = "cuts%d" % (count)
        cuts = []
        for (x1, y1, x2, y2) in coords:
            # calculate center of line
            wd = x2 - x1
            dw = wd // 2
            ht = y2 - y1
            dh = ht // 2
            x, y = x1 + dw + 4, y1 + dh + 4

            cut = self._create_cut(x, y, count, x1, y1, x2, y2, color='cyan')
            self._update_tines(cut)
            cuts.append(cut)

        if len(cuts) == 1:
            cut = cuts[0]
        else:
            cut = self._combine_cuts(*cuts)

        cut.set_data(count=count)

        self.canvas.delete_object_by_tag(tag)
        self.canvas.add(cut, tag=tag)
        self.add_cuts_tag(tag)

        self.logger.debug("redoing cut plots")
        return self.replot_all()

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        canvas.delete_object_by_tag(tag)

        if obj.kind not in self.cuttypes:
            return True

        count = self._get_cut_index()
        tag = "cuts%d" % (count)

        cut = self._create_cut_obj(count, obj, color='cyan')
        cut.set_data(count=count)
        self._update_tines(cut)

        canvas.delete_object_by_tag(tag)
        self.canvas.add(cut, tag=tag)
        self.add_cuts_tag(tag)

        self.logger.debug("redoing cut plots")
        return self.replot_all()

    def edit_cb(self, canvas, obj):
        self.redraw_cuts()
        self.replot_all()
        return True

    def edit_select_cuts(self):
        if self.cutstag != self._new_cut:
            obj = self.canvas.get_object_by_tag(self.cutstag)
            # drill down to reference shape
            if hasattr(obj, 'objects'):
                obj = obj.objects[0]
            self.canvas.edit_select(obj)
        else:
            self.canvas.clear_selected()
        self.canvas.update_canvas()

    def set_mode_cb(self, mode, tf):
        """Called when one of the Move/Draw/Edit radio buttons is selected."""
        if tf:
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_select_cuts()
        return True

    def set_mode(self, mode):
        self.canvas.set_draw_mode(mode)
        self.w.btn_move.set_state(mode == 'move')
        self.w.btn_draw.set_state(mode == 'draw')
        self.w.btn_edit.set_state(mode == 'edit')

    def redraw_cuts(self):
        """Redraws cuts with tines (for cuts with a 'width')."""
        self.logger.debug("redrawing cuts")
        for cutstag in self.tags:
            if cutstag == self._new_cut:
                continue
            obj = self.canvas.get_object_by_tag(cutstag)
            if obj.kind != 'compound':
                continue
            self._update_tines(obj)
        self.canvas.redraw(whence=3)

    def width_radius_changed_cb(self, widget, val):
        """Callback executed when the Width radius is changed."""
        self.width_radius = val
        self.redraw_cuts()
        self.replot_all()
        return True

    def set_width_type_cb(self, widget, idx):
        self.widthtype = self.widthtypes[idx]
        self.redraw_cuts()
        self.replot_all()
        return True

    def save_cb(self, mode):
        """Save image, figure, and plot data arrays."""

        # This just defines the basename.
        # Extension has to be explicitly defined or things can get messy.
        w = Widgets.SaveDialog(title='Save {0} data'.format(mode))
        filename = w.get_path()

        if filename is None:
            # user canceled dialog
            return

        # TODO: This can be a user preference?
        fig_dpi = 100

        if mode == 'cuts':
            fig, xarr, yarr = self.cuts_plot.get_data()

        elif mode == 'slit':
            fig, xarr, yarr = self.slit_plot.get_data()

        figname = filename + '.png'
        self.logger.info("saving figure as: %s" % (figname))
        fig.savefig(figname, dpi=fig_dpi)

        dataname = filename + '.npz'
        self.logger.info("saving data as: %s" % (dataname))
        np.savez_compressed(dataname, x=xarr, y=yarr)

    def axis_toggle_cb(self, w, tf, pos):
        children = self.hbox_axes.get_children()

        # Deactivate previously selected axis
        if self.selected_axis is not None:
            children[self.selected_axis - 1].set_state(False)

        # Check if the old axis is clicked
        if pos == self.selected_axis:
            self.selected_axis = None
            if self.gui_up:
                self.save_slit.set_enabled(False)
            self.redraw_slit('clear')
        else:
            self.selected_axis = pos
            children[pos - 1].set_state(tf)
            if self.gui_up:
                if self.cutstag != self._new_cut:
                    self.save_slit.set_enabled(True)
                    self._plot_slit()
                else:
                    # no cut selected ("new cut")
                    self.redraw_slit('clear')

    def redraw_slit(self, mode):
        if mode == 'clear':
            self.slit_plot.clear()
        elif mode == 'transpose':
            self.slit_data = self.slit_data.T
            self.slit_plot.ax.imshow(
                self.slit_data, interpolation='nearest',
                origin='lower', aspect='auto').set_cmap('gray')
            self.set_labels()

        self.slit_plot.draw()

    def transpose_plot(self, w, tf):
        old_val = self.transpose_enabled
        self.transpose_enabled = tf

        if (old_val != tf and self.cutstag != self._new_cut and
                self.selected_axis):
            self.redraw_slit('transpose')

    def set_labels(self):
        image = self.fitsimage.get_image()
        shape = image.get_mddata().shape

        if (shape[0] == len(self.slit_data[0]) or
                shape[1] == len(self.slit_data[0])):
            self.slit_plot.ax.set_xlabel('')
            self.slit_plot.ax.set_ylabel('Position along slit')
        else:
            self.slit_plot.ax.set_ylabel('')
            self.slit_plot.ax.set_xlabel('Position along slit')

    def __str__(self):
        return 'cuts'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Cuts', package='ginga')

# END
