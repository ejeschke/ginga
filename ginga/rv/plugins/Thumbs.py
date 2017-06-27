#
# Thumbs.py -- Thumbs plugin for Ginga image viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import threading

from ginga import GingaPlugin
from ginga import RGBImage
from ginga.misc import Bunch
from ginga.util import iohelper
from ginga.gw import Widgets, Viewers
from ginga.util.paths import icondir
from ginga import cmap, RGBImage
from ginga.pilw.ImageViewPil import CanvasView

class Thumbs(GingaPlugin.GlobalPlugin):
    """
    Thumbs
    ======
    The Thumbs plugin provides a thumbnail index of all images viewed since
    the program was started.  By default, Thumbs appear in cronological viewing
    history, with the newest images at the bottom and the oldest at the top.
    The sorting can be made alphanumeric by a setting in the "plugin_Thumbs.cfg"
    configuration file.

    Plugin Type: Global
    -------------------
    Thumbs is a global plugin.  Only one instance can be opened.

    Usage
    -----
    Clicking on a thumbnail navigates you directly to that image in the
    associated channel.  Hovering the cursor over a thumbnail will show a
    tool tip that contains a couple of useful pieces of metadata from the
    image.  Right-clicking on a thumbnail brings up a context menu with
    options for displaying or removing an image.

    The "Auto Scroll" checkbox, if checked, will cause the Thumbs pan to
    scroll to the active image.
    """
    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        # For thumbnail pane
        self.thumb_dict = {}
        self.thumb_list = []
        self.thumb_num_cols = 1
        self.thumb_row_count = 0
        self.thumb_col_count = 0
        # distance in pixels between thumbs
        self.thumb_sep = 15
        self._wd = 300
        self._ht = 400
        self._cmyoff = 10
        self._max_y = 0
        tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Thumbs')
        self.settings.add_defaults(cache_thumbs=False,
                                   cache_location='local',
                                   auto_scroll=True,
                                   rebuild_wait=4.0,
                                   tt_keywords=tt_keywords,
                                   mouseover_name_key='NAME',
                                   thumb_length=192,
                                   sort_order=None,
                                   label_length=14,
                                   label_cutoff='right',
                                   highlight_tracks_keyboard_focus=True,
                                   label_font_color='white',
                                   label_font_size=10,
                                   label_bg_color='lightgreen')
        self.settings.load(onError='silent')
        # max length of thumb on the long side
        self.thumb_width = self.settings.get('thumb_length', 192)

        tg = CanvasView(logger=self.logger)
        tg.configure_surface(self.thumb_width, self.thumb_width)
        tg.enable_autozoom('on')
        tg.set_autocut_params('zscale')
        tg.enable_autocuts('override')
        tg.enable_auto_orient(True)
        tg.defer_redraw = False
        tg.set_bg(0.7, 0.7, 0.7)
        self.thumb_generator = tg

        self.thmbtask = fv.get_timer()
        self.thmbtask.set_callback('expired', self.redo_delay_timer)
        self.lagtime = self.settings.get('rebuild_wait', 4.0)
        self.thmblock = threading.RLock()

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
        # the RGB image, and to let the user pick the cmap
        self.c_view = Viewers.CanvasView(logger=self.logger)
        c_v = self.c_view
        c_v.set_desired_size(self._wd, self._ht)
        c_v.enable_autozoom('off')
        c_v.enable_autocuts('off')
        c_v.set_pan(0, 0)
        c_v.zoom_to(1)
        c_v.transform(False, True, False)
        c_v.cut_levels(0, 255)
        c_v.set_bg(0.4, 0.4, 0.4)
        # for debugging
        c_v.set_name('cmimage')
        c_v.add_callback('configure', self.thumbpane_resized_cb)
        c_v.add_callback('drag-drop', self.drag_drop_cb)

        canvas = c_v.get_canvas()
        canvas.register_for_cursor_drawing(c_v)
        c_v.add_callback('scroll', self.scroll_cb)
        canvas.set_draw_mode('pick')
        canvas.ui_set_active(True)

        bd = c_v.get_bindings()
        bd.enable_pan(True)
        # disable zooming so scrolling can be used to pan up/down
        bd.enable_zoom(False)
        bd.enable_cmap(False)

        iw = Viewers.GingaScrolledViewerWidget(c_v)
        iw.resize(self._wd, self._ht)

        vbox.add_widget(iw, stretch=1)

        captions = (('Auto scroll', 'checkbutton', 'Clear', 'button'),)
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.auto_scroll.set_tooltip(
            "Scroll the thumbs window when new images arrive")
        b.clear.set_tooltip("Remove all current thumbnails")
        b.clear.add_callback('activated', lambda w: self.clear())
        auto_scroll = self.settings.get('auto_scroll', True)
        b.auto_scroll.set_state(auto_scroll)
        vbox.add_widget(w, stretch=0)

        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def scroll_cb(self, viewer, direction, amt, data_x, data_y):
        """Called when the user scrolls in the thumb pane.
        Pan up or down to show additional thumbs.
        """
        bd = viewer.get_bindings()
        direction = bd.get_direction(direction)
        pan_x, pan_y = viewer.get_pan()[:2]
        qty = self.thumb_sep * amt * self.settings.get('thumb_pan_accel', 1.0)
        if direction == 'up':
            pan_y -= qty
        else:
            pan_y += qty

        limits = viewer.get_limits(coord='data')
        pan_y = min(max(pan_y, limits[0][1]), limits[1][1])

        viewer.set_pan(pan_x, pan_y)

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

    def add_image_cb(self, viewer, chname, image, image_info):
        if not self.gui_up:
            return False

        channel = self.fv.get_channel(chname)
        self.redo_delay(channel.fitsimage)

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

        # Is there a cached thumbnail image on disk we can use?
        thmb_image = RGBImage.RGBImage()
        loaded = False
        if (thumbpath is not None) and os.path.exists(thumbpath):
            #save_thumb = False
            try:
                # try to load the thumbnail image
                thmb_image.load_file(thumbpath)
                # make sure name is consistent
                thmb_image.set(name=info.name)
                loaded = True

            except Exception as e:
                self.logger.warning("Error loading thumbnail: %s" % (str(e)))

        if not loaded:
            # no luck loading thumbnail, try to load a cached image
            try:
                thmb_image = channel.get_loaded_image(info.name)

            except KeyError:
                self.logger.info("image not in memory; using placeholder")

                # load a plcaeholder image
                tmp_path = os.path.join(icondir, 'fits.png')
                thmb_image = RGBImage.RGBImage()
                thmb_image.load_file(tmp_path)
                # make sure name is consistent
                thmb_image.set(name=info.name, path=None)

        self.fv.gui_do(self._make_thumb, chname, thmb_image, info.name,
                       info.path, thumbkey, info, save_thumb=save_thumb,
                       thumbpath=thumbpath)


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
            # Is this thumbnail already in the list?
            thumbkey = self.get_thumb_key(chname, imname, impath)
            self.remove_thumb(thumbkey)
        except Exception as e:
            self.logger.error("Error removing thumb for %s: %s" % (
                imname, str(e)))

    def remove_thumb(self, thumbkey):
        with self.thmblock:
            if thumbkey not in self.thumb_dict:
                return
            del self.thumb_dict[thumbkey]
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
                    self.thumb_list.remove(thumbkey)
                    del self.thumb_dict[thumbkey]
                    self._tkf_highlight.discard(thumbkey)

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)

    def thumbpane_resized_cb(self, thumbvw, width, height):
        self.fv.gui_do_oneshot('thumbs-resized', self._resized, width, height)

    def _resized(self, width, height):
        self.logger.debug("thumbs resized, width=%d" % (width))

        with self.thmblock:
            cols = max(1, width // (self.thumb_width + self.thumb_sep))
            if self.thumb_num_cols == cols:
                # If we have not actually changed the possible number of columns
                # then don't do anything
                return False
            self.logger.info("column count is now %d" % (cols))
            self.thumb_num_cols = cols

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)
        return False

    def load_file(self, thumbkey, chname, name, path, image_future):
        self.logger.debug("loading image: %s" % (str(thumbkey)))
        self.fv.switch_name(chname, name, path=path,
                            image_future=image_future)

    def clear(self):
        with self.thmblock:
            self.thumb_list = []
            self.thumb_dict = {}
            self._tkf_highlight = set([])

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

    def copy_attrs(self, fitsimage):
        # Reflect transforms, colormap, etc.
        fitsimage.copy_attributes(self.thumb_generator,
                                  ['transforms', 'cutlevels',
                                   'rgbmap'])

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

        self.c_view.redraw(whence=0)

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

    def redo_thumbnail(self, fitsimage, save_thumb=None):
        self.logger.debug("redoing thumbnail...")
        # Get the thumbnail image
        image = fitsimage.get_image()
        if image is None:
            return

        # image is flagged not to make a thumbnail?
        nothumb = image.get('nothumb', False)
        if nothumb:
            return

        if save_thumb is None:
            save_thumb = self.settings.get('cache_thumbs', False)

        chname = self.fv.get_channel_name(fitsimage)

        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

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
        metadata[self.settings.get('mouseover_name_key', 'NAME')] = name

        thumbkey = self.get_thumb_key(chname, name, path)
        with self.thmblock:
            if thumbkey not in self.thumb_dict:
                # No memory of this thumbnail, so regenerate it
                self._add_image(self.fv, chname, image)
                return

            # Generate new thumbnail
            self.logger.debug("generating new thumbnail")
            fitsimage.copy_attributes(self.thumb_generator,
                                      ['transforms', 'cutlevels',
                                       'rgbmap'])

            thumb_np = image.get_thumbnail(self.thumb_width)
            self.thumb_generator.set_data(thumb_np)

            # Save a thumbnail for future browsing
            if save_thumb and path is not None:
                thumbpath = self.get_thumbpath(path)
                if thumbpath is not None:
                    if os.path.exists(thumbpath):
                        os.remove(thumbpath)
                    ## self.thumb_generator.save_plain_image_as_file(thumbpath,
                    ##                                               format='jpeg')

            rgb_img = self.thumb_generator.get_image_as_array()
            imgwin = RGBImage.RGBImage(rgb_img)

        self.update_thumbnail(thumbkey, imgwin, name, metadata)

    def delete_channel_cb(self, viewer, channel):
        """Called when a channel is deleted from the main interface.
        Parameter is channel (a bunch)."""
        chname_del = channel.name
        # TODO: delete thumbs for this channel!
        self.logger.info("deleting thumbs for channel '%s'" % (chname_del))
        with self.thmblock:
            newThumbList = []
            un_hilite_set = set([])
            for thumbkey in self.thumb_list:
                chname = thumbkey[0]
                if chname != chname_del:
                    newThumbList.append(thumbkey)
                else:
                    del self.thumb_dict[thumbkey]
                    un_hilite_set.add(thumbkey)
            self.thumb_list = newThumbList
            self._tkf_highlight -= un_hilite_set  # Unhighlight

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)

    def make_tt(self, viewer, canvas, text, pt, fontsize=10):
        Text = canvas.get_draw_class('text')
        Rectangle = canvas.get_draw_class('rectangle')
        Point = canvas.get_draw_class('point')

        x, y = pt
        # override x coord so that tooltip can be sure to be somewhat
        # visible on the canvas
        tup = viewer.get_pan_rect()
        x = tup[0][0] + 10
        mxwd = 0
        lines = text.split('\n')

        point = Point(x, y, radius=0, color='black', alpha=0.0)
        rect = Rectangle(x, y, x, y, color='black', fill=True,
                         fillcolor='lightyellow')
        crdmap = viewer.get_coordmap('offset')
        crdmap.refobj = point

        l = [point, rect]
        a, b = 2, 0
        for line in lines:
            text = Text(a, b, text=line, color='black', fontsize=fontsize)
            text.crdmap = crdmap
            l.append(text)
            txt_wd, txt_ht = viewer.renderer.get_dimensions(text)
            b += txt_ht + 2
            text.y = b
            mxwd = max(mxwd, txt_wd)
        rect.x2 = rect.x1 + mxwd + 2
        rect.y2 = rect.y1 + b + 4

        Compound = canvas.get_draw_class('compoundobject')
        obj = Compound(*l)
        return obj

    def show_tt(self, obj, canvas, event, pt,
                thumbkey, chname, name, image_info, tf):

        text = image_info.thumb_extras.tooltip

        tag = '_$tooltip'
        try:
            canvas.delete_object_by_tag(tag)
        except KeyError:
            pass
        if tf:
            tt = self.make_tt(self.c_view, canvas, text, pt)
            canvas.add(tt, tag=tag)

    def _make_thumb(self, chname, image, name, path, thumbkey,
                    image_info, save_thumb=False, thumbpath=None):
        # This is called by the make_thumbs() as a gui thread
        with self.thmblock:
            thumb_np = image.get_thumbnail(self.thumb_width)
            self.thumb_generator.set_data(thumb_np)

            # Save a thumbnail for future browsing
            if save_thumb and (thumbpath is not None):
                ## self.thumb_generator.save_plain_image_as_file(thumbpath,
                ##                                               format='jpeg')
                pass

            rgb_img = self.thumb_generator.get_image_as_array()
            imgwin = RGBImage.RGBImage(rgb_img)

        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        thumbname = name
        self.insert_thumbnail(imgwin, thumbkey, thumbname,
                              chname, name, path, thumbpath, metadata,
                              image_info)

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
        # TODO: should really be text ht
        text_ht = self.thumb_sep

        # calc in window coords
        twd_plus = self.thumb_width + text_ht + self.thumb_sep
        xt = self.thumb_sep + col * twd_plus
        yt = self._cmyoff + (row * twd_plus) + text_ht

        # convert to data coords
        crdmap = self.c_view.get_coordmap('window')
        xt, yt = crdmap.to_data((xt, yt))

        xi = xt
        yi = yt
        return (xt, yt, xi, yi)

    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path,
                         thumbpath, metadata, image_info):

        self.logger.debug("inserting thumb %s" % (thumbname))
        # make a context menu
        image_future = image_info.image_future
        menu = self._mk_context_menu(thumbkey, chname, name, path,
                                     image_future)

        # Get any previously stored thumb information in the image info
        thumb_extra = image_info.setdefault('thumb_extras', Bunch.Bunch())

        # If there is no previously made tooltip, then generate one
        if 'tooltip' in thumb_extra:
            text = thumb_extra.tooltip
        else:
            text = self.query_thumb(thumbkey, name, metadata)
            thumb_extra.tooltip = text

        canvas = self.c_view.get_canvas()
        Image = canvas.get_draw_class('image')
        Text = canvas.get_draw_class('text')
        Compound = canvas.get_draw_class('compoundobject')
        fg = self.settings.get('label_font_color', 'black')
        fontsize = self.settings.get('label_font_size', 10)

        # Shorten thumbnail label, if requested
        label_length = self.settings.get('label_length', None)
        label_cutoff = self.settings.get('label_cutoff', 'right')

        if label_length is not None:
            ## thumbname = iohelper.shorten_name(thumbname, label_length,
            ##                                   side=label_cutoff)
            # TEMP
            thumbname = thumbname[:label_length]

        with self.thmblock:
            row, col = self.thumb_row_count, self.thumb_col_count
            self.thumb_col_count = (self.thumb_col_count + 1) % self.thumb_num_cols
            if self.thumb_col_count == 0:
                self.thumb_row_count += 1

            xt, yt, xi, yi = self._calc_thumb_pos(row, col)
            l2 = []
            namelbl = Text(xt, yt, thumbname, color=fg, fontsize=fontsize,
                           coord='data')
            l2.append(namelbl)

            image = Image(xi, yi, imgwin, alpha=1.0,
                          linewidth=1, color='black', coord='data')
            l2.append(image)

            obj = Compound(*l2, coord='data')
            obj.pickable = True
            obj.opaque = True

            bnch = Bunch.Bunch(widget=obj, image=image, info=image_info,
                               name=name, imname=name, namelbl=namelbl,
                               chname=chname, path=path, thumbpath=thumbpath,
                               image_future=image_future)

            self.thumb_dict[thumbkey] = bnch
            self.thumb_list.append(thumbkey)

            # set the load callback
            obj.add_callback('pick-down',
                             lambda *args: self.load_file(thumbkey, chname,
                                                          name,
                                                          path, image_future))
            # set callbacks for tool tips
            obj.add_callback('pick-enter', self.show_tt,
                             thumbkey, chname, name, image_info, True)
            obj.add_callback('pick-leave', self.show_tt,
                             thumbkey, chname, name, image_info, False)

            # add thumb to canvas
            canvas.add(obj)

        #self.c_view.redraw(whence=0)

        sort_order = self.settings.get('sort_order', None)
        if sort_order:
            self.thumb_list.sort()

        self.fv.gui_do_oneshot('thumbs-reorder', self.reorder_thumbs)

        self.logger.debug("added thumb for %s" % (name))

    def _auto_scroll(self, xi, yi):
        # force scroll to bottom of thumbs, if checkbox is set
        scrollp = self.w.auto_scroll.get_state()
        if scrollp:
            # override X parameter because we only want to scroll vertically
            pan_x, pan_y = self.c_view.get_pan()
            self.c_view.panset_xy(pan_x, yi)

    def clear_widget(self):
        """
        Clears the thumbnail display widget of all thumbnails, but does
        not remove them from the thumb_dict or thumb_list.
        """
        canvas = self.c_view.get_canvas()
        canvas.delete_all_objects()
        self.c_view.redraw(whence=0)

    def reorder_thumbs(self):
        self.logger.debug("Reordering thumb grid")
        canvas = self.c_view.get_canvas()

        xi, yi = None, None
        with self.thmblock:
            self.clear_widget()

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

                canvas.add(bnch.widget, redraw=False)

        self.c_view.redraw(whence=0)

        if xi is not None:
            xi += self.thumb_width
            xm, ym, x_, y_ = self._calc_thumb_pos(0, 0)
            self.c_view.set_limits([(xm, ym), (xi, yi)], coord='data')
            self._auto_scroll(xi, yi)

        self.logger.debug("Reordering done")

    def query_thumb(self, thumbkey, name, metadata):
        result = []
        for kwd in self.keywords:
            try:
                text = kwd + ': ' + str(metadata[kwd])
            except Exception as e:
                self.logger.warning("Couldn't determine %s name: %s" % (
                    kwd, str(e)))
                text = "%s: N/A" % (kwd)
            result.append(text)

        return '\n'.join(result)

    def _mk_context_menu(self, thumbkey, chname, name, path, image_future):
        menu = Widgets.Menu()
        item = menu.add_name("Display")
        item.add_callback('activated',
                          lambda w: self.load_file(
                              thumbkey, chname, name, path, image_future))
        menu.add_separator()
        item = menu.add_name("Remove")
        item.add_callback('activated',
                          lambda w: self.fv.remove_image_by_name(
                              chname, name, impath=path))

        return menu

    def update_thumbnail(self, thumbkey, imgwin, name, metadata):
        with self.thmblock:
            try:
                bnch = self.thumb_dict[thumbkey]
            except KeyError:
                self.logger.debug("No thumb found for %s; not updating "
                                  "thumbs" % (str(thumbkey)))
                return

            image_info = bnch.info
            # Get any previously stored thumb information in the image info
            thumb_extra = image_info.setdefault('thumb_extras', Bunch.Bunch())

            # Update the tooltip, in case of new or changed metadata
            text = self.query_thumb(thumbkey, name, metadata)
            thumb_extra.tooltip = text

            self.logger.info("updating thumbnail '%s'" % (name))
            bnch.image.set_image(imgwin)
            self.logger.debug("update finished.")

        self.c_view.redraw(whence=0)

    def __str__(self):
        return 'thumbs'

#END
