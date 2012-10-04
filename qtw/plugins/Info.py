#
# Info.py -- FITS Info plugin for fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Wed Oct  3 14:31:53 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import GingaPlugin

from PyQt4 import QtGui, QtCore
import QtHelp

import numpy
import Bunch

class Info(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Info, self).__init__(fv)

        self.channel = {}
        self.active = None
        self.info = None

        self.w.tooltips = self.fv.w.tooltips

        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.set_callback('field-info', self.field_info)
        fv.set_callback('active-image', self.focus_cb)
        
    def initialize(self, container):
        nb = QtHelp.StackedWidget()
        self.nb = nb
        container.addWidget(nb, stretch=0)

    def _create_info_window(self):
        sw = QtGui.QScrollArea()

        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(vbox)
        
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

        w, b = QtHelp.build_info(captions)

        b.cut_levels.setToolTip("Set cut levels manually")
        b.auto_levels.setToolTip("Set cut levels by algorithm")
        b.cut_low.setToolTip("Set low cut level (press Enter)")
        b.cut_high.setToolTip("Set high cut level (press Enter)")
        b.preferences.setToolTip("Set preferences for this channel")
        #b.multidim.setToolTip("View other HDUs or slices")

        
        vbox.addWidget(w, stretch=0)
        
        # Convenience navigation buttons
        btns = QtGui.QWidget()
        layout = QtGui.QHBoxLayout()
        layout.setSpacing(3)
        btns.setLayout(layout)
        #btns.set_layout(gtk.BUTTONBOX_CENTER)
        #btns.set_child_size(15, -1)

        bw = Bunch.Bunch()
        for tup in (
            #("Load", 'button', 'fits_open_48', "Open an image file"),
            ("Prev", 'button', 'prev_48', "Go to previous image"),
            ("Next", 'button', 'next_48', "Go to next image"),
            ("Zoom In", 'button', 'zoom_in_48', "Zoom in"),
            ("Zoom Out", 'button', 'zoom_out_48', "Zoom out"),
            ("Zoom Fit", 'button', 'zoom_fit_48', "Zoom to fit window size"),
            ("Zoom 1:1", 'button', 'zoom_100_48', "Zoom to 100% (1:1)"),
            #("Quit", 'button', 'exit', "Quit the program"),
            ):

            btn = self.fv.make_button(*tup)
            name = tup[0]
            if tup[3]:
                btn.setToolTip(tup[3])
                
            bw[QtHelp._name_mangle(name, pfx='btn_')] = btn
            layout.addWidget(btn, stretch=0)

        #self.w.btn_load.connect("clicked", lambda w: self.gui_load_file())
        bw.btn_prev.clicked.connect(self.fv.prev_img)
        bw.btn_next.clicked.connect(self.fv.next_img)
        bw.btn_zoom_in.clicked.connect(self.fv.zoom_in)
        bw.btn_zoom_out.clicked.connect(self.fv.zoom_out)
        bw.btn_zoom_fit.clicked.connect(self.fv.zoom_fit)
        bw.btn_zoom_1_1.clicked.connect(self.fv.zoom_1_to_1)

        vbox.addWidget(btns, stretch=0)

        #widget.show()
        sw.setWidget(widget)
        return sw, b

    def add_channel(self, viewer, chinfo):
        sw, winfo = self._create_info_window()
        chname = chinfo.name

        self.nb.addTab(sw, chname)
        sw.show()
        index = self.nb.indexOf(sw)
        info = Bunch.Bunch(widget=sw, winfo=winfo,
                           nbindex=index)
        self.channel[chname] = info

        winfo.cut_low.returnPressed.connect(lambda: self.cut_levels(
            chinfo.fitsimage, info))
        winfo.cut_high.returnPressed.connect(lambda: self.cut_levels(
            chinfo.fitsimage, info))
        winfo.cut_levels.clicked.connect(lambda: self.cut_levels(
            chinfo.fitsimage, info))
        winfo.auto_levels.clicked.connect(lambda: self.auto_levels(
            chinfo.fitsimage, info))
        winfo.preferences.clicked.connect(lambda: self.preferences(
            chinfo))
        #winfo.multidim.connect('clicked', self.multidim,
        #                         chinfo, info)

        fitsimage = chinfo.fitsimage
        fitsimage.set_callback('image-set', self.new_image_cb, info)
        #fitsimage.set_callback('motion', self.motion_cb, chinfo, info)
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

        if self.active != chname:
            index = self.channel[chname].nbindex
            self.nb.setCurrentIndex(index)
            self.active = chname
            self.info = self.channel[self.active]

        self.set_info(self.info, fitsimage)
        return True
        
    def zoomset_cb(self, fitsimage, zoomlevel, scalefactor, info):
        """This callback is called when the main window is zoomed.
        """
        self.logger.debug("scalefactor = %.2f" % (scalefactor))
        # Set text showing zoom factor (1X, 2X, etc.)
        text = self.fv.scale2text(scalefactor)
        info.winfo.zoom.setText(text)
        
    def cutset_cb(self, fitsimage, loval, hival, info):
        info.winfo.cut_low.setText('%.2f' % (loval))
        info.winfo.lbl_cut_low.setText('%.2f' % (loval))
        info.winfo.cut_high.setText('%.2f' % (hival))
        info.winfo.lbl_cut_high.setText('%.2f' % (hival))

    def autocuts_cb(self, fitsimage, option, info):
        info.winfo.cut_new.setText(option)

    def autozoom_cb(self, fitsimage, option, info):
        info.winfo.zoom_new.setText(option)

    def motion_cb(self, fitsimage, button, data_x, data_y, chinfo, info):
        """Motion event in the big fits window.  Show the pointing
        information under the cursor.
        """
        if button != 0:
            return True
        
        # Note: FITS coordinates are 1-based, whereas numpy FITS arrays
        # are 0-based
        fits_x, fits_y = data_x + 1, data_y + 1
        # Get the value under the data coordinates
        try:
            value = fitsimage.get_data(data_x, data_y)

        except (Exception, FitsImage.FitsImageCoordsError):
            value = None

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = fitsimage.get_image()
            ra_txt, dec_txt = image.pixtoradec(data_x, data_y,
                                               format='str')
        except Exception, e:
            self.logger.error("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        self.set_info(fits_x, fits_y, value, ra_txt, dec_txt)
        return True

    # LOGIC

    def preferences(self, chinfo):
        self.fv.start_operation('Preferences')
        return True
        
    def set_info(self, info, fitsimage):
        image = fitsimage.get_image()
        header = image.get_header()
        
        # Update info panel
        name = image.get('name', 'Noname')
        info.winfo.name.setText(name)
        objtext = header.get('OBJECT', 'UNKNOWN')
        info.winfo.object.setText(objtext)
        equinox = header.get('EQUINOX', '')
        info.winfo.equinox.setText(str(equinox))

        # Show min, max values
        width, height = fitsimage.get_data_size()
        minval, maxval = fitsimage.get_minmax()
        info.winfo.max.setText(str(maxval))
        info.winfo.min.setText(str(minval))

        # Show cut levels
        loval, hival = fitsimage.get_cut_levels()
        #info.winfo.cut_low.setText('%.2f' % (loval))
        info.winfo.lbl_cut_low.setText('%.2f' % (loval))
        #info.winfo.cut_high.setText('%.2f' % (hival))
        info.winfo.lbl_cut_high.setText('%.2f' % (hival))

        # Show dimensions
        dim_txt = "%dx%d" % (width, height)
        info.winfo.dimensions.setText(dim_txt)

        # update zoom indicator
        scalefactor = fitsimage.get_scale()
        text = self.fv.scale2text(scalefactor)
        info.winfo.zoom.setText(text)

        # update cut new/zoom new indicators
        info.winfo.cut_new.setText(fitsimage.t_autolevels)
        info.winfo.zoom_new.setText(fitsimage.t_autoscale)
        


    def field_info(self, viewer, fitsimage,
                   fits_x, fits_y, value, ra_txt, dec_txt):
        # TODO: can this be made more efficient?
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name
        info = self.channel[chname]
        
        #info.winfo.x.setText(str(fits_x))
        #info.winfo.y.setText(str(fits_y))
        info.winfo.x.setText("%.3f" % fits_x)
        info.winfo.y.setText("%.3f" % fits_y)
        info.winfo.value.setText(str(value))
        info.winfo.ra.setText(ra_txt)
        info.winfo.dec.setText(dec_txt)

    def cut_levels(self, fitsimage, info):
        try:
            loval = float(info.winfo.cut_low.text())
            hival = float(info.winfo.cut_high.text())

            return fitsimage.cut_levels(loval, hival)
        except Exception, e:
            self.fv.showStatus("Error cutting levels: %s" % (str(e)))
            
        return True

    def auto_levels(self, fitsimage, info):
        fitsimage.auto_levels()

    def __str__(self):
        return 'info'
    
#END
