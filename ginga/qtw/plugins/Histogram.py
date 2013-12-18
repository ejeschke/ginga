#
# Histogram.py -- Histogram plugin for Ginga fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.qtw import Plot
from ginga.misc.plugins import HistogramBase

class Histogram(HistogramBase.HistogramBase):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Histogram, self).__init__(fv, fitsimage)

        self.gui_up = False

    def build_gui(self, container):
        # Splitter is just to provide a way to size the graph
        # to a reasonable size
        vpaned = QtGui.QSplitter()
        vpaned.setOrientation(QtCore.Qt.Vertical)

        # Make the cuts plot
        twidget = QtHelp.VBox()
        vbox1 = twidget.layout()
        vbox1.setContentsMargins(4, 4, 4, 4)
        vbox1.setSpacing(2)

        msgFont = self.fv.getFont("sansFont", 14)
        tw = QtGui.QLabel()
        tw.setFont(msgFont)
        tw.setWordWrap(True)
        self.tw = tw

        fr = QtHelp.Frame("Instructions")
        fr.layout().addWidget(tw, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        self.plot = Plot.Plot(self.logger)
        w = self.plot.get_widget()
        vbox1.addWidget(w, stretch=1, alignment=QtCore.Qt.AlignTop)

        captions = (('Cut Low', 'xlabel', '@Cut Low', 'entry'),
                    ('Cut High', 'xlabel', '@Cut High', 'entry', 'Cut Levels', 'button'),
                    ('Auto Levels', 'button'),
                    ('Log Histogram', 'checkbutton', 'Plot By Cuts', 'checkbutton')
                    )

        w, b = QtHelp.build_info(captions)
        self.w.update(b)
        b.cut_levels.setToolTip("Set cut levels manually")
        b.auto_levels.setToolTip("Set cut levels by algorithm")
        b.cut_low.setToolTip("Set low cut level (press Enter)")
        b.cut_high.setToolTip("Set high cut level (press Enter)")
        b.log_histogram.setToolTip("Use the log of the pixel values for the histogram (empty bins map to 10^-1)")
        b.plot_by_cuts.setToolTip("Only show the part of the histogram between the cuts")
        b.cut_low.returnPressed.connect(self.cut_levels)
        b.cut_high.returnPressed.connect(self.cut_levels)
        b.cut_levels.clicked.connect(self.cut_levels)
        b.auto_levels.clicked.connect(self.auto_levels)
        b.log_histogram.setChecked(self.plot.logy)
        b.log_histogram.stateChanged.connect(lambda w: self.log_histogram_cb(b.log_histogram))
        b.plot_by_cuts.setChecked(self.xlimbycuts)

        b.plot_by_cuts.stateChanged.connect(lambda w: self.plot_by_cuts_cb(b.plot_by_cuts))

        vbox1.addWidget(w, stretch=0, alignment=QtCore.Qt.AlignLeft)

        btns = QtHelp.HBox()
        layout= btns.layout()
        layout.setSpacing(3)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(self.close)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QPushButton("Full Image")
        btn.clicked.connect(self.full_image)
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vbox1.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        vpaned.addWidget(twidget)
        vpaned.addWidget(QtGui.QLabel(''))

        container.addWidget(vpaned, stretch=1)

        self.gui_up = True

    def _getText(self, w):
        return w.text()

    def _setText(self, w, text):
        w.setText(text)

    def instructions(self):
        self.tw.setText("""Draw (or redraw) a region with the right mouse button.  Click or drag left mouse button to reposition region.""")

    def log_histogram_cb(self, w):
        self.plot.logy = w.checkState()
        if (self.histtag is not None) and self.gui_up:
            # self.histtag == None means no data is loaded yet
            self.redo()

    def plot_by_cuts_cb(self, w):
        self.xlimbycuts = w.checkState()
        if (self.histtag is not None) and self.gui_up:
            # self.histtag == None means no data is loaded yet
            self.redo()

    def __str__(self):
        return 'histogram'

# END
