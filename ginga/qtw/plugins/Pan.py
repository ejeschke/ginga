#
# Pan.py -- Pan plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
from ginga.qtw.QtHelp import QtGui, QtCore

from ginga.misc import Bunch

from ginga.qtw import ImageViewCanvasQt
from ginga.qtw import ImageViewCanvasTypesQt as CanvasTypes
from ginga import GingaPlugin


class Pan(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Pan, self).__init__(fv)

        self.channel = {}
        self.active = None
        self.info = None

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.set_callback('active-image', self.focus_cb)

    def build_gui(self, container):
        nb = QtGui.QStackedWidget()
        self.nb = nb
        container.addWidget(self.nb, stretch=1)

    def _create_pan_image(self):
        width, height = 300, 300

        sfi = ImageViewCanvasQt.ImageViewCanvas(logger=self.logger)
        sfi.enable_autozoom('on')
        sfi.enable_autocuts('off')
        sfi.enable_draw(True)
        sfi.set_drawtype('rectangle', linestyle='dash')
        sfi.set_drawcolor('green')
        sfi.set_callback('draw-event', self.draw_cb)
        hand = sfi.get_cursor('pan')
        sfi.define_cursor('pick', hand)
        ## sfi.enable_cuts(False)
        sfi.set_bg(0.4, 0.4, 0.4)
        sfi.set_desired_size(width, height)
        sfi.set_callback('cursor-down', self.btndown)
        sfi.set_callback('cursor-move', self.drag_cb)
        sfi.set_callback('none-move', self.motion_cb)
        sfi.set_callback('scroll', self.zoom)
        sfi.set_callback('configure', self.reconfigure)

        bd = sfi.get_bindings()
        bd.enable_pan(False)
        bd.enable_zoom(False)

        iw = sfi.get_widget()
        iw.resize(width, height)
        iw.show()
        return sfi

    def add_channel(self, viewer, chinfo):
        panimage = self._create_pan_image()
        chname = chinfo.name
        
        iw = panimage.get_widget()
        self.nb.addWidget(iw)
        index = self.nb.indexOf(iw)
        paninfo = Bunch.Bunch(panimage=panimage, widget=iw,
                              pancompass=None, panrect=None,
                              nbindex=index)
        self.channel[chname] = paninfo

        # Extract RGBMap object from main image and attach it to this
        # pan image
        fitsimage = chinfo.fitsimage
        rgbmap = fitsimage.get_rgbmap()
        panimage.set_rgbmap(rgbmap, redraw=False)
        rgbmap.add_callback('changed', self.rgbmap_cb, panimage)
        
        fitsimage.copy_attributes(panimage, ['cutlevels'])
        fitsimage.add_callback('image-set', self.new_image_cb, chinfo, paninfo)
        fitsimage.add_callback('redraw', self.panset, chinfo, paninfo)

        fitssettings = fitsimage.get_settings()
        pansettings = panimage.get_settings()
        
        zoomsettings = ['zoom_algorithm', 'zoom_rate',
                        'scale_x_base', 'scale_y_base']
        fitssettings.shareSettings(pansettings, zoomsettings)
        for key in zoomsettings:
            pansettings.getSetting(key).add_callback('set', self.zoom_cb,
                                                     fitsimage, chinfo, paninfo)

        xfrmsettings = ['flip_x', 'flip_y', 'swap_xy', 'cuts']
        fitssettings.shareSettings(pansettings, xfrmsettings)
        for key in xfrmsettings:
            pansettings.getSetting(key).add_callback('set', self.redraw_cb,
                                                     fitsimage, chinfo, paninfo, 0.5)
            
        fitssettings.shareSettings(pansettings, ['rot_deg'])
        pansettings.getSetting('rot_deg').add_callback('set', self.redraw_cb,
                                                       fitsimage, chinfo, paninfo, 0)
        self.logger.debug("channel %s added." % (chinfo.name))

    def delete_channel(self, viewer, chinfo):
        self.logger.debug("TODO: delete channel %s" % (chinfo.name))
        #del self.channel[chinfo.name]

    def start(self):
        names = self.fv.get_channelNames()
        for name in names:
            chinfo = self.fv.get_channelInfo(name)
            self.add_channel(self.fv, chinfo)
        
    # CALLBACKS

    def rgbmap_cb(self, rgbmap, panimage):
        # color mapping has changed in some way
        panimage.redraw(whence=1)
    
    def new_image_cb(self, fitsimage, image, chinfo, paninfo):
        loval, hival = fitsimage.get_cut_levels()
        paninfo.panimage.cut_levels(loval, hival, redraw=False)
        
        self.set_image(chinfo, paninfo, image)

    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name

        if self.active != chname:
            index = self.channel[chname].nbindex
            self.nb.setCurrentIndex(index)
            self.active = chname
            self.info = self.channel[self.active]
       
        
    def reconfigure(self, fitsimage, width, height):
        self.logger.debug("new pan image dimensions are %dx%d" % (
            width, height))
        fitsimage.zoom_fit()
        
    def redraw_cb(self, setting, value, deg, chinfo, paninfo, whence):
        paninfo.panimage.redraw(whence=whence)
        self.panset(chinfo.fitsimage, chinfo, paninfo)
        return True
        
    def zoom_cb(self, setting, value, fitsimage, chinfo, paninfo):
        # refit the pan image, because scale factors may have changed
        paninfo.panimage.zoom_fit(redraw=True)
        # redraw pan info
        self.panset(fitsimage, chinfo, paninfo)
        return True
        
    # LOGIC
    
    def clear(self):
        self.info.panimage.clear()

    def set_image(self, chinfo, paninfo, image):
        paninfo.panimage.set_image(image)

        # remove old compass
        try:
            paninfo.panimage.deleteObjectByTag(paninfo.pancompass,
                                               redraw=False)
        except Exception:
            pass

        # create compass
        try:
            (x, y, xn, yn, xe, ye) = image.calc_compass_center()
            self.logger.debug("x=%d y=%d xn=%d yn=%d xe=%d ye=%d" % (
                x, y, xn, yn, xe, ye))
            paninfo.pancompass = paninfo.panimage.add(CanvasTypes.Compass(
                x, y, xn, yn, xe, ye, color='skyblue',
                fontsize=14), redraw=True)
        except Exception, e:
            self.logger.warn("Can't calculate compass: %s" % (
                str(e)))

        self.panset(chinfo.fitsimage, chinfo, paninfo)

    def panset(self, fitsimage, chinfo, paninfo):
        x, y = fitsimage.get_pan()
        points = fitsimage.get_pan_rect()

        # calculate pan position point radius
        image = paninfo.panimage.get_image()
        width, height = image.get_size()
        edgew = math.sqrt(width**2 + height**2)
        radius = int(0.015 * edgew)

        # Mark pan rectangle and pan position
        try:
            obj = paninfo.panimage.getObjectByTag(paninfo.panrect)
            if obj.kind != 'compound':
                return True
            point, bbox = obj.objects
            self.logger.debug("starting panset")
            point.x, point.y = x, y
            point.radius = radius
            bbox.points = points
            paninfo.panimage.redraw(whence=3)

        except KeyError:
            paninfo.panrect = paninfo.panimage.add(CanvasTypes.CompoundObject(
                CanvasTypes.Point(x, y, radius=radius),
                CanvasTypes.Polygon(points)))

    def motion_cb(self, fitsimage, button, data_x, data_y):
        bigimage = self.fv.getfocus_fitsimage()
        self.fv.showxy(bigimage, data_x, data_y)
        return True

    def drag_cb(self, fitsimage, action, data_x, data_y):
        # this is a panning move in the small
        # window for the big window
        bigimage = self.fv.getfocus_fitsimage()
        bigimage.panset_xy(data_x, data_y)
        return True

    def btndown(self, fitsimage, action, data_x, data_y):
        bigimage = self.fv.getfocus_fitsimage()
        bigimage.panset_xy(data_x, data_y)
        return True

    def zoom(self, fitsimage, direction):
        """Scroll event in the small fits window.  Just zoom the large fits
        window.
        """
        fitsimage = self.fv.getfocus_fitsimage()
        if direction == 'up':
            fitsimage.zoom_in()
        elif direction == 'down':
            fitsimage.zoom_out()
        fitsimage.onscreen_message(fitsimage.get_scale_text(),
                                   delay=1.0)
        
    def draw_cb(self, fitsimage, tag):
        # Get and delete the drawn object
        obj = fitsimage.getObjectByTag(tag)
        fitsimage.deleteObjectByTag(tag, redraw=True)

        # determine center of drawn rectangle and set pan position
        if obj.kind != 'rectangle':
            return True
        xc = (obj.x1 + obj.x2) / 2.0
        yc = (obj.y1 + obj.y2) / 2.0
        fitsimage = self.fv.getfocus_fitsimage()
        # note: fitsimage <-- referring to large non-pan image
        fitsimage.panset_xy(xc, yc, redraw=False)

        # Determine appropriate zoom level to fit this rect
        wd = obj.x2 - obj.x1
        ht = obj.y2 - obj.y1
        wwidth, wheight = fitsimage.get_window_size()
        wd_scale = float(wwidth) / float(wd)
        ht_scale = float(wheight) / float(ht)
        scale = min(wd_scale, ht_scale)
        self.logger.debug("wd_scale=%f ht_scale=%f scale=%f" % (
            wd_scale, ht_scale, scale))
        if scale < 1.0:
            zoomlevel = - max(2, int(math.ceil(1.0/scale)))
        else:
            zoomlevel = max(1, int(math.floor(scale)))
        self.logger.debug("zoomlevel=%d" % (zoomlevel))

        fitsimage.zoom_to(zoomlevel, redraw=True)
        return True

        
    def __str__(self):
        return 'pan'
    
#END
