#
# ThumbsBase.py -- Thumbnail plugin base class for Ginga
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import time
import hashlib
import threading

from ginga import GingaPlugin
from ginga.misc import Bunch


class ThumbsBase(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(ThumbsBase, self).__init__(fv)

        # For thumbnail pane
        self.thumbDict = {}
        self.thumbList = []
        self.thumbRowList = []
        self.thumbNumRows = 20
        self.thumbNumCols = 1
        self.thumbColCount = 0
        # distance in pixels between thumbs
        self.thumbSep = 15
        # max length of thumb on the long side
        self.thumbWidth = 150
        self.cursor = 0

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Thumbs')
        self.settings.load(onError='silent')

        self.thmbtask = fv.get_timer()
        self.thmbtask.set_callback('expired', self.redo_delay_timer)
        self.lagtime = 4.0
        self.thmblock = threading.RLock()

        self.keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        fv.set_callback('add-image', self.add_image)
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.add_callback('active-image', self.focus_cb)

    def add_image(self, viewer, chname, image):
        noname = 'Noname' + str(time.time())
        name = image.get('name', noname)
        path = image.get('path', None)
        nothumb = image.get('nothumb', False)
        if path != None:
            path = os.path.abspath(path)
        thumbname = name
        if '.' in thumbname:
            thumbname = thumbname.split('.')[0]
        self.logger.debug("making thumb for %s" % (thumbname))
            
        # Is there a preference set to avoid making thumbnails?
        chinfo = self.fv.get_channelInfo(chname)
        prefs = chinfo.prefs
        if not prefs.get('genthumb', False):
            return
        
        # Is this thumbnail already in the list?
        # NOTE: does not handle two separate images with the same name
        # in the same channel
        thumbkey = (chname.lower(), path)
        with self.thmblock:
            if self.thumbDict.has_key(thumbkey) or nothumb:
                return

        #data = image.get_data()
        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        thumbpath = self.get_thumbpath(path)
        
        #self.thumb_generator.set_data(data)
        with self.thmblock:
            self.thumb_generator.set_image(image)
            self.copy_attrs(chinfo.fitsimage)
            imgwin = self.thumb_generator.get_image_as_widget()

        self.insert_thumbnail(imgwin, thumbkey, thumbname, chname, name, path,
                              thumbpath, metadata)

    def update_thumbs(self, nameList):
        
        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumbList) - set(nameList)
        if len(invalid) > 0:
            with self.thmblock:
                for thumbkey in invalid:
                    self.thumbList.remove(thumbkey)
                    del self.thumbDict[thumbkey]

            self.reorder_thumbs()


    def thumbpane_resized(self, width, height):
        self.logger.debug("reordering thumbs width=%d" % (width))

        with self.thmblock:
            cols = max(1, width // (self.thumbWidth + self.thumbSep))
            if self.thumbNumCols == cols:
                # If we have not actually changed the possible number of columns
                # then don't do anything
                return False
            self.logger.debug("column count is now %d" % (cols))
            self.thumbNumCols = cols

        self.reorder_thumbs()
        return False
        
    def load_file(self, thumbkey, chname, name, path):
        self.logger.debug("loading image: %s" % (str(thumbkey)))
        self.fv.switch_name(chname, name, path=path)

        # remember the last file we loaded
        with self.thmblock:
            index = self.thumbList.index(thumbkey)
            self.cursor = index

            preload = self.settings.get('preloadImages', False)
            if not preload:
                return

            # TODO: clear any existing files waiting to be preloaded?

            # queue next and previous files for preloading
            if index < len(self.thumbList)-1:
                nextkey = self.thumbList[index+1]
                bnch = self.thumbDict[nextkey]
                if bnch.path != None:
                    self.fv.add_preload(bnch.chname, bnch.imname, bnch.path)

            if index > 0:
                prevkey = self.thumbList[index-1]
                bnch = self.thumbDict[prevkey]
                if bnch.path != None:
                    self.fv.add_preload(bnch.chname, bnch.imname, bnch.path)

    def load_next(self):
        with self.thmblock:
            index = self.cursor + 1
            if index < len(self.thumbList)-1:
                nextkey = self.thumbList[index+1]
                bnch = self.thumbDict[nextkey]
                self.gui_do(self.load_file, nextkey,
                            bnch.chname, bnch.imname, bnch.path)
        
    def load_previous(self):
        with self.thmblock:
            index = self.cursor - 1
            if index > 0:
                prevkey = self.thumbList[index+1]
                bnch = self.thumbDict[prevkey]
                self.gui_do(self.load_file, prevkey,
                            bnch.chname, bnch.imname, bnch.path)
        
    def clear(self):
        with self.thmblock:
            self.clearWidget()
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
                                   'rgbmap'],
                                  redraw=False)

    def have_thumbnail(self, fitsimage, image):
        """Returns True if we already have a thumbnail version of this image
        cached, False otherwise.
        """
        chname = self.fv.get_channelName(fitsimage)

        # Look up our version of the thumb
        path = image.get('path', None)
        if path == None:
            # No path, so no way to find key for cached image
            return False
        path = os.path.abspath(path)
        thumbkey = (chname, path)
        with self.thmblock:
            return self.thumbDict.has_key(thumbkey)

    def redo_thumbnail(self, fitsimage, save_thumb=None):
        self.logger.debug("redoing thumbnail...")
        # Get the thumbnail image 
        image = fitsimage.get_image()
        if image == None:
            return
        if save_thumb == None:
            save_thumb = self.settings.get('cacheThumbs', False)
        
        chname = self.fv.get_channelName(fitsimage)

        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        # Look up our version of the thumb
        name = image.get('name', None)
        path = image.get('path', None)
        if path == None:
            return
        path = os.path.abspath(path)
        thumbkey = (chname, path)
        with self.thmblock:
            if not self.thumbDict.has_key(thumbkey):
                # No memory of this thumbnail, so regenerate it
                self.add_image(self.fv, chname, image)
                return

            # Generate new thumbnail
            # TODO: Can't use set_image() because we will override the saved
            # cuts settings...should look into fixing this...
            ## timage = self.thumb_generator.get_image()
            ## if timage != image:
            ##     self.thumb_generator.set_image(image)
            #data = image.get_data()
            #self.thumb_generator.set_data(data)
            self.thumb_generator.set_image(image)
            fitsimage.copy_attributes(self.thumb_generator,
                                      ['transforms', 'cutlevels',
                                       'rgbmap'],
                                      redraw=False)

            # Save a thumbnail for future browsing
            if save_thumb:
                thumbpath = self.get_thumbpath(path)
                if thumbpath != None:
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
            newThumbList = []
            for thumbkey in self.thumbList:
                chname, path = thumbkey
                if chname != chname_del:
                    newThumbList.append(thumbkey)
                else:
                    del self.thumbDict[thumbkey]
            self.thumbList = newThumbList
        self.reorder_thumbs()

    def _make_thumb(self, chname, image, path, thumbkey,
                    save_thumb=False, thumbpath=None):
        # This is called by the make_thumbs() as a gui thread
        with self.thmblock:
            self.thumb_generator.set_image(image)
            # Save a thumbnail for future browsing
            if save_thumb and (thumbpath != None):
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
                              chname, name, path, thumbpath, metadata)
        self.fv.update_pending(timeout=0.001)
        
    def make_thumbs(self, chname, filelist):
        # NOTE: this is called by the FBrowser plugin, as a non-gui thread!
        lcname = chname.lower()

        cacheThumbs = self.settings.get('cacheThumbs', False)

        for path in filelist:
            self.logger.info("generating thumb for %s..." % (
                path))

            # Do we already have this thumb loaded?
            path = os.path.abspath(path)
            thumbkey = (lcname, path)
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
            save_thumb = cacheThumbs
            image = None
            if (thumbpath != None) and os.path.exists(thumbpath):
                save_thumb = False
                try:
                    image = self.fv.load_image(thumbpath)
                except Exception, e:
                    pass

            try:
                if image == None:
                    image = self.fv.load_image(path)
                self.fv.gui_do(self._make_thumb, chname, image, path,
                               thumbkey, save_thumb=save_thumb,
                               thumbpath=thumbpath)
                
            except Exception, e:
                self.logger.error("Error generating thumbnail for '%s': %s" % (
                    path, str(e)))
                continue
                # TODO: generate "broken thumb"?


    def _gethex(self, s):
        return hashlib.sha1(s.encode()).hexdigest()
    
    def get_thumbpath(self, path, makedir=True):
        if path == None:
            return None
        
        path = os.path.abspath(path)
        dirpath, filename = os.path.split(path)
        # Get thumb directory
        cacheLocation = self.settings.get('cacheLocation', 'local')
        if cacheLocation == 'ginga':
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
                os.mkdir(thumbdir)
                # Write meta file
                metafile = os.path.join(thumbdir, "meta")
                with open(metafile, 'w') as out_f:
                    out_f.write("srcdir: %s\n" % (dirpath))
                    
            except OSError, e:
                self.logger.error("Could not make thumb directory '%s': %s" % (
                    thumbdir, str(e)))
                return None

        # Get location of thumb
        modtime = os.stat(path).st_mtime
        thumbkey = self._gethex("%s.%s" % (filename, modtime))
        thumbpath = os.path.join(thumbdir, thumbkey + ".jpg")
        self.logger.debug("thumb path is '%s'" % (thumbpath))
        return thumbpath
                                 
#END
