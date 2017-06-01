#
# MultiDim.py -- Multidimensional plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import re
import os
from distutils import spawn
from contextlib import contextmanager

from ginga.gw import Widgets
from ginga.misc import Future
from ginga import GingaPlugin
from ginga.util.iohelper import get_hdu_suffix
from ginga.util.videosink import VideoSink
from ginga.table.AstroTable import AstroTable

import numpy as np

have_mencoder = False
if spawn.find_executable("mencoder"):
    have_mencoder = True


class MultiDim(GingaPlugin.LocalPlugin):
    """
    MultiDim
    ========
    A plugin to navigate HDUs in a FITS file or planes in a 3D cube or
    higher dimension dataset.

    Plugin Type: Local
    ------------------
    MultiDim is a local plugin, which means it is associated with a
    channel.  An instance can be opened for each channel.

    Browsing HDUs
    -------------
    Use the HDU drop down list in the upper part of the UI to browse and
    select an HDU to open in the channel.

    Navigating Cubes
    ----------------
    Use the controls in the lower part of the UI to select the axis and
    to step through the planes in that axis.
    """
    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(MultiDim, self).__init__(fv, fitsimage)

        self.curhdu = 0
        self.naxispath = []
        self.name_pfx = 'NONAME'
        self.img_path = None
        self.img_name = None
        self.file_obj = None
        self.orientation = 'vertical'

        # For animation feature
        self.play_image = None
        self.play_axis = 2
        self.play_idx = 1
        self.play_max = 1
        self.play_int_sec = 0.1
        self.play_min_sec = 1.0 / 30
        self.play_last_time = 0.0
        self.play_fps = 0
        self.timer = fv.get_timer()
        self.timer.set_callback('expired', self._play_next_cb)

        # Load plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_MultiDim')
        self.settings.set_defaults(auto_start_naxis=False)
        self.settings.load(onError='silent')

        self.gui_up = False

    def build_gui(self, container):
        top = Widgets.VBox()
        top.set_border_width(4)

        vbox, sw, orientation = Widgets.get_oriented_box(container,
                                                         scrolled=True)
        self.orientation = orientation
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        fr = Widgets.Frame("HDU")

        vb1 = Widgets.VBox()
        captions = [("Num HDUs:", 'label', "Num HDUs", 'llabel'),
                    ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.numhdu = b.num_hdus
        self.w.update(b)
        vb1.add_widget(w)

        captions = [("Choose HDU", 'combobox'),
                    ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        vb1.add_widget(w)

        self.w.hdu = b.choose_hdu
        self.w.hdu.set_tooltip("Choose which HDU to view")
        self.w.hdu.add_callback('activated', self.set_hdu_cb)

        fr.set_widget(vb1)
        vbox.add_widget(fr, stretch=0)

        fr = Widgets.Frame("NAXIS (data cubes)")
        self.naxisfr = fr
        vbox.add_widget(fr, stretch=0)

        tbar = Widgets.Toolbar(orientation='horizontal')
        for name, actn, cb in (
                ('first', 'first', lambda w: self.first_slice()),
                ('last', 'last', lambda w: self.last_slice()),
                ('reverse', 'prev', lambda w: self.prev_slice()),
                ('forward', 'next', lambda w: self.next_slice()),
                ('play', 'play', lambda w: self.play_start()),
                ('stop', 'stop', lambda w: self.play_stop()), ):
            iconpath = os.path.join(self.fv.iconpath, "%s_48.png" % name)
            btn = tbar.add_action(None, iconpath=iconpath)
            self.w[actn] = btn
            btn.set_enabled(False)
            btn.set_tooltip(actn)
            btn.add_callback('activated', cb)
        vbox.add_widget(tbar, stretch=0)

        captions = [("Interval:", 'label', "Interval", 'spinfloat',
                     "fps", 'llabel'),
                    ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        lower, upper = self.play_min_sec, 8.0
        b.interval.set_limits(lower, upper, incr_value=0.01)
        b.interval.set_value(self.play_int_sec)
        b.interval.set_decimals(2)
        b.interval.add_callback('value-changed', self.play_int_cb)

        b.interval.set_enabled(False)
        vbox.add_widget(w, stretch=0)

        captions = [("Slice:", 'label', "Slice", 'llabel'),
                    # ("Value:", 'label', "Value", 'llabel'),
                    ("Save Slice", 'button'),
                    ]
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.save_slice.add_callback('activated', lambda w: self.save_slice_cb())
        b.save_slice.set_enabled(False)
        b.save_slice.set_tooltip("Save current slice as RGB image")
        vbox.add_widget(w, stretch=0)

        fr = Widgets.Frame("Movie")
        if have_mencoder:
            captions = [("Start:", 'label', "Start Slice", 'entry',
                         "End:", 'label', "End Slice", 'entry',
                         'Save Movie', 'button')]
            w, b = Widgets.build_info(captions, orientation=orientation)
            self.w.update(b)
            b.start_slice.set_tooltip("Starting slice")
            b.end_slice.set_tooltip("Ending slice")
            b.start_slice.set_length(6)
            b.end_slice.set_length(6)
            b.save_movie.add_callback(
                'activated', lambda w: self.save_movie_cb())
            b.save_movie.set_enabled(False)
            fr.set_widget(w)
        else:
            infolbl = Widgets.Label()
            infolbl.set_text("Please install 'mencoder' to save as movie")
            fr.set_widget(infolbl)
        vbox.add_widget(fr, stretch=0)

        # spacer = Widgets.Label('')
        # vbox.add_widget(spacer, stretch=1)

        top.add_widget(sw, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        top.add_widget(btns, stretch=0)

        container.add_widget(top, stretch=1)

        self.gui_up = True

    def set_hdu_cb(self, w, val):
        # idx = int(val)
        idx = w.get_index()
        idx = max(0, idx)
        try:
            self.set_hdu(idx)

        except Exception as e:
            self.logger.error("Error loading HDU #%d: %s" % (
                idx+1, str(e)))

    def set_naxis_cb(self, w, idx, n):
        # idx = int(w.get_value()) - 1
        self.set_naxis(idx, n)
        # schedule a redraw
        self.fitsimage.redraw(whence=0)

    def build_naxis(self, dims, image):
        imname = image.get('name')
        self.naxispath = list(image.naxispath)

        # build a vbox of NAXIS controls
        captions = [("NAXIS1:", 'label', 'NAXIS1', 'llabel'),
                    ("NAXIS2:", 'label', 'NAXIS2', 'llabel')]

        for n in range(2, len(dims)):
            key = 'naxis%d' % (n+1)
            title = key.upper()
            maxn = int(dims[n])
            self.logger.debug("NAXIS%d=%d" % (n+1, maxn))
            if maxn <= 1:
                captions.append((title+':', 'label', title, 'llabel'))
            else:
                captions.append((title+':', 'label', title, 'llabel',
                                # "Choose %s" % (title), 'spinbutton'))
                                 "Choose %s" % (title), 'hscale'))

        if len(dims) > 3:  # only add radiobuttons if we have more than 3 dim
            radiobuttons = []
            for i in range(2, len(dims)):
                title = 'AXIS%d' % (i+1)
                radiobuttons.extend((title, 'radiobutton'))
            captions.append(radiobuttons)

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
            slkey = 'choose_' + key
            if slkey in b:
                slider = b[slkey]
                lower = 1
                upper = maxn
                slider.set_limits(lower, upper, incr_value=1)
                text = self.naxispath[n - 2] + 1
                if np.isscalar(text):
                    slider.set_value(text)
                else:
                    slider.set_value(text[n - 2])

                slider.set_tracking(True)
                # slider.set_digits(0)
                # slider.set_wrap(True)
                slider.add_callback('value-changed', self.set_naxis_cb, n)
            # Disable playback if there is only 1 slice in the higher dimension
            if n > 2 and dims[n] == 1:
                radiobutton = b['axis%d' % (n+1)]
                radiobutton.set_enabled(False)

        # Add vbox of naxis controls to gui
        self.naxisfr.set_widget(w)

        # for storing play_idx for each dim of image. used for going back to
        # the idx where you left off.
        self.play_indices = ([0 for i in range(len(dims) - 2)] if len(dims) > 3
                             else None)

        if len(dims) > 3:

            # dims only exists in here, hence this function exists here
            def play_axis_change_func_creator(n):
                # widget callable needs (widget, value) args
                def play_axis_change():

                    self.play_indices[self.play_axis - 2] = (self.play_idx - 1) % dims[self.play_axis]  # noqa

                    self.play_axis = n
                    self.logger.debug("play_axis changed to %d" % n)

                    if self.play_axis < len(dims):
                        self.play_max = dims[self.play_axis]

                    self.play_idx = self.play_indices[n - 2]

                def check_if_we_need_change(w, v):
                    if self.play_axis is not n:
                        play_axis_change()

                return check_if_we_need_change

            for n in range(2, len(dims)):
                key = 'axis%d' % (n + 1)
                self.w[key].add_callback(
                    'activated', play_axis_change_func_creator(n))
                if n == 2:
                    self.w[key].set_state(True)

        is_dc = len(dims) > 2
        self.play_axis = 2
        if self.play_axis < len(dims):
            self.play_max = dims[self.play_axis]
        if is_dc:
            self.play_idx = self.naxispath[self.play_axis - 2] + 1
        else:
            self.play_idx = 1
        if self.play_indices:
            text = [i + 1 for i in self.naxispath]
        else:
            text = self.play_idx
        self.w.slice.set_text(str(text))

        # Enable or disable NAXIS animation controls
        self.w.next.set_enabled(is_dc)
        self.w.prev.set_enabled(is_dc)
        self.w.first.set_enabled(is_dc)
        self.w.last.set_enabled(is_dc)
        self.w.play.set_enabled(is_dc)
        self.w.stop.set_enabled(is_dc)
        self.w.interval.set_enabled(is_dc)

        self.w.save_slice.set_enabled(is_dc)
        if have_mencoder:
            self.w.save_movie.set_enabled(is_dc)

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        self.resume()

    def pause(self):
        self.play_stop()
        pass

    def resume(self):
        self.redo()

    def stop(self):
        self.gui_up = False
        self.play_stop()
        try:
            self.file_obj.close()
        except:
            pass
        self.file_obj = None
        self.img_path = None
        self.img_name = None
        self.fv.show_status("")

    def set_hdu(self, idx):
        self.logger.debug("Loading fits hdu #%d" % (idx))

        # determine canonical index of this HDU
        info = self.file_obj.hdu_info[idx]
        aidx = (info.name, info.extver)
        if aidx not in self.file_obj.hdu_db:
            aidx = idx
        sfx = get_hdu_suffix(aidx)

        # See if this HDU is still in the channel's datasrc
        imname = self.name_pfx + sfx
        chname = self.chname
        chinfo = self.channel
        if imname in chinfo.datasrc:
            self.curhdu = idx
            image = chinfo.datasrc[imname]
            self.fv.switch_name(chname, imname)

            return

        # Nope, we'll have to load it
        self.logger.debug("HDU %d not in memory; refreshing from file" % (idx))
        try:
            self.curhdu = idx
            dims = [0, 0]
            info = self.file_obj.hdu_info[idx]

            image = self.file_obj.get_hdu(idx)

            # create a future for reconstituting this HDU
            future = Future.Future()
            future.freeze(self.fv.load_image, self.img_path, idx=aidx)
            image.set(path=self.img_path, idx=aidx, name=imname,
                      image_future=future)

            self.fv.add_image(imname, image, chname=chname)

            self.logger.debug("HDU #%d loaded." % (idx))

        except Exception as e:
            errmsg = "Error loading FITS HDU #%d: %s" % (
                idx, str(e))
            self.logger.error(errmsg)
            self.fv.show_error(errmsg, raisetab=True)

    def set_naxis(self, idx, n):
        self.play_idx = idx
        idx = idx - 1
        self.logger.debug("naxis %d index is %d" % (n+1, idx+1))

        image = self.fitsimage.get_image()
        slidername = 'choose_naxis%d' % (n+1)
        try:
            if image is None:
                raise ValueError("Please load an image cube")

            m = n - 2

            self.naxispath[m] = idx
            self.logger.debug("m=%d naxispath=%s" % (m, str(self.naxispath)))

            image.set_naxispath(self.naxispath)
            self.logger.debug("NAXIS%d slice %d loaded." % (n+1, idx+1))

            if self.play_indices:
                self.play_indices[m] = idx
                text = [i + 1 for i in self.naxispath]
                if slidername in self.w:
                    self.w[slidername].set_value(text[m])
            else:
                text = idx + 1
                if slidername in self.w:
                    self.w[slidername].set_value(text)
            self.w.slice.set_text(str(text))

        except Exception as e:
            errmsg = "Error loading NAXIS%d slice %d: %s" % (
                n+1, idx+1, str(e))
            self.logger.error(errmsg)
            self.fv.error(errmsg)

    def play_start(self):
        image = self.fitsimage.get_image()
        if image is None:
            return
        self.play_image = image
        self._isplaying = True
        image.block_callback('modified')
        self.play_last_time = time.time()
        self.play_next(self.timer)

    def _play_next_cb(self, timer):
        # this is the playback timer callback
        # timer is run in a non-gui thread
        self.fv.gui_do(self.play_next, timer)

    def play_next(self, timer):
        if not self._isplaying:
            # callback after user stopped playback
            return

        image = self.fitsimage.get_image()
        if image is None:
            self.play_stop()
            return

        time_start = time.time()
        deadline = time_start + self.play_int_sec

        # calculate fps
        fps = 1.0 / (time_start - self.play_last_time)
        self.play_last_time = time_start
        if int(fps) != int(self.play_fps):
            self.play_fps = fps
            self.w.fps.set_text(str("%.2f fps" % fps))

        self.next_slice()

        # set timer for next turnaround
        delta = deadline - time.time()
        timer.set(max(delta, 0.001))

    def play_stop(self):
        self._isplaying = False
        if self.play_image is not None:
            self.play_image.unblock_callback('modified')
            self.play_image = None

    def first_slice(self):
        play_idx = 1
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def last_slice(self):
        play_idx = self.play_max
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def prev_slice(self):
        if np.isscalar(self.play_idx):
            play_idx = self.play_idx - 1
        else:
            m = self.play_axis - 2
            play_idx = self.play_idx[m] - 1
        if play_idx < 1:
            play_idx = self.play_max
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def next_slice(self):
        if np.isscalar(self.play_idx):
            play_idx = self.play_idx + 1
        else:
            m = self.play_axis - 2
            play_idx = self.play_idx[m] + 1
        if play_idx > self.play_max:
            play_idx = 1
        self.fv.gui_do(self.set_naxis_cb, None, play_idx, self.play_axis)

    def play_int_cb(self, w, val):
        # force at least play_min_sec, otherwise playback is untenable
        self.play_int_sec = max(self.play_min_sec, val)

    def prep_hdu_menu(self, w, hdu_info):
        # clear old TOC
        w.clear()

        for idx, d in enumerate(hdu_info):

            toc_ent = "%(index)4d %(name)-12.12s (%(extver)3d) %(htype)-12.12s %(dtype)-8.8s" % d  # noqa
            w.append_text(toc_ent)

        idx = w.get_index()
        if idx < 0:
            idx = 0
        if idx >= len(hdu_info):
            idx = len(hdu_info) - 1
        # w.set_index(idx)

    def redo(self):
        """Called when an image is set in the channel."""
        image = self.channel.get_current_image()
        if image is None:
            return True

        path = image.get('path', None)
        if path is None:
            self.fv.show_error(
                "Cannot open image: no value for metadata key 'path'")
            return

        if path != self.img_path:
            # <-- New file is being looked at
            self.img_path = path

            self.file_obj = self.fv.fits_opener.get_factory()
            # TODO: specify 'readonly' somehow?
            self.file_obj.open_file(path)

            upper = len(self.file_obj) - 1
            self.prep_hdu_menu(self.w.hdu, self.file_obj.hdu_info)
            self.num_hdu = upper
            self.logger.debug("there are %d hdus" % (upper+1))
            self.w.numhdu.set_text("%d" % (upper+1))

            self.w.hdu.set_enabled(len(self.file_obj) > 0)

        name = image.get('name', self.fv.name_image_from_path(path))
        idx = image.get('idx', None)
        # remove index designation from root of name, if any
        match = re.match(r'^(.+)\[(.+)\]$', name)
        if match:
            name = match.group(1)
        self.name_pfx = name

        if idx is not None:
            # set the HDU in the drop down if known
            info = self.file_obj.hdu_db.get(idx, None)
            if info is not None:
                index = info.index
                self.w.hdu.set_index(index)

        # rebuild the NAXIS controls, if necessary
        # No two images in the same channel can have the same name.
        # Here we keep track of the name to decide if we need to rebuild
        if self.img_name != name:
            self.img_name = name
            dims = [0, 0]
            data = image.get_data()
            if data is None:
                # <- empty data part to this HDU
                self.logger.warning("Empty data part in HDU #%d" % (idx))

            elif info.htype.lower() in ('bintablehdu', 'tablehdu',):
                pass

            elif info.htype.lower() not in ('imagehdu', 'primaryhdu'):
                self.logger.warning("HDU #%d is not an image" % (idx))

            else:
                mddata = image.get_mddata()
                if mddata is not None:
                    dims = list(mddata.shape)
                    dims.reverse()

            self.build_naxis(dims, image)

    def save_slice_cb(self):
        import matplotlib.pyplot as plt

        w = Widgets.SaveDialog(title='Save slice',
                               selectedfilter='*.png')
        target = w.get_path()
        if target is None:
            # save canceled
            return

        with open(target, 'w') as target_file:
            hival = self.fitsimage.get_cut_levels()[1]
            image = self.fitsimage.get_image()
            curr_slice_data = image.get_data()

            plt.imsave(target_file, curr_slice_data, vmax=hival,
                       cmap=plt.get_cmap('gray'), origin='lower')
            self.fv.show_status("Successfully saved slice")

    def save_movie_cb(self):
        start = int(self.w.start_slice.get_text())
        end = int(self.w.end_slice.get_text())
        if not start or not end:
            return
        elif start < 0 or end > self.play_max:
            self.fv.show_status("Wrong slice index")
            return
        elif start > end:
            self.fv.show_status("Wrong slice order")
            return

        if start == 1:
            start = 0

        w = Widgets.SaveDialog(title='Save Movie',
                               selectedfilter='*.avi')
        target = w.get_path()
        if target is not None:
            self.save_movie(start, end, target)

    def save_movie(self, start, end, target_file):
        image = self.fitsimage.get_image()
        loval, hival = self.fitsimage.get_cut_levels()
        data = np.array(image.get_mddata()).clip(loval, hival)

        # http://stackoverflow.com/questions/7042190/plotting-directly-to-movie-with-numpy-and-mencoder
        data_rescaled = ((data - loval) * 255 / (hival - loval)).astype(
            np.uint8, copy=False)

        W, H = image.get_data_size()
        with self.video_writer(VideoSink((H, W), target_file)) as video:
            for i in range(start, end):
                video.write(np.flipud(data_rescaled[i]))

        self.fv.show_status("Successfully saved movie")

    @contextmanager
    def video_writer(self, v):
        v.open()
        try:
            yield v
        finally:
            v.close()
        return

    def __str__(self):
        return 'multidim'


# Replace module docstring with config doc for auto insert by Sphinx.
# In the future, if we need the real docstring, we can append instead of
# overwrite.
from ginga.util.toolbox import generate_cfg_example  # noqa
__doc__ = generate_cfg_example('plugin_MultiDim', package='ginga')
