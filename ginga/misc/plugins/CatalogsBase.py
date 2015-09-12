#
# CatalogsBase.py -- Catalogs plugin for Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import math
import numpy

from ginga.misc import Bunch
from ginga import GingaPlugin
from ginga import cmap, imap
from ginga.util import wcs
from ginga.util.six.moves import map, zip


class CatalogsBase(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        super(CatalogsBase, self).__init__(fv, fitsimage)

        self.limit_stars_to_area = False
        self.pan_to_selected = False
        self.use_dss_channel = False
        self.dsscnt = 0
        self.plot_max = 500
        self.plot_limit = 100
        self.plot_start = 0
        self.drawtype = 'circle'

        # star list
        self.starlist = []
        # catalog listing
        self.table = None

        self.color_outline = 'aquamarine'
        self.layertag = 'catalog-canvas'
        self.areatag = None

        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Catalogs')
        self.settings.load(onError='silent')

        self.image_server_options = []
        self.image_server_params = None

        self.catalog_server_options = []
        self.catalog_server_params = None

        self.dc = fv.getDrawClasses()
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype(self.drawtype, color='cyan', linestyle='dash',
                            #drawdims=True
                            )
        canvas.set_callback('cursor-down', self.btndown)
        canvas.set_callback('cursor-up', self.btnup)
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.color_selected = 'skyblue'
        self.hilite = None

    def ok(self):
        return self.close()

    def cancel(self):
        return self.close()

    def update_gui(self):
        self.fv.update_pending()

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def start(self, future=None):
        self.instructions()
        # start catalog operation
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        # Raise the params tab
        self._raise_tab(self.w.params)

        self.setfromimage()
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_setActive(True)
        #self.fv.showStatus("Draw a rectangle with the right mouse button")

    def stop(self):
        # stop catalog operation
        self.clearAll()
        # remove the canvas from the image
        self.canvas.ui_setActive(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.deleteObjectByTag(self.layertag)
        except:
            pass
        try:
            self.table.close()
        except:
            pass
        self.fv.showStatus("")

    def redo(self):
        obj = self.canvas.getObjectByTag(self.areatag)
        if not obj.kind in ('rectangle', 'circle'):
            return True

        try:
            image = self.fitsimage.get_image()

            if obj.kind == 'rectangle':
                # if  the object drawn is a rectangle, calculate the radius
                # of a circle necessary to cover the area
                # calculate center of bbox
                x1, y1, x2, y2 = obj.get_llur()
                wd = x2 - x1
                dw = wd // 2
                ht = y2 - y1
                dh = ht // 2
                ctr_x, ctr_y = x1 + dw, y1 + dh
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
                ctr_x, ctr_y = obj.crdmap.to_data(obj.x, obj.y)
                ra_ctr, dec_ctr = image.pixtoradec(ctr_x, ctr_y)
                dst_x, dst_y = obj.crdmap.to_data(obj.x + obj.radius, obj.y)
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
            wd = deg*60.0 + float(mn) + sec/60.0
            sgn, deg, mn, sec = wcs.degToDms(ht_deg)
            ht = deg*60.0 + float(mn) + sec/60.0
            sgn, deg, mn, sec = wcs.degToDms(radius_deg)
            radius = deg*60.0 + float(mn) + sec/60.0
            #wd, ht, radius = wd_deg, ht_deg, radius_deg

        except Exception as e:
            errmsg = 'Error calculating bounding box: %s' % str(e)
            self.logger.error(errmsg)
            self.fv.show_error(errmsg)
            return True

        # Copy the image parameters out to the widget
        d = { 'ra': ra_ctr, 'dec': dec_ctr, 'width': str(wd),
              'height': ht, 'r': radius, 'r2': radius,
              'r1': 0.0,
              }
        self._update_widgets(d)
        return True

    def btndown(self, canvas, event, data_x, data_y):
        return True

    def btnup(self, canvas, event, data_x, data_y):

        objs = self.canvas.getItemsAt(data_x, data_y)
        for obj in objs:
            if (obj.tag is not None) and obj.tag.startswith('star'):
                info = obj.get_data()
                self.table.show_selection(info.star)
                return True
        return True

    def highlight_object(self, obj, tag, color, redraw=True):
        x = obj.objects[0].x
        y = obj.objects[0].y
        delta = 10
        radius = obj.objects[0].radius + delta

        hilite = self.dc.Circle(x, y, radius, linewidth=4, color=color)
        self.hilite.addObject(hilite)
        if redraw:
            self.canvas.update_canvas()

    def update_selected(self, redraw=True):
        if self.hilite is None:
            self.hilite = self.dc.CompoundObject()
        if not self.canvas.has_object(self.hilite):
            self.canvas.add(self.hilite, tag='selected', redraw=False)

        self.hilite.deleteAllObjects()

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
        Rectangle = self.canvas.getDrawClass('Rectangle')
        tag = self.canvas.add(Rectangle(x1, y1, x2, y2,
                                        color=self.color_outline))

        self.draw_cb(self.canvas, tag)


    def draw_cb(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if not obj.kind in ('rectangle', 'circle'):
            return True

        if self.areatag:
            try:
                canvas.deleteObjectByTag(self.areatag)
            except:
                pass

        obj.color = self.color_outline
        obj.linestyle = 'solid'
        canvas.update_canvas()

        self.areatag = tag
        # Raise the params tab
        self._raise_tab(self.w.params)
        return self.redo()

    def getimage_cb(self):
        params = self.get_params(self.image_server_params)

        index = self._get_cbidx(self.w.server)
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

    def get_sky_image(self, servername, params):

        srvbank = self.fv.get_ServerBank()
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
                obj = self.canvas.getObjectByTag(self.areatag)

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
            errmsg ="Failed to load catalog: %s" % (str(e))
            raise Exception(errmsg)

    def getcatalog(self, server, params, obj):
        try:
            srvbank = self.fv.get_ServerBank()
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

    def filter_results(self, starlist, filter_obj):
        image = self.fitsimage.get_image()

        # Filter starts by a containing object, if provided
        if filter_obj:
            num_cat = len(starlist)
            self.logger.debug("number of incoming stars=%d" % (num_cat))
            # TODO: vectorize wcs lookup
            coords = [ image.radectopix(star['ra_deg'], star['dec_deg'])
                       for star in starlist ]
            arr = numpy.array(coords)
            self.logger.debug("arr.shape = %s" % str(arr.shape))

            # vectorized test for inclusion in shape
            res = filter_obj.contains_arr(arr.T[0], arr.T[1])
            self.logger.debug("res.shape = %s" % str(res.shape))

            stars = [ starlist[i] for i in range(num_cat) if res[i] ]
            self.logger.debug("number of filtered stars=%d" % (len(stars)))
            starlist = stars

        return starlist

    def clear(self):
        objects = self.canvas.getObjectsByTagpfx('star')
        self.canvas.deleteObjects(objects)
        self.canvas.deleteObjectsByTag(['selected'])

    def clearAll(self):
        self.canvas.deleteAllObjects()

    def reset(self):
        self.clear()
        #self.clearAll()
        self.table.clear()

    def plot_star(self, obj, image=None):

        if not image:
            image = self.fitsimage.get_image()
        x, y = image.radectopix(obj['ra_deg'], obj['dec_deg'])
        # TODO: auto-pick a decent radius
        radius = 10
        color = self.table.get_color(obj)

        circle = self.dc.Circle(x, y, radius, color=color)
        point = self.dc.Point(x, y, radius, color=color)

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
        subset = self.table.get_subset_from_starlist(i, i+length)

        with self.fitsimage.suppress_redraw:
            for obj in subset:
                self.plot_star(obj, image=image)

            self.update_selected(redraw=False)

            canvas.update_canvas()


class CatalogListingBase(object):

    def __init__(self, logger, container):
        super(CatalogListingBase, self).__init__()

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

        self.operation_table = []
        self._select_flag = False

        self._build_gui(container)


    def get_color(self, obj):
        try:
            mag = obj[self.mag_field]
        except:
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
                self.logger.warn("Error unhilighting star: %s" % (str(e)))

            self.catalog.update_selected()
            return False
        else:
            if self.selection_mode == 'single':
                # if selection mode is 'single' unselect any existing selections
                for star2 in self.selected:
                    self.selected.remove(star2)
                    try:
                        self._unselect_tv(star2, fromtable=fromtable)
                    except Exception as e:
                        self.logger.warn("Error unhilighting star: %s" % (str(e)))
            self.selected.append(star)
            try:
                # highlight line in table
                self._select_tv(star, fromtable=fromtable)
                if self.catalog.pan_to_selected:
                    self.catalog.pan_to_star(star)
            except Exception as e:
                self.logger.warn("Error hilighting star: %s" % (str(e)))

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
        subset = self.get_subset_from_starlist(i, i+length)
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

# END
