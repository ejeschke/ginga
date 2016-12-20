#
# Thumbs.py -- Thumbs plugin for Ginga image viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import threading

from ginga import GingaPlugin
from ginga.misc import Bunch
from ginga.util import iohelper
from ginga.gw import Widgets, Viewers


class Thumbs(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        # For thumbnail pane
        self.thumbDict = {}
        self.thumbList = []
        self.thumbRowList = []
        self.thumbNumRows = 20
        self.thumbNumCols = 1
        self.thumbRowCount = 0
        self.thumbColCount = 0
        # distance in pixels between thumbs
        self.thumbSep = 15
        tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Thumbs')
        self.settings.addDefaults(cache_thumbs=False,
                                  cache_location='local',
                                  auto_scroll=True,
                                  rebuild_wait=4.0,
                                  tt_keywords=tt_keywords,
                                  mouseover_name_key='NAME',
                                  thumb_length=192,
                                  sort_order=None,
                                  label_length=25,
                                  label_cutoff='right',
                                  highlight_tracks_keyboard_focus=True,
                                  label_font_color='black',
                                  label_bg_color='lightgreen')
        self.settings.load(onError='silent')
        # max length of thumb on the long side
        self.thumbWidth = self.settings.get('thumb_length', 150)

        self.thmbtask = fv.get_timer()
        self.thmbtask.set_callback('expired', self.redo_delay_timer)
        self.lagtime = self.settings.get('rebuild_wait', 4.0)
        self.thmblock = threading.RLock()

        # TODO: these maybe should be configurable by channel
        # different instruments have different keywords of interest
        self.keywords = self.settings.get('tt_keywords', tt_keywords)
        self.keywords.insert(0, self.settings.get('mouseover_name_key', 'NAME'))

        self.highlight_tracks_keyboard_focus = self.settings.get(
            'highlight_tracks_keyboard_focus', True)
        self._tkf_highlight = set([])

        fv.set_callback('add-image', self.add_image_cb)
        fv.set_callback('add-image-info', self.add_image_info_cb)
        fv.set_callback('remove-image', self.remove_image_cb)
        fv.set_callback('add-channel', self.add_channel_cb)
        fv.set_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('channel-change', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):
        # width, height = 300, 300
        # cm, im = self.fv.cm, self.fv.im

        thumb_len = self.settings.get('thumb_length', 192)

        tg = Viewers.ImageViewCanvas(logger=self.logger)
        tg.configure_window(thumb_len, thumb_len)
        tg.enable_autozoom('on')
        tg.set_autocut_params('zscale')
        tg.enable_autocuts('override')
        tg.enable_auto_orient(True)
        tg.defer_redraw = False
        tg.set_bg(0.7, 0.7, 0.7)
        self.thumb_generator = tg

        sw = Widgets.ScrollArea()
        sw.add_callback('configure', self.thumbpane_resized_cb)

        # Create thumbnails pane
        vbox = Widgets.GridBox()
        vbox.set_margins(4, 4, 4, 4)
        vbox.set_column_spacing(14)
        self.w.thumbs = vbox

        sw.set_widget(vbox)
        self.w.thumbs_scroll = sw

        container.add_widget(sw, stretch=1)

        captions = (('Auto scroll', 'checkbutton', 'Clear', 'button'),)
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.auto_scroll.set_tooltip(
            "Scroll the thumbs window when new images arrive")
        b.clear.set_tooltip("Remove all current thumbnails")
        b.clear.add_callback('activated', lambda w: self.clear())
        auto_scroll = self.settings.get('auto_scroll', True)
        b.auto_scroll.set_state(auto_scroll)
        container.add_widget(w, stretch=0)

        self.gui_up = True

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

        # image is flagged not to make a thumbnail?
        nothumb = image.get('nothumb', False)
        if nothumb:
            return

        # idx = image.get('idx', None)
        # get image path
        path = image_info.path

        if path is not None:
            path = os.path.abspath(path)
        name = image_info.name

        thumbname = name
        self.logger.info("making thumb for %s" % (thumbname))

        future = image_info.image_future

        # Is there a preference set to avoid making thumbnails?
        chinfo = self.fv.get_channel(chname)
        prefs = chinfo.settings
        if not prefs.get('genthumb', False):
            return

        # Is this thumbnail already in the list?
        # NOTE: does not handle two separate images with the same path
        # in the same channel
        thumbkey = self.get_thumb_key(chname, name, path)
        with self.thmblock:
            if thumbkey in self.thumbDict:
                return

        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')
        metadata[self.settings.get('mouseover_name_key', 'NAME')] = name

        thumbpath = self.get_thumbpath(path)

        with self.thmblock:
            self.copy_attrs(chinfo.fitsimage)
            thumb_np = image.get_thumbnail(self.thumbWidth)
            self.thumb_generator.set_data(thumb_np)
            imgwin = self.thumb_generator.get_plain_image_as_widget()

        label_length = self.settings.get('label_length', None)
        label_cutoff = self.settings.get('label_cutoff', 'right')

        # Shorten thumbnail label, if requested
        if label_length is not None:
            thumbname = iohelper.shorten_name(thumbname, label_length,
                                              side=label_cutoff)

        self.insert_thumbnail(imgwin, thumbkey, thumbname, chname, name, path,
                              thumbpath, metadata, future)

    def _add_image(self, viewer, chname, image):
        chinfo = self.fv.get_channel(chname)
        try:
            info = chinfo.get_image_info(image.name)
        except KeyError:
            return

        self.add_image_cb(viewer, chname, image, info)

    def remove_image_cb(self, viewer, chname, name, path):
        if not self.gui_up:
            return

        self.logger.info("removing thumb for %s" % (name))

        try:
            # Is this thumbnail already in the list?
            thumbkey = self.get_thumb_key(chname, name, path)
            self.remove_thumb(thumbkey)
        except Exception as e:
            self.logger.error("Error removing thumb for %s: %s" % (
                name, str(e)))

    def remove_thumb(self, thumbkey):
        with self.thmblock:
            if thumbkey not in self.thumbDict:
                return
            self.clear_widget()
            del self.thumbDict[thumbkey]
            self.thumbList.remove(thumbkey)

            # Unhighlight
            chname = thumbkey[0]
            channel = self.fv.get_channel(chname)
            self._tkf_highlight.discard(thumbkey)
            channel.extdata.thumbs_old_highlight.discard(thumbkey)

        self.reorder_thumbs()

    def update_thumbs(self, nameList):

        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumbList) - set(nameList)
        if len(invalid) > 0:
            with self.thmblock:
                for thumbkey in invalid:
                    self.thumbList.remove(thumbkey)
                    del self.thumbDict[thumbkey]
                    self._tkf_highlight.discard(thumbkey)

            self.reorder_thumbs()

    def thumbpane_resized_cb(self, widget, width, height):
        self.logger.info("reordering thumbs width=%d" % (width))

        with self.thmblock:
            cols = max(1, width // (self.thumbWidth + self.thumbSep))
            if self.thumbNumCols == cols:
                # If we have not actually changed the possible number of columns
                # then don't do anything
                return False
            self.logger.info("column count is now %d" % (cols))
            self.thumbNumCols = cols

        self.reorder_thumbs()
        return False

    def load_file(self, thumbkey, chname, name, path, image_future):
        self.logger.debug("loading image: %s" % (str(thumbkey)))
        self.fv.switch_name(chname, name, path=path,
                            image_future=image_future)

    def clear(self):
        with self.thmblock:
            self.clear_widget()
            self.thumbList = []
            self.thumbDict = {}
            self._tkf_highlight = set([])
        self.reorder_thumbs()

    def add_channel_cb(self, viewer, chinfo):
        """Called when a channel is added from the main interface.
        Parameter is chinfo (a bunch)."""
        fitsimage = chinfo.fitsimage
        fitssettings = fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.getSetting(name).add_callback(
                'set', self.cutset_cb, fitsimage)
        fitsimage.add_callback('transform', self.transform_cb)

        rgbmap = fitsimage.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, fitsimage)

        # add old highlight set to channel external data
        chinfo.extdata.setdefault('thumbs_old_highlight', set([]))

    def focus_cb(self, viewer, channel):
        # Reflect transforms, colormap, etc.
        fitsimage = channel.fitsimage
        image = channel.get_current_image()
        if image is not None:
            chname = channel.name
            thumbkey = self._get_thumb_key(chname, image)
            new_highlight = set([thumbkey])

            # TODO: already calculated thumbkey, use simpler test
            if not self.have_thumbnail(fitsimage, image):
                # No memory of this thumbnail, so regenerate it
                self._add_image(viewer, chname, image)
                return

            # Else schedule an update of the thumbnail for changes to
            # cut levels, etc.
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

            # unhighlight thumb labels that should NOT be highlighted any more
            for thumbkey in un_hilite_set:
                if thumbkey in self.thumbDict:
                    namelbl = self.thumbDict[thumbkey].get('namelbl')
                    namelbl.set_color(bg=None, fg=None)

            # highlight new labels that should be
            bg = self.settings.get('label_bg_color', 'lightgreen')
            fg = self.settings.get('label_font_color', 'black')

            for thumbkey in re_hilite_set:
                if thumbkey in self.thumbDict:
                    namelbl = self.thumbDict[thumbkey].get('namelbl')
                    namelbl.set_color(bg=bg, fg=fg)

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
            return thumbkey in self.thumbDict

    def redo_thumbnail(self, fitsimage, save_thumb=None):
        self.logger.debug("redoing thumbnail...")
        # Get the thumbnail image
        image = fitsimage.get_image()
        if image is None:
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
            if thumbkey not in self.thumbDict:
                # No memory of this thumbnail, so regenerate it
                self._add_image(self.fv, chname, image)
                return

            # Generate new thumbnail
            fitsimage.copy_attributes(self.thumb_generator,
                                      ['transforms', 'cutlevels',
                                       'rgbmap'])
            thumb_np = image.get_thumbnail(self.thumbWidth)
            self.thumb_generator.set_data(thumb_np)

            # Save a thumbnail for future browsing
            if save_thumb:
                thumbpath = self.get_thumbpath(path)
                if thumbpath is not None:
                    if os.path.exists(thumbpath):
                        os.remove(thumbpath)
                    self.thumb_generator.save_plain_image_as_file(thumbpath,
                                                            format='jpeg')

            imgwin = self.thumb_generator.get_plain_image_as_widget()

        self.update_thumbnail(thumbkey, imgwin, name, metadata)

    def delete_channel_cb(self, viewer, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname_del = chinfo.name
        # TODO: delete thumbs for this channel!
        self.logger.info("deleting thumbs for channel '%s'" % (chname_del))
        with self.thmblock:
            self.clear_widget()
            newThumbList = []
            un_hilite_set = set([])
            for thumbkey in self.thumbList:
                chname = thumbkey[0]
                if chname != chname_del:
                    newThumbList.append(thumbkey)
                else:
                    del self.thumbDict[thumbkey]
                    un_hilite_set.add(thumbkey)
            self.thumbList = newThumbList
            self._tkf_highlight -= un_hilite_set  # Unhighlight

        self.reorder_thumbs()

    def _make_thumb(self, chname, image, name, path, thumbkey,
                    image_future, save_thumb=False, thumbpath=None):
        # This is called by the make_thumbs() as a gui thread
        with self.thmblock:
            thumb_np = image.get_thumbnail(self.thumbWidth)
            self.thumb_generator.set_data(thumb_np)

            # Save a thumbnail for future browsing
            if save_thumb and (thumbpath is not None):
                self.thumb_generator.save_plain_image_as_file(thumbpath,
                                                        format='jpeg')

            imgwin = self.thumb_generator.get_plain_image_as_widget()

        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        thumbname = name
        self.insert_thumbnail(imgwin, thumbkey, thumbname,
                              chname, name, path, thumbpath, metadata,
                              image_future)
        self.fv.update_pending(timeout=0.001)

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

    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path,
                         thumbpath, metadata, image_future):

        # make a context menu
        menu = self._mk_context_menu(thumbkey, chname, name, path, image_future)

        thumbw = Widgets.Image(native_image=imgwin, menu=menu,
                               style='clickable')
        thumbw.resize(self.thumbWidth, self.thumbWidth)

        # set the load callback
        thumbw.add_callback('activated',
                            lambda w: self.load_file(thumbkey, chname, name,
                                                     path, image_future))

        # make a tool tip
        text = self.query_thumb(thumbkey, name, metadata)
        thumbw.set_tooltip(text)

        vbox = Widgets.VBox()
        vbox.set_margins(0, 0, 0, 0)
        vbox.set_spacing(0)
        namelbl = Widgets.Label(text=thumbname, halign='left')
        vbox.add_widget(namelbl, stretch=0)
        vbox.add_widget(thumbw, stretch=0)
        # special hack for Qt widgets
        vbox.cfg_expand(0, 0)

        bnch = Bunch.Bunch(widget=vbox, image=thumbw,
                           name=name, imname=name, namelbl=namelbl,
                           chname=chname, path=path, thumbpath=thumbpath,
                           image_future=image_future)

        with self.thmblock:
            self.thumbDict[thumbkey] = bnch
            self.thumbList.append(thumbkey)

            sort_order = self.settings.get('sort_order', None)
            if sort_order:
                self.thumbList.sort()
                self.reorder_thumbs()
                return

            self.w.thumbs.add_widget(vbox,
                                     self.thumbRowCount, self.thumbColCount)
            self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols
            if self.thumbColCount == 0:
                self.thumbRowCount += 1

        self._auto_scroll()
        self.logger.debug("added thumb for %s" % (name))

    def _auto_scroll(self):
        # force scroll to bottom of thumbs, if checkbox is set
        scrollp = self.w.auto_scroll.get_state()
        if scrollp:
            self.fv.update_pending()
            self.w.thumbs_scroll.scroll_to_end()

    def clear_widget(self):
        """
        Clears the thumbnail display widget of all thumbnails, but does
        not remove them from the thumbDict or thumbList.
        """
        with self.thmblock:
            self.w.thumbs.remove_all()

    def reorder_thumbs(self):
        self.logger.debug("Reordering thumb grid")
        with self.thmblock:
            self.clear_widget()

            # Add thumbs back in by rows
            self.thumbColCount = 0
            self.thumbRowCount = 0
            for thumbkey in self.thumbList:
                bnch = self.thumbDict[thumbkey]
                self.w.thumbs.add_widget(bnch.widget,
                                         self.thumbRowCount, self.thumbColCount)
                self.thumbColCount = ((self.thumbColCount + 1) %
                                      self.thumbNumCols)
                if self.thumbColCount == 0:
                    self.thumbRowCount += 1

        self._auto_scroll()
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
                bnch = self.thumbDict[thumbkey]
            except KeyError:
                self.logger.debug("No thumb found for %s; not updating "
                                  "thumbs" % (str(thumbkey)))
                return

            self.logger.info("updating thumbnail '%s'" % (name))
            bnch.image._set_image(imgwin)
            self.logger.debug("update finished.")

    def add_image_info_cb(self, viewer, channel, info):

        save_thumb = self.settings.get('cache_thumbs', False)

        # Do we already have this thumb loaded?
        chname = channel.name
        thumbkey = self.get_thumb_key(chname, info.name, info.path)
        thumbpath = self.get_thumbpath(info.path)

        with self.thmblock:
            try:
                bnch = self.thumbDict[thumbkey]
                # if these are not equal then the mtime must have
                # changed on the file, better reload and regenerate
                if bnch.thumbpath == thumbpath:
                    return
            except KeyError:
                pass

        # Is there a cached thumbnail image on disk we can use?
        image = None
        if (thumbpath is not None) and os.path.exists(thumbpath):
            save_thumb = False
            try:
                # try to load the thumbnail image
                image = self.fv.load_image(thumbpath)
            except Exception as e:
                pass

        try:
            if image is None:
                if info.path is None:
                    # No way to generate a thumbnail for this image
                    return

                # no luck loading thumbnail, try to load the full image
                image = info.image_loader(info.path)

            # make sure name is consistent
            image.set(name=info.name)

            self.fv.gui_do(self._make_thumb, chname, image, info.name,
                           info.path, thumbkey, info.image_future,
                           save_thumb=save_thumb,
                           thumbpath=thumbpath)

        except Exception as e:
            self.logger.error("Error generating thumbnail for '%s': %s" % (
                info.path, str(e)))
            # TODO: generate "broken thumb"?

    def __str__(self):
        return 'thumbs'

#END
