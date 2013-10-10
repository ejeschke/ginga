#
# ZoomBase.py -- Zoom plugin base class for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time

from ginga.misc import Bunch
from ginga import GingaPlugin


class ZoomBase(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(ZoomBase, self).__init__(fv)

        self.zoomimage = None
        self.default_radius = 30
        self.default_zoom = 3
        self.zoom_radius = self.default_radius
        self.zoom_amount = self.default_zoom
        self.zoom_x = 0
        self.zoom_y = 0
        self.t_abszoom = True
        self.zoomtask = fv.get_timer()
        self.zoomtask.set_callback('expired', self.showzoom_timer)
        self.fitsimage_focus = None
        self.refresh_interval = 0.02
        self.update_time = time.time()

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('active-image', self.focus_cb)

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
        self.zoomimage.zoom_to(myzoomlevel, redraw=True)
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

    def showzoom_timer(self, timer):
        data = timer.data
        self.showzoom(data.image, data.data_x, data.data_y)
        
    def showzoom(self, image, data_x, data_y):
        # cut out detail area and set the zoom image
        data, x1, y1, x2, y2 = image.cutout_radius(int(data_x), int(data_y),
                                                   self.zoom_radius)
        self.update_time = time.time()
        self.fv.gui_do(self.zoomimage.set_data, data)

    def __str__(self):
        return 'zoom'
    
#END
