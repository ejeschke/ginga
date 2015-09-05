#
# PixTable.py -- Pixel Table plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.gw import Widgets
from ginga import GingaPlugin


class PixTable(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(PixTable, self).__init__(fv, fitsimage)

        self.layertag = 'pixtable-canvas'
        self.pan2mark = False

        self.dc = self.fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        ## canvas.enable_draw(True)
        ## canvas.set_drawtype('point', color='pink')
        ## canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('cursor-down', self.btndown_cb)
        canvas.set_callback('none-move', self.motion_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        # For pixel table
        self.pixtbl_radius = 2
        self.sizes = [ 1, 2, 3, 4 ]
        self.lastx = 0
        self.lasty = 0

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

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Pixel Values")

        # Make the values table as a text widget
        msgFont = self.fv.getFont('fixedFont', 10)
        tw = Widgets.TextArea(wrap=False, editable=False)
        tw.set_font(msgFont)
        self.tw = tw

        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=1)

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
        cbox1.add_callback('activated', self.set_cutout_size)
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
                obj = self.canvas.getObjectByTag(self.mark_selected)
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
        obj = self.canvas.getObjectByTag(tag)
        obj.setAttrAll(color=self.select_color)
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
        self.canvas.deleteObjectByTag(tag)
        self.w.marks.delete_alpha(tag)
        self.marks.remove(tag)
        self.w.marks.set_index(0)
        self.mark_selected = None

    def clear_all(self):
        self.canvas.deleteAllObjects()
        for name in self.marks:
            self.w.marks.delete_alpha(name)
        self.marks = ['None']
        self.w.marks.append_text('None')
        self.w.marks.set_index(0)
        self.mark_selected = None

    def plot(self, data, x1, y1, x2, y2, data_x, data_y, radius,
             maxv=9):

        width, height = self.fitsimage.get_dims(data)

        maxval = numpy.nanmax(data)
        minval = numpy.nanmin(data)
        avgval = numpy.average(data)

        maxdigits = 9
        sep = '  '
        # make format string for a row
        fmt_cell = '%%%d.2f' % maxdigits
        fmt_r = (fmt_cell + sep) * width
        fmt_r = '%6d | ' + fmt_r

        fmt_h = (('%%%dd' % maxdigits) + sep) * width
        fmt_h = ('%6s | ') % '' + fmt_h
        t = tuple([i + x1 + 1 for i in range(width)])

        # format the buffer and insert into the tw
        l = [fmt_h % t]
        for i in range(height):
            t = tuple([y1 + i + 1] + list(data[i]))
            l.append(fmt_r % t)
        l.append('')

        # append statistics line
        fmt_stat = "  Min: %s  Max: %s  Avg: %s" % (fmt_cell, fmt_cell,
                                                  fmt_cell)
        l.append(fmt_stat % (minval, maxval, avgval))

        # update the text widget
        self.tw.set_text('\n'.join(l))

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def instructions(self):
        self.tw.set_text("""Move cursor around to see surrounding pixel values.
""")

    def start(self):
        self.instructions()
        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)
        self.resume()

    def stop(self):
        # remove the canvas from the image
        self.canvas.ui_setActive(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.deleteObjectByTag(self.layertag)
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
        data, x1, y1, x2, y2 = image.cutout_radius(self.lastx, self.lasty,
                                                   self.pixtbl_radius)
        self.plot(data, x1, y1, x2, y2, self.lastx, self.lasty,
                  self.pixtbl_radius, maxv=9)

    def set_cutout_size(self, w, val):
        index = w.get_index()
        self.pixtbl_radius = self.sizes[index]

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
