#
# Catalogs.py -- Catalogs plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.qtw import ColorBar
from ginga.misc import Bunch
from ginga.misc.plugins import CatalogsBase

class Catalogs(CatalogsBase.CatalogsBase):

    def __init__(self, fv, fitsimage):
        super(Catalogs, self).__init__(fv, fitsimage)

    def build_gui(self, container, future=None):
        vbox1 = QtHelp.VBox()

        msgFont = self.fv.getFont("sansFont", 14)
        tw = QtGui.QLabel()
        tw.setFont(msgFont)
        tw.setWordWrap(True)
        self.tw = tw

        fr = QtHelp.Frame("Instructions")
        fr.addWidget(tw, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        nb = QtHelp.TabWidget()
        nb.setTabPosition(QtGui.QTabWidget.South)
        nb.setUsesScrollButtons(True)
        self.w.nb = nb
        #vbox1.addWidget(nb, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox1.addWidget(nb, stretch=1)

        vbox0 = QtHelp.VBox()

        hbox = QtHelp.HBox()
        hbox.setSpacing(4)
        vbox0.addWidget(hbox, stretch=1, alignment=QtCore.Qt.AlignTop)

        vbox = QtHelp.VBox()
        fr = QtHelp.Frame(" Image Server ")
        fr.addWidget(vbox, stretch=1, alignment=QtCore.Qt.AlignTop)
        hbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignLeft)

        captions = (('Server', 'xlabel'),
                    ('@Server', 'combobox'),
                    ('Use DSS channel', 'checkbutton'),
                    ('Get Image', 'button'))
        w, b = QtHelp.build_info(captions)
        self.w.update(b)
        self.w.get_image.clicked.connect(self.getimage_cb)
        self.w.use_dss_channel.setChecked(self.use_dss_channel)
        self.w.use_dss_channel.stateChanged.connect(self.use_dss_channel_cb)

        vbox.addWidget(w, stretch=0, alignment=QtCore.Qt.AlignTop)

        self.w.img_params = QtHelp.StackedWidget()
        vbox.addWidget(self.w.img_params, stretch=1,
                       alignment=QtCore.Qt.AlignTop)

        combobox = self.w.server
        index = 0
        self.image_server_options = self.fv.imgsrv.getServerNames(kind='image')
        for name in self.image_server_options:
            combobox.addItem(name)
            index += 1
        index = 0
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.setup_params_image)
        if len(self.image_server_options) > 0:
            self.setup_params_image(index, redo=False)

        vbox = QtHelp.VBox()
        fr = QtHelp.Frame(" Catalog Server ")
        fr.addWidget(vbox, stretch=1, alignment=QtCore.Qt.AlignTop)
        hbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignLeft)

        captions = (('Server', 'xlabel'),
                    ('@Server', 'combobox'),
                    ('Limit stars to area', 'checkbutton'),
                    ('Search', 'button'))
        w, self.w2 = QtHelp.build_info(captions)
        self.w2.search.clicked.connect(self.getcatalog_cb)
        self.w2.limit_stars_to_area.setChecked(self.limit_stars_to_area)
        self.w2.limit_stars_to_area.stateChanged.connect(self.limit_area_cb)

        vbox.addWidget(w, stretch=0, alignment=QtCore.Qt.AlignTop)

        self.w2.cat_params = QtHelp.StackedWidget()
        vbox.addWidget(self.w2.cat_params, stretch=1,
                       alignment=QtCore.Qt.AlignTop)

        combobox = self.w2.server
        index = 0
        self.catalog_server_options = self.fv.imgsrv.getServerNames(kind='catalog')
        for name in self.catalog_server_options:
            combobox.addItem(name)
            index += 1
        index = 0
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.setup_params_catalog)
        if len(self.catalog_server_options) > 0:
            self.setup_params_catalog(index, redo=False)

        btns = QtHelp.HBox()
        btns.setSpacing(5)

        btn = QtGui.QRadioButton("Rectangle")
        if self.drawtype == 'rectangle':
            btn.setChecked(True)
        btn.toggled.connect(lambda tf: self.set_drawtype_cb(tf, 'rectangle'))
        btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QRadioButton("Circle")
        if self.drawtype == 'circle':
            btn.setChecked(True)
        btn.toggled.connect(lambda tf: self.set_drawtype_cb(tf, 'circle'))
        btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("Entire image")
        btn.clicked.connect(self.setfromimage)
        btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox0.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignTop)

        self.w.params = vbox0

        sw = QtGui.QScrollArea()
        sw.setWidgetResizable(True)
        sw.setWidget(vbox0)

        nb.addTab(sw, "Params")

        vbox = QtHelp.VBox()
        self.table = CatalogListing(self.logger, vbox)

        hbox = QtHelp.HBox()
        adj = QtGui.QScrollBar(QtCore.Qt.Horizontal)
        adj.setRange(0, 1000)
        adj.setSingleStep(1)
        adj.setPageStep(10)
        #adj.setMaximum(1000)
        adj.setValue(0)
        #adj.resize(200, -1)
        adj.setTracking(True)
        adj.setToolTip("Choose subset of stars plotted")
        self.w.plotgrp = adj
        adj.valueChanged.connect(self.plot_pct_cb)
        hbox.addWidget(adj, stretch=1)

        sb = QtGui.QSpinBox()
        sb.setRange(10, self.plot_max)
        sb.setValue(self.plot_limit)
        sb.setSingleStep(10)
        adj.setPageStep(100)
        sb.setWrapping(False)
        self.w.plotnum = sb
        sb.setToolTip("Adjust size of subset of stars plotted")
        sb.valueChanged.connect(self.plot_limit_cb)
        hbox.addWidget(sb, stretch=0)

        vbox.addWidget(hbox, stretch=0)
        self.w.listing = vbox
        nb.addTab(vbox, "Listing")

        btns = QtHelp.HBox()
        btns.setSpacing(3)
        #btns.set_child_size(15, -1)
        self.w.buttons = btns

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)

        if future:
            btn = QtGui.QPushButton('Ok')
            btn.clicked.connect(lambda w: self.ok())
            btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
            btn = QtGui.QPushButton('Cancel')
            btn.clicked.connect(lambda w: self.cancel())
            btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vbox1.addWidget(btns, stretch=0)

        cw = container.get_widget()
        cw.addWidget(vbox1, stretch=1)


    def limit_area_cb(self, tf):
        self.limit_stars_to_area = (tf != 0)
        return True

    def use_dss_channel_cb(self, tf):
        self.use_dss_channel = (tf != 0)
        return True

    def plot_pct_cb(self):
        val = self.w.plotgrp.value()
        self.plot_start = int(val)
        self.replot_stars()
        return True

    def _update_plotscroll(self):
        num_stars = len(self.starlist)
        if num_stars > 0:
            adj = self.w.plotgrp
            page_size = self.plot_limit
            self.plot_start = min(self.plot_start, num_stars-1)
            adj.setRange(0, num_stars)
            adj.setSingleStep(1)
            adj.setPageStep(page_size)

        self.replot_stars()

    def plot_limit_cb(self):
        val = self.w.plotnum.value()
        self.plot_limit = int(val)
        self._update_plotscroll()
        return True

    def set_message(self, msg):
        self.tw.setText(msg)

    def _raise_tab(self, w):
        self.w.nb.setCurrentWidget(w)

    def _get_cbidx(self, w):
        return w.currentIndex()

    def _setup_params(self, obj, container):
        params = obj.getParams()
        captions = []
        paramList = sorted(params.values(), key=lambda b: b.order)
        for bnch in paramList:
            text = bnch.name
            if 'label' in bnch:
                text = bnch.label
            #captions.append((text, 'entry'))
            captions.append((text, 'xlabel', '@'+bnch.name, 'entry'))

        # TODO: put RA/DEC first, and other stuff not in random orders
        w, b = QtHelp.build_info(captions)

        # remove old widgets
        old_w = container.currentWidget()
        if old_w is not None:
            container.removeWidget(old_w)

        # add new widgets
        container.insertWidget(0, w)
        return b

    def setup_params_image(self, index, redo=True):
        key = self.image_server_options[index]

        # Get the parameter list and adjust the widget
        obj = self.fv.imgsrv.getImageServer(key)
        b = self._setup_params(obj, self.w.img_params)
        self.image_server_params = b

        if redo:
            self.redo()

    def setup_params_catalog(self, index, redo=True):
        key = self.catalog_server_options[index]

        # Get the parameter list and adjust the widget
        obj = self.fv.imgsrv.getCatalogServer(key)
        b = self._setup_params(obj, self.w2.cat_params)
        self.catalog_server_params = b

        if redo:
            self.redo()

    def _update_widgets(self, d):
        for bnch in (self.image_server_params,
                     self.catalog_server_params):
            if bnch is not None:
                for key in bnch.keys():
                    if key in d:
                        bnch[key].setText(str(d[key]))

    def get_params(self, bnch):
        params = {}
        for key in bnch.keys():
            params[key] = str(bnch[key].text())
        return params

    def instructions(self):
        self.set_message("""TBD.""")

    def set_drawtype_cb(self, tf, drawtype):
        if tf:
            self.drawtype = drawtype
            self.canvas.set_drawtype(self.drawtype, color='cyan',
                                     linestyle='dash')

    def __str__(self):
        return 'catalogs'


