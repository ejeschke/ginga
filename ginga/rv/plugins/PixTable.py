#
# PixTable.py -- Pixel Table plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.gw import Widgets, Viewers
from ginga import GingaPlugin, colors


class PixTable(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(PixTable, self).__init__(fv, fitsimage)

        self.layertag = 'pixtable-canvas'
        self.pan2mark = False

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_PixTable')
        self.settings.addDefaults(fontsize=12,
                                  font='fixed')
        self.settings.load(onError='silent')

        self.dc = self.fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.set_callback('cursor-down', self.btndown_cb)
        canvas.set_callback('none-move', self.motion_cb)
        canvas.set_surface(self.fitsimage)
        self.canvas = canvas

        # For pixel table
        self.pixtbl_radius = 2
        self.txt_arr = None
        self.sum_arr = None
        self.sizes = [ 1, 2, 3, 4 ]
        self.maxdigits = 9
        self.fmt_cell = '{:> %d.%dg}'% (self.maxdigits-1, self.maxdigits // 2)
        self.lastx = 0
        self.lasty = 0
        self.font = self.settings.get('font', 'fixed')
        self.fontsize = self.settings.get('fontsize', 12)
        self.fontsizes = [6, 8, 9, 10, 11, 12, 14, 16]

        # For "marks" feature
        self.mark_radius = 10
        self.mark_style = 'cross'
        self.mark_color = 'purple'
        self.select_color = 'cyan'
        self.marks = ['None']
        self.mark_index = 0
        self.mark_selected = None
        self.tw = None

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         fill=True)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msg_font = self.fv.get_font("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msg_font)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Pixel Values")

        # We just use a ginga widget to implement the pixtable
        pixview = Viewers.CanvasView(logger=self.logger)
        width, height = 300, 300
        pixview.set_desired_size(width, height)
        bg = colors.lookup_color('#202030')
        pixview.set_bg(*bg)

        bd = pixview.get_bindings()

        self.pixview = pixview
        self.pix_w = Viewers.GingaViewerWidget(pixview)
        #self.pix_w.resize(width, height)
        fr.set_widget(self.pix_w)
        vbox.add_widget(fr, stretch=1)

        self._rebuild_table()

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        cbox1 = Widgets.ComboBox()
        index = 0
        for i in self.sizes:
            j = 1 + i*2
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
        #cbox2.setMinimumContentsLength(8)
        btns.add_widget(cbox2, stretch=0)

        btn1 = Widgets.Button("Delete")
        btn1.add_callback('activated', lambda w: self.clear_mark_cb())
        btn1.set_tooltip("Delete selected mark")
        btns.add_widget(btn1, stretch=0)

        btn2 = Widgets.Button("Delete All")
        btn2.add_callback('activated', lambda w: self.clear_all())
        btn2.set_tooltip("Clear all marks")
        btns.add_widget(btn2, stretch=0)
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
            ('Font size:', 'label', 'Font size', 'combobox'),
            ]
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        b.font_size.set_tooltip("Set font size for pixel display")
        for size in (8, 9, 10, 11, 12, 14, 16):
            b.font_size.append_text(str(size))
        b.font_size.show_text(str(self.fontsize))
        b.font_size.add_callback('activated', self.set_font_size_cb)

        vbox2.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(vbox2, stretch=1)

        ## spacer = Widgets.Label('')
        ## vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(btns, stretch=0)
        container.add_widget(top, stretch=1)

    def select_mark(self, tag, pan=True):
        # deselect the current selected mark, if there is one
        if self.mark_selected is not None:
            try:
                obj = self.canvas.get_object_by_tag(self.mark_selected)
                obj.set_attr_all(color=self.mark_color)
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

    def clear_all(self):
        self.canvas.delete_all_objects()
        for name in self.marks:
            self.w.marks.delete_alpha(name)
        self.marks = ['None']
        self.w.marks.append_text('None')
        self.w.marks.set_index(0)
        self.mark_selected = None

    def set_font_size_cb(self, w, index):
        self.fontsize = self.fontsizes[index]
        self._rebuild_table()

    def plot(self, data, x1, y1, x2, y2, data_x, data_y, radius,
             maxv=9):

        width, height = self.fitsimage.get_dims(data)
        if self.txt_arr is None:
            return

        maxval = numpy.nanmax(data)
        minval = numpy.nanmin(data)
        avgval = numpy.average(data)
        fmt_cell = self.fmt_cell

        # can we do this with a numpy.vectorize() fn call and
        # speed things up?
        for i in range(width):
            for j in range(height):
                self.txt_arr[i][j].text = fmt_cell.format(data[i][j])

        # append statistics line
        fmt_stat = "  Min: %s  Max: %s  Avg: %s" % (fmt_cell, fmt_cell,
                                                    fmt_cell)
        self.sum_arr[0].text = fmt_stat.format(minval, maxval, avgval)

        # update the pixtable
        self.pixview.redraw(whence=3)

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def instructions(self):
        self.tw.set_text("""Move cursor around to see surrounding pixel values.
""")

    def start(self):
        self.instructions()
        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)
        self.resume()

    def stop(self):
        # remove the canvas from the image
        self.canvas.ui_setActive(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass
        self.tw = None

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_setActive(True)
        self.redo()

    def redo(self):
        if self.tw is None:
            return
        # cut out and set the pixel table data
        image = self.fitsimage.get_image()

        if image is None:
            return

        # We report the value across the pixel, even though the coords
        # change halfway across the pixel
        data_x, data_y = int(self.lastx+0.5), int(self.lasty+0.5)

        # cutout image data
        data, x1, y1, x2, y2 = image.cutout_radius(data_x, data_y,
                                                   self.pixtbl_radius)
        self.plot(data, x1, y1, x2, y2, self.lastx, self.lasty,
                  self.pixtbl_radius, maxv=9)

    def _rebuild_table(self):
        canvas = self.pixview.get_canvas()
        canvas.delete_all_objects(redraw=False)

        Text = canvas.get_draw_class('text')
        ex_txt = Text(0, 0, text='5', fontsize=self.fontsize, font=self.font)
        font_wd, font_ht = self.fitsimage.renderer.get_dimensions(ex_txt)
        max_wd = self.maxdigits + 2
        crdmap = self.pixview.get_coordmap('canvas')

        rows = []
        objs = []
        max_x = 0
        for row in range(self.pixtbl_radius*2+1):
            cols = []
            for col in range(self.pixtbl_radius*2+1):
                col_wd = font_wd * max_wd
                x = col_wd * col + 4
                max_x = max(max_x, x + col_wd)
                y = font_ht * (row + 1) + 4

                color = 'lightgreen'
                if (row == col) and (row == self.pixtbl_radius):
                    color = 'pink'

                dx, dy = crdmap.to_data(x, y)
                text_obj = Text(dx, dy, text='', font=self.font,
                                color=color, fontsize=self.fontsize,
                                coord='data')
                objs.append(text_obj)
                cols.append(text_obj)

            rows.append(cols)

        self.txt_arr = numpy.array(rows)

        # add summary row(s)
        x = (font_wd + 2) + 4
        y += font_ht+20
        dx, dy = crdmap.to_data(x, y)
        s1 = Text(dx, dy, text='', font=self.font,
                  color=color, fontsize=self.fontsize,
                  coord='data')
        objs.append(s1)
        self.sum_arr = numpy.array([s1])

        # add all of the text objects to the canvas as one large
        # compound object
        CompoundObject = canvas.get_draw_class('compoundobject')
        canvas.add(CompoundObject(*objs), redraw=False)

        # set limits for scrolling
        self.pixview.set_limits(((0, 0), (max_x, y)), coord='canvas')

    def set_cutout_size_cb(self, w, val):
        index = w.get_index()
        self.pixtbl_radius = self.sizes[index]
        self._rebuild_table()

    def motion_cb(self, canvas, event, data_x, data_y):
        if self.mark_selected is not None:
            return False
        if self.tw is None:
            return

        self.lastx, self.lasty = data_x, data_y

        self.redo()
        return False

    def btndown_cb(self, canvas, event, data_x, data_y):
        self.add_mark(data_x, data_y)
        return True

    def add_mark(self, data_x, data_y, radius=None, color=None, style=None):
        if not radius:
            radius = self.mark_radius
        if not color:
            color = self.mark_color
        if not style:
            style = self.mark_style

        self.logger.debug("Setting mark at %d,%d" % (data_x, data_y))
        self.mark_index += 1
        tag = 'mark%d' % (self.mark_index)
        tag = self.canvas.add(self.dc.CompoundObject(
            self.dc.Point(data_x, data_y, self.mark_radius,
                          style=style, color=color,
                          linestyle='solid'),
            self.dc.Text(data_x + 10, data_y, "%d" % (self.mark_index),
                         color=color)),
                              tag=tag)
        self.marks.append(tag)
        self.w.marks.append_text(tag)
        self.select_mark(tag, pan=False)


    def __str__(self):
        return 'pixtable'

#END
