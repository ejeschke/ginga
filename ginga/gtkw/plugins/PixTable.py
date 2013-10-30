#
# PixTable.py -- Pixel Table plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk
import numpy

from ginga.gtkw import GtkHelp
from ginga.gtkw import ImageViewCanvasTypesGtk as CanvasTypes
from ginga import GingaPlugin


class PixTable(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(PixTable, self).__init__(fv, fitsimage)

        self.layertag = 'pixtable-canvas'
        self.pan2mark = False

        canvas = CanvasTypes.DrawingCanvas()
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

    def build_gui(self, container):
        # Paned container is just to provide a way to size the graph
        # to a reasonable size
        box = gtk.VPaned()
        container.pack_start(box, expand=True, fill=True)
        
        # Make the histogram plot
        vbox = gtk.VBox()

        self.msgFont = self.fv.getFont('fixedFont', 10)
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_NONE)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.modify_font(self.msgFont)
        self.tw = tw

        fr = gtk.Frame(label=" Pixel Values ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.set_label_align(0.1, 0.5)
        fr.add(tw)
        fr.show_all()
        vbox.pack_start(fr, padding=4, fill=True, expand=False)
        
        box.pack1(vbox, resize=True, shrink=True)

        hbox = gtk.HBox(spacing=4)
        combobox = GtkHelp.combo_box_new_text()
        index = 0
        for i in self.sizes:
            j = 1 + i*2
            name = "%dx%d" % (j, j)
            combobox.insert_text(index, name)
            index += 1
        index = self.sizes.index(self.pixtbl_radius)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_cutout_size)
        combobox.set_tooltip_text("Select size of pixel table")
        hbox.pack_start(combobox, fill=False, expand=False)

        # control for selecting a mark
        combobox = GtkHelp.combo_box_new_text()
        for tag in self.marks:
            combobox.append_text(tag)
        if self.mark_selected == None:
            combobox.set_active(0)
        else:
            combobox.show_text(self.mark_selected)
        combobox.sconnect("changed", self.mark_select_cb)
        self.w.marks = combobox
        combobox.set_tooltip_text("Select a mark")
        hbox.pack_start(combobox, fill=False, expand=False)

        btn = gtk.Button("Delete")
        btn.connect('clicked', lambda w: self.clear_mark_cb())
        btn.set_tooltip_text("Delete selected mark")
        hbox.pack_start(btn, fill=False, expand=False)
        
        btn = gtk.Button("Delete All")
        btn.connect('clicked', lambda w: self.clear_all())
        btn.set_tooltip_text("Clear all marks")
        hbox.pack_start(btn, fill=False, expand=False)
        
        btn = GtkHelp.CheckButton("Pan to mark")
        btn.set_active(self.pan2mark)
        btn.sconnect('toggled', self.pan2mark_cb)
        btn.set_tooltip_text("Pan follows selected mark")
        hbox.pack_start(btn, fill=False, expand=False)
        
        vbox.pack_start(hbox, fill=True, expand=False)
        
        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        vbox.pack_start(btns, padding=4, fill=True, expand=False)

        box.pack2(gtk.Label(), resize=True, shrink=True)

    def select_mark(self, tag, pan=True):
        # deselect the current selected mark, if there is one
        if self.mark_selected != None:
            try:
                obj = self.canvas.getObjectByTag(self.mark_selected)
                obj.setAttrAll(color=self.mark_color)
            except:
                # old object may have been deleted
                pass
            
        self.mark_selected = tag
        if tag == None:
            self.w.marks.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.marks.show_text(tag)
        obj = self.canvas.getObjectByTag(tag)
        obj.setAttrAll(color=self.select_color)
        self.lastx = obj.objects[0].x
        self.lasty = obj.objects[0].y
        if self.pan2mark and pan:
            self.fitsimage.panset_xy(self.lastx, self.lasty, redraw=True)
        self.canvas.redraw(whence=3)

        self.redo()
        
    def mark_select_cb(self, w):
        index = w.get_active()
        tag = self.marks[index]
        if index == 0:
            tag = None
        self.select_mark(tag)

    def pan2mark_cb(self, w):
        self.pan2mark = w.get_active()
        
    def clear_mark_cb(self):
        tag = self.mark_selected
        if tag == None:
            return
        index = self.marks.index(tag)
        self.canvas.deleteObjectByTag(tag)
        model = self.w.marks.get_model()
        del model[index]
        self.marks.remove(tag)
        self.w.marks.set_active(0)
        self.mark_selected = None
        
    def clear_all(self):
        self.canvas.deleteAllObjects()
        model = self.w.marks.get_model()
        model.clear()
        self.marks = ['None']
        self.w.marks.append_text('None')
        self.w.marks.set_active(0)
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
        t = tuple([i + x1 + 1 for i in xrange(width)])

        # format the buffer and insert into the tw
        l = [fmt_h % t]
        for i in xrange(height):
            t = tuple([y1 + i + 1] + list(data[i]))
            l.append(fmt_r % t)
        l.append('')

        # append statistics line
        fmt_stat = "  Min: %s  Max: %s  Avg: %s" % (fmt_cell, fmt_cell,
                                                  fmt_cell)
        l.append(fmt_stat % (minval, maxval, avgval))

        # update the text widget
        clear_tv(self.tw)
        append_tv(self.tw, '\n'.join(l))

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def start(self):
        # insert layer if it is not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)
        self.resume()

    def stop(self):
        # remove the canvas from the image
        self.canvas.ui_setActive(False)
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        
    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        self.canvas.ui_setActive(True)
        self.redo()
        
    def redo(self):
        # cut out and set the pixel table data
        image = self.fitsimage.get_image()
        data, x1, y1, x2, y2 = image.cutout_radius(self.lastx, self.lasty,
                                                   self.pixtbl_radius)
        self.plot(data, x1, y1, x2, y2, self.lastx, self.lasty,
                  self.pixtbl_radius, maxv=9)

    def set_cutout_size(self, w):
        index = w.get_active()
        self.pixtbl_radius = self.sizes[index]
        
    def motion_cb(self, canvas, button, data_x, data_y):
        if self.mark_selected != None:
            return
        self.lastx, self.lasty = data_x, data_y
        self.redo()
        return False
        
    def btndown_cb(self, canvas, button, data_x, data_y):
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
        tag = self.canvas.add(CanvasTypes.CompoundObject(
            CanvasTypes.Point(data_x, data_y, self.mark_radius,
                              style=style, color=color,
                              linestyle='solid'),
            CanvasTypes.Text(data_x + 10, data_y, "%d" % (self.mark_index),
                             color=color)),
                              tag=tag)
        self.marks.append(tag)
        self.w.marks.append_text(tag)
        self.select_mark(tag, pan=False)
        
        
    def __str__(self):
        return 'pixtable'
    

def append_tv(widget, text):
    txtbuf = widget.get_buffer()
    enditer = txtbuf.get_end_iter()
    txtbuf.place_cursor(enditer)
    txtbuf.insert_at_cursor(text)
    enditer = txtbuf.get_end_iter()
    txtbuf.place_cursor(enditer)
#    widget.scroll_to_iter(enditer, False, 0, 0)

def clear_tv(widget):
    txtbuf = widget.get_buffer()
    startiter = txtbuf.get_start_iter()
    enditer = txtbuf.get_end_iter()
    txtbuf.delete(startiter, enditer)


#END
        
