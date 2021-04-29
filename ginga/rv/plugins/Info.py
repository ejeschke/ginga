# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Info`` plugin provides a pane of commonly useful metadata about the
associated channel image.  Common information includes some metadata
header values, coordinates, dimensions of the image, minimum and
maximum values, etc.  As the cursor is moved around the image, the X, Y,
Value, RA, and DEC values are updated to reflect the value under the cursor.

**Plugin Type: Global**

``Info`` is a global plugin.  Only one instance can be opened.

**Usage**

At the bottom of the ``Info`` interface the cut levels controls. Here
the low and high cut levels are shown and can be adjusted.  Pressing the
"Auto Levels" button will recalculate cut levels based on the current
auto cut levels algorithm and parameters defined in the channel
preferences.

Below the "Auto Levels" button, the status of the settings for
"Cut New", "Zoom New", and "Center New" are shown for the currently active
channel.  These indicate how new images that are added to the channel
will be affected by auto cut levels, fitting to the window and panning
to the center of the image.

The "Follow New" checkbox controls whether the viewer will automatically
display new images added to the channel.  The "Raise New" checkbox controls
whether an image viewer window is raised when a new image is added.  These
two controls can be useful, for example, if an external program is adding
images to the viewer, and you wish to prevent interruption of your work
examining a particular image.

As a global plugin, ``Info`` responds to a change of focus to a new channel
by displaying the metadata from the new channel.
It typically appears under the "Synopsis" tab in the user interface.

This plugin is not usually configured to be closeable, but the user can
make it so by setting the "closeable" setting to True in the configuration
file--then Close and Help buttons will be added to the bottom of the UI.