class CatalogListing(CatalogsBase.CatalogListingBase):

    def _build_gui(self, container):
        self.mframe = container

        vbox = QtHelp.VBox()

        # create the table
        table = QtGui.QTableView()
        self.table = table
        table.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        table.setShowGrid(False)
        vh = table.verticalHeader()
        # Hack to make the rows in a TableView all have a
        # reasonable height for the data
        if QtHelp.have_pyqt5:
            vh.setSectionResizeMode(QtGui.QHeaderView.ResizeToContents)
        else:
            vh.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        # Hide vertical header
        vh.setVisible(False)

        vbox.addWidget(table, stretch=1)

        self.cbar = ColorBar.ColorBar(self.logger)
        self.cbar.set_cmap(self.cmap)
        self.cbar.set_imap(self.imap)
        #self.cbar.set_size_request(-1, 20)
        rgbmap = self.cbar.get_rgbmap()
        rgbmap.add_callback('changed', lambda *args: self.replot_stars())

        vbox.addWidget(self.cbar, stretch=0)

        btns = QtHelp.HBox()
        btns.setSpacing(5)

        combobox = QtHelp.ComboBox()
        options = []
        index = 0
        for name in self.cmap_names:
            options.append(name)
            combobox.addItem(name)
            index += 1
        cmap_name = self.magcmap
        try:
            index = self.cmap_names.index(cmap_name)
        except Exception:
            index = self.cmap_names.index('gray')
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_cmap_cb)
        self.btn['cmap'] = combobox
        btns.addWidget(combobox, stretch=0, alignment=QtCore.Qt.AlignRight)

        combobox = QtHelp.ComboBox()
        options = []
        index = 0
        for name in self.imap_names:
            options.append(name)
            combobox.addItem(name)
            index += 1
        imap_name = self.magimap
        try:
            index = self.imap_names.index(imap_name)
        except Exception:
            index = self.imap_names.index('ramp')
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.set_imap_cb)
        self.btn['imap'] = combobox
        btns.addWidget(combobox, stretch=0, alignment=QtCore.Qt.AlignRight)

        combobox = QtHelp.ComboBox()
        options = []
        index = 0
        for name, fn in self.operation_table:
            options.append(name)
            combobox.addItem(name)
            index += 1
        combobox.setCurrentIndex(0)
        combobox.activated.connect(self.do_operation_cb)
        self.btn['oprn'] = combobox
        btns.addWidget(combobox, stretch=0, alignment=QtCore.Qt.AlignRight)

        btn = QtGui.QPushButton("Do it")
        btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignRight)

        vbox.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignTop)

        btns = QtHelp.HBox()
        btns.setSpacing(5)

        for name in ('Plot', 'Clear', #'Close'
                     ):
            btn = QtGui.QPushButton(name)
            btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
            self.btn[name.lower()] = btn

        self.btn.plot.clicked.connect(self.replot_stars)
        self.btn.clear.clicked.connect(self.clear)
        #self.btn.close.clicked.connect(self.close)

        combobox = QtHelp.ComboBox()
        options = []
        index = 0
        for name in ['Mag']:
            options.append(name)
            combobox.addItem(name)
            index += 1
        combobox.setCurrentIndex(0)
        combobox.activated.connect(self.set_field_cb)
        self.btn['field'] = combobox
        btns.addWidget(combobox, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vbox.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignTop)

        # create the table
        info = Bunch.Bunch(columns=self.columns, color='Mag')
        self.build_table(info)

        self.mframe.addWidget(vbox, stretch=1)

    def build_table(self, info):
        columns = info.columns
        self.columns = columns

        # Set up the field selector
        fidx = 0
        combobox = self.btn['field']
        combobox.clear()

        col = 0
        for hdr, kwd in columns:
            #item = QtGui.QTableWidgetItem(hdr)
            #table.setHorizontalHeaderItem(col, item)

            combobox.addItem(hdr)
            if hdr == info.color:
                fidx = col
            col += 1

        combobox.setCurrentIndex(fidx)

        fieldname = self.columns[fidx][1]
        self.mag_field = fieldname

    def show_table(self, catalog, info, starlist):
        self.starlist = starlist
        self.catalog = catalog
        # info is ignored, for now
        #self.info = info
        self.selected = []

        # rebuild table according to metadata
        self.build_table(info)

        table = self.table
        model = CatalogTableModel(info.columns, self.starlist)
        table.setModel(model)
        selectionModel = QtHelp.QItemSelectionModel(model, table)
        table.setSelectionModel(selectionModel)
        selectionModel.currentRowChanged.connect(self.select_star_cb)
        model.layoutChanged.connect(self.sort_cb)

        # set column width to fit contents
        table.resizeColumnsToContents()
        table.resizeRowsToContents()

        table.setSortingEnabled(True)

    def _update_selections(self):

        self.table.clearSelection()

        # Mark any selected stars
        for star in self.selected:
            idx = self.starlist.index(star)
            self.table.selectRow(idx)

    def _get_star_path(self, star):
        model = self.table.model()
        starlist = model.starlist
        star_idx = starlist.index(star)
        return star_idx

    def get_subset_from_starlist(self, fromidx, toidx):
        model = self.table.model()
        starlist = model.starlist
        res = []
        for idx in range(fromidx, toidx):
            star = starlist[idx]
            res.append(star)
        return res

    def _select_tv(self, star, fromtable=False):
        self._update_selections()

        star_idx = self._get_star_path(star)
        midx = self.table.indexAt(QtCore.QPoint(star_idx, 0))

        if not fromtable:
            self.table.scrollTo(midx)

    def _unselect_tv(self, star, fromtable=False):
        self._update_selections()

    ## def select_star_cb(self, selected, deselected):
    ##     """This method is called when the user selects a star from the table.
    ##     """
    ##     srows = set()
    ##     dsrows = set()
    ##     for midx in selected.indexes():
    ##         srows.add(midx.row())
    ##     for midx in deselected.indexes():
    ##         dsrows.add(midx.row())
    ##     print("selected: %s  deselected: %s" % (srows, dsrows))
    ##     if len(srows) > 0:
    ##         row = srows.pop()
    ##     else:
    ##         row = dsrows.pop()
    ##     star = self.starlist[row]
    ##     #self.mark_selection(star, fromtable=True)
    ##     return True

    def select_star_cb(self, midx_to, midx_from):
        """This method is called when the user selects a star from the table.
        """
        row = midx_to.row()
        star = self.starlist[row]
        if not self._select_flag:
            self.mark_selection(star, fromtable=True)
        return True

    def set_cmap_cb(self, index):
        name = self.cmap_names[index]
        self.set_cmap_byname(name)

    def set_imap_cb(self, index):
        name = self.imap_names[index]
        self.set_imap_byname(name)

    def set_field_cb(self, index):
        fieldname = self.columns[index][1]
        self.set_field(fieldname)

    def do_operation_cb(self, w, index):
        if index >= 0:
            fn = self.operation_table[index][1]
            fn(self.selected)

    def sort_cb(self):
        self.replot_stars()


class CatalogTableModel(QtCore.QAbstractTableModel):

    def __init__(self, columns, starlist):
        super(CatalogTableModel, self).__init__(None)

        self.columns = columns
        self.starlist = starlist

    def rowCount(self, parent):
        return len(self.starlist)

    def columnCount(self, parent):
        return len(self.columns)

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != QtCore.Qt.DisplayRole:
            return None

        star = self.starlist[index.row()]
        field = self.columns[index.column()][1]
        return str(star[field])

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
        def sortfn(star):
            field = self.columns[Ncol][1]
            return star[field]

        if QtHelp.have_pyqt4:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))

        self.starlist = sorted(self.starlist, key=sortfn)

        if order == QtCore.Qt.DescendingOrder:
            self.starlist.reverse()
        if QtHelp.have_pyqt4:
            self.emit(QtCore.SIGNAL("layoutChanged()"))


# END
