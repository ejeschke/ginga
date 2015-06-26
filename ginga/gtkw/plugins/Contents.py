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
from ginga.misc import Bunch, Future

import gtk
import time

class Contents(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Contents, self).__init__(fv)

        columns = [ ('Name', 'NAME'), ('Object', 'OBJECT'),
                    ('Date', 'DATE-OBS'), ('Time UT', 'UT'),
                     ]

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Contents')
        self.settings.addDefaults(columns=columns, always_expand=True)
        self.settings.load(onError='silent')

        # For table-of-contents pane
        self.nameDict = Bunch.caselessDict()
        # TODO: this ought to be customizable by channel
        self.columns = self.settings.get('columns', columns)

        self.cell_sort_funcs = []
        for hdr, key in self.columns:
            self.cell_sort_funcs.append(self._mksrtfnN(key))

        self.gui_up = False
        fv.set_callback('add-image', self.add_image)
        fv.set_callback('remove-image', self.remove_image)
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

        cw = container.get_widget()
        cw.pack_start(sw, fill=True, expand=True)

        self.gui_up = True


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

        self.fv.switch_name(chname, imname, path=path,
                            image_future=bnch.image_future)

    def switch_image2(self, treeview):
        path, column = treeview.get_cursor()
        self.switch_image(treeview, path, column)

    def get_info(self, chname, name, image):
        path = image.get('path', None)
        future = image.get('image_future', None)
        if future is None:
            image_loader = image.get('loader', self.fv.load_image)
            future = Future.Future()
            future.freeze(image_loader, path)

        bnch = Bunch.Bunch(CHNAME=chname, path=path,
                           image_future=future)

        # Get header keywords of interest
        header = image.get_header()
        for x, key in self.columns:
            bnch[key] = header.get(key, 'N/A')
        # name should always be available
        bnch.NAME = name
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
            filelist.sort(key=lambda s: s.lower())

            for fname in filelist:
                bnch = fileDict[fname]
                model.append(it, [ bnch ])

        self.treeview.set_fixed_height_mode(False)
        self.treeview.set_model(model)
        self.treeview.set_fixed_height_mode(True)

        # User wants auto expand?
        if self.settings.get('always_expand', False):
            self.treeview.expand_all()

    def add_image(self, viewer, chname, image):
        if not self.gui_up:
            return False

        noname = 'Noname' + str(time.time())
        name = image.get('name', noname)
        self.logger.debug("name=%s" % (name))

        nothumb = image.get('nothumb', False)
        if nothumb:
            return

        model = self.treeview.get_model()
        if chname not in self.nameDict:
            it = model.append(None, [ chname ])
            fileDict = { '_iter': it }
            self.nameDict[chname] = fileDict
        else:
            fileDict = self.nameDict[chname]
            it = fileDict['_iter']

        key = name.lower()
        if key in fileDict:
            return

        bnch = self.get_info(chname, name, image)
        fileDict[key] = bnch
        model.append(it, [ bnch ])

        # User wants auto expand?
        if self.settings.get('always_expand', False):
            self.treeview.expand_all()

        #self.treeview.scroll_to_cell(it)
        self.logger.debug("%s added to Contents" % (name))

    def remove_image(self, viewer, chname, name, path):
        if not self.gui_up:
            return False

        if chname not in self.nameDict:
            return
        else:
            fileDict = self.nameDict[chname]
            it = fileDict['_iter']

        key = name.lower()
        if key not in fileDict:
            return

        del fileDict[key]
        self.recreate_toc()
        self.logger.debug("%s removed from Contents" % (name))

    def clear(self):
        self.nameDict = Bunch.caselessDict()
        self.recreate_toc()

    def delete_channel(self, viewer, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name
        del self.nameDict[chname]
        if not self.gui_up:
            return False
        self.recreate_toc()

    def stop(self):
        self.gui_up = False

    def get_contents_by_channel(self, chname):
        fileDict = self.nameDict[chname]
        return fileDict

    def __str__(self):
        return 'contents'

#END
