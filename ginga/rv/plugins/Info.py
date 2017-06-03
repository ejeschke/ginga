#
# Info.py -- FITS Info plugin for the Ginga fits viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga import GingaPlugin


class Info(GingaPlugin.GlobalPlugin):
    """
    Info
    ====
    The Info plugin provides a pane of commonly useful metadata about the
    associated channel image.  Common information includes some
    FITS header values, the equinox, dimensions of the image, minimum and
    maximum values and the zoom level.  As the cursor is moved around the
    image, the X, Y, Value, RA and DEC values are updated to reflect the
    value under the cursor.

    Plugin Type: Global
    -------------------
    Info is a global plugin.  Only one instance can be opened.

    Usage
    -----
    At the bottom of the Info interface are the cut levels controls. Here
    the low and high cut levels are shown and can be adjusted.  Pressing the
    "Auto Levels" button will recalculate cut levels based on the current
    auto cut levels algorithm and parameters defined in the channel
    preferences.

    Below the "Auto Levels" button, the status of the settings for
    "Cut New", "Zoom New" and "Center New" are shown for the currently active
    channel.  These indicate how new images that are added to the channel
    will be affected by auto cut levels, fitting to the window and panning
    to the center of the image.

    The Info plugin typically appears under the "Synopsis" tab in the user
    interface.
    """
    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Info, self).__init__(fv)

        self.active = None
        self.info = None
        # truncate names after this size
        self.maxstr = 60

        self.autozoom_options = ['on', 'override', 'once', 'off']
        self.autocut_options = self.autozoom_options
        self.autocenter_options = self.autozoom_options

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.add_callback('field-info', self.field_info)
        fv.add_callback('channel-change', self.focus_cb)

    def build_gui(self, container):
        nb = Widgets.StackWidget()
        self.nb = nb
        container.add_widget(self.nb, stretch=1)

    def _create_info_window(self):
        sw = Widgets.ScrollArea()

        vbox = Widgets.VBox()
        sw.set_widget(vbox)

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
        col.add_widget(row, stretch=0)
        col.add_widget(Widgets.Label(''), stretch=1)
        sw2 = Widgets.ScrollArea()
        sw2.set_widget(col)
        vbox.add_widget(sw2, stretch=1)

        captions = (('Zoom:', 'label', 'Zoom', 'llabel'),
                    ('Cut Low:', 'label', 'Cut Low Value', 'llabel',
                     'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High Value', 'llabel',
                     'Cut High', 'entry'),
                    ('Auto Levels', 'button', 'spacer1', 'spacer',
                     'Cut Levels', 'button'),
                    ('Cut New:', 'label', 'Cut New', 'combobox'),
                    ('Zoom New:', 'label', 'Zoom New', 'combobox'),
                    ('Center New:', 'label', 'Center New', 'combobox'),
                    )

        w, b2 = Widgets.build_info(captions)
        b.update(b2)
        b.cut_levels.set_tooltip("Set cut levels manually")
        b.auto_levels.set_tooltip("Set cut levels by algorithm")
        b.cut_low.set_tooltip("Set low cut level (press Enter)")
        b.cut_low_value.set_text('')
        b.cut_high.set_tooltip("Set high cut level (press Enter)")
        b.cut_high_value.set_text('')

        combobox = b.cut_new
        index = 0
        for name in self.autocut_options:
            combobox.append_text(name)
            index += 1
        b.cut_new.set_tooltip("Automatically set cut levels for new images")

        combobox = b.zoom_new
        index = 0
        for name in self.autozoom_options:
            combobox.append_text(name)
            index += 1
        b.zoom_new.set_tooltip("Automatically fit new images to window")

        combobox = b.center_new
        index = 0
        for name in self.autocenter_options:
            combobox.append_text(name)
            index += 1
        b.center_new.set_tooltip("Automatically center new images in window")

        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(row, stretch=0)

        return sw, b

    def add_channel(self, viewer, channel):
        sw, winfo = self._create_info_window()
        chname = channel.name

        self.nb.add_widget(sw, title=chname)
        index = self.nb.index_of(sw)
        info = Bunch.Bunch(widget=sw, winfo=winfo,
                           mode_w=None,
                           chinfo=channel)
        channel.extdata._info_info = info

        winfo.cut_low.add_callback('activated', self.cut_levels,
                                   channel.fitsimage, info)
        winfo.cut_high.add_callback('activated', self.cut_levels,
                                    channel.fitsimage, info)
        winfo.cut_levels.add_callback('activated', self.cut_levels,
                                      channel.fitsimage, info)
        winfo.auto_levels.add_callback('activated', self.auto_levels,
                                       channel.fitsimage, info)
        winfo.cut_new.add_callback('activated', self.set_autocuts_cb,
                                   channel.fitsimage, info)
        winfo.zoom_new.add_callback('activated', self.set_autozoom_cb,
                                    channel.fitsimage, info)
        winfo.center_new.add_callback('activated', self.set_autocenter_cb,
                                      channel.fitsimage, info)

        fitsimage = channel.fitsimage
        fitssettings = fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.get_setting(name).add_callback('set',
                               self.cutset_cb, fitsimage, info)
        for name in ['scale']:
            fitssettings.get_setting(name).add_callback('set',
                               self.zoomset_cb, fitsimage, info)
        fitssettings.get_setting('autocuts').add_callback('set',
                               self.autocuts_cb, fitsimage, info)
        fitssettings.get_setting('autozoom').add_callback('set',
                               self.autozoom_cb, fitsimage, info)
        fitssettings.get_setting('autocenter').add_callback('set',
                               self.autocenter_cb, fitsimage, info)

    def delete_channel(self, viewer, channel):
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        info = channel.extdata._info_info
        widget = info.widget
        self.nb.remove(widget, delete=True)
        self.active = None
        self.info = None

    # CALLBACKS

    def redo(self, channel, image):
        fitsimage = channel.fitsimage
        info = channel.extdata._info_info

        self.set_info(info, fitsimage)
        return True

    def focus_cb(self, viewer, channel):
        chname = channel.name

        if self.active != chname:
            if not channel.extdata.has_key('_info_info'):
                self.add_channel(viewer, channel)
            info = channel.extdata._info_info
            widget = info.widget
            index = self.nb.index_of(widget)
            self.nb.set_index(index)
            self.active = chname
            self.info = info

        self.set_info(self.info, channel.fitsimage)

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
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        info.winfo.cut_new.set_index(index)

    def autozoom_cb(self, setting, option, fitsimage, info):
        index = self.autozoom_options.index(option)
        info.winfo.zoom_new.set_index(index)

    def autocenter_cb(self, setting, option, fitsimage, info):
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = { True: 'on', False: 'off' }
            option = choice[option]
        index = self.autocenter_options.index(option)
        info.winfo.center_new.set_index(index)

    def set_autocuts_cb(self, w, index, fitsimage, info):
        option = self.autocut_options[index]
        fitsimage.enable_autocuts(option)

    def set_autozoom_cb(self, w, index, fitsimage, info):
        option = self.autozoom_options[index]
        fitsimage.enable_autozoom(option)

    def set_autocenter_cb(self, w, index, fitsimage, info):
        option = self.autocenter_options[index]
        fitsimage.enable_autocenter(option)

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
        index = self.autocut_options.index(t_['autocuts'])
        info.winfo.cut_new.set_index(index)
        index = self.autozoom_options.index(t_['autozoom'])
        info.winfo.zoom_new.set_index(index)
        option = t_['autocenter']
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = { True: 'on', False: 'off' }
            option = choice[option]
        index = self.autocenter_options.index(option)
        info.winfo.center_new.set_index(index)


    def field_info(self, viewer, channel, info):
        chname = channel.name
        if not channel.extdata.has_key('_info_info'):
            return
        obj = channel.extdata._info_info

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
