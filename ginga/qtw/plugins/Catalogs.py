#
# Catalogs.py -- Catalogs plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.qtw import ColorBar
from ginga.misc import Bunch, Future
from ginga.misc.plugins import CatalogsBase
from ginga import wcs
from ginga.Catalog import Star

import pyvo 
import os
_dot_ginga_dir = os.path.join(os.environ.get('HOME', '/tmp'), ".ginga")
_def_cat_config_file = os.path.join(_dot_ginga_dir, "catalogs")
_def_im_config_file = os.path.join(_dot_ginga_dir, "image_archives")

class Catalogs(CatalogsBase.CatalogsBase):

    def __init__(self, fv, fitsimage):
        super(Catalogs, self).__init__(fv, fitsimage)

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Catalogs')
        self.settings.load(onError='silent')

        self.logger.info("initializing SCS parameters")
        self._scs_params = {}
        for label in "ra dec r".split():
            self._scs_params[label] = Bunch.Bunch(name=label, convert=str)
        self._sia_params = {}
        for label in "ra dec width height".split():
            self._sia_params[label] = Bunch.Bunch(name=label, convert=str)

        self.catalog_services = {}
        self.image_services = {}
        self._load_def_catalogs()
        self._load_def_image_archives()

    def _load_def_catalogs(self, configfile=None):
        self.logger.info("initializing default catalogs")

        # PLEASE REPLACE: integrate into config framework, format?
        if not configfile:
            configfile = self.settings.get('vo_catalog_servers', 
                                           _def_cat_config_file)
            if not os.path.exists(configfile): return

        self._load_def_servers(configfile, self.catalog_services, 
                               self.catalog_server_options)

    def _load_def_image_archives(self, configfile=None):
        self.logger.info("initializing default catalogs")

        # PLEASE REPLACE: integrate into config framework, format?
        if not configfile:
            configfile = self.settings.get('vo_image_servers',
                                           _def_im_config_file)
            if not os.path.exists(configfile): return

        self._load_def_servers(configfile, self.image_services, 
                               self.image_server_options)

    def _load_def_servers(self, configfile, services, names):

        try:
            with open(configfile) as cnf:
                # for now, format has each line being a 2-tuple giving label 
                # and base url
                for line in cnf:
                    line = line.strip()
                    if line.startswith('#'):
                        continue
                    pair = eval(line)
                    services[pair[0]] = pair[1]
                    names.append(pair[0])
        except Exception, ex:
            self.fv.show_error(str(ex))

    def getcatalog(self, server, params, obj):
        try:
            self.logger.debug("ra=%s, dec=%s, sr=%s" % 
                             (params['ra'], params['dec'], params['r']))
            self.logger.debug("ra=%d, dec=%d, sr=%d" % 
                              (wcs.hmsStrToDeg(params['ra']), 
                               wcs.dmsStrToDeg(params['dec']), 
                               float(params['r'])/60.0))
            # self.fv.show_error("za")

            # initialize our query object with the service's base URL
            query = pyvo.scs.SCSQuery(self.catalog_services[server])
            query.ra = wcs.hmsStrToDeg(params['ra'])
            query.dec = wcs.dmsStrToDeg(params['dec'])
            query.radius = float(params['r'])/60.0
            self.logger.info("Will query: %s" % query.getqueryurl(True))

            results = query.execute()
            self.logger.info("Found %d sources" % len(results))

            starlist = []
            for source in results:
                starlist.append(self.toStar(source))

            self.logger.debug("starlist=%s" % str(starlist))

            starlist = self.filter_results(starlist, obj)
            info = {}
            self.logger.info("Filtered down to %d sources" % len(starlist))

            ## Update the GUI
            self.fv.gui_do(self.update_catalog, starlist, info)
        except Exception, ex:
            self.fv.gui_do(self.fv.show_error, "Trouble building query")
            print str(ex)

    def getimage(self, server, params, chname):
        try:
            self.logger.debug("ra=%s, dec=%s, width=%s height=%s" % 
                             (params['ra'], params['dec'], 
                              params['width'], params['height']))
            self.logger.debug("pos=(%d, %d), size=(%d, %d)" % 
                              (wcs.hmsStrToDeg(params['ra']), 
                               wcs.dmsStrToDeg(params['dec']), 
                               float(params['width'])/60.0, 
                               float(params['height'])/60.0))

            # initialize our query object with the service's base URL
            query = pyvo.sia.SIAQuery(self.image_services[server])
            query.ra = wcs.hmsStrToDeg(params['ra'])
            query.dec = wcs.dmsStrToDeg(params['dec'])
            query.size = (float(params['width'])/60.0, 
                          float(params['height'])/60.0)
            query.format = 'image/fits'
            self.logger.info("Will query: %s" % query.getqueryurl(True))

            results = query.execute()
            if len(results) > 0:
                self.logger.info("Found %d images" % len(results))
            else:
                self.logger.warn("Found no images in this area" % len(results))
                return

            # For now, we pick the first one found

            # REQUIRES FIX IN PYVO:
            # imfile = results[0].cachedataset(dir="/tmp")
            #
            # Workaround:
            fitspath = results[0].make_dataset_filename(dir="/tmp")
            results[0].cachedataset(fitspath)

            self.fv.load_file(fitspath, chname=chname)

            # Update the GUI
            def getimage_update(self):
                self.setfromimage()
                self.redo()

            self.fv.gui_do(getimage_update)

        except Exception, ex:
            self.fv.gui_do(self.fv.show_error, "Trouble building query")
            print str(ex)


    def toStar(self, sourcerec):
        data = { 'name':         sourcerec.id,
                 'ra_deg':       float(sourcerec.ra),
                 'dec_deg':      float(sourcerec.dec),
                 'mag':          18.0,
                 'preference':   0,
                 'priority':     0,
                 'description':  'fake magnitude' }
        data['ra'] = wcs.raDegToString(data['ra_deg'])
        data['dec'] = wcs.decDegToString(data['dec_deg'])
        return Star(**data)


        
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
        for name in self.image_services.keys():
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

        for name in self.catalog_services.keys():
            combobox.addItem(name)
            index += 1
        index = 0
        combobox.setCurrentIndex(index)
        combobox.activated.connect(self.setup_params_catalog)
        if len(self.catalog_server_options) > 0:
           self.setup_params_catalog(index, redo=False)

        btns = QtHelp.HBox()
        btns.setSpacing(5)
        
        btn = QtGui.QPushButton("Set parameters from entire image")
        btn.clicked.connect(self.setfromimage)
        btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignCenter)
        vbox0.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignTop)

        self.w.params = vbox0
        nb.addTab(vbox0, u"Params")

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
        nb.addTab(vbox, u"Listing")

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

        container.addWidget(vbox1, stretch=1)
        

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
        
    def setup_params_catalog(self, index, redo=True):
        key = self.catalog_server_options[index]

        # Get the parameter list and adjust the widget
        # obj = self.fv.imgsrv.getCatalogServer(key)
        b = self._setup_params(self._scs_params, self.w2.cat_params)
        self.catalog_server_params = b

        if redo:
            self.redo()

    def setup_params_image(self, index, redo=True):
        key = self.image_server_options[index]

        # Get the parameter list and adjust the widget
        # obj = self.fv.imgsrv.getImageServer(key)
        b = self._setup_params(self._sia_params, self.w.img_params)
        self.image_server_params = b

        if redo:
            self.redo()

    def _setup_params(self, params, container):
        self.logger.info("loading service parameter")
        captions = []
        for key, bnch in params.items():
            text = key
            if bnch.has_key('label'):
                text = bnch.label
            captions.append((text, 'entry'))

        # TODO: put RA/DEC first, and other stuff not in random orders
        w, b = QtHelp.build_info(captions)

        # remove old widgets
        old_w = container.currentWidget()
        if old_w != None:
            container.removeWidget(old_w)

        # add new widgets
        container.insertWidget(0, w)
        return b

    def _update_widgets(self, d):
        for bnch in (self.image_server_params,
                     self.catalog_server_params):
            if bnch != None:
                for key in bnch.keys():
                    if d.has_key(key):
                        bnch[key].setText(str(d[key]))
    
    def get_params(self, bnch):
        params = {}
        for key in bnch.keys():
            params[key] = str(bnch[key].text())
        return params

    def instructions(self):
        self.set_message("""TBD.""")
        
    def __str__(self):
        return 'catalogs'
    

