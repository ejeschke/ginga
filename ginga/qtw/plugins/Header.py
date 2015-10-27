#
# Header.py -- FITS Header plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch
from ginga.misc.plugins.HeaderBase import HeaderBase
import ginga.util.six as six

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp


class Header(HeaderBase):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Header, self).__init__(fv)

        self._image = None

    def build_gui(self, container):
        nb = QtHelp.StackedWidget()
        self.nb = nb
        cw = container.get_widget()
        cw.addWidget(nb, stretch=0)

    def _create_header_window(self, info):
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
        if QtHelp.have_pyqt5:
            # NOTE: this makes a terrible hit on performance--DO NOT USE!
            #vh.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
            vh.setSectionResizeMode(QtGui.QHeaderView.Fixed)
        else:
            # NOTE: this makes a terrible hit on performance--DO NOT USE!
            #vh.setResizeMode(QtGui.QHeaderView.ResizeToContents)
            vh.setResizeMode(QtGui.QHeaderView.Fixed)
        vh.setDefaultSectionSize(18)
        # Hide vertical header
        vh.setVisible(False)

        vbox.addWidget(table, stretch=1)

        # create sort toggle
        cb = QtGui.QCheckBox("Sortable")
        cb.stateChanged.connect(lambda tf: self.set_sortable_cb(info))
        hbox = QtHelp.HBox()
        hbox.addWidget(cb, stretch=0)
        vbox.addWidget(hbox, stretch=0)

        # toggle sort
        if self.settings.get('sortable', False):
            cb.setCheckState(QtCore.Qt.Checked)

        info.setvals(widget=widget, table=table, sortw=cb)
        return widget

    def set_header(self, info, image):
        if self._image == image:
            # we've already handled this header
            return
        self.logger.debug("setting header")
        header = image.get_header()
        table = info.table

        model = HeaderTableModel(self.columns, header)
        table.setModel(model)
        selectionModel = QtHelp.QItemSelectionModel(model, table)
        table.setSelectionModel(selectionModel)

        # set column width to fit contents
        # NOTE: this makes a terrible hit on performance--DO NOT USE!
        ## table.resizeColumnsToContents()
        ## table.resizeRowsToContents()

        is_sorted = info.sortw.isChecked()
        table.setSortingEnabled(is_sorted)
        self.logger.debug("setting header done ({0})".format(is_sorted))
        self._image = image

    def add_channel(self, viewer, chinfo):
        chname = chinfo.name
        info = Bunch.Bunch(chname=chname)
        sw = self._create_header_window(info)

        self.nb.addTab(sw, chname)
        index = self.nb.indexOf(sw)
        info.setvals(widget=sw)
        self.channel[chname] = info

        fitsimage = chinfo.fitsimage
        fitsimage.set_callback('image-set', self.new_image_cb, info)

    def delete_channel(self, viewer, chinfo):
        chname = chinfo.name
        self.logger.debug("deleting channel %s" % (chname))
        widget = self.channel[chname].widget
        self.nb.removeWidget(widget)
        widget.setParent(None)
        widget.deleteLater()
        self.active = None
        self.info = None
        del self.channel[chname]

    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name

        if self.active != chname:
            widget = self.channel[chname].widget
            index = self.nb.indexOf(widget)
            self.nb.setCurrentIndex(index)
            self.active = chname
            self.info = self.channel[self.active]

        image = fitsimage.get_image()
        if image is None:
            return
        self.set_header(self.info, image)

    def set_sortable_cb(self, info):
        self._image = None
        super(Header, self).set_sortable_cb(info)

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

        if QtHelp.have_pyqt4:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))

        self.header = sorted(self.header, key=sortfn)

        if order == QtCore.Qt.DescendingOrder:
            self.header.reverse()
        if QtHelp.have_pyqt4:
            self.emit(QtCore.SIGNAL("layoutChanged()"))


#END
