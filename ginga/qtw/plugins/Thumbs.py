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

from ginga.qtw import ImageViewCanvasQt
from ginga.qtw.QtHelp import QtGui, QtCore, QPixmap, QApplication
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
        self.event_type = None

        if buttons & QtCore.Qt.LeftButton:
            self.drag_start_position = event.pos()
            self.event_type = 'click'

        ## elif buttons & QtCore.Qt.RightButton:
        ##     self.context_menu_cb()

    def mouseMoveEvent(self, event):

        if event.buttons() != QtCore.Qt.LeftButton:
            return

        # only consider this a drag if user has moved a certain amount
        # away from the press position
        if ((event.pos() - self.drag_start_position).manhattanLength() <
            QApplication.startDragDistance()):
            return

        # prepare formatted possibilities on drop
        mimeData = QtCore.QMimeData()
        chname, name, path = self._dragdata
        data = "%s||%s||%s" % (chname, name, path)
        mimeData.setData("text/thumb", data)
        mimeData.setData("text/plain", path)

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(self.pixmap())
        drag.setHotSpot(event.pos() - self.rect().topLeft())

        self.event_type = 'drag'
        #dropAction = drag.start(QtCore.Qt.CopyAction | QtCore.Qt.MoveAction)
        dropAction = drag.start(QtCore.Qt.CopyAction)

    def mouseReleaseEvent(self, event):
        if self.event_type == 'click':
            self.thumbs_cb()
        ## elif buttons & QtCore.Qt.RightButton:
        ##     self.context_menu_cb()

class Thumbs(ThumbsBase.ThumbsBase):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Thumbs, self).__init__(fv)

        self.thumbRowCount = 0

    def build_gui(self, container):
        width, height = 300, 300
        cm, im = self.fv.cm, self.fv.im

        tg = ImageViewCanvasQt.ImageViewCanvas(logger=self.logger)
        tg.configure_window(200, 200)
        tg.enable_autozoom('on')
        tg.set_autocut_params('zscale')
        tg.enable_autocuts('override')
        tg.enable_auto_orient(True)
        tg.defer_redraw = False
        tg.set_bg(0.7, 0.7, 0.7)
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
        auto_scroll = self.settings.get('auto_scroll', True)
        b.auto_scroll.setChecked(auto_scroll)
        cw.addWidget(w, stretch=0)
        self.gui_up = True

    def insert_thumbnail(self, imgwin, thumbkey, thumbname, chname, name, path,
                         thumbpath, metadata, image_future):
        pixmap = QPixmap.fromImage(imgwin)
        imglbl = MyLabel()
        imglbl.setPixmap(pixmap)
        imglbl._dragdata = (chname, name, path)
        # set the load callback
        imglbl.thumbs_cb = lambda: self.load_file(thumbkey, chname, name, path,
                                                  image_future)
        # make a context menu
        self._mk_context_menu(imglbl, thumbkey, chname, name, path,
                              image_future)
        # make a tool tip
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
                           pixmap=pixmap, image_future=image_future)

        with self.thmblock:
            self.thumbDict[thumbkey] = bnch
            self.thumbList.append(thumbkey)

            sort_order = self.settings.get('sort_order', None)
            if sort_order:
                self.thumbList.sort()
                self.reorder_thumbs()
                return

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
        self.logger.debug("added thumb for %s" % (name))

    def clearWidget(self):
        """
        Clears the thumbnail display widget of all thumbnails, but does
        not remove them from the thumbDict or thumbList.
        """
        with self.thmblock:
            # Remove widgets from grid
            for thumbkey in self.thumbList:
                bnch = self.thumbDict[thumbkey]
                self.w.thumbs.removeWidget(bnch.widget)
                bnch.widget.setParent(None)
        self.w.thumbs_w.update()

    def reorder_thumbs(self):
        self.logger.debug("Reordering thumb grid")
        with self.thmblock:
            # Remove widgets from grid
            for thumbkey in self.thumbList:
                bnch = self.thumbDict[thumbkey]
                try:
                    self.w.thumbs.removeWidget(bnch.widget)
                except:
                    # widget may already be removed by a clearWidget()
                    pass

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
        self.logger.debug("Reordering done")


    def thumbpane_resized_cb(self, width, height):
        self.thumbpane_resized(width, height)
        return False

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

    def _mk_context_menu(self, lbl, thumbkey, chname, name, path,
                         image_future):
        lbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        menu = QtGui.QMenu()
        item = QtGui.QAction("Display", menu)
        item.triggered.connect(lambda: self.load_file(thumbkey, chname, name,
                                                      path, image_future))
        menu.addAction(item)
        menu.addSeparator()
        item = QtGui.QAction("Remove", menu)
        item.triggered.connect(lambda: self.fv.remove_image_by_name(chname, name, impath=path))
        menu.addAction(item)

        def on_context_menu(point):
            menu.exec_(lbl.mapToGlobal(point))

        lbl.customContextMenuRequested.connect(on_context_menu)

    def update_thumbnail(self, thumbkey, imgwin, name, metadata):
        with self.thmblock:
            try:
                bnch = self.thumbDict[thumbkey]
            except KeyError:
                self.logger.debug("No thumb found for %s; not updating thumbs" % (
                    str(thumbkey)))
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