class CatalogListing(CatalogsBase.CatalogListingBase):
    
    def _build_gui(self, container):
        self.mframe = container
            
        vbox = QtHelp.VBox()

        # create the table
        table = QtGui.QTableWidget()
        table.setColumnCount(len(self.columns))
        table.cellClicked.connect(self.select_star_cb)
        self.table = table
        
        col = 0
        for hdr, kwd in self.columns:
            item = QtGui.QTableWidgetItem(hdr)
            table.setHorizontalHeaderItem(col, item)
            col += 1

        vbox.addWidget(table, stretch=1)

        self.cbar = ColorBar.ColorBar(self.logger)
        self.cbar.set_cmap(self.cmap)
        self.cbar.set_imap(self.imap)
        #self.cbar.set_size_request(-1, 20)

        vbox.addWidget(self.cbar, stretch=0)

        btns = QtHelp.HBox()
        btns.setSpacing(5)

        for name in ('Plot', 'Clear', #'Close'
                     ):
            btn = QtGui.QPushButton(name)
            btns.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignCenter)
            self.btn[name.lower()] = btn

        self.btn.plot.clicked.connect(self.replot_stars)
        self.btn.clear.clicked.connect(self.clear)
        #self.btn.close.clicked.connect(self.close)

        vbox.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignTop)
        
        self.mframe.addWidget(vbox, stretch=1)

    def show_table(self, catalog, info, starlist):
        self.starlist = starlist
        self.catalog = catalog
        # info is ignored, for now
        #self.info = info
        self.selected = []

        table = self.table
        table.clearContents()
        table.setSortingEnabled(False)
        # Update the starlist info
        row = 0
        table.setRowCount(len(starlist))
        
        for star in starlist:
            col = 0
            for hdr, kwd in self.columns:
                val = str(star.starInfo.get(kwd, ''))
                item = QtGui.QTableWidgetItem(val)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                table.setItem(row, col, item)
                col += 1
            row += 1
        table.setSortingEnabled(True)

        # TODO: fix.  This is raising a segfault!
        #self.cbar.set_range(self.mag_min, self.mag_max)


    def _update_selections(self):

        maxcol = len(self.columns)-1
        # Go through all selections in the table and ensure that the
        # ones in self.selected are highlighted and the others are not.
        checked = set()
        for modelidx in self.table.selectedIndexes():
            idx = modelidx.row()
            star2 = self.starlist[idx]
            checked.add(star2)
            isSelected = star2 in self.selected
            _range = QtGui.QTableWidgetSelectionRange(idx, 0, idx, maxcol)
            self.table.setRangeSelected(_range, isSelected)

        # Mark any other selected stars that are not highlighted
        for star2 in set(self.selected) - checked:
            idx = self.starlist.index(star2)
            _range = QtGui.QTableWidgetSelectionRange(idx, 0, idx, maxcol)
            self.table.setRangeSelected(_range, True)

    def _select_tv(self, star, fromtable=False):
        self._update_selections()
        
        star_idx = self.starlist.index(star)
        item = self.table.item(star_idx, 0)

        if not fromtable:
            self.table.scrollToItem(item)

    def _unselect_tv(self, star):
        self._update_selections()

    def select_star_cb(self, row, col):
        """This method is called when the user selects a star from the table.
        """
        star = self.starlist[row]
        self.mark_selection(star, fromtable=True)
        return True
    

# END
