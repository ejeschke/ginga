#
# Pick.py -- Pick plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga import iqcalc
from ginga.misc.plugins import PickBase

try:
    import matplotlib
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    have_mpl = True
except ImportError:
    have_mpl = False

from ginga.qtw import ImageViewCanvasQt


class Pick(PickBase.PickBase):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Pick, self).__init__(fv, fitsimage)

        self.have_mpl = have_mpl


    def build_gui(self, container):
        assert iqcalc.have_scipy == True, \
               Exception("Please install python-scipy to use this plugin")

        self.pickcenter = None

        # Splitter is just to provide a way to size the graph
        # to a reasonable size
        vpaned = QtGui.QSplitter()
        vpaned.setOrientation(QtCore.Qt.Vertical)
        
        nb = QtHelp.TabWidget()
        nb.setTabPosition(QtGui.QTabWidget.East)
        nb.setUsesScrollButtons(True)
        self.w.nb1 = nb
        vpaned.addWidget(nb)
        
        cm, im = self.fv.cm, self.fv.im

        di = ImageViewCanvasQt.ImageViewCanvas(logger=self.logger)
        di.set_desired_size(200, 200)
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
        self.pickimage = di

        bd = di.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)

        iw = di.get_widget()
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                               QtGui.QSizePolicy.MinimumExpanding)
        iw.setSizePolicy(sp)
        width, height = 200, 200
        iw.resize(width, height)
        nb.addTab(iw, 'Image')

        if have_mpl:
            self.w.fig = matplotlib.figure.Figure()
            self.w.ax = self.w.fig.add_subplot(111, axisbg='black')
            self.w.ax.set_aspect('equal', adjustable='box')
            self.w.ax.set_title('Contours')
            #self.w.ax.grid(True)
            canvas = MyFigureCanvas(self.w.fig)
            canvas.setDelegate(self)
            #canvas.resize(width, height)
            self.w.canvas = canvas
            nb.addTab(canvas, u"Contour")

            self.w.fig2 = matplotlib.figure.Figure()
            self.w.ax2 = self.w.fig2.add_subplot(111, axisbg='white')
            #self.w.ax2.set_aspect('equal', adjustable='box')
            self.w.ax2.set_ylabel('brightness')
            self.w.ax2.set_xlabel('pixels')
            self.w.ax2.set_title('FWHM')
            self.w.ax.grid(True)
            canvas = FigureCanvas(self.w.fig2)
            self.w.canvas2 = canvas
            nb.addTab(canvas, u"FWHM")

        sw = QtGui.QScrollArea()

        twidget = QtHelp.VBox()
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                               QtGui.QSizePolicy.Fixed)
        twidget.setSizePolicy(sp)
        vbox = twidget.layout()
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(2)
        sw.setWidgetResizable(True)
        sw.setWidget(twidget)

        msgFont = self.fv.getFont('sansFont', 14)
        tw = QtGui.QLabel()
        tw.setFont(msgFont)
        tw.setWordWrap(True)
        self.tw = tw

        fr = QtHelp.Frame("Instructions")
        fr.layout().addWidget(tw, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)
        
        fr = QtHelp.Frame("Pick")

        nb = QtHelp.TabWidget()
        nb.setTabPosition(QtGui.QTabWidget.South)
        nb.setUsesScrollButtons(True)
        self.w.nb2 = nb

        fr.layout().addWidget(nb, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        vbox2 = QtHelp.VBox()
        captions = (('Zoom', 'label', 'Contour Zoom', 'label'),
                    ('Object_X', 'label', 'Object_Y', 'label'),
                    ('RA', 'label', 'DEC', 'label'),
                    ('Equinox', 'label', 'Background', 'label'),
                    ('Sky Level', 'label', 'Brightness', 'label'), 
                    ('FWHM X', 'label', 'FWHM Y', 'label'),
                    ('FWHM', 'label', 'Star Size', 'label'),
                    ('Sample Area', 'label', 'Default Region', 'button'),
                    )

        w, b = QtHelp.build_info(captions)
        self.w.update(b)
        b.zoom.setText(self.fv.scale2text(di.get_scale()))
        self.wdetail = b
        b.default_region.clicked.connect(self.reset_region)
        b.default_region.setToolTip("Reset region size to default")

        vbox2.addWidget(w, stretch=1)
        
        # Pick field evaluation status
        label = QtGui.QLabel()
        self.w.eval_status = label
        ## w.layout().addWidget(label, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox2.addWidget(label, stretch=0)

        # Pick field evaluation progress bar and stop button
        hbox = QtHelp.HBox()
        pgs = QtGui.QProgressBar()
        pgs.setRange(0, 100)
        pgs.setTextVisible(True)
        self.w.eval_pgs = pgs
        hbox.addWidget(pgs, stretch=0)
        btn = QtGui.QPushButton("Stop")
        btn.clicked.connect(lambda w: self.eval_intr())
        btn.setEnabled(False)
        self.w.btn_intr_eval = btn
        hbox.addWidget(btn, stretch=0)
        vbox2.addWidget(hbox, stretch=0)

        nb.addTab(vbox2, "Readout")

        # Build settings panel
        captions = (('Show Candidates', 'checkbutton'),
                    ('Radius', 'xlabel', '@Radius', 'spinfloat'),
                    ('Threshold', 'xlabel', '@Threshold', 'entry'),
                    ('Min FWHM', 'xlabel', '@Min FWHM', 'spinfloat'),
                    ('Max FWHM', 'xlabel', '@Max FWHM', 'spinfloat'),
                    ('Ellipticity', 'xlabel', '@Ellipticity', 'entry'),
                    ('Edge', 'xlabel', '@Edge', 'entry'),
                    ('Max side', 'xlabel', '@Max side', 'spinbutton'),
                    ('Redo Pick', 'button'),
            )

        w, b = QtHelp.build_info(captions)
        self.w.update(b)
        b.radius.setToolTip("Radius for peak detection")
        b.threshold.setToolTip("Threshold for peak detection (blank=default)")
        b.min_fwhm.setToolTip("Minimum FWHM for selection")
        b.max_fwhm.setToolTip("Maximum FWHM for selection")
        b.ellipticity.setToolTip("Minimum ellipticity for selection")
        b.edge.setToolTip("Minimum edge distance for selection")
        b.show_candidates.setToolTip("Show all peak candidates")
        b.show_candidates.setChecked(self.show_candidates)
        b.show_candidates.stateChanged.connect(self.show_candidates_cb)

        # radius control
        adj = b.radius
        adj.setRange(5.0, 200.0)
        adj.setSingleStep(1.0)
        adj.setValue(self.radius)
        def chg_radius(val):
            self.radius = val
            self.w.xlbl_radius.setText(str(self.radius))
            return True
        b.xlbl_radius.setText(str(self.radius))
        b.radius.valueChanged.connect(chg_radius)

        # threshold control
        def chg_threshold():
            threshold = None
            ths = str(self.w.threshold.text()).strip()
            if len(ths) > 0:
                threshold = float(ths)
            self.threshold = threshold
            self.w.xlbl_threshold.setText(str(self.threshold))
            return True
        b.xlbl_threshold.setText(str(self.threshold))
        b.threshold.returnPressed.connect(chg_threshold)

        # min fwhm
        adj = b.min_fwhm
        adj.setRange(0.1, 200.0)
        adj.setSingleStep(1.0)
        adj.setValue(self.min_fwhm)
        def chg_min(val):
            self.min_fwhm = val
            self.w.xlbl_min_fwhm.setText(str(self.min_fwhm))
            return True
        b.xlbl_min_fwhm.setText(str(self.min_fwhm))
        b.min_fwhm.valueChanged.connect(chg_min)

        # max fwhm
        adj = b.max_fwhm
        adj.setRange(0.1, 200.0)
        adj.setSingleStep(1.0)
        adj.setValue(self.max_fwhm)
        def chg_max(val):
            self.max_fwhm = val
            self.w.xlbl_max_fwhm.setText(str(self.max_fwhm))
            return True
        b.xlbl_max_fwhm.setText(str(self.max_fwhm))
        b.max_fwhm.valueChanged.connect(chg_max)

        # Ellipticity control
        def chg_ellipticity():
            minellipse = None
            val = str(self.w.ellipticity.text()).strip()
            if len(val) > 0:
                minellipse = float(val)
            self.min_ellipse = minellipse
            self.w.xlbl_ellipticity.setText(str(self.min_ellipse))
            return True
        b.xlbl_ellipticity.setText(str(self.min_ellipse))
        b.ellipticity.returnPressed.connect(chg_ellipticity)

        # Edge control
        def chg_edgew():
            edgew = None
            val = str(self.w.edge.text()).strip()
            if len(val) > 0:
                edgew = float(val)
            self.edgew = edgew
            self.w.xlbl_edge.setText(str(self.edgew))
            return True
        b.xlbl_edge.setText(str(self.edgew))
        b.edge.returnPressed.connect(chg_edgew)

        adj = b.max_side
        adj.setRange(5, 10000)
        adj.setSingleStep(10)
        adj.setValue(self.max_side)
        def chg_max_side(val):
            self.max_side = val
            self.w.xlbl_max_side.setText(str(self.max_side))
            return True
        b.xlbl_max_side.setText(str(self.max_side))
        b.max_side.valueChanged.connect(chg_max_side)

        b.redo_pick.clicked.connect(self.redo)

        nb.addTab(w, "Settings")

        captions = (
            ('Sky cut', 'button', 'Delta sky', 'entry'),
            ('Bright cut', 'button', 'Delta bright', 'entry'),
            )

        w, b = QtHelp.build_info(captions)
        self.w.update(b)

        b.sky_cut.setToolTip("Set image low cut to Sky Level")
        b.delta_sky.setToolTip("Delta to apply to low cut")
        b.bright_cut.setToolTip("Set image high cut to Sky Level+Brightness")
        b.delta_bright.setToolTip("Delta to apply to high cut")

        b.sky_cut.setEnabled(False)
        self.w.btn_sky_cut = b.sky_cut
        self.w.btn_sky_cut.clicked.connect(self.sky_cut)
        self.w.sky_cut_delta = b.delta_sky
        b.delta_sky.setText(str(self.delta_sky))
        b.bright_cut.setEnabled(False)
        self.w.btn_bright_cut = b.bright_cut
        self.w.btn_bright_cut.clicked.connect(self.bright_cut)
        self.w.bright_cut_delta = b.delta_bright
        b.delta_bright.setText(str(self.delta_bright))

        nb.addTab(w, "Controls")

        vbox3 = QtHelp.VBox()
        tw = QtGui.QPlainTextEdit()
        self.w.report = tw
        tw.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        vbox3.addWidget(self.w.report, stretch=1)
        self._appendText(tw, self._mkreport_header())
        
        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)

        btn = QtGui.QPushButton("Add Pick")
        btn.clicked.connect(self.add_pick_cb)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QCheckBox("Record Picks")
        btn.setChecked(self.do_record)
        btn.stateChanged.connect(self.record_cb)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox3.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)
        nb.addTab(vbox3, "Report")

        ## vbox4 = QtHelp.VBox()
        ## tw = QtGui.QPlainTextEdit()
        ## self.w.correct = tw
        ## tw.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        ## self._appendText(tw, "# paste a reference report here")
        ## vbox4.addWidget(self.w.correct, stretch=1)
        
        ## btns = QtHelp.HBox()
        ## layout = btns.layout()
        ## layout.setSpacing(3)

        ## btn = QtGui.QPushButton("Correct WCS")
        ## btn.clicked.connect(self.correct_wcs)
        ## layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        ## vbox4.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)
        ## nb.addTab(vbox4, "Correct")

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)
        #btns.set_child_size(15, -1)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vpaned.addWidget(sw)
        
        container.addWidget(vpaned, stretch=1)
        #vpaned.moveSplitter(260, 1)

    def _setText(self, w, text):
        w.setText(text)
        
    def _appendText(self, w, text):
        w.appendPlainText(text)
        
    def _copyText(self, w):
        return w.toPlainText()
        
    def _getText(self, w):
        return w.toPlainText()
        
    def _setEnabled(self, w, tf):
        w.setEnabled(tf)
        
    def record_cb(self, do_record):
        self.do_record = bool(do_record)
        
    def instructions(self):
        self.tw.setText("""Left-click to place region.  Left-drag to position region.  Redraw region with the right mouse button.""")
            
    def update_status(self, text):
        self.fv.gui_do(self.w.eval_status.setText, text)

    def init_progress(self):
        self.w.btn_intr_eval.setEnabled(True)
        self.w.eval_pgs.setValue(0)
        #self.w.eval_pgs.set_text("%.2f %%" % (0.0))
            
    def update_progress(self, pct):
        self.w.eval_pgs.setValue(int(pct * 100.0))
        #self.w.eval_pgs.set_text("%.2f %%" % (pct*100.0))
        
    def show_candidates_cb(self, tf):
        self.show_candidates = tf
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
        
        dialog = QtHelp.Dialog("Adjust WCS",
                               0,
                               [['Cancel', 0], ['Ok', 1]],
                               lambda w, rsp: self.adjust_wcs_cb(w, rsp, image, wcs_m))
        box = dialog.get_content_area()
        layout = QtGui.QVBoxLayout()
        box.setLayout(layout)
        
        layout.addWidget(QtGui.QLabel(msg), stretch=1)
        dialog.show()

    def adjust_wcs_cb(self, w, rsp, image, wcs_m):
        w.close()
        if rsp == 0:
            return

        #image.wcs = wcs_m.wcs
        image.update_keywords(wcs_m.hdr)
        return True
        
    def plot_scroll(self, event):
        delta = event.delta()
        direction = None
        if delta > 0:
            direction = 'up'
        elif delta < 0:
            direction = 'down'
        if direction == 'up':
            #delta = 0.9
            self.plot_zoomlevel += 1.0
        elif direction == 'down':
            #delta = 1.1
            self.plot_zoomlevel -= 1.0

        self.plot_panzoom()
        
        # x1, x2 = self.w.ax.get_xlim()
        # y1, y2 = self.w.ax.get_ylim()
        # self.w.ax.set_xlim(x1*delta, x2*delta)
        # self.w.ax.set_ylim(y1*delta, y2*delta)
        # self.w.canvas.draw()
        
    def plot_button_press(self, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
        self.logger.debug("button down event at %dx%d, button=%x" % (
            x, y, button))

        self.plot_x, self.plot_y = x, y
        return True

    def plot_button_release(self, event):
        # note: for mouseRelease this needs to be button(), not buttons()!
        buttons = event.button()
        x, y = event.x(), event.y()
        
        button = self.kbdmouse_mask
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))
            
    def plot_motion_notify(self, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()
        
        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4

        if button & 0x1:
            xdelta = x - self.plot_x
            ydelta = y - self.plot_y
            self.pan_plot(xdelta, ydelta)

    def __str__(self):
        return 'pick'

class MyFigureCanvas(FigureCanvas):

    def setDelegate(self, delegate):
        self.delegate = delegate
        
    def keyPressEvent(self, event):
        self.delegate.pan_plot(event)
        
    def mousePressEvent(self, event):
        self.delegate.plot_button_press(event)

    def mouseReleaseEvent(self, event):
        self.delegate.plot_button_release(event)

    def mouseMoveEvent(self, event):
        self.delegate.plot_motion_notify(event)

    def wheelEvent(self, event):
        self.delegate.plot_scroll(event)

        
    
#END
