# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Thumbs`` plugin provides a thumbnail index of all images viewed since
the program was started.

**Plugin Type: Global**

``Thumbs`` is a global plugin.  Only one instance can be opened.

**Usage**

By default, ``Thumbs`` appear in cronological viewing history,
with the newest images at the bottom and the oldest at the top.
The sorting can be made alphanumeric by a setting in the
"plugin_Thumbs.cfg" configuration file.

Clicking on a thumbnail navigates you directly to that image in the
associated channel.  Hovering the cursor over a thumbnail will show a
tool tip that contains a couple of useful pieces of metadata from the
image.

The "Auto Scroll" checkbox, if checked, will cause the ``Thumbs`` pan to
scroll to the active image.

This plugin is not usually configured to be closeable, but the user can
make it so by setting the "closeable" setting to True in the configuration
file--then Close and Help buttons will be added to the bottom of the UI.

**Excluding images from Thumbs**

.. note:: This also controls the behavior of ``Contents``.

Although the default behavior is for every image that is loaded into the
reference viewer to show up in ``Thumbs``, there may be cases where this
is undesirable (e.g., when there are many images being loaded at a
periodic rate by some automated process).  In such cases there are two
mechanisms for suppressing certain images from showing up in ``Thumbs``:

* Assigning the "genthumb" setting to False in a channel's settings
  (for example from the ``Preferences`` plugin, under the "General"
  settings) will exclude the channel itself and any of its images.
* Setting the "nothumb" keyword in the metadata of an image wrapper
  (not the FITS header, but by e.g., ``image.set(nothumb=True)``)
  will exclude that particular image from ``Thumbs``, even if the
  "genthumb" setting is True for that channel.

