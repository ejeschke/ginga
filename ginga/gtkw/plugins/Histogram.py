#
# Histogram.py -- Histogram plugin for Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk

from ginga.misc.plugins import HistogramBase
from ginga.gtkw import GtkHelp
from ginga.gtkw import Plot

class Histogram(HistogramBase.HistogramBase):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Histogram, self).__init__(fv, fitsimage)

        self.gui_up = False

    def build_gui(self, container):
        # Paned container is just to provide a way to size the graph
        # to a reasonable size
        box = gtk.VPaned()
        container.pack_start(box, expand=True, fill=True)

        # Make the histogram plot
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

        self.plot = Plot.Plot(self.logger)
        w = self.plot.get_widget()
        vbox.pack_start(w, padding=4, fill=True, expand=True)

        captions = (('Cut Low:', 'label', 'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High', 'entry', 'Cut Levels', 'button'),
                    ('Auto Levels', 'button'),
                    ('Log Histogram', 'checkbutton', 'Plot By Cuts', 'checkbutton'),
                    ('NumBins:', 'label', 'NumBins', 'entry'),
                    )

        w, b = GtkHelp.build_info2(captions)
        self.w.update(b)
        b.cut_levels.set_tooltip_text("Set cut levels manually")
        b.auto_levels.set_tooltip_text("Set cut levels by algorithm")
        b.cut_low.set_tooltip_text("Set low cut level (press Enter)")
        b.cut_high.set_tooltip_text("Set high cut level (press Enter)")
        b.log_histogram.set_tooltip_text("Use the log of the pixel values for the histogram (empty bins map to 10^-1)")
        b.plot_by_cuts.set_tooltip_text("Only show the part of the histogram between the cuts")
        b.numbins.set_tooltip_text("Number of bins for the histogram")
        b.numbins.set_text(str(self.numbins))
        b.cut_low.connect('activate', lambda w: self.cut_levels())
        b.cut_high.connect('activate', lambda w: self.cut_levels())
        b.cut_levels.connect('clicked', lambda w: self.cut_levels())
        b.auto_levels.connect('clicked', lambda w: self.auto_levels())
        b.numbins.connect('activate', lambda w: self.set_numbins_cb())

        b.log_histogram.set_active(self.plot.logy)
        b.log_histogram.connect('toggled', self.log_histogram_cb)
        b.plot_by_cuts.set_active(self.xlimbycuts)
        b.plot_by_cuts.connect('toggled', self.plot_by_cuts_cb)

        vbox.pack_start(w, padding=4, fill=True, expand=False)
        box.pack1(vbox, resize=True, shrink=True)
        box.pack2(gtk.Label(), resize=True, shrink=True)
        #self.plot.set_callback('close', lambda x: self.stop())

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)
        btns.set_child_size(15, -1)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        btn = gtk.Button("Full Image")
        btn.connect('clicked', lambda w: self.full_image())
        btns.add(btn)
        container.pack_start(btns, padding=4, fill=True, expand=False)

        self.gui_up = True

    def _getText(self, w):
        return w.get_text()

    def _setText(self, w, text):
        w.set_text(text)

    def instructions(self):
        buf = self.tw.get_buffer()
        buf.set_text("""Draw (or redraw) a region with the right mouse button.  Click or drag left mouse button to reposition region.""")
        self.tw.modify_font(self.msgFont)

    def log_histogram_cb(self, w):
        self.plot.logy = w.get_active()
        if (self.histtag is not None) and self.gui_up:
            # self.histtag == None means no data is loaded yet
            self.redo()

    def plot_by_cuts_cb(self, w):
        self.xlimbycuts = w.get_active()
        if (self.histtag is not None) and self.gui_up:
            # self.histtag == None means no data is loaded yet
            self.redo()

    def __str__(self):
        return 'histogram'

# END
