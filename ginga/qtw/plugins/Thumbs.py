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

from ginga.qtw import ImageViewQt as ImageViewQt
from ginga.qtw.QtHelp import QtGui, QtCore, QPixmap
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

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        self.thumbRowCount = 0

    def build_gui(self, container):
        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        tg = ImageViewQt.ImageViewQt(logger=self.logger)
        tg.configure(200, 200)
        tg.enable_autozoom('on')
        tg.set_autocut_params('zscale')
        tg.enable_autocuts('on')
        tg.enable_auto_orient(True)
        tg.set_makebg(False)
        tg.enable_overlays(False)
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
        cw = container.get_widget()
        cw.addWidget(sw, stretch=1)
        sw.show()

        captions = (('Auto scroll', 'checkbutton', 'Clear', 'button'),)
        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        b.auto_scroll.setToolTip("Scroll the thumbs window when new images arrive")
        b.clear.setToolTip("Remove all current thumbnails")
        b.clear.clicked.connect(self.clear)
        autoScroll = self.settings.get('autoScroll', True)
        b.auto_scroll.setChecked(autoScroll)
        cw.addWidget(w, stretch=0)

    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path,
                         thumbpath, metadata, image_loader):
        pixmap = QPixmap.fromImage(imgwin)
        imglbl = MyLabel()
        imglbl.setPixmap(pixmap)
        imglbl.thumbs_cb = lambda: self.load_file(thumbkey, chname, name, path,
                                                  image_loader)

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
                           chname=chname, path=path, thumbpath=thumbpath,
                           pixmap=pixmap)

        with self.thmblock:
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

    def clearWidget(self):
        """Clears the thumbnail display widget of all thumbnails, but does
        not remove them from the thumbDict or thumbList.
        """
        with self.thmblock:
            # Remove widgets from grid
            for thumbkey in self.thumbList:
                bnch = self.thumbDict[thumbkey]
                self.w.thumbs.removeWidget(bnch.widget)
                bnch.widget.setParent(None)
                bnch.widget.deleteLater()
        self.w.thumbs_w.update()
        
    def reorder_thumbs(self):
        with self.thmblock:
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
        except Exception as e:
            self.logger.error("Couldn't determine OBJECT name: %s" % str(e))

        uttext = 'UT: UNKNOWN'
        try:
            uttext = 'UT: ' + metadata['UT']
        except Exception as e:
            self.logger.error("Couldn't determine UT: %s" % str(e))

        chname, path = thumbkey

        s = "%s\n%s\n%s\n%s" % (chname, name, objtext, uttext)
        return s

    def update_thumbnail(self, thumbkey, imgwin, name, metadata):
        with self.thmblock:
            try:
                bnch = self.thumbDict[thumbkey]
            except KeyError:
                return

            self.logger.debug("generating pixmap.")
            pixmap = QPixmap.fromImage(imgwin)
            bnch.imgwin = imgwin
            bnch.pixmap = pixmap
            bnch.imglbl.setPixmap(pixmap)
            bnch.imglbl.repaint()
            self.w.thumbs_w.update()
        self.logger.debug("update finished.")
        
    def __str__(self):
        return 'thumbs'
    
#END
