#
# Contents.py -- Table of Contents plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import GingaPlugin
from ginga.misc import Bunch

import gtk
import time

class Contents(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Contents, self).__init__(fv)

        # For table-of-contents pane
        self.nameDict = {}
        self.columns = [('Name', 'NAME'),
                        ('Object', 'OBJECT'),
                        ('Date', 'DATE-OBS'),
                        ('Time UT', 'UT')]
        self.cell_sort_funcs = []
        for hdr, key in self.columns:
            self.cell_sort_funcs.append(self._mksrtfnN(key))
        
        fv.set_callback('add-image', self.add_image)
        fv.set_callback('delete-channel', self.delete_channel)

    def build_gui(self, container):
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        # create the TreeView
        self.treeview = gtk.TreeView()
        
        # create the TreeViewColumns to display the data
        self.tvcolumn = [None] * len(self.columns)
        for n in range(0, len(self.columns)):
            cell = gtk.CellRendererText()
            cell.set_padding(2, 0)
            header, kwd = self.columns[n]
            tvc = gtk.TreeViewColumn(header, cell)
            tvc.set_resizable(True)
            tvc.connect('clicked', self.sort_cb, n)
            tvc.set_clickable(True)
            self.tvcolumn[n] = tvc
            if n == 0:
                fn_data = self._mkcolfn0(kwd)
                ## cell.set_property('xalign', 1.0)
            else:
                fn_data = self._mkcolfnN(kwd)
            self.tvcolumn[n].set_cell_data_func(cell, fn_data)
            self.treeview.append_column(self.tvcolumn[n])

        sw.add(self.treeview)
        #self.treeview.connect('row-activated', self.switch_image)
        self.treeview.connect('cursor-changed', self.switch_image2)

        treemodel = gtk.TreeStore(object)
        self.treeview.set_fixed_height_mode(False)
        self.treeview.set_model(treemodel)
        # This speeds up rendering of TreeViews
        self.treeview.set_fixed_height_mode(True)

        container.pack_start(sw, fill=True, expand=True)


    def sort_cb(self, column, idx):
        treeview = column.get_tree_view()
        model = treeview.get_model()
        model.set_sort_column_id(idx, gtk.SORT_ASCENDING)
        fn = self.cell_sort_funcs[idx]
        model.set_sort_func(idx, fn)
        return True

    def _mksrtfnN(self, key):
        def fn(*args):
            model, iter1, iter2 = args[:3]
            bnch1 = model.get_value(iter1, 0)
            bnch2 = model.get_value(iter2, 0)
            if isinstance(bnch1, str):
                if isinstance(bnch2, str):
                    return cmp(bnch1.lower(), bnch2.lower())
                return 0
            val1, val2 = bnch1[key], bnch2[key]
            if isinstance(val1, str):
                val1 = val1.lower()
                val2 = val2.lower()
            res = cmp(val1, val2)
            return res
        return fn

    def _mkcolfn0(self, kwd):
        def fn(*args):
            column, cell, model, iter = args[:4]
            bnch = model.get_value(iter, 0)
            if isinstance(bnch, str):
                cell.set_property('text', bnch)
            else:
                cell.set_property('text', bnch[kwd])
        return fn

    def _mkcolfnN(self, kwd):
        def fn(*args):
            column, cell, model, iter = args[:4]
            bnch = model.get_value(iter, 0)
            if isinstance(bnch, str):
                cell.set_property('text', '')
            else:
                cell.set_property('text', bnch[kwd])
        return fn

    def switch_image(self, treeview, path, column):
        #print "path is %s" % (str(path))
        model = treeview.get_model()
        iter = model.get_iter(path)
        bnch = model.get_value(iter, 0)
        if isinstance(bnch, str):
            return
        chname = bnch.CHNAME
        imname = bnch.NAME
        path = bnch.path
        self.logger.debug("chname=%s name=%s path=%s" % (
            chname, imname, path))

        self.fv.switch_name(chname, imname, path=path)

    def switch_image2(self, treeview):
        path, column = treeview.get_cursor()
        self.switch_image(treeview, path, column)

    def get_info(self, chname, name, image):
        path = image.get('path', None)
        bnch = Bunch.Bunch(NAME=name, CHNAME=chname, path=path)

        # Get header keywords of interest
        header = image.get_header()
        for x, key in self.columns[1:]:
            bnch[key] = header.get(key, 'N/A')
        return bnch
    
    def recreate_toc(self):
        self.logger.debug("Recreating table of contents...")
        toclist = self.nameDict.keys()
        toclist.sort()

        model = gtk.TreeStore(object)
        for key in toclist:
            it = model.append(None, [ key ])
            fileDict = self.nameDict[key]
            filelist = fileDict.keys()
            filelist.remove('_iter')
            fileDict['_iter'] = it
            filelist.sort(key=str.lower)

            for fname in filelist:
                bnch = fileDict[fname]
                model.append(it, [ bnch ])

        self.treeview.set_fixed_height_mode(False)
        self.treeview.set_model(model)
        self.treeview.set_fixed_height_mode(True)
            

    def add_image(self, viewer, chname, image):
        noname = 'Noname' + str(time.time())
        name = image.get('name', noname)
        path = image.get('path', None)

        model = self.treeview.get_model()
        if not self.nameDict.has_key(chname):
            it = model.append(None, [ chname ])
            fileDict = { '_iter': it }
            self.nameDict[chname] = fileDict
        else:
            fileDict = self.nameDict[chname]
            it = fileDict['_iter']
            
        key = name.lower()
        if fileDict.has_key(key):
            return

        bnch = self.get_info(chname, name, image)
        fileDict[key] = bnch
        model.append(it, [ bnch ])

    def clear(self):
        self.nameDict = {}
        self.recreate_toc()

    def delete_channel(self, viewer, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name
        del self.nameDict[chname]
        self.recreate_toc()
        

    def __str__(self):
        return 'contents'
    
#END
