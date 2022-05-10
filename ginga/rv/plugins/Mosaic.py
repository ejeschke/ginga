# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Plugin to create an image mosaic by constructing a composite image.

**Plugin Type: Local**

``Mosaic`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**

.. warning:: This can be very memory intensive.

This plugin is used to automatically build a mosaic image in the channel
using images provided by the user (e.g., using ``FBrowser``).
The position of an image on the mosaic is determined by its WCS without
distortion correction. This is meant as a quick-look tool, not a
replacement for image drizzling that takes account of image distortion, etc.
The mosaic only exists in memory but you can save it out to a
FITS file using ``SaveImage``.

When a mosaic falls out of memory, it is no longer accessible in Ginga.
To avoid this, you must configure your session such that your Ginga data cache
is sufficiently large (see "Customizing Ginga" in the manual).

To create a new mosaic, set the FOV and drag files onto the display window.
Images must have a working WCS.  The first image's WCS will be used to orient
the other tiles.

**Controls**

The "Method" control is used to choose a method for mosaicing the images in
the collage.  It has two values: 'simple' and 'warp':

- 'simple' will attempt to rotate and flip the images according to the WCS.
  It is a fast method, at the expense of accuracy.  It will not handle
  distortions near the edge of the field that should skew the image.
- 'warp' will use the WCS to completely move each pixel in the image
  according to the reference image's WCS.  This may leave empty pixels in
  the image that are filled in by sampling from surrounding pixels.
  This will be slower than the simple method, and the time increases
  linearly with the size of the images.

**Difference from `Collage` plugin**

- Allocates a single large array to hold all the mosaic contents
- Slower to build, but can be quicker to manipulate large resultant images
- Can save the mosaic as a new data file
- Fills in values between tiles with a fill value (can be `NaN`)

"""
import time
from datetime import datetime, timezone
import threading

import numpy as np

from ginga.AstroImage import AstroImage
from ginga.util import wcs, dp
from ginga.util.io import io_fits
from ginga.util.mosaic import ImageMosaicer
from ginga import GingaPlugin
from ginga.gw import Widgets


__all__ = ['Mosaic']


class Mosaic(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Mosaic, self).__init__(fv, fitsimage)

        # Load plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Mosaic')
        self.settings.set_defaults(annotate_images=False, fov_deg=0.2,
                                   match_bg=False, trim_px=0,
                                   merge=False, num_threads=4,
                                   drop_creates_new_mosaic=False,
                                   mosaic_hdus=False, skew_limit=0.1,
                                   allow_expand=True, expand_pad_deg=0.01,
                                   max_center_deg_delta=2.0,
                                   make_thumbs=True, reuse_image=False,
                                   warp_by_wcs=False, ann_fits_kwd=None)
        self.settings.load(onError='silent')

        self.mosaicer = ImageMosaicer(self.logger, settings=self.settings)
        self.mosaicer.add_callback('progress', self._mosaic_progress_cb)
        self.mosaicer.add_callback('finished', self._mosaic_finished_cb)

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
        self.ann_fits_kwd = self.settings.get('ann_fits_kwd', None)

        self.dc = self.fv.get_draw_classes()

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(False)
        canvas.add_callback('drag-drop', self.drop_cb)
        canvas.set_surface(fitsimage)
        #canvas.ui_set_active(True)
        self.canvas = canvas
        self.layertag = 'mosaic-canvas'

        # channel where mosaic should appear (default=ours)
        self.mosaic_chname = self.chname

        # hook to allow special processing before inlining
        self.preprocess = lambda x: x

        self.fv.add_callback('remove-image', self._remove_image_cb)

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         orientation=self.settings.get('orientation', None))
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("Mosaic")

        captions = [
            ("FOV (deg):", 'label', 'Fov', 'llabel', 'set_fov', 'entryset'),
            ("New Mosaic", 'button', "Method:", 'label', 'method', 'combobox'),
            ("Mosaic HDUs", 'checkbutton', "Label images", 'checkbutton',
             "Match bg", 'checkbutton'),
            ("Trim Pixels:", 'label', 'Trim Px', 'llabel',
             'trim_pixels', 'entryset'),
            ("Num Threads:", 'label', 'Num Threads', 'llabel',
             'set_num_threads', 'entryset'),
            ("Merge data", 'checkbutton', "Drop new", 'checkbutton',
             "Allow expansion", 'checkbutton'),
        ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        fov_deg = self.settings.get('fov_deg', 1.0)
        if np.isscalar(fov_deg):
            fov_str = str(fov_deg)
        else:
            x_fov, y_fov = fov_deg
            fov_str = str(x_fov) + ', ' + str(y_fov)
        #b.set_fov.set_length(8)
        b.fov.set_text(fov_str)
        b.set_fov.set_text(fov_str)
        b.set_fov.add_callback('activated', self.set_fov_cb)
        b.set_fov.set_tooltip("Set size of mosaic FOV (deg)")

        b.new_mosaic.add_callback('activated', lambda w: self.new_mosaic_cb())

        combobox = b.method
        options = ['simple', 'warp']
        for name in options:
            combobox.append_text(name)
        method = self.settings.get('mosaic_method', 'simple')
        combobox.set_text(method)
        combobox.add_callback('activated', self.set_mosaic_method_cb)
        combobox.set_tooltip("Choose mosaic method: %s" % ','.join(options))

        labelem = self.settings.get('annotate_images', False)
        b.label_images.set_state(labelem)
        b.label_images.set_tooltip(
            "Label tiles with their names (only if allow_expand=False)")
        b.label_images.add_callback('activated', self.annotate_cb)

        mosaic_hdus = self.settings.get('mosaic_hdus', False)
        b.mosaic_hdus.set_tooltip("Mosaic data HDUs in each file")
        b.mosaic_hdus.set_state(mosaic_hdus)
        b.mosaic_hdus.add_callback('activated', self.mosaic_hdus_cb)

        match_bg = self.settings.get('match_bg', False)
        b.match_bg.set_tooltip("Try to match background levels")
        b.match_bg.set_state(match_bg)
        b.match_bg.add_callback('activated', self.match_bg_cb)

        b.allow_expansion.set_tooltip("Allow image to expand the FOV")
        allow_expand = self.settings.get('allow_expand', True)
        b.allow_expansion.set_state(allow_expand)
        b.allow_expansion.add_callback('activated', self.allow_expand_cb)

        trim_px = self.settings.get('trim_px', 0)
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
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)
        self.gui_up = True

    def set_preprocess(self, fn):
        if fn is None:
            fn = lambda x: x  # noqa
        self.preprocess = fn

    def prepare_mosaic(self, ref_image, name=None):
        """Prepare a new (blank) mosaic image based on the pointing of
        the parameter image
        """
        old_mosaic = self.mosaicer.baseimage
        img_mosaic = self.mosaicer.prepare_mosaic(ref_image)

        if img_mosaic is not old_mosaic:
            if name is not None:
                img_mosaic.set(name=name)
            imname = img_mosaic.get('name', ref_image.get('name', "NoName"))
            self.logger.debug("mosaic name is '%s'" % (imname))

            # avoid making a thumbnail of this if seed image is also that way
            nothumb = not self.settings.get('make_thumbs', False)
            if nothumb:
                img_mosaic.set(nothumb=True)

            # image is not on disk, set indication for other plugins
            img_mosaic.set(path=None)

            self.img_mosaic = img_mosaic
            self.logger.info("adding mosaic image '%s' to channel" % (imname))
            self.fv.gui_call(self.fv.add_image, imname, img_mosaic,
                             chname=self.mosaic_chname)

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
        info = dict(time_modified=datetime.now(tz=timezone.utc),
                    reason_modified='Added {0}'.format(
            ','.join([im.get('name') for im in images])))
        self.fv.update_image_info(self.img_mosaic, info)

        # # annotate ingested image with its name?
        # if annotate and (not allow_expand):
        #     for i, image in enumerate(images):
        #         (xlo, ylo, xhi, yhi) = loc[i]
        #         header = image.get_header()
        #         if self.ann_fits_kwd is not None:
        #             imname = str(header[self.ann_fits_kwd])
        #         else:
        #             imname = image.get('name', 'noname')

        #         x, y = (xlo + xhi) / 2., (ylo + yhi) / 2.
        #         self.canvas.add(self.dc.Text(x, y, imname, color='red'),
        #                         redraw=False)

        time_intr2 = time.time()
        self.process_elapsed += time_intr2 - time_intr1

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        self.gui_up = False
        return True

    def start(self):
        # insert layer if it is not already
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.get_object_by_tag(self.layertag)

        except KeyError:
            # Add canvas layer
            p_canvas.add(self.canvas, tag=self.layertag)

        # image loaded in channel is used as initial reference image,
        # if there is one
        ref_image = self.fitsimage.get_image()
        if ref_image is not None:
            self.prepare_mosaic(ref_image)
        else:
            self.mosaicer.reset()

        self.resume()

    def stop(self):
        self.canvas.ui_set_active(False)
        p_canvas = self.fitsimage.get_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layertag)
        except Exception:
            pass
        # dereference potentially large mosaic image
        self.mosaicer.reset()
        self.fv.show_status("")

    def pause(self):
        # comment this to NOT disable the UI for this plugin
        # when it loses focus
        #self.canvas.ui_set_active(False)
        pass

    def resume(self):
        self.canvas.ui_set_active(True)

    def new_mosaic_cb(self):
        self.mosaicer.reset()
        self.fitsimage.clear()
        self.fitsimage.onscreen_message("Drag new files...",
                                        delay=2.0)

    def drop_cb(self, canvas, paths, *args):
        self.logger.info("files dropped: %s" % str(paths))
        new_mosaic = self.settings.get('drop_creates_new_mosaic', False)
        self.fv.gui_do(self.fv.error_wrap, self.mosaic, paths,
                       new_mosaic=new_mosaic)
        return True

    def annotate_cb(self, widget, tf):
        self.settings.set(annotate_images=tf)

    def allow_expand_cb(self, widget, tf):
        self.settings.set(allow_expand=tf)

    def load_tiles(self, paths, image_loader=None, preprocess=None):
        self.fv.assert_nongui_thread()

        if image_loader is None:
            image_loader = self.fv.load_image
        if preprocess is None:
            preprocess = self.preprocess

        try:
            for url in paths:
                if self.ev_intr.is_set():
                    break
                mosaic_hdus = self.settings.get('mosaic_hdus', False)
                if mosaic_hdus:
                    self.logger.debug("loading hdus")
                    opener = io_fits.get_fitsloader(logger=self.logger)
                    # User wants us to mosaic HDUs
                    opener.open_file(url, memmap=False)
                    try:
                        for i in range(len(opener)):
                            self.logger.debug("ingesting hdu #%d" % (i))
                            try:
                                image = opener.load_idx(i)

                            except Exception as e:
                                self.logger.error(
                                    "Failed to open HDU #%d: %s" % (i, str(e)))
                                continue

                            if not isinstance(image, AstroImage):
                                self.logger.debug(
                                    "HDU #%d is not an image; skipping..." % (i))
                                continue

                            data = image.get_data()
                            if data is None:
                                # skip blank data
                                continue

                            if image.ndim != 2:
                                # skip images without 2 dimensions
                                continue

                            wd, ht = image.get_size()
                            if wd == 0 or ht == 0:
                                # or size 0 in either dimension
                                continue

                            image.set(name='hdu%d' % (i))

                            if preprocess is not None:
                                image = preprocess(image)

                            with self.lock:
                                self.images.append(image)

                    finally:
                        opener.close()
                        opener = None

                else:
                    image = image_loader(url)

                    if preprocess is not None:
                        image = preprocess(image)

                    with self.lock:
                        self.images.append(image)

        finally:
            with self.lock:
                self.num_groups -= 1
                if self.num_groups <= 0:
                    images, self.images = self.images, []
                    self.fv.gui_do(self.finish_mosaic, images)

    def finish_mosaic(self, images):
        self.fv.assert_gui_thread()

        self.update_status("mosaicing images...")
        self.load_time = time.time() - self.start_time
        self.logger.info("num images={}".format(len(images)))

        if self.ev_intr.is_set():
            self.update_status("mosaicing cancelled!")
            self.end_progress()
            return

        self.w.eval_pgs.set_value(0.0)
        self.w.btn_intr_eval.set_enabled(False)

        self.fv.nongui_do(self.mosaicer.mosaic, images)

        # Add description for ChangeHistory
        info = dict(time_modified=datetime.utcnow(),
                    reason_modified='Added {0}'.format(
            ','.join([im.get('name') for im in images])))
        self.fv.update_image_info(self.mosaicer.baseimage, info)

        # annotate ingested image with its name?
        annotate = self.settings['annotate_images']
        if self.settings['annotate_images']:
            for image in images:
                wd, ht = image.get_size()
                ctr_x, ctr_y = wd * 0.5, ht * 0.5
                ctr_ra, ctr_dec = image.pixtoradec(ctr_x, ctr_y)
                if self.ann_fits_kwd is not None:
                    header = image.get_header()
                    imname = str(header[self.ann_fits_kwd])
                else:
                    imname = image.get('name', 'noname')

                self.canvas.add(self.dc.Text(ctr_ra, ctr_dec, imname,
                                             color='red', coord='wcs'),
                                redraw=False)

    def mosaic(self, paths, image_loader=None, preprocess=None,
               new_mosaic=False, name=None):
        """Mosaic images obtained by loading ``paths`` using optional
        ``image_loader`` and ``proprocess`` (post-load, pre-mosaic)
        functions.  A new mosaic is started if ``new_mosaic`` is True
        otherwise an existing mosaic is built on.
        """
        self.fv.assert_gui_thread()

        if image_loader is None:
            image_loader = self.fv.load_image

        if new_mosaic:
            self.mosaicer.reset()
            self.canvas.delete_all_objects()
            self.fitsimage.clear()

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

        max_center_deg_delta = self.settings.get('max_center_deg_delta', None)

        img_mosaic = self.mosaicer.baseimage
        # If there is no current mosaic then prepare a new one
        if new_mosaic or img_mosaic is None:
            img_mosaic = self.prepare_mosaic(image, name=name)

        elif max_center_deg_delta is not None:
            # get our center position
            ctr_x, ctr_y = img_mosaic.get_center()
            ra1_deg, dec1_deg = img_mosaic.pixtoradec(ctr_x, ctr_y)

            # get new image's center position
            ctr_x, ctr_y = image.get_center()
            ra2_deg, dec2_deg = image.pixtoradec(ctr_x, ctr_y)

            # distance between our center and new image's center
            dist = wcs.deltaStarsRaDecDeg(ra1_deg, dec1_deg,
                                          ra2_deg, dec2_deg)
            # if distance is greater than trip setting, start a new mosaic
            if dist > max_center_deg_delta:
                self.prepare_mosaic(image, name=name)

        self.update_status("Loading images...")

        time_intr2 = time.time()
        self.process_elapsed += time_intr2 - time_intr1

        num_threads = self.settings.get('num_threads', 4)
        groups = dp.split_n(paths, num_threads)
        with self.lock:
            self.num_groups = len(groups)
        self.logger.info("num groups=%d" % (self.num_groups))

        for group in groups:
            self.fv.nongui_do(self.load_tiles, group,
                              image_loader=image_loader, preprocess=preprocess)

    def set_fov_cb(self, w):
        fov_str = w.get_text()
        if ',' in fov_str:
            x_fov, y_fov = fov_str.split(',')
            x_fov, y_fov = float(x_fov), float(y_fov)
            fov_deg = (x_fov, y_fov)
            self.w.fov.set_text(str(x_fov) + ', ' + str(y_fov))
        else:
            fov_deg = float(fov_str)
            self.w.fov.set_text(str(fov_deg))
        self.settings.set(fov_deg=fov_deg)

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

    def set_mosaic_method_cb(self, w, idx):
        method = w.get_text()
        self.settings.set(mosaic_method=method)

    def set_num_threads_cb(self, w):
        num_threads = int(w.get_text())
        self.w.num_threads.set_text(str(num_threads))
        self.settings.set(num_threads=num_threads)

    def _remove_image_cb(self, fv, chname, imname, impath):
        # clear our handle to the mosaic image if it has been
        # deleted from the channel
        img_mosaic = self.mosaicer.baseimage
        if img_mosaic is not None:
            if imname == img_mosaic.get('name', None):
                self.mosaicer.reset()

    def update_status(self, text):
        if self.gui_up:
            self.fv.gui_do(self.w.eval_status.set_text, text)
            self.fv.gui_do(self.fv.update_pending)

    def _mosaic_progress_cb(self, mosaicer, category, pct):
        self.fv.gui_do(self.w.eval_status.set_text, category + '...')
        self.fv.gui_do(self.w.eval_pgs.set_value, pct)

    def _mosaic_finished_cb(self, mosaicer, t_sec):
        # a redraw shouldn't be necessary if the modified callback
        # is forcing a correct redraw at whence=0
        self.fv.gui_do(self.mosaicer.baseimage.make_callback, 'modified')

        total = self.load_time + t_sec
        msg = "done. load: %.4f mosaic: %.4f total: %.4f sec" % (
            self.load_time, t_sec, total)
        self.update_status(msg)

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


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Mosaic', package='ginga')