"""
from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga import GingaPlugin

__all__ = ['Info']


class Info(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Info, self).__init__(fv)

        self.active = None
        self.info = None
        # truncate names after this size
        self.maxstr = 60

        spec = self.fv.get_plugin_spec(str(self))

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Info')
        self.settings.add_defaults(closeable=not spec.get('hidden', False))
        self.settings.load(onError='silent')

        self.autozoom_options = ['on', 'override', 'once', 'off']
        self.autocut_options = self.autozoom_options
        self.autocenter_options = self.autozoom_options

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.add_callback('field-info', self.field_info)
        fv.add_callback('channel-change', self.focus_cb)
        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(2)

        nb = Widgets.StackWidget()
        self.nb = nb
        vbox.add_widget(nb, stretch=1)

        if self.settings.get('closeable', False):
            btns = Widgets.HBox()
            btns.set_border_width(4)
            btns.set_spacing(4)

            btn = Widgets.Button("Close")
            btn.add_callback('activated', lambda w: self.close())
            btns.add_widget(btn)
            btn = Widgets.Button("Help")
            btn.add_callback('activated', lambda w: self.help())
            btns.add_widget(btn, stretch=0)
            btns.add_widget(Widgets.Label(''), stretch=1)
            vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)
        self.gui_up = True

    def _create_info_window(self, channel):
        sw = Widgets.ScrollArea()

        vbox = Widgets.VBox()
        sw.set_widget(vbox)

        captions = (('Name:', 'label', 'Name', 'llabel'),
                    ('Object:', 'label', 'Object', 'llabel'),
                    ('X:', 'label', 'X', 'llabel'),
                    ('Y:', 'label', 'Y', 'llabel'),
                    ('Image-X:', 'label', 'Image_X', 'llabel'),
                    ('Image-Y:', 'label', 'Image_Y', 'llabel'),
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

        captions = (('Channel:', 'label', 'Channel', 'llabel'),
                    ('Zoom:', 'label', 'Zoom', 'llabel'),
                    ('Cut Low:', 'label', 'Cut Low Value', 'llabel',
                     'Cut Low', 'entry'),
                    ('Cut High:', 'label', 'Cut High Value', 'llabel',
                     'Cut High', 'entry'),
                    ('Auto Levels', 'button', 'spacer_1', 'spacer',
                     'Cut Levels', 'button'),
                    ('Cut New:', 'label', 'Cut New', 'combobox'),
                    ('Zoom New:', 'label', 'Zoom New', 'combobox',
                     'Follow New', 'checkbutton'),
                    ('Center New:', 'label', 'Center New', 'combobox',
                     'Raise New', 'checkbutton'),
                    )

        w, b2 = Widgets.build_info(captions)
        b.update(b2)
        b.cut_levels.set_tooltip("Set cut levels manually")
        loval, hival = channel.fitsimage.get_cut_levels()
        b.auto_levels.set_tooltip("Set cut levels by algorithm")
        b.cut_low.set_tooltip("Set low cut level (press Enter)")
        b.cut_low.set_length(9)
        b.cut_low.set_text(str(loval))
        b.cut_low_value.set_text(str(loval))
        b.cut_high.set_tooltip("Set high cut level (press Enter)")
        b.cut_high.set_length(9)
        b.cut_high.set_text(str(hival))
        b.cut_high_value.set_text(str(hival))

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

        b.follow_new.set_tooltip("Automatically switch to new images in channel")
        b.raise_new.set_tooltip("Automatically raise channel viewer for new images")

        row = Widgets.HBox()
        row.set_spacing(0)
        row.set_border_width(0)
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(row, stretch=0)

        return sw, b

    def add_channel(self, viewer, channel):
        if not self.gui_up:
            return
        sw, winfo = self._create_info_window(channel)
        chname = channel.name

        self.nb.add_widget(sw, title=chname)
        index = self.nb.index_of(sw)  # noqa
        info = Bunch.Bunch(widget=sw, winfo=winfo,
                           mode_w=None,
                           chinfo=channel)
        channel.extdata._info_info = info

        winfo.channel.set_text(chname)
        winfo.cut_low.add_callback('activated', self.cut_levels,
                                   channel, info)
        winfo.cut_high.add_callback('activated', self.cut_levels,
                                    channel, info)
        winfo.cut_levels.add_callback('activated', self.cut_levels,
                                      channel, info)
        winfo.auto_levels.add_callback('activated', self.auto_levels,
                                       channel, info)
        winfo.cut_new.add_callback('activated', self.set_autocuts_cb,
                                   channel, info)
        winfo.zoom_new.add_callback('activated', self.set_autozoom_cb,
                                    channel, info)
        winfo.center_new.add_callback('activated', self.set_autocenter_cb,
                                      channel, info)
        winfo.follow_new.add_callback('activated', self.set_follow_cb,
                                      channel, info)
        winfo.raise_new.add_callback('activated', self.set_raise_cb,
                                     channel, info)

        fitsimage = channel.fitsimage
        fitssettings = fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.get_setting(name).add_callback(
                'set', self.cutset_cb, channel)
        for name in ['scale']:
            fitssettings.get_setting(name).add_callback(
                'set', self.zoomset_cb, channel)
        fitssettings.get_setting('autocuts').add_callback(
            'set', self.autocuts_cb, channel)
        fitssettings.get_setting('autozoom').add_callback(
            'set', self.autozoom_cb, channel)
        fitssettings.get_setting('autocenter').add_callback(
            'set', self.autocenter_cb, channel)
        fitssettings.get_setting('switchnew').add_callback(
            'set', self.follow_cb, channel)
        fitssettings.get_setting('raisenew').add_callback(
            'set', self.raise_cb, channel)

        self.set_info(info, fitsimage)

    def delete_channel(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        info = channel.extdata._info_info
        channel.extdata._info_info = None
        widget = info.widget
        self.nb.remove(widget, delete=True)
        self.active = None
        self.info = None

    def start(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            self.add_channel(self.fv, channel)

        channel = self.fv.get_channel_info()
        if channel is not None:
            viewer = channel.fitsimage

            image = viewer.get_image()
            if image is not None:
                self.redo(channel, image)

            self.focus_cb(viewer, channel)

    def stop(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            channel.extdata._info_info = None

        self.active = None
        self.nb = None
        self.info = None
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def redo(self, channel, image):
        if not self.gui_up:
            return
        fitsimage = channel.fitsimage
        info = channel.extdata._info_info

        self.set_info(info, fitsimage)
        return True

    def focus_cb(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name

        if self.active != chname:
            if '_info_info' not in channel.extdata:
                self.add_channel(viewer, channel)
            info = channel.extdata._info_info
            widget = info.widget
            index = self.nb.index_of(widget)
            self.nb.set_index(index)
            self.active = chname
            self.info = info

        self.set_info(self.info, channel.fitsimage)

    def zoomset_cb(self, setting, value, channel):
        """This callback is called when the main window is zoomed.
        """
        if not self.gui_up:
            return
        info = channel.extdata._info_info
        if info is None:
            return
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

    def cutset_cb(self, setting, value, channel):
        if not self.gui_up:
            return
        info = channel.extdata._info_info
        if info is None:
            return
        loval, hival = value
        #info.winfo.cut_low.set_text('%.4g' % (loval))
        info.winfo.cut_low_value.set_text('%.4g' % (loval))
        #info.winfo.cut_high.set_text('%.4g' % (hival))
        info.winfo.cut_high_value.set_text('%.4g' % (hival))

    def autocuts_cb(self, setting, option, channel):
        if not self.gui_up:
            return
        info = channel.extdata._info_info
        if info is None:
            return
        self.logger.debug("autocuts changed to %s" % option)
        index = self.autocut_options.index(option)
        info.winfo.cut_new.set_index(index)

    def autozoom_cb(self, setting, option, channel):
        if not self.gui_up:
            return
        info = channel.extdata._info_info
        if info is None:
            return
        index = self.autozoom_options.index(option)
        info.winfo.zoom_new.set_index(index)

    def autocenter_cb(self, setting, option, channel):
        if not self.gui_up:
            return
        info = channel.extdata._info_info
        if info is None:
            return
        # Hack to convert old values that used to be T/F
        if isinstance(option, bool):
            choice = {True: 'on', False: 'off'}
            option = choice[option]
        index = self.autocenter_options.index(option)
        info.winfo.center_new.set_index(index)

    def follow_cb(self, setting, option, channel):
        if not self.gui_up:
            return
        info = channel.extdata._info_info
        if info is None:
            return
        info.winfo.follow_new.set_state(option)

    def raise_cb(self, setting, option, channel):
        if not self.gui_up:
            return
        info = channel.extdata._info_info
        if info is None:
            return
        info.winfo.raise_new.set_state(option)

    def set_autocuts_cb(self, w, index, channel, info):
        if not self.gui_up:
            return
        option = self.autocut_options[index]
        channel.fitsimage.enable_autocuts(option)

    def set_autozoom_cb(self, w, index, channel, info):
        if not self.gui_up:
            return
        option = self.autozoom_options[index]
        channel.fitsimage.enable_autozoom(option)

    def set_autocenter_cb(self, w, index, channel, info):
        if not self.gui_up:
            return
        option = self.autocenter_options[index]
        channel.fitsimage.enable_autocenter(option)

    def set_follow_cb(self, w, tf, channel, info):
        if not self.gui_up:
            return
        channel.fitsimage.get_settings().set(switchnew=tf)

    def set_raise_cb(self, w, tf, channel, info):
        if not self.gui_up:
            return
        channel.fitsimage.get_settings().set(raisenew=tf)

    # LOGIC

    def trunc(self, s):
        if len(s) > self.maxstr:
            return s[:self.maxstr - 3] + '...'
        else:
            return s

    def set_info(self, info, fitsimage):
        # Show cut levels
        loval, hival = fitsimage.get_cut_levels()
        #info.winfo.cut_low.set_text('%.4g' % (loval))
        info.winfo.cut_low_value.set_text('%.4g' % (loval))
        #info.winfo.cut_high.set_text('%.4g' % (hival))
        info.winfo.cut_high_value.set_text('%.4g' % (hival))

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
            choice = {True: 'on', False: 'off'}
            option = choice[option]
        index = self.autocenter_options.index(option)
        info.winfo.center_new.set_index(index)
        info.winfo.follow_new.set_state(t_['switchnew'])
        info.winfo.raise_new.set_state(t_['raisenew'])

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

        # Show dimensions
        dim_txt = "%dx%d" % (width, height)
        info.winfo.dimensions.set_text(dim_txt)

    def field_info(self, viewer, channel, info):
        if not self.gui_up or channel is None:
            return
        if '_info_info' not in channel.extdata:
            return
        obj = channel.extdata._info_info

        obj.winfo.x.set_text("%.3f" % info.x)
        obj.winfo.y.set_text("%.3f" % info.y)
        if 'image_x' in info:
            obj.winfo.image_x.set_text("%.3f" % info.image_x)
        else:
            obj.winfo.image_x.set_text("")
        if 'image_y' in info:
            obj.winfo.image_y.set_text("%.3f" % info.image_y)
        else:
            obj.winfo.image_y.set_text("")
        obj.winfo.value.set_text(str(info.value))
        if 'ra_txt' in info:
            obj.winfo.ra.set_text(info.ra_txt)
            obj.winfo.dec.set_text(info.dec_txt)
        if 'ra_lbl' in info:
            obj.winfo.lbl_ra.set_text(info.ra_lbl + ':')
            obj.winfo.lbl_dec.set_text(info.dec_lbl + ':')

    def cut_levels(self, w, channel, info):
        fitsimage = channel.fitsimage
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

    def auto_levels(self, w, channel, info):
        channel.fitsimage.auto_levels()

    def __str__(self):
        return 'info'

# END
