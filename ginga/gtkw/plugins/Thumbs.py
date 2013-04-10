#
# Thumbs.py -- Thumbnail plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gtkw import FitsImageGtk as FitsImageGtk
from ginga import GingaPlugin

import os
import time
import hashlib
import gtk
import gobject

from ginga.misc import Bunch


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
        self.thumbColCount = 0
        # distance in pixels between thumbs
        self.thumbSep = 15
        # max length of thumb on the long side
        self.thumbWidth = 150
        # should we cache thumbs on disk?
        self.cacheThumbs = False
        # where the cache is stored
        prefs = self.fv.get_preferences()
        self.thumbDir = os.path.join(prefs.get_baseFolder(), 'thumbs')

        self.thmbtask = None
        self.lagtime = 4000

        self.keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        fv.set_callback('add-image', self.add_image)
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.add_callback('active-image', self.focus_cb)

    def initialize(self, container):
        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        tg = FitsImageGtk.FitsImageGtk(logger=self.logger)
        tg.configure(200, 200)
        tg.enable_autozoom('on')
        tg.enable_autocuts('on')
        tg.enable_auto_orient(True)
        tg.set_makebg(False)
        self.thumb_generator = tg

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        # Create thumbnails pane
        vbox = gtk.VBox(spacing=14)
        vbox.set_border_width(4)
        self.w.thumbs = vbox
        sw.add_with_viewport(vbox)
        sw.show_all()
        self.w.thumbs_scroll = sw
        self.w.thumbs_scroll.connect("size_allocate", self.thumbpane_resized)
        #nb.connect("size_allocate", self.thumbpane_resized)

        # TODO: should this even have it's own scrolled window?
        container.pack_start(sw, fill=True, expand=True)


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

        imgwin.set_property("has-tooltip", True)
        imgwin.connect("query-tooltip", self._mktt(thumbkey, name, metadata))

        self.insert_thumbnail(imgwin, thumbkey, thumbname, chname, name, path)

    def _mktt(self, thumbkey, name, metadata):
        return lambda tw, x, y, kbmode, ttw: self.query_thumb(thumbkey, name, metadata, x, y, ttw)
    
    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path):

        vbox = gtk.VBox(spacing=0)
        vbox.pack_start(gtk.Label(thumbname), expand=False,
                        fill=False, padding=0)
        evbox = gtk.EventBox()
        evbox.add(imgwin)
        evbox.connect("button-press-event",
                      lambda w, e: self.fv.switch_name(chname, name,
                                                       path=path))
        vbox.pack_start(evbox, expand=False, fill=False)
        vbox.show_all()

        bnch = Bunch.Bunch(widget=vbox, evbox=evbox)

        if self.thumbColCount == 0:
            hbox = gtk.HBox(homogeneous=True, spacing=self.thumbSep)
            self.w.thumbs.pack_start(hbox)
            self.thumbRowList.append(hbox)

        else:
            hbox = self.thumbRowList[-1]

        hbox.pack_start(bnch.widget)
        self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols

        self.w.thumbs.show_all()
        
        self.thumbDict[thumbkey] = bnch
        self.thumbList.append(thumbkey)
        # force scroll to bottom of thumbs
        adj_w = self.w.thumbs_scroll.get_vadjustment()
        max = adj_w.get_upper()
        adj_w.set_value(max)

    def reorder_thumbs(self):
        # Remove old rows
        for hbox in self.thumbRowList:
            children = hbox.get_children()
            for child in children:
                hbox.remove(child)
            self.w.thumbs.remove(hbox)

        # Add thumbs back in by rows
        self.thumbRowList = []
        colCount = 0
        hbox = None
        for thumbkey in self.thumbList:
            self.logger.debug("adding thumb for %s" % (str(thumbkey)))
            chname, name = thumbkey
            bnch = self.thumbDict[thumbkey]
            if colCount == 0:
                hbox = gtk.HBox(homogeneous=True, spacing=self.thumbSep)
                hbox.show()
                self.w.thumbs.pack_start(hbox)
                self.thumbRowList.append(hbox)

            hbox.pack_start(bnch.widget)
            hbox.show_all()
            colCount = (colCount + 1) % self.thumbNumCols

        self.thumbColCount = colCount
        self.w.thumbs.show_all()
        
    def update_thumbs(self, nameList):
        
        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumbList) - set(nameList)
        if len(invalid) > 0:
            for thumbkey in invalid:
                self.thumbList.remove(thumbkey)
                del self.thumbDict[thumbkey]

            self.reorder_thumbs()


    def thumbpane_resized(self, widget, allocation):
        x, y, width, height = self.w.thumbs_scroll.get_allocation()
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
        
    def query_thumb(self, thumbkey, name, metadata, x, y, ttw):
        objtext = 'Object: UNKNOWN'
        try:
            objtext = 'Object: ' + metadata['OBJECT']
        except Exception, e:
            self.logger.error("Couldn't determine OBJECT name: %s" % str(e))

        uttext = 'UT: UNKNOWN'
        try:
            uttext = 'UT: ' + metadata['UT']
        except Exception, e:
            self.logger.error("Couldn't determine UT: %s" % str(e))

        chname, path = thumbkey

        s = "%s\n%s\n%s\n%s" % (chname, name, objtext, uttext)
        ttw.set_text(s)
            
        return True

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
                                  ['transforms', 'cutlevels',
                                   'rgbmap'],
                                  redraw=False)

    def redo_delay(self, fitsimage):
        # Delay regeneration of thumbnail until most changes have propagated
        if self.thmbtask != None:
            gobject.source_remove(self.thmbtask)
        self.thmbtask = gobject.timeout_add(self.lagtime, self.redo_thumbnail,
                                            fitsimage)
        return True

    def redo_thumbnail(self, fitsimage, save_thumb=None):
        self.logger.debug("redoing thumbnail...")
        # Get the thumbnail image 
        image = fitsimage.get_image()
        if image == None:
            return
        if save_thumb == None:
            save_thumb = self.cacheThumbs
        
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
        try:
            thumbkey = (chname, path)
            bnch = self.thumbDict[thumbkey]
        except KeyError:
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

        imgwin.set_property("has-tooltip", True)
        imgwin.connect("query-tooltip", self._mktt(thumbkey, name, metadata))

        # Replace thumbnail image widget
        child = bnch.evbox.get_child()
        bnch.evbox.remove(child)
        bnch.evbox.add(imgwin)

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
                    save_thumb=False):
        # This is called by the make_thumbs() as a gui thread
        self.thumb_generator.set_image(image)
        # Save a thumbnail for future browsing
        if save_thumb:
            thumbpath = self.get_thumbpath(path)
            if thumbpath != None:
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

        imgwin.set_property("has-tooltip", True)
        imgwin.connect("query-tooltip", self._mktt(thumbkey, name, metadata))

        thumbname = name
        if '.' in thumbname:
            thumbname = thumbname.split('.')[0]

        self.insert_thumbnail(imgwin, thumbkey, thumbname,
                              chname, name, path)
        self.fv.update_pending(timeout=0.001)
        
    def make_thumbs(self, chname, filelist):
        # This is called by the FBrowser plugin, as a non-gui thread!
        lcname = chname.lower()

        for path in filelist:
            self.logger.info("generating thumb for %s..." % (
                path))

            # Do we already have this thumb loaded?
            path = os.path.abspath(path)
            thumbkey = (lcname, path)
            if self.thumbDict.has_key(thumbkey):
                continue

            # Is there a cached thumbnail image on disk we can use?
            save_thumb = self.cacheThumbs
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
                               thumbkey, save_thumb=save_thumb)
                
            except Exception, e:
                self.logger.error("Error generating thumbnail for '%s': %s" % (
                    path, str(e)))
                continue
                # TODO: generate "broken thumb"?


    def _gethex(self, s):
        return hashlib.sha1(s).hexdigest()
    
    def get_thumbpath(self, path, makedir=True):
        path = os.path.abspath(path)
        dirpath, filename = os.path.split(path)
        # Get thumb directory
        thumbdir = os.path.join(self.thumbDir, self._gethex(dirpath))
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
        return thumbpath
                                 
    def __str__(self):
        return 'thumbs'
    
#END
