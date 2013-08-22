#
# Cuts.py -- Cuts plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk
from ginga.gtkw import GtkHelp

from ginga.gtkw import Plot
from ginga.misc.plugins import CutsBase


class Cuts(CutsBase.CutsBase):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Cuts, self).__init__(fv, fitsimage)

    def build_gui(self, container):
        # Paned container is just to provide a way to size the graph
        # to a reasonable size
        box = gtk.VPaned()
        container.pack_start(box, expand=True, fill=True)
        
        # Make the cuts plot
        vbox = gtk.VBox()

        self.msgFont = self.fv.getFont("sansFont", 14)
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
        combobox.sconnect('changed', self.cut_select_cb)
        self.w.cuts = combobox
        combobox.set_tooltip_text("Select a cut")
        hbox.pack_start(combobox, fill=False, expand=False)

        btn = gtk.Button("Delete")
        btn.connect('clicked', lambda w: self.delete_cut_cb())
        btn.set_tooltip_text("Delete selected cut")
        hbox.pack_start(btn, fill=False, expand=False)
        
        btn = gtk.Button("Delete All")
        btn.connect('clicked', lambda w: self.delete_all())
        btn.set_tooltip_text("Clear all cuts")
        hbox.pack_start(btn, fill=False, expand=False)
        
        combobox = GtkHelp.combo_box_new_text()
        for cuttype in self.cuttypes:
            combobox.append_text(cuttype)
        self.w.cuts_type = combobox
        index = self.cuttypes.index(self.cuttype)
        combobox.set_active(index)
        combobox.sconnect('changed', self.set_cutsdrawtype_cb)
        combobox.set_tooltip_text("Choose the cut type")
        hbox.pack_start(combobox, fill=False, expand=False)
        
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

    def instructions(self):
        buf = self.tw.get_buffer()
        buf.set_text("""Draw (or redraw) a line with the right mouse button.  Click or drag left button to reposition line.""")
        self.tw.modify_font(self.msgFont)
            
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
        
    def set_cutsdrawtype_cb(self, w):
        index = w.get_active()
        self.cuttype = self.cuttypes[index]
        if self.cuttype in ('free', ):
            self.canvas.set_drawtype('line', color='cyan', linestyle='dash')
        else:
            self.canvas.set_drawtype('rectangle', color='cyan',
                                     linestyle='dash')
        return True

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
        self.cutstag = None
        tag = self.tags[idx]
        if tag == 'None':
            tag = None
        self.select_cut(tag)
        if tag != None:
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
        
    def __str__(self):
        return 'cuts'
    
#END
