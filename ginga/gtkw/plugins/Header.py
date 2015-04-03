#
# Header.py -- FITS Header plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.misc import Bunch

from ginga.gtkw import gtksel, GtkHelp
import gtk


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
        self.cell_sort_funcs = []
        for kwd, key in self.columns:
            self.cell_sort_funcs.append(self._mksrtfnN(key))

        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.set_callback('active-image', self.focus_cb)
        

    def build_gui(self, container):
        nb = GtkHelp.Notebook()
        nb.set_group_id(-30)
        nb.set_tab_pos(gtk.POS_BOTTOM)
        nb.set_scrollable(False)
        nb.set_show_tabs(False)
        nb.set_show_border(False)
        nb.show()
        self.nb = nb
        cw = container.get_widget()
        cw.pack_start(self.nb, fill=True, expand=True)

    def _create_header_window(self, info):
        width, height = 300, -1
        vbox = gtk.VBox()
        
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        # create the TreeView
        treeview = gtk.TreeView()
        
        # create the TreeViewColumns to display the data
        tvcolumn = [None] * len(self.columns)
        for n in range(0, len(self.columns)):
            cell = gtk.CellRendererText()
            cell.set_padding(2, 0)
            header, kwd = self.columns[n]
            tvc = gtk.TreeViewColumn(header, cell)
            tvc.set_resizable(True)
            tvc.connect('clicked', self.sort_cb, n)
            tvc.set_clickable(True)
            tvcolumn[n] = tvc
            fn_data = self._mkcolfnN(kwd)
            tvcolumn[n].set_cell_data_func(cell, fn_data)
            treeview.append_column(tvcolumn[n])

        sw.add(treeview)
        vbox.pack_start(sw, fill=True, expand=True)
        
        # create sort toggle
        cb = GtkHelp.CheckButton("Sortable")
        cb.sconnect('toggled', lambda w: self.set_sortable_cb(info))
        hbox = gtk.HBox()
        hbox.pack_start(cb, fill=True, expand=False)
        vbox.pack_start(hbox, fill=True, expand=False)
        vbox.show_all()
        
        info.setvals(widget=vbox, treeview=treeview, sortw=cb)
        return vbox

    def sort_cb(self, column, idx):
        treeview = column.get_tree_view()
        model = treeview.get_model()
        model.set_sort_column_id(idx, gtk.SORT_ASCENDING)
        fn = self.cell_sort_funcs[idx]
        model.set_sort_func(idx, fn)
        return True

    def _mkcolfnN(self, kwd):
        def fn(*args):
            column, cell, model, iter = args[:4]
            bnch = model.get_value(iter, 0)
            cell.set_property('text', bnch[kwd])
        return fn

    def _mksrtfnN(self, key):
        def fn(*args):
            model, iter1, iter2 = args[:3]
            bnch1 = model.get_value(iter1, 0)
            bnch2 = model.get_value(iter2, 0)
            val1, val2 = bnch1[key], bnch2[key]
            if isinstance(val1, str):
                val1 = val1.lower()
                val2 = val2.lower()
            res = cmp(val1, val2)
            return res
        return fn

    def set_header(self, info, image):
        treeview = info.treeview
        
        header = image.get_header()
        # Update the header info
        listmodel = gtk.ListStore(object)
        keyorder = list(header.keys())

        sorted = info.sortw.get_active()
        if sorted:
            keyorder.sort()
            
        for key in keyorder:
            card = header.get_card(key)
            bnch = Bunch.Bunch(kwd=key, value=str(card.value),
                               comment=card.comment)
            listmodel.append([bnch])

        treeview.set_fixed_height_mode(False)
        treeview.set_model(listmodel)
        # This speeds up rendering of TreeViews
        treeview.set_fixed_height_mode(True)

    def add_channel(self, viewer, chinfo):
        chname = chinfo.name
        info = Bunch.Bunch(chname=chname)
        widget = self._create_header_window(info)

        self.nb.append_page(widget, gtk.Label(chname))
        info.setvals(widget=widget)
        self.channel[chname] = info

        fitsimage = chinfo.fitsimage
        fitsimage.set_callback('image-set', self.new_image_cb, info)

    def delete_channel(self, viewer, chinfo):
        chname = chinfo.name
        self.logger.debug("deleting channel %s" % (chname))
        widget = self.channel[chname].widget
        index = self.nb.page_num(widget)
        self.nb.remove_page(index)
        self.active = None
        self.info = None
        del self.channel[chname]

    def start(self):
        names = self.fv.get_channelNames()
        for name in names:
            chinfo = self.fv.get_channelInfo(name)
            self.add_channel(self.fv, chinfo)
        
    def new_image_cb(self, fitsimage, image, info):
        self.set_header(info, image)
        
    def set_sortable_cb(self, info):
        chinfo = self.fv.get_channelInfo(info.chname)
        image = chinfo.fitsimage.get_image()
        self.set_header(info, image)
        
    def focus_cb(self, viewer, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        chname = chinfo.name

        if self.active != chname:
            widget = self.channel[chname].widget
            index = self.nb.page_num(widget)
            self.nb.set_current_page(index)
            self.active = chname
            self.info = self.channel[self.active]

        image = fitsimage.get_image()
        if image is None:
            return
        self.set_header(self.info, image)
        
    def __str__(self):
        return 'header'
    
#END
