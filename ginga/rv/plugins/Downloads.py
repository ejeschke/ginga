# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Downloads GUI for the Ginga reference viewer.

**Plugin Type: Global**

``Download`` is a global plugin.  Only one instance can be opened.

**Usage**

Open this plugin to monitor the progress of URI downloads.  Start it
using the "Plugins" or "Operations" menu, and selecting the "Downloads"
plugin from under the "Util" category.

If you want to initiate a download, simply drag a URI into a channel
image viewer or the ``Thumbs`` pane.

You can remove the information about a download at any time by clicking
the "Clear" button for its entry. You can clear entries for all downloads
by clicking the "Clear All" button at the bottom.

Currently, it is not possible to cancel a download in progress.

**Settings**

The ``auto_clear_download`` option, if set to `True`, will cause a download
entry to be automatically deleted from the pane when the download completes.
It does not remove any downloaded file(s).

The download folder can be user-defined by assigning a value to the
"download_folder" setting in ~/.ginga/general.cfg.  If unassigned, it
defaults to a folder in the platform-specific default temp directory
(as told by the Python 'tempfile' module).

"""
import time

from ginga.gw import Widgets
from ginga import GingaPlugin
from ginga.misc import Bunch, Future
from ginga.locale.localize import _tr

__all__ = ['Downloads']


class Downloads(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Downloads, self).__init__(fv)

        # get Downloads preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Downloads')
        self.settings.add_defaults(auto_clear_download=False)
        self.settings.load(onError='silent')

        self.dlbox = None
        self.w_track = dict()
        self.downloads = []
        self.gui_up = False

    def build_gui(self, container):

        self.w = Bunch.Bunch()
        self.w_track = dict()
        vbox = Widgets.VBox()

        sc = Widgets.ScrollArea()
        vbox2 = Widgets.VBox()
        fr = Widgets.Frame(title=_tr("Downloads"))
        self.dlbox = Widgets.VBox()
        fr.set_widget(self.dlbox)
        vbox2.add_widget(fr, stretch=0)
        vbox2.add_widget(Widgets.Label(''), stretch=1)
        sc.set_widget(vbox2)
        vbox.add_widget(sc, stretch=1)
        self.w_scroll = sc

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button(_tr("Close"))
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        btn = Widgets.Button(_tr("Clear All"))
        btn.add_callback('activated', lambda w: self.gui_clear_all())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def gui_add_track(self, track):
        vbox = Widgets.VBox()
        fname = Widgets.TextEntry()
        fname.set_text(track.info.url)
        vbox.add_widget(fname, stretch=0)
        hbox = Widgets.HBox()
        hbox.set_spacing(2)
        time_lbl = Widgets.Label(track.elapsed)
        prog_bar = Widgets.ProgressBar()
        prog_bar.set_value(track.progress)
        hbox.add_widget(time_lbl)
        hbox.add_widget(prog_bar, stretch=1)
        rmv = Widgets.Button(_tr('Clear'))

        def _clear_download(w):
            self.gui_rm_track(track)

        rmv.add_callback('activated', _clear_download)
        hbox.add_widget(rmv)
        vbox.add_widget(hbox, stretch=0)
        self.dlbox.add_widget(vbox)
        w_track = Bunch.Bunch(container=vbox, time_lbl=time_lbl,
                              prog_bar=prog_bar, track=track)
        self.w_track[track.key] = w_track
        self.w_scroll.scroll_to_end(vertical=True)

    def gui_rm_track(self, track):
        if track in self.downloads:
            self.downloads.remove(track)

        if self.gui_up:
            w_track = self.w_track.get(track.key, None)
            if w_track is not None:
                del self.w_track[track.key]
            self.dlbox.remove(w_track.container)

    def gui_clear_all(self):
        for track in list(self.downloads):
            self.gui_rm_track(track)

    def add_download(self, info, future, download_cb=None):
        add_time = time.time()
        key = str(add_time)

        # create tracker for this download
        track = Bunch.Bunch(key=key, info=info, time_start=add_time,
                            elapsed='00:00:00', progress=0.0,
                            future=future, download_cb=download_cb)
        self.downloads.append(track)

        if self.gui_up:
            self.gui_add_track(track)

        self.fv.nongui_do(self.download, info.url, info.filepath, track)

    def download(self, url, localpath, track):
        # Dispatched via nongui_do().  Delegate the actual fetch to the
        # central object's download_file() (which transparently handles
        # the threaded vs. in-situ/async backends); this plugin just
        # drives the progress GUI and resolves the caller's future.  We
        # download into our own ``dl_future`` so we can keep this plugin's
        # behavior of *not* resolving the caller's future on failure
        # (it merely surfaces an error message).  download_file() may
        # return a coroutine (in-situ), which we pass back up to nongui_do.
        def _progress(fraction):
            self._update_track(track, fraction)
            # forward progress to any external listener (e.g. a plugin
            # that initiated this download and shows its own progress bar)
            if track.download_cb is not None:
                track.download_cb(fraction)

        dl_future = Future.Future()
        dl_future.add_callback('resolved', self._download_complete, track)
        return self.fv.download_file(url, localpath, dl_future,
                                     progress_cb=_progress)

    def _download_complete(self, dl_future, track):
        try:
            filepath = dl_future.get_value(block=False)
        except Exception as e:
            self._download_failed(track.info.url, e)
            return
        self._download_finished(track, filepath)

    def _update_track(self, track, progress):
        # calculate elapsed time label
        cur_time = time.time()
        elapsed = cur_time - track.time_start
        hrs = int(elapsed / 3600)
        mins = int((elapsed % 3600) / 60)
        secs = int((elapsed % 3600) % 60)
        track.elapsed = "%02d:%02d:%02d" % (hrs, mins, secs)

        track.progress = min(1.0, progress)

        if (self.settings.get('auto_clear_download', False) and
                track.progress >= 1.0):
            self.fv.gui_do(self.gui_rm_track, track)
        else:
            w_track = self.w_track.get(track.key, None)
            if w_track is None:
                return
            self.fv.gui_do(w_track.time_lbl.set_text, track.elapsed)
            self.fv.gui_do(w_track.prog_bar.set_value, track.progress)

    def _download_finished(self, track, filepath):
        # call the future
        self.logger.info("download of '%s' finished" % (filepath))
        track.future.resolve(filepath)

    def _download_failed(self, url, e):
        self.fv.gui_do(self.fv.show_error,
                       "Download of '%s' failed: %s" % (url, str(e)))

    def stop(self):
        self.dlbox = None
        self.w_track = dict()
        self.gui_up = False

    def start(self):
        if self.gui_up:
            for track in self.downloads:
                self.gui_add_track(track)

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'downloads'

# END
