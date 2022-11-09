# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
``AutoLoad`` is a simple plugin to monitor a folder for new files and
automatically load them into a channel when they appear.

**Plugin Type: Local**

``AutoLoad`` is a local plugin, which means it is associated with a channel.
An instance can be opened for each channel.

.. note:: You need to install the Python "watchdog" package to use this
          plugin.

**Usage**

* To set up a folder to be monitored, type a path of a folder (directory)
  in the "Watched folder" field and press ENTER or click "Set".
* If you need to distinguish between files that will be added to this folder,
  you may type a Python regular expression in the "Regex" box and click "Set".
  Only files with names matching the pattern will be considered.  Note that
  the regex is for the filename only; not any part of the folder path.
* If you ever want to pause the auto loading, you can check the box marked
  "Pause"; this will stop any auto loading.  Note that if you subsequently
  uncheck the box, files that arrived in the intervening period will not be
  loaded.

.. note:: Monitoring folders that reside on network drives may or may not
          work.

**User Configuration**

"""
import os.path
import re

from ginga import GingaPlugin
from ginga.gw import Widgets

# pip install watchdog
have_watchdog = False
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    have_watchdog = True
except ImportError:
    pass

__all__ = ['AutoLoad']


class AutoLoad(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super().__init__(fv, fitsimage)

        # get AutoLoad preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_AutoLoad')
        self.settings.add_defaults(watch_folder=None, filename_regex=None,
                                   start_paused=False)
        self.settings.load(onError='silent')

        self.observer = None
        self._watch = None
        self.data_dir = self.settings.get('watch_folder', None)
        self.regex = self.settings.get('filename_regex', None)
        self.regex_c = None
        self.pause_flag = self.settings.get('start_paused', False)
        self.gui_up = False

    def build_gui(self, container):
        if not have_watchdog:
            raise ImportError("Install 'watchdog' to use this plugin")

        container.set_border_width(2)
        top = Widgets.VBox()
        top.set_border_width(4)

        # Possible future options:
        # - file rename
        # - add metadata
        # - run a script or a custom function
        captions = (("Watched folder:", 'label', 'folder', 'entryset'),
                    ("Match regex:", 'label', 'regex', 'entryset'),
                    ("Pause", 'checkbox'),
                    )
        w, b = Widgets.build_info(captions, orientation='vertical')
        self.w.update(b)

        b.folder.set_tooltip("Folder to monitor for new files")
        if self.data_dir is not None:
            b.folder.set_text(self.data_dir)
        b.folder.add_callback('activated', self.set_folder_cb)
        b.regex.set_tooltip("Regular expression to match file name")
        if self.regex is not None:
            b.folder.set_text(self.regex)
        b.regex.add_callback('activated', self.set_regex_cb)
        b.pause.set_tooltip("Pause auto loading")
        b.pause.set_state(self.pause_flag)
        b.pause.add_callback('activated', self.set_pause_cb)

        top.add_widget(w, stretch=0)
        # for customization by subclasses
        self.w.vbox = top

        container.add_widget(top, stretch=0)

        container.add_widget(Widgets.Label(''), stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        container.add_widget(btns, stretch=0)

        self.gui_up = True

    def set_folder_cb(self, w):
        data_dir = w.get_text().strip()
        self.set_folder(data_dir)

    def set_folder(self, data_dir):
        if self.data_dir is not None:
            # remove old watch
            if self._watch is not None:
                self.observer.unschedule(self._watch)

        if data_dir is None or len(data_dir) == 0:
            self.data_dir = None
            return
        # add new watch folder
        event_handler = FileSystemEventHandler()
        event_handler.on_closed = self._file_detected_cb
        self._watch = self.observer.schedule(event_handler, data_dir,
                                             recursive=False)
        self.data_dir = data_dir

    def set_regex_cb(self, w):
        regex = w.get_text().strip()
        self.set_regex(regex)

    def set_regex(self, regex):
        if regex is None or len(regex) == 0:
            self.regex_c = None
            self.regex = None
            return

        try:
            self.regex_c = re.compile(regex)
            self.regex = regex

        except Exception as e:
            self.regex = None
            msgerr = "Couldn't compile regular expression: {}".format(e)
            self.fv.show_error(msgerr)

    def set_pause_cb(self, w, tf):
        self.pause_flag = tf

    def close(self):
        self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def start(self):
        if self.regex is not None:
            self.set_regex(self.regex)
        self.observer = Observer()

        if self.data_dir is not None:
            self.set_folder(self.data_dir)

        self.observer.start()

    def stop(self):
        self.observer.stop()
        self._watch = None
        self.observer.join()
        self.gui_up = False

    def _file_detected_cb(self, event):
        if self.pause_flag:
            return
        filepath = event.src_path
        self.logger.info(f"new file detected: {filepath}")

        if self.check_file(filepath):
            self.load_file(filepath)

    def check_file(self, filepath):
        """Check path and return True if we should load it.
        Subclass can override this to add different checks.
        """
        if self.regex is not None:
            fname = os.path.basename(filepath)
            match = self.regex_c.match(fname)
            if not match:
                self.logger.info(f"filename {fname} did not match regex")
                return False

        # file did not fail any checks we set for it
        return True

    def load_file(self, filepath):
        """Subclass can override to change behavior."""
        self.fv.nongui_do(self.fv.load_file, filepath)

    def redo(self):
        pass

    def __str__(self):
        return 'autoload'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_AutoLoad', package='ginga')
