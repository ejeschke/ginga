# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
A plugin for plotting object locations from a catalog on an image.

**Plugin Type: Local**

``Catalogs`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**
Draw a shape on the displayed image and adjust search parameters as desired.
When you are ready, press on the button to perform the search.
When search results are available, they will be displayed on the image and
also listed in a table on the plugin GUI. You can click on either the table
or the image to highlight selection.

**Defining catalogs**

You can customize the catalogs used by copying the ``plugin_Catalogs.cfg``
from the example configurations directory to your ``$HOME/.ginga`` directory and
modifying the ``catalog_sources`` table defined inside.

The format of this option is a list of dicts, where each dict defines a
source and has the following fields:

* ``shortname``: str, the short name appearing in the control for selecting
  a source in the plugin.  This is the name that will appear in the
  drop-down menu in the catalogs control area of the GUI
* ``fullname``: str, the full name, should correspond *exactly* with the
  name required by the ``astroquery.vo_conesearch`` ``catalog`` parameter
* ``type``: str, should be "astroquery.vo_conesearch" for an ``astroquery.vo_conesearch``
  function
* ``mapping``: dict, a nested dict providing the mapping for the return results
  to the GUI, in terms of field name to Ginga table.  In each source dict,
  there must be keys for 'id', 'ra', and 'dec'. 'mag', if present, can be a
  list of field names that define magnitudes of the elements in various
  wavelengths.

"""
import os
import math
from collections import OrderedDict

import numpy as np

from ginga.misc import Bunch
from ginga import GingaPlugin
from ginga import cmap, imap
from ginga.util import wcs, catalog
from ginga.gw import ColorBar, Widgets

__all__ = ['Catalogs']


default_catalog_sources = [
    {'shortname': "GSC 2.3", 'fullname': "Guide Star Catalog 2.3 Cone Search 1",
     'type': 'astroquery.vo_conesearch',
     'mapping': {'id': 'objID', 'ra': 'ra', 'dec': 'dec', 'mag': ['Mag']}},
    {'shortname': "USNO-A2.0 1", 'fullname': "The USNO-A2.0 Catalogue (Monet+ 1998) 1",
     'type': 'astroquery.vo_conesearch',
     'mapping': {'id': 'USNO-A2.0', 'ra': 'RAJ2000', 'dec': 'DEJ2000', 'mag': ['Bmag', 'Rmag']}},
    {'shortname': "2MASS 1", 'fullname': "Two Micron All Sky Survey (2MASS) 1",
     'type': 'astroquery.vo_conesearch',
     'mapping': {'id': 'htmID', 'ra': 'ra', 'dec': 'dec', 'mag': []}},
]


default_image_sources = []


class Catalogs(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        super(Catalogs, self).__init__(fv, fitsimage)

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Catalogs')
        self.settings.add_defaults(draw_type='circle',
                                   select_color='skyblue',
                                   color_outline='aquamarine',
                                   click_radius=10,
                                   catalog_sources=default_catalog_sources,
                                   image_sources=default_image_sources)
        self.settings.load(onError='silent')

        self.limit_stars_to_area = False
        self.pan_to_selected = False
        self.use_dss_channel = False
        self.dsscnt = 0
        self.plot_max = 500
        self.plot_limit = 100
        self.plot_start = 0
        self.drawtype = self.settings.get('draw_type', 'circle')

        # star list
        self.starlist = []
        # catalog listing
        self.table = None

        self.color_outline = self.settings.get('color_outline', 'aquamarine')
        self.layertag = 'catalog-canvas'
        self.areatag = None

        self.image_server_options = []
        self.image_server_params = None

        self.catalog_server_options = []
        self.catalog_server_params = None

        self.dc = fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype(self.drawtype, color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_surface(self.fitsimage)
        canvas.set_draw_mode('draw')
        self.canvas = canvas

        self.color_selected = self.settings.get('select_color', 'skyblue')
        self.hilite = None
        self.gui_up = False

        bank = self.fv.get_ServerBank()

        # add catalogs found in configuration file
        catalogs = self.settings.get('catalog_sources', [])
        for d in catalogs:
            typ = d.get('type', None)
            obj = None
            if typ == 'astroquery.vo_conesearch':
                obj = catalog.AstroqueryVOCatalogServer(self.logger, d['fullname'],
                                                        d['shortname'], d['mapping'],
                                                        d['fullname'])
            else:
                self.logger.debug("Unknown type ({}) specified for catalog--skipping".format(typ))

            if obj is not None:
                bank.addCatalogServer(obj)

        # add image servers found in configuration file
        catalogs = self.settings.get('image_sources', [])
        for d in catalogs:
            typ = d.get('type', None)
            obj = None
            if typ == 'astroquery':
                obj = catalog.AstroqueryVOCatalogServer(self.logger, d['fullname'],
                                                        d['shortname'], d['mapping'],
                                                        d['fullname'])
            else:
                self.logger.debug("Unknown type ({}) specified for catalog--skipping".format(typ))

            if obj is not None:
                bank.addCatalogServer(obj)

    def build_gui(self, container, future=None):
        vbox1 = Widgets.VBox()

        nb = Widgets.TabWidget(tabpos='bottom')
        self.w.nb = nb
        vbox1.add_widget(nb, stretch=1)

        vbox0 = Widgets.VBox()

        hbox = Widgets.HBox()
        hbox.set_spacing(4)
        vbox0.add_widget(hbox, stretch=1)

        vbox = Widgets.VBox()
        fr = Widgets.Frame(" Image Server ")
        fr.set_widget(vbox)
        hbox.add_widget(fr, stretch=0)

        captions = (('Server:', 'llabel'),
                    ('Server', 'combobox'),
                    ('Use DSS channel', 'checkbutton'),
                    ('Get Image', 'button'))
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        self.w.get_image.add_callback('activated',
                                      lambda w: self.getimage_cb())
        self.w.use_dss_channel.set_state(self.use_dss_channel)
        self.w.use_dss_channel.add_callback(
            'activated', self.use_dss_channel_cb)

        vbox.add_widget(w, stretch=0)

        self.w.img_params = Widgets.StackWidget()
        vbox.add_widget(self.w.img_params, stretch=1)

        combobox = self.w.server
        index = 0
        self.image_server_options = self.fv.imgsrv.getServerNames(kind='image')
        for name in self.image_server_options:
            combobox.append_text(name)
            index += 1
        index = 0
        combobox.set_index(index)
        combobox.add_callback('activated',
                              lambda w, idx: self.setup_params_image(idx))
        if len(self.image_server_options) > 0:
            self.setup_params_image(index, redo=False)

        vbox = Widgets.VBox()
        fr = Widgets.Frame(" Catalog Server ")
        fr.set_widget(vbox)
        hbox.add_widget(fr, stretch=0)

        captions = (('Server:', 'llabel'),
                    ('Server', 'combobox'),
                    ('Limit stars to area', 'checkbutton'),
                    ('Search', 'button'))
        w, self.w2 = Widgets.build_info(captions)
        self.w2.search.add_callback('activated',
                                    lambda w: self.getcatalog_cb())
        self.w2.limit_stars_to_area.set_state(self.limit_stars_to_area)
        self.w2.limit_stars_to_area.add_callback('activated',
                                                 self.limit_area_cb)

        vbox.add_widget(w, stretch=0)

        self.w2.cat_params = Widgets.StackWidget()
        vbox.add_widget(self.w2.cat_params, stretch=1)

        combobox = self.w2.server
        index = 0
        self.catalog_server_options = self.fv.imgsrv.getServerNames(
            kind='catalog')
        for name in self.catalog_server_options:
            combobox.append_text(name)
            index += 1
        index = 0
        combobox.set_index(index)
        combobox.add_callback('activated',
                              lambda w, idx: self.setup_params_catalog(idx))
        if len(self.catalog_server_options) > 0:
            self.setup_params_catalog(index, redo=False)

        # stretch
        vbox0.add_widget(Widgets.Label(''), stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(5)

        btn1 = Widgets.RadioButton("Rectangle")
        btn1.set_state(self.drawtype == 'rectangle')
        btn1.add_callback('activated',
                          lambda w, tf: self.set_drawtype_cb(tf, 'rectangle'))
        btns.add_widget(btn1, stretch=0)
        btn2 = Widgets.RadioButton("Circle", group=btn1)
        btn2.set_state(self.drawtype == 'circle')
        btn2.add_callback('activated',
                          lambda w, tf: self.set_drawtype_cb(tf, 'circle'))
        btns.add_widget(btn2, stretch=0)
        btn = Widgets.Button("Entire image")
        btn.add_callback('activated', lambda w: self.setfromimage())
        btns.add_widget(btn, stretch=0)
        vbox0.add_widget(btns, stretch=0)

        mode = self.canvas.get_draw_mode()
        btns = Widgets.HBox()
        btns.set_spacing(5)

        btn1 = Widgets.RadioButton("Select")
        btn1.set_state(mode == 'select')
        btn1.add_callback('activated',
                          lambda w, val: self.set_mode_cb('select', val))
        btn1.set_tooltip("Choose this to highlight selection on table")
        self.w.btn_select = btn1
        btns.add_widget(btn1, stretch=0)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback('activated',
                          lambda w, val: self.set_mode_cb('draw', val))
        btn2.set_tooltip("Choose this to define search region")
        self.w.btn_draw = btn2
        btns.add_widget(btn2, stretch=0)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback('activated', lambda w, val: self.set_mode_cb('edit', val))
        btn3.set_tooltip("Choose this to edit or move a region")
        self.w.btn_edit = btn3
        btns.add_widget(btn3)

        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox0.add_widget(btns, stretch=0)

        self.w.params = vbox0

        sw = Widgets.ScrollArea()
        sw.set_widget(vbox0)

        nb.add_widget(sw, title="Params")

        vbox = Widgets.VBox()
        self.table = CatalogListing(self.logger, vbox)

        hbox = Widgets.HBox()
        adj = Widgets.Slider(orientation='horizontal')
        adj.set_limits(0, 1000, incr_value=1)
        adj.set_value(0)
        #adj.resize(200, -1)
        adj.set_tracking(True)
        adj.set_tooltip("Choose subset of stars plotted")
        self.w.plotgrp = adj
        adj.add_callback('value-changed', self.plot_pct_cb)
        hbox.add_widget(adj, stretch=1)

        sb = Widgets.SpinBox(dtype=int)
        sb.set_limits(10, self.plot_max, incr_value=10)
        sb.set_value(self.plot_limit)
        #sb.set_wrapping(False)
        self.w.plotnum = sb
        sb.set_tooltip("Adjust size of subset of stars plotted")
        sb.add_callback('value-changed', self.plot_limit_cb)
        hbox.add_widget(sb, stretch=0)

        vbox.add_widget(hbox, stretch=0)
        self.w.listing = vbox
        nb.add_widget(vbox, title="Listing")

        btns = Widgets.HBox()
        btns.set_spacing(3)
        self.w.buttons = btns

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)

        if future:
            btn = Widgets.Button('Ok')
            btn.add_callback('activated', lambda w: self.ok())
            btns.add_widget(btn, stretch=0)
            btn = Widgets.Button('Cancel')
            btn.add_callback('activated', lambda w: self.cancel())
            btns.add_widget(btn, stretch=0)

        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vbox1.add_widget(btns, stretch=0)

        container.add_widget(vbox1, stretch=1)
        self.gui_up = True

    def ok(self):
        return self.close()

    def cancel(self):
        return self.close()

    def update_gui(self):
        self.fv.update_pending()

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self, future=None):
        # start catalog operation
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)
        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        # Raise the params tab
        self._raise_tab(self.w.params)

        self.setfromimage()
        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        #self.fv.show_status("Draw a rectangle with the right mouse button")

    def stop(self):
        # stop catalog operation
        try:
            self.clear_all()
        except Exception:
            pass
        # remove the canvas from the image
        self.canvas.ui_set_active(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        try:
            self.table.close()
        except Exception:
            pass
        self.gui_up = False
        self.fv.show_status("")

    def redo(self):
        try:
            obj = self.canvas.get_object_by_tag(self.areatag)
        except Exception:
            return True
        if obj.kind not in ('rectangle', 'circle'):
            return True

        try:
            image = self.fitsimage.get_image()

            if obj.kind == 'rectangle':
                # if the object drawn is a rectangle, calculate the radius
                # of a circle necessary to cover the area
                # calculate center of bbox
                x1, y1, x2, y2 = obj.get_llur()
                wd = x2 - x1
                dw = wd // 2
                ht = y2 - y1
                dh = ht // 2
                ctr_x, ctr_y = x1 + dw, y1 + dh
                ra_ctr_deg, dec_ctr_deg = image.pixtoradec(ctr_x, ctr_y)
                ra_ctr, dec_ctr = image.pixtoradec(ctr_x, ctr_y, format='str')

                # Calculate RA and DEC for the three points
                # origination point
                ra_org, dec_org = image.pixtoradec(x1, y1)

                # destination point
                ra_dst, dec_dst = image.pixtoradec(x2, y2)

                # "heel" point making a right triangle
                ra_heel, dec_heel = image.pixtoradec(x1, y2)

                ht_deg = wcs.deltaStarsRaDecDeg(ra_org, dec_org,
                                                ra_heel, dec_heel)
                wd_deg = wcs.deltaStarsRaDecDeg(ra_heel, dec_heel,
                                                ra_dst, dec_dst)
                radius_deg = wcs.deltaStarsRaDecDeg(ra_heel, dec_heel,
                                                    ra_dst, dec_dst)
            else:
                # if the object drawn is a circle, calculate the box
                # enclosed by the circle
                ctr_x, ctr_y = obj.crdmap.to_data((obj.x, obj.y))
                ra_ctr, dec_ctr = image.pixtoradec(ctr_x, ctr_y)
                ra_ctr_deg, dec_ctr_deg = ra_ctr, dec_ctr
                dst_x, dst_y = obj.crdmap.to_data((obj.x + obj.radius, obj.y))
                ra_dst, dec_dst = image.pixtoradec(dst_x, dst_y)
                radius_deg = wcs.deltaStarsRaDecDeg(ra_ctr, dec_ctr,
                                                    ra_dst, dec_dst)
                # redo as str format for widget
                ra_ctr, dec_ctr = image.pixtoradec(ctr_x, ctr_y, format='str')

                wd = ht = math.fabs(dst_x - ctr_x) * 2.0
                dw = wd // 2
                dh = ht // 2

                ra_org, dec_org = image.pixtoradec(ctr_x, ctr_y - dh)
                ra_dst, dec_dst = image.pixtoradec(ctr_x, ctr_y + dh)
                ht_deg = wcs.deltaStarsRaDecDeg(ra_org, dec_org,
                                                ra_dst, dec_dst)
                ra_org, dec_org = image.pixtoradec(ctr_x - dw, ctr_y)
                ra_dst, dec_dst = image.pixtoradec(ctr_x + dw, ctr_y)
                wd_deg = wcs.deltaStarsRaDecDeg(ra_org, dec_org,
                                                ra_dst, dec_dst)

            # width and height are specified in arcmin
            sgn, deg, mn, sec = wcs.degToDms(wd_deg)
            wd = deg * 60.0 + float(mn) + sec / 60.0
            sgn, deg, mn, sec = wcs.degToDms(ht_deg)
            ht = deg * 60.0 + float(mn) + sec / 60.0
            sgn, deg, mn, sec = wcs.degToDms(radius_deg)
            radius = deg * 60.0 + float(mn) + sec / 60.0
            #wd, ht, radius = wd_deg, ht_deg, radius_deg

        except Exception as e:
            errmsg = 'Error calculating bounding box: %s' % str(e)
            self.logger.error(errmsg)
            self.fv.show_error(errmsg)
            return True

        # Copy the image parameters out to the widget
        d = {'ra': ra_ctr, 'dec': dec_ctr, 'width': str(wd),
             'ra_deg': ra_ctr_deg, 'dec_deg': dec_ctr_deg,
             'height': ht, 'r': radius, 'r2': radius,
             'r1': 0.0}
        self._update_widgets(d)
        return True

    def edit_select_region(self):
        if self.areatag is not None:
            obj = self.canvas.get_object_by_tag(self.areatag)
            self.canvas.edit_select(obj)
        else:
            self.canvas.clear_selected()
        self.canvas.update_canvas()

    def set_mode_cb(self, mode, tf):
        """Called when one of the Select/Draw/Edit radio buttons is selected."""
        if tf:
            if mode == 'select':
                mode = 'pick'
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_select_region()
        return True

    def set_mode(self, mode):
        if mode == 'select':
            mode = 'pick'
        self.canvas.set_draw_mode(mode)
        self.w.btn_select.set_state(mode == 'pick')
        self.w.btn_draw.set_state(mode == 'draw')
        self.w.btn_edit.set_state(mode == 'edit')

    def highlight_object(self, obj, tag, color, redraw=True):
        x = obj.objects[0].x
        y = obj.objects[0].y
        delta = 10
        radius = obj.objects[0].radius + delta

        hilite = self.dc.Circle(x, y, radius, linewidth=4, color=color)
        hilite.editable = False
        self.hilite.add_object(hilite)
        if redraw:
            self.canvas.update_canvas()

    def update_selected(self, redraw=True):
        if self.hilite is None:
            self.hilite = self.dc.CompoundObject()
        if not self.canvas.has_object(self.hilite):
            self.canvas.add(self.hilite, tag='selected', redraw=False)

        self.hilite.delete_all_objects()

        image = self.fitsimage.get_image()
        selected = self.table.get_selected()
        for obj in selected:
            # plot stars in selected list even if they are not in the range
            if ('canvobj' not in obj) or (obj.canvobj is None):
                self.plot_star(obj, image=image)

            # add highlight ring to selected stars
            self.highlight_object(obj.canvobj, 'selected',
                                  self.color_selected)

        if redraw:
            self.canvas.update_canvas()

    def setfromimage(self):
        image = self.fitsimage.get_image()
        if image is None:
            return
        x1, y1 = 0, 0
        x2, y2 = self.fitsimage.get_data_size()
        tag = self.canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                color=self.color_outline))

        self.draw_cb(self.canvas, tag)

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        if obj.kind not in ('rectangle', 'circle'):
            return True

        if self.areatag:
            try:
                canvas.delete_object_by_tag(self.areatag)
            except Exception:
                pass

        obj.color = self.color_outline
        obj.linestyle = 'solid'
        canvas.update_canvas()

        self.areatag = tag
        # Raise the params tab
        self._raise_tab(self.w.params)
        return self.redo()

    def edit_cb(self, canvas, obj):
        if self.areatag is not None:
            obj2 = canvas.get_object_by_tag(self.areatag)
            if obj != obj2:
                # Not editing the area
                return

        # Raise the params tab
        self._raise_tab(self.w.params)
        return self.redo()

    def getimage_cb(self):
        params = self.get_params(self.image_server_params)

        index = self._get_cbidx(self.w.server)
        server = self.image_server_options[index]

        self.clear_all()

        if self.use_dss_channel:
            chname = 'DSS'
            if not self.fv.has_channel(chname):
                self.fv.add_channel(chname)
        else:
            chname = self.chname

        self.fitsimage.onscreen_message("Querying image db...",
                                        delay=1.0)

        # Offload this network task to a non-gui thread
        self.fv.nongui_do(self.getimage, server, params, chname)

    def get_sky_image(self, servername, params):

        srvbank = self.fv.get_server_bank()
        #filename = 'sky-' + str(time.time()).replace('.', '-') + '.fits'
        filename = 'sky-' + str(self.dsscnt) + '.fits'
        self.dsscnt = (self.dsscnt + 1) % 5
        filepath = os.path.join(self.fv.tmpdir, filename)
        try:
            os.remove(filepath)
        except Exception as e:
            self.logger.error("failed to remove tmp file '%s': %s" % (
                filepath, str(e)))
        try:
            dstpath = srvbank.getImage(servername, filepath, **params)
            return dstpath

        except Exception as e:
            errmsg = "Failed to load sky image: %s" % (str(e))
            raise Exception(errmsg)

    def getimage(self, server, params, chname):
        try:
            fitspath = self.get_sky_image(server, params)

        except Exception as e:
            errmsg = "Query exception: %s" % (str(e))
            self.logger.error(errmsg)
            # pop up the error in the GUI under "Errors" tab
            self.fv.gui_do(self.fv.show_error, errmsg)
            return

        self.fv.load_file(fitspath, chname=chname)

        # Update the GUI
        def getimage_update():
            self.setfromimage()
            self.redo()

        self.fv.gui_do(getimage_update)

    def getcatalog_cb(self):
        params = self.get_params(self.catalog_server_params)

        index = self._get_cbidx(self.w2.server)
        server = self.catalog_server_options[index]

        obj = None
        if self.limit_stars_to_area:
            # Look for the defining object to filter stars
            # If none, then use the visible image area
            try:
                obj = self.canvas.get_object_by_tag(self.areatag)

            except KeyError:
                pass

        self.reset()
        self.fitsimage.onscreen_message("Querying catalog db...",
                                        delay=1.0)
        # Offload this network task to a non-gui thread
        self.fv.nongui_do(self.getcatalog, server, params, obj)

    def _get_catalog(self, srvbank, key, params):
        try:
            starlist, info = srvbank.getCatalog(key, None, **params)
            return starlist, info

        except Exception as e:
            errmsg = "Failed to load catalog: %s" % (str(e))
            raise Exception(errmsg)

    def getcatalog(self, server, params, obj):
        try:
            srvbank = self.fv.get_server_bank()
            starlist, info = self._get_catalog(srvbank, server, params)
            self.logger.debug("starlist=%s" % str(starlist))

            starlist = self.filter_results(starlist, obj)

            # Update the GUI
            self.fv.gui_do(self.update_catalog, starlist, info)

        except Exception as e:
            errmsg = "Query exception: %s" % (str(e))
            self.logger.error(errmsg)
            # pop up the error in the GUI under "Errors" tab
            self.fv.gui_do(self.fv.show_error, errmsg)

    def update_catalog(self, starlist, info):
        self.starlist = starlist
        self.table.show_table(self, info, starlist)

        # Raise the listing tab
        self._raise_tab(self.w.listing)

        self._update_plotscroll()
        self.set_mode('select')

    def filter_results(self, starlist, filter_obj):
        image = self.fitsimage.get_image()

        # Filter starts by a containing object, if provided
        if filter_obj:
            num_cat = len(starlist)
            self.logger.debug("number of incoming stars=%d" % (num_cat))
            coords = np.asarray([(star['ra_deg'], star['dec_deg'])
                                 for star in starlist])

            # vectorized wcs transform to data coords
            coords = image.wcs.wcspt_to_datapt(coords)

            # vectorized test for inclusion in shape
            res = filter_obj.contains_pts(coords)
            self.logger.debug("res.shape = %s" % str(res.shape))

            stars = np.array(starlist)[np.flatnonzero(res)]
            self.logger.debug("number of filtered stars=%d" % (len(stars)))
            starlist = list(stars)

        return starlist

    def clear(self):
        objects = self.canvas.get_objects_by_tag_pfx('star')
        self.canvas.delete_objects(objects)
        self.canvas.delete_objects_by_tag(['selected'])

    def clear_all(self):
        self.canvas.delete_all_objects()
        self.set_mode('draw')

    def reset(self):
        self.clear()
        #self.clear_all()
        self.table.clear()

    def select_cb(self, obj, canvas, event, pt):
        if (obj.tag is not None) and obj.tag.startswith('star'):
            info = obj.get_data()
            self.table.show_selection(info.star)
            return True
        return True

    def plot_star(self, obj, image=None):

        if not image:
            image = self.fitsimage.get_image()
        x, y = image.radectopix(obj['ra_deg'], obj['dec_deg'])
        # TODO: auto-pick a decent radius
        radius = self.settings.get('click_radius', 10)
        color = self.table.get_color(obj)

        circle = self.dc.Circle(x, y, radius, color=color)
        circle.editable = False
        point = self.dc.Point(x, y, radius, color=color)
        point.editable = False

        ## What is this from?
        if 'pick' in obj:
            # Some objects returned from the star catalog are marked
            # with the attribute 'pick'.  If present then we show the
            # star with or without the cross, otherwise we always show the
            # cross
            if not obj['pick']:
                star = self.dc.Canvas(circle, point)
            else:
                star = self.dc.Canvas(circle)
        else:
            star = self.dc.Canvas(circle, point)

        star.pickable = True
        star.add_callback('pick-up', self.select_cb)
        star.opaque = True
        # see select_cb() above
        star.set_data(star=obj)
        obj.canvobj = star

        self.canvas.add(star, tagpfx='star', redraw=False)

    def pan_to_star(self, star):
        # Set pan position to star
        image = self.fitsimage.get_image()
        x, y = image.radectopix(star['ra_deg'], star['dec_deg'])
        self.fitsimage.panset_xy(x, y)

    def get_plot_range(self):
        length = len(self.starlist)
        if length <= self.plot_limit:
            i = 0
        else:
            i = self.plot_start
            i = int(min(i, length - self.plot_limit))
            length = self.plot_limit
        return (i, length)

    def replot_stars(self, selected=[]):
        self.clear()

        image = self.fitsimage.get_image()
        canvas = self.canvas

        # Set the color bar and plot color range based on the stars
        # we are plotting
        i, length = self.get_plot_range()
        self.table.set_minmax(i, length)

        # remove references to old plot objects from starlist
        for j in range(len(self.starlist)):
            obj = self.starlist[j]
            obj.canvobj = None

        # plot stars in range
        subset = self.table.get_subset_from_starlist(i, i + length)

        with self.fitsimage.suppress_redraw:
            for obj in subset:
                self.plot_star(obj, image=image)

            self.update_selected(redraw=False)

            canvas.update_canvas()

    def limit_area_cb(self, w, tf):
        self.limit_stars_to_area = tf
        return True

    def use_dss_channel_cb(self, w, tf):
        self.use_dss_channel = tf
        return True

    def plot_pct_cb(self, widget, val):
        #val = self.w.plotgrp.value()
        self.plot_start = int(val)
        self.replot_stars()
        return True

    def _update_plotscroll(self):
        num_stars = len(self.starlist)
        if num_stars > 0:
            adj = self.w.plotgrp
            #page_size = self.plot_limit
            self.plot_start = min(self.plot_start, num_stars - 1)
            adj.set_limits(0, num_stars, incr_value=1)

        self.replot_stars()

    def plot_limit_cb(self, widget, val):
        #val = self.w.plotnum.value()
        self.plot_limit = int(val)
        self._update_plotscroll()
        return True

    def set_message(self, msg):
        self.tw.set_text(msg)

    def _raise_tab(self, widget):
        index = self.w.nb.index_of(widget)
        if index >= 0:
            self.w.nb.set_index(index)

    def _get_cbidx(self, w):
        return w.get_index()

    def _setup_params(self, obj, container):
        params = obj.getParams()
        captions = []
        paramList = sorted(params.values(), key=lambda b: b.order)
        for bnch in paramList:
            text = bnch.name
            if 'label' in bnch:
                text = bnch.label
            #captions.append((text, 'entry'))
            captions.append((text + ':', 'label', bnch.name, 'entry'))

        # TODO: put RA/DEC first, and other stuff not in random orders
        w, b = Widgets.build_info(captions)

        # remove old widgets
        container.remove_all()

        # add new widgets
        container.add_widget(w)
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
                for key in list(bnch.keys()):
                    if key in d:
                        bnch[key].set_text(str(d[key]))

    def get_params(self, bnch):
        params = {}
        for key in list(bnch.keys()):
            params[key] = str(bnch[key].get_text())
        return params

    def set_drawtype_cb(self, tf, drawtype):
        if tf:
            self.drawtype = drawtype
            self.canvas.set_drawtype(self.drawtype, color='cyan',
                                     linestyle='dash')

    def __str__(self):
        return 'catalogs'


class CatalogListing(object):

    def __init__(self, logger, container):
        super(CatalogListing, self).__init__()

        self.logger = logger
        self.tag = None
        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        self.magcmap = 'stairs8'
        self.magimap = 'ramp'

        self.mag_field = 'mag'
        self.mag_max = 25.0
        self.mag_min = 0.0
        self.color_default = 'skyblue'

        # keys: are name, ra, dec, mag, flag, b_r, preference, priority, dst
        # TODO: automate this generation
        self.columns = [('Name', 'name'),
                        ('RA', 'ra'),
                        ('DEC', 'dec'),
                        ('Mag', 'mag'),
                        ('Preference', 'preference'),
                        ('Priority', 'priority'),
                        ('Description', 'description'),
                        ('Index', 'index'),
                        ]

        self.catalog = None
        self.cursor = 0
        self.color_selected = 'skyblue'
        self.selection_mode = 'single'
        self.selected = []
        self.moving_cursor = False

        self.btn = Bunch.Bunch()

        self.cmap = cmap.get_cmap(self.magcmap)
        self.imap = imap.get_imap('ramp')
        self.cbar_ht = 32

        self.operation_table = []
        self._select_flag = False

        self._build_gui(container)

    def get_color(self, obj):
        try:
            mag = obj[self.mag_field]
        except Exception:
            return self.color_default

        # calculate range of values
        rng = float(self.mag_max - self.mag_min)

        # clip magnitude to the range we have defined
        mag = max(self.mag_min, mag)
        mag = min(self.mag_max, mag)

        if rng != 0.0:
            point = float(mag - self.mag_min) / rng
        else:
            point = 1.0

        # sanity check: clip to 0-1 range
        point = max(0.0, point)
        point = min(1.0, point)

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
                # remove selection from table
                self._unselect_tv(star, fromtable=fromtable)
            except Exception as e:
                self.logger.warning("Error unhilighting star: %s" % (str(e)))

            self.catalog.update_selected()
            return False
        else:
            if self.selection_mode == 'single':
                # if selection mode is 'single' unselect any existing selection
                for star2 in self.selected:
                    self.selected.remove(star2)
                    try:
                        self._unselect_tv(star2, fromtable=fromtable)
                    except Exception as e:
                        self.logger.warning(
                            "Error unhilighting star: %s" % (str(e)))
            self.selected.append(star)
            try:
                # highlight line in table
                self._select_tv(star, fromtable=fromtable)
                if self.catalog.pan_to_selected:
                    self.catalog.pan_to_star(star)
            except Exception as e:
                self.logger.warning("Error hilighting star: %s" % (str(e)))

            self.catalog.update_selected()
            return True

    def show_selection(self, star):
        """This method is called when the user clicks on a plotted star in the
        fitsviewer.
        """
        try:
            # NOTE: this works around a quirk of Qt widget set where
            # selecting programatically in the table triggers the widget
            # selection callback (see select_star_cb() in Catalogs.py for Qt)
            self._select_flag = True
            self.mark_selection(star)

        finally:
            self._select_flag = False

    def clear(self):
        if self.catalog is not None:
            self.catalog.clear()

    def get_selected(self):
        return self.selected

    def replot_stars(self):
        if self.catalog is None:
            return
        self.catalog.replot_stars()

    def set_cmap_byname(self, name):
        # Get colormap
        cm = cmap.get_cmap(name)
        self.cbar.set_cmap(cm)
        self.replot_stars()

    def set_imap_byname(self, name):
        # Get intensity map
        im = imap.get_imap(name)
        self.cbar.set_imap(im)
        self.replot_stars()

    def set_minmax(self, i, length):
        subset = self.get_subset_from_starlist(i, i + length)
        values = list(map(lambda star: float(star[self.mag_field]),
                          subset))
        if len(values) > 0:
            self.mag_max = max(values)
            self.mag_min = min(values)
            self.cbar.set_range(self.mag_min, self.mag_max)

    def _set_field(self, name):
        # select new field to use for color plotting
        self.mag_field = name

        # determine the range of the values
        if self.catalog is not None:
            i, length = self.catalog.get_plot_range()
            self.set_minmax(i, length)

    def set_field(self, name):
        self._set_field(name)
        self.replot_stars()

    def add_operation(self, name, fn):
        self.operation_table.append((name, fn))

    def _build_gui(self, container):
        self.mframe = container

        vbox = Widgets.VBox()

        # create the table
        table = Widgets.TreeView(selection='single', sortable=True,
                                 use_alt_row_color=False)
        self.table = table
        table.add_callback('selected', self.select_star_cb)
        vbox.add_widget(table, stretch=1)

        self.cbar = ColorBar.ColorBar(self.logger)
        # hack to set font size of this color bar
        self.cbar.cbar.fontsize = 8
        self.cbar.set_cmap(self.cmap)
        self.cbar.set_imap(self.imap)
        rgbmap = self.cbar.get_rgbmap()
        rgbmap.add_callback('changed', lambda *args: self.replot_stars())

        cbar_w = self.cbar.get_widget()
        cbar_w.resize(-1, self.cbar_ht)
        vbox.add_widget(cbar_w, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(5)

        combobox = Widgets.ComboBox()
        options = []
        index = 0
        for name in self.cmap_names:
            options.append(name)
            combobox.append_text(name)
            index += 1
        cmap_name = self.magcmap
        try:
            index = self.cmap_names.index(cmap_name)
        except Exception:
            index = self.cmap_names.index('gray')
        combobox.set_index(index)
        combobox.add_callback(
            'activated', lambda w, idx: self.set_cmap_cb(idx))
        self.btn['cmap'] = combobox
        btns.add_widget(combobox, stretch=0)

        combobox = Widgets.ComboBox()
        options = []
        index = 0
        for name in self.imap_names:
            options.append(name)
            combobox.append_text(name)
            index += 1
        imap_name = self.magimap
        try:
            index = self.imap_names.index(imap_name)
        except Exception:
            index = self.imap_names.index('ramp')
        combobox.set_index(index)
        combobox.add_callback(
            'activated', lambda w, idx: self.set_imap_cb(idx))
        self.btn['imap'] = combobox
        btns.add_widget(combobox, stretch=0)

        combobox = Widgets.ComboBox()
        options = []
        index = 0
        for name, fn in self.operation_table:
            options.append(name)
            combobox.append_text(name)
            index += 1
        combobox.set_index(0)
        self.btn['oprn'] = combobox
        btns.add_widget(combobox, stretch=0)

        btn = Widgets.Button("Do it")
        btn.add_callback('activated', self.do_operation_cb, combobox)
        btns.add_widget(btn, stretch=0)

        vbox.add_widget(btns, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(5)

        for name in ('Plot', 'Clear'):  # 'Close'
            btn = Widgets.Button(name)
            btns.add_widget(btn, stretch=0)
            self.btn[name.lower()] = btn

        self.btn.plot.add_callback('activated',
                                   lambda w: self.replot_stars())
        self.btn.clear.add_callback('activated',
                                    lambda w: self.clear())
        #self.btn.close.add_callback('activated',
        #                            lambda w: self.close())

        combobox = Widgets.ComboBox()
        options = []
        index = 0
        for name in ['Mag']:
            options.append(name)
            combobox.append_text(name)
            index += 1
        combobox.set_index(0)
        combobox.add_callback('activated',
                              lambda w, idx: self.set_field_cb(idx))
        self.btn['field'] = combobox
        btns.add_widget(combobox, stretch=0)

        vbox.add_widget(btns, stretch=0)

        # create the table
        info = Bunch.Bunch(columns=self.columns, color='Mag')
        self.build_table(info)

        self.mframe.add_widget(vbox, stretch=1)

    def build_table(self, info):
        columns = info.columns
        self.columns = columns

        # Set up the field selector
        fidx = 0
        combobox = self.btn['field']
        combobox.clear()

        table = self.table
        table.clear()

        col = 0
        has_index = False
        for hdr, kwd in columns:
            combobox.append_text(hdr)
            if hdr == info.color:
                fidx = col
            if kwd == 'index':
                has_index = True
            col += 1

        if not has_index:
            columns.append(('Index', 'index'))

        table.setup_table(columns, 1, 'index')

        combobox.set_index(fidx)

        fieldname = self.columns[fidx][1]
        self.mag_field = fieldname

    def show_table(self, catalog, info, starlist):
        self.starlist = starlist
        self.catalog = catalog
        #self.info = info
        self.selected = []

        # rebuild table according to metadata
        self.build_table(info)

        # Use ordered dict so star list order is preserved if it is
        # significant coming in
        tree_dict = OrderedDict({})
        index = 0
        # TODO: have stars assigned a unique index coming in so we don't
        # have to do it here
        for star in starlist:
            key = str(index)
            star['index'] = key
            index += 1
            tree_dict[key] = star

        self.table.set_tree(tree_dict)

        # sort by priority, if possible
        i = self.get_column_index('priority', info)
        if i >= 0:
            self.table.sort_on_column(i)

    def get_column_index(self, name, info):
        i = 0
        for column in info.columns:
            colname = column[0]
            if colname.lower() == name.lower():
                return i
            i += 1
        return -1

    def _update_selections(self):

        self.table.clear_selection()

        # Mark any selected stars
        for star in self.selected:
            path = self._get_star_path(star)
            self.table.select_path(path)

    def _get_star_path(self, star):
        path = [star['index']]
        return path

    def get_subset_from_starlist(self, fromidx, toidx):
        starlist = self.starlist
        res = []
        for idx in range(fromidx, toidx):
            star = starlist[idx]
            res.append(star)
        return res

    def _select_tv(self, star, fromtable=False):
        if not fromtable:
            self._update_selections()

            star_path = self._get_star_path(star)
            self.table.scroll_to_path(star_path)

    def _unselect_tv(self, star, fromtable=False):
        if not fromtable:
            self._update_selections()

    def select_star_cb(self, widget, res_dict):
        """This method is called when the user selects a star from the table.
        """
        keys = list(res_dict.keys())
        if len(keys) == 0:
            self.selected = []
            self.replot_stars()
        else:
            idx = int(keys[0])
            star = self.starlist[idx]
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

    def do_operation_cb(self, btn_w, combo_w):
        index = combo_w.get_index()
        if index >= 0:
            fn = self.operation_table[index][1]
            fn(self.selected)

    def sort_cb(self):
        self.replot_stars()


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Catalogs', package='ginga')

# END
