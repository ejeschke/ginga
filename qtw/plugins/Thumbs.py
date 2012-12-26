#
# Thumbs.py -- Thumbnail plugin for fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Mon Nov 26 21:43:05 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import FitsImageQt as FitsImageQt
import GingaPlugin

from PyQt4 import QtGui, QtCore
import time
import os.path

import Bunch

class MyScrollArea(QtGui.QScrollArea):

    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
        #print "area resized to %dx%d" % (width,height)
        self.thumbs_cb(width, height)

class MyLabel(QtGui.QLabel):

    def mousePressEvent(self, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()

        if buttons & QtCore.Qt.LeftButton:
            self.thumbs_cb()

    
class Thumbs(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        # For thumbnail pane
        self.thumbDict = {}
        self.thumbList = []
        self.thumbNumRows = 20
        self.thumbNumCols = 1
        self.thumbColCount = 0
        self.thumbRowCount = 0
        # distance in pixels between thumbs
        self.thumbSep = 15
        # max length of thumb on the long side
        self.thumbWidth = 150

        self.thmbtask = None
        self.lagtime = 4000

        self.keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        fv.set_callback('add-image', self.add_image)
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.add_callback('active-image', self.focus_cb)

    def initialize(self, container):
        rvbox = container

        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        tg = FitsImageQt.FitsImageQt(logger=self.logger)
        tg.configure(200, 200)
        tg.enable_autoscale('on')
        tg.enable_autolevels('on')
        tg.set_makebg(False)
        self.thumb_generator = tg

        sw = MyScrollArea()
        sw.setWidgetResizable(True)
        sw.thumbs_cb = self.thumbpane_resized

        # Create thumbnails pane
        widget = QtGui.QWidget()
        vbox = QtGui.QGridLayout()
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(14)
        widget.setLayout(vbox)
        self.w.thumbs = vbox
        self.w.thumbs_w = widget
        #widget.show()
        sw.setWidget(widget)
        self.w.thumbs_scroll = sw
        #self.w.thumbs_scroll.connect("size_allocate", self.thumbpane_resized)

        # TODO: should this even have it's own scrolled window?
        rvbox.addWidget(sw, stretch=1)
        sw.show()

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
        if prefs.has_key('genthumb') and (not prefs['genthumb']):
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
        imgwin = self.thumb_generator.get_image_as_widget()

        self.insert_thumbnail(imgwin, thumbkey, thumbname, chname, name, path,
                              metadata)

    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path,
                         metadata):
        pixmap = QtGui.QPixmap.fromImage(imgwin)
        imglbl = MyLabel()
        imglbl.setPixmap(pixmap)
        imglbl.thumbs_cb = lambda: self.fv.switch_name(chname, name, path=path)

        text = self.query_thumb(thumbkey, name, metadata)
        imglbl.setToolTip(text)

        widget = QtGui.QWidget()
        #vbox = QtGui.QGridLayout()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        widget.setLayout(vbox)
        namelbl = QtGui.QLabel(thumbname)
        namelbl.setAlignment(QtCore.Qt.AlignLeft)
        namelbl.setAlignment(QtCore.Qt.AlignHCenter)
        ## vbox.addWidget(namelbl, 0, 0)
        ## vbox.addWidget(imglbl,  1, 0)
        vbox.addWidget(namelbl, stretch=0)
        vbox.addWidget(imglbl,  stretch=0)
        widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed))
        #widget.show()
        bnch = Bunch.Bunch(widget=widget, image=imgwin, layout=vbox,
                           imglbl=imglbl, name=name, chname=chname,
                           path=path, pixmap=pixmap)

        self.thumbDict[thumbkey] = bnch
        self.thumbList.append(thumbkey)

        self.w.thumbs.addWidget(widget,
                                self.thumbRowCount, self.thumbColCount)
        self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols
        if self.thumbColCount == 0:
            self.thumbRowCount += 1

        #self.w.thumbs.show()
        
        # force scroll to bottom of thumbs
        rect = self.w.thumbs_w.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        self.w.thumbs_scroll.ensureVisible(x1, y1)
        #self.w.thumbs_scroll.show()
        self.logger.debug("added thumb for %s" % (thumbname))

    def reorder_thumbs(self):
        # Remove widgets from grid
        for thumbkey in self.thumbList:
            bnch = self.thumbDict[thumbkey]
            self.w.thumbs.removeWidget(bnch.widget)

        # Add thumbs back in by rows
        self.thumbColCount = 0
        self.thumbRowCount = 0
        for thumbkey in self.thumbList:
            bnch = self.thumbDict[thumbkey]
            self.w.thumbs.addWidget(bnch.widget,
                                    self.thumbRowCount, self.thumbColCount)
            self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols
            if self.thumbColCount == 0:
                self.thumbRowCount += 1
                
        self.w.thumbs_w.update()
        #self.w.thumbs_scroll.show()
        
    def update_thumbs(self, nameList):
        
        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumbList) - set(nameList)
        if len(invalid) > 0:
            for thumbkey in invalid:
                self.thumbList.remove(thumbkey)
                del self.thumbDict[thumbkey]

            self.reorder_thumbs()


    def thumbpane_resized(self, width, height):
        self.logger.debug("rebuilding thumbs width=%d" % (width))

        cols = max(1, width // (self.thumbWidth + self.thumbSep))
        if self.thumbNumCols == cols:
            # If we have not actually changed the possible number of columns
            # then don't do anything
            return False
        self.logger.debug("column count is now %d" % (cols))
        self.thumbNumCols = cols

        self.reorder_thumbs()
        return False
        
    def query_thumb(self, thumbkey, name, metadata):
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
        return s

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
        try:
            self.thmbtask.stop()
        except:
            pass
        self.thmbtask = QtCore.QTimer()
        self.thmbtask.setSingleShot(True)
        self.thmbtask.timeout.connect(lambda: self.redo_thumbnail(fitsimage))
        self.thmbtask.start(self.lagtime)
        #print "added delay task..."
        return True

    def redo_thumbnail(self, fitsimage):
        self.logger.debug("redoing thumbnail...")
        # Get the thumbnail image 
        image = fitsimage.get_image()
        if image == None:
            return
        
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
        imgwin = self.thumb_generator.get_image_as_widget()

        self.logger.debug("generating pixmap.")
        pixmap = QtGui.QPixmap.fromImage(imgwin)
        bnch.imgwin = imgwin
        bnch.pixmap = pixmap
        bnch.imglbl.setPixmap(pixmap)
        bnch.imglbl.repaint()
        self.w.thumbs_w.update()
        self.logger.debug("update finished.")
        
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
        
    def _make_thumb(self, chname, image, path, thumbkey):
        # This is called by the make_thumbs() as a gui thread
        self.thumb_generator.set_image(image)
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
        #self.fv.update_pending()
        
    def make_thumbs(self, chname, filelist):
        # This is called by the FBrowser plugin, as a non-gui thread!
        lcname = chname.lower()

        for path in filelist:
            self.logger.info("generating thumb for %s..." % (
                path))

            # Do we already have this thumb made?
            path = os.path.abspath(path)
            thumbkey = (lcname, path)
            if self.thumbDict.has_key(thumbkey):
                continue

            try:
                image = self.fv.load_image(path)
                self.fv.gui_do(self._make_thumb, chname, image, path,
                               thumbkey)
                
            except Exception, e:
                self.logger.error("Error generating thumbnail for '%s': %s" % (
                    name, str(e)))
                # TODO: generate "broken thumb"?


    def __str__(self):
        return 'thumbs'
    
#END
