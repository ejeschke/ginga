# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Downloads GUI for the Ginga reference viewer.

**Plugin Type: Global**

``Download`` is a global plugin.  Only one instance can be opened.

**Usage**

"""
import time
import os.path

from ginga.gw import Widgets
from ginga import GingaPlugin
from ginga.misc import Bunch
from ginga.util import catalog

__all__ = ['Downloads']


class Downloads(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Downloads, self).__init__(fv)

        # get Downloads preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Downloads')
        self.settings.add_defaults(size_check_limit=None)
        self.settings.load(onError='silent')

        self.dlbox = None
        self.dnlds = []
        self.gui_up = False

    def build_gui(self, container):

        vbox = Widgets.VBox()

        if self.dlbox is None:
            self.dlbox = Widgets.VBox()
        vbox.add_widget(Widgets.Label("Downloads:"))
        vbox.add_widget(self.dlbox, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        btns.set_border_width(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn)
        ## btn = Widgets.Button("Help")
        ## btn.add_callback('activated', lambda w: self.help())
        ## btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

        self.gui_up = True

    def add_download(self, info, future):
        add_time = time.time()
        vbox = Widgets.VBox()
        fname = Widgets.TextEntry()
        fname.set_text(info.url)
        vbox.add_widget(fname, stretch=0)
        hbox = Widgets.HBox()
        time_lbl = Widgets.Label('00:00:00')
        prog_lbl = Widgets.Label('0%')
        hbox.add_widget(time_lbl)
        hbox.add_widget(prog_lbl)
        vbox.add_widget(hbox, stretch=0)

        # create tracker for this download
        track = Bunch.Bunch(info=info, widget=vbox, time_start=add_time,
                            time_lbl=time_lbl, prog_lbl=prog_lbl,
                            future=future)
        self.dnlds.append(track)
        if self.gui_up:
            self.dlbox.add_widget(vbox)

        tmpfile = os.path.join(self.fv.tmpdir, "foo.fits")
        self.fv.nongui_do(self.download, info.url, tmpfile, track)

    def download(self, url, localpath, track):
        def _dl_indicator(count, blksize, totalsize):
            # calculate elapsed time label
            cur_time = time.time()
            elapsed = cur_time - track.time_start
            hrs = int(elapsed / 3600)
            mins = int((elapsed % 3600) / 60)
            secs = int((elapsed % 3600) % 60)
            msg_elapsed = "%02d:%02d:%02d" % (hrs, mins, secs)
            self.fv.gui_do(track.time_lbl.set_text, msg_elapsed)

            nbytes = int(count * blksize)
            if nbytes == totalsize:
                msg_progress = "Done"
            else:
                pct = float(nbytes) / float(totalsize)
                msg_progress = "%%%.2f" % (pct * 100.0)
            self.fv.gui_do(track.prog_lbl.set_text, msg_progress)

        try:
            # Try to download the URL.  We press our generic URL server
            # into use as a generic file downloader.
            dl = catalog.URLServer(self.logger, "downloader", "dl",
                                   url, "")
            filepath = dl.retrieve(url, filepath=localpath,
                                   cb_fn=_dl_indicator)

            # call the future
            track.future.resolve(filepath)

        except Exception as e:
            self.fv.gui_do(self.fv.show_error,
                           "Download of '%s' failed: %s" % (url, str(e)))
            return

    def stop(self):
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'download'


# END
