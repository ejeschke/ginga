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
    A plugin to graph the pixel values along a straight line bisecting a cube.

    Plugin Type: Local
    ------------------
    LineProfile is a local plugin, which means it is associated with a
    channel.  An instance can be opened for each channel.

    Usage
    -----
    1. Select an axis.
    2. Pick a point or draw a region using the cursor.
    3. Use MultiDim to change step values of axes, if applicable.
    """
    def __init__(self, fv, fitsimage):
        super(LineProfile, self).__init__(fv, fitsimage)

        self.image = None
        self.layertag = 'lineprofile-canvas'
        self.selected_axis = None
        self.hbox_axes = None

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_LineProfile')
        self.settings.add_defaults(mark_type='point', mark_radius=10,
                                   mark_style='cross', mark_color='cyan')
        self.settings.load(onError='silent')

        # For "marks" feature
        self._new_mark = 'New'
        self.mark_types = ['point', 'circle', 'ellipse', 'box', 'rectangle',
                           'polygon']
        self.mark_type = self.settings.get('mark_type', 'point')
        self.mark_radius = self.settings.get('mark_radius', 10)  # point
        self.mark_style = self.settings.get('mark_style', 'cross')  # point
        self.mark_color = self.settings.get('mark_color', 'cyan')
        self.marks = [self._new_mark]
        self.mark_selected = self._new_mark
        self.mark_index = 0
        self.y_lbl = ''
        self.x_lbl = ''

        self.dc = self.fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype(self.mark_type, color=self.mark_color,
                            linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.add_draw_mode('move', down=self.buttondown_cb,
                             move=self.motion_cb, up=self.buttonup_cb)
        canvas.set_draw_mode('draw')
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

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

        captions = (('marks', 'combobox',
                     'New Mark Type:', 'label', 'Mark Type', 'combobox'),
                    ('Pan to mark', 'button'),
                    ('Delete', 'button', 'Delete All', 'button'))
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        # control for selecting a mark
        cbox2 = b.marks
        for tag in self.marks:
            cbox2.append_text(tag)
        cbox2.show_text(self.mark_selected)
        cbox2.add_callback('activated', self.mark_select_cb)
        self.w.marks = cbox2
        cbox2.set_tooltip("Select a mark")

        # control for selecting mark type
        cbox2 = b.mark_type
        for tag in self.mark_types:
            cbox2.append_text(tag)
        self.w.marks_type = cbox2
        cbox2.set_index(self.mark_types.index(self.mark_type))
        cbox2.add_callback('activated', self.set_marksdrawtype_cb)
        cbox2.set_tooltip("Choose the mark type to draw")

        b.pan_to_mark.add_callback('activated', self.pan2mark_cb)
        b.pan_to_mark.set_tooltip("Pan follows selected mark")

        b.delete.add_callback('activated', self.clear_mark_cb)
        b.delete.set_tooltip("Delete selected mark")

        b.delete_all.add_callback('activated', self.clear_all_cb)
        b.delete_all.set_tooltip("Clear all marks")

        vbox2 = Widgets.VBox()
        vbox2.add_widget(w, stretch=0)

        mode = self.canvas.get_draw_mode()
        captions = (('Move', 'radiobutton', 'Draw', 'radiobutton',
                     'Edit', 'radiobutton'), )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.move.set_state(mode == 'move')
        b.move.add_callback(
            'activated', lambda w, val: self.set_mode_cb('move', val))
        b.move.set_tooltip("Choose this to position marks")
        self.w.btn_move = b.move

        b.draw.set_state(mode == 'draw')
        b.draw.add_callback(
            'activated', lambda w, val: self.set_mode_cb('draw', val))
        b.draw.set_tooltip("Choose this to draw a new mark")
        self.w.btn_draw = b.draw

        b.edit.set_state(mode == 'edit')
        b.edit.add_callback(
            'activated', lambda w, val: self.set_mode_cb('edit', val))
        b.edit.set_tooltip("Choose this to edit a mark")
        self.w.btn_edit = b.edit

        vbox2.add_widget(w, stretch=0)

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

        self.select_mark(self._new_mark)
        self.build_axes()

    def build_axes(self):
        if (not self.gui_up) or (self.hbox_axes is None):
            return
        self.hbox_axes.remove_all()
        self.clear_plot()

        image = self.fitsimage.get_image()
        if image is not None:
            # Add Checkbox widgets
            # `image.naxispath` returns only mdim axes
            nx = len(image.naxispath)
            maxi = nx + 2
            for i in range(1, maxi + 1):
                chkbox = Widgets.CheckBox('NAXIS{}'.format(i))
                self.hbox_axes.add_widget(chkbox)

                # Disable axes for 2D images
                if nx <= 0:
                    self.selected_axis = None
                    chkbox.set_enabled(False)
                    continue

                # Add callback
                self.axes_callback_handler(chkbox, i)

            # Add filler
            self.hbox_axes.add_widget(Widgets.Label(''), stretch=1)
        else:
            self.selected_axis = None
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
            if self.gui_up:
                self.redraw_mark()

    def redo(self):
        # Get image being shown
        image = self.fitsimage.get_image()
        if image is None:
            return

        if self.image != image:
            self.image = image
            self.build_axes()

        self.redraw_mark()

    def _plot(self, tag):
        self.clear_plot()

        if self.selected_axis is None:
            return

        obj = self.canvas.get_object_by_tag(tag)
        if hasattr(obj, 'objects'):
            obj = obj.objects[0]

        mddata = self.image.get_mddata()  # ..., z2, z1, y, x
        naxes = mddata.ndim
        i_sel = abs(self.selected_axis - naxes)
        i_x = naxes - 1
        i_y = naxes - 2
        axes_slice = self.image.revnaxis + [0, 0]

        plot_x_axis_data = self.get_axis(self.selected_axis)

        # Image may lack the required keywords, or some trouble
        # building the axis.
        if plot_x_axis_data is None:
            return

        # Cutting through surface ignores drawn shape but uses its center.
        # A line through higher dim uses the same algorithm.
        if i_sel in (i_x, i_y) or obj.kind == 'point':
            xcen, ycen = obj.get_center_pt()
            # Build N-dim slice
            axes_slice[i_x] = int(round(xcen))
            axes_slice[i_y] = int(round(ycen))
            axes_slice[i_sel] = slice(None, None, None)
            plot_y_axis_data = mddata[axes_slice]

        # TODO: Add more stats choices? Only calc mean for now.
        # Do some stats of data in selected region.
        else:
            # Collapse to 3D cube
            if naxes > 3:
                for j in (i_x, i_y, i_sel):
                    axes_slice[j] = slice(None, None, None)
                data = mddata[axes_slice]  # z, y, x
            else:
                data = mddata
            # Broadcast region mask to 3D
            mask = self.image.get_shape_mask(obj)  # 2D only, True = enclosed
            mask3d = np.zeros(data.shape, dtype=np.bool)
            mask3d[:, :, :] = mask[np.newaxis, :, :]  # z, y, x
            masked_data = np.ma.masked_array(data, mask=~mask3d)
            masked_mean = masked_data.mean(axis=(1, 2))
            plot_y_axis_data = masked_mean[~masked_mean.mask].data

        # If few enough data points, add marker
        if len(plot_y_axis_data) <= 10:
            marker = 'x'
        else:
            marker = None

        # https://github.com/matplotlib/matplotlib/issues/3633/
        ax2 = self._ax2
        ax2.patch.set_visible(False)

        self.clear_plot()
        self.plot.plot(plot_x_axis_data, plot_y_axis_data,
                       xtitle=self.x_lbl, ytitle=self.y_lbl, marker=marker)

        # Highlight data point from active slice.
        if i_sel not in (i_x, i_y):
            i = self.image.revnaxis[i_sel]
            self.plot.ax.plot(plot_x_axis_data[i], plot_y_axis_data[i],
                              marker='o', ls='')

        # Top axis to show pixel location across X
        ax2.cla()
        xx1, xx2 = self.plot.ax.get_xlim()
        ax2.set_xlim((xx1 - self._crval) / self._cdelt + self._crpix - 1,
                     (xx2 - self._crval) / self._cdelt + self._crpix - 1)
        ax2.set_xlabel('Index')
        self.plot.draw()

    def get_axis(self, i):
        try:
            naxis_s = 'NAXIS{}'.format(i)
            naxis_i = self.image.get_keyword(naxis_s)
            self.x_lbl = self.image.get_keyword('CTYPE{}'.format(i), naxis_s)

            try:
                kwds = ['CRVAL{}'.format(i), 'CDELT{}'.format(i),
                        'CRPIX{}'.format(i)]
                crval_i, cdelt_i, crpix_i = self.image.get_keywords_list(*kwds)
            except KeyError as e:
                self.logger.error("Missing FITS keyword: {}".format(str(e)))
                crval_i = 0
                cdelt_i = 1
                crpix_i = 1

            n = np.arange(naxis_i) - (crpix_i - 1)
            axis = crval_i + n * cdelt_i
            self._crval = crval_i
            self._cdelt = cdelt_i
            self._crpix = crpix_i

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

    def buttondown_cb(self, canvas, event, data_x, data_y, viewer):
        return self.motion_cb(canvas, event, data_x, data_y, viewer)

    def motion_cb(self, canvas, event, data_x, data_y, viewer):
        if self.mark_selected == self._new_mark:
            return True

        obj = self.canvas.get_object_by_tag(self.mark_selected)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)
        canvas.redraw(whence=3)

        # self.redraw_mark()  # Uncomment if you want drag_update
        return True

    def buttonup_cb(self, canvas, event, data_x, data_y, viewer):
        if self.mark_selected == self._new_mark:
            return True

        obj = self.canvas.get_object_by_tag(self.mark_selected)
        # Assume first element of this compound object is the reference obj
        obj = obj.objects[0]
        obj.move_to(data_x, data_y)

        self.redraw_mark()
        return True

    def add_mark(self, obj):
        self.logger.debug("Setting mark of type {}".format(obj.kind))

        # Adding a new mark, so use a new tag.
        if self.mark_selected == self._new_mark:
            draw_new = True
            self.mark_index += 1
            idx = self.mark_index
        # Replace existing mark (to support old-style drawing).
        else:
            draw_new = False
            try:
                idx = int(self.mark_selected.replace('mark', ''))
            except ValueError as e:
                self.logger.error(str(e))
                return

        obj.color = self.mark_color
        obj.linestyle = 'solid'
        if obj.kind == 'point':
            obj.radius = self.mark_radius
            obj.style = self.mark_style
        args = [obj]

        text_obj = self.dc.Text(4, 4, '{}'.format(idx), color=self.mark_color,
                                coord='offset', ref_obj=obj)
        args.append(text_obj)

        cobj = self.dc.CompoundObject(*args)
        cobj.set_data(count=idx)

        tag = 'mark{}'.format(idx)
        self.canvas.delete_object_by_tag(tag)
        self.canvas.add(cobj, tag=tag)

        if draw_new:
            self.marks.append(tag)
            self.w.marks.append_text(tag)

        self.select_mark(tag)

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        canvas.delete_object_by_tag(tag)

        if obj.kind not in self.mark_types:
            return True

        # Disable plotting for 2D images
        image = self.fitsimage.get_image()
        if image is None or len(image.naxispath) < 1:
            return

        self.add_mark(obj)

    def edit_cb(self, canvas, obj):
        self.redraw_mark()
        return True

    def edit_select_marks(self):
        if self.mark_selected != self._new_mark:
            obj = self.canvas.get_object_by_tag(self.mark_selected)
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
                self.edit_select_marks()
        return True

    def set_mode(self, mode):
        self.canvas.set_draw_mode(mode)
        self.w.btn_move.set_state(mode == 'move')
        self.w.btn_draw.set_state(mode == 'draw')
        self.w.btn_edit.set_state(mode == 'edit')

    def select_mark(self, tag):
        try:
            obj = self.canvas.get_object_by_tag(self.mark_selected)
        except Exception:  # old object may have been deleted
            pass
        else:
            # drill down to reference shape
            if hasattr(obj, 'objects'):
                obj = obj.objects[0]

        self.mark_selected = tag
        self.w.marks.show_text(tag)
        none_left = len(self.marks) < 2

        if (tag == self._new_mark) or none_left:
            if none_left:
                self.w.delete_all.set_enabled(False)

            self.w.delete.set_enabled(False)
            self.w.pan_to_mark.set_enabled(False)

            self.w.btn_move.set_enabled(False)
            self.w.btn_draw.set_enabled(True)
            self.w.btn_edit.set_enabled(False)
            self.set_mode('draw')

        else:
            self.w.delete_all.set_enabled(True)
            self.w.delete.set_enabled(True)
            self.w.pan_to_mark.set_enabled(True)

            self.w.btn_move.set_enabled(True)
            self.w.btn_draw.set_enabled(False)
            self.w.btn_edit.set_enabled(True)

            if self.w.btn_edit.get_state():
                self.edit_select_marks()

            mode = self.canvas.get_draw_mode()
            if mode == 'draw':
                self.set_mode('move')

            self.redraw_mark()

    def redraw_mark(self):
        tag = self.mark_selected
        if tag == self._new_mark:
            self.clear_plot()
            return
        self._plot(tag)

    def mark_select_cb(self, w, index):
        tag = self.marks[index]
        self.select_mark(tag)

    def set_marksdrawtype_cb(self, w, index):
        self.mark_type = self.mark_types[index]
        self.canvas.set_drawtype(self.mark_type, color=self.mark_color,
                                 linestyle='dash')

    def pan2mark_cb(self, w):
        if self.mark_selected == self._new_mark:
            return
        obj = self.canvas.get_object_by_tag(self.mark_selected)
        # drill down to reference shape
        if hasattr(obj, 'objects'):
            obj = obj.objects[0]
        if obj.kind not in self.mark_types:
            return
        x, y = obj.get_center_pt()
        self.fitsimage.panset_xy(x, y)
        self.canvas.redraw(whence=3)

    def clear_mark_cb(self, w):
        tag = self.mark_selected
        if tag == self._new_mark:
            return
        self.canvas.delete_object_by_tag(tag)
        self.w.marks.delete_alpha(tag)
        self.marks.remove(tag)

        idx = len(self.marks) - 1
        tag = self.marks[idx]
        self.select_mark(tag)

        # plot cleared in redraw_mark() if no more cuts
        self.redraw_mark()

    def clear_all_cb(self, w):
        self.canvas.delete_all_objects()
        self.w.marks.clear()
        self.marks = [self._new_mark]
        self.mark_selected = self._new_mark
        self.w.marks.append_text(self._new_mark)
        self.select_mark(self._new_mark)

        # plot cleared in redraw_mark() if no more cuts
        self.redraw_mark()

    # GENERAL PLUGIN MANAGEMENT #

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        self.gui_up = False
        return True

    def start(self):
        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True)
        self.fv.show_status("Mark a point or region and choose axis")
        self.redo()

    def stop(self):
        # remove the canvas from the image
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass

        # Don't hang on to current image
        self.image = None
        self.fv.show_status("")

    def __str__(self):
        return 'lineprofile'


# Replace module docstring with config doc for auto insert by Sphinx.
# In the future, if we need the real docstring, we can append instead of
# overwrite.
from ginga.util.toolbox import generate_cfg_example  # noqa
__doc__ = generate_cfg_example('plugin_LineProfile', package='ginga')
