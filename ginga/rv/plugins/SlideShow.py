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
header line.  The file must contain at least one column, titled "filename".
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
import csv
from datetime import timedelta

# GINGA
from ginga.GingaPlugin import LocalPlugin
from ginga.gw import Widgets
from ginga.gw.GwHelp import FileSelection
from ginga.util import loader

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

        self.index = 0
        self.def_duration = self.settings.get('default_duration', 5.0)
        self.gui_up = False

    def build_gui(self, container):
        """Build GUI such that image list area is maximized."""

        self.w.fs = FileSelection(container.get_widget())
        vbox = Widgets.VBox()

        captions = (('Load', 'button', 'path', 'textentry',
                     'Reload', 'button'),
                    ('Prev', 'button', 'Slide', 'spinbox', 'Next', 'button'),
                    ('Start', 'button', 'filename', 'textentry', 'Stop', 'button'),
                    ('Default duration:', 'llabel', 'default_duration', 'textentryset'),
                    ('Duration:', 'llabel', 'duration', 'label',
                     'Total:', 'llabel', 'total', 'label'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)
        vbox.add_widget(w, stretch=0)

        b.load.set_tooltip('Load a slideshow file')
        b.load.add_callback('activated', self._popup_load_dialog_cb)
        b.path.set_tooltip('Path for slideshow file')
        b.path.add_callback('activated', self.load_slideshow_cb)
        b.reload.set_tooltip('Reload slideshow file')
        b.reload.add_callback('activated', self.load_slideshow_cb)

        b.prev.add_callback('activated', self.prev_slide_cb)
        b.slide.add_callback('value-changed', self.set_slide_cb)
        b.next.add_callback('activated', self.next_slide_cb)

        b.start.add_callback('activated', self.start_slideshow_cb)
        b.stop.add_callback('activated', self.stop_slideshow_cb)
        b.filename.set_editable(False)

        b.default_duration.add_callback('activated', self.set_duration_cb)
        b.default_duration.set_text(str(self.def_duration))
        b.default_duration.set_tooltip("Set the default duration if none found for a slide")

        container.add_widget(vbox, stretch=0)

        container.add_widget(Widgets.Label(''), stretch=1)

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
        self.w.fs.popup('Load slide show', self._load_slideshow_file,
                        initialdir='.',
                        filename='Slide show files (*.csv)')

    def _load_slideshow_file(self, path):
        self.w.path.set_text(path)
        self.load_slideshow(path)

    def load_slideshow_cb(self, w):
        path = self.w.path.get_text()
        self.load_slideshow(path)

    def load_slideshow(self, path):
        self.slideshow = []
        slide_dir, fname = os.path.split(path)
        with open(path, 'r') as in_f:
            reader = csv.DictReader(decomment(in_f), delimiter=',')
            index = 0
            for slide_d in reader:
                # append slide directory to filename if a full
                # path is not given
                fname = slide_d['filename']
                if not fname.startswith('/'):
                    fname = os.path.join(slide_dir, fname)
                    slide_d['filename'] = fname

                # if 'duration' not in slide_d:
                #     slide_d['duration'] = None
                if 'position' not in slide_d:
                    slide_d['position'] = index

                self.slideshow.append(slide_d)
                index += 1

            self.slideshow.sort(key=lambda slide_d: slide_d['position'])
        self.w.slide.set_limits(0, len(self.slideshow) - 1, incr_value=1)
        self.w.slide.set_value(0)

        duration = sum(float(d.get('duration', self.def_duration))
                       for d in self.slideshow)
        delta = timedelta(seconds=duration)
        self.w.duration.set_text(str(delta))
        self.w.total.set_text(str(len(self.slideshow)))

        self.show_slide(self.index, set_timer=False)

    def start_slideshow_cb(self, w):
        self.show_slide(self.index, set_timer=True)

    def stop_slideshow_cb(self, w):
        self.timer.cancel()

    def show_slide(self, index, set_timer=False):
        slide_d = self.slideshow[index]

        image = slide_d.get('image', None)
        if image is None:
            image = loader.load_data(slide_d['filename'], logger=self.logger)
            slide_d['image'] = image

        self.w.slide.set_value(index)
        _dir, fname = os.path.split(slide_d['filename'])
        self.w.filename.set_text(fname)

        if set_timer:
            self.timer.set(slide_d.get('duration', self.def_duration))

        #self.fitsimage.set_image(image)
        name = image.get('name', None)
        if name in self.channel:
            self.channel.switch_image(image)
        else:
            self.channel.add_image(image)

    def timer_cb(self, timer):
        self.index += 1
        if self.index >= len(self.slideshow):
            return

        self.show_slide(self.index, set_timer=True)

    def set_slide_cb(self, w, idx):
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

    def redo(self):
        pass

    def close(self):
        chname = self.fv.get_channel_name(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))

    def start(self):
        self.resume()

    def resume(self):
        # turn off any mode user may be in
        try:
            self.modes_off()
        except AttributeError:
            pass

        self.fv.show_status('Press "Help" for instructions')

    def stop(self):
        self.gui_up = False
        self.fv.show_status('')

    def __str__(self):
        """
        This method should be provided and should return the lower case
        name of the plugin.
        """
        return 'slideshow'


def decomment(csvreader):
    # used to remove comments from CSV file
    for row in csvreader:
        line = row.split('#')[0].strip()
        if len(line) > 0:
            yield line

# Append module docstring with config doc for auto insert by Sphinx.
#from ginga.util.toolbox import generate_cfg_example  # noqa
#if __doc__ is not None:
#    __doc__ += generate_cfg_example('plugin_SlideShow', package='ginga')
