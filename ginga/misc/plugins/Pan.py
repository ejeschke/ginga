#
# Pan.py -- Pan plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import traceback
import math
from ginga.gw import Widgets, Viewers
from ginga.misc import Bunch
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

        self.dc = fv.getDrawClasses()

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Pan')
        self.settings.addDefaults(use_shared_canvas=False,
                                  pan_position_color='yellow',
                                  pan_rectangle_color='red',
                                  compass_color='skyblue')
        self.settings.load(onError='silent')
        # share canvas with channel viewer?
        self.use_shared_canvas = self.settings.get('use_shared_canvas', False)

    def build_gui(self, container):
        nb = Widgets.StackWidget()
        self.nb = nb
        container.add_widget(self.nb, stretch=1)

    def _create_pan_image(self, fitsimage):
        width, height = 300, 300

        #pi = Viewers.ImageViewCanvas(logger=self.logger)
        pi = Viewers.CanvasView(logger=self.logger)
        pi.enable_autozoom('on')
        pi.enable_autocuts('off')
        hand = pi.get_cursor('pan')
        pi.define_cursor('pick', hand)
        pi.set_bg(0.4, 0.4, 0.4)
        pi.set_desired_size(width, height)
        pi.set_callback('cursor-down', self.btndown)
        pi.set_callback('cursor-move', self.drag_cb)
        pi.set_callback('none-move', self.motion_cb)
        pi.set_callback('zoom-scroll', self.zoom_cb)
        pi.set_callback('configure', self.reconfigure)
        # for debugging
        pi.set_name('panimage')
        #pi.ui_setActive(True)

        my_canvas = pi.get_canvas()
        my_canvas.enable_draw(True)
        my_canvas.set_drawtype('rectangle', linestyle='dash', color='green')
        my_canvas.set_callback('draw-event', self.draw_cb)
        my_canvas.ui_setActive(True)

        if self.use_shared_canvas:
            canvas = fitsimage.get_canvas()
            pi.set_canvas(canvas)

        bd = pi.get_bindings()
        bd.enable_pan(False)
        bd.enable_zoom(False)

        pi.set_desired_size(width, height)
        return pi

    def add_channel(self, viewer, chinfo):
        fitsimage = chinfo.fitsimage
        panimage = self._create_pan_image(fitsimage)
        chname = chinfo.name

        # ?? Can't we use panimage directly as a wrapped widget ??
        iw = panimage.get_widget()
        # wrap widget
        iw = Widgets.wrap(iw)
        self.nb.add_widget(iw)
        index = self.nb.index_of(iw)
        paninfo = Bunch.Bunch(panimage=panimage, widget=iw,
                              pancompass=None, panrect=None)
        self.channel[chname] = paninfo

        # Extract RGBMap object from main image and attach it to this
        # pan image
        rgbmap = fitsimage.get_rgbmap()
        panimage.set_rgbmap(rgbmap)
        rgbmap.add_callback('changed', self.rgbmap_cb, panimage)

        fitsimage.copy_attributes(panimage, ['cutlevels'])
        fitsimage.add_callback('image-set', self.new_image_cb, chinfo, paninfo)

        fitssettings = fitsimage.get_settings()
        pansettings = panimage.get_settings()

        xfrmsettings = ['flip_x', 'flip_y', 'swap_xy', 'rot_deg']
        fitssettings.shareSettings(pansettings, xfrmsettings)
        for key in xfrmsettings:
            pansettings.getSetting(key).add_callback('set', self.settings_cb,
                                                     fitsimage, chinfo, paninfo, 0)


        fitssettings.shareSettings(pansettings, ['cuts'])
        pansettings.getSetting('cuts').add_callback('set', self.settings_cb,
                                                    fitsimage, chinfo, paninfo, 1)

        zoomsettings = ['zoom_algorithm', 'zoom_rate',
                        'scale_x_base', 'scale_y_base']
        fitssettings.shareSettings(pansettings, zoomsettings)
        for key in zoomsettings:
            pansettings.getSetting(key).add_callback('set', self.zoom_ext_cb,
                                                     fitsimage, chinfo, paninfo)

        fitsimage.add_callback('redraw', self.redraw_cb, chinfo, paninfo)

        self.logger.debug("channel '%s' added." % (chinfo.name))

    def delete_channel(self, viewer, chinfo):
        chname = chinfo.name
        self.logger.debug("deleting channel %s" % (chname))
        widget = self.channel[chname].widget
        self.nb.remove(widget, delete=True)
        self.active = None
        self.info = None
        del self.channel[chname]

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

        # HACK: when is the non-shared _imgobj being created?
        # we have to null it here so that it get's recreated correctly--fix!
        #print(('new_image_cb', paninfo.panimage._imgobj))
        paninfo.panimage._imgobj = None

        loval, hival = fitsimage.get_cut_levels()
        paninfo.panimage.cut_levels(loval, hival)

        # add cb to image so that if it is modified we can update info
        ## image.add_callback('modified', self.image_update_cb, fitsimage,
        ##                    chinfo, paninfo)

        # This seems to trigger a crash with mosaic images if we call
        # set_image() immediately, so just queue up on the GUI thread
        #self.set_image(chinfo, paninfo, image)
        self.fv.gui_do(self.set_image, chinfo, paninfo, image)
        return False

    def image_update_cb(self, image, fitsimage, chinfo, paninfo):
        # image has changed (e.g. size, value range, etc)
        cur_img = fitsimage.get_image()
        if cur_img == image:
            self.fv.gui_do(self.set_image, chinfo, paninfo, image)
        return False

    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name

        # If the active widget has changed, then raise our Info widget
        # that corresponds to it
        if self.active != chname:
            iw = self.channel[chname].widget
            index = self.nb.index_of(iw)
            self.nb.set_index(index)
            self.active = chname
            self.info = self.channel[self.active]


    def reconfigure(self, panimage, width, height):
        self.logger.debug("new pan image dimensions are %dx%d" % (
            width, height))
        panimage.zoom_fit()
        panimage.redraw(whence=0)
        return True

    def redraw_cb(self, fitsimage, chinfo, paninfo):
        #paninfo.panimage.redraw(whence=whence)
        self.panset(chinfo.fitsimage, chinfo, paninfo)
        return True

    def settings_cb(self, setting, value, fitsimage, chinfo, paninfo, whence):
        #paninfo.panimage.redraw(whence=whence)
        self.panset(chinfo.fitsimage, chinfo, paninfo)
        return True

    def zoom_ext_cb(self, setting, value, fitsimage, chinfo, paninfo):
        # refit the pan image, because scale factors may have changed
        paninfo.panimage.zoom_fit()
        # redraw pan info
        self.panset(fitsimage, chinfo, paninfo)
        return False

    # LOGIC

    def clear(self):
        self.info.panimage.clear()

    def set_image(self, chinfo, paninfo, image):
        if image is None:
            return

        if not self.use_shared_canvas:
            paninfo.panimage.set_image(image)
        else:
            paninfo.panimage.zoom_fit()

        p_canvas = paninfo.panimage.private_canvas
        # remove old compass
        try:
            p_canvas.deleteObjectByTag(paninfo.pancompass)
        except Exception:
            pass

        # create compass
        if image.has_valid_wcs():
            try:
                width, height = image.get_size()
                x, y = width / 2.0, height / 2.0
                # radius we want the arms to be (approx 1/4 the largest dimension)
                radius = float(max(width, height)) / 4.0

                # HACK: force a wcs error here if one is going to happen
                image.add_offset_xy(x, y, 1.0, 1.0)

                paninfo.pancompass = p_canvas.add(self.dc.Compass(
                    x, y, radius, color=self.settings.get('compass_color', 'skyblue'),
                    fontsize=14))
            except Exception as e:
                self.logger.warn("Can't calculate compass: %s" % (
                    str(e)))
                try:
                    # log traceback, if possible
                    (type_, value_, tb) = sys.exc_info()
                    tb_str = "".join(traceback.format_tb(tb))
                    self.logger.error("Traceback:\n%s" % (tb_str))
                except Exception:
                    tb_str = "Traceback information unavailable."
                    self.logger.error(tb_str)

        self.panset(chinfo.fitsimage, chinfo, paninfo)

    def panset(self, fitsimage, chinfo, paninfo):
        image = fitsimage.get_image()
        if image is None:
            return

        x, y = fitsimage.get_pan()
        points = fitsimage.get_pan_rect()

        # calculate pan position point radius
        p_image = paninfo.panimage.get_image()
        try:
            obj = paninfo.panimage.canvas.getObjectByTag('__image')
        except KeyError:
            obj = None
        #print(('panset', image, p_image, obj, obj.image, paninfo.panimage._imgobj))

        width, height = image.get_size()
        edgew = math.sqrt(width**2 + height**2)
        radius = int(0.015 * edgew)

        # Mark pan rectangle and pan position
        #p_canvas = paninfo.panimage.get_canvas()
        p_canvas = paninfo.panimage.private_canvas
        try:
            obj = p_canvas.getObjectByTag(paninfo.panrect)
            if obj.kind != 'compound':
                return False
            point, bbox = obj.objects
            self.logger.debug("starting panset")
            point.x, point.y = x, y
            point.radius = radius
            bbox.points = points
            p_canvas.update_canvas(whence=0)

        except KeyError:
            paninfo.panrect = p_canvas.add(self.dc.CompoundObject(
                self.dc.Point(x, y, radius=radius, style='plus',
                              color=self.settings.get('pan_position_color', 'yellow')),
                self.dc.Polygon(points,
                                color=self.settings.get('pan_rectangle_color', 'red'))))

        p_canvas.update_canvas(whence=0)
        return True

    def motion_cb(self, fitsimage, event, data_x, data_y):
        bigimage = self.fv.getfocus_fitsimage()
        self.fv.showxy(bigimage, data_x, data_y)
        return True

    def drag_cb(self, fitsimage, event, data_x, data_y):
        # this is a panning move in the small
        # window for the big window
        bigimage = self.fv.getfocus_fitsimage()
        bigimage.panset_xy(data_x, data_y)
        return True

    def btndown(self, fitsimage, event, data_x, data_y):
        bigimage = self.fv.getfocus_fitsimage()
        bigimage.panset_xy(data_x, data_y)
        return True

    def zoom_cb(self, fitsimage, event):
        """Zoom event in the small fits window.  Just zoom the large fits
        window.
        """
        fitsimage = self.fv.getfocus_fitsimage()
        bd = fitsimage.get_bindings()

        if hasattr(bd, 'sc_zoom'):
            return bd.sc_zoom(fitsimage, event)

        return False

    def draw_cb(self, canvas, tag):
        # Get and delete the drawn object
        obj = canvas.getObjectByTag(tag)
        canvas.deleteObjectByTag(tag)

        # determine center of drawn rectangle and set pan position
        if obj.kind != 'rectangle':
            return False
        xc = (obj.x1 + obj.x2) / 2.0
        yc = (obj.y1 + obj.y2) / 2.0
        fitsimage = self.fv.getfocus_fitsimage()
        # note: fitsimage <-- referring to large non-pan image
        fitsimage.panset_xy(xc, yc)

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

        fitsimage.zoom_to(zoomlevel)
        return True


    def __str__(self):
        return 'pan'

#END
