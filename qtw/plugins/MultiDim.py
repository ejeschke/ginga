#
# MultiDim.py -- Multidimensional plugin for fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:50:29 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from PyQt4 import QtGui, QtCore
import QtHelp

import pyfits
from AstroImage import AstroImage

import GingaPlugin

class MultiDim(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(MultiDim, self).__init__(fv, fitsimage)

        self.curhdu = 0
        self.naxispath = []

    def build_gui(self, container):
        sw = QtGui.QScrollArea()

        twidget = QtHelp.VBox()
        sp = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding,
                               QtGui.QSizePolicy.Fixed)
        twidget.setSizePolicy(sp)
        vbox1 = twidget.layout()
        vbox1.setContentsMargins(4, 4, 4, 4)
        vbox1.setSpacing(2)
        sw.setWidgetResizable(True)
        sw.setWidget(twidget)

        msgFont = QtGui.QFont("Sans", 14)
        tw = QtGui.QLabel()
        tw.setFont(msgFont)
        tw.setWordWrap(True)
        self.tw = tw

        fr = QtHelp.Frame("Instructions")
        fr.layout().addWidget(tw, stretch=1, alignment=QtCore.Qt.AlignTop)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)
        
        fr = QtHelp.Frame("HDU")

        captions = [("Num HDUs", 'label'), ("Choose HDU", 'spinbutton')]
        w, b = QtHelp.build_info(captions)
        self.w.update(b)
        self.w.numhdu = b.num_hdus
        self.w.hdu = b.choose_hdu
        self.w.hdu.valueChanged.connect(self.set_hdu_cb)
        
        fr.layout().addWidget(w, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        fr = QtHelp.Frame("NAXIS")

        self.stack = QtHelp.StackedWidget()
        self.stack.addWidget(QtGui.QLabel(''))
        fr.layout().addWidget(self.stack, stretch=1, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(fr, stretch=0, alignment=QtCore.Qt.AlignTop)

        btns = QtHelp.HBox()
        layout = btns.layout()
        layout.setSpacing(3)
        #btns.set_child_size(15, -1)

        btn = QtGui.QPushButton("Close")
        btn.clicked.connect(lambda w: self.close())
        layout.addWidget(btn, stretch=0, alignment=QtCore.Qt.AlignLeft)
        vbox1.addWidget(btns, stretch=0, alignment=QtCore.Qt.AlignLeft)

        container.addWidget(sw, stretch=1)

    def set_hdu_cb(self, idx):
        #idx = int(w.currentIndex())
        self.set_hdu(idx)

    def build_naxis(self, dims):
        # build a vbox of NAXIS controls
        captions = [("NAXIS1", 'label'), ("NAXIS2", 'label')]

        self.naxispath = []
        for n in xrange(2, len(dims)):
            self.naxispath.append(0)
            key = 'naxis%d' % (n+1)
            title = key.upper()
            maxn = int(dims[n])
            self.logger.debug("NAXIS%d=%d" % (n+1, maxn))
            if maxn <= 1:
                captions.append((title, 'label'))
            else:
                captions.append((title, 'label',
                                 "Choose %s" % (title), 'spinbutton'))

        w, b = QtHelp.build_info(captions)
        for n in xrange(0, len(dims)):
            key = 'naxis%d' % (n+1)
            lbl = b[key]
            maxn = int(dims[n])
            lbl.setText("%d" % maxn)
            slkey = 'choose_'+key
            if b.has_key(slkey):
                slider = b[slkey]
                lower = 1
                upper = maxn
                slider.setRange(lower, upper)
                slider.setSingleStep(1)
                slider.setWrapping(True)
                def make_cbfn(n):
                    return lambda idx: self.set_naxis_cb(idx-1, n)
                slider.valueChanged.connect(make_cbfn(n))

        # Add naxis controls to gui
        try:
            oldw = self.stack.currentWidget()
            self.stack.removeWidget(oldw)
        except:
            pass
        self.stack.addWidget(w)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def instructions(self):
        self.tw.setText("""Use mouse wheel to choose HDU or axis of data cube.""")
            
    def start(self):
        self.instructions()
        self.resume()

    def pause(self):
        pass
        
    def resume(self):
        self.redo()
        
    def stop(self):
        try:
            self.fits_f.close()
        except:
            pass
        self.fv.showStatus("")
        
    def set_hdu(self, idx):
        self.logger.debug("Loading fits hdu #%d" % (idx))
        image = AstroImage()
        image.set(path=self.path)
        try:
            hdu = self.fits_f[idx-1]
            dims = list(hdu.data.shape)
            dims.reverse()
            image.load_hdu(hdu)

            self.fitsimage.set_image(image)
            self.build_naxis(dims)
            self.curhdu = idx-1
            self.logger.debug("hdu #%d loaded." % (idx))
        except Exception, e:
            errmsg = "Error loading fits hdu #%d: %s" % (
                idx, str(e))
            self.logger.error(errmsg)
            self.fv.error(errmsg)

    def set_naxis_cb(self, idx, n):
        self.logger.debug("naxis %d index is %d" % (n+1, idx+1))

        image = AstroImage()
        image.set(path=self.path)
        try:
            hdu = self.fits_f[self.curhdu]
            data = hdu.data
            self.logger.debug("HDU #%d has naxis=%s" % (
                self.curhdu+1, str(data.shape)))

            # invert index
            m = len(data.shape) - (n+1)
            self.naxispath[m] = idx
            self.logger.debug("m=%d naxispath=%s" % (m, str(self.naxispath)))
        
            image.load_hdu(hdu, naxispath=self.naxispath)

            self.fitsimage.set_image(image)
            self.logger.debug("NAXIS%d slice %d loaded." % (n+1, idx+1))
        except Exception, e:
            errmsg = "Error loading NAXIS%d slice %d: %s" % (
                n+1, idx+1, str(e))
            self.logger.error(errmsg)
            self.fv.error(errmsg)

        
    def redo(self):
        image = self.fitsimage.get_image()
        md = image.get_metadata()
        path = md.get('path', 'NO PATH')
        self.logger.debug("path=%s metadata: %s" % (path, str(md)))

        self.path = path
        self.fits_f = pyfits.open(path, 'readonly')

        lower = 1
        upper = len(self.fits_f)
        self.num_hdu = upper
        self.logger.debug("there are %d hdus" % (upper))
        self.w.numhdu.setText("%d" % (upper))

        self.w.hdu.setRange(lower, upper)
        self.w.hdu.setEnabled(upper > 1)

        self.set_hdu(lower)

    def __str__(self):
        return 'multidim'
    
#END
