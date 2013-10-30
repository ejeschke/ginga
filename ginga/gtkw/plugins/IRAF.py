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

import gtk
from ginga.gtkw import GtkHelp
from ginga.gtkw import ImageViewCanvasTypesGtk as CanvasTypes


class IRAF(IRAFBase.IRAFBase):

    def build_gui(self, container):

        canvas = CanvasTypes.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.set_callback('cursor-motion', self.cursormotion)
        canvas.add_callback('key-press', self.window_key_press)
        canvas.add_callback('key-release', self.window_key_release)
        self.canvas = canvas

        vbox1 = gtk.VBox()

        fr = gtk.Frame("IRAF")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = [("Control", 'hbox'),
                    ("Channel", 'label'),
                    ]
        w, b = GtkHelp.build_info(captions)
        fr.add(w)
        self.w = b
        self.w.mode_d = {}
        btn = GtkHelp.RadioButton(group=None, label="Ginga")
        btn.sconnect('toggled', lambda w: self.switchMode('ginga'))
        self.w.mode_d['ginga'] = btn
        self.w.control.pack_start(btn, padding=4, fill=False, expand=False)
        btn = GtkHelp.RadioButton(group=btn, label="IRAF")
        btn.sconnect('toggled', lambda w: self.switchMode('iraf'))
        self.w.mode_d['iraf'] = btn
        self.w.control.pack_start(btn, padding=4, fill=False, expand=False)
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)

        fr = gtk.Frame("Frame/Channel")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        lbl = gtk.Label("")
        self.w.frch = lbl
        fr.add(lbl)
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)

        vbox1.show_all()
        container.pack_start(vbox1, padding=0, fill=True, expand=False)

    def update_chinfo(self, fmap):
        # Update the GUI with the new frame/channel mapping
        fmap.sort(lambda x, y: x[1] - y[1])

        s = ["%2d: %s" % (num, name) for (name, num) in fmap]
        self.w.frch.set_text("\n".join(s))

    def _setMode(self, modeStr, chname):
        modeStr = modeStr.lower()
        self.w.mode_d[modeStr].set_active(True)
        self.w.channel.set_text(chname)

        self.switchMode(modeStr)
        
    def toggleMode(self):
        isIRAF = self.w.mode_d['iraf'].get_active()
        chname = self.imexam_chname
        if isIRAF:
            print "setting mode to Ginga"
            self.setMode('Ginga', chname)
        else:
            print "setting mode to IRAF"
            self.setMode('IRAF', chname)


#END
