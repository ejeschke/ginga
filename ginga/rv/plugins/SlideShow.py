# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Play a slide show of images.

**Plugin Type: Local**

``SlideShow`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

**Usage**

***Loading a slideshow***

After starting the plugin, you can use the "Load" button to load a slideshow
(see below for slideshow file format).  You can then reload this slideshow
after externally editing the file at any time by pressing "Reload".

***Playing a slideshow***

The "Prev" and "Next" buttons can be used to go backward and forward manually
within the list.  The spin button control between these two buttons will
advance you to a particular slide within the list.

The "Start" and "Stop" buttons are used to start or stop the automatic
advancement within the slideshow.

***Controlling the duration***

Each slide can have a separate "duration" parameter (in seconds) to control
how long before advancing to the next slide, but if this is missing for a
slide the default duration is used.  The default duration can be set using
the control marked "Default duration".

Below the default duration control is a label that shows the duration
of the slide and the total duration of the show.

**Slide show file format**

The slide show file format is a comma-separated (CSV) plain text file with a
header line.  The file must contain at least one column, titled "file".
This column contains the filenames (relative or absolute) of the paths to
the files to be loaded for each slide.

***Optional columns***

* "duration":  should contain the duration (in seconds) for each slide
* "position": indicates the position of the slide in the show.
  Floating point numbers can be used to make it easier to reorder the
  slides when editing the slideshow file.

"""
# STDLIB
import os
from datetime import timedelta
import time
import tempfile

import pandas as pd
import yaml

# GINGA
from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets
from ginga.pilw.ImageViewPil import CanvasView
from ginga.util import loader
from ginga.util.paths import icondir

__all__ = ['SlideShow']


class SlideShow(LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(SlideShow, self).__init__(fv, fitsimage)

        # User preferences. Some are just default values and can also be
        # changed by GUI.
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_SlideShow')
        self.settings.add_defaults(default_duration=5.0)
        self.settings.load(onError='silent')

        self.timer = self.fv.make_timer()
        self.timer.add_callback('expired', self.timer_cb)

        self.slideshow = []
        self.index = 0
        self.def_duration = self.settings.get('default_duration', 5.0)

        self.dc = self.fv.get_draw_classes()
        canvas = self.dc.DrawingCanvas()
        canvas.set_surface(self.fitsimage)
        canvas.add_callback('drag-drop', self.drop_cb)
        self.canvas = canvas

        # Build our thumb generator
        self.thumb_width = 180
        self.tg = self.get_thumb_generator()
        self.tg.name = 'slideshow-thumb-generator'
        self._genthumb = fitsimage.get_settings().get('genthumb', True)

        self.cover = self.dc.Polygon([(0, 0), (0, 0), (0, 0), (0, 0)],
                                     fill=True, fillcolor='brown',
                                     fillalpha=0.75, coord='window')
        self.gui_up = False

    def build_gui(self, container):
        """Build GUI such that image list area is maximized."""

        vbox = Widgets.VBox()

        captions = (('Load', 'button', 'path', 'textentry',
                     'Reload', 'button'),
                    ('Save As', 'button', 'save_path', 'textentry'),
                    ('Default duration:', 'llabel', 'default_duration', 'textentryset'),
                    ('Duration:', 'llabel', 'duration', 'label',
                     'Total:', 'llabel', 'total', 'label'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.load.set_tooltip('Load a slideshow file')
        b.load.add_callback('activated', self._popup_load_dialog_cb)
        b.path.set_tooltip('Path for slideshow file')
        b.path.add_callback('activated', self.load_slideshow_cb)
        b.reload.set_tooltip('Reload slideshow file')
        b.reload.add_callback('activated', self.load_slideshow_cb)
        b.save_as.add_callback('activated', self.save_slideshow_cb)

        b.default_duration.add_callback('activated', self.set_duration_cb)
        b.default_duration.set_text(str(self.def_duration))
        b.default_duration.set_tooltip("Set the default duration if none found for a slide")

        self.w.fs = Widgets.FileDialog(parent=b.load, title='Load slide show')
        self.w.fs.set_mode('file')
        self.w.fs.add_callback('activated', self._load_slideshow_file)

        vbox2 = Widgets.VBox()
        vbox2.add_widget(w, stretch=0)
        self.w.load_progress = Widgets.ProgressBar()
        vbox2.add_widget(self.w.load_progress, stretch=0)

        fr = Widgets.Frame("Load")
        fr.set_widget(vbox2)
        vbox.add_widget(fr, stretch=0)

        captions = (('Prev', 'button', 'Slide', 'spinbox', 'Next', 'button'),
                    ('Start', 'button', 'filename', 'textentry', 'Stop', 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.prev.add_callback('activated', self.prev_slide_cb)
        b.slide.add_callback('value-changed', self.set_slide_cb)
        b.next.add_callback('activated', self.next_slide_cb)

        b.start.add_callback('activated', self.start_slideshow_cb)
        b.stop.add_callback('activated', self.stop_slideshow_cb)
        b.filename.set_editable(False)

        fr = Widgets.Frame("Play")
        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        captions = (('Move Up', 'button', 'sp1', 'spacer', 'Move Down', 'button'),
                    ('Get Index', 'button', 'ins_index', 'spinbox', 'Move To', 'button'),
                    ('Hide', 'button', 'Unhide', 'button', 'Delete', 'button'),)
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.move_up.add_callback('activated', self.edit_move_up_cb)
        b.move_down.add_callback('activated', self.edit_move_down_cb)
        b.get_index.add_callback('activated', self.edit_get_index_cb)
        b.move_to.add_callback('activated', self.edit_move_to_cb)
        b.hide.add_callback('activated', self.edit_hide_cb)
        b.unhide.add_callback('activated', self.edit_unhide_cb)
        b.delete.add_callback('activated', self.edit_delete_cb)

        fr = Widgets.Frame("Edit")
        fr.set_widget(w)
        vbox.add_widget(fr, stretch=0)

        # holds the slides
        self.w.grid = Widgets.GridBox()
        self.w.grid.set_row_spacing(2)
        sw = Widgets.ScrollArea()
        sw.set_widget(self.w.grid)
        vbox.add_widget(sw, stretch=1)

        container.add_widget(vbox, stretch=0)

        #container.add_widget(Widgets.Label(''), stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        container.add_widget(btns, stretch=0)

        self.gui_up = True

    def _popup_load_dialog_cb(self, w):
        self.w.fs.popup()

    def _load_slideshow_file(self, w, paths):
        path = paths[0]
        self.w.path.set_text(path)
        self.load_slideshow(path)

    def load_slideshow_cb(self, w):
        path = self.w.path.get_text()
        self.load_slideshow(path)

    def get_thumbnail(self, path, slide_d, menu=None):
        tmp_filename = os.path.join(tempfile.gettempdir(), "thumb.png")
        full_image = loader.load_data(path, idx=0, logger=self.logger)
        image_name = "img-{}".format(str(time.time()))
        slide_d['name'] = image_name
        full_image.set(name=image_name, nothumb=True)
        self.tg.set_image(full_image)
        thumb_bytes = self.tg.get_rgb_image_as_bytes(format='png')
        with open(tmp_filename, 'wb') as out_f:
            out_f.write(thumb_bytes)
        image = Widgets.Image(style='clickable', menu=menu)
        image.load_file(tmp_filename)
        image.add_callback('activated', self.goto_slide_cb, slide_d)
        self.channel.add_image(full_image, silent=True)
        return full_image, image

    def load_slideshow(self, path):
        slide_dir, fname = os.path.split(path)
        _, ext = os.path.splitext(fname)
        ext = ext.lower()
        try:
            if ext in ['.yml', '.yaml']:
                with open(path, 'r') as in_f:
                    buf = in_f.read()
                contents = yaml.safe_load(buf)
                slideshow = contents['slideshow']['slides']
            elif ext in ['.csv']:
                df = pd.read_csv(path, skip_blank_lines=True, comment='#')
                slideshow = df.to_dict(orient='records')
            else:
                self.fv.show_error(f"Don't recognize format '{ext}'")
                return
        except Exception as e:
            errmsg = f"Error loading slide show: {e}"
            self.fv.show_error(errmsg)
            self.logger.error(errmsg, exc_info=True)
            return

        self.w.grid.remove_all(delete=True)
        self.w.load_progress.set_value(0.0)
        # TODO: have a custom error slide
        error_fname = os.path.join(icondir, 'ginga-512x512.png')

        for row, slide_d in enumerate(slideshow):
            # append slide directory to filename if a full
            # path is not given
            fname = slide_d['file']
            if not fname.startswith('/'):
                fname = os.path.join(slide_dir, fname)
                slide_d['file'] = fname

            try:
                image, image_w = self.get_thumbnail(fname, slide_d)
            except Exception as e:
                errmsg = f"Error loading slide #{row} ({fname}): {e}"
                self.fv.show_error(errmsg)
                self.logger.error(errmsg, exc_info=True)
                # TODO: show an error slide
                try:
                    slide_d['file'] = error_fname
                    image, image_w = self.get_thumbnail(error_fname, slide_d)
                except Exception as e:
                    continue

            self.w.grid.add_widget(image_w, row, 0)

            # if 'duration' not in slide_d:
            #     slide_d['duration'] = None
            # if 'position' not in slide_d:
            #     slide_d['position'] = index
            # if 'hide' not in slide_d:
            #     slide_d['hide'] = False

            self.w.load_progress.set_value(row / len(slideshow))
            self.fv.update_pending(0.001)

        self.w.load_progress.set_value(1.0)
        self.slideshow = slideshow
        self.w.slide.set_limits(0, len(self.slideshow) - 1, incr_value=1)
        self.w.slide.set_value(0)

        self.update_duration()
        self.w.save_path.set_text(path)

        self.w.ins_index.set_limits(0, len(self.slideshow))
        self.w.ins_index.set_value(0)

        self.show_slide(self.index, set_timer=False)

    def update_duration(self):
        duration = sum(float(d.get('duration', self.def_duration))
                       for d in self.slideshow)
        delta = timedelta(seconds=duration)
        self.w.duration.set_text(str(delta))
        self.w.total.set_text(str(len(self.slideshow)))

    def save_slideshow_cb(self, w):
        save_path = self.w.save_path.get_text().strip()
        df = pd.DataFrame(self.slideshow)
        df.to_csv(save_path, index=False)

    def start_slideshow_cb(self, w):
        self.show_slide(self.index, set_timer=True)

    def stop_slideshow_cb(self, w):
        self.timer.cancel()

    def show_slide(self, index, set_timer=False):
        slide_d = self.slideshow[index]

        # image = slide_d.get('image', None)
        # if image is None:
        #     image = loader.load_data(slide_d['file'], logger=self.logger)
        #     slide_d['image'] = image

        self.w.slide.set_value(index)
        _dir, fname = os.path.split(slide_d['file'])
        self.w.filename.set_text(fname)

        hidden = slide_d.get('hide', False)
        if set_timer:
            if hidden:
                duration = 0.1
            else:
                duration = slide_d.get('duration', self.def_duration)
            self.timer.set(duration)

        if hidden:
            wd, ht = self.fitsimage.get_window_size()
            self.cover.points = [(0, 0), (wd, 0), (wd, ht), (0, ht)]
            if self.cover not in self.canvas:
                self.canvas.add(self.cover, tag='cover')
        else:
            if self.cover in self.canvas:
                self.canvas.delete_object_by_tag('cover')

        self.channel.switch_name(slide_d['name'])

    def timer_cb(self, timer):
        self.index += 1
        if self.index >= len(self.slideshow):
            return

        self.show_slide(self.index, set_timer=True)

    def set_slide_cb(self, w, idx):
        self.index = idx
        self.show_slide(self.index)

    def goto_slide_cb(self, w, slide_d):
        idx = self.slideshow.index(slide_d)
        self.index = idx
        self.show_slide(self.index)

    def prev_slide_cb(self, w):
        if self.index <= 0:
            self.fitsimage.onscreen_message("START OF SLIDE SHOW", delay=2.0)
            return

        self.index = max(self.index - 1, 0)
        self.show_slide(self.index)

    def next_slide_cb(self, w):
        if self.index + 1 >= len(self.slideshow):
            self.fitsimage.onscreen_message("END OF SLIDE SHOW", delay=2.0)
            return

        self.index = min(self.index + 1, len(self.slideshow))
        self.show_slide(self.index)

    def set_duration_cb(self, w):
        duration = float(w.get_text())
        self.def_duration = duration
        self.update_duration()

    def drop_cb(self, canvas, uris):
        self.w.load_progress.set_value(0.0)
        for i, uri in enumerate(uris):
            self.add_slide(uri)

            self.w.load_progress.set_value(i / len(uris))
            self.fv.update_pending(0.001)
        self.w.load_progress.set_value(1.0)
        return True

    def redo(self):
        pass

    def close(self):
        chname = self.fv.get_channel_name(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))

    def start(self):
        # insert canvas, if not already
        p_canvas = self.fitsimage.get_canvas()
        if self.canvas not in p_canvas:
            p_canvas.add(self.canvas, tag='slideshow')
        self.resume()

        # record state of creating thumbnails for this channel
        # and turn it off
        t_ = self.fitsimage.get_settings()
        self._genthumb = t_.get('genthumb', True)
        t_.set(genthumb=False)

    def pause(self):
        self.canvas.ui_set_active(False)

    def resume(self):
        self.canvas.ui_set_active(True)
        # turn off any mode user may be in
        try:
            self.modes_off()
        except AttributeError:
            pass
        self.fv.show_status('Press "Help" for instructions')

    def stop(self):
        self.pause()
        self.gui_up = False
        p_canvas = self.fitsimage.get_canvas()
        if self.canvas in p_canvas:
            p_canvas.delete_object_by_tag('slideshow')
        t_ = self.fitsimage.get_settings()
        t_.set(genthumb=self._genthumb)
        self.fv.show_status('')

    def swap_slides(self, from_idx, to_idx):
        assert 0 <= from_idx < len(self.slideshow)
        assert 0 <= to_idx < len(self.slideshow)

        self.slideshow[from_idx], self.slideshow[to_idx] = \
            self.slideshow[to_idx], self.slideshow[from_idx]

        from_img = self.w.grid.get_widget_at_cell(from_idx, 0)
        to_img = self.w.grid.get_widget_at_cell(to_idx, 0)
        self.w.grid.remove(from_img, delete=False)
        self.w.grid.remove(to_img, delete=False)
        self.w.grid.add_widget(from_img, to_idx, 0)
        self.w.grid.add_widget(to_img, from_idx, 0)

    def move_slide(self, from_idx, to_idx):
        assert 0 <= from_idx < len(self.slideshow)
        assert 0 <= to_idx <= len(self.slideshow)
        if from_idx == to_idx:
            return

        from_img = self.w.grid.get_widget_at_cell(from_idx, 0)

        if from_idx < to_idx:
            self.slideshow.insert(to_idx, self.slideshow[from_idx])
            self.slideshow.pop(from_idx)

            self.w.grid.insert_row(to_idx)
            self.w.grid.remove(from_img, delete=False)
            self.w.grid.add_widget(from_img, to_idx, 0)
            self.w.grid.delete_row(from_idx)
        else:
            self.slideshow.insert(to_idx, self.slideshow[from_idx])
            self.slideshow.pop(from_idx + 1)

            self.w.grid.remove(from_img, delete=False)
            self.w.grid.delete_row(from_idx)
            self.w.grid.insert_row(to_idx)
            self.w.grid.add_widget(from_img, to_idx, 0)

    def edit_move_up_cb(self, w):
        if self.index <= 0:
            self.fv.show_error("Slide is already at the beginning")
            return
        self.swap_slides(self.index, self.index - 1)
        self.index -= 1
        self.show_slide(self.index)

    def edit_move_down_cb(self, w):
        if self.index >= len(self.slideshow) - 1:
            self.fv.show_error("Slide is already at the end")
            return
        self.swap_slides(self.index, self.index + 1)
        self.index += 1
        self.show_slide(self.index)

    def edit_get_index_cb(self, w):
        self.w.ins_index.set_value(self.index)

    def edit_move_to_cb(self, w):
        from_index = int(self.w.ins_index.get_value())
        if self.index == from_index:
            # No-op
            return
        self.move_slide(from_index, self.index)
        self.show_slide(self.index)

    def edit_hide_cb(self, w):
        self.slideshow[self.index].update(dict(hide=True))
        self.show_slide(self.index)

    def edit_unhide_cb(self, w):
        self.slideshow[self.index].update(dict(hide=False))
        self.show_slide(self.index)

    def edit_delete_cb(self, w):
        # TODO: dialog to confirm deletion
        self.slideshow.pop(self.index)
        from_img = self.w.grid.get_widget_at_cell(self.index, 0)
        self.w.grid.delete_row(self.index)
        from_img.delete()
        self.w.ins_index.set_limits(0, len(self.slideshow))
        self.w.ins_index.set_value(0)
        self.index = min(self.index, len(self.slideshow) - 1)
        self.show_slide(self.index)

    def add_slide(self, uri):
        slide_d = dict()
        image, image_w = self.get_thumbnail(uri, slide_d)
        slide_d['file'] = image.get('path')

        row = len(self.slideshow)
        self.slideshow.append(slide_d)
        self.w.grid.add_widget(image_w, row, 0)
        self.w.slide.set_limits(0, len(self.slideshow) - 1, incr_value=1)
        self.w.slide.set_value(0)
        self.w.ins_index.set_limits(0, len(self.slideshow))
        self.w.ins_index.set_value(0)

        self.update_duration()
        self.index = row
        self.show_slide(self.index)

    def get_thumb_generator(self):
        tg = CanvasView(logger=self.logger)
        tg.configure_surface(self.thumb_width, self.thumb_width)
        tg.enable_autozoom('on')
        tg.set_autocut_params('histogram')
        tg.enable_autocuts('on')
        tg.enable_auto_orient(True)
        tg.defer_redraw = False
        tg.set_bg(0.7, 0.7, 0.7)
        return tg

    def __str__(self):
        """
        This method should be provided and should return the lower case
        name of the plugin.
        """
        return 'slideshow'


# Append module docstring with config doc for auto insert by Sphinx.
#from ginga.util.toolbox import generate_cfg_example  # noqa
#if __doc__ is not None:
#    __doc__ += generate_cfg_example('plugin_SlideShow', package='ginga')
