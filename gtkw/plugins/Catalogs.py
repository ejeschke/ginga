#
# Catalogs.py -- Catalogs plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import FitsImageCanvasTypesGtk as CanvasTypes
import GingaPlugin
import ColorBar
import cmap, imap
import wcs

import Bunch
import Future
import gobject
import gtk
import pango
import GtkHelp

class Catalogs(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        super(Catalogs, self).__init__(fv, fitsimage)

        self.mycolor = 'skyblue'
        self.color_cursor = 'red'

        self.limit_stars_to_area = False
        self.use_dss_channel = False
        self.plot_max = 500
        self.plot_limit = 100
        self.plot_start = 0

        # star list
        self.starlist = []
        # catalog listing
        self.table = None
        
        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('rectangle', color='cyan', linestyle='dash',
                            drawdims=True)
        canvas.set_callback('button-release', self.btnup)
        canvas.set_callback('draw-event', self.getarea)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas
        self.layertag = 'catalog-canvas'
        self.areatag = None
        self.curstar = None

        self.image_server_options = []
        self.image_server_params = None

        self.catalog_server_options = []
        self.catalog_server_params = None

        self.tooltips = self.fv.w.tooltips

    def build_gui(self, container, future=None):
        vbox1 = gtk.VBox()

        self.msgFont = pango.FontDescription("Sans 12")
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_WORD)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.modify_font(self.msgFont)
        self.tw = tw

        fr = gtk.Frame(" Instructions ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.set_label_align(0.1, 0.5)
        fr.add(tw)
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)
        
        nb = gtk.Notebook()
        #nb.set_group_id(group)
        #nb.connect("create-window", self.detach_page, group)
        nb.set_tab_pos(gtk.POS_BOTTOM)
        nb.set_scrollable(True)
        nb.set_show_tabs(True)
        nb.set_show_border(False)
        vbox1.pack_start(nb, padding=4, fill=True, expand=True)

        vbox0 = gtk.VBox()
        hbox = gtk.HBox(spacing=4)

        vbox = gtk.VBox()
        fr = gtk.Frame(" Image Server ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)
        fr.add(vbox)

        captions = (('Server', 'xlabel'),
                    ('@Server', 'combobox'),
                    ('Use DSS channel', 'checkbutton'),
                    ('Get Image', 'button'))
        w, self.w = GtkHelp.build_info(captions)
        self.w.nb = nb
        self.w.get_image.connect('clicked', lambda w: self.getimage_cb())
        self.w.use_dss_channel.set_active(self.use_dss_channel)
        self.w.use_dss_channel.connect('toggled', self.use_dss_channel_cb)

        vbox.pack_start(w, padding=4, fill=True, expand=False)

        self.w.img_params = gtk.VBox()
        vbox.pack_start(self.w.img_params, padding=4, fill=True, expand=False)
        
        combobox = self.w.server
        index = 0
        self.image_server_options = self.fv.imgsrv.getServerNames(kind='image')
        for name in self.image_server_options:
            combobox.insert_text(index, name)
            index += 1
        index = 0
        combobox.set_active(index)
        combobox.sconnect('changed', self.setup_params_image)
        if len(self.image_server_options) > 0:
            self.setup_params_image(combobox, redo=False)

        hbox.pack_start(fr, fill=True, expand=True)

        vbox = gtk.VBox()
        fr = gtk.Frame(" Catalog Server ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)
        fr.add(vbox)

        captions = (('Server', 'xlabel'),
                    ('@Server', 'combobox'),
                    ('Limit stars to area', 'checkbutton'),
                    ('Search', 'button'))
        w, self.w2 = GtkHelp.build_info(captions)
        self.w2.search.connect('clicked', lambda w: self.getcatalog_cb())
        self.w2.limit_stars_to_area.set_active(self.limit_stars_to_area)
        self.w2.limit_stars_to_area.connect('toggled', self.limit_area_cb)

        vbox.pack_start(w, padding=4, fill=True, expand=False)

        self.w2.cat_params = gtk.VBox()
        vbox.pack_start(self.w2.cat_params, padding=4, fill=True, expand=False)
        
        combobox = self.w2.server
        index = 0
        self.catalog_server_options = self.fv.imgsrv.getServerNames(kind='catalog')
        for name in self.catalog_server_options:
            combobox.insert_text(index, name)
            index += 1
        index = 0
        combobox.set_active(index)
        combobox.sconnect('changed', self.setup_params_catalog)
        if len(self.catalog_server_options) > 0:
            self.setup_params_catalog(combobox, redo=False)

        hbox.pack_start(fr, fill=True, expand=True)
        vbox0.pack_start(hbox, fill=True, expand=True)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_CENTER)
        btns.set_spacing(5)

        btn = gtk.Button("Set parameters from entire image")
        btn.connect('clicked', lambda w: self.setfromimage())
        btns.add(btn)
        vbox0.pack_start(btns, padding=4, fill=True, expand=False)

        lbl = gtk.Label("Params")
        self.w.params = vbox0
        nb.append_page(vbox0, lbl)

        vbox = gtk.VBox()
        self.table = CatalogListing(self.logger, vbox)

        hbox = gtk.HBox()
        scale = gtk.HScrollbar()
        adj = scale.get_adjustment()
        adj.configure(0, 0, 0, 1, 10, self.plot_limit)
        #scale.set_size_request(200, -1)
        self.tooltips.set_tip(scale, "Choose subset of stars plotted")
        #scale.set_update_policy(gtk.UPDATE_DELAYED)
        scale.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.w.plotgrp = scale
        scale.connect('value-changed', self.plot_pct_cb)
        hbox.pack_start(scale, padding=2, fill=True, expand=True)

        sb = GtkHelp.SpinButton()
        adj = sb.get_adjustment()
        adj.configure(self.plot_limit, 10, self.plot_max, 10, 100, 100)
        self.w.plotnum = sb
        self.tooltips.set_tip(sb, "Adjust size of subset of stars plotted")
        sb.connect('value-changed', self.plot_limit_cb)
        hbox.pack_start(sb, padding=2, fill=False, expand=False)
        vbox.pack_start(hbox, padding=0, fill=False, expand=False)

        #vbox1.pack_start(vbox, padding=4, fill=True, expand=True)
        lbl = gtk.Label("Listing")
        self.w.listing = vbox
        nb.append_page(vbox, lbl)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)
        btns.set_child_size(15, -1)
        self.w.buttons = btns

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)

        if future:
            btn = gtk.Button('Ok')
            btn.connect('clicked', lambda w: self.ok())
            btns.add(btn)
            btn = gtk.Button('Cancel')
            btn.connect('clicked', lambda w: self.cancel())
            btns.add(btn)
        vbox1.pack_start(btns, padding=4, fill=True, expand=False)

        vbox1.show_all()
        container.pack_start(vbox1, padding=0, fill=True, expand=True)
        

    def limit_area_cb(self, w):
        self.limit_stars_to_area = w.get_active()
        return True

    def use_dss_channel_cb(self, w):
        self.use_dss_channel = w.get_active()
        return True

    def plot_pct_cb(self, rng):
        val = rng.get_value()
        self.plot_start = int(val)
        self.replot_stars()
        return True

    def _update_plotscroll(self):
        num_stars = len(self.starlist)
        if num_stars > 0:
            adj = self.w.plotgrp.get_adjustment()
            page_size = self.plot_limit
            self.plot_start = min(self.plot_start, num_stars-1)
            adj.configure(self.plot_start, 0, num_stars, 1,
                          page_size, page_size)

        self.replot_stars()

    def plot_limit_cb(self, rng):
        val = rng.get_value()
        self.plot_limit = int(val)
        self._update_plotscroll()
        return True

    def set_message(self, msg):
        buf = self.tw.get_buffer()
        buf.set_text(msg)
        self.tw.modify_font(self.msgFont)
        
    def ok(self):
        return self.close()

    def cancel(self):
        return self.close()

    def update_gui(self):
        self.fv.update_pending()

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def _setup_params(self, obj, container):
        params = obj.getParams()
        captions = []
        for key, bnch in params.items():
            text = key
            if bnch.has_key('label'):
                text = bnch.label
            captions.append((text, 'entry'))

        # TODO: put RA/DEC first, and other stuff not in random orders
        w, b = GtkHelp.build_info(captions)

        # remove old widgets
        children = container.get_children()
        for child in children:
            container.remove(child)

        # add new widgets
        container.pack_start(w, fill=False, expand=False)
        container.show_all()
        return b

    def setup_params_image(self, combobox, redo=True):
        index = combobox.get_active()
        key = self.image_server_options[index]

        # Get the parameter list and adjust the widget
        obj = self.fv.imgsrv.getImageServer(key)
        b = self._setup_params(obj, self.w.img_params)
        self.image_server_params = b

        if redo:
            self.redo()

    def setup_params_catalog(self, combobox, redo=True):
        index = combobox.get_active()
        key = self.catalog_server_options[index]

        # Get the parameter list and adjust the widget
        obj = self.fv.imgsrv.getCatalogServer(key)
        b = self._setup_params(obj, self.w2.cat_params)
        self.catalog_server_params = b

        if redo:
            self.redo()
            
    def instructions(self):
        self.set_message("""TBD.""")
            
    def start(self, future=None):
        self.instructions()
        # start catalog operation
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)
            
        # Raise the params tab
        num = self.w.nb.page_num(self.w.params)
        self.w.nb.set_current_page(num)

        self.setfromimage()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        #self.fv.showStatus("Draw a rectangle with the right mouse button")
        
    def stop(self):
        # stop catalog operation
        self.clearAll()
        # remove the canvas from the image
        self.canvas.ui_setActive(False)
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        try:
            self.table.close()
        except:
            pass
        self.fv.showStatus("")
        
    def redo(self):
        obj = self.canvas.getObjectByTag(self.areatag)
        if obj.kind != 'rectangle':
            self.stop()
            return True
        
        try:
            image = self.fitsimage.get_image()

            # calculate center of bbox
            wd = obj.x2 - obj.x1
            dw = wd // 2
            ht = obj.y2 - obj.y1
            dh = ht // 2
            ctr_x, ctr_y = obj.x1 + dw, obj.y1 + dh
            ra_ctr, dec_ctr = image.pixtoradec(ctr_x, ctr_y, format='str')

            # Calculate RA and DEC for the three points
            # origination point
            ra_org, dec_org = image.pixtoradec(obj.x1, obj.y1)

            # destination point
            ra_dst, dec_dst = image.pixtoradec(obj.x2, obj.y2)

            # "heel" point making a right triangle
            ra_heel, dec_heel = image.pixtoradec(obj.x1, obj.y2)

            ht_deg = image.deltaStarsRaDecDeg(ra_org, dec_org, ra_heel, dec_heel)
            wd_deg = image.deltaStarsRaDecDeg(ra_heel, dec_heel, ra_dst, dec_dst)
            radius_deg = image.deltaStarsRaDecDeg(ra_heel, dec_heel, ra_dst, dec_dst)
            # width and height are specified in arcmin
            sgn, deg, mn, sec = wcs.degToDms(wd_deg)
            wd = deg*60.0 + float(mn) + sec/60.0
            sgn, deg, mn, sec = wcs.degToDms(ht_deg)
            ht = deg*60.0 + float(mn) + sec/60.0
            sgn, deg, mn, sec = wcs.degToDms(radius_deg)
            radius = deg*60.0 + float(mn) + sec/60.0
            
        except Exception, e:
            self.fv.showStatus('BAD WCS: %s' % str(e))
            return True

        # Copy the image parameters out to the widget
        d = { 'ra': ra_ctr, 'dec': dec_ctr, 'width': str(wd),
              'height': ht, 'r': radius, 'r2': radius,
              'r1': 0.0,
              }
        for bnch in (self.image_server_params,
                     self.catalog_server_params):
            if bnch != None:
                for key in bnch.keys():
                    if d.has_key(key):
                        bnch[key].set_text(str(d[key]))

        return True
    
    def btndown(self, canvas, button, data_x, data_y):
        pass

    def btnup(self, canvas, button, data_x, data_y):
        if not (button == 0x1):
            return
        
        objs = self.canvas.getItemsAt(data_x, data_y)
        for obj in objs:
            if (obj.tag != None) and obj.tag.startswith('star'):
                info = obj.get_data()
                self.table.show_selection(info.star)
                return True
    
    def highlight_object(self, obj, tag, color, redraw=True):
        x = obj.objects[0].x
        y = obj.objects[0].y
        delta = 10
        radius = obj.objects[0].radius + delta

        hilite = CanvasTypes.Circle(x, y, radius,
                                    linewidth=4, color=color)
        obj.add(hilite, tag=tag, redraw=redraw)
        
    def highlight_objects(self, objs, tag, color, redraw=True):
        for obj in objs:
            self.highlight_object(obj, tag, color, redraw=False)
        if redraw:
            self.canvas.redraw()
        
    def unhighlight_object(self, obj, tag):
        # delete the highlight ring of the former cursor object
        try:
            #hilite = obj.objects[2]
            obj.deleteObjectByTag(tag)
        except:
            pass
        
    def highlight_cursor(self, obj):
        if self.curstar:
            bnch = self.curstar
            if bnch.obj == obj:
                # <-- we are already highlighting this object
                return True

            # delete the highlight ring of the former cursor object
            self.unhighlight_object(bnch.obj, 'cursor')

        self.highlight_object(obj, 'cursor', self.color_cursor)
        self.curstar = Bunch.Bunch(obj=obj)
        self.canvas.redraw()
        

    def setfromimage(self):
        x1, y1 = 0, 0
        x2, y2 = self.fitsimage.get_data_size()
        tag = self.canvas.add(CanvasTypes.Rectangle(x1, y1, x2, y2,
                                                    color=self.mycolor))

        self.getarea(self.canvas, tag)
        
        
    def getarea(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if obj.kind != 'rectangle':
            return True

        if self.areatag:
            try:
                canvas.deleteObjectByTag(self.areatag)
            except:
                pass

        obj.color = self.mycolor
        obj.linestyle = 'solid'
        canvas.redraw(whence=3)

        self.areatag = tag
        # Raise the params tab
        num = self.w.nb.page_num(self.w.params)
        self.w.nb.set_current_page(num)
        return self.redo()

    def get_params(self, bnch):
        params = {}
        for key in bnch.keys():
            params[key] = bnch[key].get_text()
        return params

        
    def getimage_cb(self):
        params = self.get_params(self.image_server_params)

        index = self.w.server.get_active()
        server = self.image_server_options[index]

        self.clearAll()

        if self.use_dss_channel:
            chname = 'DSS'
            if not self.fv.has_channel(chname):
                self.fv.add_channel(chname)
        else:
            chname = self.fv.get_channelName(self.fitsimage)

        self.fitsimage.onscreen_message("Querying image db...",
                                        delay=1.0)

        # Offload this network task to a non-gui thread
        self.fv.nongui_do(self.getimage, server, params, chname)

    def getimage(self, server, params, chname):
        fitspath = self.fv.get_sky_image(server, params)

        self.fv.load_file(fitspath, chname=chname)

        # Update the GUI
        def getimage_update(self):
            self.setfromimage()
            self.redo()

        self.fv.gui_do(getimage_update)

    def getcatalog_cb(self):
        params = self.get_params(self.catalog_server_params)

        index = self.w2.server.get_active()
        server = self.catalog_server_options[index]

        obj = None
        if self.limit_stars_to_area:
            # Look for the defining object to filter stars
            # If none, then use the visible image area
            try:
                obj = self.canvas.getObjectByTag(self.areatag)
            
            except KeyError:
                pass
            
        self.reset()
        self.fitsimage.onscreen_message("Querying catalog db...",
                                        delay=1.0)
        # Offload this network task to a non-gui thread
        self.fv.nongui_do(self.getcatalog, server, params, obj)

    def getcatalog(self, server, params, obj):
        starlist, info = self.fv.get_catalog(server, params)
        self.logger.debug("starlist=%s" % str(starlist))

        starlist = self.filter_results(starlist, obj)

        # Update the GUI
        self.fv.gui_do(self.update_catalog, starlist, info)
        
    def update_catalog(self, starlist, info):
        self.starlist = starlist
        self.table.show_table(self, info, starlist)

        # Raise the listing tab
        num = self.w.nb.page_num(self.w.listing)
        self.w.nb.set_current_page(num)

        self._update_plotscroll()

    def filter_results(self, starlist, filter_obj):
        image = self.fitsimage.get_image()

        # Filter starts by a containing object, if provided
        if filter_obj:
            stars = []
            for star in starlist:
                x, y = image.radectopix(star['ra_deg'], star['dec_deg'])
                if filter_obj.contains(x, y):
                    stars.append(star)
            starlist = stars

        return starlist

    def clear(self):
        objects = self.canvas.getObjectsByTagpfx('star')
        self.canvas.deleteObjects(objects)
       
    def clearAll(self):
        self.canvas.deleteAllObjects()
       
    def reset(self):
        #self.clear()
        self.clearAll()
        self.table.clear()
       
    def plot_star(self, obj, image=None):
        if not image:
            image = self.fitsimage.get_image()
        x, y = image.radectopix(obj['ra_deg'], obj['dec_deg'])
        #print "STAR at %d,%d" % (x, y)
        # TODO: auto-pick a decent radius
        radius = 10
        color = self.table.get_color(obj)
        #print "color is %s" % str(color)
        circle = CanvasTypes.Circle(x, y, radius, color=color)
        point = CanvasTypes.Point(x, y, radius, color=color)
        ## What is this from?
        if obj.has_key('pick'):
            # Some objects returned from the Gen2 star catalog are marked
            # with the attribute 'pick'.  If present then we show the
            # star with or without the cross, otherwise we always show the
            # cross
            if not obj['pick']:
                star = CanvasTypes.Canvas(circle, point)
            else:
                star = CanvasTypes.Canvas(circle)
        else:
            star = CanvasTypes.Canvas(circle, point)
        star.set_data(star=obj)
        obj.canvobj = star

        self.canvas.add(star, tagpfx='star', redraw=False)

    def replot_stars(self, selected=[]):
        self.clear()

        image = self.fitsimage.get_image()
        canvas = self.canvas

        length = len(self.starlist)
        if length <= self.plot_limit:
            i = 0
        else:
            i = self.plot_start
            i = int(min(i, length - self.plot_limit))
            length = self.plot_limit

        # remove references to old objects before this range
        for j in xrange(i):
            obj = self.starlist[j]
            obj.canvobj = None

        # plot stars in range
        for j in xrange(length):
            obj = self.starlist[i]
            i += 1
            self.plot_star(obj, image=image)

        # remove references to old objects after this range
        for j in xrange(i, length):
            obj = self.starlist[j]
            obj.canvobj = None

        # plot stars in selected list even if they are not in the range
        #for obj in selected:
        selected = self.table.get_selected()
        for obj in selected:
            if (not obj.has_key('canvobj')) or (obj.canvobj == None):
                self.plot_star(obj, image=image)
            self.highlight_object(obj.canvobj, 'selected', 'skyblue')
            
        canvas.redraw(whence=3)

        
    def __str__(self):
        return 'catalogs'
    

class CatalogListing(object):
    
    def __init__(self, logger, container):
        self.logger = logger
        self.tag = None
        self.mycolor = 'skyblue'
        self.magmap = 'stairs8'

        self.mag_max = 25.0
        self.mag_min = 0.0

        # keys: are name, ra, dec, mag, flag, b_r, preference, priority, dst
        # TODO: automate this generation
        self.columns = [('Name', 'name'),
                        ('RA', 'ra'),
                        ('DEC', 'dec'),
                        ('Mag', 'mag'),
                        ('Preference', 'preference'),
                        ('Priority', 'priority'),
                        ('Flag', 'flag'),
                        ('b-r', 'b_r'),
                        ('Dst', 'dst'),
                        ('Description', 'description'),
                        ]
        self.cell_sort_funcs = []
        for kwd, key in self.columns:
            self.cell_sort_funcs.append(self._mksrtfnN(key))

        self.catalog = None
        self.cursor = 0
        self.color_cursor = 'red'
        self.color_selected = 'skyblue'
        self.selection_mode = 'single'
        self.selected = []
        self.moving_cursor = False

        self.btn = Bunch.Bunch()

        self.mframe = container
            
        vbox = gtk.VBox()

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        #self.font = pango.FontDescription('Monospace 10')
        
        # create the TreeView
        treeview = gtk.TreeView()
        self.treeview = treeview
        
        # create the TreeViewColumns to display the data
        tvcolumn = [None] * len(self.columns)
        for n in range(0, len(self.columns)):
            cell = gtk.CellRendererText()
            cell.set_padding(2, 0)
            header, kwd = self.columns[n]
            tvc = gtk.TreeViewColumn(header, cell)
            tvc.set_spacing(4)
            tvc.set_resizable(True)
            tvc.connect('clicked', self.sort_cb, n)
            tvc.set_clickable(True)
            tvcolumn[n] = tvc
            fn_data = self._mkcolfnN(kwd)
            tvcolumn[n].set_cell_data_func(cell, fn_data)
            treeview.append_column(tvcolumn[n])

        sw.add(treeview)
        self.treeview.connect('cursor-changed', self.select_star)
        sw.show_all()
        vbox.pack_start(sw, fill=True, expand=True)

        self.cbar = ColorBar.ColorBar(self.logger)
        self.cmap = cmap.get_cmap(self.magmap)
        self.imap = imap.get_imap('ramp')
        self.cbar.set_cmap(self.cmap)
        self.cbar.set_imap(self.imap)
        self.cbar.set_size_request(-1, 20)

        vbox.pack_start(self.cbar, padding=4, fill=True, expand=False)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_CENTER)
        btns.set_spacing(5)

        for name in ('Plot', 'Clear', #'Close'
                     ):
            btn = gtk.Button(name)
            btns.add(btn)
            self.btn[name.lower()] = btn

        self.btn.plot.connect('clicked', lambda w: self.replot_stars())
        self.btn.clear.connect('clicked', lambda w: self.clear())
        #self.btn.close.connect('clicked', lambda w: self.close())

        vbox.pack_start(btns, padding=4, fill=True, expand=False)
        vbox.show_all()
        
        self.mframe.pack_start(vbox, expand=True, fill=True)
        self.mframe.show_all()

    def _mkcolfnN(self, kwd):
        def fn(column, cell, model, iter):
            bnch = model.get_value(iter, 0)
            cell.set_property('text', bnch[kwd])
        return fn

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

    def show_table(self, catalog, info, starlist):
        self.starlist = starlist
        self.catalog = catalog
        # info is ignored, for now
        #self.info = info
        self.selected = []

        # Update the starlist info
        listmodel = gtk.ListStore(object)
        for star in starlist:
            # TODO: find mag range
            listmodel.append([star])

        self.treeview.set_model(listmodel)

        self.cbar.set_range(self.mag_min, self.mag_max)


    def get_color(self, obj):
        try:
            mag = obj['mag']
        except:
            return self.mycolor

        # clip magnitude to the range we have defined
        mag = max(self.mag_min, mag)
        mag = min(self.mag_max, mag)

        # calculate percentage in range
        point = float(mag) / float(self.mag_max - self.mag_min)
        # invert
        #point = 1.0 - point
        # map to a 8-bit color range
        point = int(point * 255.0)

        # Apply colormap.  
        rgbmap = self.cbar.get_rgbmap()
        (r, g, b) = rgbmap.get_rgbval(point)
        r = float(r) / 255.0
        g = float(g) / 255.0
        b = float(b) / 255.0
        return (r, g, b)

    def mark_selection(self, star, fromtable=False):
        """Mark or unmark a star as selected.  (fromtable)==True if the
        selection action came from the table (instead of the star plot).
        """
        self.logger.debug("star selected name=%s ra=%s dec=%s" % (
            star['name'], star['ra'], star['dec']))

        if star in self.selected:
            # Item is already selected--so unselect it
            self.selected.remove(star)
            try:
                self._unselect_tv(star)
                self.catalog.unhighlight_object(star.canvobj, 'selected')
            except Exception, e:
                self.logger.warn("Error unhilighting star: %s" % (str(e)))
            return False
        else:
            if self.selection_mode == 'single':
                # if selection mode is 'single' unselect any existing selections
                for star2 in self.selected:
                    self.selected.remove(star2)
                    try:
                        self._unselect_tv(star2)
                        self.catalog.unhighlight_object(star2.canvobj, 'selected')
                    except Exception, e:
                        self.logger.warn("Error unhilighting star: %s" % (str(e)))
            self.selected.append(star)
            try:
                # If this star is not plotted, then plot it
                if (not star.has_key('canvobj')) or (star.canvobj == None):
                    self.catalog.plot_star(star)
                    
                self._select_tv(star, fromtable=fromtable)
                self.catalog.highlight_object(star.canvobj, 'selected', 'skyblue')
            except Exception, e:
                self.logger.warn("Error hilighting star: %s" % (str(e)))
            return True


    def show_selection(self, star):
        """This method is called when the user clicks on a plotted star in the
        fitsviewer.
        """
        self.mark_selection(star)

    def _select_tv(self, star, fromtable=False):
        treeselection = self.treeview.get_selection()
        star_idx = self.starlist.index(star)
        treeselection.select_path(star_idx)
        if not fromtable:
            # If the user did not select the star from the table, scroll
            # the table so they can see the selection
            self.treeview.scroll_to_cell(star_idx, use_align=True, row_align=0.5)

    def _unselect_tv(self, star):
        treeselection = self.treeview.get_selection()
        star_idx = self.starlist.index(star)
        treeselection.unselect_path(star_idx)

    def clear(self):
        try:
            self.catalog.clear()
        except Exception, e:
            # may not have generated a catalog yet
            self.logger.warn("Error clearing star table: %s" % (str(e)))

    def get_selected(self):
        return self.selected
    
    def replot_stars(self):
        self.catalog.replot_stars()
        canvobjs = map(lambda star: star.canvobj, self.selected)
        self.catalog.highlight_objects(canvobjs, 'selected', 'skyblue')
            
    def select_star(self, treeview):
        """This method is called when the user selects a star from the table.
        """
        path, column = treeview.get_cursor()
        model = treeview.get_model()
        iter = model.get_iter(path)
        star = model.get_value(iter, 0)
        self.logger.debug("selected star: %s" % (str(star)))
        self.mark_selection(star, fromtable=True)
        return True
    

    def motion_notify_event(self, widget, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x, y, state = event.x, event.y, event.state

        buf_x1, buf_y1 = self.tw.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT,
                                                         x, y)
        txtiter = self.tw.get_iter_at_location(buf_x1, buf_y1)

        line = txtiter.get_line()
        star = self.line_to_object(line)
        
        if star == self.cursor:
            return True
        
        self._mark_cursor(star)
        try:
            self.catalog.highlight_cursor(star.canvobj)
        except:
            pass
        return True
        

# END
