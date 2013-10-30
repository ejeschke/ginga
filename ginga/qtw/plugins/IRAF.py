#
# IRAF.py -- IRAF plugin for Ginga fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
The IRAF plugin implements a remote control interface for the Ginga FITS
viewer from an IRAF session.  In particular it supports the use of the
IRAF 'display' and 'imexamine' commands.

NOTE: Almost all of the functionality is implemented in the IRAFBase and
IIS_DataListener classes located in the misc/plugins directory.  This is
just the GUI-specific pieces.

See instructions for use in IRAFBase.
"""
from ginga.misc.plugins import IRAFBase

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.qtw import ImageViewCanvasTypesQt as CanvasTypes


class IRAF(IRAFBase.IRAFBase):

    def build_gui(self, container):

        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.set_callback('none-move', self.cursormotion)
        canvas.add_callback('key-press', self.window_key_press)
        canvas.add_callback('key-release', self.window_key_release)
        self.canvas = canvas

        vbox = QtHelp.VBox()
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                               QtGui.QSizePolicy.Fixed)
        vbox.setSizePolicy(sp)

        fr = QtHelp.Frame("IRAF")

        captions = [("Control", 'hbox'),
                    ("Channel", 'label'),
                    ]
        w, b = QtHelp.build_info(captions)
        self.w = b
        self.w.mode_d = {}
        btn = QtGui.QRadioButton("Ginga")
        btn.toggled.connect(lambda w: self.switchMode('ginga'))
        self.w.mode_d['ginga'] = btn
        self.w.control.layout().addWidget(btn, stretch=0,
                                          alignment=QtCore.Qt.AlignLeft)
        btn = QtGui.QRadioButton("IRAF")
        btn.toggled.connect(lambda w: self.switchMode('iraf'))
        self.w.mode_d['iraf'] = btn
        self.w.control.layout().addWidget(btn, stretch=0,
                                          alignment=QtCore.Qt.AlignLeft)

        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        fr = QtHelp.Frame("Frame/Channel")

        lbl = QtGui.QLabel("")
        self.w.frch = lbl

        fr.layout().addWidget(lbl, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        container.addWidget(vbox, stretch=0, alignment=QtCore.Qt.AlignTop)

    def update_chinfo(self, fmap):
        # Update the GUI with the new frame/channel mapping
        fmap.sort(lambda x, y: x[1] - y[1])

        s = ["%2d: %s" % (num, name) for (name, num) in fmap]
        self.w.frch.setText("\n".join(s))

    def _setMode(self, modeStr, chname):
        modeStr = modeStr.lower()
        self.w.mode_d[modeStr].setChecked(True)
        self.w.channel.setText(chname)

        self.switchMode(modeStr)
        
    def toggleMode(self):
        isIRAF = self.w.mode_d['iraf'].isChecked()
        chname = self.imexam_chname
        if isIRAF:
            print "setting mode to Ginga"
            self.setMode('Ginga', chname)
        else:
            print "setting mode to IRAF"
            self.setMode('IRAF', chname)


#END
