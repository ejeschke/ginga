# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""Perform quick astronomical stellar analysis.

**Plugin Type: Local**

``Pick`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

The ``Pick`` plugin is used to perform quick astronomical data quality analysis
on stellar objects.  It locates stellar candidates within a drawn box
and picks the most likely candidate based on a set of search settings.
The Full Width Half Max (FWHM) is reported on the candidate object, as
well as its size based on the plate scale of the detector.  Rough
measurement of background, sky level and brightness is also done.

**Defining the pick area**

The default pick area is defined as a box of approximately 30x30
pixels that encloses the search area.

The move/draw/edit selector at the bottom of the plugin is used to
determine what operation is being done to the pick area:

.. figure:: figures/pick-move-draw-edit.png
   :width: 400px
   :align: center
   :alt: Move, Draw and Edit buttons

   "Move", "Draw", and "Edit" buttons.

* If "move" is selected, then you can move the existing pick area by
  dragging it or clicking where you want the center of it placed.
  If there is no existing area, a default one will be created.
* If "draw" is selected, then you can draw a shape with the cursor
  to enclose and define a new pick area.  The default shape is a
  box, but other shapes can be selected in the "Settings" tab.
* If "edit" is selected, then you can edit the pick area by dragging its
  control points, or moving it by dragging in the bounding box.

After the area is moved, drawn or edited, ``Pick`` will perform one of three
actions:

1. In "Quick Mode" ON, with "From Peak" OFF, it will simply attempt to
   perform a calculation based on the coordinate under the crosshair in
   the center of the pick area.
2. In "Quick Mode" ON, with "From Peak" ON, it will perform a quick
   detection of peaks in the pick area and perform a calculation on the
   first one found, using the peak's coordinates.
3. In "Quick Mode" OFF, it will search the area for all peaks and
   evaluate the peaks based on the criteria in the "Settings" tab of the UI
   (see "The Settings Tab" below) and try to locate the best candidate
   matching the settings.

**If a candidate is found**

The candidate will be marked with a point (usually an "X") in the
channel viewer canvas, centered on the object as determined by the
horizontal and vertical FWHM measurements.

The top set of tabs in the UI will be populated as follows:

.. figure:: figures/pick-cutout.png
   :width: 400px
   :align: center
   :alt: Image tab of Pick area

   "Image" tab of ``Pick`` area.

The "Image" tab will show the contents of the cutout area.
The widget in this tab is a Ginga widget and so can be zoomed and panned
with the usual keyboard and mouse bindings (e.g., scroll wheel).  It will
also be marked with a point centered on the object and additionally the
pan position will be set to the found center.

.. figure:: figures/pick-contour.png
   :width: 300px
   :align: center
   :alt: Contour tab of Pick area

   "Contour" tab of ``Pick`` area.

The "Contour" tab will show a contour plot.
This is a contour plot of the area immediately surrounding the
candidate, and not usually encompassing the entire region of the pick
area.  You can use the scroll wheel to zoom the plot and a click of the
scroll wheel (mouse button 2) to set the pan position in the plot.

.. figure:: figures/pick-fwhm.png
   :width: 400px
   :align: center
   :alt: FWHM tab of Pick area

   "FWHM" tab of ``Pick`` area.

The "FWHM" tab will show a FWHM plot.
The purple lines show measurements in the X direction and the green lines
show measurements in the Y direction.  The solid lines indicate actual
pixel values and the dotted lines indicate the fitted 1D function.
The shaded purple and green regions indicate the FWHM measurements for the
respective axes.

.. figure:: figures/pick-radial.png
   :width: 400px
   :align: center
   :alt: Radial tab of Pick area

   "Radial" tab of ``Pick`` area.

The "Radial" tab contains a radial profile plot.
Plotted points in purple are data values, and a line is fitted to the
data.

.. figure:: figures/pick-ee.png
   :width: 600px
   :align: center
   :alt: EE tab of Pick area

   "EE" tab of ``Pick`` area.

The "EE" tab contains a plot of fractional encircled and ensquared energies
(EE) in purple and green, respectively, for the chosen target. Simple
background subtraction is done in a way that is consistent with FWHM
calculations before EE values are measured. The sampling and total radii,
shown as black dashed lines, can be set in the "Settings" tab; when these are
changed, click "Redo Pick" to update the plot and measurements.
The measured EE values at the given sampling radius are also displayed in the
"Readout" tab. When reporting is requested, the EE values at the given sampling
radius and the radius itself will be recorded under "Report" table, along with
other information.

When "Show Candidates" is active, the candidates near the edges of the bounding
box will not have EE values (set to 0).

.. figure:: figures/pick-readout.png
   :width: 400px
   :align: center
   :alt: Readout tab of Pick area

   "Readout" tab of ``Pick`` area.

The "Readout" tab will be populated with a summary of the measurements.
There are two buttons and three check boxes in this tab:

* The "Default Region" button restores the pick region to the default
  shape and size.
* The "Pan to pick" button will pan the channel viewer to the
  located center.
* The "Quick Mode" check box toggles "Quick Mode" on and off.
  This affects the behavior of the pick region as described above.
* The "From Peak" check box changes the behavior of "Quick Mode" slightly
  as described above.
* If "Center on pick" is checked, the shape will be recentered on the
  located center, if found (i.e., the shape "tracks" the pick).

.. figure:: figures/pick-controls.png
   :width: 400px
   :align: center
   :alt: Controls tab of Pick area

   "Controls" tab of ``Pick`` area.

The "Controls" tab has a couple of buttons that will work off of the
measurements.

* The "Bg cut" button will set the low cut level of the channel viewer
  to the measured background level.  A delta to this value can be
  applied by setting a value in the "Delta bg" box (press "Enter" to
  change the setting).
* The "Sky cut" button will set the low cut level of the channel viewer
  to the measured sky level.  A delta to this value can be
  applied by setting a value in the "Delta sky" box (press "Enter" to
  change the setting).
* The "Bright cut" button will set the high cut level of the channel
  viewer to the measured sky+brightness levels. A delta to this value
  can be applied by setting a value in the "Delta bright" box
  (press "Enter" to change the setting).

.. figure:: figures/pick-report.png
   :width: 400px
   :align: center
   :alt: Report tab of Pick area

   "Report" tab of ``Pick`` area.

The "Report" tab is used to record information about the measurements in
tabular form.

By pressing the "Add Pick" button, the information about the most recent
candidate is added to the table.  If the "Record Picks automatically"
checkbox is checked, then any candidates are added to the table
automatically.

.. note:: If the "Show Candidates" checkbox in the "Settings" tab is
          checked, then *all* objects found in the region (according to
          the settings) will be added to the table instead of just the
          selected candidate.

You can clear the table at any time by pressing the "Clear Log" button.
The log can be saved to a table by putting a valid path and
filename in the "File:" box and pressing "Save table". File type is
automatically determined by the given extension (e.g., ".fits" is FITS and
".txt" is plain text).

**If no candidate is found**

If no candidate can be found (based on the settings), then the pick area
is marked with a red point centered on the pick area.

.. figure:: figures/pick-no-candidate.png
   :width: 800px
   :align: center
   :alt: Marker when no candidate found

   Marker when no candidate found.

The image cutout will be taken from this central area and so the "Image"
tab will still have content.  It will also be marked with a central red
"X".

The contour plot will still be produced from the cutout.

.. figure:: figures/pick-contour-no-candidate.png
   :width: 400px
   :align: center
   :alt: Contour when no candidate found.

   Contour when no candidate found.

All the other plots will be cleared.

**The Settings Tab**

.. figure:: figures/pick-settings.png
   :width: 400px
   :align: center
   :alt: Settings tab of Pick plugin

   "Settings" tab of ``Pick`` plugin.

The "Settings" tab controls aspects of the search within the pick area:

* The "Show Candidates" checkbox controls whether all detected sources
  are marked or not (as shown in the figure below).  Additionally, if
  checked, then all the found objects are added to the pick log table
  when using the "Report" controls.
* The "Draw type" parameter is used to choose the shape of the pick area
  to be drawn.
* The "Radius" parameter sets the radius to be used when finding and
  evaluating bright peaks in the image.
* The "Threshold" parameter is used to set a threshold for peak finding;
  if set to "None", then a reasonable default value will be chosen.
* The "Min FWHM" and "Max FWHM" parameters can be used to eliminate
  certain sized objects from being candidates.
* The "Ellipticity" parameter is used to eliminate candidates based on
  their asymmetry in shape.
* The "Edge" parameter is used to eliminate candidates based on how
  close to the edge of the cutout they are.  *NOTE: currently this
  works reliably only for non-rotated rectangular shapes.*
* The "Max side" parameter is used to limit the size of the bounding box
  that can be used in the pick shape.  Larger sizes take longer to
  evaluate.
* The "Coordinate Base" parameter is an offset to apply to located
  sources.  Set to "1" if you want sources pixel locations reported
  in a FITS-compliant manner and "0" if you prefer 0-based indexing.
* The "Calc center" parameter is used to determine whether the center
  is calculated from FWHM fitting ("fwhm") or centroiding ("centroid").
* The "FWHM fitting" parameter is used to determine which function is
  is used for FWHM fitting ("gaussian" or "moffat"). The option to use
  "lorentz" is also available if "calc_fwhm_lib" is set to "astropy"
  in ``~/.ginga/plugin_Pick.cfg``.
* The "Contour Interpolation" parameter is used to set the interpolation
  method used in rendering the background image in the "Contour" plot.
* The "EE total radius" defines the radius (for encircled energy) and box
  half-width (for ensquared energy) in pixels where EE fraction is expected to
  be 1 (i.e., all the flux for a point-spread function is contained within).
* The "EE sampling radius" is the radius in pixel used to sample the measured
  EE curves for reporting.

The "Redo Pick" button will redo the search operation.  It is convenient
if you have changed some parameters and want to see the effect based on the
current pick area without disturbing it.

.. figure:: figures/pick-candidates.png
   :width: 600px
   :align: center
   :alt: The channel viewer when "Show Candidates" is checked.

   The channel viewer when "Show Candidates" is checked.

**User Configuration**

"""
import threading
import sys
import traceback
import time
from collections import OrderedDict

import numpy as np

from ginga.gw import Widgets, Viewers
from ginga.misc import Bunch
from ginga.util import wcs, contour
from ginga import GingaPlugin, cmap, trcalc

try:
    from ginga.gw import Plot
    from ginga.util import plots
    have_mpl = True
except ImportError:
    have_mpl = False

region_default_width = 30
region_default_height = 30

__all__ = ['Pick']


class Pick(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Pick, self).__init__(fv, fitsimage)

        self.layertag = 'pick-canvas'
        self.pickimage = None
        self.pickcenter = None
        self.pick_qs = None
        self.pick_obj = None
        self._textlabel = 'Pick'

        self.contour_image = None
        self.contour_plot = None
        self.fwhm_plot = None
        self.radial_plot = None
        self.contour_interp_methods = trcalc.interpolation_methods

        # types of pick shapes that can be drawn
        self.drawtypes = ['box', 'squarebox', 'rectangle',
                          'circle', 'ellipse',
                          'freepolygon', 'polygon',
                          ]

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
        self._wd, self._ht = 400, 300
        self._split_sizes = [self._ht, self._ht]

        self.last_rpt = []
        self.rpt_dict = OrderedDict({})
        self.rpt_cnt = 0
        self.rpt_tbl = None
        self.rpt_mod_time = 0.0
        self.rpt_wrt_time = 0.0
        self.rpt_wrt_interval = self.settings.get('report_write_interval',
                                                  30.0)

        if self.iqcalc_lib == 'astropy':
            self.logger.debug('Using iqcalc_astropy')
            from ginga.util import iqcalc_astropy as iqcalc
        else:  # Falls back to native
            self.logger.debug('Using native iqcalc')
            from ginga.util import iqcalc

        if not iqcalc.have_scipy:
            raise ImportError('Please install scipy to use this plugin')

        self.iqcalc = iqcalc.IQCalc(self.logger)
        self.copy_attrs = ['transforms', 'cutlevels']
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
        self.gui_up = False

    def sync_preferences(self):
        # Load various preferences
        self.pickcolor = self.settings.get('color_pick', 'green')
        self.pickshape = self.settings.get('shape_pick', 'box')
        if self.pickshape not in self.drawtypes:
            self.pickshape = 'box'
        self.candidate_color = self.settings.get('color_candidate', 'orange')
        self.quick_mode = self.settings.get('quick_mode', False)
        self.from_peak = self.settings.get('quick_from_peak', True)

        # Peak finding parameters and selection criteria
        self.max_side = self.settings.get('max_side', 1024)
        self.radius = self.settings.get('radius', 10)
        self.ee_total_radius = self.settings.get('ee_total_radius', 10.0)
        self.ee_sampling_radius = self.settings.get('ee_sampling_radius', 2.5)
        self.threshold = self.settings.get('threshold', None)
        self.min_fwhm = self.settings.get('min_fwhm', 1.5)
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
        self.iqcalc_lib = self.settings.get('calc_fwhm_lib', 'native')
        if self.iqcalc_lib == 'astropy':
            self.fwhm_algs.append('lorentz')
        self.fwhm_alg = self.settings.get('calc_fwhm_alg', 'gaussian')
        self.center_on_pick = self.settings.get('center_on_pick', False)

        # For controls
        self.delta_bg = self.settings.get('delta_bg', 0.0)
        self.delta_sky = self.settings.get('delta_sky', 0.0)
        self.delta_bright = self.settings.get('delta_bright', 0.0)

        # Formatting for reports
        self.do_record = self.settings.get('record_picks', False)
        columns = [("RA", 'ra_txt'), ("DEC", 'dec_txt'), ("Equinox", 'equinox'),
                   ("X", 'x'), ("Y", 'y'), ("FWHM", 'fwhm'),
                   ("FWHM_X", 'fwhm_x'), ("FWHM_Y", 'fwhm_y'),
                   ("EE_circ", 'encircled_energy'), ("EE_sq", 'ensquared_energy'),
                   ("EE_r", 'ee_sampling_radius'),
                   ("Star Size", 'starsize'),
                   ("Ellip", 'ellipse'), ("Background", 'background'),
                   ("Sky Level", 'skylevel'), ("Brightness", 'brightness'),
                   ("Time Local", 'time_local'), ("Time UT", 'time_ut'),
                   ("RA deg", 'ra_deg'), ("DEC deg", 'dec_deg'),
                   ]
        self.rpt_columns = self.settings.get('report_columns', columns)

        # For contour plot
        self.num_contours = self.settings.get('num_contours', 8)
        self.contour_size_max = self.settings.get('contour_size_limit', 100)
        self.contour_size_min = self.settings.get('contour_size_min', 30)
        self.contour_interpolation = self.settings.get('contour_interpolation',
                                                       'nearest')

    def build_gui(self, container):
        vtop = Widgets.VBox()
        vtop.set_border_width(4)

        box, sw, orientation = Widgets.get_oriented_box(container,
                                                        orientation=self.settings.get('orientation', None))
        box.set_border_width(4)
        box.set_spacing(2)

        paned = Widgets.Splitter(orientation=orientation)
        self.w.splitter = paned

        nb = Widgets.TabWidget(tabpos='bottom')
        self.w.nb1 = nb
        paned.add_widget(Widgets.hadjust(nb, orientation))

        cm, im = self.fv.cm, self.fv.im

        # Set up "Image" tab viewer
        di = Viewers.CanvasView(logger=self.logger)
        width, height = self._wd, self._ht
        di.set_desired_size(width, height)
        di.enable_autozoom('override')
        di.enable_autocuts('off')
        di.set_zoom_algorithm('rate')
        di.set_zoomrate(1.6)
        settings = di.get_settings()
        settings.get_setting('zoomlevel').add_callback('set', self.zoomset, di)

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
        di.show_mode_indicator(True)
        self.pickimage = di

        bd = di.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)
        bd.enable_cmap(True)

        di.set_desired_size(width, height)

        p_canvas = di.get_canvas()
        tag = p_canvas.add(self.dc.Point(width / 2, height / 2, 5,
                                         linewidth=1, color='red'))
        self.pickcenter = p_canvas.get_object_by_tag(tag)

        iw = Viewers.GingaViewerWidget(viewer=di)
        iw.resize(width, height)
        nb.add_widget(iw, title="Image")

        # Set up "Contour" tab viewer
        if contour.have_skimage:
            # Contour plot, Ginga-style
            ci = Viewers.CanvasView(logger=self.logger)
            width, height = 400, 300
            ci.set_desired_size(width, height)
            ci.enable_autozoom('override')
            ci.enable_autocuts('override')
            ci.set_zoom_algorithm('rate')
            ci.set_zoomrate(1.6)
            ci.set_autocut_params('histogram')

            t_ = ci.get_settings()
            if self.contour_interpolation not in self.contour_interp_methods:
                self.contour_interpolation = 'basic'
            t_.set(interpolation=self.contour_interpolation)

            ci.set_bg(0.4, 0.4, 0.4)
            # for debugging
            ci.set_name('contour_image')

            self.contour_canvas = self.dc.DrawingCanvas()
            ci.get_canvas().add(self.contour_canvas)
            if cmap.has_cmap('RdYlGn_r'):
                ci.set_color_map('RdYlGn_r')
            else:
                ci.set_color_map('pastel')
            ci.show_color_bar(True)
            self.contour_image = ci

            bd = ci.get_bindings()
            bd.enable_pan(True)
            bd.enable_zoom(True)
            bd.enable_cuts(True)
            bd.enable_cmap(True)

            ci.set_desired_size(width, height)
            ci.show_mode_indicator(True)

            ciw = Viewers.GingaViewerWidget(viewer=ci)
            ciw.resize(width, height)

            nb.add_widget(ciw, title="Contour")

        if have_mpl:
            if not contour.have_skimage:
                # Contour plot
                self.contour_plot = plots.ContourPlot(
                    logger=self.logger, width=width, height=height)
                self.contour_plot.add_axis(facecolor='black')
                pw = Plot.PlotWidget(self.contour_plot)
                pw.resize(width, height)
                self.contour_plot.enable(pan=True, zoom=True)

                self.contour_interp_methods = ('bilinear', 'nearest', 'bicubic')
                if self.contour_interpolation not in self.contour_interp_methods:
                    self.contour_interpolation = 'nearest'
                self.contour_plot.interpolation = self.contour_interpolation

                nb.add_widget(pw, title="Contour")

            # FWHM gaussians plot
            self.fwhm_plot = plots.FWHMPlot(logger=self.logger,
                                            width=width, height=height)
            self.fwhm_plot.add_axis(facecolor='white')
            pw = Plot.PlotWidget(self.fwhm_plot)
            pw.resize(width, height)
            nb.add_widget(pw, title="FWHM")

            # Radial profile plot
            self.radial_plot = plots.RadialPlot(logger=self.logger,
                                                width=width, height=height)
            self.radial_plot.add_axis(facecolor='white')
            pw = Plot.PlotWidget(self.radial_plot)
            pw.resize(width, height)
            nb.add_widget(pw, title="Radial")

            # EE profile plot
            self.ee_plot = plots.EEPlot(logger=self.logger,
                                        width=width, height=height)
            self.ee_plot.add_axis(facecolor='white')
            pw = Plot.PlotWidget(self.ee_plot)
            pw.resize(width, height)
            nb.add_widget(pw, title="EE")

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
                    ('EE (circ):', 'label', 'Encircled energy', 'llabel',
                     'EE (sq):', 'label', 'Ensquared energy', 'llabel'),
                    ('Sample Area:', 'label', 'Sample Area', 'llabel',
                     'Default Region', 'button', 'Pan to pick', 'button'),
                    ('Quick Mode', 'checkbutton', 'From Peak', 'checkbutton',
                     'Center on pick', 'checkbutton'),
                    )

        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.zoom.set_text(self.fv.scale2text(di.get_scale()))
        self.wdetail = b
        b.encircled_energy.set_tooltip("Encircled energy")
        b.ensquared_energy.set_tooltip("Ensquared energy")
        b.default_region.add_callback('activated',
                                      lambda w: self.reset_region())
        b.default_region.set_tooltip("Reset region size to default")
        b.pan_to_pick.add_callback('activated',
                                   lambda w: self.pan_to_pick_cb())
        b.pan_to_pick.set_tooltip("Pan image to pick center")
        b.quick_mode.set_tooltip("Turn Quick Mode on or off.\n"
                                 "ON: Pick object manually ('From Peak' off)\n"
                                 "or simply evaluate first peak found\n"
                                 "in pick region ('From Peak' on).\n"
                                 "OFF: Compare all peaks against selection\n"
                                 "criteria (Settings) to avoid objects\n"
                                 "and/or find 'best' peak.")
        b.quick_mode.add_callback('activated', self.quick_mode_cb)
        b.quick_mode.set_state(self.quick_mode)
        b.from_peak.set_tooltip("In quick mode, calculate from any peak\n"
                                "found (on), or simply calculate from the\n"
                                "center of pick shape (off).")
        b.from_peak.add_callback('activated', self.from_peak_cb)
        b.from_peak.set_state(self.from_peak)
        ## b.drag_only.set_tooltip("In quick mode, require cursor press or follow cursor")
        ## b.drag_only.add_callback('activated', self.drag_only_cb)
        ## b.drag_only.set_state(self.drag_only)
        b.center_on_pick.add_callback('activated', self.center_on_pick_cb)
        b.center_on_pick.set_state(self.center_on_pick)
        b.center_on_pick.set_tooltip("When peak is found, center shape\n"
                                     "on peak.")

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
                    ('EE total radius:', 'label', 'xlbl_ee_total_radius', 'label',
                     'EE total radius', 'spinfloat'),
                    ('EE sampling radius:', 'label', 'xlbl_ee_radius', 'label',
                     'EE sampling radius', 'spinfloat')
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
        b.ee_total_radius.set_tooltip("Radius where EE fraction is 1")
        b.ee_sampling_radius.set_tooltip("Radius for EE sampling")

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

        # EE total radius control
        b.ee_total_radius.set_limits(0.1, 200.0, incr_value=0.1)
        b.ee_total_radius.set_value(self.ee_total_radius)

        def chg_ee_total_radius(w, val):
            self.ee_total_radius = float(val)
            self.w.xlbl_ee_total_radius.set_text(str(self.ee_total_radius))
            return True
        b.xlbl_ee_total_radius.set_text(str(self.ee_total_radius))
        b.ee_total_radius.add_callback('value-changed', chg_ee_total_radius)

        # EE sampling radius control
        b.ee_sampling_radius.set_limits(0.1, 200.0, incr_value=0.1)
        b.ee_sampling_radius.set_value(self.ee_sampling_radius)

        def chg_ee_sampling_radius(w, val):
            self.ee_sampling_radius = float(val)
            self.w.xlbl_ee_radius.set_text(str(self.ee_sampling_radius))
            return True
        b.xlbl_ee_radius.set_text(str(self.ee_sampling_radius))
        b.ee_sampling_radius.add_callback('value-changed', chg_ee_sampling_radius)

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
            if self.contour_image is not None:
                t_ = self.contour_image.get_settings()
                t_.set(interpolation=self.contour_interpolation)
            elif self.contour_plot is not None:
                self.contour_plot.interpolation = self.contour_interpolation
            return True

        for name in self.contour_interp_methods:
            combobox.append_text(name)
        index = self.contour_interp_methods.index(self.contour_interpolation)
        combobox.set_index(index)
        self.w.xlbl_cinterp.set_text(self.contour_interpolation)
        if self.contour_plot is not None:
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
        paned.set_sizes(self._split_sizes)

        vtop.add_widget(paned, stretch=5)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        btn1 = Widgets.RadioButton("Move")
        btn1.set_state(mode == 'move')
        btn1.add_callback(
            'activated', lambda w, val: self.set_mode_cb('move', val))
        btn1.set_tooltip("Choose this to position pick")
        self.w.btn_move = btn1
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Draw", group=btn1)
        btn2.set_state(mode == 'draw')
        btn2.add_callback(
            'activated', lambda w, val: self.set_mode_cb('draw', val))
        btn2.set_tooltip("Choose this to draw a replacement pick")
        self.w.btn_draw = btn2
        hbox.add_widget(btn2)

        btn3 = Widgets.RadioButton("Edit", group=btn1)
        btn3.set_state(mode == 'edit')
        btn3.add_callback(
            'activated', lambda w, val: self.set_mode_cb('edit', val))
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
        self.gui_up = True

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
            radius = max(wd, ht) // 2

            if self.pick_qs is not None:
                x, y = self.pick_qs.x, self.pick_qs.y
            data, x1, y1, x2, y2 = image.cutout_radius(x, y, radius)
            x, y = x - x1, y - y1
            ht, wd = data.shape

        else:
            data = self.pick_data
            x, y = self.pickcenter.x, self.pickcenter.y

        try:
            if self.contour_image is not None:
                cv = self.contour_image
                with cv.suppress_redraw:
                    cv.set_data(data)
                    # copy orientation of main image, so that contour will
                    # make sense.  Don't do rotation, for now.
                    flips = self.fitsimage.get_transforms()
                    cv.transform(*flips)
                    #rot_deg = self.fitsimage.get_rotation()
                    #cv.rotate(rot_deg)

                    cv.panset_xy(x, y)

                    canvas = self.contour_canvas
                    try:
                        canvas.delete_object_by_tag('_$cntr', redraw=False)
                    except KeyError:
                        pass

                    # calculate contour polygons
                    contour_grps = contour.calc_contours(data, self.num_contours)

                    # get compound polygons object
                    c_obj = contour.create_contours_obj(canvas, contour_grps,
                                                        colors=['black'],
                                                        linewidth=2)
                    canvas.add(c_obj, tag='_$cntr')

            elif self.contour_plot is not None:
                self.contour_plot.plot_contours_data(
                    x, y, data, num_contours=self.num_contours)

        except Exception as e:
            self.logger.error("Error making contour plot: %s" % (
                str(e)))

    def clear_contours(self):
        if self.contour_image is not None:
            self.contour_canvas.delete_all_objects()
        elif self.contour_plot is not None:
            self.contour_plot.clear()

    def plot_fwhm(self, qs, image):
        # Make a FWHM plot
        x, y = qs.x - self.pick_x1, qs.y - self.pick_y1
        radius = qs.fwhm_radius

        try:
            self.fwhm_plot.plot_fwhm_data(x, y, radius, self.pick_data,
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

    def plot_ee(self, qs):
        # Make a EE plot
        try:
            self.ee_plot.plot_ee(
                encircled_energy_function=qs.encircled_energy_fn,
                ensquared_energy_function=qs.ensquared_energy_fn,
                sampling_radius=self.ee_sampling_radius,
                total_radius=self.ee_total_radius)
        except Exception as e:
            self.logger.error("Error making EE plot: %s" % (str(e)))

    def clear_ee(self):
        self.ee_plot.clear()

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        # turn off any mode user may be in
        self.modes_off()

        self.canvas.ui_set_active(True, viewer=self.fitsimage)
        self.fv.show_status("Draw a shape with the right mouse button")

    def stop(self):
        self.gui_up = False
        self._split_sizes = self.w.splitter.get_sizes()
        # Delete previous peak marks
        objs = self.canvas.get_objects_by_tag_pfx('peak')
        self.canvas.delete_objects(objs)

        # deactivate the canvas
        self.canvas.ui_set_active(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        self.fv.show_status("")

    def redo_manual(self):
        if self.quick_mode:
            self.redo_quick()
            self.calc_quick()
        else:
            serialnum = self.bump_serial()
            self.ev_intr.set()
            self._redo(serialnum)

    def redo(self):
        serialnum = self.bump_serial()
        self._redo(serialnum)

    def _redo(self, serialnum):
        if self.pick_obj is None:
            return

        pickobj = self.pick_obj
        if pickobj.kind != 'compound':
            return True
        shape = pickobj.objects[0]
        point = pickobj.objects[1]
        text = pickobj.objects[2]

        # reposition other elements to match
        ctr_x, ctr_y = shape.get_center_pt()
        point.x, point.y = ctr_x, ctr_y
        x1, y1, x2, y2 = shape.get_llur()
        text.x, text.y = x1, y2

        try:
            image = self.fitsimage.get_vip()

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
                objlist = self.iqcalc.evaluate_peaks(
                    peaks, data,
                    fwhm_radius=self.radius,
                    cb_fn=cb_fn,
                    ev_intr=self.ev_intr,
                    fwhm_method=self.fwhm_alg,
                    ee_total_radius=self.ee_total_radius)

                num_candidates = len(objlist)
                if num_candidates == 0:
                    raise Exception(
                        "Error evaluating bright peaks: no candidates found")

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
                    if qs.objx is not None:
                        qs.objx += x1
                        qs.objy += y1
                    if qs.oid_x is not None:
                        qs.oid_x += x1
                        qs.oid_y += y1

                # pick main result
                qs = results[0]

            except Exception as e:
                msg = str(e)
                self.update_status(msg)

            self.fv.gui_do(self.update_pick, serialnum, results, qs,
                           x1, y1, wd, ht, data, pickobj, msg)

    def _make_report(self, vip_img, qs):
        d = Bunch.Bunch()
        try:
            x, y = qs.objx, qs.objy
            if (qs.oid_x is not None) and (self.center_alg == 'centroid'):
                # user wants RA/DEC calculated by centroid instead of fwhm
                x, y = qs.oid_x, qs.oid_y

            image, pt2 = vip_img.get_image_at_pt((x, y))
            equinox = float(image.get_keyword('EQUINOX', 2000.0))
            try:
                ra_deg, dec_deg = image.pixtoradec(x, y, coords='data')
                ra_txt, dec_txt = wcs.deg2fmt(ra_deg, dec_deg, 'str')

            except Exception as e:
                self.logger.warning(
                    "Couldn't calculate sky coordinates: %s" % (str(e)))
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
                self.logger.warning(
                    "Couldn't calculate star size: %s" % (str(e)))
                starsize = 0.0

            rpt_x = x + self.pixel_coords_offset
            rpt_y = y + self.pixel_coords_offset

            # EE at sampling radius
            try:
                ee_circ = qs.encircled_energy_fn(self.ee_sampling_radius)
                ee_sq = qs.ensquared_energy_fn(self.ee_sampling_radius)
            except Exception as e:
                self.logger.warning("Couldn't calculate EE at %.2f: %s" % (self.ee_sampling_radius, str(e)))
                ee_circ = 0
                ee_sq = 0

            # make a report in the form of a dictionary
            d.setvals(x=rpt_x, y=rpt_y,
                      ra_deg=ra_deg, dec_deg=dec_deg,
                      ra_txt=ra_txt, dec_txt=dec_txt,
                      equinox=equinox,
                      fwhm=qs.fwhm,
                      fwhm_x=qs.fwhm_x, fwhm_y=qs.fwhm_y,
                      ellipse=qs.elipse, background=qs.background,
                      skylevel=qs.skylevel, brightness=qs.brightness,
                      encircled_energy=ee_circ, ensquared_energy=ee_sq,
                      ee_sampling_radius=self.ee_sampling_radius,
                      starsize=starsize,
                      time_local=time.strftime("%Y-%m-%d %H:%M:%S",
                                               time.localtime()),
                      time_ut=time.strftime("%Y-%m-%d %H:%M:%S",
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

            vip_img = self.fitsimage.get_vip()
            shape_obj = pickobj.objects[0]
            point = pickobj.objects[1]
            text = pickobj.objects[2]
            text.text = self._textlabel
            _x1, _y1, x2, y2 = shape_obj.get_llur()
            text.x, text.y = x1, y2

            if msg is not None:
                raise Exception(msg)

            # Mark new peaks, if desired
            if self.show_candidates:
                reports = [self._make_report(vip_img, x) for x in objlist]
                for obj in objlist:
                    self.canvas.add(self.dc.Point(
                        obj.objx, obj.objy, 5, linewidth=1,
                        color=self.candidate_color), tagpfx='peak')
            else:
                reports = [self._make_report(vip_img, qs)]

            # Calculate X/Y of center of star
            obj_x = qs.objx
            obj_y = qs.objy
            fwhm = qs.fwhm
            fwhm_x, fwhm_y = qs.fwhm_x, qs.fwhm_y
            point.x, point.y = obj_x, obj_y
            text.color = 'cyan'

            if self.center_on_pick:
                shape_obj.move_to_pt((obj_x, obj_y))
                # reposition label above moved shape
                _x1, _y1, x2, y2 = shape_obj.get_llur()
                text.x, text.y = _x1, y2

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
            self.wdetail.object_x.set_text('%.3f' % d.x)
            self.wdetail.object_y.set_text('%.3f' % d.y)
            self.wdetail.sky_level.set_text('%.3f' % qs.skylevel)
            self.wdetail.background.set_text('%.3f' % qs.background)
            self.wdetail.brightness.set_text('%.3f' % qs.brightness)
            self.wdetail.encircled_energy.set_text('%.3f' % d.encircled_energy)
            self.wdetail.ensquared_energy.set_text('%.3f' % d.ensquared_energy)
            self.wdetail.ra.set_text(d.ra_txt)
            self.wdetail.dec.set_text(d.dec_txt)
            self.wdetail.equinox.set_text(str(d.equinox))
            self.wdetail.star_size.set_text('%.3f' % d.starsize)

            self.w.btn_bg_cut.set_enabled(True)
            self.w.btn_sky_cut.set_enabled(True)
            self.w.btn_bright_cut.set_enabled(True)

            # Mark center of object on pick image
            i1 = obj_x - x1
            j1 = obj_y - y1
            self.pickcenter.x = i1
            self.pickcenter.y = j1
            self.pickcenter.color = 'cyan'
            self.pick_qs = qs
            self.pickimage.panset_xy(i1, j1)

            # Mark object center on image
            point.color = 'cyan'
            shape_obj.linestyle = 'solid'
            shape_obj.color = self.pickcolor

            self.update_status("Done")
            self.plot_panx = float(i1) / wd
            self.plot_pany = float(j1) / ht
            if self.have_mpl:
                self.plot_contours(vip_img)
                self.plot_fwhm(qs, vip_img)
                self.plot_radial(qs, vip_img)
                self.plot_ee(qs)

        except Exception as e:
            errmsg = "Error calculating quality metrics: %s" % (
                str(e))
            self.logger.error(errmsg)
            self.fv.show_error(errmsg, raisetab=False)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
            except Exception as e:
                tb_str = "Traceback information unavailable."
            self.logger.error(tb_str)
            #self.update_status("Error")
            for key in ('sky_level', 'background', 'brightness',
                        'star_size', 'fwhm_x', 'fwhm_y',
                        'ra', 'dec', 'object_x', 'object_y',
                        'encircled_energy', 'ensquared_energy'):
                self.wdetail[key].set_text('')
            self.wdetail.fwhm.set_text('Failed')
            self.w.btn_bg_cut.set_enabled(False)
            self.w.btn_sky_cut.set_enabled(False)
            self.w.btn_bright_cut.set_enabled(False)
            self.pick_qs = None
            text.color = 'red'
            shape_obj.linestyle = 'dash'

            self.pickimage.center_image()
            self.plot_panx = self.plot_pany = 0.5
            if self.have_mpl:
                self.plot_contours(vip_img)
                # TODO: could calc background based on numpy calc
                self.clear_fwhm()
                self.clear_radial()
                self.clear_ee()

        self.w.btn_intr_eval.set_enabled(False)
        self.pickimage.redraw(whence=3)
        self.canvas.redraw(whence=3)

        self.fv.show_status("Click left mouse button to reposition pick")
        return True

    def eval_intr(self):
        self.ev_intr.set()

    def redo_quick(self):
        vip_img = self.fitsimage.get_vip()

        obj = self.pick_obj
        if obj is None:
            return
        shape = obj.objects[0]

        x1, y1, x2, y2, data = self.cutdetail(vip_img, shape)
        self.pick_x1, self.pick_y1 = x1, y1
        self.pick_data = data

    def calc_quick(self):
        if self.pick_data is None:
            return

        # examine cut area
        data, x1, y1 = self.pick_data, self.pick_x1, self.pick_y1
        ht, wd = data.shape[:2]
        xc, yc = wd // 2, ht // 2
        radius = min(xc, yc)
        peaks = [(xc, yc)]

        with_peak = self.w.from_peak.get_state()
        if with_peak:
            # find the peak in the area, if possible, and calc from that
            try:
                peaks = self.iqcalc.find_bright_peaks(data,
                                                      threshold=self.threshold,
                                                      radius=radius)
            except Exception as e:
                self.logger.debug("no peaks found in data--using center")

            if len(peaks) > 0:
                xc, yc = peaks[0]

        self.pickcenter.x = xc
        self.pickcenter.y = yc
        self.pickcenter.color = 'red'
        msg = qs = None

        try:
            radius = int(round(radius))
            objlist = self.iqcalc.evaluate_peaks(peaks, data,
                                                 fwhm_radius=radius,
                                                 fwhm_method=self.fwhm_alg)

            num_candidates = len(objlist)
            if num_candidates == 0:
                raise Exception("Error calculating image quality")

            # Add back in offsets into image to get correct values with
            # respect to the entire image
            qs = objlist[0]
            qs.x += x1
            qs.y += y1
            if qs.objx is not None:
                qs.objx += x1
                qs.objy += y1
            if qs.oid_x is not None:
                qs.oid_x += x1
                qs.oid_y += y1

        except Exception as e:
            msg = str(e)
            self.update_status(msg)

        self.fv.gui_do(self.update_pick, 0, objlist, qs,
                       x1, y1, wd, ht, data, self.pick_obj, msg)

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        canvas.delete_object_by_tag(tag)

        if obj.kind not in self.drawtypes:
            return True

        self.create_pick_box(obj)

        self.redo_manual()

    def edit_cb(self, canvas, obj):
        if obj.kind not in self.drawtypes:
            return True

        if self.pick_obj is not None and self.pick_obj.has_object(obj):
            self.redo_manual()

    def reset_region(self):
        self.dx = region_default_width
        self.dy = region_default_height
        self.set_drawtype('box')

        obj = self.pick_obj
        if obj.kind != 'compound':
            return
        shape = obj.objects[0]

        # determine center of shape
        data_x, data_y = shape.get_center_pt()
        rd_x, rd_y = self.dx // 2, self.dy // 2
        x1, y1 = data_x - rd_x, data_y - rd_y
        x2, y2 = data_x + rd_x, data_y + rd_y

        # replace shape
        Box = self.dc.Box
        tag = self.canvas.add(Box(data_x, data_y, self.dx // 2, self.dy // 2,
                                  color=self.pickcolor))

        self.draw_cb(self.canvas, tag)

    def create_pick_box(self, obj):
        pick_obj = self.pick_obj
        if pick_obj is not None and self.canvas.has_object(pick_obj):
            self.canvas.delete_object(pick_obj)

        # determine center of object
        x1, y1, x2, y2 = obj.get_llur()
        x, y = obj.get_center_pt()

        obj.color = self.pickcolor
        args = [obj,
                self.dc.Point(x, y, 10, color='red'),
                self.dc.Text(x1, y2, '{0}: calc'.format(self._textlabel),
                             color=self.pickcolor)
                ]

        self.pick_obj = self.dc.CompoundObject(*args)
        self.canvas.add(self.pick_obj)

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

    def detailxy(self, canvas, event, data_x, data_y):
        """Motion event in the pick fits window.  Show the pointing
        information under the cursor.
        """
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
        mdata = np.ma.array(data, mask=np.logical_not(mask))

        return (x1, y1, x2, y2, mdata)

    def pan_plot(self, xdelta, ydelta):
        x1, x2 = self.w.ax.get_xlim()
        y1, y2 = self.w.ax.get_ylim()

        self.w.ax.set_xlim(x1 + xdelta, x2 + xdelta)
        self.w.ax.set_ylim(y1 + ydelta, y2 + ydelta)
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
        obj = self.pick_obj
        if obj is not None and self.canvas.has_object(obj):
            if obj.kind != 'compound':
                return True
            # drill down to reference shape
            bbox = obj.objects[0]
            self.canvas.edit_select(bbox)
            self.canvas.update_canvas()
            return

        self.canvas.clear_selected()
        self.canvas.update_canvas()

    def btn_down(self, canvas, event, data_x, data_y, viewer):

        if self.pick_obj is not None:
            if not canvas.has_object(self.pick_obj):
                self.canvas.add(self.pick_obj)

            obj = self.pick_obj
            shape = obj.objects[0]
            shape.color = 'cyan'
            shape.linestyle = 'dash'
            point = obj.objects[1]
            point.color = 'red'

            shape.move_to(data_x, data_y)
            self.canvas.update_canvas()

            if self.quick_mode:
                self.redo_quick()

        else:
            # No object yet? Add a default one.
            self.set_drawtype('box')
            rd_x, rd_y = self.dx // 2, self.dy // 2
            x1, y1 = data_x - rd_x, data_y - rd_y
            x2, y2 = data_x + rd_x, data_y + rd_y

            Box = self.canvas.get_draw_class('box')
            tag = self.canvas.add(Box(data_x, data_y, rd_x, rd_y,
                                      color=self.pickcolor))

            self.draw_cb(self.canvas, tag)

        return True

    def btn_drag(self, canvas, event, data_x, data_y, viewer):

        if self.pick_obj is not None:
            obj = self.pick_obj
            if obj.kind != 'compound':
                return False

            shape = obj.objects[0]
            shape.move_to(data_x, data_y)
            self.canvas.update_canvas()

            if self.quick_mode:
                self.redo_quick()
            return True

        return False

    def btn_up(self, canvas, event, data_x, data_y, viewer):

        if self.pick_obj is not None:
            obj = self.pick_obj
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

    def quick_mode_cb(self, w, tf):
        self.quick_mode = tf
        return True

    def from_peak_cb(self, w, tf):
        self.from_peak = tf
        return True

    def center_on_pick_cb(self, w, tf):
        self.center_on_pick = tf
        return True

    def drag_only_cb(self, w, tf):
        self.drag_only = tf
        return True

    def __str__(self):
        return 'pick'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Pick', package='ginga')

# END
