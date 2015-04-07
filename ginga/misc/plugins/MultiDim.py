#
# MultiDim.py -- Multidimensional plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import re

from ginga import AstroImage
from ginga.misc import Widgets, Future
from ginga import GingaPlugin
import ginga.util.six as six

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

        self.hdu_info = []
        self.curhdu = 0
        self.naxispath = []
        self.imgname = 'NONAME'
        self.image = None
        self.orientation = 'vertical'

        # For animation feature
        self.play_axis = 2
        self.play_idx = 1
        self.play_max = 1
        self.play_int_sec = 0.1
        self.play_min_sec = 0.1
        self.timer = fv.get_timer()
        self.timer.set_callback('expired', self.play_next)


    def build_gui(self, container):
        assert have_pyfits == True, \
               Exception("Please install astropy/pyfits to use this plugin")

        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         scrolled=False)
        self.orientation = orientation
        vbox.set_border_width(4)
        vbox.set_spacing(2)

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

        fr = Widgets.Frame("HDU")

        captions = [("Num HDUs:", 'label', "Num HDUs", 'llabel'),
                    ("Choose HDU", 'combobox'),
                    ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        self.w.numhdu = b.num_hdus
        self.w.hdu = b.choose_hdu
        self.w.hdu.set_tooltip("Choose which HDU to view")
        self.w.hdu.add_callback('activated', self.set_hdu_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("NAXIS (data cubes)")
        self.naxisfr = fr
        vbox.add_widget(fr, stretch=0)

        captions = [("First", 'button', "Prev", 'button', "Stop", 'button'),
                    ("Last", 'button', "Next", 'button', "Play", 'button'),
                    ("Interval:", 'label', "Interval", 'spinfloat'),
                    ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        b.next.add_callback('activated', lambda w: six.advance_iterator(self))
        b.prev.add_callback('activated', lambda w: self.prev())
        b.first.add_callback('activated', lambda w: self.first())
        b.last.add_callback('activated', lambda w: self.last())
        b.play.add_callback('activated', lambda w: self.play_start())
        b.stop.add_callback('activated', lambda w: self.play_stop())
        lower, upper = 0.1, 8.0
        b.interval.set_limits(lower, upper, incr_value=0.1)
        b.interval.set_value(lower)
        b.interval.set_decimals(2)
        b.interval.add_callback('value-changed', self.play_int_cb)

        b.next.set_enabled(False)
        b.prev.set_enabled(False)
        b.first.set_enabled(False)
        b.last.set_enabled(False)
        b.play.set_enabled(False)
        b.stop.set_enabled(False)
        b.interval.set_enabled(False)
        vbox.add_widget(w, stretch=0)

        captions = [("Slice:", 'label', "Slice", 'llabel',
                     "Value:", 'label', "Value", 'llabel'),
                    ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        vbox.add_widget(w, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=0)

        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=0)

    def set_hdu_cb(self, w, val):
        #idx = int(val)
        idx = w.get_index()
        idx = max(0, idx)
        self.set_hdu(idx)

    def set_naxis_cb(self, w, idx, n):
        #idx = int(w.get_value()) - 1
        self.set_naxis(idx, n)

    def build_naxis(self, dims):
        # build a vbox of NAXIS controls
        captions = [("NAXIS1:", 'label', 'NAXIS1', 'llabel'),
                    ("NAXIS2:", 'label', 'NAXIS2', 'llabel')]

        self.naxispath = []
        for n in range(2, len(dims)):
            self.naxispath.append(0)
            key = 'naxis%d' % (n+1)
            title = key.upper()
            maxn = int(dims[n])
            self.logger.debug("NAXIS%d=%d" % (n+1, maxn))
            if maxn <= 1:
                captions.append((title+':', 'label', title, 'llabel'))
            else:
                captions.append((title+':', 'label', title, 'llabel',
                                 #"Choose %s" % (title), 'spinbutton'))
                                 "Choose %s" % (title), 'hscale'))

        # Remove old naxis widgets
        for key in self.w:
            if key.startswith('choose_'):
                self.w[key] = None

        w, b = Widgets.build_info(captions, orientation=self.orientation)
        self.w.update(b)
        for n in range(0, len(dims)):
            key = 'naxis%d' % (n+1)
            lbl = b[key]
            maxn = int(dims[n])
            lbl.set_text("%d" % maxn)
            slkey = 'choose_'+key
            if slkey in b:
                slider = b[slkey]
                lower = 1
                upper = maxn
                slider.set_limits(lower, upper, incr_value=1)
                slider.set_value(lower)
                slider.set_tracking(True)
                #slider.set_digits(0)
                #slider.set_wrap(True)
                slider.add_callback('value-changed', self.set_naxis_cb, n)

        # Add vbox of naxis controls to gui
        self.naxisfr.set_widget(w)

        self.play_axis = 2
        if self.play_axis < len(dims):
            self.play_max = dims[self.play_axis]
        self.play_idx = 1

        # Enable or disable NAXIS animation controls
        is_dc = len(dims) > 2
        self.w.next.set_enabled(is_dc)
        self.w.prev.set_enabled(is_dc)
        self.w.first.set_enabled(is_dc)
        self.w.last.set_enabled(is_dc)
        self.w.play.set_enabled(is_dc)
        self.w.stop.set_enabled(is_dc)
        self.w.interval.set_enabled(is_dc)

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def instructions(self):
        self.tw.set_text("""Use mouse wheel to choose HDU or axis of data cube (NAXIS controls).""")
            
    def start(self):
        self.instructions()
        self.resume()

    def pause(self):
        self.play_stop()
        pass

    def resume(self):
        self.redo()

    def stop(self):
        self.play_stop()
        try:
            self.fits_f.close()
        except:
            pass
        self.fv.showStatus("")

    def get_name(self, idx):
        return '%s[%d]' % (self.imgname, idx)

    def set_hdu(self, idx):
        self.logger.debug("Loading fits hdu #%d" % (idx))

        # See if this HDU is still in the channel's datasrc
        imname = self.get_name(idx)
        chname = self.fv.get_channelName(self.fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        if imname in chinfo.datasrc:
            self.curhdu = idx
            self.image = chinfo.datasrc[imname]
            self.fv.switch_name(chname, imname)

            # Still need to build datacube profile
            hdu = self.fits_f[idx]
            dims = list(hdu.data.shape)
            dims.reverse()
            self.build_naxis(dims)
            return

        # Nope, we'll have to load it
        self.logger.debug("HDU %d not in memory; refreshing from file" % (idx))

        # inherit from primary header?
        inherit_prihdr = self.fv.settings.get('inherit_primary_header', False)
        
        image = AstroImage.AstroImage(logger=self.logger,
                                      inherit_primary_header=inherit_prihdr)
        self.image = image
        try:
            self.curhdu = idx
            dims = [0, 0]
            info = self.hdu_info[idx]
            hdu = self.fits_f[idx]

            if hdu.data is None:
                # <- empty data part to this HDU
                self.logger.warn("Empty data part in HDU #%d" % (idx))

            elif info['htype'].lower() not in ('imagehdu', 'primaryhdu'):
                self.logger.warn("HDU #%d is not an image" % (idx))

            else:
                dims = list(hdu.data.shape)
                dims.reverse()

            image.load_hdu(hdu, fobj=self.fits_f)

            # create a future for reconstituting this HDU
            future = Future.Future()
            future.freeze(self.fv.load_image, self.path, idx=idx)
            image.set(path=self.path, name=imname, image_future=future)

            ## self.fitsimage.set_image(image,
            ##                          raise_initialize_errors=False)
            self.fv.add_image(imname, image, chname=chname)

            self.build_naxis(dims)
            self.logger.debug("HDU #%d loaded." % (idx))

        except Exception as e:
            errmsg = "Error loading FITS HDU #%d: %s" % (
                idx, str(e))
            self.logger.error(errmsg)
            self.fv.show_error(errmsg)

    def set_naxis(self, idx, n):
        self.play_idx = idx
        self.w['choose_naxis%d' % (n+1)].set_value(idx)
        idx = idx - 1
        self.logger.debug("naxis %d index is %d" % (n+1, idx+1))

        image = self.fitsimage.get_image()
        try:
            if image is None:
                raise ValueError("Please load an image cube")

            hdu = self.fits_f[self.curhdu]
            data = hdu.data
            if data is None:
                raise ValueError("Empty data for this HDU")

            self.logger.debug("HDU #%d has naxis=%s" % (
                self.curhdu, str(data.shape)))

            # invert index
            m = len(data.shape) - (n+1)
            self.naxispath[m] = idx
            self.logger.debug("m=%d naxispath=%s" % (m, str(self.naxispath)))

            for i in self.naxispath:
                data = data[i]

            if n == 2:
                # Try to print the spectral coordinate
                try:
                    specval = image.spectral_coord()
                    self.w.slice.set_text(str(idx+1))
                    self.w.value.set_text(str(specval))
                except:
                    pass

            image.set_data(data)
            self.logger.debug("NAXIS%d slice %d loaded." % (n+1, idx+1))

        except Exception as e:
            errmsg = "Error loading NAXIS%d slice %d: %s" % (
                n+1, idx+1, str(e))
            self.logger.error(errmsg)
            self.fv.error(errmsg)

    def play_start(self):
        self._isplaying = True
        self.play_next(self.timer)

    def play_next(self, timer):
        if self._isplaying:
            time_start = time.time()
            deadline = time_start + self.play_int_sec
            six.advance_iterator(self)
            #self.fv.update_pending(0.001)
            delta = max(deadline - time.time(), 0.001)
            self.timer.set(delta)

    def play_stop(self):
        self._isplaying = False

    def first(self):
        play_idx = 1
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def last(self):
        play_idx = self.play_max
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def prev(self):
        play_idx = self.play_idx - 1
        if play_idx < 1:
            play_idx = self.play_max
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def next(self):
        play_idx = self.play_idx + 1
        if play_idx > self.play_max:
            play_idx = 1
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def play_int_cb(self, w, val):
        # force at least play_min_sec, otherwise playback is untenable
        self.play_int_sec = max(self.play_min_sec, val)

    def prep_hdu_menu(self, w, info):
        # clear old TOC
        w.clear()
        self.hdu_info = []

        idx = 0
        for tup in info:
            d = dict(index=idx, name=tup[1], htype=tup[2], dtype=tup[5])
            self.hdu_info.append(d)

            toc_ent = "%(index)4d %(name)-12.12s %(htype)-12.12s %(dtype)-8.8s" % d
            w.append_text(toc_ent)
            idx += 1

        idx = w.get_index()
        if idx < 0:
            idx = 0
        if idx >= len(self.hdu_info):
            idx = len(self.hdu_info) - 1
        #w.set_index(idx)

    def redo(self):
        image = self.fitsimage.get_image()
        if (image is None) or (image == self.image):
            return True

        path = image.get('path', None)
        if path is None:
            self.fv.show_error("Cannot open image: no value for metadata key 'path'")
            return

        self.path = path

        name = self.fv.name_image_from_path(path)
        # remove index designation from root of name, if any
        match = re.match(r'^(.+)\[(\d+)\]$', name)
        if match:
            name = match.group(1)
        self.imgname = name

        self.fits_f = pyfits.open(path, 'readonly')

        lower = 0
        upper = len(self.fits_f) - 1
        info = self.fits_f.info(output=False)
        self.prep_hdu_menu(self.w.hdu, info)
        self.num_hdu = upper
        self.logger.debug("there are %d hdus" % (upper))
        self.w.numhdu.set_text("%d" % (upper))

        self.w.hdu.set_enabled(len(self.fits_f) > 0)


    def __str__(self):
        return 'multidim'

#END
