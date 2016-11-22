#
# Mosaic.py -- Mosaic plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import time
import numpy
import os.path
import threading

from ginga.AstroImage import AstroImage
from ginga.util import mosaic
from ginga.util import wcs, iqcalc, dp
from ginga import GingaPlugin
from ginga.gw import Widgets

try:
    import astropy.io.fits as pyfits
    have_pyfits = True
except ImportError:
    have_pyfits = False

class Mosaic(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Mosaic, self).__init__(fv, fitsimage)

        self.mosaic_count = 0
        self.img_mosaic = None
        self.bg_ref = 0.0

        self.ev_intr = threading.Event()
        self.lock = threading.RLock()
        self.read_elapsed = 0.0
        self.process_elapsed = 0.0
        self.ingest_count = 0
        # holds processed images to be inserted into mosaic image
        self.images = []
        self.total_files = 0
        self.num_groups = 0
        # can set this to annotate images with a specific
        # value drawn from the FITS kwd
        self.ann_fits_kwd = None

        self.dc = self.fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.add_callback('drag-drop', self.drop_cb)
        canvas.set_surface(fitsimage)
        #canvas.ui_setActive(True)
        self.canvas = canvas
        self.layertag = 'mosaic-canvas'

        # Load plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_Mosaic')
        self.settings.setDefaults(annotate_images=False, fov_deg=0.2,
                                  match_bg=False, trim_px=0,
                                  merge=False, num_threads=4,
                                  drop_creates_new_mosaic=False,
                                  mosaic_hdus=False, skew_limit=0.1,
                                  allow_expand=True, expand_pad_deg=0.01,
                                  max_center_deg_delta=2.0,
                                  make_thumbs=True, reuse_image=False)
        self.settings.load(onError='silent')

        # channel where mosaic should appear (default=ours)
        self.mosaic_chname = self.chname

        # hook to allow special processing before inlining
        self.preprocess = lambda x: x

        self.gui_up = False


    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        self.msg_font = self.fv.get_font("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msg_font)
        self.tw = tw

        fr = Widgets.Expander("Instructions")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("Mosaic")

        captions = [
            ("FOV (deg):", 'label', 'Fov', 'llabel', 'set_fov', 'entry'),
            ("New Mosaic", 'button', "Allow expansion", 'checkbutton'),
            ("Label images", 'checkbutton', "Match bg", 'checkbutton'),
            ("Trim Pixels:", 'label', 'Trim Px', 'llabel',
             'trim_pixels', 'entry'),
            ("Num Threads:", 'label', 'Num Threads', 'llabel',
             'set_num_threads', 'entry'),
            ("Merge data", 'checkbutton', "Drop new",
             'checkbutton'),
            ("Mosaic HDUs", 'checkbutton'),
            ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        fov_deg = self.settings.get('fov_deg', 1.0)
        b.fov.set_text(str(fov_deg))
        #b.set_fov.set_length(8)
        b.set_fov.set_text(str(fov_deg))
        b.set_fov.add_callback('activated', self.set_fov_cb)
        b.set_fov.set_tooltip("Set size of mosaic FOV (deg)")
        b.allow_expansion.set_tooltip("Allow image to expand the FOV")
        allow_expand = self.settings.get('allow_expand', True)
        b.allow_expansion.set_state(allow_expand)
        b.allow_expansion.add_callback('activated', self.allow_expand_cb)
        b.new_mosaic.add_callback('activated', lambda w: self.new_mosaic_cb())
        labelem = self.settings.get('annotate_images', False)
        b.label_images.set_state(labelem)
        b.label_images.set_tooltip("Label tiles with their names (only if allow_expand=False)")
        b.label_images.add_callback('activated', self.annotate_cb)

        trim_px = self.settings.get('trim_px', 0)
        match_bg = self.settings.get('match_bg', False)
        b.match_bg.set_tooltip("Try to match background levels")
        b.match_bg.set_state(match_bg)
        b.match_bg.add_callback('activated', self.match_bg_cb)
        b.trim_pixels.set_tooltip("Set number of pixels to trim from each edge")
        b.trim_px.set_text(str(trim_px))
        b.trim_pixels.add_callback('activated', self.trim_pixels_cb)
        #b.trim_pixels.set_length(8)
        b.trim_pixels.set_text(str(trim_px))

        num_threads = self.settings.get('num_threads', 4)
        b.num_threads.set_text(str(num_threads))
        #b.set_num_threads.set_length(8)
        b.set_num_threads.set_text(str(num_threads))
        b.set_num_threads.set_tooltip("Number of threads to use for mosaicing")
        b.set_num_threads.add_callback('activated', self.set_num_threads_cb)
        merge = self.settings.get('merge', False)
        b.merge_data.set_tooltip("Merge data instead of overlay")
        b.merge_data.set_state(merge)
        b.merge_data.add_callback('activated', self.merge_cb)
        drop_new = self.settings.get('drop_creates_new_mosaic', False)
        b.drop_new.set_tooltip("Dropping files on image starts a new mosaic")
        b.drop_new.set_state(drop_new)
        b.drop_new.add_callback('activated', self.drop_new_cb)
        mosaic_hdus = self.settings.get('mosaic_hdus', False)
        b.mosaic_hdus.set_tooltip("Mosaic data HDUs in each file")
        b.mosaic_hdus.set_state(mosaic_hdus)
        b.mosaic_hdus.add_callback('activated', self.mosaic_hdus_cb)

        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        vbox2 = Widgets.VBox()
        # Mosaic evaluation status
        hbox = Widgets.HBox()
        hbox.set_spacing(4)
        hbox.set_border_width(4)
        label = Widgets.Label()
        self.w.eval_status = label
        hbox.add_widget(self.w.eval_status, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox2.add_widget(hbox, stretch=0)

        # Mosaic evaluation progress bar and stop button
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

        vbox2.add_widget(hbox, stretch=0)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(vbox2, stretch=1)

        self.w.vbox = Widgets.VBox()
        vbox.add_widget(self.w.vbox, stretch=0)

        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)
        self.gui_up = True


    def set_preprocess(self, fn):
        if fn is None:
            fn = lambda x: x
        self.preprocess = fn


    def prepare_mosaic(self, image, fov_deg, name=None):
        """Prepare a new (blank) mosaic image based on the pointing of
        the parameter image
        """
        header = image.get_header()
        ra_deg, dec_deg = header['CRVAL1'], header['CRVAL2']

        data_np = image.get_data()
        #dtype = data_np.dtype
        dtype = None
        self.bg_ref = iqcalc.get_median(data_np)

        # TODO: handle skew (differing rotation for each axis)?

        skew_limit = self.settings.get('skew_limit', 0.1)
        (rot_deg, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header,
                                                               skew_threshold=skew_limit)
        self.logger.debug("image0 rot=%f cdelt1=%f cdelt2=%f" % (
            rot_deg, cdelt1, cdelt2))

        # TODO: handle differing pixel scale for each axis?
        px_scale = math.fabs(cdelt1)
        cdbase = [numpy.sign(cdelt1), numpy.sign(cdelt2)]

        reuse_image = self.settings.get('reuse_image', False)
        if (not reuse_image) or (self.img_mosaic is None):
            self.logger.debug("creating blank image to hold mosaic")
            self.fv.gui_do(self._prepare_mosaic1, "Creating blank image...")

            # GC old mosaic
            self.img_mosaic = None

            img_mosaic = dp.create_blank_image(ra_deg, dec_deg,
                                               fov_deg, px_scale,
                                               rot_deg,
                                               cdbase=cdbase,
                                               logger=self.logger,
                                               pfx='mosaic',
                                               dtype=dtype)

            if name is not None:
                img_mosaic.set(name=name)
            imname = img_mosaic.get('name', image.get('name', "NoName"))

            # avoid making a thumbnail of this if seed image is also that way
            nothumb = not self.settings.get('make_thumbs', False)
            if nothumb:
                img_mosaic.set(nothumb=True)
            else:
                # image is not on disk, set indication for other plugins
                img_mosaic.set(path=None)

            # TODO: fill in interesting/select object headers from seed image

            self.img_mosaic = img_mosaic
            self.fv.gui_call(self.fv.add_image, imname, img_mosaic,
                             chname=self.mosaic_chname)

        else:
            # <-- reuse image (faster)
            self.logger.debug("Reusing previous mosaic image")
            self.fv.gui_do(self._prepare_mosaic1, "Reusing previous mosaic image...")

            img_mosaic = dp.recycle_image(self.img_mosaic,
                                          ra_deg, dec_deg,
                                          fov_deg, px_scale,
                                          rot_deg,
                                          cdbase=cdbase,
                                          logger=self.logger,
                                          pfx='mosaic')

        header = img_mosaic.get_header()
        (rot, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header,
                                                           skew_threshold=skew_limit)
        self.logger.debug("mosaic rot=%f cdelt1=%f cdelt2=%f" % (
            rot, cdelt1, cdelt2))

        return img_mosaic

    def _prepare_mosaic1(self, msg):
        self.canvas.delete_all_objects()
        self.update_status(msg)

    def _inline(self, images):
        self.fv.assert_nongui_thread()

        # Get optional parameters
        trim_px = self.settings.get('trim_px', 0)
        match_bg = self.settings.get('match_bg', False)
        merge = self.settings.get('merge', False)
        allow_expand = self.settings.get('allow_expand', True)
        expand_pad_deg = self.settings.get('expand_pad_deg', 0.010)
        annotate = self.settings.get('annotate_images', False)
        bg_ref = None
        if match_bg:
            bg_ref = self.bg_ref

        time_intr1 = time.time()

        # Add description for ChangeHistory
        iminfo = self.channel.get_image_info(self.img_mosaic.get('name'))
        iminfo.reason_modified = 'Added {0}'.format(
            ','.join([im.get('name') for im in images]))

        loc = self.img_mosaic.mosaic_inline(images,
                                            bg_ref=bg_ref,
                                            trim_px=trim_px,
                                            merge=merge,
                                            allow_expand=allow_expand,
                                            expand_pad_deg=expand_pad_deg,
                                            suppress_callback=True)

        # annotate ingested image with its name?
        if annotate and (not allow_expand):
            for i, image in enumerate(images):
                (xlo, ylo, xhi, yhi) = loc[i]
                header = image.get_header()
                if self.ann_fits_kwd is not None:
                    imname = str(header[self.ann_fits_kwd])
                else:
                    imname = image.get('name', 'noname')

                x, y = (xlo+xhi) / 2., (ylo+yhi) / 2.
                self.canvas.add(self.dc.Text(x, y, imname, color='red'),
                                redraw=False)

        time_intr2 = time.time()
        self.process_elapsed += time_intr2 - time_intr1

    def close(self):
        self.img_mosaic = None
        self.fv.stop_local_plugin(self.chname, str(self))
        self.gui_up = False
        return True

    def instructions(self):
        self.tw.set_text("""Set the FOV and drag files onto the window.""")

    def start(self):
        self.instructions()
        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            obj = p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        self.resume()

    def stop(self):
        self.canvas.ui_setActive(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except:
            pass
        # dereference potentially large mosaic image
        self.img_mosaic = None
        self.fv.show_status("")

    def pause(self):
        # comment this to NOT disable the UI for this plugin
        # when it loses focus
        #self.canvas.ui_setActive(False)
        pass

    def resume(self):
        self.canvas.ui_setActive(True)

    def new_mosaic_cb(self):
        self.img_mosaic = None
        self.fitsimage.onscreen_message("Drag new files...",
                                        delay=2.0)

    def drop_cb(self, canvas, paths, *args):
        self.logger.info("files dropped: %s" % str(paths))
        new_mosaic = self.settings.get('drop_creates_new_mosaic', False)
        self.fv.nongui_do(self.fv.error_wrap, self.mosaic, paths,
                          new_mosaic=new_mosaic)
        return True

    def annotate_cb(self, widget, tf):
        self.settings.set(annotate_images=tf)

    def allow_expand_cb(self, widget, tf):
        self.settings.set(allow_expand=tf)

    def ingest_one(self, image):

        with self.lock:
            self.images.append(image)
            self.ingest_count += 1
            count = self.ingest_count

            self.update_progress(float(count) / self.total_files)

    def mosaic_some(self, paths, image_loader=None):
        if image_loader is None:
            image_loader = self.fv.load_image

        try:
            for url in paths:
                if self.ev_intr.isSet():
                    break
                mosaic_hdus = self.settings.get('mosaic_hdus', False)
                if mosaic_hdus:
                    self.logger.debug("loading hdus")
                    # User wants us to mosaic HDUs
                    # TODO: do this in a different thread?
                    with pyfits.open(url, 'readonly') as in_f:
                        i = 0
                        for hdu in in_f:
                            i += 1
                            # TODO: I think we need a little more rigorous test
                            # than just whether the data section is empty
                            if hdu.data is None:
                                continue
                            self.logger.debug("ingesting hdu #%d" % (i))
                            image = None
                            try:
                                image = self.fv.fits_opener.load_hdu(hdu)

                            except Exception as e:
                                self.logger.error("Failed to open HDU #%d: %s" % (
                                    i, str(e)))
                                continue

                            if not isinstance(image, AstroImage):
                                self.logger.debug("HDU #%d is not an image; skipping..." % (
                                    i))
                                continue

                            image.set(name='hdu%d' % (i))

                            image = self.preprocess(image)

                            # we have to up the number of total files
                            if i > 1:
                                with self.lock:
                                    self.total_files += 1

                            self.ingest_one(image)

                else:
                    image = image_loader(url)

                    image = self.preprocess(image)
                    self.ingest_one(image)

        finally:
            with self.lock:
                self.num_groups -= 1
                if self.num_groups <= 0:
                    self.fv.nongui_do(self.finish_mosaic)


    def finish_mosaic(self):
        # NOTE: this runs in a nongui thread
        self.fv.assert_nongui_thread()

        self.update_status("mosaicing images...")
        images, self.images = self.images, []
        #self.fv.gui_do(self._inline, images)
        self._inline(images)

        self.end_progress()

        total_elapsed = time.time() - self.start_time
        msg = "Done. Total=%.2f Process=%.2f (sec)" % (
            total_elapsed, self.process_elapsed)
        self.update_status(msg)

        self.fv.gui_do(self.fitsimage.redraw, whence=0)

    def mosaic(self, paths, new_mosaic=False, name=None, image_loader=None):
        if image_loader is None:
            image_loader = self.fv.load_image

        # NOTE: this runs in a non-gui thread
        self.fv.assert_nongui_thread()

        # Initialize progress bar
        self.total_files = len(paths)
        if self.total_files == 0:
            return

        self.ingest_count = 0
        self.images = []
        self.ev_intr.clear()
        self.process_elapsed = 0.0
        self.init_progress()
        self.start_time = time.time()

        image = image_loader(paths[0])
        time_intr1 = time.time()

        fov_deg = self.settings.get('fov_deg', 0.2)
        max_center_deg_delta = self.settings.get('max_center_deg_delta', None)

        # If there is no current mosaic then prepare a new one
        if new_mosaic or (self.img_mosaic is None):
            self.prepare_mosaic(image, fov_deg, name=name)

        elif max_center_deg_delta is not None:
            # get our center position
            ctr_x, ctr_y = self.img_mosaic.get_center()
            ra1_deg, dec1_deg = self.img_mosaic.pixtoradec(ctr_x, ctr_y)

            # get new image's center position
            ctr_x, ctr_y = image.get_center()
            ra2_deg, dec2_deg = image.pixtoradec(ctr_x, ctr_y)

            # distance between our center and new image's center
            dist = wcs.deltaStarsRaDecDeg(ra1_deg, dec1_deg,
                                          ra2_deg, dec2_deg)
            # if distance is greater than trip setting, start a new mosaic
            if dist > max_center_deg_delta:
                self.prepare_mosaic(image, fov_deg, name=name)

        self.update_status("Loading images...")
        #self.fv.gui_call(self.fv.error_wrap, self.ingest_one, image)
        #self.update_progress(float(self.ingest_count)/self.total_files)

        time_intr2 = time.time()
        self.process_elapsed += time_intr2 - time_intr1

        num_threads = self.settings.get('num_threads', 4)
        groups = dp.split_n(paths, num_threads)
        with self.lock:
            self.num_groups = len(groups)
        self.logger.info("num groups=%d" % (self.num_groups))

        for group in groups:
            self.fv.nongui_do(self.mosaic_some, group,
                              image_loader=image_loader)

        return self.img_mosaic

    def set_fov_cb(self, w):
        fov_deg = float(w.get_text())
        self.settings.set(fov_deg=fov_deg)
        self.w.fov.set_text(str(fov_deg))

    def trim_pixels_cb(self, w):
        trim_px = int(w.get_text())
        self.w.trim_px.set_text(str(trim_px))
        self.settings.set(trim_px=trim_px)

    def match_bg_cb(self, w, tf):
        self.settings.set(match_bg=tf)

    def merge_cb(self, w, tf):
        self.settings.set(merge=tf)

    def drop_new_cb(self, w, tf):
        self.settings.set(drop_creates_new_mosaic=tf)

    def mosaic_hdus_cb(self, w, tf):
        self.settings.set(mosaic_hdus=tf)

    def set_num_threads_cb(self, w):
        num_threads = int(w.get_text())
        self.w.num_threads.set_text(str(num_threads))
        self.settings.set(num_threads=num_threads)

    def update_status(self, text):
        if self.gui_up:
            self.fv.gui_do(self.w.eval_status.set_text, text)

    def init_progress(self):
        def _foo():
            self.w.btn_intr_eval.set_enabled(True)
            self.w.eval_pgs.set_value(0.0)
        if self.gui_up:
            self.fv.gui_do(_foo)

    def update_progress(self, pct):
        if self.gui_up:
            self.fv.gui_do(self.w.eval_pgs.set_value, pct)

    def end_progress(self):
        if self.gui_up:
            self.fv.gui_do(self.w.btn_intr_eval.set_enabled, False)

    def eval_intr(self):
        self.ev_intr.set()

    def __str__(self):
        return 'mosaic'


# Replace module docstring with config doc for auto insert by Sphinx.
# In the future, if we need the real docstring, we can append instead of
# overwrite.
from ginga.util.toolbox import generate_cfg_example
__doc__ = generate_cfg_example('plugin_Mosaic', package='ginga')

#END
