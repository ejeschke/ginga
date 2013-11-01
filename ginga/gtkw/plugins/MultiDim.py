#
# MultiDim.py -- Multidimensional plugin for fits viewer
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gtkw import GtkHelp, gtksel
import gtk

from ginga import AstroImage, wcs
from ginga import GingaPlugin

class MultiDim(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(MultiDim, self).__init__(fv, fitsimage)

        self.curhdu = 0
        self.naxispath = []

    def build_gui(self, container):
        vbox1 = gtk.VBox()

        self.msgFont = self.fv.getFont("sansFont", 14)
        tw = gtk.TextView()
        tw.set_wrap_mode(gtk.WRAP_WORD)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.set_editable(False)
        tw.set_left_margin(4)
        tw.set_right_margin(4)
        tw.modify_font(self.msgFont)
        self.tw = tw

        fr = gtk.Frame(label=" Instructions ")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.set_label_align(0.1, 0.5)
        fr.add(tw)
        fr.show_all()
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)
        
        fr = gtk.Frame(label="HDU")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        captions = [("Num HDUs", 'label'), ("Choose HDU", 'spinbutton')]
        w, b = GtkHelp.build_info(captions)
        self.w.update(b)
        self.w.numhdu = b.num_hdus
        self.w.hdu = b.choose_hdu
        self.w.hdu.set_tooltip_text("Choose which HDU to view")
        if not gtksel.have_gtk3:
            self.w.hdu.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.w.hdu.connect('value-changed', self.set_hdu_cb)
        
        fr.add(w)
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)

        fr = gtk.Frame(label="NAXIS")
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.5, 0.5)

        self.naxisfr = fr
        vbox1.pack_start(fr, padding=4, fill=True, expand=False)

        btns = gtk.HButtonBox()
        btns.set_layout(gtk.BUTTONBOX_START)
        btns.set_spacing(3)

        btn = gtk.Button("Close")
        btn.connect('clicked', lambda w: self.close())
        btns.add(btn)
        vbox1.pack_start(btns, padding=4, fill=True, expand=False)

        vbox1.show_all()
        container.pack_start(vbox1, padding=0, fill=True, expand=False)

    def set_hdu_cb(self, w):
        idx = int(w.get_value())
        self.set_hdu(idx)

    def _make_slider(self, lower, upper):
        adj = gtk.Adjustment(lower=lower, upper=upper)
        adj.set_value(lower)
        scale = gtk.HScale(adj)
        #scale.set_size_request(200, -1)
        scale.set_digits(0)
        scale.set_draw_value(True)
        scale.set_value_pos(gtk.POS_BOTTOM)
        # if not gtksel.have_gtk3:
        #     scale.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        scale.add_mark(lower, gtk.POS_BOTTOM, "%d" % lower)
        scale.add_mark(upper, gtk.POS_BOTTOM, "%d" % upper)
        return scale

    def _make_spin(self, lower, upper):
        #adj = gtk.Adjustment(lower=lower, upper=upper)
        adj = gtk.Adjustment()
        adj.configure(lower, lower, upper, 1, 1, 0)
        adj.set_value(lower)
        scale = GtkHelp.SpinButton(adj)
        scale.set_digits(0)
        scale.set_wrap(True)
        scale.set_snap_to_ticks(True)
        # if not gtksel.have_gtk3:
        #     scale.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        return scale

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

        w, b = GtkHelp.build_info(captions)
        for n in xrange(0, len(dims)):
            key = 'naxis%d' % (n+1)
            lbl = b[key]
            maxn = int(dims[n])
            lbl.set_text("%d" % maxn)
            slkey = 'choose_'+key
            if b.has_key(slkey):
                slider = b[slkey]
                adj = slider.get_adjustment()
                lower = 1
                upper = maxn
                adj.configure(lower, lower, upper, 1, 1, 0)
                adj.set_value(lower)
                slider.set_digits(0)
                slider.set_wrap(True)
                slider.set_snap_to_ticks(True)
                slider.connect('value-changed', self.set_naxis_cb, n)
                if not gtksel.have_gtk3:
                    slider.set_update_policy(gtk.UPDATE_DISCONTINUOUS)

        # Add vbox of naxis controls to gui
        try:
            oldv = self.naxisfr.get_child()
            self.naxisfr.remove(oldv)
        except:
            pass
        self.naxisfr.add(w)
        self.naxisfr.show_all()

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_operation_channel(chname, str(self))
        return True
        
    def instructions(self):
        buf = self.tw.get_buffer()
        buf.set_text("""Use mouse wheel to choose HDU or axis of data cube.""")
        self.tw.modify_font(self.msgFont)
            
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

    def set_naxis_cb(self, w, n):
        idx = int(w.get_value()) - 1
        self.logger.debug("naxis %d index is %d" % (n+1, idx+1))

        image = AstroImage.AstroImage(logger=self.logger)
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
        #print "path=%s metadata: %s" % (path, str(md))

        self.path = path
        self.fits_f = wcs.pyfits.open(path, 'readonly')

        lower = 1
        upper = len(self.fits_f)
        self.num_hdu = upper
        ## self.w.num_hdus.set_text("%d" % self.num_hdu)
        self.logger.debug("there are %d hdus" % (upper))
        self.w.numhdu.set_text("%d" % (upper))
        adj = self.w.hdu.get_adjustment()
        adj.configure(lower, lower, upper, 1, 1, 0)
        self.w.hdu.set_sensitive(upper > 1)
        ## self.w.hdu.clear_marks()
        ## self.w.hdu.add_mark(lower, gtk.POS_BOTTOM, "%d" % lower)
        ## self.w.hdu.add_mark(upper, gtk.POS_BOTTOM, "%d" % upper)

        self.set_hdu(lower)

    def __str__(self):
        return 'multidim'
    
#END
