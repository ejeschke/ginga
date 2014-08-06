#
# Pick.py -- Pick plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading
import numpy

from ginga.misc import Widgets, CanvasTypes, Bunch
from ginga.util import iqcalc, dp, wcs
from ginga import GingaPlugin
from ginga.util.six.moves import map, zip, filter

try:
    from ginga.misc import Plot
    have_mpl = True
except ImportError:
    have_mpl = False

region_default_width = 30
region_default_height = 30


class Pick(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Pick, self).__init__(fv, fitsimage)

        self.layertag = 'pick-canvas'
        self.pickimage = None
        self.pickcenter = None
        self.pick_qs = None
        self.picktag = None
        self.pickcolor = 'green'
        self.candidate_color = 'purple'

        self.pick_x1 = 0
        self.pick_y1 = 0
        self.pick_data = None
        self.dx = region_default_width
        self.dy = region_default_height
        # For offloading intensive calculation from graphics thread
        self.serialnum = 0
        self.lock = threading.RLock()
        self.lock2 = threading.RLock()
        self.ev_intr = threading.Event()

        # Peak finding parameters and selection criteria
        # this is the maximum size a side can be
        self.max_side = 1024
        self.radius = 10
        self.threshold = None
        self.min_fwhm = 2.0
        self.max_fwhm = 50.0
        self.min_ellipse = 0.5
        self.edgew = 0.01
        self.show_candidates = False
        self.do_record = False
        self.last_report = None

        self.plot_panx = 0.5
        self.plot_pany = 0.5
        self.plot_zoomlevel = 1.0
        self.num_contours = 8
        self.contour_size_limit = 70
        self.contour_data = None
        self.delta_sky = 0.0
        self.delta_bright = 0.0
        self.iqcalc = iqcalc.IQCalc(self.logger)

        self.dc = self.fv.getDrawClasses()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_callback('cursor-down', self.btndown)
        canvas.set_callback('cursor-move', self.drag)
        canvas.set_callback('cursor-up', self.update)
        canvas.set_drawtype('rectangle', color='cyan', linestyle='dash',
                            drawdims=True)
        canvas.set_callback('draw-event', self.setpickregion)
        canvas.setSurface(self.fitsimage)
        self.canvas = canvas

        self.have_mpl = have_mpl

    def build_gui(self, container):
        assert iqcalc.have_scipy == True, \
               Exception("Please install python-scipy to use this plugin")
        
        self.pickcenter = None

        vtop = Widgets.VBox()
        vtop.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        vpaned = Widgets.Splitter(orientation=orientation)

        nb = Widgets.TabWidget(tabpos='bottom')
        #nb.set_scrollable(True)
        self.w.nb1 = nb
        vpaned.add_widget(nb)
        
        cm, im = self.fv.cm, self.fv.im

        di = CanvasTypes.ImageViewCanvas(logger=self.logger)
        width, height = 200, 200
        di.set_desired_size(width, height)
        di.enable_autozoom('off')
        di.enable_autocuts('off')
        di.zoom_to(3, redraw=False)
        settings = di.get_settings()
        settings.getSetting('zoomlevel').add_callback('set',
                               self.zoomset, di)
        di.set_cmap(cm, redraw=False)
        di.set_imap(im, redraw=False)
        di.set_callback('none-move', self.detailxy)
        di.set_bg(0.4, 0.4, 0.4)
        # for debugging
        di.set_name('pickimage')
        self.pickimage = di

        bd = di.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)

        iw = Widgets.wrap(di.get_widget())
        nb.add_widget(iw, title="Image")

        if have_mpl:
            self.plot1 = Plot.Plot(logger=self.logger,
                                   width=2, height=3, dpi=72)
            self.w.canvas = self.plot1.canvas
            self.w.fig = self.plot1.fig
            self.w.ax = self.w.fig.add_subplot(111, axisbg='black')
            self.w.ax.set_aspect('equal', adjustable='box')
            self.w.ax.set_title('Contours')
            #self.w.ax.grid(True)

            canvas = self.w.canvas
            connect = canvas.mpl_connect
            # These are not ready for prime time...
            # connect("motion_notify_event", self.plot_motion_notify)
            # connect("button_press_event", self.plot_button_press)
            connect("scroll_event", self.plot_scroll)
            nb.add_widget(Widgets.wrap(canvas), title="Contour")

            self.plot2 = Plot.Plot(logger=self.logger,
                                   width=2, height=3, dpi=72)
            self.w.canvas2 = self.plot2.canvas
            self.w.fig2 = self.plot2.fig
            self.w.ax2 = self.w.fig2.add_subplot(111, axisbg='white')
            #self.w.ax2.set_aspect('equal', adjustable='box')
            self.w.ax2.set_ylabel('brightness')
            self.w.ax2.set_xlabel('pixels')
            self.w.ax2.set_title('FWHM')
            self.w.ax.grid(True)
            canvas = self.w.canvas2
            nb.add_widget(Widgets.wrap(canvas), title="FWHM")

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Frame("Instructions")
        vbox2 = Widgets.VBox()
        vbox2.add_widget(tw)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=0)
        
        vpaned.add_widget(Widgets.Label(''))
        vbox.add_widget(vpaned, stretch=1)
        
        fr = Widgets.Frame("Pick")

        nb = Widgets.TabWidget(tabpos='bottom')
        self.w.nb2 = nb

        # Build report panel
        captions = (('Zoom:', 'label', 'Zoom', 'llabel',
                     'Contour Zoom:', 'label', 'Contour Zoom', 'llabel'),
                    ('Object_X', 'label', 'Object_X', 'llabel',
                     'Object_Y', 'label', 'Object_Y', 'llabel'),
                    ('RA:', 'label', 'RA', 'llabel',
                     'DEC:', 'label', 'DEC', 'llabel'),
                    ('Equinox:', 'label', 'Equinox', 'llabel',
                     'Background:', 'label', 'Background', 'llabel'),
                    ('Sky Level:', 'label', 'Sky Level', 'llabel',
                     'Brightness:', 'label', 'Brightness', 'llabel'), 
                    ('FWHM X:', 'label', 'FWHM X', 'llabel',
                     'FWHM Y:', 'label', 'FWHM Y', 'llabel'),
                    ('FWHM:', 'label', 'FWHM', 'llabel',
                     'Star Size:', 'label', 'Star Size', 'llabel'),
                    ('Sample Area:', 'label', 'Sample Area', 'llabel',
                     'Default Region', 'button'),
                    )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.zoom.set_text(self.fv.scale2text(di.get_scale()))
        self.wdetail = b
        b.default_region.add_callback('activated',
                                      lambda w: self.reset_region())
        b.default_region.set_tooltip("Reset region size to default")

        vbox1 = Widgets.VBox()
        vbox1.add_widget(w, stretch=0)

        # spacer
        vbox1.add_widget(Widgets.Label(''), stretch=0)
        
        # Pick field evaluation status
        hbox = Widgets.HBox()
        hbox.set_spacing(4)
        hbox.set_border_width(4)
        label = Widgets.Label()
        #label.set_alignment(0.05, 0.5)
        self.w.eval_status = label
        hbox.add_widget(self.w.eval_status, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)                
        vbox1.add_widget(hbox, stretch=0)

        # Pick field evaluation progress bar and stop button
        hbox = Widgets.HBox()
        hbox.set_spacing(4)
        hbox.set_border_width(4)
        btn = Widgets.Button("Stop")
        btn.add_callback('activated', lambda w: self.eval_intr())
        btn.set_enabled(False)
        self.w.btn_intr_eval = btn
        hbox.add_widget(btn, stretch=0)

        self.w.eval_pgs = Widgets.ProgressBar()
        hbox.add_widget(self.w.eval_pgs, stretch=1)
        vbox1.add_widget(hbox, stretch=0)
        
        nb.add_widget(vbox1, title="Readout")

        # Build settings panel
        captions = (('Show Candidates', 'checkbutton'),
                    ('Radius:', 'label', 'xlbl_radius', 'label',
                     'Radius', 'spinbutton'),
                    ('Threshold:', 'label', 'xlbl_threshold', 'label',
                     'Threshold', 'entry'),
                    ('Min FWHM:', 'label', 'xlbl_min_fwhm', 'label',
                     'Min FWHM', 'spinbutton'),
                    ('Max FWHM:', 'label', 'xlbl_max_fwhm', 'label',
                     'Max FWHM', 'spinbutton'),
                    ('Ellipticity:', 'label', 'xlbl_ellipticity', 'label',
                     'Ellipticity', 'entry'),
                    ('Edge:', 'label', 'xlbl_edge', 'label',
                     'Edge', 'entry'),
                    ('Max side:', 'label', 'xlbl_max_side', 'label',
                     'Max side', 'spinbutton'),
                    ('Redo Pick', 'button'),
                    )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.radius.set_tooltip("Radius for peak detection")
        b.threshold.set_tooltip("Threshold for peak detection (blank=default)")
        b.min_fwhm.set_tooltip("Minimum FWHM for selection")
        b.max_fwhm.set_tooltip("Maximum FWHM for selection")
        b.ellipticity.set_tooltip("Minimum ellipticity for selection")
        b.edge.set_tooltip("Minimum edge distance for selection")
        b.show_candidates.set_tooltip("Show all peak candidates")
        # radius control
        #b.radius.set_digits(2)
        #b.radius.set_numeric(True)
        b.radius.set_limits(5.0, 200.0, incr_value=1.0)
        b.radius.set_value(self.radius)
        def chg_radius(w, val):
            self.radius = float(val)
            self.w.xlbl_radius.set_text(str(self.radius))
            return True
        b.xlbl_radius.set_text(str(self.radius))
        b.radius.add_callback('value-changed', chg_radius)

        # threshold control
        def chg_threshold(w):
            threshold = None
            ths = w.get_text().strip()
            if len(ths) > 0:
                threshold = float(ths)
            self.threshold = threshold
            self.w.xlbl_threshold.set_text(str(self.threshold))
            return True
        b.xlbl_threshold.set_text(str(self.threshold))
        b.threshold.add_callback('activated', chg_threshold)

        # min fwhm
        #b.min_fwhm.set_digits(2)
        #b.min_fwhm.set_numeric(True)
        b.min_fwhm.set_limits(0.1, 200.0, incr_value=0.1)
        b.min_fwhm.set_value(self.min_fwhm)
        def chg_min(w, val):
            self.min_fwhm = float(val)
            self.w.xlbl_min_fwhm.set_text(str(self.min_fwhm))
            return True
        b.xlbl_min_fwhm.set_text(str(self.min_fwhm))
        b.min_fwhm.add_callback('value-changed', chg_min)

        # max fwhm
        #b.max_fwhm.set_digits(2)
        #b.max_fwhm.set_numeric(True)
        b.max_fwhm.set_limits(0.1, 200.0, incr_value=0.1)
        b.max_fwhm.set_value(self.max_fwhm)
        def chg_max(w, val):
            self.max_fwhm = float(val)
            self.w.xlbl_max_fwhm.set_text(str(self.max_fwhm))
            return True
        b.xlbl_max_fwhm.set_text(str(self.max_fwhm))
        b.max_fwhm.add_callback('value-changed', chg_max)

        # Ellipticity control
        def chg_ellipticity(w):
            minellipse = None
            val = w.get_text().strip()
            if len(val) > 0:
                minellipse = float(val)
            self.min_ellipse = minellipse
            self.w.xlbl_ellipticity.set_text(str(self.min_ellipse))
            return True
        b.xlbl_ellipticity.set_text(str(self.min_ellipse))
        b.ellipticity.add_callback('activated', chg_ellipticity)

        # Edge control
        def chg_edgew(w):
            edgew = None
            val = w.get_text().strip()
            if len(val) > 0:
                edgew = float(val)
            self.edgew = edgew
            self.w.xlbl_edge.set_text(str(self.edgew))
            return True
        b.xlbl_edge.set_text(str(self.edgew))
        b.edge.add_callback('activated', chg_edgew)

        #b.max_side.set_digits(0)
        #b.max_side.set_numeric(True)
        b.max_side.set_limits(5, 10000, incr_value=10)
        b.max_side.set_value(self.max_side)
        def chg_max_side(w, val):
            self.max_side = int(val)
            self.w.xlbl_max_side.set_text(str(self.max_side))
            return True
        b.xlbl_max_side.set_text(str(self.max_side))
        b.max_side.add_callback('value-changed', chg_max_side)

        b.redo_pick.add_callback('activated', lambda w: self.redo())
        b.show_candidates.set_state(self.show_candidates)
        b.show_candidates.add_callback('activated', self.show_candidates_cb)

        nb.add_widget(w, title="Settings")

        # Build controls panel
        captions = (
            ('Sky cut', 'button', 'Delta sky:', 'label',
             'xlbl_delta_sky', 'label', 'Delta sky', 'entry'),
            ('Bright cut', 'button', 'Delta bright:', 'label',
             'xlbl_delta_bright', 'label', 'Delta bright', 'entry'),
            )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.sky_cut.set_tooltip("Set image low cut to Sky Level")
        b.delta_sky.set_tooltip("Delta to apply to low cut")
        b.bright_cut.set_tooltip("Set image high cut to Sky Level+Brightness")
        b.delta_bright.set_tooltip("Delta to apply to high cut")

        b.sky_cut.set_enabled(False)
        self.w.btn_sky_cut = b.sky_cut
        self.w.btn_sky_cut.add_callback('activated', lambda w: self.sky_cut())
        self.w.sky_cut_delta = b.delta_sky
        b.xlbl_delta_sky.set_text(str(self.delta_sky))
        b.delta_sky.set_text(str(self.delta_sky))
        def chg_delta_sky(w):
            delta_sky = 0.0
            val = w.get_text().strip()
            if len(val) > 0:
                delta_sky = float(val)
            self.delta_sky = delta_sky
            self.w.xlbl_delta_sky.set_text(str(self.delta_sky))
            return True
        b.delta_sky.add_callback('activated', chg_delta_sky)
        
        b.bright_cut.set_enabled(False)
        self.w.btn_bright_cut = b.bright_cut
        self.w.btn_bright_cut.add_callback('activated',
                                           lambda w: self.bright_cut())
        self.w.bright_cut_delta = b.delta_bright
        b.xlbl_delta_bright.set_text(str(self.delta_bright))
        b.delta_bright.set_text(str(self.delta_bright))
        def chg_delta_bright(w):
            delta_bright = 0.0
            val = w.get_text().strip()
            if len(val) > 0:
                delta_bright = float(val)
            self.delta_bright = delta_bright
            self.w.xlbl_delta_bright.set_text(str(self.delta_bright))
            return True
        b.delta_bright.add_callback('activated', chg_delta_bright)

        nb.add_widget(w, title="Controls")

        vbox3 = Widgets.VBox()
        msgFont = self.fv.getFont("fixedFont", 10)
        tw = Widgets.TextArea(wrap=False, editable=True)
        tw.set_font(msgFont)
        self.w.report = tw
        sw1 = Widgets.ScrollArea()
        sw1.set_widget(tw)
        vbox3.add_widget(sw1, stretch=1)
        tw.append_text(self._mkreport_header())
        
        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Add Pick")
        btn.add_callback('activated', lambda w: self.add_pick_cb())
        btns.add_widget(btn)
        btn = Widgets.CheckBox("Record Picks")
        btn.set_state(self.do_record)
        btn.add_callback('activated', self.record_cb)
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox3.add_widget(btns, stretch=0)

        nb.add_widget(vbox3, title="Report")

        ## vbox4 = Widgets.VBox()
        ## tw = Widgets.TextArea(wrap=False, editable=True)
        ## tw.set_font(msgFont)
        ## self.w.correct = tw
        ## sw1 = Widgets.ScrollArea()
        ## sw1.set_widget(tw)
        ## vbox4.add_widget(sw1, stretch=1)
        ## tw.append_text("# paste a reference report here")
        
        ## btns = Widgets.HBox()
        ## btns.set_spacing(4)

        ## btn = Widgets.Button("Correct WCS")
        ## btn.add_callback('activated', lambda w: self.correct_wcs())
        ## btns.add_widget(btn)
        ## vbox4.add_widget(btns, stretch=0)

        ## nb.add_widget(vbox4, title="Correct")

        fr.set_widget(nb)
        vbox.add_widget(fr, stretch=0)

        ## spacer = Widgets.Label('')
        ## vbox.add_widget(spacer, stretch=1)
        
        vtop.add_widget(sw, stretch=1)
        
        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vtop.add_widget(btns, stretch=0)

        container.add_widget(vtop, stretch=1)

    def copyText(self, w):
        text = w.get_text()
        # TODO: put it in the clipboard
        
    def record_cb(self, w, tf):
        self.do_record = tf
        return True
        
    def instructions(self):
        self.tw.set_text("""Left-click to place region.  Left-drag to position region.  Redraw region with the right mouse button.""")
        self.tw.set_font(self.msgFont)
            
    def update_status(self, text):
        self.fv.gui_do(self.w.eval_status.set_text, text)

    def init_progress(self):
        self.w.btn_intr_eval.set_enabled(True)
        self.w.eval_pgs.set_value(0.0)
            
    def update_progress(self, pct):
        self.w.eval_pgs.set_value(pct)
        
    def show_candidates_cb(self, w, state):
        self.show_candidates = state
        if not self.show_candidates:
            # Delete previous peak marks
            objs = self.fitsimage.getObjectsByTagpfx('peak')
            self.fitsimage.deleteObjects(objs, redraw=True)
        
    def adjust_wcs(self, image, wcs_m, tup):
        d_ra, d_dec, d_theta = tup
        msg = "Calculated shift: dra, ddec = %f, %f\n" % (
            d_ra/3600.0, d_dec/3600.0)
        msg += "Calculated rotation: %f deg\n" % (d_theta)
        msg += "\nAdjust WCS?"
        
        dialog = GtkHelp.Dialog("Adjust WCS",
                                gtk.DIALOG_DESTROY_WITH_PARENT,
                                [['Cancel', 0], ['Ok', 1]],
                                lambda w, rsp: self.adjust_wcs_cb(w, rsp,
                                                                  image, wcs_m))
        box = dialog.get_content_area()
        w = gtk.Label(msg)
        box.pack_start(w, expand=True, fill=True)
        dialog.show_all()
        
    def adjust_wcs_cb(self, w, rsp, image, wcs_m):
        w.destroy()
        if rsp == 0:
            return

        #image.wcs = wcs_m.wcs
        image.update_keywords(wcs_m.hdr)
        return True
        
    def plot_scroll(self, event):
        # Matplotlib only gives us the number of steps of the scroll,
        # positive for up and negative for down.
        direction = None
        if event.step > 0:
            #delta = 0.9
            self.plot_zoomlevel += 1.0
        elif event.step < 0:
            #delta = 1.1
            self.plot_zoomlevel -= 1.0

        self.plot_panzoom()
        
        # x1, x2 = self.w.ax.get_xlim()
        # y1, y2 = self.w.ax.get_ylim()
        # self.w.ax.set_xlim(x1*delta, x2*delta)
        # self.w.ax.set_ylim(y1*delta, y2*delta)
        # self.w.canvas.draw()
        
    def plot_button_press(self, event):
        if event.button == 1:
            self.plot_x, self.plot_y = event.x, event.y
        return True

    def plot_motion_notify(self, event):
        if event.button == 1:
            xdelta = event.x - self.plot_x
            #ydelta = event.y - self.plot_y
            ydelta = self.plot_y - event.y
            self.pan_plot(xdelta, ydelta)

    def bump_serial(self):
        with self.lock:
            self.serialnum += 1
            return self.serialnum
        
    def get_serial(self):
        with self.lock:
            return self.serialnum
        
    def plot_panzoom(self):
        ht, wd = self.contour_data.shape
        x = int(self.plot_panx * wd)
        y = int(self.plot_pany * ht)

        if self.plot_zoomlevel >= 1.0:
            scalefactor = 1.0 / self.plot_zoomlevel
        elif self.plot_zoomlevel < -1.0:
            scalefactor = - self.plot_zoomlevel
        else:
            # wierd condition?--reset to 1:1
            scalefactor = 1.0
            self.plot_zoomlevel = 1.0

        # Show contour zoom level
        text = self.fv.scale2text(1.0/scalefactor)
        self.wdetail.contour_zoom.set_text(text)

        xdelta = int(scalefactor * (wd/2.0))
        ydelta = int(scalefactor * (ht/2.0))
        xlo, xhi = x-xdelta, x+xdelta
        # distribute remaining x space from plot
        if xlo < 0:
            xsh = abs(xlo)
            xlo, xhi = 0, min(wd-1, xhi+xsh)
        elif xhi >= wd:
            xsh = xhi - wd
            xlo, xhi = max(0, xlo-xsh), wd-1
        self.w.ax.set_xlim(xlo, xhi)

        ylo, yhi = y-ydelta, y+ydelta
        # distribute remaining y space from plot
        if ylo < 0:
            ysh = abs(ylo)
            ylo, yhi = 0, min(ht-1, yhi+ysh)
        elif yhi >= ht:
            ysh = yhi - ht
            ylo, yhi = max(0, ylo-ysh), ht-1
        self.w.ax.set_ylim(ylo, yhi)

        self.w.fig.canvas.draw()

    def plot_contours(self):
        # Make a contour plot

        ht, wd = self.pick_data.shape

        # If size of pick region is too large, carve out a subset around
        # the picked object coordinates for plotting contours
        maxsize = max(ht, wd)
        if maxsize > self.contour_size_limit:
            image = self.fitsimage.get_image()
            radius = int(self.contour_size_limit // 2)
            x, y = self.pick_qs.x, self.pick_qs.y
            data, x1, y1, x2, y2 = image.cutout_radius(x, y, radius)
            x, y = x - x1, y - y1
            ht, wd = data.shape
        else:
            data = self.pick_data
            x, y = self.pickcenter.x, self.pickcenter.y
        self.contour_data = data
        # Set pan position in contour plot
        self.plot_panx = float(x) / wd
        self.plot_pany = float(y) / ht
        
        self.w.ax.cla()
        try:
            # Create a contour plot
            xarr = numpy.arange(wd)
            yarr = numpy.arange(ht)
            self.w.ax.contourf(xarr, yarr, data, self.num_contours)
            # Mark the center of the object
            self.w.ax.plot([x], [y], marker='x', ms=20.0,
                           color='black')

            # Set the pan and zoom position & redraw
            self.plot_panzoom()
            
        except Exception as e:
            self.logger.error("Error making contour plot: %s" % (
                str(e)))

    def clear_contours(self):
        self.w.ax.cla()
        
    def _plot_fwhm_axis(self, arr, skybg, color1, color2, color3):
        N = len(arr)
        X = numpy.array(list(range(N)))
        Y = arr
        # subtract sky background
        ## skybg = numpy.median(Y)
        Y = Y - skybg
        maxv = Y.max()
        # clamp to 0..max
        Y = Y.clip(0, maxv)
        self.logger.debug("Y=%s" % (str(Y)))
        self.w.ax2.plot(X, Y, color=color1, marker='.')

        fwhm, mu, sdev, maxv = self.iqcalc.calc_fwhm(arr)
        Z = numpy.array([self.iqcalc.gaussian(x, (mu, sdev, maxv)) for x in X])
        self.w.ax2.plot(X, Z, color=color1, linestyle=':')
        self.w.ax2.axvspan(mu-fwhm/2.0, mu+fwhm/2.0,
                           facecolor=color3, alpha=0.25)
        return (fwhm, mu, sdev, maxv)

    def plot_fwhm(self, qs):
        # Make a FWHM plot
        self.w.ax2.cla()
        x, y, radius = qs.x, qs.y, qs.fwhm_radius
        try:
            image = self.fitsimage.get_image()
            x0, y0, xarr, yarr = dp.cutout_cross(image, x, y, radius)

            # get median value from the cutout area
            skybg = numpy.median(self.pick_data)
            self.logger.debug("cutting x=%d y=%d r=%d med=%f" % (
                x, y, radius, skybg))
            
            self.logger.debug("xarr=%s" % (str(xarr)))
            fwhm_x, mu, sdev, maxv = self._plot_fwhm_axis(xarr, skybg,
                                                          'blue', 'blue', 'skyblue')

            self.logger.debug("yarr=%s" % (str(yarr)))
            fwhm_y, mu, sdev, maxv = self._plot_fwhm_axis(yarr, skybg,
                                                          'green', 'green', 'seagreen')
            plt = self.w.ax2
            plt.legend(('data x', 'gauss x', 'data y', 'gauss y'),
                       'upper right', shadow=False, fancybox=False,
                       prop={'size': 8}, labelspacing=0.2)
            plt.set_title("FWHM X: %.2f  Y: %.2f" % (fwhm_x, fwhm_y))

            self.w.fig2.canvas.draw()
        except Exception as e:
            self.logger.error("Error making fwhm plot: %s" % (
                str(e)))

    def clear_fwhm(self):
        self.w.ax2.cla()
        
    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True
        
    def start(self):
        self.instructions()
        # insert layer if it is not already
        try:
            obj = self.fitsimage.getObjectByTag(self.layertag)

        except KeyError:
            # Add canvas layer
            self.fitsimage.add(self.canvas, tag=self.layertag)
            
        self.resume()

    def pause(self):
        self.canvas.ui_setActive(False)
        
    def resume(self):
        self.canvas.ui_setActive(True)
        self.fv.showStatus("Draw a rectangle with the right mouse button")
        
    def stop(self):
        # Delete previous peak marks
        objs = self.fitsimage.getObjectsByTagpfx('peak')
        self.fitsimage.deleteObjects(objs, redraw=False)

        # deactivate the canvas 
        self.canvas.ui_setActive(False)
        try:
            self.fitsimage.deleteObjectByTag(self.layertag)
        except:
            pass
        self.fv.showStatus("")
        
    def redo(self):
        serialnum = self.bump_serial()
        self.ev_intr.set()
        
        fig = self.canvas.getObjectByTag(self.picktag)
        if fig.kind != 'compound':
            return True
        bbox  = fig.objects[0]
        point = fig.objects[1]
        text = fig.objects[2]
        data_x, data_y = point.x, point.y
        #self.fitsimage.panset_xy(data_x, data_y, redraw=False)

        # set the pick image to have the same cut levels and transforms
        self.fitsimage.copy_attributes(self.pickimage,
                                       ['transforms', 'cutlevels',
                                        'rgbmap'],
                                       redraw=False)
        
        try:
            image = self.fitsimage.get_image()

            # sanity check on region
            width = bbox.x2 - bbox.x1
            height = bbox.y2 - bbox.y1
            if (width > self.max_side) or (height > self.max_side):
                errmsg = "Image area (%dx%d) too large!" % (
                    width, height)
                self.fv.show_error(errmsg)
                raise Exception(errmsg)
        
            # Note: FITS coordinates are 1-based, whereas numpy FITS arrays
            # are 0-based
            fits_x, fits_y = data_x + 1, data_y + 1

            # Cut and show pick image in pick window
            #self.pick_x, self.pick_y = data_x, data_y
            self.logger.debug("bbox %f,%f %f,%f" % (bbox.x1, bbox.y1,
                                                    bbox.x2, bbox.y2))
            x1, y1, x2, y2, data = self.cutdetail(self.fitsimage,
                                                  self.pickimage,
                                                  int(bbox.x1), int(bbox.y1),
                                                  int(bbox.x2), int(bbox.y2))
            self.logger.debug("cut box %f,%f %f,%f" % (x1, y1, x2, y2))

            # calculate center of pick image
            wd, ht = self.pickimage.get_data_size()
            xc = wd // 2
            yc = ht // 2
            if not self.pickcenter:
                tag = self.pickimage.add(self.dc.Point(xc, yc, 5,
                                                       linewidth=1,
                                                       color='red'))
                self.pickcenter = self.pickimage.getObjectByTag(tag)
            
            self.pick_x1, self.pick_y1 = x1, y1
            self.pick_data = data
            self.wdetail.sample_area.set_text('%dx%d' % (x2-x1, y2-y1))

            point.color = 'red'
            text.text = 'Pick: calc'
            self.pickcenter.x = xc
            self.pickcenter.y = yc
            self.pickcenter.color = 'red'

            # clear contour and fwhm plots
            if self.have_mpl:
                self.clear_contours()
                self.clear_fwhm()

            # Delete previous peak marks
            objs = self.fitsimage.getObjectsByTagpfx('peak')
            self.fitsimage.deleteObjects(objs, redraw=True)

            # Offload this task to another thread so that GUI remains
            # responsive
            self.fv.nongui_do(self.search, serialnum, data,
                              x1, y1, wd, ht, fig)

        except Exception as e:
            self.logger.error("Error calculating quality metrics: %s" % (
                str(e)))
            return True

    def search(self, serialnum, data, x1, y1, wd, ht, fig):
        if serialnum != self.get_serial():
            return
        with self.lock2:
            self.pgs_cnt = 0
            self.ev_intr.clear()
            self.fv.gui_call(self.init_progress)
            
            msg, results, qs = None, None, None
            try:
                self.update_status("Finding bright peaks...")
                # Find bright peaks in the cutout
                peaks = self.iqcalc.find_bright_peaks(data,
                                                      threshold=self.threshold,
                                                      radius=self.radius)
                num_peaks = len(peaks)
                if num_peaks == 0:
                    raise Exception("Cannot find bright peaks")

                def cb_fn(obj):
                    self.pgs_cnt += 1
                    pct = float(self.pgs_cnt) / num_peaks
                    self.fv.gui_do(self.update_progress, pct)
                    
                # Evaluate those peaks
                self.update_status("Evaluating %d bright peaks..." % (
                    num_peaks))
                objlist = self.iqcalc.evaluate_peaks(peaks, data,
                                                     fwhm_radius=self.radius,
                                                     cb_fn=cb_fn,
                                                     ev_intr=self.ev_intr)

                num_candidates = len(objlist)
                if num_candidates == 0:
                    raise Exception("Error evaluating bright peaks: no candidates found")

                self.update_status("Selecting from %d candidates..." % (
                    num_candidates))
                height, width = data.shape
                results = self.iqcalc.objlist_select(objlist, width, height,
                                                     minfwhm=self.min_fwhm,
                                                     maxfwhm=self.max_fwhm,
                                                     minelipse=self.min_ellipse,
                                                     edgew=self.edgew)
                if len(results) == 0:
                    raise Exception("No object matches selection criteria")
                qs = results[0]

            except Exception as e:
                msg = str(e)
                self.update_status(msg)

            if serialnum == self.get_serial():
                self.fv.gui_do(self.update_pick, serialnum, results, qs,
                               x1, y1, wd, ht, fig, msg)

    def _mkreport_header(self):
        rpt = "# ra, dec, eq, x, y, fwhm, fwhm_x, fwhm_y, ellip, bg, sky, bright"
        return rpt
    
    def _mkreport(self, image, qs):
        equinox = 2000.0
        ra_deg, dec_deg = image.pixtoradec(qs.objx, qs.objy, coords='data')
        rpt = "%f, %f, %6.1f, %f, %f, %f, %f, %f, %f, %f, %f, %f" % (
            ra_deg, dec_deg, equinox, qs.objx, qs.objy,
            qs.fwhm, qs.fwhm_x, qs.fwhm_y, qs.elipse,
            qs.background, qs.skylevel, qs.brightness)
        return rpt
    
    def update_pick(self, serialnum, objlist, qs, x1, y1, wd, ht, fig, msg):
        if serialnum != self.get_serial():
            return
        
        try:
            image = self.fitsimage.get_image()
            point = fig.objects[1]
            text = fig.objects[2]
            text.text = "Pick"

            if msg != None:
                raise Exception(msg)
            
            # Mark new peaks, if desired
            if self.show_candidates:
                for obj in objlist:
                    tag = self.fitsimage.add(self.dc.Point(x1+obj.objx,
                                                           y1+obj.objy,
                                                           5,
                                                           linewidth=1,
                                                           color=self.candidate_color),
                                             tagpfx='peak', redraw=False)

            # Add back in offsets into image to get correct values with respect
            # to the entire image
            qs.x += x1
            qs.y += y1
            qs.objx += x1
            qs.objy += y1

            # Calculate X/Y of center of star
            obj_x = qs.objx
            obj_y = qs.objy
            self.logger.info("object center is x,y=%f,%f" % (obj_x, obj_y))
            fwhm = qs.fwhm
            fwhm_x, fwhm_y = qs.fwhm_x, qs.fwhm_y
            point.x, point.y = obj_x, obj_y
            text.color = 'cyan'

            self.wdetail.fwhm_x.set_text('%.3f' % fwhm_x)
            self.wdetail.fwhm_y.set_text('%.3f' % fwhm_y)
            self.wdetail.fwhm.set_text('%.3f' % fwhm)
            self.wdetail.object_x.set_text('%.3f' % (obj_x+1))
            self.wdetail.object_y.set_text('%.3f' % (obj_y+1))
            self.wdetail.sky_level.set_text('%.3f' % qs.skylevel)
            self.wdetail.background.set_text('%.3f' % qs.background)
            self.wdetail.brightness.set_text('%.3f' % qs.brightness)

            self.w.btn_sky_cut.set_enabled(True)
            self.w.btn_bright_cut.set_enabled(True)

            # Mark center of object on pick image
            i1 = point.x - x1
            j1 = point.y - y1
            self.pickcenter.x = i1
            self.pickcenter.y = j1
            self.pickcenter.color = 'cyan'
            self.pick_qs = qs
            self.pickimage.panset_xy(i1, j1, redraw=True)

            # Mark object center on image
            point.color = 'cyan'
            #self.fitsimage.panset_xy(obj_x, obj_y, redraw=False)

            equinox = float(image.get_keyword('EQUINOX', 2000.0))
            # Calc RA, DEC, EQUINOX of X/Y center pixel
            try:
                ra_txt, dec_txt = image.pixtoradec(obj_x, obj_y, format='str')
                self.last_rpt = self._mkreport(image, qs)
                if self.do_record:
                    self.w.report.append_text(self.last_rpt)

            except Exception as e:
                ra_txt = 'WCS ERROR'
                dec_txt = 'WCS ERROR'
            self.wdetail.ra.set_text(ra_txt)
            self.wdetail.dec.set_text(dec_txt)

            self.wdetail.equinox.set_text(str(equinox))

            # Calculate star size from pixel pitch
            try:
                #cdelt1, cdelt2 = image.get_keywords_list('CDELT1', 'CDELT2')
                header = image.get_header()
                ((xrot, yrot),
                 (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(header)
                starsize = self.iqcalc.starsize(fwhm_x, cdelt1, fwhm_y, cdelt2)
                self.wdetail.star_size.set_text('%.3f' % starsize)
            except Exception as e:
                self.wdetail.star_size.set_text('ERROR')
                self.fv.show_error("Couldn't calculate star size: %s" % (
                    str(e)), raisetab=False)

            self.update_status("Done")
            self.plot_panx = float(i1) / wd
            self.plot_pany = float(j1) / ht
            if self.have_mpl:
                self.plot_contours()
                self.plot_fwhm(qs)

        except Exception as e:
            errmsg = "Error calculating quality metrics: %s" % (
                str(e))
            self.logger.error(errmsg)
            self.fv.show_error(errmsg, raisetab=False)
            #self.update_status("Error")
            for key in ('sky_level', 'background', 'brightness',
                        'star_size', 'fwhm_x', 'fwhm_y'):
                self.wdetail[key].set_text('')
            self.wdetail.fwhm.set_text('Failed')
            self.w.btn_sky_cut.set_enabled(False)
            self.w.btn_bright_cut.set_enabled(False)
            self.pick_qs = None
            text.color = 'red'

            self.plot_panx = self.plot_pany = 0.5
            #self.plot_contours()
            # TODO: could calc background based on numpy calc

        self.w.btn_intr_eval.set_enabled(False)
        self.pickimage.redraw(whence=3)
        self.canvas.redraw(whence=3)

        self.fv.showStatus("Click left mouse button to reposition pick")
        return True

    def eval_intr(self):
        self.ev_intr.set()
        
    def btndown(self, canvas, button, data_x, data_y):
        try:
            obj = self.canvas.getObjectByTag(self.picktag)
            if obj.kind == 'rectangle':
                bbox = obj
            else:
                bbox  = obj.objects[0]
                point = obj.objects[1]
            self.dx = (bbox.x2 - bbox.x1) // 2
            self.dy = (bbox.y2 - bbox.y1) // 2
        except Exception as e:
            pass

        dx = self.dx
        dy = self.dy
        
        # Mark center of object and region on main image
        try:
            self.canvas.deleteObjectByTag(self.picktag, redraw=False)
        except:
            pass

        x1, y1 = data_x - dx, data_y - dy
        x2, y2 = data_x + dx, data_y + dy

        tag = self.canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                color='cyan',
                                                linestyle='dash'))
        self.picktag = tag

        #self.setpickregion(self.canvas, tag)
        return True
        
    def update(self, canvas, button, data_x, data_y):
        try:
            obj = self.canvas.getObjectByTag(self.picktag)
            if obj.kind == 'rectangle':
                bbox = obj
            else:
                bbox  = obj.objects[0]
                point = obj.objects[1]
            self.dx = (bbox.x2 - bbox.x1) // 2
            self.dy = (bbox.y2 - bbox.y1) // 2
        except Exception as e:
            obj = None
            pass

        dx = self.dx
        dy = self.dy
        
        x1, y1 = data_x - dx, data_y - dy
        x2, y2 = data_x + dx, data_y + dy
        
        if (not obj) or (obj.kind == 'compound'):
            # Replace compound image with rectangle
            try:
                self.canvas.deleteObjectByTag(self.picktag, redraw=False)
            except:
                pass

            tag = self.canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                    color='cyan',
                                                    linestyle='dash'),
                                  redraw=False)
        else:
            # Update current rectangle with new coords
            bbox.x1, bbox.y1, bbox.x2, bbox.y2 = x1, y1, x2, y2
            tag = self.picktag

        self.setpickregion(self.canvas, tag)
        return True

        
    def drag(self, canvas, button, data_x, data_y):

        obj = self.canvas.getObjectByTag(self.picktag)
        if obj.kind == 'compound':
            bbox = obj.objects[0]
        elif obj.kind == 'rectangle':
            bbox = obj
        else:
            return True

        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate offsets of move
        dx = (data_x - x)
        dy = (data_y - y)

        # calculate new coords
        x1, y1, x2, y2 = bbox.x1+dx, bbox.y1+dy, bbox.x2+dx, bbox.y2+dy

        if (not obj) or (obj.kind == 'compound'):
            # Replace compound image with rectangle
            try:
                self.canvas.deleteObjectByTag(self.picktag, redraw=False)
            except:
                pass

            self.picktag = self.canvas.add(self.dc.Rectangle(x1, y1, x2, y2,
                                                             color='cyan',
                                                             linestyle='dash'))
        else:
            # Update current rectangle with new coords and redraw
            bbox.x1, bbox.y1, bbox.x2, bbox.y2 = x1, y1, x2, y2
            self.canvas.redraw(whence=3)

        return True


    def setpickregion(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        if obj.kind != 'rectangle':
            return True
        canvas.deleteObjectByTag(tag, redraw=False)

        if self.picktag:
            try:
                canvas.deleteObjectByTag(self.picktag, redraw=False)
            except:
                pass

        # determine center of rectangle
        x = obj.x1 + (obj.x2 - obj.x1) // 2
        y = obj.y1 + (obj.y2 - obj.y1) // 2

        tag = canvas.add(self.dc.CompoundObject(
            self.dc.Rectangle(obj.x1, obj.y1, obj.x2, obj.y2,
                              color=self.pickcolor),
            self.dc.Point(x, y, 10, color='red'),
            self.dc.Text(obj.x1, obj.y2+4, "Pick: calc",
                         color=self.pickcolor)),
                         redraw=False)
        self.picktag = tag

        #self.fv.raise_tab("detail")
        return self.redo()
    
    def reset_region(self):
        self.dx = region_default_width
        self.dy = region_default_height

        obj = self.canvas.getObjectByTag(self.picktag)
        if obj.kind != 'compound':
            return True
        bbox = obj.objects[0]
    
        # calculate center of bbox
        wd = bbox.x2 - bbox.x1
        dw = wd // 2
        ht = bbox.y2 - bbox.y1
        dh = ht // 2
        x, y = bbox.x1 + dw, bbox.y1 + dh

        # calculate new coords
        bbox.x1, bbox.y1, bbox.x2, bbox.y2 = (x-self.dx, y-self.dy,
                                              x+self.dx, y+self.dy)

        self.redo()


    def sky_cut(self):
        if not self.pick_qs:
            self.fv.showStatus("Please pick an object to set the sky level!")
            return
        loval = self.pick_qs.skylevel
        oldlo, hival = self.fitsimage.get_cut_levels()
        try:
            loval += self.delta_sky
            self.fitsimage.cut_levels(loval, hival)
            
        except Exception as e:
            self.fv.showStatus("No valid sky level: '%s'" % (loval))
            
    def bright_cut(self):
        if not self.pick_qs:
            self.fv.showStatus("Please pick an object to set the brightness!")
            return
        skyval = self.pick_qs.skylevel
        hival = self.pick_qs.brightness
        loval, oldhi = self.fitsimage.fitsimage.get_cut_levels()
        try:
            # brightness is measured ABOVE sky level
            hival = skyval + hival + self.delta_bright
            self.fitsimage.cut_levels(loval, hival)
            
        except Exception as e:
            self.fv.showStatus("No valid brightness level: '%s'" % (hival))
            
    def zoomset(self, setting, zoomlevel, fitsimage):
        scalefactor = fitsimage.get_scale()
        self.logger.debug("scalefactor = %.2f" % (scalefactor))
        text = self.fv.scale2text(scalefactor)
        self.wdetail.zoom.set_text(text)

    def detailxy(self, canvas, button, data_x, data_y):
        """Motion event in the pick fits window.  Show the pointing
        information under the cursor.
        """
        if button == 0:
            # TODO: we could track the focus changes to make this check
            # more efficient
            fitsimage = self.fv.getfocus_fitsimage()
            # Don't update global information if our fitsimage isn't focused
            if fitsimage != self.fitsimage:
                return True
        
            # Add offsets from cutout
            data_x = data_x + self.pick_x1
            data_y = data_y + self.pick_y1

            return self.fv.showxy(self.fitsimage, data_x, data_y)

    def cutdetail(self, srcimage, dstimage, x1, y1, x2, y2, redraw=True):
        image = srcimage.get_image()
        data, x1, y1, x2, y2 = image.cutout_adjust(x1, y1, x2, y2)

        dstimage.set_data(data, redraw=redraw)

        return (x1, y1, x2, y2, data)

    def pan_plot(self, xdelta, ydelta):
        x1, x2 = self.w.ax.get_xlim()
        y1, y2 = self.w.ax.get_ylim()
        
        self.w.ax.set_xlim(x1+xdelta, x2+xdelta)
        self.w.ax.set_ylim(y1+ydelta, y2+ydelta)
        self.w.canvas.draw()
        
    def add_pick_cb(self):
        if self.last_rpt != None:
            self.w.report.append_text(self.last_rpt)

    def correct_wcs(self):
        # small local function to strip comment and blank lines
        def _flt(line):
            line = line.strip()
            if line.startswith('#'):
                return False
            if len(line) == 0:
                return False
            return True

        # extract image and reference coords from text widgets
        txt1 = self.w.report.get_text()
        lines1 = filter(_flt, txt1.split('\n'))
        txt2 = self.w.correct.get_text()
        lines2 = filter(_flt, txt2.split('\n'))
        assert len(lines1) == len(lines2), \
               Exception("Number of lines don't match in reports")

        img_coords = map(lambda l: map(float, l.split(',')[3:5]), lines1)
        #print "img coords:", img_coords
        ref_coords = map(lambda l: map(float, l.split(',')[0:2]), lines2)
        #print "ref coords:", ref_coords

        image = self.fitsimage.get_image()
        self.fv.nongui_do(self._calc_match, image, img_coords, ref_coords)

    def _calc_match(self, image, img_coords, ref_coords):
        # NOTE: this function is run in a non-gui thread!
        try:
            wcs_m, tup = image.match_wcs(img_coords, ref_coords)
            self.fv.gui_do(self.adjust_wcs, image, wcs_m, tup)

        except Exception as e:
            errmsg = "Error calculating WCS match: %s" % (str(e))
            self.fv.gui_do(self.fv.show_error, errmsg)
            return

    def __str__(self):
        return 'pick'
    
#END
