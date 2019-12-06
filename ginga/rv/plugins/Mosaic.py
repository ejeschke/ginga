# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Plugin to create image mosaic.

**Plugin Type: Local**

``Mosaic`` is a local plugin, which means it is associated with a
channel.  An instance can be opened for each channel.

**Usage**

This plugin is used to automatically create a mosaic in the channel using
images provided by the user (e.g., using ``FBrowser``).
The position of an image on the mosaic is determined by its WCS without
distortion correction. This is meant as a quick-look tool, not a
replacement for image drizzling that takes account of image distortion, etc.
The mosaic only exists as a plot on the Ginga canvas.

When a mosaic falls out of memory, it is no longer accessible in Ginga.
To avoid this, you must configure your session such that your Ginga data cache
is sufficiently large (see "Customizing Ginga" in the manual).

To create a new mosaic, set the FOV and drag files onto the display window.
Images must have a working WCS.

"""
import time
import threading

from ginga.AstroImage import AstroImage
from ginga.util import dp, io_fits
from ginga.util.mosaic import CanvasMosaicer
from ginga import GingaPlugin
from ginga.gw import Widgets


__all__ = ['Mosaic']


class Mosaic(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(Mosaic, self).__init__(fv, fitsimage)

        self.mosaicer = CanvasMosaicer(self.logger)
        self.mosaicer.add_callback('progress', self._plot_progress_cb)
        self.mosaicer.add_callback('finished', self._plot_finished_cb)

        self.ev_intr = threading.Event()
        self.lock = threading.RLock()
        # holds processed images to be inserted into mosaic image
        self.images = []
        self.ingest_count = 0
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
        canvas.ui_set_active(True, viewer=fitsimage)
        self.canvas = canvas
        self.layertag = 'mosaic-canvas'

        # Load plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Mosaic')
        self.settings.set_defaults(annotate_images=False,
                                   match_bg=False,
                                   num_threads=4,
                                   mosaic_hdus=False,
                                   make_thumbs=True)
        self.settings.load(onError='silent')

        # hook to allow special processing before inlining
        self.preprocess = lambda x: x

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("Mosaic")

        captions = [
            ("New Mosaic", 'button'),
            ("Mosaic HDUs", 'checkbutton', "Label images", 'checkbutton',
             "Match bg", 'checkbutton'),
            ("Num Threads:", 'label', 'Num Threads', 'llabel',
             'set_num_threads', 'entry'),
        ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.new_mosaic.add_callback('activated', lambda w: self.new_mosaic_cb())

        mosaic_hdus = self.settings.get('mosaic_hdus', False)
        b.mosaic_hdus.set_tooltip("Mosaic data HDUs in each file")
        b.mosaic_hdus.set_state(mosaic_hdus)
        b.mosaic_hdus.add_callback('activated', self.mosaic_hdus_cb)

        labelem = self.settings.get('annotate_images', False)
        b.label_images.set_state(labelem)
        b.label_images.set_tooltip("Label tiles with their names")
        b.label_images.add_callback('activated', self.annotate_cb)

        match_bg = self.settings.get('match_bg', False)
        b.match_bg.set_tooltip("Try to match background levels")
        b.match_bg.set_state(match_bg)
        b.match_bg.add_callback('activated', self.match_bg_cb)

        num_threads = self.settings.get('num_threads', 4)
        b.num_threads.set_text(str(num_threads))
        #b.set_num_threads.set_length(8)
        b.set_num_threads.set_text(str(num_threads))
        b.set_num_threads.set_tooltip("Number of threads to use for mosaicing")
        b.set_num_threads.add_callback('activated', self.set_num_threads_cb)

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

    def close(self):
        self.canvas.delete_all_objects()
        self.mosaicer.reset()
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
            self.mosaicer.prepare_mosaic(ref_image)
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
        self.fitsimage.clear()
        self.fitsimage.reset_limits()
        self.mosaicer.reset()
        self.fv.show_status("")

    def pause(self):
        # comment this to NOT disable the UI for this plugin
        # when it loses focus
        #self.canvas.ui_set_active(False)
        pass

    def resume(self):
        self.canvas.ui_set_active(True, viewer=self.fitsimage)

    def new_mosaic_cb(self):
        self.mosaicer.reset()
        self.canvas.delete_all_objects()
        self.fitsimage.clear()
        self.fitsimage.onscreen_message("Drag new files...",
                                        delay=2.0)

    def drop_cb(self, canvas, paths, *args):
        self.logger.info("files dropped: %s" % str(paths))
        self.fv.gui_do(self.fv.error_wrap, self.mosaic, paths)
        return True

    def annotate_cb(self, widget, tf):
        self.settings.set(annotate_images=tf)

    def load_tiles(self, paths, image_loader=None):
        # NOTE: this runs in a gui thread
        self.fv.assert_nongui_thread()

        if image_loader is None:
            image_loader = self.fv.load_image

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

                            image.set(name='hdu%d' % (i))

                            image = self.preprocess(image)

                            with self.lock:
                                self.images.append(image)

                    finally:
                        opener.close()
                        opener = None

                else:
                    image = image_loader(url)

                    image = self.preprocess(image)

                    with self.lock:
                        self.images.append(image)

                with self.lock:
                    self.ingest_count += 1
                    self.update_progress(self.ingest_count / self.total_files)

        finally:
            with self.lock:
                self.num_groups -= 1
                if self.num_groups <= 0:
                    self.fv.gui_do(self.finish_mosaic)

    def mosaic(self, paths, image_loader=None):
        if image_loader is None:
            image_loader = self.fv.load_image

        self.fv.assert_gui_thread()

        self.ingest_count = 0
        self.total_files = len(paths)
        if self.total_files == 0:
            return

        self.images = []
        self.ev_intr.clear()
        # Initialize progress bar
        self.update_status("Loading files...")
        self.init_progress()
        self.start_time = time.time()

        num_threads = self.settings.get('num_threads', 4)
        groups = dp.split_n(paths, num_threads)
        self.num_groups = len(groups)
        self.logger.info("num groups=%d" % (self.num_groups))

        for group in groups:
            self.fv.nongui_do(self.load_tiles, group,
                              image_loader=image_loader)

    def finish_mosaic(self):
        self.fv.assert_gui_thread()

        self.load_time = time.time() - self.start_time
        images, self.images = self.images, []
        self.logger.info("num images={}".format(len(images)))

        if self.ev_intr.is_set():
            self.update_status("mosaic cancelled!")
            self.end_progress()
            return

        self.w.eval_pgs.set_value(0.0)
        self.w.btn_intr_eval.set_enabled(False)

        # set options
        self.mosaicer.annotate = self.settings.get('annotate_images', False)
        self.mosaicer.match_bg = self.settings.get('match_bg', False)

        self.mosaicer.mosaic(self.fitsimage, images, canvas=self.canvas,)

    def match_bg_cb(self, w, tf):
        self.settings.set(match_bg=tf)

    def mosaic_hdus_cb(self, w, tf):
        self.settings.set(mosaic_hdus=tf)

    def set_num_threads_cb(self, w):
        num_threads = int(w.get_text())
        self.w.num_threads.set_text(str(num_threads))
        self.settings.set(num_threads=num_threads)

    def update_status(self, text):
        if self.gui_up:
            self.fv.gui_do(self.w.eval_status.set_text, text)
            self.fv.gui_do(self.fv.update_pending)

    def _plot_progress_cb(self, mosaicer, category, pct):
        self.w.eval_status.set_text(category + '...')
        self.w.eval_pgs.set_value(pct)

    def _plot_finished_cb(self, mosaicer, t_sec):
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
        def _foo():
            self.w.eval_pgs.set_value(pct)
        if self.gui_up:
            self.fv.gui_do(_foo)

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

# END
