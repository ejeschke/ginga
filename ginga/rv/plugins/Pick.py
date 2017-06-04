#
# Pick.py -- Pick plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading
import numpy
import time
from collections import OrderedDict
import os.path

from ginga.gw import Widgets, Viewers
from ginga.misc import Bunch
from ginga.util import iqcalc, wcs
from ginga import GingaPlugin
from ginga.util.six.moves import map, zip, filter

try:
    from ginga.gw import Plot
    from ginga.util import plots
    have_mpl = True
except ImportError:
    have_mpl = False

region_default_width = 30
region_default_height = 30


class Pick(GingaPlugin.LocalPlugin):
    """
    Pick
    ====
    Perform astronomical stellar quick analysis.

    The Pick plugin is used to perform quick astronomical data quality analysis
    on stellar objects.  It locates stellar candidates within a drawn rectangle,
    and picks the most likely candidate based on a set of search settings.
    The Full Width Half Max (FWHM) is reported on the candidate object, as
    well as its size based on the plate scale of the detector.  Rough
    measurement of background, sky level and brightness is done.

    Plugin Type: Local
    ------------------
    Pick is a local plugin, which means it is associated with a channel.
    An instance can be opened for each channel.

    Usage
    =====

    Defining the pick area
    ----------------------
    The default pick area is defined as a rectangle of approximately 30x30
    pixels that encloses the search area.

    The move/draw/edit selector at the bottom of the plugin is used to
    determine what operation is being done to the pick area:

    * If "move" is selected then you can move the existing pick area by
      dragging it or clicking where you want the center of it placed.
      If there is no existing area a default one will be created.
    * If "draw" is selected then you can draw a shape with the cursor
      to enclose and define a new pick area.  The default shape is a
      rectangle, but other shapes can be selected in the "Settings" tab.
    * If "edit" is selected, then you can edit the pick area by dragging its
      control points, or moving it by dragging in the bounding box.

    After the area is moved, drawn or edited, it will perform a search on
    the area based on the criteria in the "Settings" tab of the UI
    (see "The Settings Tab", below) and try to locate a candidate.

    If a candidate is found
    -----------------------
    The candidate will be marked with a `Point` (usually an "X") in the
    channel viewer canvas, centered on the object as determined by the
    horizontal and vertical FWHM measurements.

    The top set of tabs in the UI will be populated as follows.
    The "Image" tag will show the contents of the cutout area.

    The widget in this tab is a Ginga widget and so can be zoomed and panned
    with the usual keyboard and mouse bindings (e.g. scroll wheel).  It will
    also be marked with a `Point` centered on the object and additionally the
    pan position will be set to the found center.

    The "Contour" tab will show a contour plot.

    This is a contour plot of the area immediately surrounding the
    candidate, and not usually encompassing the entire region of the pick
    area.  You can use the vertical slider to the right of the plot to
    increase or decrease the area of the contour plot.

    The "FWHM" tab will show a FWHM plot.

    The blue lines show measurements in the X direction and the green lines
    show measurements in the Y direction.  The solid lines indicate actual
    pixel values and the dotted lines indicate the fitted 1D gaussians.
    The shaded green and blue regions indicate the FWHM measurements.

    The "Radial" tab contains a radial profile plot.

    Plotted points in blue are data values, and a line is fitted to the
    data.

    The "Readout" tab will be populated with a summary of the measurements.

    There are two buttons in this tab:

    * The "Pan to pick" button will pan the channel viewer to the
      located center.
    * The "Default Region" button restores the pick region to the default
      shape and size.

    The "Controls" tab has a couple of buttons that will work off of the
    measurements.

    * The "Bg cut" button will set the low cut level of the channel viewer
      to the measured background level.  A delta to this value can be
      applied by setting a value in the "Delta bg" box (press Enter to
      change the setting).
    * The "Sky cut" button will set the low cut level of the channel viewer
      to the measured sky level.  A delta to this value can be
      applied by setting a value in the "Delta sky" box (press Enter to
      change the setting).
    * The "Bright cut" button will set the high cut level of the channel viewer
      to the measured sky+brightness levels.  A delta to this value can be
      applied by setting a value in the "Delta bright" box (press Enter to
      change the setting).

    The "Report" tab is used to record information about the measurements in
    tabular form.

    By pressing the "Add Pick" button the information about the most recent
    candidate is added to the table.  If the "Record Picks automatically"
    checkbox is checked, then any candidates are added to the table
    automatically.

    .. note:: If the "Show candidates" checkbox in the "Settings" tab is
              checked, then *all* objects found in the region (according to
              the Settings) will be added to the table instead of just the
              selected candidate.

    You can clear the table at any time by pressing the "Clear Log" button.
    The log can be saved to a table by putting a valid path and
    filename in the "File:" box and pressing "Save table". File type is
    automatically determined by the given extension (e.g., ".fits" is FITS and
    ".txt" is plain text).

    If no candidate is found
    ------------------------
    If no candidate can be found (based on the Settings) then the pick area
    is marked with a red `Point` centered on the pick area.

    The image cutout will be taken from this central area and so the "Image"
    tab will still have content.  It will also be marked with a central red
    "X" as shown.

    The contour plot will still be produced from the cutout.

    But all the other plots will be cleared.


    The Settings Tab
    ================

    The "Settings" tab controls aspects of the search within the pick area:

    * The "Show candidates" checkbox controls whether all detected sources
      are marked or not (as shown in the figure below).  Additionally, if
      checked then all the found objects are added to the pick log table
      when using the Report controls.
    * The "Draw type" parameter is used to choose the shape of the pick area
      to be drawn.
    * The "Radius" parameter sets the radius to be used when finding and
      evaluating bright peaks in the image.
    * The "Threshold" parameter is used to set a threshold for peak finding;
      if set to None then a reasonable default value will be chosen.
    * The "Min FWHM" and "Max FWHM" parameters can be used to eliminate
      certain sized objects from being candidates.
    * The "Ellipticity" parameter is used to eliminate candidates based on
      their asymmetry in shape.
    * The "Edge" parameter is used to eliminate candidates based on how
      close to the edge of the cutout they are.  **NOTE: currently this
      works reliably only for non-rotated rectangular shapes.**
    * The "Max side" parametergit p is used to limit the size of the bounding box
      that can be used in the pick shape.  Larger sizes take longer to
      evaluate.
    * The "Coordinate Base" parameter is an offset to apply to located
      sources.  Set to "1" if you want sources pixel locations reported
      in a FITS-compliant manner and "0" if you prefer 0-based indexing.
    * The "Calc center" parameter is used to determine whether the center
      is calculated from FWHM fitting ("fwhm") or centroiding ("centroid").
    * The "FWHM fitting" parameter is used to determine which function is
      is used for FWHM fitting ("gaussian" or "moffat").
    * The "Contour Interpolation" parameter is used to set the interpolation
      method used in rendering the background image in the "Contour" plot.

    The "Redo Pick" button will redo the search operation.  It's convenient
    if you have changed some parameters and want to see the effect based on the
    current pick area without disturbing it.
    """
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Pick, self).__init__(fv, fitsimage)

        self.layertag = 'pick-canvas'
        self.pickimage = None
        self.pickcenter = None
        self.pick_qs = None
        self.picktag = None
        self._textlabel = 'Pick'

        # types of pick shapes that can be drawn
        self.drawtypes = ['rectangle', 'box', 'circle', 'ellipse',
                          'freepolygon', 'polygon', 'triangle']

        # get Pick preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Pick')
        self.settings.load(onError='silent')

        self.sync_preferences()

        self.pick_x1 = 0
        self.pick_y1 = 0
        self.pick_data = None
        self.pick_log = None
        self.dx = region_default_width
        self.dy = region_default_height
        # For offloading intensive calculation from graphics thread
        self.serialnum = 0
        self.lock = threading.RLock()
        self.lock2 = threading.RLock()
        self.ev_intr = threading.Event()

        self.last_rpt = []
        self.rpt_dict = OrderedDict({})
        self.rpt_cnt = 0
        self.rpt_tbl = None
        self.rpt_mod_time = 0.0
        self.rpt_wrt_time = 0.0
        self.rpt_wrt_interval = self.settings.get('report_write_interval',
                                                  30.0)

        self.iqcalc = iqcalc.IQCalc(self.logger)
        self.contour_interp_methods = ('bilinear', 'nearest', 'bicubic')
        self.copy_attrs = ['transforms', 'cutlevels', 'autocuts']
        if (self.settings.get('pick_cmap_name', None) is None and
            self.settings.get('pick_imap_name', None) is None):
            self.copy_attrs.append('rgbmap')

        self.dc = self.fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype(self.pickshape, color='cyan', linestyle='dash')
        canvas.set_callback('draw-event', self.draw_cb)
        canvas.set_callback('edit-event', self.edit_cb)
        canvas.add_draw_mode('move', down=self.btn_down,
                             move=self.btn_drag, up=self.btn_up)
        canvas.register_for_cursor_drawing(self.fitsimage)
        canvas.set_surface(self.fitsimage)
        canvas.set_draw_mode('move')
        self.canvas = canvas

        self.have_mpl = have_mpl

    def sync_preferences(self):
        # Load various preferences
        self.pickcolor = self.settings.get('color_pick', 'green')
        self.pickshape = self.settings.get('shape_pick', 'rectangle')
        if self.pickshape not in self.drawtypes:
            self.pickshape = 'box'
        self.candidate_color = self.settings.get('color_candidate', 'orange')

        # Peak finding parameters and selection criteria
        self.max_side = self.settings.get('max_side', 1024)
        self.radius = self.settings.get('radius', 10)
        self.threshold = self.settings.get('threshold', None)
        self.min_fwhm = self.settings.get('min_fwhm', 2.0)
        self.max_fwhm = self.settings.get('max_fwhm', 50.0)
        self.min_ellipse = self.settings.get('min_ellipse', 0.5)
        self.edgew = self.settings.get('edge_width', 0.01)
        self.show_candidates = self.settings.get('show_candidates', False)
        # Report in 0- or 1-based coordinates
        coord_offset = self.fv.settings.get('pixel_coords_offset', 0.0)
        self.pixel_coords_offset = self.settings.get('pixel_coords_offset',
                                                     coord_offset)
        self.center_algs = ['fwhm', 'centroid']
        self.center_alg = self.settings.get('calc_center_alg', 'fwhm')
        self.fwhm_algs = ['gaussian', 'moffat']
        self.fwhm_alg = self.settings.get('calc_fwhm_alg', 'gaussian')

        # For controls
        self.delta_bg = self.settings.get('delta_bg', 0.0)
        self.delta_sky = self.settings.get('delta_sky', 0.0)
        self.delta_bright = self.settings.get('delta_bright', 0.0)

        # Formatting for reports
        self.do_record = self.settings.get('record_picks', False)
        columns = [("RA", 'ra_txt'), ("DEC", 'dec_txt'), ("Equinox", 'equinox'),
                   ("X", 'x'), ("Y", 'y'), ("FWHM", 'fwhm'),
                   ("FWHM_X", 'fwhm_x'), ("FWHM_Y", 'fwhm_y'),
                   ("Star Size", 'starsize'),
                   ("Ellip", 'ellipse'), ("Background", 'background'),
                   ("Sky Level", 'skylevel'), ("Brightness", 'brightness'),
                   ("Time Local", 'time_local'), ("Time UT", 'time_ut'),
                   ("RA deg", 'ra_deg'), ("DEC deg", 'dec_deg'),
                   ]
        self.rpt_columns = self.settings.get('report_columns', columns)

        # For contour plot
        self.num_contours = self.settings.get('num_contours', 8)
        self.contour_size_max = self.settings.get('contour_size_limit', 70)
        self.contour_size_min = self.settings.get('contour_size_min', 10)
        self.contour_interpolation = self.settings.get('contour_interpolation',
                                                       'bilinear')

    def build_gui(self, container):
        assert iqcalc.have_scipy == True, \
               Exception("Please install python-scipy to use this plugin")

        vtop = Widgets.VBox()
        vtop.set_border_width(4)

        box, sw, orientation = Widgets.get_oriented_box(container)
        box.set_border_width(4)
        box.set_spacing(2)

        paned = Widgets.Splitter(orientation=orientation)

        nb = Widgets.TabWidget(tabpos='bottom')
        self.w.nb1 = nb
        paned.add_widget(Widgets.hadjust(nb, orientation))

        cm, im = self.fv.cm, self.fv.im

        di = Viewers.CanvasView(logger=self.logger)
        width, height = 400, 300
        di.set_desired_size(width, height)
        di.enable_autozoom('off')
        di.enable_autocuts('off')
        di.zoom_to(3)
        settings = di.get_settings()
        settings.get_setting('zoomlevel').add_callback('set',
                               self.zoomset, di)

        cmname = self.settings.get('pick_cmap_name', None)
        if cmname is not None:
            di.set_color_map(cmname)
        else:
            di.set_cmap(cm)
        imname = self.settings.get('pick_imap_name', None)
        if imname is not None:
            di.set_intensity_map(imname)
        else:
            di.set_imap(im)
        di.set_callback('none-move', self.detailxy)
        di.set_bg(0.4, 0.4, 0.4)
        # for debugging
        di.set_name('pickimage')
        self.pickimage = di

        bd = di.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)
        bd.enable_cmap(True)

        di.configure(width, height)

        p_canvas = di.get_canvas()
        tag = p_canvas.add(self.dc.Point(width / 2, height / 2, 5,
                                         linewidth=1, color='red'))
        self.pickcenter = p_canvas.get_object_by_tag(tag)

        iw = Viewers.GingaViewerWidget(viewer=di)
        iw.resize(width, height)
        nb.add_widget(iw, title="Image")

        if have_mpl:
            # Contour plot
            hbox = Widgets.HBox()
            self.contour_plot = plots.ContourPlot(logger=self.logger,
                                                  width=width, height=height)
            if plots.MPL_GE_2_0:
                kwargs = {'facecolor': 'black'}
            else:
                kwargs = {'axisbg': 'black'}
            self.contour_plot.add_axis(**kwargs)
            pw = Plot.PlotWidget(self.contour_plot)
            pw.resize(width, height)
            hbox.add_widget(pw, stretch=1)

            # calc contour zoom setting
            max_z = 100
            zv = int(numpy.sqrt(self.dx**2 + self.dy**2) * 0.15)
            zv = max(1, min(zv, 100))
            self.contour_plot.plot_zoomlevel = zv

            zoom = Widgets.Slider(orientation='vertical', track=True)
            zoom.set_limits(1, max_z, incr_value=1)
            zoom.set_value(zv)

            def zoom_contour_cb(w, val):
                self.contour_plot.plot_zoom(val/10.0)

            zoom.add_callback('value-changed', zoom_contour_cb)
            hbox.add_widget(zoom, stretch=0)
            nb.add_widget(hbox, title="Contour")

            # FWHM gaussians plot
            self.fwhm_plot = plots.FWHMPlot(logger=self.logger,
                                            width=width, height=height)
            if plots.MPL_GE_2_0:
                kwargs = {'facecolor': 'white'}
            else:
                kwargs = {'axisbg': 'white'}
            self.fwhm_plot.add_axis(**kwargs)
            pw = Plot.PlotWidget(self.fwhm_plot)
            pw.resize(width, height)
            nb.add_widget(pw, title="FWHM")

            # Radial profile plot
            self.radial_plot = plots.RadialPlot(logger=self.logger,
                                                width=width, height=height)
            self.radial_plot.add_axis(**kwargs)
            pw = Plot.PlotWidget(self.radial_plot)
            pw.resize(width, height)
            nb.add_widget(pw, title="Radial")

        fr = Widgets.Frame(self._textlabel)

        nb = Widgets.TabWidget(tabpos='bottom')
        self.w.nb2 = nb

        # Build report panel
        captions = (('Zoom:', 'label', 'Zoom', 'llabel'),
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
                    ('Pan to pick', 'button'),
                    )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.zoom.set_text(self.fv.scale2text(di.get_scale()))
        self.wdetail = b
        b.default_region.add_callback('activated',
                                      lambda w: self.reset_region())
        b.default_region.set_tooltip("Reset region size to default")
        b.pan_to_pick.add_callback('activated',
                                   lambda w: self.pan_to_pick_cb())
        b.pan_to_pick.set_tooltip("Pan image to pick center")

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
                    ("Draw type:", 'label', 'xlbl_drawtype', 'label',
                     "Draw type", 'combobox'),
                    ('Radius:', 'label', 'xlbl_radius', 'label',
                     'Radius', 'spinbutton'),
                    ('Threshold:', 'label', 'xlbl_threshold', 'label',
                     'Threshold', 'entry'),
                    ('Min FWHM:', 'label', 'xlbl_min_fwhm', 'label',
                     'Min FWHM', 'spinfloat'),
                    ('Max FWHM:', 'label', 'xlbl_max_fwhm', 'label',
                     'Max FWHM', 'spinfloat'),
                    ('Ellipticity:', 'label', 'xlbl_ellipticity', 'label',
                     'Ellipticity', 'entry'),
                    ('Edge:', 'label', 'xlbl_edge', 'label',
                     'Edge', 'entry'),
                    ('Max side:', 'label', 'xlbl_max_side', 'label',
                     'Max side', 'spinbutton'),
                    ('Coordinate Base:', 'label',
                     'xlbl_coordinate_base', 'label',
                     'Coordinate Base', 'entry'),
                    ("Calc center:", 'label', 'xlbl_calccenter', 'label',
                     "Calc center", 'combobox'),
                    ("FWHM fitting:", 'label', 'xlbl_fwhmfitting', 'label',
                     "FWHM fitting", 'combobox'),
                    ('Contour Interpolation:', 'label', 'xlbl_cinterp', 'label',
                     'Contour Interpolation', 'combobox'),
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
        b.max_side.set_tooltip("Maximum dimension to search for peaks")
        b.coordinate_base.set_tooltip("Base of pixel coordinate system")
        b.calc_center.set_tooltip("How to calculate the center of object")
        b.fwhm_fitting.set_tooltip("Function for fitting the FWHM")
        b.contour_interpolation.set_tooltip("Interpolation for use in contour plot")

        def chg_pickshape(w, idx):
            pickshape = self.drawtypes[idx]
            self.set_drawtype(pickshape)
            return True
        combobox = b.draw_type
        for name in self.drawtypes:
            combobox.append_text(name)
        index = self.drawtypes.index(self.pickshape)
        combobox.set_index(index)
        combobox.add_callback('activated', chg_pickshape)
        b.xlbl_drawtype.set_text(self.pickshape)

        # radius control
        #b.radius.set_digits(2)
        #b.radius.set_numeric(True)
        b.radius.set_limits(5, 200, incr_value=1)

        def chg_radius(w, val):
            self.radius = int(val)
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

        combobox = b.contour_interpolation
        def chg_contour_interp(w, idx):
            self.contour_interpolation = self.contour_interp_methods[idx]
            self.w.xlbl_cinterp.set_text(self.contour_interpolation)
            self.contour_plot.interpolation = self.contour_interpolation
            return True
        for name in self.contour_interp_methods:
            combobox.append_text(name)
        index = self.contour_interp_methods.index(self.contour_interpolation)
        combobox.set_index(index)
        self.w.xlbl_cinterp.set_text(self.contour_interpolation)
        self.contour_plot.interpolation = self.contour_interpolation
        combobox.add_callback('activated', chg_contour_interp)

        b.show_candidates.set_state(self.show_candidates)
        b.show_candidates.add_callback('activated', self.show_candidates_cb)
        self.w.xlbl_coordinate_base.set_text(str(self.pixel_coords_offset))
        b.coordinate_base.set_text(str(self.pixel_coords_offset))
        b.coordinate_base.add_callback('activated', self.coordinate_base_cb)

        def chg_calccenter(w, idx):
            self.center_alg = self.center_algs[idx]
            self.w.xlbl_calccenter.set_text(self.center_alg)
            return True
        combobox = b.calc_center
        for name in self.center_algs:
            combobox.append_text(name)
        index = self.center_algs.index(self.center_alg)
        combobox.set_index(index)
        combobox.add_callback('activated', chg_calccenter)
        b.xlbl_calccenter.set_text(self.center_alg)

        def chg_fwhmfitting(w, idx):
            self.fwhm_alg = self.fwhm_algs[idx]
            self.w.xlbl_fwhmfitting.set_text(self.fwhm_alg)
            return True
        combobox = b.fwhm_fitting
        for name in self.fwhm_algs:
            combobox.append_text(name)
        index = self.fwhm_algs.index(self.fwhm_alg)
        combobox.set_index(index)
        combobox.add_callback('activated', chg_fwhmfitting)
        b.xlbl_fwhmfitting.set_text(self.fwhm_alg)

        sw2 = Widgets.ScrollArea()
        sw2.set_widget(w)

        vbox3 = Widgets.VBox()
        vbox3.add_widget(sw2, stretch=1)

        btns = Widgets.HBox()
        btn = Widgets.Button('Redo Pick')
        btn.add_callback('activated', lambda w: self.redo_manual())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox3.add_widget(btns, stretch=0)
        nb.add_widget(vbox3, title="Settings")

        # Build controls panel
        vbox3 = Widgets.VBox()
        captions = (
            ('Bg cut', 'button', 'Delta bg:', 'label',
             'xlbl_delta_bg', 'label', 'Delta bg', 'entry'),
            ('Sky cut', 'button', 'Delta sky:', 'label',
             'xlbl_delta_sky', 'label', 'Delta sky', 'entry'),
            ('Bright cut', 'button', 'Delta bright:', 'label',
             'xlbl_delta_bright', 'label', 'Delta bright', 'entry'),
            )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.bg_cut.set_tooltip("Set image low cut to Background Level")
        b.delta_bg.set_tooltip("Delta to apply to this cut")
        b.sky_cut.set_tooltip("Set image low cut to Sky Level")
        b.delta_sky.set_tooltip("Delta to apply to this cut")
        b.bright_cut.set_tooltip("Set image high cut to Sky Level+Brightness")
        b.delta_bright.set_tooltip("Delta to apply to this cut")

        b.bg_cut.set_enabled(False)
        self.w.btn_bg_cut = b.bg_cut
        self.w.btn_bg_cut.add_callback('activated', lambda w: self.bg_cut())
        self.w.bg_cut_delta = b.delta_bg
        b.xlbl_delta_bg.set_text(str(self.delta_bg))
        b.delta_bg.set_text(str(self.delta_bg))
        def chg_delta_bg(w):
            delta_bg = 0.0
            val = w.get_text().strip()
            if len(val) > 0:
                delta_bg = float(val)
            self.delta_bg = delta_bg
            self.w.xlbl_delta_bg.set_text(str(self.delta_bg))
            return True
        b.delta_bg.add_callback('activated', chg_delta_bg)

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

        vbox3.add_widget(w, stretch=0)
        vbox3.add_widget(Widgets.Label(''), stretch=1)
        nb.add_widget(vbox3, title="Controls")

        vbox3 = Widgets.VBox()
        tv = Widgets.TreeView(sortable=True, use_alt_row_color=True)
        self.rpt_tbl = tv
        vbox3.add_widget(tv, stretch=1)

        tv.setup_table(self.rpt_columns, 1, 'time_local')

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btn = Widgets.Button("Add Pick")
        btn.add_callback('activated', lambda w: self.add_pick_cb())
        btns.add_widget(btn)
        btn = Widgets.CheckBox("Record Picks automatically")
        btn.set_state(self.do_record)
        btn.add_callback('activated', self.record_cb)
        btns.add_widget(btn)
        btn = Widgets.Button("Clear Log")
        btn.add_callback('activated', lambda w: self.clear_pick_log_cb())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox3.add_widget(btns, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btn = Widgets.Button("Save table")
        btn.add_callback('activated', self.write_pick_log_cb)
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label("File:"))
        ent = Widgets.TextEntry()
        report_log = self.settings.get('report_log_path', None)
        if report_log is None:
            report_log = "pick_log.fits"
        ent.set_text(report_log)
        ent.set_tooltip('File type determined by extension')
        self.w.report_log = ent
        btns.add_widget(ent, stretch=1)
        vbox3.add_widget(btns, stretch=0)

        nb.add_widget(vbox3, title="Report")

        fr.set_widget(nb)

        box.add_widget(fr, stretch=5)
        paned.add_widget(sw)
        # hack to set a reasonable starting position for the splitter
        paned.set_sizes([height, height])
        vtop.add_widget(paned, stretch=5)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Move")
        btn1.set_state(mode == 'move')
        btn1.add_callback('activated', lambda w, val: self.set_mode_cb('move', val))
        btn1.set_tooltip("Choose this to position pick")
        self.w.btn_move = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback('activated', lambda w, val: self.set_mode_cb('draw', val))
        btn2.set_tooltip("Choose this to draw a replacement pick")
        self.w.btn_draw = btn2
        hbox.add_widget(btn2)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback('activated', lambda w, val: self.set_mode_cb('edit', val))
        btn3.set_tooltip("Choose this to edit or move a pick")
        self.w.btn_edit = btn3
        hbox.add_widget(btn3)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        vtop.add_widget(hbox, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vtop.add_widget(btns, stretch=0)

        container.add_widget(vtop, stretch=5)

    def record_cb(self, w, tf):
        self.do_record = tf
        return True

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
            objs = self.canvas.get_objects_by_tag_pfx('peak')
            self.canvas.delete_objects(objs)

    def coordinate_base_cb(self, w):
        self.pixel_coords_offset = float(w.get_text())
        self.w.xlbl_coordinate_base.set_text(str(self.pixel_coords_offset))

    def bump_serial(self):
        with self.lock:
            self.serialnum += 1
            return self.serialnum

    def get_serial(self):
        with self.lock:
            return self.serialnum

    def plot_contours(self, image):
        # Make a contour plot

        ht, wd = self.pick_data.shape
        x, y = self.pick_x1 + wd // 2, self.pick_y1 + ht // 2

        # If size of pick region is too small/large, recut out a subset
        # around the picked object coordinates for plotting contours
        recut = False
        if wd < self.contour_size_min or wd > self.contour_size_max:
            wd = max(self.contour_size_min, min(wd, self.contour_size_max))
            recut = True
        if ht < self.contour_size_min or ht > self.contour_size_max:
            ht = max(self.contour_size_min, min(ht, self.contour_size_max))
            recut = True

        if recut:
            radius = max(wd, ht)

            if self.pick_qs is not None:
                x, y = self.pick_qs.x, self.pick_qs.y
            data, x1, y1, x2, y2 = image.cutout_radius(x, y, radius)
            x, y = x - x1, y - y1
            ht, wd = data.shape

        else:
            data = self.pick_data
            x, y = self.pickcenter.x, self.pickcenter.y

        try:
            self.contour_plot.plot_contours_data(x, y, data,
                                                 num_contours=self.num_contours)

        except Exception as e:
            self.logger.error("Error making contour plot: %s" % (
                str(e)))

    def clear_contours(self):
        self.contour_plot.clear()

    def plot_fwhm(self, qs, image):
        # Make a FWHM plot
        x, y, radius = qs.x, qs.y, qs.fwhm_radius

        try:
            self.fwhm_plot.plot_fwhm(x, y, radius, image,
                                     cutout_data=self.pick_data,
                                     iqcalc=self.iqcalc,
                                     fwhm_method=self.fwhm_alg)

        except Exception as e:
            self.logger.error("Error making fwhm plot: %s" % (
                str(e)))

    def clear_fwhm(self):
        self.fwhm_plot.clear()

    def plot_radial(self, qs, image):
        # Make a radial plot
        x, y, radius = qs.x, qs.y, qs.fwhm_radius

        try:
            self.radial_plot.plot_radial(x, y, radius, image)

        except Exception as e:
            self.logger.error("Error making radial plot: %s" % (
                str(e)))

    def clear_radial(self):
        self.radial_plot.clear()

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True)
        self.fv.show_status("Draw a rectangle with the right mouse button")

    def stop(self):
        # Delete previous peak marks
        objs = self.canvas.get_objects_by_tag_pfx('peak')
        self.canvas.delete_objects(objs)

        # deactivate the canvas
        self.canvas.ui_set_active(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass
        self.fv.show_status("")

    def redo_manual(self):
        serialnum = self.bump_serial()
        self.ev_intr.set()

        self._redo(serialnum)

    def redo(self):
        serialnum = self.bump_serial()
        self._redo(serialnum)

    def _redo(self, serialnum):
        if self.picktag is None:
            return

        pickobj = self.canvas.get_object_by_tag(self.picktag)
        if pickobj.kind != 'compound':
            return True
        shape = pickobj.objects[0]
        point = pickobj.objects[1]
        text = pickobj.objects[2]

        # reposition other elements to match
        ctr_x, ctr_y = shape.get_center_pt()
        point.x, point.y = ctr_x, ctr_y
        x1, y1, x2, y2 = shape.get_llur()
        text.x, text.y = x1, y2 + 4

        try:
            image = self.fitsimage.get_image()

            # sanity check on size of region
            width, height = abs(x2 - x1), abs(y2 - y1)

            if (width > self.max_side) or (height > self.max_side):
                errmsg = "Image area (%dx%d) too large!" % (
                    width, height)
                self.fv.show_error(errmsg)
                raise Exception(errmsg)

            # Extract image in pick window
            self.logger.debug("bbox %f,%f %f,%f" % (x1, y1, x2, y2))
            x1, y1, x2, y2, data = self.cutdetail(image, shape)
            self.logger.debug("cut box %d,%d %d,%d" % (x1, y1, x2, y2))

            # calculate center of pick image
            ht, wd = data.shape[:2]
            xc = wd // 2
            yc = ht // 2
            self.pick_x1, self.pick_y1 = x1, y1
            self.pick_data = data

            point.color = 'red'
            text.text = '{0}: calc'.format(self._textlabel)
            self.pickcenter.x = xc
            self.pickcenter.y = yc
            self.pickcenter.color = 'red'

            # Offload this task to another thread so that GUI remains
            # responsive
            self.fv.nongui_do(self.search, serialnum, data,
                              x1, y1, wd, ht, pickobj)

        except Exception as e:
            self.logger.error("Error calculating quality metrics: %s" % (
                str(e)))
            return True

    def search(self, serialnum, data, x1, y1, wd, ht, pickobj):

        with self.lock2:
            if serialnum != self.get_serial():
                return

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
                                                     ev_intr=self.ev_intr,
                                                     fwhm_method=self.fwhm_alg)

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

                # Add back in offsets into image to get correct values with
                # respect to the entire image
                for qs in results:
                    qs.x += x1
                    qs.y += y1
                    qs.objx += x1
                    qs.objy += y1
                    qs.oid_x += x1
                    qs.oid_y += y1

                # pick main result
                qs = results[0]

            except Exception as e:
                msg = str(e)
                self.update_status(msg)

            self.fv.gui_do(self.update_pick, serialnum, results, qs,
                           x1, y1, wd, ht, data, pickobj, msg)

    def _make_report_header(self):
        return self.rpt_header + '\n'

    def _make_report(self, image, qs):
        d = Bunch.Bunch()
        try:
            x, y = qs.objx, qs.objy
            if (qs.oid_x is not None) and (self.center_alg == 'centroid'):
                # user wants RA/DEC calculated by centroid instead of fwhm
                x, y = qs.oid_x, qs.oid_y

            equinox = float(image.get_keyword('EQUINOX', 2000.0))
            try:
                ra_deg, dec_deg = image.pixtoradec(x, y, coords='data')
                ra_txt, dec_txt = wcs.deg2fmt(ra_deg, dec_deg, 'str')

            except Exception as e:
                self.logger.warning("Couldn't calculate sky coordinates: %s" % (str(e)))
                ra_deg, dec_deg = 0.0, 0.0
                ra_txt = dec_txt = 'BAD WCS'

            # Calculate star size from pixel pitch
            try:
                header = image.get_header()
                ((xrot, yrot),
                 (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(header)

                starsize = self.iqcalc.starsize(qs.fwhm_x, cdelt1,
                                                qs.fwhm_y, cdelt2)
            except Exception as e:
                self.logger.warning("Couldn't calculate star size: %s" % (str(e)))
                starsize = 0.0

            rpt_x = x + self.pixel_coords_offset
            rpt_y = y + self.pixel_coords_offset

            # make a report in the form of a dictionary
            d.setvals(x = rpt_x, y = rpt_y,
                      ra_deg = ra_deg, dec_deg = dec_deg,
                      ra_txt = ra_txt, dec_txt = dec_txt,
                      equinox = equinox,
                      fwhm = qs.fwhm,
                      fwhm_x = qs.fwhm_x, fwhm_y = qs.fwhm_y,
                      ellipse = qs.elipse, background = qs.background,
                      skylevel = qs.skylevel, brightness = qs.brightness,
                      starsize = starsize,
                      time_local = time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.localtime()),
                      time_ut = time.strftime("%Y-%m-%d %H:%M:%S",
                                              time.gmtime()),
                      )
        except Exception as e:
            self.logger.error("Error making report: %s" % (str(e)))

        return d

    def update_pick(self, serialnum, objlist, qs, x1, y1, wd, ht, data,
                    pickobj, msg):

        try:
            # set the pick image to have the same cut levels and transforms
            self.fitsimage.copy_attributes(self.pickimage, self.copy_attrs)
            self.pickimage.set_data(data)

            # Delete previous peak marks
            objs = self.canvas.get_objects_by_tag_pfx('peak')
            self.canvas.delete_objects(objs)

            image = self.fitsimage.get_image()
            shape_obj = pickobj.objects[0]
            point = pickobj.objects[1]
            text = pickobj.objects[2]
            text.text = self._textlabel

            if msg is not None:
                raise Exception(msg)

            # Mark new peaks, if desired
            if self.show_candidates:
                reports = list(map(lambda x: self._make_report(image, x),
                                   objlist))
                for obj in objlist:
                    tag = self.canvas.add(self.dc.Point(obj.objx,
                                                        obj.objy,
                                                        5,
                                                        linewidth=1,
                                                        color=self.candidate_color),
                                          tagpfx='peak')
            else:
                reports = [self._make_report(image, qs)]

            # Calculate X/Y of center of star
            obj_x = qs.objx
            obj_y = qs.objy
            fwhm = qs.fwhm
            fwhm_x, fwhm_y = qs.fwhm_x, qs.fwhm_y
            point.x, point.y = obj_x, obj_y
            text.color = 'cyan'

            # Make report
            self.last_rpt = reports
            if self.do_record:
                self.add_reports(reports)
                self.last_rpt = []

            d = reports[0]
            self.wdetail.sample_area.set_text('%dx%d' % (wd, ht))
            self.wdetail.fwhm_x.set_text('%.3f' % fwhm_x)
            self.wdetail.fwhm_y.set_text('%.3f' % fwhm_y)
            self.wdetail.fwhm.set_text('%.3f' % fwhm)
            self.wdetail.object_x.set_text('%.3f' % (d.x))
            self.wdetail.object_y.set_text('%.3f' % (d.y))
            self.wdetail.sky_level.set_text('%.3f' % qs.skylevel)
            self.wdetail.background.set_text('%.3f' % qs.background)
            self.wdetail.brightness.set_text('%.3f' % qs.brightness)
            self.wdetail.ra.set_text(d.ra_txt)
            self.wdetail.dec.set_text(d.dec_txt)
            self.wdetail.equinox.set_text(str(d.equinox))
            self.wdetail.star_size.set_text('%.3f' % d.starsize)

            self.w.btn_bg_cut.set_enabled(True)
            self.w.btn_sky_cut.set_enabled(True)
            self.w.btn_bright_cut.set_enabled(True)

            # Mark center of object on pick image
            i1 = point.x - x1
            j1 = point.y - y1
            self.pickcenter.x = i1
            self.pickcenter.y = j1
            self.pickcenter.color = 'cyan'
            self.pick_qs = qs
            self.pickimage.panset_xy(i1, j1)

            # Mark object center on image
            point.color = 'cyan'
            shape_obj.linestyle = 'solid'
            #self.fitsimage.panset_xy(obj_x, obj_y)

            self.update_status("Done")
            self.plot_panx = float(i1) / wd
            self.plot_pany = float(j1) / ht
            if self.have_mpl:
                self.plot_contours(image)
                self.plot_fwhm(qs, image)
                self.plot_radial(qs, image)

        except Exception as e:
            errmsg = "Error calculating quality metrics: %s" % (
                str(e))
            self.logger.error(errmsg)
            self.fv.show_error(errmsg, raisetab=False)
            #self.update_status("Error")
            for key in ('sky_level', 'background', 'brightness',
                        'star_size', 'fwhm_x', 'fwhm_y',
                        'ra', 'dec', 'object_x', 'object_y'):
                self.wdetail[key].set_text('')
            self.wdetail.fwhm.set_text('Failed')
            self.w.btn_bg_cut.set_enabled(False)
            self.w.btn_sky_cut.set_enabled(False)
            self.w.btn_bright_cut.set_enabled(False)
            self.pick_qs = None
            text.color = 'red'
            shape_obj.linestyle = 'dash'

            self.plot_panx = self.plot_pany = 0.5
            if self.have_mpl:
                self.plot_contours(image)
                # TODO: could calc background based on numpy calc
                self.clear_fwhm()
                self.clear_radial()

        self.w.btn_intr_eval.set_enabled(False)
        self.pickimage.redraw(whence=3)
        self.canvas.redraw(whence=3)

        self.fv.show_status("Click left mouse button to reposition pick")
        return True

    def eval_intr(self):
        self.ev_intr.set()

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        if obj.kind not in self.drawtypes:
            return True
        canvas.delete_object_by_tag(tag)

        if self.picktag is not None:
            try:
                canvas.delete_object_by_tag(self.picktag)
            except:
                pass

        # determine center of bounding box
        x1, y1, x2, y2 = obj.get_llur()
        x = x1 + (x2 - x1) // 2
        y = y1 + (y2 - y1) // 2

        obj.color = self.pickcolor
        tag = canvas.add(self.dc.CompoundObject(
            obj,
            self.dc.Point(x, y, 10, color='red'),
            self.dc.Text(x1, y2+4, '{0}: calc'.format(self._textlabel),
                         color=self.pickcolor)))
        self.picktag = tag

        return self.redo_manual()

    def edit_cb(self, canvas, obj):
        if obj.kind not in self.drawtypes:
            return True

        # Get the compound object that sits on the canvas.
        # Make sure edited rectangle was our pick rectangle.
        c_obj = self.canvas.get_object_by_tag(self.picktag)
        if (c_obj.kind != 'compound') or (len(c_obj.objects) < 3) or \
               (c_obj.objects[0] != obj):
            return False

        return self.redo_manual()

    def reset_region(self):
        self.dx = region_default_width
        self.dy = region_default_height
        self.set_drawtype('rectangle')

        if not self.canvas.has_tag(self.picktag):
            return
        obj = self.canvas.get_object_by_tag(self.picktag)
        if obj.kind != 'compound':
            return
        shape = obj.objects[0]

        # determine center of shape
        data_x, data_y = shape.get_center_pt()
        rd_x, rd_y = self.dx // 2, self.dy // 2
        x1, y1 = data_x - rd_x, data_y - rd_y
        x2, y2 = data_x + rd_x, data_y + rd_y

        # replace shape
        # TODO: makes sense to change this to 'box'
        Rect = self.canvas.get_draw_class('rectangle')
        tag = self.canvas.add(Rect(x1, y1, x2, y2,
                                   color=self.pickcolor))

        self.draw_cb(self.canvas, tag)

    def pan_to_pick_cb(self):
        if not self.pick_qs:
            self.fv.show_status("Please pick an object to set the sky level!")
            return
        pan_x, pan_y = self.pick_qs.objx, self.pick_qs.objy

        # TODO: convert to WCS coords based on user preference
        self.fitsimage.set_pan(pan_x, pan_y, coord='data')
        return True

    def bg_cut(self):
        if not self.pick_qs:
            self.fv.show_status("Please pick an object to set the bg level!")
            return
        loval = self.pick_qs.background
        oldlo, hival = self.fitsimage.get_cut_levels()
        try:
            loval += self.delta_bg
            self.fitsimage.cut_levels(loval, hival)

        except Exception as e:
            self.fv.show_status("No valid bg level: '%s'" % (loval))

    def sky_cut(self):
        if not self.pick_qs:
            self.fv.show_status("Please pick an object to set the sky level!")
            return
        loval = self.pick_qs.skylevel
        oldlo, hival = self.fitsimage.get_cut_levels()
        try:
            loval += self.delta_sky
            self.fitsimage.cut_levels(loval, hival)

        except Exception as e:
            self.fv.show_status("No valid sky level: '%s'" % (loval))

    def bright_cut(self):
        if not self.pick_qs:
            self.fv.show_status("Please pick an object to set the brightness!")
            return
        skyval = self.pick_qs.skylevel
        hival = self.pick_qs.brightness
        loval, oldhi = self.fitsimage.get_cut_levels()
        try:
            # brightness is measured ABOVE sky level
            hival = skyval + hival + self.delta_bright
            self.fitsimage.cut_levels(loval, hival)

        except Exception as e:
            self.fv.show_status("No valid brightness level: '%s'" % (hival))

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
            chviewer = self.fv.getfocus_viewer()
            # Don't update global information if our chviewer isn't focused
            if chviewer != self.fitsimage:
                return True

            # Add offsets from cutout
            data_x = data_x + self.pick_x1
            data_y = data_y + self.pick_y1

            return self.fv.showxy(chviewer, data_x, data_y)

    def cutdetail(self, image, shape_obj):
        view, mask = image.get_shape_view(shape_obj)

        data = image._slice(view)

        y1, y2 = view[0].start, view[0].stop
        x1, x2 = view[1].start, view[1].stop

        # mask non-containing members
        mdata = numpy.ma.array(data, mask=numpy.logical_not(mask))

        return (x1, y1, x2, y2, mdata)

    def pan_plot(self, xdelta, ydelta):
        x1, x2 = self.w.ax.get_xlim()
        y1, y2 = self.w.ax.get_ylim()

        self.w.ax.set_xlim(x1+xdelta, x2+xdelta)
        self.w.ax.set_ylim(y1+ydelta, y2+ydelta)
        self.w.canvas.draw()

    def write_pick_log(self, filepath):
        if len(self.rpt_dict) == 0:
            return

        # Save the table as a binary table HDU
        from astropy.table import Table

        try:
            self.logger.debug("Writing modified pick log")
            tbl = Table(rows=list(self.rpt_dict.values()))
            tbl.meta['comments'] = ["Written by ginga Pick plugin"]
            if filepath.lower().endswith('.txt'):
                fmt = 'ascii.commented_header'
            else:
                fmt = None
            tbl.write(filepath, format=fmt, overwrite=True)
            self.rpt_wrt_time = time.time()

        except Exception as e:
            self.logger.error("Error writing to pick log: %s" % (str(e)))

    def write_pick_log_cb(self, w):
        path = self.w.report_log.get_text().strip()
        self.write_pick_log(path)

    def add_reports(self, reports):
        for rpt in reports:
            self.rpt_cnt += 1
            # Hack to insure that we get the columns in the desired order
            d = OrderedDict([(key, rpt[key])
                             for col, key in self.rpt_columns])
            self.rpt_dict[self.rpt_cnt] = d
            self.rpt_mod_time = time.time()

            self.rpt_tbl.set_tree(self.rpt_dict)

    def add_pick_cb(self):
        if len(self.last_rpt) > 0:
            self.add_reports(self.last_rpt)
            self.last_rpt = []

    def clear_pick_log_cb(self):
        self.rpt_dict = OrderedDict({})
        self.rpt_tbl.set_tree(self.rpt_dict)

    def set_drawtype(self, shapename):
        if shapename not in self.drawtypes:
            raise ValueError("shape must be one of %s not %s" % (
                str(self.drawtypes), shapename))

        self.pickshape = shapename
        self.w.xlbl_drawtype.set_text(self.pickshape)
        self.canvas.set_drawtype(self.pickshape, color='cyan',
                                     linestyle='dash')

    def edit_select_pick(self):
        if self.picktag is not None:
            obj = self.canvas.get_object_by_tag(self.picktag)
            if obj.kind != 'compound':
                return True
            # drill down to reference shape
            bbox = obj.objects[0]
            self.canvas.edit_select(bbox)
        else:
            self.canvas.clear_selected()
        self.canvas.update_canvas()

    def btn_down(self, canvas, event, data_x, data_y, viewer):

        if (self.picktag is not None) and canvas.has_tag(self.picktag):
            obj = self.canvas.get_object_by_tag(self.picktag)
            if obj.kind != 'compound':
                return False

            shape = obj.objects[0]
            shape.linestyle = 'dash'
            point = obj.objects[1]
            point.color = 'red'

            shape.move_to(data_x, data_y)
            self.canvas.update_canvas()

        else:
            # No object yet? Add a default one.
            self.set_drawtype('rectangle')
            rd_x, rd_y = self.dx // 2, self.dy // 2
            x1, y1 = data_x - rd_x, data_y - rd_y
            x2, y2 = data_x + rd_x, data_y + rd_y

            # TODO: makes sense to change this to 'box'
            Rect = self.canvas.get_draw_class('rectangle')
            tag = self.canvas.add(Rect(x1, y1, x2, y2,
                                       color=self.pickcolor))

            self.draw_cb(self.canvas, tag)

        return True

    def btn_drag(self, canvas, event, data_x, data_y, viewer):

        if (self.picktag is not None) and canvas.has_tag(self.picktag):
            obj = self.canvas.get_object_by_tag(self.picktag)
            if obj.kind != 'compound':
                return False

            shape = obj.objects[0]

            shape.move_to(data_x, data_y)
            self.canvas.update_canvas()
            return True

        return False

    def btn_up(self, canvas, event, data_x, data_y, viewer):

        if (self.picktag is not None) and canvas.has_tag(self.picktag):
            obj = self.canvas.get_object_by_tag(self.picktag)
            if obj.kind != 'compound':
                return False

            shape = obj.objects[0]

            shape.move_to(data_x, data_y)
            self.canvas.update_canvas()

            self.redo_manual()

        return True


    def set_mode_cb(self, mode, tf):
        if tf:
            self.canvas.set_draw_mode(mode)
            if mode == 'edit':
                self.edit_select_pick()
        return True

    def __str__(self):
        return 'pick'

#END
