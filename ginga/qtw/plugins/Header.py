#
# Header.py -- FITS Header plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.misc import Bunch

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp


class Header(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Header, self).__init__(fv)

        self.channel = {}
        self.active = None
        self.info = None

        self.columns = [('Keyword', 'key'),
                        ('Value', 'value'),
                        ('Comment', 'comment'),
                        ]
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.set_callback('active-image', self.focus_cb)
        

    def build_gui(self, container):
        nb = QtHelp.StackedWidget()
        self.nb = nb
        container.addWidget(nb, stretch=0)

    def _create_header_window(self):
        widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(2, 2, 2, 2)
        widget.setLayout(vbox)

        table = QtGui.QTableView()
        self.table = table
        table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        table.setShowGrid(False)
        vh = table.verticalHeader()
        # Hack to make the rows in a TableView all have a
        # reasonable height for the data
        vh.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        # Hide vertical header
        vh.setVisible(False)

        vbox.addWidget(table, stretch=1)
        return widget, table

    def set_header(self, table, image):
        header = image.get_header()

        model = HeaderTableModel(self.columns, header)
        table.setModel(model)
        selectionModel = QtGui.QItemSelectionModel(model, table)
        table.setSelectionModel(selectionModel)
        
        # set column width to fit contents
        table.resizeColumnsToContents()
        table.resizeRowsToContents()

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

    def start(self):
        names = self.fv.get_channelNames()
        for name in names:
            chinfo = self.fv.get_channelInfo(name)
            self.add_channel(self.fv, chinfo)
        
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


class HeaderTableModel(QtCore.QAbstractTableModel):

    def __init__(self, columns, header):
        super(HeaderTableModel, self).__init__(None)

        self.columns = columns
        self.header = []
        # Copy cards from header into a local list
        # TODO: what if the header changes underneath us?
        for key in header.keys():
            self.header.append(header.get_card(key))

    def rowCount(self, parent): 
        return len(self.header) 
 
    def columnCount(self, parent): 
        return len(self.columns) 
 
    def data(self, index, role): 
        if not index.isValid(): 
            return None 
        elif role != QtCore.Qt.DisplayRole: 
            return None

        card = self.header[index.row()]
        field = self.columns[index.column()][1]
        return str(card[field])

    def headerData(self, col, orientation, role):
        if (orientation == QtCore.Qt.Horizontal) and \
               (role == QtCore.Qt.DisplayRole):
            return self.columns[col][0]
        
        # Hack to make the rows in a TableView all have a
        # reasonable height for the data
        elif (role == QtCore.Qt.SizeHintRole) and \
                 (orientation == QtCore.Qt.Vertical):
            return 1
        return None

    def sort(self, Ncol, order):
        """Sort table by given column number.
        """
        def sortfn(card):
            field = self.columns[Ncol][1]
            return card[field]
        
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))

        self.header = sorted(self.header, key=sortfn)        

        if order == QtCore.Qt.DescendingOrder:
            self.header.reverse()
        self.emit(QtCore.SIGNAL("layoutChanged()"))
        
    
#END
