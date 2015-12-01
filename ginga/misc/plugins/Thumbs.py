#
# Thumbs.py -- Thumbs plugin for Ginga image viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import hashlib
import threading

from ginga import GingaPlugin
from ginga.misc import Bunch, Future
from ginga.util import iohelper
from ginga.misc import Bunch
from ginga.gw import GwHelp, Widgets, Viewers


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
        self.cursor = 0
        tt_keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Thumbs')
        self.settings.addDefaults(preload_images=False,
                                  cache_thumbs=False,
                                  cache_location='local',
                                  auto_scroll=True,
                                  rebuild_wait=4.0,
                                  tt_keywords=tt_keywords,
                                  mouseover_name_key='NAME',
                                  thumb_length=150,
                                  sort_order=None,
                                  label_length=25,
                                  label_cutoff='right')
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

        fv.set_callback('add-image', self.add_image)
        fv.set_callback('remove-image', self.remove_image)
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.add_callback('active-image', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):
        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        tg = Viewers.ImageViewCanvas(logger=self.logger)
        tg.configure_window(200, 200)
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

        b.auto_scroll.set_tooltip("Scroll the thumbs window when new images arrive")
        b.clear.set_tooltip("Remove all current thumbnails")
        b.clear.add_callback('activated', lambda w: self.clear())
        auto_scroll = self.settings.get('auto_scroll', True)
        b.auto_scroll.set_state(auto_scroll)
        container.add_widget(w, stretch=0)

        self.gui_up = True

    def get_thumb_key(self, chname, imname, path):
        if path is not None:
            path = os.path.abspath(path)
        thumbkey = (chname.lower(), imname, path)
        return thumbkey

    def add_image(self, viewer, chname, image):
        if not self.gui_up:
            return False

        # image is flagged not to make a thumbnail?
        nothumb = image.get('nothumb', False)
        if nothumb:
            return

        idx = image.get('idx', None)
        # get image path
        path = image.get('path', None)
        if path is not None:
            # get image name
            name = self.fv.name_image_from_path(path, idx=idx)
        else:
            name = 'NoName'

        name = image.get('name', name)

        thumbname = name
        self.logger.info("making thumb for %s" % (thumbname))

        future = image.get('image_future', None)
        if future is None:
            image_loader = image.get('loader', self.fv.load_image)
            future = Future.Future()
            future.freeze(image_loader, path, idx=idx)

        # Is there a preference set to avoid making thumbnails?
        chinfo = self.fv.get_channelInfo(chname)
        prefs = chinfo.prefs
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
        metadata[self.settings.get('mouseover_name_key','NAME')] = name

        thumbpath = self.get_thumbpath(path)

        with self.thmblock:
            self.copy_attrs(chinfo.fitsimage)
            self.thumb_generator.set_image(image)
            imgwin = self.thumb_generator.get_image_as_widget()

        label_length = self.settings.get('label_length', None)
        label_cutoff = self.settings.get('label_cutoff', 'right')

        # Shorten thumbnail label, if requested
        if label_length is not None:
            thumbname = iohelper.shorten_name(thumbname, label_length,
                                              side=label_cutoff)

        self.insert_thumbnail(imgwin, thumbkey, thumbname, chname, name, path,
                              thumbpath, metadata, future)

    def remove_image(self, viewer, chname, name, path):
        if not self.gui_up:
            return

        if path is None:
            # Currently we need a path to make a thumb key
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

        self.reorder_thumbs()

    def update_thumbs(self, nameList):

        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumbList) - set(nameList)
        if len(invalid) > 0:
            with self.thmblock:
                for thumbkey in invalid:
                    self.thumbList.remove(thumbkey)
                    del self.thumbDict[thumbkey]

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

    def load_file(self, thumbkey, chname, name, path,
                  image_future):
        self.logger.debug("loading image: %s" % (str(thumbkey)))
        self.fv.switch_name(chname, name, path=path,
                            image_future=image_future)

        # remember the last file we loaded
        with self.thmblock:
            index = self.thumbList.index(thumbkey)
            self.cursor = index

            preload = self.settings.get('preload_images', False)
            if not preload:
                return

            # TODO: clear any existing files waiting to be preloaded?

            # queue next and previous files for preloading
            if index < len(self.thumbList)-1:
                nextkey = self.thumbList[index+1]
                bnch = self.thumbDict[nextkey]
                if bnch.path is not None:
                    self.fv.add_preload(bnch.chname, bnch.imname, bnch.path,
                                        image_future=bnch.image_future)

            if index > 0:
                prevkey = self.thumbList[index-1]
                bnch = self.thumbDict[prevkey]
                if bnch.path is not None:
                    self.fv.add_preload(bnch.chname, bnch.imname, bnch.path,
                                        image_future=bnch.image_future)

    def load_next(self):
        with self.thmblock:
            index = self.cursor + 1
            if index < len(self.thumbList)-1:
                nextkey = self.thumbList[index+1]
                bnch = self.thumbDict[nextkey]
                self.gui_do(self.load_file, nextkey,
                            bnch.chname, bnch.imname, bnch.path,
                            bnch.image_future)

    def load_previous(self):
        with self.thmblock:
            index = self.cursor - 1
            if index > 0:
                prevkey = self.thumbList[index+1]
                bnch = self.thumbDict[prevkey]
                self.gui_do(self.load_file, prevkey,
                            bnch.chname, bnch.imname, bnch.path,
                            bnch.image_future)

    def clear(self):
        with self.thmblock:
            self.clear_widget()
            self.thumbList = []
            self.thumbDict = {}
        self.reorder_thumbs()

    def add_channel(self, viewer, chinfo):
        """Called when a channel is added from the main interface.
        Parameter is chinfo (a bunch)."""
        fitsimage = chinfo.fitsimage
        fitssettings = fitsimage.get_settings()
        for name in ['cuts']:
            fitssettings.getSetting(name).add_callback('set',
                               self.cutset_cb, fitsimage)
        fitsimage.add_callback('transform', self.transform_cb)

        rgbmap = fitsimage.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, fitsimage)

    def focus_cb(self, viewer, fitsimage):
        # Reflect transforms, colormap, etc.
        image = fitsimage.get_image()
        if image is None:
            return
        if not self.have_thumbnail(fitsimage, image):
            # No memory of this thumbnail, so regenerate it
            chname = viewer.get_channelName(fitsimage)
            self.add_image(viewer, chname, image)
            return

        # Else schedule an update of the thumbnail for changes to
        # cut levels, etc.
        self.redo_delay(fitsimage)

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

    def have_thumbnail(self, fitsimage, image):
        """Returns True if we already have a thumbnail version of this image
        cached, False otherwise.
        """
        chname = self.fv.get_channelName(fitsimage)

        # Look up our version of the thumb
        idx = image.get('idx', None)
        path = image.get('path', None)
        if not (path is None):
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

        chname = self.fv.get_channelName(fitsimage)

        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        # Look up our version of the thumb
        idx = image.get('idx', None)
        path = image.get('path', None)
        if not (path is None):
            path = os.path.abspath(path)
            name = self.fv.name_image_from_path(path, idx=idx)
        else:
            name = 'NoName'

        # get image name
        name = image.get('name', name)
        metadata[self.settings.get('mouseover_name_key','NAME')] = name

        thumbkey = self.get_thumb_key(chname, name, path)
        with self.thmblock:
            if thumbkey not in self.thumbDict:
                # No memory of this thumbnail, so regenerate it
                self.add_image(self.fv, chname, image)
                return

            # Generate new thumbnail
            fitsimage.copy_attributes(self.thumb_generator,
                                      ['transforms', 'cutlevels',
                                       'rgbmap'])
            self.thumb_generator.set_image(image)

            # Save a thumbnail for future browsing
            if save_thumb:
                thumbpath = self.get_thumbpath(path)
                if thumbpath is not None:
                    self.thumb_generator.save_image_as_file(thumbpath,
                                                            format='jpeg')

            imgwin = self.thumb_generator.get_image_as_widget()

        self.update_thumbnail(thumbkey, imgwin, name, metadata)

    def delete_channel(self, viewer, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname_del = chinfo.name.lower()
        # TODO: delete thumbs for this channel!
        self.logger.info("deleting thumbs for channel '%s'" % (
            chname_del))
        with self.thmblock:
            self.clear_widget()
            newThumbList = []
            for thumbkey in self.thumbList:
                chname = thumbkey[0].lower()
                if chname != chname_del:
                    newThumbList.append(thumbkey)
                else:
                    del self.thumbDict[thumbkey]
            self.thumbList = newThumbList
        self.reorder_thumbs()

    def _make_thumb(self, chname, image, path, thumbkey,
                    image_future, save_thumb=False, thumbpath=None):
        # This is called by the make_thumbs() as a gui thread
        with self.thmblock:
            self.thumb_generator.set_image(image)
            # Save a thumbnail for future browsing
            if save_thumb and (thumbpath is not None):
                self.thumb_generator.save_image_as_file(thumbpath,
                                                        format='jpeg')

            imgwin = self.thumb_generator.get_image_as_widget()

            # Get metadata for mouse-over tooltip
            image = self.thumb_generator.get_image()

        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        dirname, name = os.path.split(path)

        thumbname = name
        if '.' in thumbname:
            thumbname = thumbname.split('.')[0]

        self.insert_thumbnail(imgwin, thumbkey, thumbname,
                              chname, name, path, thumbpath, metadata,
                              image_future)
        self.fv.update_pending(timeout=0.001)

    def make_thumbs(self, chname, filelist, image_loader=None):
        # NOTE: this is called by the FBrowser plugin, as a non-gui thread!
        if image_loader is None:
            image_loader = self.fv.load_image

        cache_thumbs = self.settings.get('cache_thumbs', False)

        for path in filelist:
            self.logger.info("generating thumb for %s..." % (
                path))
            imname = self.fv.name_image_from_path(path)

            # Do we already have this thumb loaded?
            thumbkey = self.get_thumb_key(chname, imname, path)
            thumbpath = self.get_thumbpath(path)

            with self.thmblock:
                try:
                    bnch = self.thumbDict[thumbkey]
                    # if these are not equal then the mtime must have
                    # changed on the file, better reload and regenerate
                    if bnch.thumbpath == thumbpath:
                        continue
                except KeyError:
                    pass

            # Is there a cached thumbnail image on disk we can use?
            save_thumb = cache_thumbs
            image = None
            if (thumbpath is not None) and os.path.exists(thumbpath):
                save_thumb = False
                try:
                    image = image_loader(thumbpath)
                except Exception as e:
                    pass

            try:
                if image is None:
                    image = image_loader(path)

                image_future = Future.Future()
                image_future.freeze(image_loader, path)

                self.fv.gui_do(self._make_thumb, chname, image, path,
                               thumbkey, image_future,
                               save_thumb=save_thumb,
                               thumbpath=thumbpath)

            except Exception as e:
                self.logger.error("Error generating thumbnail for '%s': %s" % (
                    path, str(e)))
                continue
                # TODO: generate "broken thumb"?


    def _gethex(self, s):
        return hashlib.sha1(s.encode()).hexdigest()

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
            thumbdir = os.path.join(thumbDir, self._gethex(dirpath))
        else:
            # thumbs in .thumbs subdirectory of image folder
            thumbdir = os.path.join(dirpath, '.thumbs')

        if not os.path.exists(thumbdir):
            if not makedir:
                self.logger.error("Thumb directory does not exist: %s" % (
                    thumbdir))
                return None

            try:
                os.makedirs(thumbdir)
                # Write meta file
                metafile = os.path.join(thumbdir, "meta")
                with open(metafile, 'w') as out_f:
                    out_f.write("srcdir: %s\n" % (dirpath))

            except OSError as e:
                self.logger.error("Could not make thumb directory '%s': %s" % (
                    thumbdir, str(e)))
                return None

        # Get location of thumb
        modtime = os.stat(path).st_mtime
        thumb_fname = self._gethex("%s.%s" % (filename, modtime))
        thumbpath = os.path.join(thumbdir, thumb_fname + ".jpg")
        self.logger.debug("thumb path is '%s'" % (thumbpath))
        return thumbpath

    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path,
                         thumbpath, metadata, image_future):

        # make a context menu
        menu = self._mk_context_menu(thumbkey, chname, name, path, image_future)

        thumbw = Widgets.Image(native_image=imgwin, menu=menu,
                               style='clickable')
        wd, ht = self.thumb_generator.get_window_size()
        thumbw.resize(wd, ht)

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
                           name=name, imname=name,
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
                self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols
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
                self.logger.warn("Couldn't determine %s name: %s" % (
                    kwd, str(e)))
                text = "%s: N/A" % (kwd)
            result.append(text)

        return '\n'.join(result)

    def _mk_context_menu(self, thumbkey, chname, name, path, image_future):
        menu = Widgets.Menu()
        item = menu.add_name("Display")
        item.add_callback('activated',
                          lambda w: self.load_file(thumbkey, chname, name,
                                                      path, image_future))
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
                self.logger.debug("No thumb found for %s; not updating thumbs" % (
                    str(thumbkey)))
                return

            self.logger.info("updating thumbnail '%s'" % (name))
            bnch.image._set_image(imgwin)
            self.logger.debug("update finished.")

    def __str__(self):
        return 'thumbs'

#END
