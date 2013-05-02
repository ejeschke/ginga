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
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Thumbs')
        self.settings.load(onError='silent')

        self.thmbtask = None
        self.lagtime = 4000

        self.keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        fv.set_callback('add-image', self.add_image)
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.add_callback('active-image', self.focus_cb)

    def add_image(self, viewer, chname, image):
        noname = 'Noname' + str(time.time())
        name = image.get('name', noname)
        path = image.get('path', None)
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
        if self.thumbDict.has_key(thumbkey):
            return

        #data = image.get_data()
        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        #self.thumb_generator.set_data(data)
        self.thumb_generator.set_image(image)
        self.copy_attrs(chinfo.fitsimage)
        imgwin = self.thumb_generator.get_image_as_widget()

        self.insert_thumbnail(imgwin, thumbkey, thumbname, chname, name, path,
                              metadata)

    def update_thumbs(self, nameList):
        
        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumbList) - set(nameList)
        if len(invalid) > 0:
            for thumbkey in invalid:
                self.thumbList.remove(thumbkey)
                del self.thumbDict[thumbkey]

            self.reorder_thumbs()


    def thumbpane_resized(self, width, height):
        self.logger.debug("reordering thumbs width=%d" % (width))

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
        self.fv.switch_name(chname, name, path=path)

        index = self.thumbList.index(thumbkey)
        prevkey = nextkey = None
        if index > 0:
            prevkey = self.thumbList[index-1]
        if index < len(self.thumbList)-1:
            nextkey = self.thumbList[index+1]

        if nextkey != None:
            bnch = self.thumbDict[nextkey]
            self.fv.nongui_do(self.preload_file, bnch.chname,
                              bnch.imname, bnch.path)
        
    def preload_file(self, chname, imname, path):

        print "preload: checking %s" % (imname)
        chinfo = self.fv.get_channelInfo(chname)
        datasrc = chinfo.datasrc
        print datasrc.keys(sort='time')
        print datasrc.datums.keys()
        print "has item: %s" % datasrc.has_key(imname)
        if not chinfo.datasrc.has_key(imname):
            self.logger.info("preloading image %s" % (path))
            image = self.fv.load_image(path)
            self.fv.gui_do(self.fv.add_image, imname, image,
                           chname=chname, silent=True)
        print "end preload"
    
    def clear(self):
        self.thumbList = []
        self.thumbDict = {}
        self.reorder_thumbs()
        
    def add_channel(self, viewer, chinfo):
        """Called when a channel is added from the main interface.
        Parameter is chinfo (a bunch)."""
        fitsimage = chinfo.fitsimage
        fitsimage.add_callback('cut-set', self.cutset_cb)
        fitsimage.add_callback('transform', self.transform_cb)

        rgbmap = fitsimage.get_rgbmap()
        rgbmap.add_callback('changed', self.rgbmap_cb, fitsimage)

    def focus_cb(self, viewer, fitsimage):
        # Reflect transforms, colormap, etc.
        #self.copy_attrs(fitsimage)
        self.redo_delay(fitsimage)

    def transform_cb(self, fitsimage):
        self.redo_delay(fitsimage)
        return True
        
    def cutset_cb(self, fitsimage, loval, hival):
        self.redo_delay(fitsimage)
        return True

    def rgbmap_cb(self, rgbmap, fitsimage):
        # color mapping has changed in some way
        self.redo_delay(fitsimage)
        return True

    def copy_attrs(self, fitsimage):
        # Reflect transforms, colormap, etc.
        fitsimage.copy_attributes(self.thumb_generator,
                                  ['transforms', #'cutlevels',
                                   'rgbmap'],
                                  redraw=False)

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
        if not self.thumbDict.has_key(thumbkey):
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
                              chname, name, path, metadata)
        self.fv.update_pending(timeout=0.001)
        
    def make_thumbs(self, chname, filelist):
        # This is called by the FBrowser plugin, as a non-gui thread!
        lcname = chname.lower()

        cacheThumbs = self.settings.get('cacheThumbs', False)

        for path in filelist:
            self.logger.info("generating thumb for %s..." % (
                path))

            # Do we already have this thumb loaded?
            path = os.path.abspath(path)
            thumbkey = (lcname, path)
            if self.thumbDict.has_key(thumbkey):
                continue

            # Is there a cached thumbnail image on disk we can use?
            save_thumb = cacheThumbs
            image = None
            thumbpath = self.get_thumbpath(path)
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
