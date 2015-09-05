#
# Info.py -- FITS Info plugin for the Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga import GingaPlugin


class Info(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Info, self).__init__(fv)

        self.channel = {}
        self.active = None
        self.info = None
        # truncate names after this size
        self.maxstr = 60

        #self.w = Bunch.Bunch()
        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.add_callback('field-info', self.field_info)
        fv.add_callback('active-image', self.focus_cb)

    def build_gui(self, container):
        nb = Widgets.StackWidget()
        self.nb = nb
        container.add_widget(self.nb, stretch=1)

    def _create_info_window(self):
        sw = Widgets.ScrollArea()

        vbox = Widgets.VBox()
        captions = (('Name:', 'label', 'Name', 'llabel'),
                    ('Object:', 'label', 'Object', 'llabel'),
                    ('X:', 'label', 'X', 'llabel'),
                    ('Y:', 'label', 'Y', 'llabel'),
                    ('Value:', 'label', 'Value', 'llabel'),
                    ('RA:', 'label', 'RA', 'llabel'),
                    ('DEC:', 'label', 'DEC', 'llabel'),
                    ('Equinox:', 'label', 'Equinox', 'llabel'),
                    ('Dimensions:', 'label', 'Dimensions', 'llabel'),
                    ('Min:', 'label', 'Min', 'llabel'),
                    ('Max:', 'label', 'Max', 'llabel'),
                    )
        w, b = Widgets.build_info(captions)

        col = Widgets.VBox()
        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        col.add_widget(row, stretch=1)
        col.add_widget(Widgets.Label(''), stretch=1)
        sw2 = Widgets.ScrollArea()
        sw2.set_widget(col)
        vbox.add_widget(sw2, stretch=2)

        captions = (('Zoom:', 'label', 'Zoom', 'llabel'),
                    ('Cut Low:', 'label', 'Cut Low Value', 'llabel',
                     'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High Value', 'llabel',
                     'Cut High', 'entry'),
                    ('Auto Levels', 'button', 'spacer1', 'spacer',
                     'Cut Levels', 'button'),
                    ('Cut New:', 'label', 'Cut New', 'llabel'),
                    ('Zoom New:', 'label', 'Zoom New', 'llabel'),
                    ('Center New:', 'label', 'Center New', 'llabel'),
                    )

        w, b2 = Widgets.build_info(captions)
        b.update(b2)
        # TODO: need a more general solution to gtk labels resizing their
        # parent window
        #b.object.set_length(12)
        b.cut_levels.set_tooltip("Set cut levels manually")
        b.auto_levels.set_tooltip("Set cut levels by algorithm")
        b.cut_low.set_tooltip("Set low cut level (press Enter)")
        b.cut_high.set_tooltip("Set high cut level (press Enter)")

        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(row, stretch=1)

        # stretcher
        vbox.add_widget(Widgets.Label(''), stretch=1)

        sw.set_widget(vbox)
        return sw, b

    def add_channel(self, viewer, chinfo):
        sw, winfo = self._create_info_window()
        chname = chinfo.name

        self.nb.add_widget(sw, title=chname)
        index = self.nb.index_of(sw)
        info = Bunch.Bunch(widget=sw, winfo=winfo,
                           mode_w=None,
                           chinfo=chinfo)
        self.channel[chname] = info

        winfo.cut_low.add_callback('activated', self.cut_levels,
                                   chinfo.fitsimage, info)
        winfo.cut_high.add_callback('activated', self.cut_levels,
                                    chinfo.fitsimage, info)
        winfo.cut_levels.add_callback('activated', self.cut_levels,
                                      chinfo.fitsimage, info)
        winfo.auto_levels.add_callback('activated', self.auto_levels,
                                       chinfo.fitsimage, info)

        fitsimage = chinfo.fitsimage
        fitssettings = fitsimage.get_settings()
        fitsimage.add_callback('image-set', self.new_image_cb, info)
        for name in ['cuts']:
            fitssettings.getSetting(name).add_callback('set',
                               self.cutset_cb, fitsimage, info)
        for name in ['scale']:
            fitssettings.getSetting(name).add_callback('set',
                               self.zoomset_cb, fitsimage, info)
        fitssettings.getSetting('autocuts').add_callback('set',
                               self.autocuts_cb, fitsimage, info)
        fitssettings.getSetting('autozoom').add_callback('set',
                               self.autozoom_cb, fitsimage, info)
        fitssettings.getSetting('autocenter').add_callback('set',
                               self.autocenter_cb, fitsimage, info)

    def delete_channel(self, viewer, chinfo):
        chname = chinfo.name
        self.logger.debug("deleting channel %s" % (chname))
        widget = self.channel[chname].widget
        self.nb.remove(widget, delete=True)
        self.active = None
        self.info = None
        del self.channel[chname]

    # CALLBACKS

    def new_image_cb(self, fitsimage, image, info):
        # add cb to image so that if it is modified we can update info
        image.add_callback('modified', self.image_update_cb, fitsimage, info)

        self.set_info(info, fitsimage)
        return True

    def image_update_cb(self, image, fitsimage, info):
        cur_img = fitsimage.get_image()
        if cur_img == image:
            self.fv.gui_do(self.set_info, info, fitsimage)
        return True

    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name

        if self.active != chname:
            widget = self.channel[chname].widget
            index = self.nb.index_of(widget)
            self.nb.set_index(index)
            self.active = chname
            self.info = self.channel[self.active]

        self.set_info(self.info, fitsimage)

    def zoomset_cb(self, setting, value, fitsimage, info):
        """This callback is called when the main window is zoomed.
        """
        #scale_x, scale_y = fitsimage.get_scale_xy()
        scale_x, scale_y = value

        # Set text showing zoom factor (1X, 2X, etc.)
        if scale_x == scale_y:
            text = self.fv.scale2text(scale_x)
        else:
            textx = self.fv.scale2text(scale_x)
            texty = self.fv.scale2text(scale_y)
            text = "X: %s  Y: %s" % (textx, texty)
        info.winfo.zoom.set_text(text)

    def cutset_cb(self, setting, value, fitsimage, info):
        loval, hival = value
        #info.winfo.cut_low.set_text('%.4g' % (loval))
        info.winfo.cut_low_value.set_text('%.4g' % (loval))
        #info.winfo.cut_high.set_text('%.4g' % (hival))
        info.winfo.cut_high_value.set_text('%.4g' % (hival))

    def autocuts_cb(self, setting, option, fitsimage, info):
        info.winfo.cut_new.set_text(option)

    def autozoom_cb(self, setting, option, fitsimage, info):
        info.winfo.zoom_new.set_text(option)

    def autocenter_cb(self, setting, option, fitsimage, info):
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = { True: 'on', False: 'off' }
            option = choice[option]
        info.winfo.center_new.set_text(option)

    # LOGIC

    def trunc(self, s):
        if len(s) > self.maxstr:
            return s[:self.maxstr-3] + '...'
        else:
            return s

    def set_info(self, info, fitsimage):
        image = fitsimage.get_image()
        if image is None:
            return
        header = image.get_header()

        # Update info panel
        name = self.trunc(image.get('name', 'Noname'))
        info.winfo.name.set_text(name)
        objtext = self.trunc(header.get('OBJECT', 'UNKNOWN'))
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
        #info.winfo.cut_low.set_text('%.4g' % (loval))
        info.winfo.cut_low_value.set_text('%.4g' % (loval))
        #info.winfo.cut_high.set_text('%.4g' % (hival))
        info.winfo.cut_high_value.set_text('%.4g' % (hival))

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
        option = t_['autocenter']
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = { True: 'on', False: 'off' }
            option = choice[option]
        info.winfo.center_new.set_text(option)


    def field_info(self, viewer, fitsimage, info):
        # TODO: can this be made more efficient?
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name
        if not chname in self.channel:
            return
        obj = self.channel[chname]

        obj.winfo.x.set_text("%.3f" % info.x)
        obj.winfo.y.set_text("%.3f" % info.y)
        obj.winfo.value.set_text(str(info.value))
        if 'ra_txt' in info:
            obj.winfo.ra.set_text(info.ra_txt)
            obj.winfo.dec.set_text(info.dec_txt)
        if 'ra_lbl' in info:
            obj.winfo.lbl_ra.set_text(info.ra_lbl+':')
            obj.winfo.lbl_dec.set_text(info.dec_lbl+':')

    def cut_levels(self, w, fitsimage, info):
        loval, hival = fitsimage.get_cut_levels()
        try:
            lostr = info.winfo.cut_low.get_text().strip()
            if lostr != '':
                loval = float(lostr)

            histr = info.winfo.cut_high.get_text().strip()
            if histr != '':
                hival = float(histr)
            self.logger.debug("locut=%f hicut=%f" % (loval, hival))

            return fitsimage.cut_levels(loval, hival)
        except Exception as e:
            self.fv.show_error("Error cutting levels: %s" % (str(e)))

        return True

    def auto_levels(self, w, fitsimage, info):
        fitsimage.auto_levels()

    def __str__(self):
        return 'info'

#END