"""
import os
import math
import time
import threading
import bisect

from ginga import GingaPlugin
from ginga import RGBImage
from ginga.misc import Bunch
from ginga.util import iohelper
from ginga.gw import Widgets, Viewers
from ginga.util.paths import icondir
from ginga.pilw.ImageViewPil import CanvasView
from ginga.util import io_rgb

__all__ = ['Thumbs']


class Thumbs(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        # For thumbnail pane
        self.thumblock = threading.RLock()
        self.thumb_dict = {}
        self.thumb_list = []
        self.thumb_num_cols = 1
        self._wd = 300
        self._ht = 400
        self._cmxoff = 0
        self._cmyoff = 0
        self._displayed_thumb_dict = {}
        tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        spec = self.fv.get_plugin_spec(str(self))

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Thumbs')
        self.settings.add_defaults(cache_thumbs=False,
                                   cache_location='local',
                                   auto_scroll=False,
                                   rebuild_wait=0.5,
                                   tt_keywords=tt_keywords,
                                   mouseover_name_key='NAME',
                                   thumb_length=180,
                                   thumb_hsep=15,
                                   thumb_vsep=15,
                                   sort_order=None,
                                   label_length=25,
                                   label_cutoff='right',
                                   highlight_tracks_keyboard_focus=True,
                                   label_font_color='white',
                                   label_font='sans condensed',
                                   label_font_size=10,
                                   label_bg_color='lightgreen',
                                   autoload_visible_thumbs=False,
                                   autoload_interval=0.25,
                                   update_interval=0.25,
                                   closeable=not spec.get('hidden', False),
                                   transfer_attrs=['transforms', 'autocuts',
                                                   'cutlevels', 'rgbmap',
                                                   'icc', 'interpolation'])
        self.settings.load(onError='silent')
        # max length of thumb on the long side
        self.thumb_width = self.settings.get('thumb_length', 180)
        # distance in pixels between thumbs
        self.thumb_hsep = self.settings.get('thumb_hsep', 15)
        self.thumb_vsep = self.settings.get('thumb_vsep', 15)
        self.transfer_attrs = self.settings.get('transfer_attrs', [])

        # used to open thumbnails on disk
        self.rgb_opener = io_rgb.RGBFileHandler(self.logger)
        tmp_path = os.path.join(icondir, 'fits.png')
        self.placeholder_image = self.rgb_opener.load_file(tmp_path)

        # Build our thumb generator
        self.thumb_generator = self.get_thumb_generator()

        # a timer that controls how fast we attempt to update a thumbnail
        # after its associated full image has been modified
        self.timer_redo = self.fv.get_backend_timer()
        self.timer_redo.set_callback('expired', self.timer_redo_cb)
        self.lagtime = self.settings.get('rebuild_wait', 0.5)

        # a timer that controls how quickly we attempt to autoload missing
        # thumbnails
        self.timer_autoload = self.fv.get_backend_timer()
        self.timer_autoload.set_callback('expired', self.timer_autoload_cb)
        self.autoload_interval = self.settings.get('autoload_interval',
                                                   0.25)
        self.autoload_visible = self.settings.get('autoload_visible_thumbs',
                                                  False)
        self.autoload_serial = time.time()

        # timer that controls how quickly we attempt to rebuild thumbs after
        # a pan/scroll operation
        self.timer_update = self.fv.get_backend_timer()
        self.timer_update.set_callback('expired', self.timer_update_cb)
        self.update_interval = 0.25
        self._to_build = set([])
        self._latest_thumb = None
        self.save_thumbs = self.settings.get('cache_thumbs', False)

        # this will hold the thumbnails pane viewer
        self.c_view = None

        # TODO: these maybe should be configurable by channel
        # different instruments have different keywords of interest
        self.keywords = self.settings.get('tt_keywords', tt_keywords)
        self.keywords.insert(0, self.settings.get('mouseover_name_key', 'NAME'))

        self.re_hilite_set = set([])
        self.highlight_tracks_keyboard_focus = self.settings.get(
            'highlight_tracks_keyboard_focus', True)
        self._tkf_highlight = set([])

        fv.set_callback('add-image', self.add_image_cb)
        fv.set_callback('add-image-info', self.add_image_info_cb)
        fv.set_callback('remove-image-info', self.remove_image_info_cb)
        fv.set_callback('add-channel', self.add_channel_cb)
        fv.set_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('channel-change', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        # construct an interactive viewer to view and scroll
        # the thumbs pane
        self.c_view = Viewers.CanvasView(logger=self.logger)
        c_v = self.c_view
        c_v.set_desired_size(self._wd, self._ht)
        c_v.enable_autozoom('off')
        c_v.enable_autocuts('off')
        c_v.set_pan(0, 0)
        c_v.scale_to(1.0, 1.0)
        # Y-axis flipped
        c_v.transform(False, True, False)
        c_v.cut_levels(0, 255)
        c_v.set_bg(0.4, 0.4, 0.4)
        # for debugging
        c_v.set_name('cmimage')
        c_v.add_callback('configure', self.thumbpane_resized_cb)
        c_v.add_callback('drag-drop', self.drag_drop_cb)
        c_v.get_settings().get_setting('pan').add_callback('set', self.thumbs_pan_cb)

        canvas = c_v.get_canvas()
        canvas.register_for_cursor_drawing(c_v)
        canvas.set_draw_mode('pick')
        canvas.ui_set_active(True, viewer=c_v)
        self.canvas = canvas

        bd = c_v.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(False)
        bd.enable_cmap(False)
        bd.get_settings().set(scroll_pan_lock_x=True)

        # remap some bindings for pan mode into no mode needed
        bm = c_v.get_bindmap()
        for name in ['home', 'end', 'page_up', 'page_down',
                     'left', 'right', 'up', 'down']:
            bm.map_event(None, [], 'kp_%s' % name, 'pan_%s' % name)
        # scroll wheel
        bm.map_event(None, [], 'sc_scroll', 'pan')

        iw = Viewers.GingaScrolledViewerWidget(c_v)
        iw.resize(self._wd, self._ht)
        iw.scroll_bars(horizontal='auto', vertical='auto')

        vbox.add_widget(iw, stretch=1)

        captions = (('Auto scroll', 'checkbutton', 'Clear', 'button'),
                    )
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.auto_scroll.set_tooltip(
            "Scroll the thumbs window when new images arrive")
        b.clear.set_tooltip("Remove all current thumbnails")
        b.clear.add_callback('activated', lambda w: self.clear())
        auto_scroll = self.settings.get('auto_scroll', False)
        b.auto_scroll.set_state(auto_scroll)
        vbox.add_widget(w, stretch=0)

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

    def get_thumb_generator(self):
        tg = CanvasView(logger=self.logger)
        tg.configure_surface(self.thumb_width, self.thumb_width)
        tg.enable_autozoom('on')
        tg.set_autocut_params('histogram')
        tg.enable_autocuts('on')
        tg.enable_auto_orient(True)
        tg.defer_redraw = False
        tg.set_bg(0.7, 0.7, 0.7)
        return tg

    def drag_drop_cb(self, viewer, urls):
        """Punt drag-drops to the ginga shell.
        """
        channel = self.fv.get_current_channel()
        if channel is None:
            return
        self.fv.open_uris(urls, chname=channel.name, bulk_add=True)
        return True

    def start(self):
        self.add_visible_thumbs()

    def stop(self):
        self.gui_up = False

    def close(self):
        # clear current thumbs
        canvas = self.c_view.get_canvas()
        canvas.delete_all_objects()
        self._displayed_thumb_dict = dict()

        self.fv.stop_global_plugin(str(self))
        self.c_view = None
        return True

    def _get_thumb_key(self, chname, image):
        path = image.get('path', None)
        return self.get_thumb_key(chname, image.get('name'), path)

    def get_thumb_key(self, chname, imname, path):
        if path is not None:
            path = os.path.abspath(path)
        thumbkey = (chname, imname, path)
        return thumbkey

    def add_image_cb(self, shell, chname, image, info):
        """This callback happens when an image is loaded into one of the
        channels in the Ginga shell.
        """
        channel = self.fv.get_channel(chname)
        genthumb = channel.settings.get('genthumb', True)
        if not genthumb:
            return False

        self.fv.gui_do(self._add_image, shell, chname, image, info)

    def _add_image(self, shell, chname, image, info):
        # invoked via add_image_cb()
        self.fv.assert_gui_thread()

        channel = self.fv.get_channel(chname)
        if info is None:
            try:
                imname = image.get('name', None)
                info = channel.get_image_info(imname)
            except KeyError:
                self.logger.warn("no information in channel about image '%s'" % (
                    imname))
                return False

        # Get any previously stored thumb information in the image info
        extras = info.setdefault('thumb_extras', Bunch.Bunch())

        # Get metadata for mouse-over tooltip
        metadata = self._get_tooltip_metadata(info, image)

        # Update the tooltip, in case of new or changed metadata
        text = self._mk_tooltip_text(metadata)
        extras.tooltip = text

        if 'rgbimg' not in extras:
            # since we have full size image in hand, generate a thumbnail
            # now, and cache it for when the thumb is added to the canvas
            thumb_image = self._regen_thumb_image(self.thumb_generator,
                                                  image, extras, channel.fitsimage)
            extras.rgbimg = thumb_image

        self._add_image_info(shell, channel, info)
        return True

    def add_image_info_cb(self, shell, channel, info):
        """This callback happens when an image is loaded into one of the
        channels in the Ginga shell OR information about an image (without)
        the actual image data is loaded into the channel (a lazy load).

        NOTE: in the case where image data is loaded into the channel, BOTH
        `add_image_cb` and `add_image_info_cb` will be called.
        """
        genthumb = channel.settings.get('genthumb', True)
        if not genthumb:
            return False

        self.fv.gui_do(self._add_image_info, shell, channel, info)

    def _add_image_info(self, shell, channel, info):
        # invoked via add_image_info_cb()
        self.fv.assert_gui_thread()

        # Do we already have this thumb loaded?
        chname = channel.name
        thumbkey = self.get_thumb_key(chname, info.name, info.path)
        thumbpath = self.get_thumbpath(info.path)

        with self.thumblock:
            try:
                bnch = self.thumb_dict[thumbkey]

                if bnch.thumbpath == thumbpath:
                    self.logger.debug("we have this thumb--skipping regeneration")
                    return False

                # if these are not equal then the mtime must have
                # changed on the file, better reload and regenerate
                self.logger.debug("we have this thumb, but thumbpath is different--regenerating thumb")
                bnch.thumbpath = thumbpath
                #bnch.extras.setvals(placeholder=True)
                return

            except KeyError:
                self.logger.debug("we don't seem to have this thumb--generating thumb")

            self._insert_lazy_thumb(thumbkey, chname, info, thumbpath)

        return True

    def remove_image_info_cb(self, shell, channel, image_info):
        """This callback is called when an image is removed from a channel
        in the Ginga shell.
        """
        chname, imname, impath = channel.name, image_info.name, image_info.path
        try:
            thumbkey = self.get_thumb_key(chname, imname, impath)
            self.remove_thumb(thumbkey)
        except Exception as e:
            self.logger.error("Error removing thumb for %s: %s" % (
                imname, str(e)))

    def remove_thumb(self, thumbkey):
        """Remove the thumb indicated by `thumbkey`.
        """
        with self.thumblock:
            self.logger.debug("Removing thumb %s" % (str(thumbkey)))
            if thumbkey in self.thumb_dict:
                del self.thumb_dict[thumbkey]
            if thumbkey in self.thumb_list:
                self.thumb_list.remove(thumbkey)

            # Unhighlight
            chname = thumbkey[0]
            channel = self.fv.get_channel(chname)
            self._tkf_highlight.discard(thumbkey)
            channel.extdata.thumbs_old_highlight.discard(thumbkey)

        self.timer_update.set(self.update_interval)

    def thumbpane_resized_cb(self, thumb_viewer, width, height):
        """This callback is called when the Thumbs pane is resized.
        """
        self.fv.gui_do_oneshot('thumbs-resized', self._resized, width, height)

    def _resized(self, width, height):
        # invoked via thumbpane_resized_cb()
        self.fv.assert_gui_thread()
        self.logger.debug("thumbs resized, width=%d" % (width))

        with self.thumblock:
            self._cmxoff = -width // 2 + 10
            cols = max(1, width // (self.thumb_width + self.thumb_hsep))
            self.logger.debug("column count is now %d" % (cols))
            self.thumb_num_cols = cols

        self.timer_update.set(self.update_interval)
        return False

    def load_file(self, thumbkey, chname, info):
        """Called when a thumbnail is clicked (denoted by `thumbkey`)
        to load the thumbnail.
        """
        self.fv.assert_gui_thread()
        self.logger.debug("loading image: %s" % (str(thumbkey)))
        # TODO: deal with channel object directly?
        self.fv.switch_name(chname, info.name, path=info.path,
                            image_future=info.image_future)

    def clear(self):
        """Called when "Clear" button is clicked to clear the pane
        of thumbnails.
        """
        with self.thumblock:
            self.thumb_list = []
            self.thumb_dict = {}
            self._displayed_thumb_dict = {}
            self._tkf_highlight = set([])
            self.canvas.delete_all_objects(redraw=False)
            self.canvas.update_canvas(whence=0)

        self.timer_update.set(self.update_interval)

    def add_channel_cb(self, shell, channel):
        """Called when a channel is added from the main interface.
        Parameter is channel (a bunch).
        """
        fitsimage = channel.fitsimage
        fitssettings = fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.get_setting(name).add_callback(
                'set', self.cutset_cb, fitsimage)
        fitsimage.add_callback('transform', self.transform_cb)

        rgbmap = fitsimage.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, fitsimage)

        # add old highlight set to channel external data
        channel.extdata.setdefault('thumbs_old_highlight', set([]))

    def focus_cb(self, shell, channel):
        """This callback is called when a channel viewer is focused.
        We use this to highlight the proper thumbs in the Thumbs pane.
        """
        # Reflect transforms, colormap, etc.
        fitsimage = channel.fitsimage
        image = channel.get_current_image()
        if image is not None:
            chname = channel.name
            thumbkey = self._get_thumb_key(chname, image)
            new_highlight = set([thumbkey])

            if self.have_thumbnail(fitsimage, image):
                # schedule an update of the thumbnail to pick up changes
                self.redo_delay(fitsimage)
        else:
            # no image has the focus
            new_highlight = set([])

        if self.highlight_tracks_keyboard_focus:
            self.update_highlights(self._tkf_highlight, new_highlight)
            self._tkf_highlight = new_highlight

    def transform_cb(self, fitsimage):
        """Called when a channel viewer has a transform event.
        Used to transform the corresponding thumbnail.
        """
        self.redo_delay(fitsimage)
        return True

    def cutset_cb(self, setting, value, fitsimage):
        """Called when a channel viewer has a cut levels event.
        Used to adjust cuts on the corresponding thumbnail.
        """
        self.redo_delay(fitsimage)
        return True

    def rgbmap_cb(self, rgbmap, fitsimage):
        """Called when a channel viewer has an RGB mapper event.
        Used to make color and contrast adjustments on the corresponding
        thumbnail.
        """
        # color mapping has changed in some way
        self.redo_delay(fitsimage)
        return True

    def redo_delay(self, fitsimage):
        # Delay regeneration of thumbnail until most changes have propagated
        self.timer_redo.data.setvals(fitsimage=fitsimage)
        self.timer_redo.set(self.lagtime)
        return True

    def timer_redo_cb(self, timer):
        """Called when the redo timer expires; used to rebuild the thumbnail
        corresponding to changes in the viewer.
        """
        self.fv.assert_gui_thread()
        self.redo_thumbnail(timer.data.fitsimage)

    def timer_autoload_cb(self, timer):
        """Called when the autoload timer expires; used to expand placeholder
        thumbnails.
        """
        self.fv.assert_gui_thread()
        self.fv.nongui_do(self._autoload_thumbs)

    def _autoload_thumbs(self):
        # invoked via timer_autoload_cb()
        self.logger.debug("autoload missing thumbs")
        self.fv.assert_nongui_thread()

        with self.thumblock:
            to_build = self._to_build.copy()

        serial = self.autoload_serial
        for thumbkey in to_build:
            if serial != self.autoload_serial or len(to_build) == 0:
                # cancel this autoload session if autoload set has changed
                return

            with self.thumblock:
                bnch = self.thumb_dict.get(thumbkey, None)
            if bnch is None:
                return

            # Get any previously stored thumb information in the image info
            extras = bnch.extras

            placeholder = extras.get('placeholder', True)
            ignore = extras.get('ignore', False)
            path = bnch.info.path
            if placeholder and path is not None and not ignore:
                self.force_load_for_thumb(thumbkey, path, bnch, extras)

    def force_load_for_thumb(self, thumbkey, path, bnch, extras):
        """Called by _autoload_thumbs() to load a file if the pane is
        currently showing a placeholder for a thumb.
        """
        self.logger.debug("autoload missing [%s]" % (path))
        info = bnch.info
        chname = thumbkey[0]
        channel = self.fv.get_channel(chname)
        try:
            thumb_image = self._get_thumb_image(channel, info, None, extras,
                                                no_placeholder=True)
            if thumb_image is not None:
                self.fv.gui_do(self.update_thumbnail, thumbkey, thumb_image,
                               None)
                return

            # <-- No easy thumb to load.  Forced to load the full image
            #     if we want a thumbnail
            if not self.autoload_visible:
                return

            image = self.fv.load_image(path, show_error=False)
            self.logger.debug("loaded [%s]" % (path))

            ## self.fv.gui_do(channel.add_image_update, image, info,
            ##                update_viewer=False)

            self.fv.gui_do(self.redo_thumbnail_image, channel, image, bnch,
                           save_thumb=self.save_thumbs)

        except Exception as e:
            self.logger.error("autoload missing [%s] failed:" % (path))
            # load errors will be reported in self.fv.load_image()
            # Just ignore autoload errors for now...
            extras.ignore = True

    def update_highlights(self, old_highlight_set, new_highlight_set):
        """Unhighlight the thumbnails represented by `old_highlight_set`
        and highlight the ones represented by new_highlight_set.

        Both are sets of thumbkeys.
        """
        with self.thumblock:
            common = old_highlight_set & new_highlight_set
            un_hilite_set = old_highlight_set - common
            re_hilite_set = new_highlight_set | common

            bg = self.settings.get('label_bg_color', 'lightgreen')
            fg = self.settings.get('label_font_color', 'white')

            # unhighlight thumb labels that should NOT be highlighted any more
            for thumbkey in un_hilite_set:
                if thumbkey in self.thumb_dict:
                    bnch = self.thumb_dict[thumbkey]
                    namelbl = bnch.get('namelbl', None)
                    if namelbl is not None:
                        namelbl.color = fg

            # highlight new labels that should be
            for thumbkey in re_hilite_set:
                if thumbkey in self.thumb_dict:
                    bnch = self.thumb_dict[thumbkey]
                    namelbl = bnch.get('namelbl', None)
                    if namelbl is not None:
                        namelbl.color = bg

            self.re_hilite_set = re_hilite_set

        if self.gui_up:
            self.c_view.redraw(whence=3)

    def redo(self, channel, image):
        """This method is called when an image is set in a channel.
        In this plugin it mostly serves to cause a different thumbnail
        label to be highlighted.
        """
        self.fv.assert_gui_thread()
        self.logger.debug("image set")
        chname = channel.name

        # get old highlighted thumbs for this channel -- will be
        # an empty set or one thumbkey
        old_highlight = channel.extdata.thumbs_old_highlight

        # calculate new highlight thumbkeys -- again, an empty set
        # or one thumbkey
        if image is not None:
            thumbkey = self._get_thumb_key(chname, image)
            new_highlight = set([thumbkey])
        else:
            # no image has the focus
            new_highlight = set([])

        nothumb = (image.get('nothumb', False) or
                   not channel.settings.get('genthumb', True))

        with self.thumblock:
            #if not self.have_thumbnail(channel.fitsimage, image):
            if thumbkey not in self.thumb_dict and not nothumb:
                # No memory of this thumbnail, so regenerate it
                if not self._add_image(self.fv, chname, image, None):
                    return

        # this would have auto scroll feature pan to most recent image
        # loaded in channel
        #self.auto_scroll(thumbkey)

        self.logger.debug("highlighting")
        # Only highlights active image in the current channel
        if self.highlight_tracks_keyboard_focus:
            self.update_highlights(self._tkf_highlight, new_highlight)
            self._tkf_highlight = new_highlight

        # Highlight all active images in all channels
        else:
            self.update_highlights(old_highlight, new_highlight)
            channel.extdata.thumbs_old_highlight = new_highlight

        self.redo_delay(channel.fitsimage)

    def have_thumbnail(self, fitsimage, image):
        """Returns True if we already have a thumbnail version of this image
        cached, False otherwise.
        """
        chname = self.fv.get_channel_name(fitsimage)

        # Look up our version of the thumb
        idx = image.get('idx', None)
        path = image.get('path', None)
        if path is not None:
            path = os.path.abspath(path)
            name = iohelper.name_image_from_path(path, idx=idx)
        else:
            name = 'NoName'

        # get image name
        name = image.get('name', name)

        thumbkey = self.get_thumb_key(chname, name, path)
        with self.thumblock:
            return thumbkey in self.thumb_dict

    def _save_thumb(self, thumb_image, bnch):
        extras = bnch.extras
        if extras.get('ignore', False) or extras.get('placeholder', False):
            # don't save placeholders, or thumbs we are instructed to ignore
            return

        thumbpath = self.get_thumbpath(bnch.info.path)
        if thumbpath is not None:
            if os.path.exists(thumbpath):
                os.remove(thumbpath)
            thumb_image.save_as_file(thumbpath)

    def redo_thumbnail(self, viewer, save_thumb=None):
        """Regenerate the thumbnail for the image in the channel viewer
        (`viewer`).  If `save_thumb` is `True`, then save a copy of the
        thumbnail if the user has allowed it.
        """
        # Get the thumbnail image
        image = viewer.get_image()
        if image is None:
            return

        imname = image.get('name', None)
        if imname is None:
            return

        chname = self.fv.get_channel_name(viewer)
        channel = self.fv.get_channel(chname)
        try:
            info = channel[imname]
        except KeyError:
            # don't generate a thumbnail without info
            return

        thumbkey = self.get_thumb_key(chname, imname, info.path)
        with self.thumblock:
            if thumbkey not in self.thumb_dict:
                # No memory of this thumbnail
                return

            bnch = self.thumb_dict[thumbkey]
            self.redo_thumbnail_image(channel, image, bnch,
                                      save_thumb=save_thumb)

    def redo_thumbnail_image(self, channel, image, bnch, save_thumb=None):
        """Regenerate the thumbnail for image `image`, in the channel
        `channel` and whose entry in the thumb_dict is `bnch`.
        If `save_thumb` is `True`, then save a copy of the thumbnail if
        the user has allowed it.
        """
        # image is flagged not to make a thumbnail?
        nothumb = (image.get('nothumb', False) or
                   not channel.settings.get('genthumb', True))
        if nothumb:
            return

        self.logger.debug("redoing thumbnail ...")
        if save_thumb is None:
            save_thumb = self.save_thumbs

        # Get any previously stored thumb information in the image info
        extras = bnch.extras

        # Get metadata for mouse-over tooltip
        info = bnch.info
        metadata = self._get_tooltip_metadata(info, image)

        chname = channel.name
        thumbkey = self.get_thumb_key(chname, info.name, info.path)
        with self.thumblock:
            if thumbkey not in self.thumb_dict:
                # This shouldn't happen, but if it does, ignore the thumbkey
                self.logger.warning("No memory of %s..." % (str(thumbkey)))
                return

            bnch = self.thumb_dict[thumbkey]

            # Generate new thumbnail
            self.logger.debug("generating new thumbnail")
            thumb_image = self._regen_thumb_image(self.thumb_generator,
                                                  image, extras, channel.fitsimage)

            # Save a thumbnail for future browsing
            if save_thumb and info.path is not None:
                try:
                    self._save_thumb(thumb_image, bnch)
                except Exception as e:
                    # if we can't persist the thumbnail, don't let that
                    # stop everything
                    self.logger.error("Couldn't persist thumbnail: {}".format(e))

            self.update_thumbnail(thumbkey, thumb_image, metadata)

        self.fv.update_pending()

    def delete_channel_cb(self, shell, channel):
        """Called when a channel is deleted from the main interface.
        Parameter is channel (a bunch).
        """
        chname_del = channel.name
        # TODO: delete thumbs for this channel!
        self.logger.debug("deleting thumbs for channel '%s'" % (chname_del))
        with self.thumblock:
            new_thumb_list = []
            un_hilite_set = set([])
            for thumbkey in self.thumb_list:
                chname = thumbkey[0]
                if chname != chname_del:
                    new_thumb_list.append(thumbkey)
                else:
                    if thumbkey in self.thumb_dict:
                        del self.thumb_dict[thumbkey]
                    un_hilite_set.add(thumbkey)

            self.thumb_list = new_thumb_list
            self._tkf_highlight -= un_hilite_set  # Unhighlight

        self.timer_update.set(self.update_interval)

    def _get_tooltip_metadata(self, info, image, keywords=None):
        """Construct a metadata dict containing values for selected
        `keywords` (defaults to `self.keywords`) for the image `image`
        (can be `None`) whose info dict is `info`.
        """
        # Get metadata for mouse-over tooltip
        header = {}
        if image is not None:
            header = image.get_header()

        if keywords is None:
            keywords = self.keywords
        metadata = {kwd: header.get(kwd, 'N/A')
                    for kwd in keywords}

        # assign a name in the metadata if we don't have one yet
        name_key = self.settings.get('mouseover_name_key', 'NAME')
        if metadata.setdefault(name_key, info.name) == 'N/A':
            metadata[name_key] = info.name

        return metadata

    def make_tt(self, thumbs_viewer, canvas, text, pt, obj, fontsize=10):
        """Create a tooltip pop-up for a thumbnail to be displayed in
        `thumbs_viewer` on its `canvas` based on `text` where the cursor
        is at point `pt` and on the thumbnail object `obj`.  This object
        is created but not added to the canvas.

        NOTE: currently `pt` is not used, but kept for possible future use.
        """
        # Determine pop-up position on canvas.  Try to align a little below
        # the thumbnail image and offset a bit
        x1, y1, x2, y2 = obj.get_llur()

        x = x1 + 10
        y = y1 + 10
        mxwd = 0
        lines = text.split('\n')

        # create the canvas object representing the tooltip
        point = canvas.dc.Point(x, y, radius=0, color='black', alpha=0.0)
        rect = canvas.dc.Rectangle(x, y, x, y, color='black', fill=True,
                                   fillcolor='lightyellow')
        crdmap = thumbs_viewer.get_coordmap('offset')
        crdmap.refobj = point

        l = [point, rect]
        a, b = 2, 0
        for line in lines:
            text = canvas.dc.Text(a, b, text=line, color='black',
                                  font='sans condensed', fontsize=fontsize)
            text.crdmap = crdmap
            l.append(text)
            txt_wd, txt_ht = thumbs_viewer.renderer.get_dimensions(text)
            b += txt_ht + 2
            text.y = b
            mxwd = max(mxwd, txt_wd)
        rect.x2 = rect.x1 + mxwd + 2
        rect.y2 = rect.y1 + b + 4

        obj = canvas.dc.CompoundObject(*l)

        # sanity check and adjustment so that popup will be minimally obscured
        # by a window edge
        x3, y3, x4, y4 = thumbs_viewer.get_datarect()
        if rect.x2 > x4:
            off = rect.x2 - x4
            rect.x1 -= off
            rect.x2 -= off
            point.x -= off
        if rect.y1 < y3:
            off = y3 - rect.y1
            rect.y1 += off
            rect.y2 += off
            point.y += off
        if rect.y2 > y4:
            off = rect.y2 - y4
            rect.y1 -= off
            rect.y2 -= off
            point.y -= off

        return obj

    def show_tt(self, obj, canvas, event, pt,
                thumbkey, chname, info, tf):
        """Removing any previous tooltip, and if `tf` is `True`, pop up a
        new tooltip on the thumbnail viewer window for the thumb denoted
        by `thumbkey`.  `obj` is the thumbnail compound object, `canvas`
        if the thumbnail viewer canvas, `event` is the cursor event that
        caused the popup. The cursor is at point `pt`. The channel for this
        image has name `chname` and has image info `info`.
        """
        text = info.thumb_extras.tooltip

        tag = '_$tooltip'
        try:
            canvas.delete_object_by_tag(tag)
        except KeyError:
            pass
        if tf:
            tt = self.make_tt(self.c_view, canvas, text, pt, obj)
            canvas.add(tt, tag=tag)

    def _regen_thumb_image(self, tg, image, extras, viewer):
        self.logger.debug("generating new thumbnail")

        if not tg.viewable(image):
            # this is not something we know how to open
            # TODO: other viewers might be able to open it, need to check
            # with them
            image = self.placeholder_image
            extras.setvals(rgbimg=image, placeholder=False,
                           ignore=True, time_update=time.time())
            return image

        tg.set_image(image)
        if viewer is not None:
            # if a viewer was passed, and there is an image loaded there,
            # then copy the viewer attributes to teh thumbnail generator
            v_img = viewer.get_image()
            if v_img is not None:
                viewer.copy_attributes(tg, self.transfer_attrs)

        order = tg.rgb_order
        rgb_img = tg.get_image_as_array(order=order)
        thumb_image = RGBImage.RGBImage(rgb_img, order=order)
        extras.setvals(rgbimg=thumb_image, placeholder=False,
                       time_update=time.time())
        return thumb_image

    def _get_thumb_image(self, channel, info, image, extras,
                         no_placeholder=False):
        """Get a thumb image for the image `image` (can be `None`) that
        is associated with channel `channel` and image information `info`.
        """

        # Choice [A]: is there a thumb image attached to the image info?
        if 'rgbimg' in extras:
            # yes
            return extras.rgbimg

        thumbpath = self.get_thumbpath(info.path)

        # Choice [B]: is the full image available to make a thumbnail?
        if image is None:
            try:
                image = channel.get_loaded_image(info.name)

            except KeyError:
                pass

        if image is not None:
            try:
                thumb_image = self._regen_thumb_image(self.thumb_generator,
                                                      image, extras,
                                                      channel.fitsimage)
                extras.setvals(rgbimg=thumb_image, placeholder=False,
                               time_update=None)
                return thumb_image

            except Exception as e:
                self.logger.warning("Error generating thumbnail: %s" % (str(e)))

        # Choice [C]: is there a cached thumbnail image on disk we can use?
        if (thumbpath is not None) and os.path.exists(thumbpath):
            try:
                # try to load the thumbnail image
                thumb_image = self.rgb_opener.load_file(thumbpath)
                wd, ht = thumb_image.get_size()[:2]
                if max(wd, ht) > self.thumb_width:
                    # <-- thumb size does not match our expected size
                    thumb_image = self._regen_thumb_image(self.thumb_generator,
                                                          thumb_image, extras,
                                                          None)
                thumb_image.set(name=info.name)
                extras.setvals(rgbimg=thumb_image, placeholder=False,
                               time_update=None)
                return thumb_image

            except Exception as e:
                self.logger.warning("Error loading thumbnail: %s" % (str(e)))

        if no_placeholder:
            return None

        # Choice [D]: use a placeholder image
        data_np = self.placeholder_image.get_data()
        thumb_image = RGBImage.RGBImage(data_np=data_np)
        thumb_image.set(name=info.name, path=None)
        extras.setvals(placeholder=True, time_update=None)

        return thumb_image

    def get_thumbpath(self, path, makedir=True):
        """Return the path for the thumbnail location on disk based on the
        path of the original.  Can return `None` if there is no suitable path.
        The preference for where to store thumbnails is set in the settings
        for this plugin.
        """
        if path is None:
            return None

        path = os.path.abspath(path)
        dirpath, filename = os.path.split(path)
        # Get thumb directory
        cache_location = self.settings.get('cache_location', 'local')
        if cache_location == 'ginga':
            # thumbs in .ginga cache
            prefs = self.fv.get_preferences()
            thumbdir = os.path.join(prefs.get_baseFolder(), 'thumbs')
            thumbdir = os.path.join(thumbdir, iohelper.gethex(dirpath))
        else:
            # thumbs in .thumbs subdirectory of image folder
            thumbdir = os.path.join(dirpath, '.thumbs')

        try:
            thumbpath = iohelper.get_thumbpath(thumbdir, path,
                                               makedir=makedir)

        except Exception as e:
            self.logger.debug("Error getting thumb path for '%s': %s" % (
                path, str(e)))
            thumbpath = None

        return thumbpath

    def _calc_thumb_pos(self, row, col):
        """Calculate the thumb data coordinates on the thumbs canvas for
        a thumb at row `row` and column `col`.  Returns a 4-tuple of x/y
        positions for the text item and the image item.
        """
        self.logger.debug("row, col = %d, %d" % (row, col))
        # TODO: should really be text ht
        text_ht = self.thumb_vsep

        # calc in data coords
        thumb_height = self.thumb_width
        twd_hplus = self.thumb_width + self.thumb_hsep
        twd_vplus = thumb_height + text_ht + self.thumb_vsep
        xt = self._cmxoff + (col * twd_hplus)
        yt = self._cmyoff + (row * twd_vplus)

        # position of image
        xi = xt
        yi = yt + 6
        self.logger.debug("xt, yt = %d, %d" % (xt, yt))

        return (xt, yt, xi, yi)

    def get_visible_rows(self):
        """Return the list of thumbkeys for the thumbs that should be
        visible in the Thumbs pane.
        """
        x1, y1, x2, y2 = self.c_view.get_datarect()
        self.logger.debug("datarect=(%f, %f, %f, %f)", x1, y1, x2, y2)

        # TODO: should really be text ht
        text_ht = self.thumb_vsep

        # calc in data coords
        thumb_height = self.thumb_width
        twd_vplus = thumb_height + text_ht + self.thumb_vsep
        # remember, Y-axis is flipped
        row1 = max(0, int(math.floor(y1 / twd_vplus) - 2))
        row2 = max(row1 + 1, int(math.ceil(y2 / twd_vplus) + 2))
        self.logger.debug("row1, row2 = %d, %d" % (row1, row2))
        return row1, row2

    def get_visible_thumbs(self):
        """Return the list of thumbkeys for the thumbs that should be
        visible in the Thumbs pane.
        """
        row1, row2 = self.get_visible_rows()
        i = max(0, row1 * self.thumb_num_cols)
        j = min(len(self.thumb_list) - 1, row2 * self.thumb_num_cols)
        self.logger.debug("i, j = %d, %d" % (i, j))
        thumbs = [self.thumb_list[n] for n in range(i, j + 1)]
        return thumbs

    def add_visible_thumbs(self):
        """Add the thumbs to the canvas that should be visible in the
        Thumbs pane and remove the others.
        """
        if not self.gui_up:
            return
        self.fv.assert_gui_thread()

        canvas = self.c_view.get_canvas()

        with self.thumblock:
            thumb_keys = set(self.get_visible_thumbs())
            old_thumb_keys = set(self._displayed_thumb_dict.keys())
            if old_thumb_keys == thumb_keys:
                # no need to do anything
                self.c_view.redraw(whence=0)
                return

            to_delete = old_thumb_keys - thumb_keys
            to_add = thumb_keys - old_thumb_keys

            # make a copy of these for potential building thumbs
            self._to_build = set(thumb_keys)

            # delete thumbs from canvas that are no longer visible
            canvas.delete_all_objects(redraw=False)
            ## for thumbkey in to_delete:
            ##     bnch = self._displayed_thumb_dict[thumbkey]
            ##     if 'widget' in bnch and canvas.has_object(bnch.widget):
            ##         canvas.delete_object(bnch.widget, redraw=False)

            # update displayed thumbs dict
            self._displayed_thumb_dict = {thumbkey: self.thumb_dict[thumbkey]
                                          for thumbkey in thumb_keys}

            # add newly-visible thumbs to canvas
            row1, row2 = self.get_visible_rows()
            row, col = row1, 0

            while row <= row2:
                i = row * self.thumb_num_cols + col
                if 0 <= i < len(self.thumb_list):
                    thumbkey = self.thumb_list[i]
                    bnch = self.thumb_dict[thumbkey]
                    bnch.setvals(row=row, col=col)

                    if 'widget' not in bnch:
                        # lazily make a canvas object for "empty" thumb entries
                        self._make_thumb(bnch, thumbkey)
                    else:
                        # update object positions for existing entries
                        xt, yt, xi, yi = self._calc_thumb_pos(row, col)
                        bnch.namelbl.x, bnch.namelbl.y = xt, yt
                        bnch.image.x, bnch.image.y = xi, yi

                    if not canvas.has_object(bnch.widget):
                        canvas.add(bnch.widget, redraw=False)

                col = (col + 1) % self.thumb_num_cols
                if col == 0:
                    row += 1

        self.c_view.redraw(whence=0)

        self.fv.update_pending()

        # load and create thumbnails for any placeholder icons
        self.autoload_serial = time.time()
        #self.fv.gui_do_oneshot('thumbs-autoload', self._autoload_thumbs)
        self.timer_autoload.set(self.autoload_interval)

    def update_thumbs(self):
        """This is called whenever the thumb list has changed.
        """
        self.fv.assert_gui_thread()

        with self.thumblock:
            n = len(self.thumb_list)
            row = n // self.thumb_num_cols
            col = n % self.thumb_num_cols

            thumbkey = None
            if self._latest_thumb in self.thumb_dict:
                thumbkey = self._latest_thumb
            else:
                self._latest_thumb = None

        # update the visible limits (e.g. scroll bars)
        xm, ym, x_, y_ = self._calc_thumb_pos(0, 0)
        xt, yt, xi, yi = self._calc_thumb_pos(row, col)
        xi += self.thumb_width * 2
        self.c_view.set_limits([(xm, ym), (xi, yi)], coord='data')

        if thumbkey is not None:
            self.auto_scroll(thumbkey)

        # update the thumbs pane in the case that thumbs visibility
        # has changed
        self.add_visible_thumbs()

    def thumbs_pan_cb(self, thumbs_viewer, pan_vec):
        """This callback is called when the Thumbs pane is panned/scrolled.
        """
        self.fv.gui_do_oneshot('thumbs-pan', self.add_visible_thumbs)

    def _insert_lazy_thumb(self, thumbkey, chname, info, thumbpath):
        """This function gets called to create an initial entry for a
        thumb.
        """
        thumbname = info.name
        self.logger.debug("inserting an empty thumb %s" % (thumbname))

        # Make an initial entry for the thumbs in the tracking dict.
        # Nothing is actually plotted, because the thumb may be in a region
        # that is not visible.
        n = len(self.thumb_list)
        row = n // self.thumb_num_cols
        col = n % self.thumb_num_cols

        extras = info.setdefault('thumb_extras', Bunch.Bunch())
        bnch = Bunch.Bunch(info=info, extras=extras,
                           thumbname=thumbname, chname=chname,
                           thumbpath=thumbpath, row=row, col=col)

        self.thumb_dict[thumbkey] = bnch
        if thumbkey not in self.thumb_list:
            sort_order = self.settings.get('sort_order', None)
            if sort_order is not None:
                bisect.insort(self.thumb_list, thumbkey)
            else:
                self.thumb_list.append(thumbkey)

        self._latest_thumb = thumbkey

        self.timer_update.cond_set(self.update_interval)
        #self.timer_update.set(self.update_interval)

    def _make_thumb(self, bnch, thumbkey):
        """Called from inside add_visible_thumbs() to generate a placeholder
        thumb for thumbs that are not yet made manifest.
        """
        channel = self.fv.get_channel(bnch.chname)
        info = bnch.info
        image = None

        # Get any previously stored thumb information in the image info
        extras = bnch.extras

        thumbpath = self.get_thumbpath(info.path)
        thumb_image = extras.get('rgbimg', None)
        if thumb_image is None:
            thumb_image = self._get_thumb_image(channel, info, image, extras)

        # Get metadata for mouse-over tooltip
        metadata = self._get_tooltip_metadata(info, None)

        thumbname = info.name
        self.logger.debug("inserting thumb %s" % (thumbname))
        chname = bnch.chname

        # If there is no previously made tooltip, then generate one
        if 'tooltip' in extras:
            text = extras.tooltip
        else:
            text = self._mk_tooltip_text(metadata)
            extras.tooltip = text

        canvas = self.canvas
        fg = self.settings.get('label_font_color', 'white')
        bg = self.settings.get('label_bg_color', 'lightgreen')
        fontname = self.settings.get('label_font', 'sans condensed')
        fontsize = self.settings.get('label_font_size', 10)

        # Shorten thumbnail label, if requested
        label_length = self.settings.get('label_length', None)
        label_cutoff = self.settings.get('label_cutoff', None)

        if label_length is not None:
            if label_cutoff is not None:
                thumbname = iohelper.shorten_name(thumbname, label_length,
                                                  side=label_cutoff)
            else:
                thumbname = thumbname[:label_length]

        row, col = bnch.row, bnch.col

        xt, yt, xi, yi = self._calc_thumb_pos(row, col)
        l2 = []
        color = bg if thumbkey in self.re_hilite_set else fg
        namelbl = canvas.dc.Text(xt, yt, text=thumbname, color=color,
                                 font=fontname, fontsize=fontsize,
                                 coord='data')
        l2.append(namelbl)

        image = canvas.dc.Image(xi, yi, thumb_image, alpha=1.0,
                                linewidth=1, color='black', coord='data')
        l2.append(image)

        obj = canvas.dc.CompoundObject(*l2, coord='data')
        obj.pickable = True
        obj.opaque = True

        bnch.setvals(widget=obj, image=image, namelbl=namelbl,
                     thumbpath=thumbpath)

        # set the load callback
        obj.add_callback('pick-down',
                         lambda *args: self.load_file(thumbkey, chname,
                                                      info))
        # set callbacks for tool tips
        obj.add_callback('pick-enter', self.show_tt,
                         thumbkey, chname, info, True)
        obj.add_callback('pick-leave', self.show_tt,
                         thumbkey, chname, info, False)

    def auto_scroll(self, thumbkey):
        """Scroll the Thumbs viewer to the thumb denoted by `thumbkey`.
        """
        if not self.gui_up:
            return
        # force scroll to bottom of thumbs, if checkbox is set
        scrollp = self.w.auto_scroll.get_state()
        if not scrollp:
            return

        with self.thumblock:
            i = self.thumb_list.index(thumbkey)

        row = i // self.thumb_num_cols
        col = i % self.thumb_num_cols

        # override X parameter because we only want to scroll vertically
        pan_x, pan_y = self.c_view.get_pan()
        xt, yt, xi, yi = self._calc_thumb_pos(row, col)
        self.c_view.panset_xy(pan_x, yi)

    def clear_widget(self):
        """Clears the thumbnail viewer of all thumbnails, but does
        not remove them from the thumb_dict or thumb_list.
        """
        if not self.gui_up:
            return
        canvas = self.c_view.get_canvas()
        canvas.delete_all_objects()
        self.c_view.redraw(whence=0)

    def timer_update_cb(self, timer):
        if not self.gui_up:
            return
        self.fv.gui_do_oneshot('thumbs-update', self.update_thumbs)

    def _mk_tooltip_text(self, metadata):
        """Make a tooltip text from values related to interesting keywords
        in `metadata`.
        """
        result = []
        for kwd in self.keywords:
            try:
                text = kwd + ': ' + str(metadata[kwd])

            except Exception as e:
                self.logger.debug("Couldn't get keyword '%s' value: %s" % (
                    kwd, str(e)))
                text = "%s: N/A" % (kwd)
            result.append(text)

        return '\n'.join(result)

    def update_thumbnail(self, thumbkey, thumb_image, metadata):
        """Update the thumbnail denoted by `thumbkey` with a new thumbnail
        image (`thumb_image`) and new knowledge of dict `metadata`.
        """
        with self.thumblock:
            try:
                bnch = self.thumb_dict[thumbkey]
            except KeyError:
                self.logger.debug("No thumb found for %s; not updating "
                                  "thumbs" % (str(thumbkey)))
                return

            info = bnch.info
            # Get any previously stored thumb information in the image info
            extras = bnch.extras

            # Update the tooltip, in case of new or changed metadata
            if metadata is not None:
                text = self._mk_tooltip_text(metadata)
                extras.tooltip = text

            self.logger.debug("updating thumbnail '%s'" % (info.name))
            extras.rgbimg = thumb_image
            cvs_img = bnch.get('image', None)
            if cvs_img is not None:
                # TODO: figure out why set_image() causes corruption of the
                # redraw here.  Instead we force a manual redraw.
                #image.set_image(thumb_image)
                cvs_img.image = thumb_image
                # TODO: need to set width, height?

            if self.gui_up and thumbkey in self._displayed_thumb_dict:
                # redraw the thumbs viewer if the update was to a displayed
                # thumb
                self.c_view.redraw(whence=0)
            self.logger.debug("update finished.")

    def __str__(self):
        return 'thumbs'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Thumbs', package='ginga')

# END
