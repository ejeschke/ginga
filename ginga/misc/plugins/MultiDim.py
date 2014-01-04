#
# MultiDim.py -- Multidimensional plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import AstroImage
from ginga.misc import Widgets
from ginga import GingaPlugin

have_pyfits = False
try:
    from astropy.io import fits as pyfits
    have_pyfits = True
except ImportError:
    try:
        import pyfits
        have_pyfits = True
    except ImportError:
        pass

class MultiDim(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(MultiDim, self).__init__(fv, fitsimage)

        self.curhdu = 0
        self.naxispath = []
        self.refs = []

    def build_gui(self, container):
        assert have_pyfits == True, \
               Exception("Please install astropy/pyfits to use this plugin")

        vbox1 = Widgets.VBox()
        vbox1.set_border_width(4)
        vbox1.set_spacing(4)

        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        fr = Widgets.Frame("Instructions")
        fr.set_widget(tw)
        vbox1.add_widget(fr, stretch=0)
        
        fr = Widgets.Frame("HDU")

        captions = [("Num HDUs:", 'label', "Num HDUs", 'llabel'),
                    ("Choose HDU", 'spinbutton')]
        w, b = Widgets.build_info(captions)
        self.w.update(b)
        self.w.numhdu = b.num_hdus
        self.w.hdu = b.choose_hdu
        self.w.hdu.set_tooltip("Choose which HDU to view")
        self.w.hdu.add_callback('value-changed', self.set_hdu_cb)
        
        fr.set_widget(w)
        vbox1.add_widget(fr, stretch=0)

        fr = Widgets.Frame("NAXIS")
        self.naxisfr = fr
        vbox1.add_widget(fr, stretch=0)

        # FIX: somehow this is not working correctly with Qt 
        vbox1.add_widget(Widgets.Label(''), stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox1.add_widget(btns, stretch=0)

        container.add_widget(vbox1, stretch=1)

    def set_hdu_cb(self, w, val):
        idx = int(val)
        self.set_hdu(idx)

    def build_naxis(self, dims):
        # build a vbox of NAXIS controls
        captions = [("NAXIS1:", 'label', 'NAXIS1', 'llabel'),
                    ("NAXIS2:", 'label', 'NAXIS2', 'llabel')]

        self.naxispath = []
        for n in xrange(2, len(dims)):
            self.naxispath.append(0)
            key = 'naxis%d' % (n+1)
            title = key.upper()
            maxn = int(dims[n])
            self.logger.debug("NAXIS%d=%d" % (n+1, maxn))
            if maxn <= 1:
                captions.append((title+':', 'label', title, 'llabel'))
            else:
                captions.append((title+':', 'label', title, 'llabel',
                                 "Choose %s" % (title), 'spinbutton'))

        w, b = Widgets.build_info(captions)
        self.w.update(b)
        for n in xrange(0, len(dims)):
            key = 'naxis%d' % (n+1)
            lbl = b[key]
            maxn = int(dims[n])
            lbl.set_text("%d" % maxn)
            slkey = 'choose_'+key
            if b.has_key(slkey):
                slider = b[slkey]
                lower = 1
                upper = maxn
                slider.set_limits(lower, upper, incr_value=1)
                slider.set_value(lower)
                #slider.set_digits(0)
                #slider.set_wrap(True)
                slider.add_callback('value-changed', self.set_naxis_cb, n)

        # Add vbox of naxis controls to gui
        self.naxisfr.set_widget(w)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True
        
    def instructions(self):
        self.tw.set_text("""Use mouse wheel to choose HDU or axis of data cube.""")
            
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
        image = AstroImage.AstroImage(logger=self.logger)
        try:
            hdu = self.fits_f[idx-1]
            dims = list(hdu.data.shape)
            dims.reverse()
            image.load_hdu(hdu)
            image.set(path=self.path)

            self.fitsimage.set_image(image)
            self.build_naxis(dims)
            self.curhdu = idx-1
            self.logger.debug("hdu #%d loaded." % (idx))
        except Exception, e:
            errmsg = "Error loading fits hdu #%d: %s" % (
                idx, str(e))
            self.logger.error(errmsg)
            self.fv.error(errmsg)

    def set_naxis_cb(self, w, idx, n):
        #idx = int(w.get_value()) - 1
        idx = idx - 1
        self.logger.debug("naxis %d index is %d" % (n+1, idx+1))

        image = AstroImage.AstroImage(logger=self.logger)
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
            image.set(path=self.path)

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
        path = md.get('path', None)
        if path == None:
            self.fv.show_error("Cannot open image: no value for metadata key 'path'")
            return

        self.path = path
        self.fits_f = pyfits.open(path, 'readonly')

        lower = 1
        upper = len(self.fits_f)
        self.num_hdu = upper
        ## self.w.num_hdus.set_text("%d" % self.num_hdu)
        self.logger.debug("there are %d hdus" % (upper))
        self.w.numhdu.set_text("%d" % (upper))
        adj = self.w.hdu.set_limits(lower, upper, incr_value=1)
        self.w.hdu.set_enabled(upper > 1)

        self.set_hdu(lower)

    def __str__(self):
        return 'multidim'
    
#END
