#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
``PixTable`` provides a way to check or monitor the pixel values in
a region.

**Plugin Type: Local**

``PixTable`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Basic Use**

In the most basic use, simply move the cursor around the channel
viewer; an array of pixel values will appear in the "Pixel Values"
display in the plugin UI.  The center value is highlighted, and this
corresponds to the value under the cursor.

You can choose a 3x3, 5x5, 7x7, or 9x9 grid from the left-most
combobox control.  It may help to adjust the "Font Size" control
to prevent having the array values cut off on the sides.  You can
also enlarge the plugin workspace to see more of the table.

.. note:: The order of the value table shown will not necessarily match to
          the channel viewer if the images is flipped, transposed, or rotated.

**Using Marks**

When you set and select a mark, the pixel values will be shown
surrounding the mark instead of the cursor.  There can be any number
of marks, and they are each noted with a numbered "X".  Simply change the
mark drop down control to select a different mark and see the values
around it.  The currently selected mark is shown with a different color
than the others.

The marks will stay in position even if a new image is loaded and
they will show the values for the new image.  In this way you can
monitor the area around a spot if the image is updating frequently.

If the "Pan to mark" checkbox is selected, then when you select a
different mark from the mark control, the channel viewer will pan to
that mark.  This can be useful to inspect the same spots in several
different images, especially when zoomed in tight to the image.

.. note:: If you change the mark control back to "None", then the pixel
          table will again update as you move the cursor around the viewer.

The "Caption" box can be used to set a text annotation that will be
appended to the mark label when the next mark is created.  This can be
used to label a feature in the image, for example.

**Deleting Marks**

To delete a mark, select it in the mark control and then press the
button marked "Delete".  To delete all the marks, press the button
marked "Delete All".

**Moving Marks**

When the "Move" radio button is checked, and a mark is selected, then
clicking or dragging anywhere in the image will move the mark to that
location and update the pixel table.   If no mark is currently selected
then a new one will be created and moved.

**Drawing Marks**

When the "Draw" radio button is checked, then clicking and dragging creates
a new mark. The longer the draw, the bigger radius of the "X".

**Editing Marks**

When the "Edit" radio button is checked after a mark has been selected then
you can drag the control points of the mark to increase the radius of the
arms of the X or you can drag the bounding box to move the mark. If the
editing control points are not shown, simply click on the center of a mark
to enable them.

**Special Keys**

In "Move" mode the following keys are active:
- "n" will place a new mark at the site of the cursor
- "m" will move the current mark (if any) to the site of the cursor
- "d" will delete the current mark (if any)
- "j" will select the previous mark (if any)
- "k" will select the next mark (if any)

**User Configuration**

"""
import numpy as np

from ginga.gw import Widgets, Viewers
from ginga import GingaPlugin, colors

__all__ = ['PixTable']


class PixTable(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(PixTable, self).__init__(fv, fitsimage)

        self.layertag = 'pixtable-canvas'
        self.pan2mark = False

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_PixTable')
        self.settings.add_defaults(fontsize=10,
                                   font='fixed',
                                   mark_radius=10,
                                   mark_style='cross',
                                   mark_color='lightgreen',
                                   select_color='cyan',
                                   drag_update=True)
        self.settings.load(onError='silent')

        self.dc = self.fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        self.fitsimage.set_callback('cursor-changed', self.cursor_cb)
        canvas.enable_draw(True)
        canvas.set_drawtype('point', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.enable_edit(True)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.add_draw_mode('move', down=self.btndown_cb,
                             move=self.motion_cb, up=self.btnup_cb,
                             key=self.keydown_cb)
        canvas.set_draw_mode('move')
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        # For pixel table
        self.pixtbl_radius = 2
        self.txt_arr = None
        self.sum_arr = None
        self.sizes = [1, 2, 3, 4]
        self.maxdigits = 9
        self.fmt_cell = f'^{self.maxdigits}.4g'
        self.lastx = 0
        self.lasty = 0
        self.font = self.settings.get('font', 'fixed')
        self.fontsize = self.settings.get('fontsize', 12)
        self.fontsizes = [6, 8, 9, 10, 11, 12, 14, 16, 18, 24, 28, 32]
        self.pixview = None
        self._wd = 400
        self._ht = 300
        # hack to set a reasonable starting position for the splitter
        _sz = max(self._wd, self._ht)
        self._split_sizes = [_sz, _sz]
        self.gui_up = False

        # For "marks" feature
        self.mark_radius = self.settings.get('mark_radius', 10)
        self.mark_style = self.settings.get('mark_style', 'cross')
        self.mark_color = self.settings.get('mark_color', 'lightgreen')
        self.select_color = self.settings.get('select_color', 'cyan')
        self.marks = ['None']
        self.mark_index = 0
        self.mark_selected = None
        self.drag_update = self.settings.get('drag_update', True)

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        box, sw, orientation = Widgets.get_oriented_box(container,
                                                        orientation=self.settings.get('orientation', None))
        box.set_border_width(4)
        box.set_spacing(2)

        fr = Widgets.Frame("Pixel Values")

        # We just use a ginga widget to implement the pixtable
        pixview = Viewers.CanvasView(logger=self.logger)
        pixview.set_desired_size(self._wd, self._ht)
        bg = colors.lookup_color('#202030')
        pixview.set_bg(*bg)

        bd = pixview.get_bindings()
        bd.enable_zoom(True)
        bd.enable_pan(True)

        self.pixview = pixview
        self.pix_w = Viewers.GingaViewerWidget(pixview)
        fr.set_widget(self.pix_w)
        self.pix_w.resize(self._wd, self._ht)

        paned = Widgets.Splitter(orientation=orientation)
        self.w.splitter = paned
        paned.add_widget(fr)

        self._rebuild_table()

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        cbox1 = Widgets.ComboBox()
        index = 0
        for i in self.sizes:
            j = 1 + i * 2
            name = "%dx%d" % (j, j)
            cbox1.append_text(name)
            index += 1
        index = self.sizes.index(self.pixtbl_radius)
        cbox1.set_index(index)
        cbox1.add_callback('activated', self.set_cutout_size_cb)
        cbox1.set_tooltip("Select size of pixel table")
        btns.add_widget(cbox1, stretch=0)

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

        btn1 = Widgets.Button("Delete")
        btn1.add_callback('activated', lambda w: self.clear_mark_cb())
        btn1.set_tooltip("Delete selected mark")
        btn1.set_enabled(len(self.marks) > 1)
        self.w.btn_delete = btn1
        btns.add_widget(btn1, stretch=0)

        btn2 = Widgets.Button("Delete All")
        btn2.add_callback('activated', lambda w: self.clear_all())
        btn2.set_tooltip("Clear all marks")
        btns.add_widget(btn2, stretch=0)
        btn2.set_enabled(len(self.marks) > 1)
        self.w.btn_delete_all = btn2
        btns.add_widget(Widgets.Label(''), stretch=1)

        vbox2 = Widgets.VBox()
        vbox2.add_widget(btns, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn3 = Widgets.CheckBox("Pan to mark")
        btn3.set_state(self.pan2mark)
        btn3.add_callback('activated', self.pan2mark_cb)
        btn3.set_tooltip("Pan follows selected mark")
        btns.add_widget(btn3)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vbox2.add_widget(btns, stretch=0)

        captions = [
            ('Font size:', 'label', 'Font size', 'combobox',
             'Caption:', 'label', 'Caption', 'entry'),
        ]
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        b.font_size.set_tooltip("Set font size for pixel display")
        for size in self.fontsizes:
            b.font_size.append_text(str(size))
        b.font_size.show_text(str(self.fontsize))
        b.font_size.add_callback('activated', self.set_font_size_cb)

        b.caption.set_tooltip("Text to append to the marker")

        vbox2.add_widget(Widgets.Label(''), stretch=1)
        box.add_widget(vbox2, stretch=1)

        paned.add_widget(sw)
        paned.set_sizes(self._split_sizes)

        top.add_widget(paned, stretch=1)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Move")
        btn1.set_state(mode == 'move')
        btn1.add_callback('activated',
                          lambda w, val: self.set_mode_cb('move', val))
        btn1.set_tooltip("Choose this to add or move a mark")
        self.w.btn_move = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback('activated',
                          lambda w, val: self.set_mode_cb('draw', val))
        btn2.set_tooltip("Choose this to draw a new or replacement mark")
        self.w.btn_draw = btn2
        hbox.add_widget(btn2)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback('activated',
                          lambda w, val: self.set_mode_cb('edit', val))
        btn3.set_tooltip("Choose this to edit a mark")
        self.w.btn_edit = btn3
        hbox.add_widget(btn3)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(hbox, stretch=0)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(btns, stretch=0)
        container.add_widget(top, stretch=1)
        self.gui_up = True

    def select_mark(self, tag, pan=True):
        # deselect the current selected mark, if there is one
        if self.mark_selected is not None:
            try:
                obj = self.canvas.get_object_by_tag(self.mark_selected)
                obj.set_attr_all(color=self.mark_color)
            except Exception:
                # old object may have been deleted
                pass

        self.mark_selected = tag
        if tag is None:
            self.w.marks.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.marks.show_text(tag)
        obj = self.canvas.get_object_by_tag(tag)
        obj.set_attr_all(color=self.select_color)
        self.lastx = obj.objects[0].x
        self.lasty = obj.objects[0].y
        if self.pan2mark and pan:
            self.fitsimage.panset_xy(self.lastx, self.lasty)
        self.canvas.redraw(whence=3)

        self.redo()

    def mark_select_cb(self, w, index):
        tag = self.marks[index]
        if index == 0:
            tag = None
        self.select_mark(tag)

    def pan2mark_cb(self, w, val):
        self.pan2mark = val

    def clear_mark_cb(self):
        tag = self.mark_selected
        if tag is None:
            return
        self.canvas.delete_object_by_tag(tag)
        self.w.marks.delete_alpha(tag)
        self.marks.remove(tag)
        self.w.marks.set_index(0)
        self.mark_selected = None
        self.w.btn_delete.set_enabled(len(self.marks) > 1)
        self.w.btn_delete_all.set_enabled(len(self.marks) > 1)

    def clear_all(self):
        self.canvas.delete_all_objects()
        for name in self.marks:
            self.w.marks.delete_alpha(name)
        self.marks = ['None']
        self.w.marks.append_text('None')
        self.w.marks.set_index(0)
        self.mark_selected = None
        self.mark_index = 0
        self.w.btn_delete.set_enabled(False)
        self.w.btn_delete_all.set_enabled(False)

    def set_font_size_cb(self, w, index):
        self.fontsize = self.fontsizes[index]
        self._rebuild_table()
        self.redo()

    def plot(self, data, x1, y1, x2, y2, data_x, data_y, radius,
             maxv=9):

        # Because most FITS data is stored with lower Y indexes to
        # bottom
        data = np.flipud(data)

        width, height = self.fitsimage.get_dims(data)
        if self.txt_arr is None:
            return
        if data.shape != self.txt_arr.shape:
            return

        maxval = np.nanmax(data)
        minval = np.nanmin(data)
        avgval = np.mean(data)
        rmsval = np.sqrt(np.mean(np.square(data)))
        medianval = np.median(data)
        sumval = np.nansum(data)
        fmt_cell = self.fmt_cell

        def _vecfunc(val, out):
            if not np.isscalar(val):
                val = np.average(val)
            out.text = f'{val:{fmt_cell}}'

        func = np.vectorize(_vecfunc)
        func(data, self.txt_arr)

        ctr_txt = self.txt_arr[width // 2][height // 2]

        # Report statistics
        self.sum_arr[0].text = f"Min: {minval:{fmt_cell}} Mean: {avgval:{fmt_cell}} Median: {medianval:{fmt_cell}}"
        self.sum_arr[1].text = f"Max: {maxval:{fmt_cell}}  RMS: {rmsval:{fmt_cell}} Sum: {sumval:{fmt_cell}}"

        # update the pixtable
        self.pixview.panset_xy(ctr_txt.x, ctr_txt.y)

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
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

    def stop(self):
        self.gui_up = False
        self._split_sizes = self.w.splitter.get_sizes()
        # remove the canvas from the image
        self.canvas.ui_set_active(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        self.pixview = None

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.redo()

    def redo(self):
        if self.pixview is None:
            return
        # cut out and set the pixel table data
        image = self.fitsimage.get_vip()

        if image is None:
            return

        # We report the value across the pixel, even though the coords
        # change halfway across the pixel
        px_off = self.fitsimage.data_off
        data_x, data_y = (int(np.floor(self.lastx + px_off)),
                          int(np.floor(self.lasty + px_off)))

        # cutout image data
        data, x1, y1, x2, y2 = image.cutout_radius(data_x, data_y,
                                                   self.pixtbl_radius)

        self.fv.error_wrap(self.plot, data, x1, y1, x2, y2,
                           self.lastx, self.lasty,
                           self.pixtbl_radius, maxv=9)

    def _rebuild_table(self):
        canvas = self.pixview.get_canvas()
        canvas.delete_all_objects(redraw=False)

        Text = canvas.get_draw_class('text')
        ex_txt = Text(0, 0, text='5', fontsize=self.fontsize, font=self.font)
        font_wd, font_ht = self.fitsimage.renderer.get_dimensions(ex_txt)
        max_wd = self.maxdigits + 2
        crdmap = self.pixview.get_coordmap('window')

        rows = []
        objs = []
        max_cx = 0
        x_offset = 6
        y_offset = 4
        for row in range(self.pixtbl_radius * 2 + 1):
            cols = []
            for col in range(self.pixtbl_radius * 2 + 1):
                col_wd = font_wd * max_wd
                cx = col_wd * col + x_offset
                max_cx = max(max_cx, cx + col_wd)
                cy = font_ht * (row + 1) + y_offset

                color = 'lightgreen'
                if (row == col) and (row == self.pixtbl_radius):
                    color = 'pink'

                text_obj = Text(cx, cy, text='', font=self.font,
                                color=color, fontsize=self.fontsize,
                                coord='window')
                objs.append(text_obj)
                cols.append(text_obj)

            rows.append(cols)

        self.txt_arr = np.array(rows)

        # add summary row(s)
        cx = (font_wd + 2) + x_offset
        cy += font_ht + 20
        s1 = Text(cx, cy, text='', font=self.font,
                  color='cyan', fontsize=self.fontsize,
                  coord='window')
        objs.append(s1)
        cy += font_ht + y_offset
        s2 = Text(cx, cy, text='', font=self.font,
                  color='cyan', fontsize=self.fontsize,
                  coord='window')
        objs.append(s2)
        self.sum_arr = np.array([s1, s2])

        # add all of the text objects to the canvas as one large
        # compound object
        CompoundObject = canvas.get_draw_class('compoundobject')
        canvas.add(CompoundObject(*objs), redraw=False)

        # set limits for scrolling
        self.pixview.set_limits(((0, 0), (max_cx, cy)), coord='window')

    def set_cutout_size_cb(self, w, val):
        index = w.get_index()
        self.pixtbl_radius = self.sizes[index]
        self._rebuild_table()
        self.redo()

    def cursor_cb(self, canvas, junk, data_x, data_y):
        if not self.gui_up:
            return
        if self.mark_selected is not None:
            return False
        if self.pixview is None:
            return

        self.lastx, self.lasty = data_x, data_y

        self.redo()
        return False

    def add_mark(self, data_x, data_y, radius=None, color=None, style=None,
                 text=None):
        if not radius:
            radius = self.mark_radius
        if not color:
            color = self.mark_color
        if not style:
            style = self.mark_style

        self.logger.debug("Setting mark at %d,%d" % (data_x, data_y))
        self.mark_index += 1
        tag = 'mark%d' % (self.mark_index)
        caption = "%d" % (self.mark_index)
        if text is not None:
            caption = caption + ': ' + text
        if radius is None:
            radius = self.mark_radius
        pt_obj = self.dc.Point(data_x, data_y, radius,
                               style=style, color=color,
                               linestyle='solid')
        txt_obj = self.dc.Text(10, 0, caption,
                               font=self.font, fontsize=self.fontsize,
                               color=color, ref_obj=pt_obj, coord='offset')
        txt_obj.editable = False
        tag = self.canvas.add(self.dc.CompoundObject(pt_obj, txt_obj),
                              tag=tag)
        self.marks.append(tag)
        self.w.marks.append_text(tag)
        self.w.btn_delete.set_enabled(True)
        self.w.btn_delete_all.set_enabled(True)
        self.select_mark(tag, pan=False)

    def _mark_update(self, data_x, data_y):
        if self.mark_selected is None:
            return False

        m_obj = self.canvas.get_object_by_tag(self.mark_selected)
        p_obj = m_obj.objects[0]
        p_obj.move_to(data_x, data_y)
        self.lastx, self.lasty = data_x, data_y
        self.canvas.update_canvas()
        return True

    def btndown_cb(self, canvas, event, data_x, data_y, viewer):
        if self._mark_update(data_x, data_y):
            if self.drag_update:
                self.redo()
            return True

        # no selected mark, make a new one
        caption = self.w.caption.get_text().strip()
        if len(caption) == 0:
            caption = None
        self.add_mark(data_x, data_y, text=caption)
        return True

    def motion_cb(self, canvas, event, data_x, data_y, viewer):
        if not self._mark_update(data_x, data_y):
            return False

        if self.drag_update:
            self.redo()
        return True

    def btnup_cb(self, canvas, event, data_x, data_y, viewer):
        if not self._mark_update(data_x, data_y):
            return False

        self.redo()
        return True

    def prev_mark(self):
        if len(self.marks) <= 1 or self.mark_selected is None:
            # no previous
            return

        idx = self.marks.index(self.mark_selected)
        idx = idx - 1
        if idx < 0:
            return
        tag = self.marks[idx]
        if tag == 'None':
            tag = None
        self.select_mark(tag)

    def next_mark(self):
        if len(self.marks) <= 1:
            # no next
            return

        if self.mark_selected is None:
            idx = 0
        else:
            idx = self.marks.index(self.mark_selected)
        idx = idx + 1
        if idx >= len(self.marks):
            return
        tag = self.marks[idx]
        if tag == 'None':
            tag = None
        self.select_mark(tag)

    def keydown_cb(self, canvas, event, data_x, data_y, viewer):
        if event.key == 'n':
            caption = self.w.caption.get_text().strip()
            if len(caption) == 0:
                caption = None
            self.add_mark(data_x, data_y, text=caption)
            return True
        elif event.key == 'm':
            if self._mark_update(data_x, data_y):
                self.redo()
            return True
        elif event.key == 'd':
            self.clear_mark_cb()
            return True
        elif event.key == 'j':
            self.prev_mark()
            return True
        elif event.key == 'k':
            self.next_mark()
            return True
        return False

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        canvas.delete_object_by_tag(tag)

        caption = self.w.caption.get_text().strip()
        if len(caption) == 0:
            caption = None
        self.add_mark(obj.x, obj.y, text=caption, radius=obj.radius)

    def edit_cb(self, canvas, obj):
        if self.mark_selected is not None:
            m_obj = self.canvas.get_object_by_tag(self.mark_selected)
            if m_obj is not None and m_obj.objects[0] is obj:
                # edited mark was the selected mark
                self.lastx, self.lasty = obj.x, obj.y
                self.redo()
        return True

    def edit_select_mark(self):
        if self.mark_selected is not None:
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
                self.edit_select_mark()
        return True

    def set_mode(self, mode):
        self.canvas.set_draw_mode(mode)
        self.w.btn_move.set_state(mode == 'move')
        self.w.btn_draw.set_state(mode == 'draw')
        self.w.btn_edit.set_state(mode == 'edit')

    def __str__(self):
        return 'pixtable'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_PixTable', package='ginga')

# END
