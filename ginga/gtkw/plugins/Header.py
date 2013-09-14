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
        container.pack_start(self.nb, fill=True, expand=True)

    def _create_header_window(self):
        width, height = 300, -1
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
        sw.show_all()
        return sw, treeview

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

    def set_header(self, treeview, image):
        header = image.get_header()
        # Update the header info
        listmodel = gtk.ListStore(object)
        keyorder = header.keys()
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
        sw, tv = self._create_header_window()
        chname = chinfo.name

        self.nb.append_page(sw, gtk.Label(chname))
        index = self.nb.page_num(sw)
        info = Bunch.Bunch(widget=sw, treeview=tv,
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
            self.nb.set_current_page(index)
            self.active = chname
            self.info = self.channel[self.active]

        image = fitsimage.get_image()
        self.set_header(self.info.treeview, image)
        
    def __str__(self):
        return 'header'
    
#END
