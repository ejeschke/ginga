#
# Pan.py -- Pan plugin for fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Mon Jan 14 00:37:34 HST 2013
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
from PyQt4 import QtGui, QtCore

import Bunch

import FitsImageCanvasQt
import FitsImageCanvasTypesQt as CanvasTypes
import GingaPlugin


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

    def initialize(self, container):
        nb = QtGui.QStackedWidget()
        self.nb = nb
        container.addWidget(self.nb, stretch=1)

    def _create_pan_image(self):
        width, height = 300, 300

        sfi = FitsImageCanvasQt.FitsImageCanvas(logger=self.logger)
        sfi.enable_autoscale('on')
        sfi.set_autoscale_limits(-200, 100)
        sfi.set_zoom_limits(-200, 100)
        sfi.enable_pan(False)
        sfi.enable_zoom(False)
        sfi.enable_autolevels('off')
        sfi.enable_draw(True)
        sfi.set_drawtype('rectangle', linestyle='dash')
        sfi.set_drawcolor('green')
        sfi.set_callback('draw-event', self.draw_cb)
        sfi.define_cursor('pick', QtGui.QCursor(QtCore.Qt.OpenHandCursor))
        ## sfi.enable_cuts(False)
        sfi.set_bg(0.4, 0.4, 0.4)
        sfi.set_callback('button-press', self.btndown)
        sfi.set_callback('motion', self.panxy)
        sfi.set_callback('scroll', self.zoom)
        sfi.set_callback('configure', self.reconfigure)

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
        
        fitsimage.copy_attributes(panimage, ['transforms', 'cutlevels',
                                             'rotation'])
        fitsimage.add_callback('image-set', self.new_image_cb, chinfo, paninfo)
        fitsimage.add_callback('pan-set', self.panset, chinfo, paninfo)
        fitsimage.add_callback('cut-set', self.cutset_cb, chinfo, paninfo)
        fitsimage.add_callback('transform', self.transform_cb, chinfo, paninfo)
        fitsimage.add_callback('rotate', self.rotate_cb, chinfo, paninfo)
        self.logger.debug("channel %s added." % (chinfo.name))

    def delete_channel(self, viewer, chinfo):
        self.logger.debug("TODO: delete channel %s" % (chinfo.name))
        #del self.channel[chinfo.name]

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
        print "pan focus cb: chname=%s" % (chname)

        if self.active != chname:
            print "Channel is %s" % chname
            print "Current channels are %s" % self.channel.keys()
            index = self.channel[chname].nbindex
            self.nb.setCurrentIndex(index)
            self.active = chname
            self.info = self.channel[self.active]
            print "Switched page to %d" % (index)
       
        
    def reconfigure(self, fitsimage, width, height):
        self.logger.debug("new pan image dimensions are %dx%d" % (
            width, height))
        fitsimage.zoom_fit()
        
    # Match cut-levels to the ones in the "main" image
    def cutset_cb(self, fitsimage, loval, hival, chinfo, paninfo):
        paninfo.panimage.cut_levels(loval, hival)
        return True

    def transform_cb(self, fitsimage, chinfo, paninfo):
        flipx, flipy, swapxy = chinfo.fitsimage.get_transforms()
        paninfo.panimage.transform(flipx, flipy, swapxy)
        return True
        
    def rotate_cb(self, fitsimage, deg, chinfo, paninfo):
        paninfo.panimage.rotate(deg, redraw=True)
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
        #x1, y1, x2, y2 = fitsimage.get_pan_rect()
        points = fitsimage.get_pan_rect()
        try:
            obj = paninfo.panimage.getObjectByTag(paninfo.panrect)
            # if obj.kind != 'rectangle':
            #     return True
            if obj.kind != 'polygon':
                return True
            # Update current rectangle with new coords
            # if (obj.x1, obj.y1, obj.x2, obj.y2) != (x1, y1, x2, y2):
            #     self.logger.debug("starting panset")
            #     obj.x1, obj.y1, obj.x2, obj.y2 = x1, y1, x2, y2
            #     paninfo.panimage.redraw(whence=3)
            self.logger.debug("starting panset")
            obj.points = points
            paninfo.panimage.redraw(whence=3)

        except KeyError:
            # paninfo.panrect = paninfo.panimage.add(CanvasTypes.Rectangle(x1, y1, x2, y2))
            paninfo.panrect = paninfo.panimage.add(CanvasTypes.Polygon(points))

    def btndown(self, fitsimage, button, data_x, data_y):
        if button == 0x21:
            fitsimage = self.fv.getfocus_fitsimage()
            fitsimage.panset_xy(data_x, data_y, redraw=False)

    def panxy(self, fitsimage, button, data_x, data_y):
        """Motion event in the small fits window.  This is usually a panning
        control for the big window, but if the button is not held down then
        we just show the pointing information as usual.
        """
        if button == 0:
            bigimage = self.fv.getfocus_fitsimage()
            return self.fv.showxy(bigimage, data_x, data_y)

        elif button & 0x1:
            # If button1 is held down this is a panning move in the small
            # window for the big window
            # data_wd, data_ht = self.info.panimage.get_data_size()
            # panx = float(data_x) / float(data_wd)
            # pany = float(data_y) / float(data_ht)

            bigimage = self.fv.getfocus_fitsimage()
            return bigimage.set_pan(data_x, data_y)

        return False

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
        
        
    def __str__(self):
        return 'pan'
    
#END
