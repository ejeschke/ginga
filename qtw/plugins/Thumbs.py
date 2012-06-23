#
# Thumbs.py -- Thumbnail plugin for fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:50:30 HST 2012
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

import Bunch

class MyScrollArea(QtGui.QScrollArea):

    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
        print "area resized to %dx%d" % (width,height)
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
        self.thumbRowList = []
        self.thumbNumRows = 20
        self.thumbNumCols = 1
        self.thumbColCount = 0
        # distance in pixels between thumbs
        self.thumbSep = 15
        # max length of thumb on the long side
        self.thumbWidth = 150

        self.keywords = ['OBJECT', 'FRAMEID', 'UT', 'DATE-OBS']

        fv.set_callback('add-image', self.add_image)
        fv.set_callback('delete-channel', self.delete_channel)

    def initialize(self, container):
        rvbox = container

        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        self.thumb_generator = FitsImageQt.FitsImageQt(logger=self.logger)
        self.thumb_generator.configure(200, 200)
        self.thumb_generator.enable_autoscale('on')
        self.thumb_generator.enable_autolevels('on')
        self.thumb_generator.set_zoom_limits(-100, 10)

        sw = MyScrollArea()
        sw.setWidgetResizable(True)
        sw.thumbs_cb = self.thumbpane_resized

        # Create thumbnails pane
        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
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
        thumbname = name
        if '.' in thumbname:
            thumbname = thumbname.split('.')[0]
            
        # Is this thumbnail already in the list?
        # TODO: does not handle two separate images with the same name!!
        print self.thumbDict
        if self.thumbDict.has_key(name):
            return

        # Is there a preference set to avoid making thumbnails?
        chinfo = self.fv.get_channelInfo(chname)
        prefs = chinfo.prefs
        if prefs.has_key('genthumb') and (not prefs['genthumb']):
            return
        
        data = image.get_data()
        # Get metadata for mouse-over tooltip
        header = image.get_header()
        metadata = {}
        for kwd in self.keywords:
            metadata[kwd] = header.get(kwd, 'N/A')

        self.thumb_generator.set_data(data)
        imgwin = self.thumb_generator.get_image_as_widget()
        pixmap = QtGui.QPixmap.fromImage(imgwin)
        imglbl = MyLabel()
        imglbl.setPixmap(pixmap)
        imglbl.thumbs_cb = lambda: self.fv.switch_name(chname, name, path=path)

        text = self.query_thumb(metadata)
        imglbl.setToolTip(text)

        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        widget.setLayout(vbox)
        namelbl = QtGui.QLabel(thumbname)
        namelbl.setAlignment(QtCore.Qt.AlignHCenter)
        vbox.addWidget(namelbl, stretch=0)
        vbox.addWidget(imglbl, stretch=0)
        widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed))
        #widget.show()
        bnch = Bunch.Bunch(widget=widget, image=imgwin)

        if self.thumbColCount == 0:
            widget2 = QtGui.QWidget()
            hbox = QtGui.QHBoxLayout()
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(self.thumbSep)
            widget2.setLayout(hbox)
            #widget2.show()
            self.w.thumbs.addWidget(widget2, stretch=0)
            self.thumbRowList.append(widget2)

        else:
            hbox = self.thumbRowList[-1].layout()

        hbox.addWidget(bnch.widget, stretch=0)
        self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols

        #self.w.thumbs.show()
        
        self.thumbDict[name] = bnch
        self.thumbList.append(name)
        # force scroll to bottom of thumbs
        rect = self.w.thumbs_w.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        self.w.thumbs_scroll.ensureVisible(x1, y1)
        #self.w.thumbs_scroll.show()

    def rebuild_thumbs(self):
        # Remove old rows
        for widget in self.thumbRowList:
            hbox = widget.layout()
            children = widget.children()
            children.remove(hbox)
            for child in children:
                hbox.removeWidget(child)
            self.w.thumbs.removeWidget(widget)

        # Add thumbs back in by rows
        self.thumbRowList = []
        colCount = 0
        hbox = None
        for name in self.thumbList:
            self.logger.debug("adding thumb for %s" % (name))
            bnch = self.thumbDict[name]
            if colCount == 0:
                widget2 = QtGui.QWidget()
                hbox = QtGui.QHBoxLayout()
                hbox.setContentsMargins(0, 0, 0, 0)
                hbox.setSpacing(self.thumbSep)
                widget2.setLayout(hbox)
                self.w.thumbs.addWidget(widget2, stretch=0)
                self.thumbRowList.append(widget2)

            hbox.addWidget(bnch.widget, stretch=0)
            colCount = (colCount + 1) % self.thumbNumCols

        self.thumbColCount = colCount
        self.w.thumbs_scroll.show()
        
    def update_thumbs(self, nameList):
        
        # Remove old thumbs that are not in the dataset
        invalid = set(self.thumbList) - set(nameList)
        if len(invalid) > 0:
            for name in invalid:
                self.thumbList.remove(name)
                del self.thumbDict[name]

            self.rebuild_thumbs()


    def thumbpane_resized(self, width, height):
        self.logger.debug("rebuilding thumbs width=%d" % (width))

        cols = max(1, width // (self.thumbWidth + self.thumbSep))
        if self.thumbNumCols == cols:
            # If we have not actually changed the possible number of columns
            # then don't do anything
            return False
        self.logger.debug("column count is now %d" % (cols))
        self.thumbNumCols = cols

        self.rebuild_thumbs()
        return False
        
    def query_thumb(self, metadata):
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

        name = metadata.get('FRAMEID', 'Noname')
        s = "%s\n%s\n%s" % (name, objtext, uttext)
        return s

    def clear(self):
        self.thumbList = []
        self.thumbDict = {}
        self.rebuild_thumbs()
        
    def delete_channel(self, viewer, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name
        # TODO: delete thumbs for this channel!
        self.logger.info("TODO: delete thumbs for channel '%s'" % (
            chname))
        
    def __str__(self):
        return 'thumbs'
    
#END
