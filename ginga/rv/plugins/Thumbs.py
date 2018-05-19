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

"""
import os
import math
import time
import threading

from ginga import GingaPlugin
from ginga import RGBImage, BaseImage
from ginga.misc import Bunch
from ginga.util import iohelper
from ginga.gw import Widgets, Viewers
from ginga.util.paths import icondir
from ginga.pilw.ImageViewPil import CanvasView

__all__ = ['Thumbs']


class Thumbs(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        # For thumbnail pane
        self.thumb_dict = {}
        self.thumb_list = []
        self.thumb_num_cols = 1
        self.thumb_row_count = 0
        self.thumb_col_count = 0
        self._wd = 300
        self._ht = 400
        self._cmxoff = 0
        self._cmyoff = 0
        self._displayed_thumb_dict = {}
        tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

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
                                   label_font_size=10,
                                   label_bg_color='lightgreen',
                                   autoload_visible_thumbs=True,
                                   autoload_interval=1.0,
                                   transfer_attrs=['transforms',
                                                   'cutlevels', 'rgbmap'])
        self.settings.load(onError='silent')
        # max length of thumb on the long side
        self.thumb_width = self.settings.get('thumb_length', 180)
        # distance in pixels between thumbs
        self.thumb_hsep = self.settings.get('thumb_hsep', 15)
        self.thumb_vsep = self.settings.get('thumb_vsep', 15)
        self.transfer_attrs = self.settings.get('transfer_attrs', [])

        # Build our thumb generator
        tg = CanvasView(logger=self.logger)
        tg.configure_surface(self.thumb_width, self.thumb_width)
        tg.enable_autozoom('on')
        tg.set_autocut_params('histogram')
        tg.enable_autocuts('on')
        tg.enable_auto_orient(True)
        tg.defer_redraw = False
        tg.set_bg(0.7, 0.7, 0.7)
        self.thumb_generator = tg

        self.thmbtask = fv.get_timer()
        self.thmbtask.set_callback('expired', self.redo_delay_timer)
        self.lagtime = self.settings.get('rebuild_wait', 0.5)
        self.thmblock = threading.RLock()
        self.timer_autoload = fv.get_timer()
        self.timer_autoload.set_callback('expired', self.timer_autoload_cb)
        self.autoload_interval = self.settings.get('autoload_interval',
                                                   1.0)
        self.autoload_visible = self.settings.get('autoload_visible_thumbs',
                                                  False)
        self._to_build = set([])

        # this will hold the thumbnails pane viewer
        self.c_view = None

        # TODO: these maybe should be configurable by channel
        # different instruments have different keywords of interest
        self.keywords = self.settings.get('tt_keywords', tt_keywords)
        self.keywords.insert(0, self.settings.get('mouseover_name_key', 'NAME'))

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

        # construct an interaactive viewer to view and scroll
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
        canvas.ui_set_active(True)
        self.canvas = canvas

        bd = c_v.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(False)
        bd.enable_cmap(False)

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

        captions = (('Auto scroll', 'checkbutton', 'Clear', 'button'),)
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.auto_scroll.set_tooltip(
            "Scroll the thumbs window when new images arrive")
        b.clear.set_tooltip("Remove all current thumbnails")
        b.clear.add_callback('activated', lambda w: self.clear())
        auto_scroll = self.settings.get('auto_scroll', False)
        b.auto_scroll.set_state(auto_scroll)
        vbox.add_widget(w, stretch=0)

        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def drag_drop_cb(self, viewer, urls):
        """Punt drag-drops to the ginga shell.
        """
        channel = self.fv.get_current_channel()
        self.fv.dragdrop(channel.viewer, urls)
        return True

    def _get_thumb_key(self, chname, image):
        path = image.get('path', None)
        return self.get_thumb_key(chname, image.get('name'), path)

    def get_thumb_key(self, chname, imname, path):
        if path is not None:
            path = os.path.abspath(path)
        thumbkey = (chname, imname, path)
        return thumbkey

    def add_image_cb(self, viewer, chname, image, info):

        # Get any previously stored thumb information in the image info
        thumb_extra = info.setdefault('thumb_extras', Bunch.Bunch())

        # Get metadata for mouse-over tooltip
        metadata = self._get_tooltip_metadata(info, image)

        # Update the tooltip, in case of new or changed metadata
        text = self._mk_tooltip_text(metadata)
        thumb_extra.tooltip = text

        if not self.gui_up:
            return False

        channel = self.fv.get_channel(chname)

        if thumb_extra.get('time_update', None) is None:
            self.fv.gui_do(self.redo_thumbnail_image, channel, image, info)

    def add_image_info_cb(self, viewer, channel, info):

        save_thumb = self.settings.get('cache_thumbs', False)

        # Do we already have this thumb loaded?
        chname = channel.name
        thumbkey = self.get_thumb_key(chname, info.name, info.path)
        thumbpath = self.get_thumbpath(info.path)

        with self.thmblock:
            try:
                bnch = self.thumb_dict[thumbkey]
                # if these are not equal then the mtime must have
                # changed on the file, better reload and regenerate
                if bnch.thumbpath == thumbpath:
                    self.logger.debug("we have this thumb--skipping regeneration")
                    return
                self.logger.debug("we have this thumb, but thumbpath is different--regenerating thumb")
            except KeyError:
                self.logger.debug("we don't seem to have this thumb--generating thumb")

        thmb_image = self._get_thumb_image(channel, info, None)

        self.fv.gui_do(self._make_thumb, chname, thmb_image, info, thumbkey,
                       save_thumb=save_thumb, thumbpath=thumbpath)

    def _add_image(self, viewer, chname, image):
        channel = self.fv.get_channel(chname)
        try:
            imname = image.get('name', None)
            info = channel.get_image_info(imname)
        except KeyError:
            self.logger.warn("no information in channel about image '%s'" % (
                imname))
            return

        self.add_image_cb(viewer, chname, image, info)

    def remove_image_info_cb(self, viewer, channel, image_info):
        if not self.gui_up:
            return

        chname, imname, impath = channel.name, image_info.name, image_info.path
        try:
            thumbkey = self.get_thumb_key(chname, imname, impath)
            self.remove_thumb(thumbkey)
        except Exception as e:
            self.logger.error("Error removing thumb for %s: %s" % (
                imname, str(e)))

    def remove_thumb(self, thumbkey):
        with self.thmblock:
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

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)

    def update_thumbs(self, name_list):

        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumb_list) - set(name_list)
        if len(invalid) > 0:
            with self.thmblock:
                for thumbkey in invalid:
                    if thumbkey in self.thumb_list:
                        self.thumb_list.remove(thumbkey)
                    if thumbkey in self.thumb_dict:
                        del self.thumb_dict[thumbkey]
                    self._tkf_highlight.discard(thumbkey)

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)

    def thumbpane_resized_cb(self, thumbvw, width, height):
        self.fv.gui_do_oneshot('thumbs-resized', self._resized, width, height)

    def _resized(self, width, height):
        self.logger.debug("thumbs resized, width=%d" % (width))

        with self.thmblock:
            self._cmxoff = -width // 2 + 10
            cols = max(1, width // (self.thumb_width + self.thumb_hsep))
            self.logger.debug("column count is now %d" % (cols))
            self.thumb_num_cols = cols

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)
        return False

    def load_file(self, thumbkey, chname, info):
        self.logger.debug("loading image: %s" % (str(thumbkey)))
        # TODO: deal with channel object directly?
        self.fv.switch_name(chname, info.name, path=info.path,
                            image_future=info.image_future)

    def clear(self):
        with self.thmblock:
            self.thumb_list = []
            self.thumb_dict = {}
            self._displayed_thumb_dict = {}
            self._tkf_highlight = set([])
            self.canvas.delete_all_objects(redraw=False)
            self.canvas.update_canvas(whence=0)

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)

    def add_channel_cb(self, viewer, channel):
        """Called when a channel is added from the main interface.
        Parameter is channel (a bunch)."""
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

    def focus_cb(self, viewer, channel):
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
        self.redo_delay(fitsimage)
        return True

    def cutset_cb(self, setting, value, fitsimage):
        self.redo_delay(fitsimage)
        return True

    def rgbmap_cb(self, rgbmap, fitsimage):
        # color mapping has changed in some way
        self.redo_delay(fitsimage)
        return True

    def redo_delay(self, fitsimage):
        # Delay regeneration of thumbnail until most changes have propagated
        self.thmbtask.data.setvals(fitsimage=fitsimage)
        self.thmbtask.set(self.lagtime)
        return True

    def redo_delay_timer(self, timer):
        self.fv.gui_do(self.redo_thumbnail, timer.data.fitsimage)

    def timer_autoload_cb(self, timer):
        self.logger.debug("autoload missing thumbs")

        with self.thmblock:
            if len(self._to_build) == 0:
                return
            thumbkey = self._to_build.pop()
            bnch = self.thumb_dict[thumbkey]

        self.fv.nongui_do(self.force_load_for_thumb, thumbkey, bnch, timer)

    def force_load_for_thumb(self, thumbkey, bnch, timer):
        placeholder = bnch.image.get_image().get('placeholder', False)
        path = bnch.info.path
        if placeholder and (path is not None):
            self.logger.debug("autoload missing [%s]" % (path))
            info = bnch.info
            chname = thumbkey[0]
            channel = self.fv.get_channel(chname)
            try:
                image = self.fv.load_image(path, show_error=False)
                self.logger.debug("loaded [%s]" % (path))
                self.fv.gui_do(channel.add_image_update, image, info,
                               update_viewer=False)
            except Exception as e:
                # load errors will be reported in self.fv.load_image()
                # Just ignore autoload errors for now...
                pass

        timer.cond_set(0.10)

    def update_highlights(self, old_highlight_set, new_highlight_set):
        """Unhighlight the thumbnails represented by `old_highlight_set`
        and highlight the ones represented by new_highlight_set.

        Both are sets of thumbkeys.

        """
        with self.thmblock:
            un_hilite_set = old_highlight_set - new_highlight_set
            re_hilite_set = new_highlight_set - old_highlight_set

            # highlight new labels that should be
            bg = self.settings.get('label_bg_color', 'lightgreen')
            fg = self.settings.get('label_font_color', 'black')

            # unhighlight thumb labels that should NOT be highlighted any more
            for thumbkey in un_hilite_set:
                if thumbkey in self.thumb_dict:
                    namelbl = self.thumb_dict[thumbkey].get('namelbl')
                    namelbl.color = fg

            for thumbkey in re_hilite_set:
                if thumbkey in self.thumb_dict:
                    namelbl = self.thumb_dict[thumbkey].get('namelbl')
                    namelbl.color = bg

        self.c_view.redraw(whence=3)

    def redo(self, channel, image):
        """This method is called when an image is set in a channel."""
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

        # TODO: already calculated thumbkey, use simpler test
        if not self.have_thumbnail(channel.fitsimage, image):
            # No memory of this thumbnail, so regenerate it
            self._add_image(self.fv, chname, image)

        self.logger.debug("highlighting")
        # Only highlights active image in the current channel
        if self.highlight_tracks_keyboard_focus:
            self.update_highlights(self._tkf_highlight, new_highlight)
            self._tkf_highlight = new_highlight

        # Highlight all active images in all channels
        else:
            self.update_highlights(old_highlight, new_highlight)
            channel.extdata.thumbs_old_highlight = new_highlight

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
            name = self.fv.name_image_from_path(path, idx=idx)
        else:
            name = 'NoName'

        # get image name
        name = image.get('name', name)

        thumbkey = self.get_thumb_key(chname, name, path)
        with self.thmblock:
            return thumbkey in self.thumb_dict

    def redo_thumbnail(self, viewer, save_thumb=None):
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

        self.redo_thumbnail_image(channel, image, info, save_thumb=save_thumb)

    def redo_thumbnail_image(self, channel, image, info, save_thumb=None):
        # image is flagged not to make a thumbnail?
        nothumb = image.get('nothumb', False)
        if nothumb:
            return

        self.logger.debug("redoing thumbnail ...")
        if save_thumb is None:
            save_thumb = self.settings.get('cache_thumbs', False)

        # Get any previously stored thumb information in the image info
        thumb_extra = info.setdefault('thumb_extras', Bunch.Bunch())

        # Get metadata for mouse-over tooltip
        metadata = self._get_tooltip_metadata(info, image)

        chname = channel.name
        thumbkey = self.get_thumb_key(chname, info.name, info.path)
        with self.thmblock:
            if thumbkey not in self.thumb_dict:
                # No memory of this thumbnail, so regenerate it
                self.logger.debug("No memory of %s, adding..." % (str(thumbkey)))
                self._add_image(self.fv, chname, image)
                return

            # Generate new thumbnail
            self.logger.debug("generating new thumbnail")
            thmb_image = self._regen_thumb_image(image, channel.fitsimage)
            thumb_extra.time_update = time.time()

            # Save a thumbnail for future browsing
            if save_thumb and info.path is not None:
                thumbpath = self.get_thumbpath(info.path)
                if thumbpath is not None:
                    if os.path.exists(thumbpath):
                        os.remove(thumbpath)
                    thmb_image.save_as_file(thumbpath)

            self.update_thumbnail(thumbkey, thmb_image, metadata)
        self.fv.update_pending()

    def delete_channel_cb(self, viewer, channel):
        """Called when a channel is deleted from the main interface.
        Parameter is channel (a bunch)."""
        chname_del = channel.name
        # TODO: delete thumbs for this channel!
        self.logger.debug("deleting thumbs for channel '%s'" % (chname_del))
        with self.thmblock:
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

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)

    def _get_tooltip_metadata(self, info, image, keywords=None):
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

    def make_tt(self, viewer, canvas, text, pt, obj, fontsize=10):
        x1, y1, x2, y2 = obj.get_llur()

        # Determine pop-up position on canvas.  Try to align a little below
        # the thumbnail image and offset a bit
        x = x1 + 10
        y = y1 + 10
        mxwd = 0
        lines = text.split('\n')

        point = canvas.dc.Point(x, y, radius=0, color='black', alpha=0.0)
        rect = canvas.dc.Rectangle(x, y, x, y, color='black', fill=True,
                                   fillcolor='lightyellow')
        crdmap = viewer.get_coordmap('offset')
        crdmap.refobj = point

        l = [point, rect]
        a, b = 2, 0
        for line in lines:
            text = canvas.dc.Text(a, b, text=line, color='black',
                                  fontsize=fontsize)
            text.crdmap = crdmap
            l.append(text)
            txt_wd, txt_ht = viewer.renderer.get_dimensions(text)
            b += txt_ht + 2
            text.y = b
            mxwd = max(mxwd, txt_wd)
        rect.x2 = rect.x1 + mxwd + 2
        rect.y2 = rect.y1 + b + 4

        obj = canvas.dc.CompoundObject(*l)

        # sanity check and adjustment so that popup will be minimally obscured
        # by a window edge
        x3, y3, x4, y4 = viewer.get_datarect()
        if rect.x2 > x4:
            off = rect.x2 - x4
            rect.x1 -= off
            rect.x2 -= off
            point.x -= off

        return obj

    def show_tt(self, obj, canvas, event, pt,
                thumbkey, chname, info, tf):

        text = info.thumb_extras.tooltip

        tag = '_$tooltip'
        try:
            canvas.delete_object_by_tag(tag)
        except KeyError:
            pass
        if tf:
            tt = self.make_tt(self.c_view, canvas, text, pt, obj)
            canvas.add(tt, tag=tag)

    def _regen_thumb_image(self, image, viewer):
        self.logger.debug("generating new thumbnail")

        if not isinstance(image, BaseImage.BaseImage):
            # this is not a regular image type
            image = RGBImage.RGBImage()
            tmp_path = os.path.join(icondir, 'fits.png')
            image.load_file(tmp_path)

        self.thumb_generator.set_image(image)
        if viewer is not None:
            v_img = viewer.get_image()
            if v_img is not None:
                viewer.copy_attributes(self.thumb_generator,
                                       self.transfer_attrs)

        rgb_img = self.thumb_generator.get_image_as_array()
        thmb_image = RGBImage.RGBImage(rgb_img)
        thmb_image.set(placeholder=False)
        return thmb_image

    def _get_thumb_image(self, channel, info, image):

        # Get any previously stored thumb information in the image info
        thumb_extra = info.setdefault('thumb_extras', Bunch.Bunch())

        # Choice [A]: is there a thumb image attached to the image info?
        if 'rgbimg' in thumb_extra:
            # yes
            return thumb_extra.rgbimg

        thumbpath = self.get_thumbpath(info.path)

        # Choice [B]: is the full image available to make a thumbnail?
        if image is None:
            try:
                image = channel.get_loaded_image(info.name)

            except KeyError:
                pass

        if image is not None:
            try:
                thmb_image = self._regen_thumb_image(image, None)
                thumb_extra.rgbimg = thmb_image
                thumb_extra.time_update = time.time()
                return thmb_image

            except Exception as e:
                self.logger.warning("Error generating thumbnail: %s" % (str(e)))

        thmb_image = RGBImage.RGBImage()
        thmb_image.set(name=info.name, placeholder=False)

        # Choice [C]: is there a cached thumbnail image on disk we can use?
        if (thumbpath is not None) and os.path.exists(thumbpath):
            try:
                # try to load the thumbnail image
                thmb_image.load_file(thumbpath)
                thmb_image = self._regen_thumb_image(thmb_image, None)
                thumb_extra.rgbimg = thmb_image
                return thmb_image

            except Exception as e:
                self.logger.warning("Error loading thumbnail: %s" % (str(e)))

        # Choice [D]: load a placeholder image
        tmp_path = os.path.join(icondir, 'fits.png')
        thmb_image.load_file(tmp_path)
        thmb_image.set(path=None, placeholder=True)

        return thmb_image

    def _make_thumb(self, chname, thmb_image, info, thumbkey,
                    save_thumb=False, thumbpath=None):

        # This is called by the plugin FBrowser.make_thumbs() as
        # a gui thread
        with self.thmblock:
            # Save a thumbnail for future browsing
            if save_thumb and (thumbpath is not None):
                thmb_image.save_as_file(thumbpath)

        # Get metadata for mouse-over tooltip
        metadata = self._get_tooltip_metadata(info, None)

        self.insert_thumbnail(thmb_image, thumbkey, chname,
                              thumbpath, metadata, info)

    def get_thumbpath(self, path, makedir=True):
        if path is None:
            return None

        path = os.path.abspath(path)
        dirpath, filename = os.path.split(path)
        # Get thumb directory
        cache_location = self.settings.get('cache_location', 'local')
        if cache_location == 'ginga':
            # thumbs in .ginga cache
            prefs = self.fv.get_preferences()
            thumbDir = os.path.join(prefs.get_baseFolder(), 'thumbs')
            thumbdir = os.path.join(thumbDir, iohelper.gethex(dirpath))
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

    def get_visible_thumbs(self):
        x1, y1, x2, y2 = self.c_view.get_datarect()
        self.logger.debug("datarect=(%f, %f, %f, %f)", x1, y1, x2, y2)

        # TODO: should really be text ht
        text_ht = self.thumb_vsep

        # calc in data coords
        thumb_height = self.thumb_width
        twd_vplus = thumb_height + text_ht + self.thumb_vsep
        row1 = int(math.floor(abs(y1) / twd_vplus) - 2)
        row2 = int(math.ceil(abs(y2) / twd_vplus) + 2)
        self.logger.debug("row1, row2 = %d, %d" % (row1, row2))
        i = max(0, row1 * self.thumb_num_cols)
        j = min(len(self.thumb_list) - 1, row2 * self.thumb_num_cols)
        self.logger.debug("i, j = %d, %d" % (i, j))
        thumbs = [self.thumb_list[n] for n in range(i, j + 1)]
        return thumbs

    def add_visible_thumbs(self):
        canvas = self.c_view.get_canvas()

        with self.thmblock:
            thumb_keys = set(self.get_visible_thumbs())
            old_thumb_keys = set(self._displayed_thumb_dict.keys())
            if old_thumb_keys == thumb_keys:
                # no need to do anything
                return

            to_delete = old_thumb_keys - thumb_keys
            to_add = thumb_keys - old_thumb_keys

            # make a copy of these for potential building thumbs
            self._to_build = set(thumb_keys)

            # delete thumbs from canvas that are no longer visible
            for thumbkey in to_delete:
                bnch = self._displayed_thumb_dict[thumbkey]
                canvas.delete_object(bnch.widget, redraw=False)

            # update displayed thumbs dict
            self._displayed_thumb_dict = {thumbkey: self.thumb_dict[thumbkey]
                                          for thumbkey in thumb_keys}

            # add newly-visible thumbs to canvas
            for thumbkey in to_add:
                bnch = self.thumb_dict[thumbkey]
                canvas.add(bnch.widget, redraw=False)

            self.c_view.redraw(whence=0)

        self.fv.update_pending()
        if self.autoload_visible:
            # load and create thumbnails for any placeholder icons
            self.timer_autoload.set(self.autoload_interval)

    def thumbs_pan_cb(self, viewer, pan_vec):
        self.fv.gui_do_oneshot('thumbs_pan', self.add_visible_thumbs)

    def insert_thumbnail(self, thumb_img, thumbkey, chname,
                         thumbpath, metadata, info):

        thumbname = info.name
        self.logger.debug("inserting thumb %s" % (thumbname))
        # make a context menu
        menu = self._mk_context_menu(thumbkey, chname, info)  # noqa

        # Get any previously stored thumb information in the image info
        thumb_extra = info.setdefault('thumb_extras', Bunch.Bunch())

        # If there is no previously made tooltip, then generate one
        if 'tooltip' in thumb_extra:
            text = thumb_extra.tooltip
        else:
            text = self._mk_tooltip_text(metadata)
            thumb_extra.tooltip = text

        canvas = self.c_view.get_canvas()
        fg = self.settings.get('label_font_color', 'black')
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

        with self.thmblock:
            row, col = self.thumb_row_count, self.thumb_col_count
            self.thumb_col_count = (self.thumb_col_count + 1) % self.thumb_num_cols
            if self.thumb_col_count == 0:
                self.thumb_row_count += 1

            xt, yt, xi, yi = self._calc_thumb_pos(row, col)
            l2 = []
            namelbl = canvas.dc.Text(xt, yt, thumbname, color=fg,
                                     fontsize=fontsize, coord='data')
            l2.append(namelbl)

            image = canvas.dc.Image(xi, yi, thumb_img, alpha=1.0,
                                    linewidth=1, color='black', coord='data')
            l2.append(image)

            obj = canvas.dc.CompoundObject(*l2, coord='data')
            obj.pickable = True
            obj.opaque = True
            obj.set_data(row=row, col=col)

            bnch = Bunch.Bunch(widget=obj, image=image, info=info,
                               namelbl=namelbl,
                               chname=chname,
                               thumbpath=thumbpath)

            self.thumb_dict[thumbkey] = bnch
            if thumbkey not in self.thumb_list:
                self.thumb_list.append(thumbkey)

            # set the load callback
            obj.add_callback('pick-down',
                             lambda *args: self.load_file(thumbkey, chname,
                                                          info))
            # set callbacks for tool tips
            obj.add_callback('pick-enter', self.show_tt,
                             thumbkey, chname, info, True)
            obj.add_callback('pick-leave', self.show_tt,
                             thumbkey, chname, info, False)

            # thumb will be added to canvas later in reorder_thumbs()

            sort_order = self.settings.get('sort_order', None)
            if sort_order:
                self.thumb_list.sort()
            self.logger.debug("added thumb for %s" % (info.name))

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs,
                               new_thumbkey=thumbkey)

    def auto_scroll(self, thumbkey):
        """Scroll the window to the thumb."""
        if not self.gui_up:
            return
        # force scroll to bottom of thumbs, if checkbox is set
        scrollp = self.w.auto_scroll.get_state()
        if not scrollp:
            return

        bnch = self.thumb_dict[thumbkey]

        # override X parameter because we only want to scroll vertically
        pan_x, pan_y = self.c_view.get_pan()
        self.c_view.panset_xy(pan_x, bnch.image.y)

    def clear_widget(self):
        """
        Clears the thumbnail display widget of all thumbnails, but does
        not remove them from the thumb_dict or thumb_list.
        """
        canvas = self.c_view.get_canvas()
        canvas.delete_all_objects()
        self.c_view.redraw(whence=0)

    def reorder_thumbs(self, new_thumbkey=None):
        self.logger.debug("Reordering thumb grid")
        xi, yi = None, None
        with self.thmblock:

            # Add thumbs back in by rows
            self.thumb_col_count = 0
            self.thumb_row_count = 0
            for thumbkey in self.thumb_list:
                bnch = self.thumb_dict[thumbkey]

                row, col = self.thumb_row_count, self.thumb_col_count
                self.thumb_col_count = ((self.thumb_col_count + 1) %
                                        self.thumb_num_cols)
                if self.thumb_col_count == 0:
                    self.thumb_row_count += 1

                xt, yt, xi, yi = self._calc_thumb_pos(row, col)
                bnch.namelbl.x, bnch.namelbl.y = xt, yt
                bnch.image.x, bnch.image.y = xi, yi
                bnch.widget.set_data(row=row, col=col)

        if xi is not None:
            xi += self.thumb_width * 2
            xm, ym, x_, y_ = self._calc_thumb_pos(0, 0)
            self.c_view.set_limits([(xm, ym), (xi, yi)], coord='data')

        if new_thumbkey is not None:
            self.auto_scroll(new_thumbkey)

        self.add_visible_thumbs()
        self.logger.debug("Reordering done")

    def _mk_tooltip_text(self, metadata):
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

    def _mk_context_menu(self, thumbkey, chname, info):
        """NOTE: currently not used, but left here to be reincorporated
        at some point.
        """
        menu = Widgets.Menu()
        item = menu.add_name("Display")
        item.add_callback('activated',
                          lambda w: self.load_file(
                              thumbkey, chname, info.name, info.path,
                              info.image_future))
        menu.add_separator()
        item = menu.add_name("Remove")
        item.add_callback('activated',
                          lambda w: self.fv.remove_image_by_name(
                              chname, info.name, impath=info.path))

        return menu

    def update_thumbnail(self, thumbkey, thmb_image, metadata):
        with self.thmblock:
            try:
                bnch = self.thumb_dict[thumbkey]
            except KeyError:
                self.logger.debug("No thumb found for %s; not updating "
                                  "thumbs" % (str(thumbkey)))
                return

            info = bnch.info
            # Get any previously stored thumb information in the image info
            thumb_extra = info.setdefault('thumb_extras', Bunch.Bunch())

            # Update the tooltip, in case of new or changed metadata
            text = self._mk_tooltip_text(metadata)
            thumb_extra.tooltip = text

            self.logger.debug("updating thumbnail '%s'" % (info.name))
            # TODO: figure out why set_image() causes corruption of the
            # redraw here.  Instead we force a manual redraw.
            #bnch.image.set_image(thmb_image)
            bnch.image.image = thmb_image
            thumb_extra.rgbimg = thmb_image

            self.c_view.redraw(whence=0)
            self.logger.debug("update finished.")

    def __str__(self):
        return 'thumbs'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Thumbs', package='ginga')

# END
