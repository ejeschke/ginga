#
# FBrowser.py -- File Browser plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os, glob
import stat, time

from ginga.misc import Bunch
from ginga import GingaPlugin

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga import AstroImage


class FBrowser(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(FBrowser, self).__init__(fv, fitsimage)

        self.keywords = ['OBJECT', 'UT']
        self.columns = [('Name', 'name'),
                        ('Size', 'st_size'),
                        ('Mode', 'st_mode'),
                        ('Last Changed', 'st_mtime')
                        ]
        
        self.jumpinfo = []
        homedir = os.environ['HOME']
        self.curpath = os.path.join(homedir, '*')
        self.do_scanfits = False
        self.moving_cursor = False

        # Make icons
        icondir = self.fv.iconpath
        foldericon = os.path.join(icondir, 'folder.png')
        image = QtGui.QImage(foldericon)
        pixmap = QtGui.QPixmap.fromImage(image)
        self.folderpb = QtGui.QIcon(pixmap)
        fileicon = os.path.join(icondir, 'file.png')
        image = QtGui.QImage(fileicon)
        pixmap = QtGui.QPixmap.fromImage(image)
        self.filepb = QtGui.QIcon(pixmap)
        fitsicon = os.path.join(icondir, 'fits.png')
        image = QtGui.QImage(fitsicon)
        pixmap = QtGui.QPixmap.fromImage(image)
        
        self.fitspb = QtGui.QIcon(pixmap)


    def build_gui(self, container):

        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(vbox)

        # create the table
        table = QtGui.QTableWidget()
        table.setShowGrid(False)
        table.verticalHeader().hide()
        table.setColumnCount(len(self.columns))
        col = 0
        for hdr, kwd in self.columns:
            item = QtGui.QTableWidgetItem(hdr)
            table.setHorizontalHeaderItem(col, item)
            col += 1

        vbox.addWidget(table, stretch=1)
        table.itemDoubleClicked.connect(self.itemclicked_cb)
        self.treeview = table
        
        self.entry = QtGui.QLineEdit()
        vbox.addWidget(self.entry, stretch=0, alignment=QtCore.Qt.AlignTop)
        self.entry.returnPressed.connect(self.browse_cb)

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

        container.addWidget(widget, stretch=1)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True

    def file_icon(self, bnch):
        if bnch.type == 'dir':
            pb = self.folderpb
        elif bnch.type == 'fits':
            pb = self.fitspb
        else:
            pb = self.filepb
        return pb

    def open_file(self, path):
        self.logger.debug("path: %s" % (path))

        if path == '..':
            curdir, curglob = os.path.split(self.curpath)
            path = os.path.join(curdir, path, curglob)
            
        if os.path.isdir(path):
            path = os.path.join(path, '*')
            self.browse(path)

        elif os.path.exists(path):
            self.fv.load_file(path)

        else:
            self.browse(path)

    def get_info(self, path):
        dirname, filename = os.path.split(path)
        name, ext = os.path.splitext(filename)
        ftype = 'file'
        if os.path.isdir(path):
            ftype = 'dir'
        elif os.path.islink(path):
            ftype = 'link'
        elif ext.lower() == '.fits':
            ftype = 'fits'

        filestat = os.stat(path)
        bnch = Bunch.Bunch(path=path, name=filename, type=ftype,
                           st_mode=filestat.st_mode, st_size=filestat.st_size,
                           st_mtime=filestat.st_mtime)
        return bnch
        
    def browse(self, path):
        self.logger.debug("path: %s" % (path))
        if os.path.isdir(path):
            dirname = path
            globname = None
        else:
            dirname, globname = os.path.split(path)
        dirname = os.path.abspath(dirname)
        if not globname:
            globname = '*'
        path = os.path.join(dirname, globname)

        # Make a directory listing
        self.logger.debug("globbing path: %s" % (path))
        filelist = list(glob.glob(path))
        filelist.sort(key=str.lower)
        filelist.insert(0, os.path.join(dirname, '..'))

        self.jumpinfo = map(self.get_info, filelist)
        self.curpath = path
        self.entry.setText(path)

        if self.do_scanfits:
            self.scan_fits()
            
        self.makelisting()

    def makelisting(self):
        table = self.treeview
        table.clearContents()
        row = 0
        table.setRowCount(len(self.jumpinfo))

        table.setSortingEnabled(True)
        for bnch in self.jumpinfo:
            item1 = QtGui.QTableWidgetItem(bnch.name)
            icon = self.file_icon(bnch)
            item1.setIcon(icon)
            item1.setFlags(item1.flags() & ~QtCore.Qt.ItemIsEditable)
            item2 = QtGui.QTableWidgetItem(str(bnch.st_size))
            item2.setFlags(item2.flags() & ~QtCore.Qt.ItemIsEditable)
            item3 = QtGui.QTableWidgetItem(oct(bnch.st_mode))
            item3.setFlags(item2.flags() & ~QtCore.Qt.ItemIsEditable)
            item4 = QtGui.QTableWidgetItem(time.ctime(bnch.st_mtime))
            item4.setFlags(item2.flags() & ~QtCore.Qt.ItemIsEditable)
            table.setItem(row, 0, item1)
            table.setItem(row, 1, item2)
            table.setItem(row, 2, item3)
            table.setItem(row, 3, item4)
            row += 1
        #table.setSortingEnabled(True)
        table.resizeColumnsToContents()
            
    def scan_fits(self):
        for bnch in self.jumpinfo:
            if not bnch.type == 'fits':
                continue
            if not bnch.has_key('kwds'):
                try:
                    in_f = AstroImage.pyfits.open(bnch.path, 'readonly')
                    try:
                        kwds = {}
                        for kwd in self.keywords:
                            kwds[kwd] = in_f[0].header.get(kwd, 'N/A')
                        bnch.kwds = kwds
                    finally:
                        in_f.close()
                except Exception, e:
                    continue

    def refresh(self):
        self.browse(self.curpath)
        
    def scan_headers(self):
        self.browse(self.curpath)
        
    def browse_cb(self):
        path = str(self.entry.text()).strip()
        self.browse(path)
        
    def itemclicked_cb(self, item):
        row = item.row()
        item2 = self.treeview.item(row, 0)
        name = str(item2.text())
        if name != '..':
            curdir, curglob = os.path.split(self.curpath)
            path = os.path.join(curdir, name)
        else:
            path = name
        self.open_file(path)
        
    def make_thumbs(self):
        path = self.curpath
        self.logger.info("Generating thumbnails for '%s'..." % (
            path))
        filelist = glob.glob(path)
        filelist.sort(key=str.lower)

        # find out our channel
        chname = self.fv.get_channelName(self.fitsimage)
        
        # Invoke the method in this channel's Thumbs plugin
        # TODO: don't expose gpmon!
        rsobj = self.fv.gpmon.getPlugin('Thumbs')
        self.fv.nongui_do(rsobj.make_thumbs, chname, filelist)

    def start(self):
        self.win = None
        self.browse(self.curpath)

    def pause(self):
        pass
    
    def resume(self):
        pass
    
    def stop(self):
        pass
        
    def redo(self):
        return True
    
    def __str__(self):
        return 'fbrowser'
    
#END
