#
# Thumbs.py -- Thumbnail plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os

from ginga.qtw import FitsImageQt as FitsImageQt
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.misc.plugins import ThumbsBase
from ginga.qtw import QtHelp
from ginga.misc import Bunch


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

    
class Thumbs(ThumbsBase.ThumbsBase):

    def build_gui(self, container):
        rvbox = container

        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        tg = FitsImageQt.FitsImageQt(logger=self.logger)
        tg.configure(200, 200)
        tg.enable_autozoom('on')
        tg.enable_autocuts('on')
        tg.enable_auto_orient(True)
        tg.set_makebg(False)
        self.thumb_generator = tg

        sw = MyScrollArea()
        sw.setWidgetResizable(True)
        #sw.setEnabled(True)
        sw.thumbs_cb = self.thumbpane_resized_cb

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
        #self.w.thumbs_scroll.connect("size_allocate", self.thumbpane_resized_cb)

        # TODO: should this even have it's own scrolled window?
        rvbox.addWidget(sw, stretch=1)
        sw.show()

        captions = (('Auto scroll', 'checkbutton'),)
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        b.auto_scroll.setToolTip("Scroll the thumbs window when new images arrive")
        autoScroll = self.settings.get('autoScroll', True)
        b.auto_scroll.setChecked(autoScroll)
        rvbox.addWidget(w, stretch=0)


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
        widget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed,
                                               QtGui.QSizePolicy.Fixed))
        bnch = Bunch.Bunch(widget=widget, image=imgwin, layout=vbox,
                           imglbl=imglbl, name=name, imname=name,
                           chname=chname, path=path, pixmap=pixmap)

        self.thumbDict[thumbkey] = bnch
        self.thumbList.append(thumbkey)

        self.w.thumbs.addWidget(widget,
                                self.thumbRowCount, self.thumbColCount)
        self.thumbColCount = (self.thumbColCount + 1) % self.thumbNumCols
        if self.thumbColCount == 0:
            self.thumbRowCount += 1

        #self.w.thumbs.show()
        
        # force scroll to bottom of thumbs, if checkbox is set
        scrollp = self.w.auto_scroll.isChecked()
        if scrollp:
            self.fv.update_pending()
            area = self.w.thumbs_scroll
            area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
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
        

    def thumbpane_resized_cb(self, width, height):
        self.thumbpane_resized(width, height)
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

        self.update_thumbnail(thumbkey, imgwin, name, metadata)

    def update_thumbnail(self, thumbkey, imgwin, name, metadata):
        try:
            bnch = self.thumbDict[thumbkey]
        except KeyError:
            return

        self.logger.debug("generating pixmap.")
        pixmap = QtGui.QPixmap.fromImage(imgwin)
        bnch.imgwin = imgwin
        bnch.pixmap = pixmap
        bnch.imglbl.setPixmap(pixmap)
        bnch.imglbl.repaint()
        self.w.thumbs_w.update()
        self.logger.debug("update finished.")
        
    def __str__(self):
        return 'thumbs'
    
#END
