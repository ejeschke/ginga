#
# Zoom.py -- Zoom plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

from ginga.qtw import ImageViewCanvasQt
from ginga.qtw import ImageViewCanvasTypesQt as CanvasTypes
from ginga.misc.plugins import ZoomBase


class Zoom(ZoomBase.ZoomBase):

    def build_gui(self, container):
        vpaned = QtGui.QSplitter()
        vpaned.setOrientation(QtCore.Qt.Vertical)
        
        width, height = 300, 300

        zi = ImageViewCanvasQt.ImageViewCanvas(logger=self.logger)
        zi.enable_autozoom('off')
        zi.enable_autocuts('off')
        #zi.set_scale_limits(0.001, 1000.0)
        zi.zoom_to(self.default_zoom, redraw=False)
        settings = zi.get_settings()
        settings.getSetting('zoomlevel').add_callback('set',
                               self.zoomset, zi)
        #zi.add_callback('none-move', self.showxy)
        zi.set_bg(0.4, 0.4, 0.4)
        zi.show_pan_mark(True, redraw=False)
        zi.set_desired_size(width, height)
        self.zoomimage = zi

        bd = zi.get_bindings()
        bd.enable_zoom(False)
        bd.enable_pan(False)
        bd.enable_cmap(False)

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
                    ("Refresh Interval", 'spinbutton'),
                    ('Defaults', 'button'),
                    )

        w, b = QtHelp.build_info(captions)
        b.zoom.setText(self.fv.scale2text(zi.get_scale()))
        self.wzoom = b
        b.relative_zoom.setChecked(not self.t_abszoom)
        b.relative_zoom.stateChanged.connect(self.set_absrel_cb)
        b.defaults.clicked.connect(self.set_defaults)
        b.refresh_interval.setRange(0, 200)
        b.refresh_interval.setSingleStep(1)
        b.refresh_interval.setWrapping(True)
        b.refresh_interval.setValue(int(self.refresh_interval * 1000))
        b.refresh_interval.valueChanged.connect(self.set_refresh_cb)
        vbox.addWidget(w, stretch=0)

        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(False)
        sw.setWidget(widget)

        #widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed))
        vpaned.addWidget(sw)
        sw.show()

        container.addWidget(vpaned, stretch=1)
       
    # CALLBACKS

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
    
    def zoomset(self, setting, zoomlevel, fitsimage):
        scalefactor = fitsimage.get_scale()
        self.logger.debug("scalefactor = %.2f" % (scalefactor))
        text = self.fv.scale2text(scalefactor)
        self.wzoom.zoom.setText(text)
        
    def set_radius_cb(self):
        val = self.w_radius.value()
        self.set_radius(val)
        
    def set_refresh_cb(self, val):
        self.refresh_interval = val / 1000.0
        self.logger.debug("Setting refresh time to %.4f sec" % (
            self.refresh_interval))
        
    
#END
