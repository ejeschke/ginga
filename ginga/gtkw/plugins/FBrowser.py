#
# FBrowser.py -- File Browser plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org) 
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os, glob
import stat, time

from ginga.misc import Bunch
from ginga import AstroImage, GingaPlugin
from ginga.gtkw import gtksel

import gtk

#icon_ext = '.svg'
icon_ext = '.png'

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
        self.cell_data_funcs = (self.file_name, self.file_size,
                                self.file_mode, self.file_last_changed)
        self.cell_sort_funcs = []
        for hdr, key in self.columns:
            self.cell_sort_funcs.append(self._mksrtfnN(key))
        
        self.jumpinfo = []
        homedir = os.environ['HOME']
        self.curpath = os.path.join(homedir, '*')
        self.do_scanfits = False
        self.moving_cursor = False

        icondir = self.fv.iconpath
        foldericon = os.path.join(icondir, 'folder'+icon_ext)
        self.folderpb = gtksel.pixbuf_new_from_file_at_size(foldericon, 24, 24)
        fileicon = os.path.join(icondir, 'file'+icon_ext)
        self.filepb = gtksel.pixbuf_new_from_file_at_size(fileicon, 24, 24)
        fitsicon = os.path.join(icondir, 'fits'+icon_ext)
        self.fitspb = gtksel.pixbuf_new_from_file_at_size(fitsicon, 24, 24)


    def build_gui(self, container):
        rvbox = gtk.VBox()

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC,
                      gtk.POLICY_AUTOMATIC)

        # create the TreeView
        self.treeview = gtk.TreeView()
        
        # create the TreeViewColumns to display the data
        self.tvcolumn = [None] * len(self.columns)
        cellpb = gtk.CellRendererPixbuf()
        cellpb.set_padding(2, 0)
        header, kwd = self.columns[0]
        tvc = gtk.TreeViewColumn(header, cellpb)
        tvc.set_resizable(True)
        tvc.connect('clicked', self.sort_cb, 0)
        tvc.set_clickable(True)
        self.tvcolumn[0] = tvc
        self.tvcolumn[0].set_cell_data_func(cellpb, self.file_pixbuf)
        cell = gtk.CellRendererText()
        cell.set_padding(2, 0)
        self.tvcolumn[0].pack_start(cell, False)
        self.tvcolumn[0].set_cell_data_func(cell, self.file_name)
        self.treeview.append_column(self.tvcolumn[0])
        for n in range(1, len(self.columns)):
            cell = gtk.CellRendererText()
            cell.set_padding(2, 0)
            header, kwd = self.columns[n]
            tvc = gtk.TreeViewColumn(header, cell)
            tvc.set_resizable(True)
            tvc.connect('clicked', self.sort_cb, n)
            tvc.set_clickable(True)
            self.tvcolumn[n] = tvc
            if n == 1:
                cell.set_property('xalign', 1.0)
            self.tvcolumn[n].set_cell_data_func(cell, self.cell_data_funcs[n])
            self.treeview.append_column(self.tvcolumn[n])

        sw.add(self.treeview)
        self.treeview.connect('row-activated', self.open_file)

        rvbox.pack_start(sw, fill=True, expand=True)

        self.entry = gtk.Entry()
        rvbox.pack_start(self.entry, fill=True, expand=False)
        self.entry.connect('activate', self.browse_cb)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        btn = gtk.Button("Refresh")
        btn.connect('clicked', lambda w: self.refresh())
        btns.add(btn)
        btn = gtk.Button("Make Thumbs")
        btn.connect('clicked', lambda w: self.make_thumbs())
        btns.add(btn)
        rvbox.pack_start(btns, padding=4, fill=True, expand=False)

        container.pack_start(rvbox, padding=0, fill=True, expand=True)

    def sort_cb(self, column, idx):
        treeview = column.get_tree_view()
        model = treeview.get_model()
        model.set_sort_column_id(idx, gtk.SORT_ASCENDING)
        fn = self.cell_sort_funcs[idx]
        model.set_sort_func(idx, fn)
        return True

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True

    def _mksrtfnN(self, key):
        def fn(model, iter1, iter2):
            bnch1 = model.get_value(iter1, 0)
            bnch2 = model.get_value(iter2, 0)
            val1, val2 = bnch1[key], bnch2[key]
            if isinstance(val1, str):
                val1 = val1.lower()
                val2 = val2.lower()
            res = cmp(val1, val2)
            return res
        return fn

    def file_pixbuf(self, *args):
        column, cell, model, iter = args[:4]
        bnch = model.get_value(iter, 0)
        if bnch.type == 'dir':
            pb = self.folderpb
        elif bnch.type == 'fits':
            pb = self.fitspb
        else:
            pb = self.filepb
        cell.set_property('pixbuf', pb)

    def file_name(self, *args):
        column, cell, model, iter = args[:4]
        bnch = model.get_value(iter, 0)
        cell.set_property('text', bnch.name)

    def file_size(self, *args):
        column, cell, model, iter = args[:4]
        bnch = model.get_value(iter, 0)
        cell.set_property('text', str(bnch.st_size))

    def file_mode(self, *args):
        column, cell, model, iter = args[:4]
        bnch = model.get_value(iter, 0)
        cell.set_property('text', oct(stat.S_IMODE(bnch.st_mode)))

    def file_last_changed(self, *args):
        column, cell, model, iter = args[:4]
        bnch = model.get_value(iter, 0)
        cell.set_property('text', time.ctime(bnch.st_mtime))

    def open_file(self, treeview, path, column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        bnch = model.get_value(iter, 0)
        path = bnch.path
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
        filelist = glob.glob(path)
        filelist.sort(key=str.lower)
        filelist.insert(0, os.path.join(dirname, '..'))

        self.jumpinfo = map(self.get_info, filelist)
        self.curpath = path
        self.entry.set_text(path)

        if self.do_scanfits:
            self.scan_fits()
            
        self.makelisting()

    def makelisting(self):
        listmodel = gtk.ListStore(object)
        for bnch in self.jumpinfo:
            listmodel.append([bnch])

        self.treeview.set_fixed_height_mode(False)
        self.treeview.set_model(listmodel)
        # Hack to get around slow TreeView scrolling with large lists
        self.treeview.set_fixed_height_mode(True)
            
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
        
    def browse_cb(self, w):
        path = w.get_text().strip()
        self.browse(path)
        
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
