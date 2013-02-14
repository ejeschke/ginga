#
# Zoom.py -- Zoom plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from PyQt4 import QtGui, QtCore
import QtHelp

import Bunch

import FitsImageCanvasQt
import FitsImageCanvasTypesQt as CanvasTypes
import GingaPlugin


class Zoom(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Zoom, self).__init__(fv)

        self.zoomimage = None
        self.default_radius = 30
        self.default_zoom = 3
        self.zoom_radius = self.default_radius
        self.zoom_amount = self.default_zoom
        self.zoom_x = 0
        self.zoom_y = 0
        self.zoomcenter = None
        self.t_abszoom = True
        self.zoomtask = None
        self.fitsimage_focus = None
        self.lagtime = 2

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('active-image', self.focus_cb)

    def initialize(self, container):
        vpaned = QtGui.QSplitter()
        vpaned.setOrientation(QtCore.Qt.Vertical)
        
        width, height = 200, 200

        zi = FitsImageCanvasQt.FitsImageCanvas(logger=self.logger)
        zi.enable_autozoom('off')
        zi.enable_autocuts('off')
        zi.enable_zoom(False)
        #zi.set_scale_limits(0.001, 1000.0)
        zi.zoom_to(self.default_zoom, redraw=False)
        zi.add_callback('zoom-set', self.zoomset)
        #zi.add_callback('motion', self.showxy)
        zi.set_bg(0.4, 0.4, 0.4)
        self.zoomimage = zi

        iw = zi.get_widget()
        #iw.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding))
        iw.resize(width, height)
        vpaned.addWidget(iw)

        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        widget.setLayout(vbox)
        vbox.addWidget(QtGui.QLabel("Zoom Radius:"), stretch=0)

        adj = QtGui.QSlider(QtCore.Qt.Horizontal)
        adj.setMinimum(1)
        adj.setMaximum(100)
        adj.setValue(self.zoom_radius)
        adj.resize(200, -1)
        adj.setTracking(True)
        self.w_radius = adj
        adj.valueChanged.connect(self.set_radius_cb)
        vbox.addWidget(adj, stretch=0)

        vbox.addWidget(QtGui.QLabel("Zoom Amount:"), stretch=0)

        adj = QtGui.QSlider(QtCore.Qt.Horizontal)
        adj.setMinimum(-20)
        adj.setMaximum(30)
        adj.setValue(self.zoom_amount)
        adj.resize(200, -1)
        adj.setTracking(True)
        self.w_amount = adj
        adj.valueChanged.connect(self.set_amount_cb)
        vbox.addWidget(adj, stretch=0)

        captions = (('Zoom', 'label'),
                    ("Relative Zoom", 'checkbutton'),
                    ("Lag Time", 'spinbutton'),
                    ('Defaults', 'button'),
            )

        w, b = QtHelp.build_info(captions)
        b.zoom.setText(self.fv.scale2text(zi.get_scale()))
        self.wzoom = b
        b.relative_zoom.setChecked(not self.t_abszoom)
        b.relative_zoom.stateChanged.connect(self.set_absrel_cb)
        b.defaults.clicked.connect(self.set_defaults)
        b.lag_time.setRange(0, 20)
        b.lag_time.setSingleStep(1)
        b.lag_time.setWrapping(True)
        b.lag_time.setValue(self.lagtime)
        b.lag_time.valueChanged.connect(self.setlag_cb)
        vbox.addWidget(w, stretch=0)

        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(False)
        sw.setWidget(widget)

        #widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed))
        vpaned.addWidget(sw)
        sw.show()

        container.addWidget(vpaned, stretch=1)

       
    def prepare(self, fitsimage):
        fitsimage.add_callback('image-set', self.new_image_cb)
        #fitsimage.add_callback('focus', self.focus_cb)
        # TODO: should we add our own canvas instead?
        fitsimage.add_callback('motion', self.motion)
        fitsimage.ui_setActive(True)
        fitsimage.add_callback('cut-set', self.cutset_cb)
        fitsimage.add_callback('transform', self.transform_cb)
        fitsimage.add_callback('rotate', self.rotate_cb)
        fitsimage.add_callback('zoom-set', self.zoomset_cb)

    def add_channel(self, viewer, chinfo):
        self.prepare(chinfo.fitsimage)

    # CALLBACKS

    def new_image_cb(self, fitsimage, image):
        if fitsimage != self.fv.getfocus_fitsimage():
            return True

        self.fitsimage_focus = fitsimage
        # Reflect transforms, colormap, etc.
        fitsimage.copy_attributes(self.zoomimage,
                                  ['transforms', 'cutlevels',
                                   'rgbmap'],
                                  redraw=False)
                                  
        ## data = image.get_data()
        ## self.set_data(data)

    def focus_cb(self, viewer, fitsimage):
        self.fitsimage_focus = fitsimage
        # Reflect transforms, colormap, etc.
        fitsimage.copy_attributes(self.zoomimage,
                                  ['transforms', 'cutlevels',
                                   'rgbmap', 'rotation'],
                                  redraw=False)

        # TODO: redo cutout?
        
    # Match cut-levels to the ones in the "main" image
    def cutset_cb(self, fitsimage, loval, hival):
        if fitsimage != self.fitsimage_focus:
            return True
        self.zoomimage.cut_levels(loval, hival)
        return True

    def transform_cb(self, fitsimage):
        if fitsimage != self.fitsimage_focus:
            return True
        flip_x, flip_y, swap_xy = fitsimage.get_transforms()
        self.zoomimage.transform(flip_x, flip_y, swap_xy)
        return True
        
    def rotate_cb(self, fitsimage, deg):
        if fitsimage != self.fitsimage_focus:
            return True
        self.zoomimage.rotate(deg)
        return True
        
    def _zoomset(self, fitsimage, zoomlevel):
        if fitsimage != self.fitsimage_focus:
            return True
        if self.t_abszoom:
            # Did user set to absolute zoom?
            myzoomlevel = self.zoom_amount
            
        else:
            # Amount of zoom is a relative amount
            myzoomlevel = zoomlevel + self.zoom_amount

        self.logger.debug("zoomlevel=%d myzoom=%d" % (
            zoomlevel, myzoomlevel))
        self.zoomimage.zoom_to(myzoomlevel, redraw=True)
        text = self.fv.scale2text(self.zoomimage.get_scale())
        return True
        
    def zoomset_cb(self, fitsimage, zoomlevel, scale_x, scale_y):
        """This method is called when a main FITS widget changes zoom level.
        """
        fac_x, fac_y = fitsimage.get_scale_base_xy()
        fac_x_me, fac_y_me = self.zoomimage.get_scale_base_xy()
        if (fac_x != fac_x_me) or (fac_y != fac_y_me):
            alg = fitsimage.get_zoom_algorithm()
            self.zoomimage.set_zoom_algorithm(alg)
            self.zoomimage.set_scale_base_xy(fac_x, fac_y)
        return self._zoomset(self.fitsimage_focus, zoomlevel)
        
    def set_amount_cb(self):
        """This method is called when 'Zoom Amount' control is adjusted.
        """
        val = self.w_amount.value()
        self.zoom_amount = val
        zoomlevel = self.fitsimage_focus.get_zoom()
        self._zoomset(self.fitsimage_focus, zoomlevel)
        
    def set_absrel_cb(self, tf):
        self.t_abszoom = not tf
        zoomlevel = self.fitsimage_focus.get_zoom()
        return self._zoomset(self.fitsimage_focus, zoomlevel)
        
    def set_defaults(self):
        self.t_abszoom = True
        self.wzoom.relative_zoom.setChecked(not self.t_abszoom)
        self.w_radius.setValue(self.default_radius)
        self.w_amount.setValue(self.default_zoom)
        self.zoomimage.zoom_to(self.default_zoom, redraw=False)
        
    # LOGIC
    
    def zoomset(self, fitsimage, zoomlevel, scale_x, scale_y):
        scalefactor = fitsimage.get_scale()
        self.logger.debug("scalefactor = %.2f" % (scalefactor))
        text = self.fv.scale2text(scalefactor)
        self.wzoom.zoom.setText(text)
        
    def set_radius_cb(self):
        val = self.w_radius.value()
        self.set_radius(val)
        
    def setlag_cb(self, val):
        self.logger.debug("Setting lag time to %d" % (val))
        self.lagtime = val
        
    def set_radius(self, val):
        self.logger.debug("Setting radius to %d" % val)
        self.zoom_radius = val
        fitsimage = self.fitsimage_focus
        if fitsimage == None:
            return True
        image = fitsimage.get_image()
        wd, ht = image.get_size()
        data_x, data_y = wd // 2, ht // 2
        self.showxy(fitsimage, data_x, data_y)
        
    def showxy(self, fitsimage, data_x, data_y):
        # Cut and show zoom image in zoom window
        self.zoom_x, self.zoom_y = data_x, data_y

        image = fitsimage.get_image()
        if image == None:
            # No image loaded into this channel
            return True

        # If this is a new source, then update our widget with the
        # attributes of the source
        if self.fitsimage_focus != fitsimage:
            self.focus_cb(self.fv, fitsimage)
            
        # Cut out and show the zoom detail
        #self.showzoom(image, data_x, data_y)
        try:
            self.zoomtask.stop()
        except:
            pass
        self.zoomtask = QtCore.QTimer()
        self.zoomtask.setSingleShot(True)
        self.zoomtask.timeout.connect(lambda: self.showzoom(image,
                                                            data_x, data_y))
        self.zoomtask.start(self.lagtime)
        return True

    def motion(self, fitsimage, button, data_x, data_y):
        # TODO: pass _canvas_ and cut from that
        self.showxy(fitsimage, data_x, data_y)

    def showzoom_timer(self):
        self.showzoom(self._image, self._data_x, self._data_y)
        
    def showzoom(self, image, data_x, data_y):
        # cut out and set the zoom image
        x1, y1, x2, y2 = self.cutdetail_radius(image, self.zoomimage,
                                               data_x, data_y,
                                               self.zoom_radius, redraw=True)
        # mark the pixel under the cursor
        # TODO: use a contrast scheme with alternating colors in a 2-level rect
        i1 = data_x - x1 - 0.5
        j1 = data_y - y1 - 0.5
        #self.logger.debug("i1,j1=%f,%f" % (i1, j1))
        try:
            self.zoomimage.deleteObjectByTag(self.zoomcenter, redraw=False)
        except:
            pass
        self.zoomcenter = self.zoomimage.add(CanvasTypes.Rectangle(i1, j1,
                                                                   i1+1, j1+1,
                                                                   linewidth=1,
                                                                   color='red'))
        self.zoomtask = None

    def cutdetail_radius(self, image, dstimage, data_x, data_y,
                         radius, redraw=True):
        data, x1, y1, x2, y2 = image.cutout_radius(int(data_x), int(data_y),
                                                   radius)

        dstimage.set_data(data, redraw=redraw)

        return (x1, y1, x2, y2)


    def __str__(self):
        return 'zoom'
    
#END
