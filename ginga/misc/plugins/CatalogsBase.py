#
# CatalogsBase.py -- Catalogs plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch, Future
from ginga import GingaPlugin
from ginga import cmap, imap
from ginga import wcs


class CatalogsBase(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        super(CatalogsBase, self).__init__(fv, fitsimage)

        self.mycolor = 'skyblue'
        self.color_cursor = 'red'

        self.limit_stars_to_area = False
        self.pan_to_selected = False
        self.use_dss_channel = False
        self.plot_max = 500
        self.plot_limit = 100
        self.plot_start = 0

        # star list
        self.starlist = []
        # catalog listing
        self.table = None
        
        self.layertag = 'catalog-canvas'
        self.areatag = None
        self.curstar = None

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
        canvas.set_drawtype('rectangle', color='cyan', linestyle='dash',
                            drawdims=True)
        canvas.set_callback('cursor-down', self.btndown)
        canvas.set_callback('cursor-up', self.btnup)
        canvas.set_callback('draw-event', self.getarea)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas


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

    def start(self, future=None):
        self.instructions()
        # start catalog operation
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)
            
        # Raise the params tab
        self._raise_tab(self.w.params)

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
            #wd, ht, radius = wd_deg, ht_deg, radius_deg
            
        except Exception, e:
            self.fv.showStatus('BAD WCS: %s' % str(e))
            return True

        # Copy the image parameters out to the widget
        d = { 'ra': ra_ctr, 'dec': dec_ctr, 'width': str(wd),
              'height': ht, 'r': radius, 'r2': radius,
              'r1': 0.0,
              }
        self._update_widgets(d)
        return True
    
    def btndown(self, canvas, button, data_x, data_y):
        return True

    def btnup(self, canvas, button, data_x, data_y):
        
        objs = self.canvas.getItemsAt(data_x, data_y)
        for obj in objs:
            if (obj.tag != None) and obj.tag.startswith('star'):
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
        Rectangle = self.canvas.getDrawClass('Rectangle')
        tag = self.canvas.add(Rectangle(x1, y1, x2, y2,
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

    def getimage(self, server, params, chname):
        try:
            fitspath = self.fv.get_sky_image(server, params)

        except Exception as e:
            errmsg = "Query exception: %s" % (str(e))
            self.logger.error(errmsg)
            # pop up the error in the GUI under "Errors" tab
            self.fv.gui_do(self.fv.show_error, errmsg)
            return
            
        self.fv.load_file(fitspath, chname=chname)

        # Update the GUI
        def getimage_update(self):
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

    def getcatalog(self, server, params, obj):
        try:
            starlist, info = self.fv.get_catalog(server, params)
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
        self.clear()
        #self.clearAll()
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

        circle = self.dc.Circle(x, y, radius, color=color)
        point = self.dc.Point(x, y, radius, color=color)

        ## What is this from?
        if obj.has_key('pick'):
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
        for j in xrange(len(self.starlist)):
            obj = self.starlist[j]
            obj.canvobj = None

        # plot stars in range
        subset = self.table.get_subset_from_starlist(i, i+length)
        for obj in subset:
            self.plot_star(obj, image=image)

        # plot stars in selected list even if they are not in the range
        #for obj in selected:
        selected = self.table.get_selected()
        for obj in selected:
            if (not obj.has_key('canvobj')) or (obj.canvobj == None):
                self.plot_star(obj, image=image)
            self.highlight_object(obj.canvobj, 'selected', 'skyblue')
            
        canvas.redraw(whence=3)

        
class CatalogListingBase(object):
    
    def __init__(self, logger, container):
        super(CatalogListingBase, self).__init__()
        
        self.logger = logger
        self.tag = None
        self.mycolor = 'skyblue'
        self.cmap_names = cmap.get_names()
        self.imap_names = imap.get_names()
        self.magcmap = 'stairs8'
        self.magimap = 'ramp'

        self.mag_field = 'mag'
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
                        ('Description', 'description'),
                        ]

        self.catalog = None
        self.cursor = 0
        self.color_cursor = 'red'
        self.color_selected = 'skyblue'
        self.selection_mode = 'single'
        self.selected = []
        self.moving_cursor = False

        self.btn = Bunch.Bunch()

        self.cmap = cmap.get_cmap(self.magcmap)
        self.imap = imap.get_imap('ramp')

        self._build_gui(container)


    def get_color(self, obj):
        try:
            mag = obj[self.mag_field]
        except:
            return self.mycolor

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
                # unhighlight star in plot
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
                        self._unselect_tv(star2, fromtable=fromtable)
                        self.catalog.unhighlight_object(star2.canvobj, 'selected')
                    except Exception, e:
                        self.logger.warn("Error unhilighting star: %s" % (str(e)))
            self.selected.append(star)
            try:
                # If this star is not plotted, then plot it
                if (not star.has_key('canvobj')) or (star.canvobj == None):
                    self.catalog.plot_star(star)

                # highlight line in table
                self._select_tv(star, fromtable=fromtable)
                # highlight the plot object
                self.catalog.highlight_object(star.canvobj, 'selected', 'skyblue')
                if self.catalog.pan_to_selected:
                    self.catalog.pan_to_star(star)
            except Exception, e:
                self.logger.warn("Error hilighting star: %s" % (str(e)))
            return True


    def show_selection(self, star):
        """This method is called when the user clicks on a plotted star in the
        fitsviewer.
        """
        self.mark_selection(star)

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
        values = map(lambda star: float(star[self.mag_field]),
                     subset)
        self.mag_max = max(values)
        self.mag_min = min(values)
        self.cbar.set_range(self.mag_min, self.mag_max)

    def _set_field(self, name):
        # select new field to use for color plotting
        self.mag_field = name

        # determine the range of the values
        if self.catalog != None:
            i, length = self.catalog.get_plot_range()
            self.set_minmax(i, length)
        
    def set_field(self, name):
        self._set_field(name)
        self.replot_stars()
        
# END
