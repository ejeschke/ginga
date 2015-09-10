#
# Zoom.py -- Zoom plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

from ginga.gw import Widgets, Viewers
from ginga.misc import Bunch
from ginga import GingaPlugin


class Zoom(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Zoom, self).__init__(fv)

        self.zoomimage = None
        self.default_radius = 30
        self.default_zoom = 3
        self.zoom_x = 0
        self.zoom_y = 0
        self.t_abszoom = True
        self.zoomtask = fv.get_timer()
        self.zoomtask.set_callback('expired', self.showzoom_timer_cb)
        self.fitsimage_focus = None
        self.update_time = time.time()

        # read preferences for this plugin
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Zoom')
        self.settings.addDefaults(zoom_radius=self.default_radius,
                                  zoom_amount=self.default_zoom,
                                  refresh_interval=0.02)
        self.settings.load(onError='silent')

        self.zoom_radius = self.settings.get('zoom_radius', self.default_radius)
        self.zoom_amount = self.settings.get('zoom_amount', self.default_zoom)
        self.refresh_interval = self.settings.get('refresh_interval', 0.02)

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('active-image', self.focus_cb)

    def build_gui(self, container):

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         scrolled=False)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        width, height = 300, 300

        # Uncomment to debug; passing parent logger generates too
        # much noise in the main logger
        #zi = Viewers.CanvasView(logger=self.logger)
        zi = Viewers.CanvasView(logger=None)
        zi.set_desired_size(width, height)
        zi.enable_autozoom('off')
        zi.enable_autocuts('off')
        #zi.set_scale_limits(0.001, 1000.0)
        zi.zoom_to(self.default_zoom)
        settings = zi.get_settings()
        settings.getSetting('zoomlevel').add_callback('set',
                               self.zoomset, zi)
        zi.set_bg(0.4, 0.4, 0.4)
        zi.show_pan_mark(True)
        # for debugging
        zi.set_name('zoomimage')
        self.zoomimage = zi

        bd = zi.get_bindings()
        bd.enable_zoom(False)
        bd.enable_pan(False)
        bd.enable_cmap(False)

        iw = Widgets.wrap(zi.get_widget())
        vpaned = Widgets.Splitter(orientation=orientation)
        vpaned.add_widget(iw)
        vpaned.add_widget(Widgets.Label(''))
        vbox.add_widget(vpaned, stretch=1)

        vbox2 = Widgets.VBox()
        captions = (("Zoom Radius:", 'label', 'Zoom Radius', 'hscale'),
                    ("Zoom Amount:", 'label', 'Zoom Amount', 'hscale'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        self.w.zoom_radius.set_limits(1, 300, incr_value=1)
        self.w.zoom_radius.set_value(self.zoom_radius)
        self.w.zoom_radius.add_callback('value-changed', self.set_radius_cb)
        self.w.zoom_radius.set_tracking(True)

        self.w.zoom_amount.set_limits(-20, 30, incr_value=1)
        self.w.zoom_amount.set_value(self.zoom_amount)
        self.w.zoom_amount.add_callback('value-changed', self.set_amount_cb)
        self.w.zoom_amount.set_tracking(True)

        captions = (("Zoom:", 'label', 'Zoom', 'label'),
                    ("Relative Zoom", 'checkbutton'),
                    ("Refresh Interval", 'label',
                     'Refresh Interval', 'spinbutton'),
                    ("Defaults", 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.zoom.set_text(self.fv.scale2text(zi.get_scale()))
        b.relative_zoom.set_state(not self.t_abszoom)
        b.relative_zoom.add_callback("activated", self.set_absrel_cb)
        b.defaults.add_callback("activated", lambda w: self.set_defaults())
        b.refresh_interval.set_limits(0, 200, incr_value=1)
        b.refresh_interval.set_value(int(self.refresh_interval * 1000))
        b.refresh_interval.add_callback('value-changed', self.set_refresh_cb)

        row = Widgets.HBox()
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        vbox2.add_widget(row, stretch=0)

        # stretch
        spacer = Widgets.Label('')
        vbox2.add_widget(spacer, stretch=1)

        vbox.add_widget(vbox2, stretch=0)
        vbox.add_widget(Widgets.Label(''), stretch=1)

        container.add_widget(sw, stretch=1)

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

    def add_channel(self, viewer, chinfo):
        self.prepare(chinfo.fitsimage)

    def start(self):
        names = self.fv.get_channelNames()
        for name in names:
            chinfo = self.fv.get_channelInfo(name)
            self.add_channel(self.fv, chinfo)

    # CALLBACKS

    def new_image_cb(self, fitsimage, image):
        if fitsimage != self.fv.getfocus_fitsimage():
            return True

        self.fitsimage_focus = fitsimage
        # Reflect transforms, colormap, etc.
        fitsimage.copy_attributes(self.zoomimage,
                                  ['transforms', 'cutlevels',
                                   'rgbmap'])

        ## data = image.get_data()
        ## self.set_data(data)

    def focus_cb(self, viewer, fitsimage):
        self.fitsimage_focus = fitsimage
        # Reflect transforms, colormap, etc.
        fitsimage.copy_attributes(self.zoomimage,
                                  ['transforms', 'cutlevels',
                                   'rgbmap', 'rotation'])

        # TODO: redo cutout?

    # Match cut-levels to the ones in the "main" image
    def cutset_cb(self, setting, value, fitsimage):
        if fitsimage != self.fitsimage_focus:
            return True

        loval, hival = value
        self.zoomimage.cut_levels(loval, hival)
        return True

    def transform_cb(self, fitsimage):
        if fitsimage != self.fitsimage_focus:
            return True
        flip_x, flip_y, swap_xy = fitsimage.get_transforms()
        self.zoomimage.transform(flip_x, flip_y, swap_xy)
        return True

    def rotate_cb(self, setting, deg, fitsimage):
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
        self.zoomimage.zoom_to(myzoomlevel)
        text = self.fv.scale2text(self.zoomimage.get_scale())
        return True

    def zoomset_cb(self, setting, zoomlevel, fitsimage):
        """This method is called when a main FITS widget changes zoom level.
        """
        fac_x, fac_y = fitsimage.get_scale_base_xy()
        fac_x_me, fac_y_me = self.zoomimage.get_scale_base_xy()
        if (fac_x != fac_x_me) or (fac_y != fac_y_me):
            alg = fitsimage.get_zoom_algorithm()
            self.zoomimage.set_zoom_algorithm(alg)
            self.zoomimage.set_scale_base_xy(fac_x, fac_y)
        return self._zoomset(self.fitsimage_focus, zoomlevel)

    # LOGIC

    def set_radius(self, val):
        self.logger.debug("Setting radius to %d" % val)
        self.zoom_radius = val
        fitsimage = self.fitsimage_focus
        if fitsimage is None:
            return True
        image = fitsimage.get_image()
        wd, ht = image.get_size()
        data_x, data_y = wd // 2, ht // 2
        self.showxy(fitsimage, data_x, data_y)

    def showxy(self, fitsimage, data_x, data_y):
        # Cut and show zoom image in zoom window
        self.zoom_x, self.zoom_y = data_x, data_y

        image = fitsimage.get_image()
        if image is None:
            # No image loaded into this channel
            return True

        # If this is a new source, then update our widget with the
        # attributes of the source
        if self.fitsimage_focus != fitsimage:
            self.focus_cb(self.fv, fitsimage)

        # If the refresh interval has expired then update the zoom image;
        # otherwise (re)set the timer until the end of the interval.
        cur_time = time.time()
        elapsed = cur_time - self.update_time
        if elapsed > self.refresh_interval:
            # cancel timer
            self.zoomtask.clear()
            self.showzoom(image, data_x, data_y)
        else:
            # store needed data into the timer
            self.zoomtask.data.setvals(image=image,
                                       data_x=data_x, data_y=data_y)
            # calculate delta until end of refresh interval
            period = self.refresh_interval - elapsed
            # set timer
            self.zoomtask.set(period)
        return True

    def motion_cb(self, fitsimage, button, data_x, data_y):
        # TODO: pass _canvas_ and cut from that
        self.showxy(fitsimage, data_x, data_y)
        return False

    def showzoom_timer_cb(self, timer):
        data = timer.data
        self.showzoom(data.image, data.data_x, data.data_y)

    def showzoom(self, image, data_x, data_y):
        # cut out detail area and set the zoom image
        data, x1, y1, x2, y2 = image.cutout_radius(int(data_x), int(data_y),
                                                   self.zoom_radius)
        self.update_time = time.time()
        self.fv.gui_do(self.zoomimage.set_data, data)

    def set_amount_cb(self, widget, val):
        """This method is called when 'Zoom Amount' control is adjusted.
        """
        self.zoom_amount = val
        zoomlevel = self.fitsimage_focus.get_zoom()
        self._zoomset(self.fitsimage_focus, zoomlevel)

    def set_absrel_cb(self, w, val):
        self.t_abszoom = not val
        zoomlevel = self.fitsimage_focus.get_zoom()
        return self._zoomset(self.fitsimage_focus, zoomlevel)

    def set_defaults(self):
        self.t_abszoom = True
        self.w.relative_zoom.set_state(not self.t_abszoom)
        self.w.zoom_radius.set_value(self.default_radius)
        self.w.zoom_amount.set_value(self.default_zoom)
        self.zoomimage.zoom_to(self.default_zoom)

    def zoomset(self, setting, zoomlevel, fitsimage):
        text = self.fv.scale2text(self.zoomimage.get_scale())
        self.w.zoom.set_text(text)

    def set_radius_cb(self, w, val):
        self.set_radius(val)

    def set_refresh_cb(self, w, val):
        self.refresh_interval = val / 1000.0
        self.logger.debug("Setting refresh time to %.4f sec" % (
            self.refresh_interval))

    def __str__(self):
        return 'zoom'

#END
