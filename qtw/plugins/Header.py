#
# Header.py -- FITS Header plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import GingaPlugin
import Bunch

from QtHelp import QtGui, QtCore
import QtHelp


class Header(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Header, self).__init__(fv)

        self.channel = {}
        self.active = None
        self.info = None

        self.columns = [('Keyword', 'kwd'),
                        ('Value', 'value'),
                        ('Comment', 'comment'),
                        ]
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.set_callback('active-image', self.focus_cb)
        

    def initialize(self, container):
        nb = QtHelp.StackedWidget()
        self.nb = nb
        container.addWidget(nb, stretch=0)

    def _create_header_window(self):
        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(vbox)

        table = QtGui.QTableWidget()
        table.setColumnCount(len(self.columns))
        col = 0
        for hdr, kwd in self.columns:
            item = QtGui.QTableWidgetItem(hdr)
            table.setHorizontalHeaderItem(col, item)
            col += 1

        vbox.addWidget(table, stretch=1)
        return widget, table

    def set_header(self, table, image):
        header = image.get_header()
        # Update the header info
        table.clearContents()
        keyorder = image.get('keyorder', header.keys())
        row = 0
        table.setRowCount(len(keyorder))

        table.setSortingEnabled(False)
        for key in keyorder:
            if header.has_key(key):
                val = str(header[key])
                bnch = Bunch.Bunch(kwd=key, value=val, comment='')
                item1 = QtGui.QTableWidgetItem(key)
                item1.setFlags(item1.flags() & ~QtCore.Qt.ItemIsEditable)
                item2 = QtGui.QTableWidgetItem(val)
                item2.setFlags(item2.flags() & ~QtCore.Qt.ItemIsEditable)
                table.setItem(row, 0, item1)
                table.setItem(row, 1, item2)
            row += 1
        table.setSortingEnabled(True)

    def add_channel(self, viewer, chinfo):
        sw, tv = self._create_header_window()
        chname = chinfo.name

        self.nb.addTab(sw, unicode(chname))
        index = self.nb.indexOf(sw)
        info = Bunch.Bunch(widget=sw, table=tv,
                           nbindex=index)
        self.channel[chname] = info

        fitsimage = chinfo.fitsimage
        fitsimage.set_callback('image-set', self.new_image_cb, tv)

    def delete_channel(self, viewer, chinfo):
        self.logger.debug("TODO: delete channel %s" % (chinfo.name))

    def new_image_cb(self, fitsimage, image, tv):
        self.set_header(tv, image)
        
    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name

        if self.active != chname:
            index = self.channel[chname].nbindex
            self.nb.setCurrentIndex(index)
            self.active = chname
            self.info = self.channel[self.active]

        image = fitsimage.get_image()
        self.set_header(self.info.table, image)
        
    def __str__(self):
        return 'header'
    
#END
