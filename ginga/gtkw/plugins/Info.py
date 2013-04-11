#
# Info.py -- FITS Info plugin for the Ginga fits viewer
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
from ginga.misc import Bunch
from ginga import GingaPlugin


class Info(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Info, self).__init__(fv)

        self.channel = {}
        self.active = None
        self.info = None

        #self.w = Bunch.Bunch()
        self.w.tooltips = self.fv.w.tooltips

        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.set_callback('field-info', self.field_info)
        fv.set_callback('active-image', self.focus_cb)
        
    def build_gui(self, container):
        nb = gtk.Notebook()
        nb.set_group_id(-30)
        nb.set_tab_pos(gtk.POS_BOTTOM)
        nb.set_scrollable(False)
        nb.set_show_tabs(False)
        nb.set_show_border(False)
        nb.show()
        self.nb = nb
        container.pack_start(self.nb, fill=True, expand=True)

    def _create_info_window(self):
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        vbox = gtk.VBox()
        captions = (('Name', 'label'), ('Object', 'label'),
                    ('X', 'label'), ('Y', 'label'), ('Value', 'label'),
                    ('RA', 'label'), ('DEC', 'label'),
                    ('Equinox', 'label'), ('Dimensions', 'label'),
                    #('Slices', 'label', 'MultiDim', 'button'),
                    ('Min', 'label'), ('Max', 'label'),
                    ('Zoom', 'label'), 
                    ('Cut Low', 'xlabel', '@Cut Low', 'entry'),
                    ('Cut High', 'xlabel', '@Cut High', 'entry'),
                    ('Auto Levels', 'button', 'Cut Levels', 'button'), 
                    ('Cut New', 'label'), ('Zoom New', 'label'), 
                    ('Preferences', 'button'), 
                    )

        w, b = GtkHelp.build_info(captions)
        self.w.tooltips.set_tip(b.cut_levels, "Set cut levels manually")
        self.w.tooltips.set_tip(b.auto_levels, "Set cut levels by algorithm")
        self.w.tooltips.set_tip(b.cut_low, "Set low cut level (press Enter)")
        self.w.tooltips.set_tip(b.cut_high, "Set high cut level (press Enter)")
        self.w.tooltips.set_tip(b.preferences, "Set preferences for this channel")
        #self.w.tooltips.set_tip(b.multidim, "View other HDUs or slices")
        vbox.pack_start(w, padding=0, fill=True, expand=True)

        # Convenience navigation buttons
        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_CENTER)
        btns.set_spacing(3)
        btns.set_child_size(15, -1)

        bw = Bunch.Bunch()
        for tup in (
            #("Load", 'button', 'fits_open_48', "Open an image file"),
            ("Prev", 'button', 'prev_48', "Go to previous image"),
            ("Next", 'button', 'next_48', "Go to next image"),
            ("Zoom In", 'button', 'zoom_in_48', "Zoom in"),
            ("Zoom Out", 'button', 'zoom_out_48', "Zoom out"),
            ("Zoom Fit", 'button', 'zoom_fit_48', "Zoom to fit window size"),
            ("Zoom 1:1", 'button', 'zoom_100_48', "Zoom to 100% (1:1)"),
            #("Quit", 'button', 'exit_48', "Quit the program"),
            ):

            btn = self.fv.make_button(*tup)
            name = tup[0]
            if tup[3]:
                self.w.tooltips.set_tip(btn, tup[3])
                
            bw[GtkHelp._name_mangle(name, pfx='btn_')] = btn
            btns.pack_end(btn, padding=4)

        #self.w.btn_load.connect("clicked", lambda w: self.gui_load_file())
        bw.btn_prev.connect("clicked", lambda w: self.fv.prev_img())
        bw.btn_next.connect("clicked", lambda w: self.fv.next_img())
        bw.btn_zoom_in.connect("clicked", lambda w: self.fv.zoom_in())
        bw.btn_zoom_out.connect("clicked", lambda w: self.fv.zoom_out())
        bw.btn_zoom_fit.connect("clicked", lambda w: self.fv.zoom_fit())
        bw.btn_zoom_1_1.connect("clicked", lambda w: self.fv.zoom_1_to_1())

        vbox.pack_start(btns, padding=4, fill=True, expand=False)
        vbox.show_all()

        sw.add_with_viewport(vbox)
        sw.set_size_request(-1, 420)
        sw.show_all()
        return sw, b

    def add_channel(self, viewer, chinfo):
        sw, winfo = self._create_info_window()
        chname = chinfo.name

        self.nb.append_page(sw, gtk.Label(chname))
        index = self.nb.page_num(sw)
        info = Bunch.Bunch(widget=sw, winfo=winfo,
                           nbindex=index)
        self.channel[chname] = info

        winfo.cut_low.connect('activate', self.cut_levels,
                              chinfo.fitsimage, info)
        winfo.cut_high.connect('activate', self.cut_levels,
                              chinfo.fitsimage, info)
        winfo.cut_levels.connect('clicked', self.cut_levels,
                              chinfo.fitsimage, info)
        winfo.auto_levels.connect('clicked', self.auto_levels,
                              chinfo.fitsimage, info)
        winfo.preferences.connect('clicked', self.preferences,
                                  chinfo)

        fitsimage = chinfo.fitsimage
        fitsimage.set_callback('image-set', self.new_image_cb, info)
        fitsimage.set_callback('cut-set', self.cutset_cb, info)
        fitsimage.set_callback('zoom-set', self.zoomset_cb, info)
        fitsimage.set_callback('autocuts', self.autocuts_cb, info)
        fitsimage.set_callback('autozoom', self.autozoom_cb, info)

    def delete_channel(self, viewer, chinfo):
        self.logger.debug("TODO: delete channel %s" % (chinfo.name))
        
    # CALLBACKS
    
    def new_image_cb(self, fitsimage, image, info):
        self.set_info(info, fitsimage)
        return True
        
    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name
        print "info focus cb: chname=%s" % (chname)

        if self.active != chname:
            index = self.channel[chname].nbindex
            self.nb.set_current_page(index)
            self.active = chname
            self.info = self.channel[self.active]
            print "Switched page to %d" % (index)

        self.set_info(self.info, fitsimage)
        return True
        
    def zoomset_cb(self, fitsimage, zoomlevel, scale_x, scale_y, info):
        """This callback is called when the main window is zoomed.
        """
        # Set text showing zoom factor (1X, 2X, etc.)
        if scale_x == scale_y:
            text = self.fv.scale2text(scale_x)
        else:
            textx = self.fv.scale2text(scale_x)
            texty = self.fv.scale2text(scale_y)
            text = "X: %s  Y: %s" % (textx, texty)
        info.winfo.zoom.set_text(text)
        
    def cutset_cb(self, fitsimage, loval, hival, info):
        #info.winfo.cut_low.set_text('%.2f' % (loval))
        info.winfo.lbl_cut_low.set_text('%.2f' % (loval))
        #info.winfo.cut_high.set_text('%.2f' % (hival))
        info.winfo.lbl_cut_high.set_text('%.2f' % (hival))

    def autocuts_cb(self, fitsimage, option, info):
        info.winfo.cut_new.set_text(option)

    def autozoom_cb(self, fitsimage, option, info):
        info.winfo.zoom_new.set_text(option)

    # LOGIC

    def preferences(self, w, chinfo):
        self.fv.start_operation('Preferences')
        return True
        
    def set_info(self, info, fitsimage):
        image = fitsimage.get_image()
        header = image.get_header()
        
        # Update info panel
        name = image.get('name', 'Noname')
        info.winfo.name.set_text(name)
        objtext = header.get('OBJECT', 'UNKNOWN')
        info.winfo.object.set_text(objtext)
        equinox = header.get('EQUINOX', '')
        info.winfo.equinox.set_text(str(equinox))

        # Show min, max values
        width, height = fitsimage.get_data_size()
        minval, maxval = image.get_minmax(noinf=False)
        info.winfo.max.set_text(str(maxval))
        info.winfo.min.set_text(str(minval))

        # Show cut levels
        loval, hival = fitsimage.get_cut_levels()
        #info.winfo.cut_low.set_text('%.2f' % (loval))
        info.winfo.lbl_cut_low.set_text('%.2f' % (loval))
        #info.winfo.cut_high.set_text('%.2f' % (hival))
        info.winfo.lbl_cut_high.set_text('%.2f' % (hival))

        # Show dimensions
        dim_txt = "%dx%d" % (width, height)
        info.winfo.dimensions.set_text(dim_txt)

        # update zoom indicator
        scalefactor = fitsimage.get_scale()
        text = self.fv.scale2text(scalefactor)
        info.winfo.zoom.set_text(text)

        # update cut new/zoom new indicators
        t_ = fitsimage.get_settings()
        info.winfo.cut_new.set_text(t_['autocuts'])
        info.winfo.zoom_new.set_text(t_['autozoom'])


    def field_info(self, viewer, fitsimage, info):
        # TODO: can this be made more efficient?
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name
        obj = self.channel[chname]

        obj.winfo.x.set_text("%.3f" % info.x)
        obj.winfo.y.set_text("%.3f" % info.y)
        obj.winfo.value.set_text(str(info.value))
        obj.winfo.ra.set_text(info.ra_txt)
        obj.winfo.dec.set_text(info.dec_txt)

    def cut_levels(self, w, fitsimage, info):
        try:
            loval = float(info.winfo.cut_low.get_text())
            hival = float(info.winfo.cut_high.get_text())

            return fitsimage.cut_levels(loval, hival)
        except Exception, e:
            self.fv.showStatus("Error cutting levels: %s" % (str(e)))
            
        return True

    def auto_levels(self, w, fitsimage, info):
        fitsimage.auto_levels()

    def __str__(self):
        return 'info'
    
#END
