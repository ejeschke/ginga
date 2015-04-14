#
# FBrowser.py -- File Browser plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import stat, time

from ginga.misc.plugins import FBrowserBase
from ginga.qtw.QtHelp import QtGui, QtCore, QImage, QPixmap, QIcon
from ginga.qtw import QtHelp


class FBrowser(FBrowserBase.FBrowserBase):

    def __init__(self, fv, fitsimage):
        # superclass is common subset outside of toolkits
        super(FBrowser, self).__init__(fv, fitsimage)

        # Make icons
        icondir = self.fv.iconpath
        foldericon = os.path.join(icondir, 'folder.png')
        image = QImage(foldericon)
        pixmap = QPixmap.fromImage(image)
        self.folderpb = QIcon(pixmap)
        fileicon = os.path.join(icondir, 'file.png')
        image = QImage(fileicon)
        pixmap = QPixmap.fromImage(image)
        self.filepb = QIcon(pixmap)
        fitsicon = os.path.join(icondir, 'fits.png')
        image = QImage(fitsicon)
        pixmap = QPixmap.fromImage(image)
        
        self.fitspb = QIcon(pixmap)


    def build_gui(self, container):

        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(vbox)

        # create the table
        #table = QtGui.QTableWidget()
        #table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        #table.setDragEnabled(True)
        table = DragTable(plugin=self)
        table.setShowGrid(False)
        table.verticalHeader().hide()
        table.setColumnCount(len(self.columns))
        col = 0
        self._name_idx = 0
        for hdr, attrname in self.columns:
            item = QtGui.QTableWidgetItem(hdr)
            table.setHorizontalHeaderItem(col, item)
            if attrname == 'name':
                self._name_idx = col
            col += 1

        vbox.addWidget(table, stretch=1)
        table.itemDoubleClicked.connect(self.itemclicked_cb)
        self.treeview = table
        
        self.entry = QtGui.QLineEdit()
        vbox.addWidget(self.entry, stretch=0, alignment=QtCore.Qt.AlignTop)
        self.entry.returnPressed.connect(self.browse_cb)

        hbox = QtHelp.HBox()
        btn = QtGui.QPushButton("Load")
        btn.clicked.connect(lambda w: self.load_cb())
        hbox.addWidget(btn, stretch=0)
        btn = QtGui.QPushButton("Save Image As")
        hbox.addWidget(btn, stretch=0)
        self.entry2 = QtGui.QLineEdit()
        hbox.addWidget(self.entry2, stretch=1)
        vbox.addWidget(hbox, stretch=0, alignment=QtCore.Qt.AlignTop)
        self.entry2.returnPressed.connect(self.save_as_cb)
        btn.clicked.connect(lambda w: self.save_as_cb())

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("Refresh")
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("Make Thumbs")
        btn.clicked.connect(self.make_thumbs)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vbox.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        cw = container.get_widget()
        cw.addWidget(widget, stretch=1)

    def load_cb(self):
        curdir, curglob = os.path.split(self.curpath)
        sm = self.treeview.selectionModel()
        paths = [ os.path.join(curdir,
                               self.treeview.model().data(row, self._name_idx))
                  for row in sm.selectedRows() ]
        #self.fv.dragdrop(self.fitsimage, paths)
        self.fv.gui_do(self.fitsimage.make_callback, 'drag-drop',
                       paths)
        
    def makelisting(self, path):
        self.entry.setText(path)

        table = self.treeview
        table.clearContents()
        row = 0
        table.setRowCount(len(self.jumpinfo))

        table.setSortingEnabled(True)
        for bnch in self.jumpinfo:
            col = 0
            for colname, attrname in self.columns:
                item = QtGui.QTableWidgetItem(str(bnch[attrname]))
                # special handling for name--adds an icon
                if attrname == 'name':
                    icon = self.file_icon(bnch)
                    item.setIcon(icon)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                table.setItem(row, col, item)
                col += 1

            row += 1
        #table.setSortingEnabled(True)
        table.resizeColumnsToContents()

    def get_path_at_row(self, row):
        item2 = self.treeview.item(row, self._name_idx)
        name = str(item2.text())
        if name != '..':
            curdir, curglob = os.path.split(self.curpath)
            path = os.path.join(curdir, name)
        else:
            path = name
        return path

    def itemclicked_cb(self, item):
        path = self.get_path_at_row(item.row())
        self.open_file(path)
        
    def browse_cb(self):
        path = str(self.entry.text()).strip()
        self.browse(path)
        
    def save_as_cb(self):
        path = str(self.entry2.text()).strip()
        if not path.startswith('/'):
            path = os.path.join(self.curpath, path)

        image = self.fitsimage.get_image()
        self.fv.error_wrap(image.save_as_file, path)
        
    def __str__(self):
        return 'fbrowser'


class DragTable(QtGui.QTableWidget):
    # This class exists only to let us drag and drop files from the
    # file pane into the Ginga widget.
    
    def __init__(self, parent=None, plugin=None):
        super(DragTable, self).__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.plugin = plugin

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("text/uri-list"):
            event.setDropAction(QtCore.Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def startDrag(self, event):
        indices = self.selectedIndexes()
        selected = set()
        for index in indices:
            selected.add(index.row())

        urls = []
        for row in selected:
            path = "file://" + self.plugin.get_path_at_row(row)
            url = QtCore.QUrl(path)
            urls.append(url)

        mimeData = QtCore.QMimeData()
        mimeData.setUrls(urls)
        drag = QtHelp.QDrag(self)
        drag.setMimeData(mimeData)
        ## pixmap = QPixmap(":/drag.png")
        ## drag.setHotSpot(QPoint(pixmap.width()/3, pixmap.height()/3))
        ## drag.setPixmap(pixmap)
        if QtHelp.have_pyqt5:
            result = drag.exec_(QtCore.Qt.MoveAction)
        else:
            result = drag.start(QtCore.Qt.MoveAction)

    def mouseMoveEvent(self, event):
        self.startDrag(event)
        
#END
