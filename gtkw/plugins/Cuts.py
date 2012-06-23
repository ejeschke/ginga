#
# Cuts.py -- Cuts plugin for fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:44:49 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk
import pango
import GtkHelp

import FitsImageCanvasTypesGtk as CanvasTypes
import Plot
import GingaPlugin

import numpy

class Cuts(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Cuts, self).__init__(fv, fitsimage)

        self.cutscolor = 'green'
        self.layertag = 'cuts-canvas'
        self.cutstag = None
        self.tags = ['None']
        self.count = 0
        self.colors = ['green', 'red', 'blue', 'cyan', 'pink', 'magenta']
        #self.move_together = True

        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('line', color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('button-press', self.buttondown_cb)
        canvas.set_callback('motion', self.motion_cb)
        canvas.set_callback('button-release', self.buttonup_cb)
        canvas.set_callback('key-press', self.keydown)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.w.tooltips = self.fv.w.tooltips


    def build_gui(self, container):
        # Paned container is just to provide a way to size the graph
        # to a reasonable size
        box = gtk.VPaned()
        container.pack_start(box, expand=True, fill=True)
        
        # Make the cuts plot
        vbox = gtk.VBox()

        self.msgFont = pango.FontDescription("Sans 14")
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_WORD)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.modify_font(self.msgFont)
        self.tw = tw

        fr = gtk.Frame(" Instructions ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.set_label_align(0.1, 0.5)
        fr.add(tw)
        vbox.pack_start(fr, padding=4, fill=True, expand=False)
        
        self.plot = Plot.Cuts(self.logger)
        w = self.plot.get_widget()
        vbox.pack_start(w, padding=4, fill=True, expand=True)

        hbox = gtk.HBox(spacing=4)

        # control for selecting a cut
        combobox = GtkHelp.combo_box_new_text()
        for tag in self.tags:
            combobox.append_text(tag)
        if self.cutstag == None:
            combobox.set_active(0)
        else:
            combobox.show_text(self.cutstag)
        combobox.sconnect("changed", self.cut_select_cb)
        self.w.cuts = combobox
        self.w.tooltips.set_tip(combobox, "Select a cut")
        hbox.pack_start(combobox, fill=False, expand=False)

        btn = gtk.Button("Delete")
        btn.connect('clicked', lambda w: self.delete_cut_cb())
        self.w.tooltips.set_tip(btn, "Delete selected cut")
        hbox.pack_start(btn, fill=False, expand=False)
        
        btn = gtk.Button("Delete All")
        btn.connect('clicked', lambda w: self.delete_all())
        self.w.tooltips.set_tip(btn, "Clear all cuts")
        hbox.pack_start(btn, fill=False, expand=False)
        
        ## btn = GtkHelp.CheckButton("Move together")
        ## btn.set_active(self.move_together)
        ## #btn.sconnect('toggled', self.movetogether_cb)
        ## self.w.tooltips.set_tip(btn, "Move cuts as a group")
        ## hbox.pack_start(btn, fill=False, expand=False)
        
        vbox.pack_start(hbox, fill=True, expand=False)
        
        box.pack1(vbox, resize=True, shrink=True)
        box.pack2(gtk.Label(), resize=True, shrink=True)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)
        btns.set_child_size(15, -1)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        container.pack_start(btns, padding=4, fill=True, expand=False)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def instructions(self):
        buf = self.tw.get_buffer()
        buf.set_text("""Draw (or redraw) a line with the right mouse button.  Click or drag left button to reposition line.""")
        self.tw.modify_font(self.msgFont)
            
    def start(self):
        # start line cuts operation
        self.instructions()
        self.plot.set_titles(rtitle="Cuts")

        # insert canvas, if not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add ruler layer
            self.fitsimage.add(self.canvas, tag=self.layertag)

        #self.canvas.deleteAllObjects()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a line with the right mouse button")
        self.redo()

    def stop(self):
        # remove the canvas from the image
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.fv.showStatus("")

    def select_cut(self, tag):
        # deselect the current selected cut, if there is one
        if self.cutstag != None:
            try:
                obj = self.canvas.getObjectByTag(self.cutstag)
                #obj.setAttrAll(color=self.mark_color)
            except:
                # old object may have been deleted
                pass
            
        self.cutstag = tag
        if tag == None:
            self.w.cuts.show_text('None')
            self.canvas.redraw(whence=3)
            return

        self.w.cuts.show_text(tag)
        obj = self.canvas.getObjectByTag(tag)
        #obj.setAttrAll(color=self.select_color)

        #self.redo()
        
    def cut_select_cb(self, w):
        index = w.get_active()
        tag = self.tags[index]
        if index == 0:
            tag = None
        self.select_cut(tag)

    def pan2mark_cb(self, w):
        self.pan2mark = w.get_active()
        
    def delete_cut_cb(self):
        tag = self.cutstag
        if tag == None:
            return
        index = self.tags.index(tag)
        self.canvas.deleteObjectByTag(tag)
        model = self.w.cuts.get_model()
        del model[index]
        self.tags.remove(tag)
        idx = len(self.tags) - 1
        tag = self.tags[idx]
        self.select_cut(tag)
        self.redo()
        
    def delete_all(self):
        self.canvas.deleteAllObjects()
        model = self.w.cuts.get_model()
        model.clear()
        self.tags = ['None']
        self.w.cuts.append_text('None')
        self.w.cuts.set_active(0)
        self.cutstag = None
        self.redo()
        
    def deleteCutsTag(self, tag, redraw=False):
        try:
            self.canvas.deleteObjectByTag(tag, redraw=redraw)
        except:
            pass
        try:
            self.tags.remove(tag)
        except:
            pass
        if tag == self.cutstag:
            #self.unhighlightTag(tag)
            if len(self.tags) == 0:
                self.cutstag = None
            else:
                self.cutstag = self.tags[0]
                #self.highlightTag(self.cutstag)
        
    def addCutsTag(self, tag, select=False):
        if not tag in self.tags:
            self.tags.append(tag)
            self.w.cuts.append_text(tag)

        if select:
            if self.cutstag != None:
                #self.unhighlightTag(self.cutstag)
                pass
            self.cutstag = tag
            self.w.cuts.show_text(tag)
            #self.highlightTag(self.cutstag)
        
    def replaceCutsTag(self, oldtag, newtag, select=False):
        self.addCutsTag(newtag, select=select)
        self.deleteCutsTag(oldtag)
        
    def _redo(self, cutstag, color):
        obj = self.canvas.getObjectByTag(cutstag)
        if obj.kind != 'compound':
            return True
        line = obj.objects[0]
        line.color = color
        text = obj.objects[1]
        text.color = color
        
        # Get points on the line
        points = self.fitsimage.get_pixels_on_line(int(line.x1), int(line.y1),
                                                   int(line.x2), int(line.y2))
        points = numpy.array(points)
        self.plot.cuts(points, xtitle="Line Index", ytitle="Pixel Value",
                       color=color)
        return True
    
    def redo(self):
        self.plot.clear()
        idx = 0
        for cutstag in self.tags:
            if cutstag != 'None':
                color = self.colors[idx]
                self._redo(cutstag, color)
            idx = (idx+1) % len(self.colors)

        self.canvas.redraw(whence=3)
        self.fv.showStatus("Click or drag left mouse button to reposition cuts")
        return True

    def _movecut(self, obj, data_x, data_y):
        if obj.kind == 'compound':
            line = obj.objects[0]
            lbl  = obj.objects[1]
        elif obj.kind == 'line':
            line = obj
            lbl = None
        else:
            return True
        
        # calculate center of line
        wd = line.x2 - line.x1
        dw = wd // 2
        ht = line.y2 - line.y1
        dh = ht // 2
        x, y = line.x1 + dw, line.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        x1, y1, x2, y2 = line.x1 + dx, line.y1 + dy, line.x2 + dx, line.y2 + dy

        line.x1, line.y1, line.x2, line.y2 = x1, y1, x2, y2
        if lbl:
            lbl.x += dx
            lbl.y += dy
            
    def buttondown_cb(self, canvas, button, data_x, data_y):
        return self.motion_cb(canvas, button, data_x, data_y)
    
    def motion_cb(self, canvas, button, data_x, data_y):
        if not (button == 0x1):
            return

        obj = self.canvas.getObjectByTag(self.cutstag)
        if obj.kind == 'compound':
            line = obj.objects[0]
            lbl  = obj.objects[1]
        elif obj.kind == 'line':
            line = obj
            lbl = None
        else:
            return

        line.linestyle = 'dash'
        self._movecut(obj, data_x, data_y)

        canvas.redraw(whence=3)
    
    def buttonup_cb(self, canvas, button, data_x, data_y):
        if not (button == 0x1):
            return
        
        obj = self.canvas.getObjectByTag(self.cutstag)
        if obj.kind == 'compound':
            line = obj.objects[0]
        elif obj.kind == 'line':
            line = obj
        else:
            return

        line.linestyle = 'solid'
        self._movecut(obj, data_x, data_y)
        
        self.redo()

    def keydown(self, canvas, keyname):
        if keyname == 'space':
            self.select_cut(None)
            
    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if obj.kind != 'line':
            return True
        canvas.deleteObjectByTag(tag, redraw=False)

        # calculate center of line
        wd = obj.x2 - obj.x1
        dw = wd // 2
        ht = obj.y2 - obj.y1
        dh = ht // 2
        x, y = obj.x1 + dw + 4, obj.y1 + dh + 4

        if self.cutstag:
            # Replacing a cut
            print "replacing cut position"
            cutobj = canvas.getObjectByTag(self.cutstag)
            line = cutobj.objects[0]
            line.x1, line.y1, line.x2, line.y2 = obj.x1, obj.y1, obj.x2, obj.y2
            text = cutobj.objects[1]
            text.x, text.y = x, y

        else:
            # Adding new cut
            print "adding cut position"
            self.count += 1
            tag = "cuts%d" % (self.count)
            canvas.add(CanvasTypes.CompoundObject(
                CanvasTypes.Line(obj.x1, obj.y1, obj.x2, obj.y2,
                                 color='cyan',
                                 cap='ball'),
                CanvasTypes.Text(x, y, "cuts%d" % self.count,
                                 color='cyan')),
                       tag=tag)

            self.addCutsTag(tag, select=True)

        print "redoing cut plots"
        return self.redo()
    
    def __str__(self):
        return 'cuts'
    
#END
