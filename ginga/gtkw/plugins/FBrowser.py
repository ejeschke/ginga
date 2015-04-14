#
# FBrowser.py -- File Browser plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org) 
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import stat, time

from ginga.misc.plugins import FBrowserBase
from ginga.misc import Bunch
from ginga.gtkw import gtksel

import gtk

#icon_ext = '.svg'
icon_ext = '.png'

class FBrowser(FBrowserBase.FBrowserBase):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(FBrowser, self).__init__(fv, fitsimage)

        self.cell_data_funcs = []
        self.cell_sort_funcs = []
        for hdr, key in self.columns:
            self.cell_data_funcs.append(self._mk_set_cell(key))
            self.cell_sort_funcs.append(self._mksrtfnN(key))
        
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
        #self.treeview = gtk.TreeView()
        self.treeview = MultiDragDropTreeView()
        
        # create the TreeViewColumns to display the data
        self.tvcolumn = [None] * len(self.columns)

        for n in range(0, len(self.columns)):

            header, attrname = self.columns[n]
            if attrname == 'name':
                # special dispensation for attribute 'name'--add icon
                cellpb = gtk.CellRendererPixbuf()
                cellpb.set_padding(2, 0)
                tvc = gtk.TreeViewColumn(header, cellpb)
                tvc.set_cell_data_func(cellpb, self._set_file_pixbuf)
                cell = gtk.CellRendererText()
                cell.set_padding(2, 0)
                tvc.pack_start(cell, False)
            else:
                cell = gtk.CellRendererText()
                cell.set_padding(2, 0)
                tvc = gtk.TreeViewColumn(header, cell)

            tvc.set_resizable(True)
            tvc.connect('clicked', self.sort_cb, n)
            tvc.set_clickable(True)
            self.tvcolumn[n] = tvc
            #cell.set_property('xalign', 1.0)
            tvc.set_cell_data_func(cell, self.cell_data_funcs[n])
            self.treeview.append_column(tvc)

        sw.add(self.treeview)
        self.treeview.connect('row-activated', self.open_file)
        # enable multiple selection
        treeselection = self.treeview.get_selection()
        treeselection.set_mode(gtk.SELECTION_MULTIPLE)

        # enable drag from this widget
        toImage = [ ( "text/plain", 0, 0 ) ]
        self.treeview.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                                               toImage, gtk.gdk.ACTION_COPY)
        self.treeview.connect("drag-data-get", self.drag_data_get_cb)

        rvbox.pack_start(sw, fill=True, expand=True)

        self.entry = gtk.Entry()
        rvbox.pack_start(self.entry, fill=True, expand=False)
        self.entry.connect('activate', self.browse_cb)

        hbox = gtk.HBox(spacing=2)
        btn = gtk.Button("Load")
        btn.connect('clicked', lambda w: self.load_cb())
        hbox.pack_start(btn, fill=False, expand=False)
        btn = gtk.Button("Save Image As")
        btn.connect('clicked', lambda w: self.save_as_cb())
        hbox.pack_start(btn, fill=False, expand=False)
        self.entry2 = gtk.Entry()
        self.entry.connect('activate', self.browse_cb)
        hbox.pack_start(self.entry2, fill=True, expand=True)
        rvbox.pack_start(hbox, fill=True, expand=False)

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

        cw = container.get_widget()
        cw.pack_start(rvbox, padding=0, fill=True, expand=True)

    def sort_cb(self, column, idx):
        treeview = column.get_tree_view()
        model = treeview.get_model()
        model.set_sort_column_id(idx, gtk.SORT_ASCENDING)
        fn = self.cell_sort_funcs[idx]
        model.set_sort_func(idx, fn)
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

    def _mk_set_cell(self, attrname):
        def set_cell(*args):
            column, cell, model, iter = args[:4]
            bnch = model.get_value(iter, 0)
            cell.set_property('text', bnch[attrname])
        return set_cell

    def _set_file_pixbuf(self, *args):
        column, cell, model, iter = args[:4]
        bnch = model.get_value(iter, 0)
        if bnch.type == 'dir':
            pb = self.folderpb
        elif bnch.type == 'fits':
            pb = self.fitspb
        else:
            pb = self.filepb
        cell.set_property('pixbuf', pb)

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
            #self.fv.load_file(path)
            uri = "file://%s" % (path)
            self.fitsimage.make_callback('drag-drop', [uri])

        else:
            self.browse(path)

    def get_selected_paths(self):
        treeselection = self.treeview.get_selection()
        model, pathlist = treeselection.get_selected_rows()
        paths = []
        for path in pathlist:
            tree_iter = model.get_iter(path)
            bnch = model.get_value(tree_iter, 0)
            uri = "file://%s" % (bnch.path)
            paths.append(uri)
        return paths

    def load_cb(self):
        paths = self.get_selected_paths()
        #self.fv.dragdrop(self.fitsimage, paths)
        self.fv.gui_do(self.fitsimage.make_callback, 'drag-drop',
                       paths)
        
    def drag_data_get_cb(self, treeview, context, selection,
                         info, timestamp):
        paths = self.get_selected_paths()
        #selection.set_uris(paths)
        selection.set("text/plain", 0, '\n'.join(paths))
    
    def makelisting(self, path):
        self.entry.set_text(path)

        listmodel = gtk.ListStore(object)
        for bnch in self.jumpinfo:
            listmodel.append([bnch])

        self.treeview.set_fixed_height_mode(False)
        self.treeview.set_model(listmodel)
        # Hack to get around slow TreeView scrolling with large lists
        self.treeview.set_fixed_height_mode(True)
            
    def browse_cb(self, w):
        path = w.get_text().strip()
        self.browse(path)
        
    def save_as_cb(self):
        path = self.entry2.get_text()
        if not path.startswith('/'):
            path = os.path.join(self.curpath, path)

        image = self.fitsimage.get_image()
        self.fv.error_wrap(image.save_as_file, path)
        
    def __str__(self):
        return 'fbrowser'


class MultiDragDropTreeView(gtk.TreeView):
    '''TreeView that captures mouse events to make drag and drop work
    properly
    See: https://gist.github.com/kevinmehall/278480#file-multiple-selection-dnd-class-py
    '''
 
    def __init__(self):
        super(MultiDragDropTreeView, self).__init__()

        self.connect('button_press_event', self.on_button_press)
        self.connect('button_release_event', self.on_button_release)
        self.defer_select = False

    def on_button_press(self, widget, event):
        # Here we intercept mouse clicks on selected items so that we can
        # drag multiple items without the click selecting only one
        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (target 
           and event.type == gtk.gdk.BUTTON_PRESS
           and not (event.state & (gtk.gdk.CONTROL_MASK|gtk.gdk.SHIFT_MASK))
           and self.get_selection().path_is_selected(target[0])):
            # disable selection
            self.get_selection().set_select_function(lambda *ignore: False)
            self.defer_select = target[0]

    def on_button_release(self, widget, event):
        # re-enable selection
        self.get_selection().set_select_function(lambda *ignore: True)

        target = self.get_path_at_pos(int(event.x), int(event.y))	
        if (self.defer_select and target 
           and self.defer_select == target[0]
           and not (event.x==0 and event.y==0)): # certain drag and drop
            self.set_cursor(target[0], target[1], False)

        self.defer_select=False

#END
