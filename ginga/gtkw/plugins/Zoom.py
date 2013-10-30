#
# Zoom.py -- Zoom plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org) 
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import gtk
from ginga.gtkw import GtkHelp, gtksel

from ginga.gtkw import ImageViewCanvasGtk
from ginga.gtkw import ImageViewCanvasTypesGtk as CanvasTypes
from ginga.misc.plugins import ZoomBase


class Zoom(ZoomBase.ZoomBase):

    def build_gui(self, container):

        vpaned = gtk.VPaned()
    
        width, height = 300, 300

        # Uncomment to debug; passing parent logger generates too
        # much noise in the main logger
        #zi = ImageViewCanvasGtk.ImageViewCanvas(logger=self.logger)
        zi = ImageViewCanvasGtk.ImageViewCanvas(logger=None)
        zi.set_desired_size(width, height)
        zi.enable_autozoom('off')
        zi.enable_autocuts('off')
        #zi.set_scale_limits(0.001, 1000.0)
        zi.zoom_to(self.default_zoom, redraw=False)
        settings = zi.get_settings()
        settings.getSetting('zoomlevel').add_callback('set',
                               self.zoomset, zi)
        zi.set_bg(0.4, 0.4, 0.4)
        zi.show_pan_mark(True, redraw=False)
        self.zoomimage = zi

        bd = zi.get_bindings()
        bd.enable_zoom(False)
        bd.enable_pan(False)
        bd.enable_cmap(False)

        iw = zi.get_widget()
        vpaned.pack1(iw, resize=True, shrink=True)

        vbox = gtk.VBox()
        vbox.pack_start(gtk.Label("Zoom Radius:"), padding=2,
                        fill=True, expand=False)

        adj = gtk.Adjustment(lower=1, upper=100)
        adj.set_value(self.zoom_radius)
        scale = GtkHelp.HScale(adj)
        #scale.set_size_request(width, -1)
        scale.set_digits(0)
        scale.set_draw_value(True)
        scale.set_value_pos(gtk.POS_BOTTOM)
        self.w_radius = scale
        scale.connect('value-changed', self.set_radius_cb)
        vbox.pack_start(scale, padding=0, fill=True, expand=False)

        vbox.pack_start(gtk.Label("Zoom Amount:"), padding=2,
                        fill=True, expand=False)

        adj = gtk.Adjustment(lower=-20, upper=30)
        adj.set_value(self.zoom_amount)
        scale = GtkHelp.HScale(adj)
        #scale.set_size_request(width, -1)
        scale.set_digits(0)
        scale.set_draw_value(True)
        scale.set_value_pos(gtk.POS_BOTTOM)
        self.w_amount = scale
        scale.connect('value-changed', self.set_amount_cb)
        vbox.pack_start(scale, padding=0, fill=True, expand=False)

        captions = (('Zoom', 'label'),
                    ("Relative Zoom", 'checkbutton'),
                    ("Refresh Interval", 'spinbutton'),
                    ('Defaults', 'button'),
                    )

        w, b = GtkHelp.build_info(captions)
        b.zoom.set_text(self.fv.scale2text(zi.get_scale()))
        self.wzoom = b
        b.relative_zoom.set_active(not self.t_abszoom)
        b.relative_zoom.sconnect("toggled", self.set_absrel_cb)
        b.defaults.connect("clicked", lambda w: self.set_defaults())
        adj = b.refresh_interval.get_adjustment()
        adj.configure(0, 0, 200, 1, 1, 0)
        adj.set_value(int(self.refresh_interval * 1000))
        b.refresh_interval.set_digits(0)
        b.refresh_interval.set_wrap(True)
        b.refresh_interval.connect('value-changed', self.set_refresh_cb)
        vbox.pack_start(w, padding=4, fill=True, expand=False)

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(vbox)

        vpaned.pack2(sw, resize=True, shrink=True)
        vpaned.show_all()
        vpaned.set_position(height)
        
        container.pack_start(vpaned, padding=0, fill=True, expand=True)

    def prepare(self, fitsimage):
        fitssettings = fitsimage.get_settings()
        zoomsettings = self.zoomimage.get_settings()
        fitsimage.add_callback('image-set', self.new_image_cb)
        #fitsimage.add_callback('focus', self.focus_cb)
        # TODO: should we add our own canvas instead?
        fitsimage.add_callback('motion', self.motion_cb)
        for name in ['cuts']:
            fitssettings.getSetting(name).add_callback('set',
                               self.cutset_cb, fitsimage)
        fitsimage.add_callback('transform', self.transform_cb)
        fitssettings.copySettings(zoomsettings, ['rot_deg'])
        fitssettings.getSetting('rot_deg').add_callback('set', self.rotate_cb, fitsimage)
        fitssettings.getSetting('zoomlevel').add_callback('set',
                               self.zoomset_cb, fitsimage)

    # CALLBACKS

    def set_amount_cb(self, rng):
        """This method is called when 'Zoom Amount' control is adjusted.
        """
        val = rng.get_value()
        self.zoom_amount = val
        zoomlevel = self.fitsimage_focus.get_zoom()
        self._zoomset(self.fitsimage_focus, zoomlevel)
        
    def set_absrel_cb(self, w):
        self.t_abszoom = not w.get_active()
        zoomlevel = self.fitsimage_focus.get_zoom()
        return self._zoomset(self.fitsimage_focus, zoomlevel)
        
    def set_defaults(self):
        self.t_abszoom = True
        self.wzoom.relative_zoom.set_active(not self.t_abszoom)
        self.w_radius.set_value(self.default_radius)
        self.w_amount.set_value(self.default_zoom)
        self.zoomimage.zoom_to(self.default_zoom, redraw=False)
        
    # LOGIC
    
    def zoomset(self, setting, zoomlevel, fitsimage):
        text = self.fv.scale2text(self.zoomimage.get_scale())
        self.wzoom.zoom.set_text(text)
        
    def set_radius_cb(self, rng):
        val = rng.get_value()
        self.set_radius(val)
        
    def set_refresh_cb(self, w):
        val = w.get_value()
        self.refresh_interval = val / 1000.0
        self.logger.debug("Setting refresh time to %.4f sec" % (
            self.refresh_interval))
        
    
#END
