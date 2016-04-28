#
# FBrowser.py -- file browser plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os, glob
import stat, time

from ginga.misc import Bunch
from ginga import GingaPlugin
from ginga import AstroImage
from ginga.util import paths, iohelper
from ginga.util.six.moves import map, zip
from ginga.gw import Widgets

try:
    from astropy.io import fits as pyfits
    have_astropy = True
except ImportError:
    have_astropy = False


class FBrowser(GingaPlugin.LocalPlugin):

    def __init__(self, *args):
        # superclass defines some variables for us, like logger
        if len(args) == 2:
            super(FBrowser, self).__init__(*args)
        else:
            super(FBrowser, self).__init__(args[0], None)

        keywords = [ ('Object', 'OBJECT'),
                     ('Date', 'DATE-OBS'),
                     ('Time UT', 'UT'),
                     ]
        columns = [('Type', 'icon'),
                   ('Name', 'name'),
                   ('Size', 'st_size_str'),
                   ('Mode', 'st_mode_oct'),
                   ('Last Changed', 'st_mtime_str')
                   ]

        self.jumpinfo = []

        # setup plugin preferences
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_FBrowser')
        self.settings.addDefaults(home_path=paths.home,
                                  scan_fits_headers=False,
                                  scan_limit=100,
                                  keywords=keywords,
                                  columns=columns,
                                  color_alternate_rows=True,
                                  max_rows_for_col_resize=5000)
        self.settings.load(onError='silent')

        homedir = self.settings.get('home_path', None)
        if homedir is None or not os.path.isdir(homedir):
            homedir = paths.home
        self.curpath = os.path.join(homedir, '*')
        self.do_scanfits = self.settings.get('scan_fits_headers', False)
        self.scan_limit = self.settings.get('scan_limit', 100)
        self.keywords = self.settings.get('keywords', keywords)
        self.columns = self.settings.get('columns', columns)
        self.moving_cursor = False
        self.na_dict = { attrname: 'N/A' for colname, attrname in self.columns }

        # Make icons
        icondir = self.fv.iconpath
        self.folderpb = self.fv.get_icon(icondir, 'folder.png')
        self.filepb = self.fv.get_icon(icondir, 'file.png')
        self.fitspb = self.fv.get_icon(icondir, 'fits.png')

    def build_gui(self, container):

        vbox = Widgets.VBox()
        vbox.set_margins(2, 2, 2, 2)

        # create the table
        color_alternate = self.settings.get('color_alternate_rows', True)
        table = Widgets.TreeView(sortable=True, selection='multiple',
                                 use_alt_row_color=color_alternate,
                                 dragable=True)
        table.add_callback('activated', self.item_dblclicked_cb)
        table.add_callback('drag-start', self.item_drag_cb)

        # set header
        col = 0
        self._name_idx = 0
        for hdr, attrname in self.columns:
            if attrname == 'name':
                self._name_idx = col
            col += 1
        table.setup_table(self.columns, 1, 'name')

        vbox.add_widget(table, stretch=1)
        self.treeview = table

        self.entry = Widgets.TextEntry()
        vbox.add_widget(self.entry, stretch=0)
        self.entry.add_callback('activated', self.browse_cb)

        hbox = Widgets.HBox()
        btn = Widgets.Button("Load")
        btn.add_callback('activated', lambda w: self.load_cb())
        hbox.add_widget(btn, stretch=0)
        btn = Widgets.Button("Save Image As")
        hbox.add_widget(btn, stretch=0)
        self.entry2 = Widgets.TextEntry()
        hbox.add_widget(self.entry2, stretch=1)
        vbox.add_widget(hbox, stretch=0)
        self.entry2.add_callback('activated', self.save_as_cb)
        btn.add_callback('activated', lambda w: self.save_as_cb())

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Refresh")
        btn.add_callback('activated', lambda w: self.refresh())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Make Thumbs")
        btn.add_callback('activated', lambda w: self.make_thumbs())
        btns.add_widget(btn, stretch=0)

        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

    def load_paths(self, paths):
        if self.fitsimage is not None:
            self.fv.gui_do(self.fitsimage.make_callback, 'drag-drop', paths)
        else:
            fitsimage = self.fv.getfocus_fitsimage()
            self.fv.gui_do(fitsimage.make_callback, 'drag-drop', paths)

    def load_cb(self):
        # Load from text box
        path = str(self.entry.get_text()).strip()
        retcode = self.open_files(path)
        if retcode:
            return

        # Load from tree view
        #curdir, curglob = os.path.split(self.curpath)
        select_dict = self.treeview.get_selected()
        paths = [ info.path for key, info in select_dict.items() ]
        self.logger.debug('Loading {0}'.format(paths))

        # Open directory
        if len(paths) == 1 and os.path.isdir(paths[0]):
            path = os.path.join(paths[0], '*')
            self.entry.set_text(path)
            self.browse_cb(self.entry)
            return

        # Exclude directories
        paths = [path for path in paths if os.path.isfile(path)]

        # Load files
        self.load_paths(paths)

    def makelisting(self, path):
        self.entry.set_text(path)

        tree_dict = {}
        for bnch in self.jumpinfo:
            icon = self.file_icon(bnch)
            bnch.setvals(icon=icon)
            entry_key = bnch.name

            assert entry_key is not None, \
                   Exception("No key for tuple")

            tree_dict[entry_key] = bnch

        self.treeview.set_tree(tree_dict)

        # Resize column widths
        n_rows = len(tree_dict)
        if n_rows < self.settings.get('max_rows_for_col_resize', 5000):
            self.treeview.set_optimal_column_widths()
            self.logger.debug("Resized columns for {0} row(s)".format(n_rows))

    def get_path_from_item(self, res_dict):
        paths = [ info.path for key, info in res_dict.items() ]
        path = paths[0]
        return path

    def item_dblclicked_cb(self, widget, res_dict):
        path = self.get_path_from_item(res_dict)
        self.open_file(path)

    def item_drag_cb(self, widget, drag_pkg, res_dict):
        urls = [ "file://" + info.path for key, info in res_dict.items() ]
        self.logger.info("urls: %s" % (urls))
        drag_pkg.set_urls(urls)

    def browse_cb(self, widget):
        path = str(widget.get_text()).strip()

        # Load file(s) -- image*.fits, image*.fits[ext]
        retcode = self.open_files(path)

        # Open directory
        if not retcode:
            self.browse(path)

    def save_as_cb(self):
        path = str(self.entry2.get_text()).strip()
        if not path.startswith('/'):
            path = os.path.join(self.curpath, path)

        image = self.fitsimage.get_image()
        if image is None:
            self.logger.error('No image to save')
            return

        self.fv.error_wrap(image.save_as_file, path)

    def close(self):
        if self.fitsimage is None:
            self.fv.stop_global_plugin(str(self))
        else:
            self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def file_icon(self, bnch):
        if bnch.type == 'dir':
            pb = self.folderpb
        elif bnch.type == 'fits':
            pb = self.fitspb
        else:
            pb = self.filepb
        return pb


    def open_files(self, path):
        """Load file(s) -- image*.fits, image*.fits[ext].
        Returns success code (True or False).
        """
        # Strips trailing wildcard
        if path.endswith('*'):
            path = path[:-1]

        if os.path.isdir(path):
            return False

        self.logger.debug('Opening files matched by {0}'.format(path))
        info = iohelper.get_fileinfo(path)
        ext = iohelper.get_hdu_suffix(info.numhdu)
        files = glob.glob(info.filepath)  # Expand wildcard
        paths = ['{0}{1}'.format(f, ext) for f in files]

        self.load_paths(paths)
        return True

    def open_file(self, path):
        self.logger.debug("path: %s" % (path))

        if path == '..':
            curdir, curglob = os.path.split(self.curpath)
            path = os.path.join(curdir, path, curglob)

        if os.path.isdir(path):
            path = os.path.join(path, '*')
            self.browse(path)

        elif os.path.exists(path):
            #self.fv.load_file(path)
            uri = "file://%s" % (path)
            self.load_paths([uri])

        else:
            self.browse(path)

    def get_info(self, path):
        dirname, filename = os.path.split(path)
        name, ext = os.path.splitext(filename)
        ftype = 'file'
        if os.path.isdir(path):
            ftype = 'dir'
        elif os.path.islink(path):
            ftype = 'link'
        elif ext.lower() == '.fits':
            ftype = 'fits'

        bnch = Bunch.Bunch(self.na_dict)
        try:
            filestat = os.stat(path)
            bnch.update(dict(path=path, name=filename, type=ftype,
                             st_mode=filestat.st_mode,
                             st_mode_oct=oct(filestat.st_mode),
                             st_size=filestat.st_size,
                             st_size_str=str(filestat.st_size),
                             st_mtime=filestat.st_mtime,
                             st_mtime_str=time.ctime(filestat.st_mtime)))
        except OSError as e:
            # TODO: identify some kind of error with this path
            bnch.update(dict(path=path, name=filename, type=ftype,
                             st_mode=0, st_size=0,
                             st_mtime=0))

        return bnch

    def browse(self, path):
        self.logger.debug("path: %s" % (path))
        if os.path.isdir(path):
            dirname = path
            globname = None
        else:
            dirname, globname = os.path.split(path)
        dirname = os.path.abspath(dirname)

        # check validity of leading path name
        if not os.path.isdir(dirname):
            self.fv.show_error("Not a valid path: %s" % (dirname))
            return

        if not globname:
            globname = '*'
        path = os.path.join(dirname, globname)

        # Make a directory listing
        self.logger.debug("globbing path: %s" % (path))
        filelist = list(glob.glob(path))
        filelist.sort(key=lambda s: s.lower())
        filelist.insert(0, os.path.join(dirname, '..'))

        self.jumpinfo = list(map(self.get_info, filelist))
        self.curpath = path

        if self.do_scanfits:
            num_files = len(self.jumpinfo)
            if num_files <= self.scan_limit:
                self.scan_fits()
            else:
                self.logger.warning("Number of files (%d) is greater than scan limit (%d)--skipping header scan" % (
                    num_files, self.scan_limit))

        self.makelisting(path)

    def scan_fits(self):
        # Scan each FITS file and add header items
        self.logger.info("scanning files for header keywords...")
        start_time = time.time()
        for bnch in self.jumpinfo:
            if (not bnch.type == 'fits') or (not have_astropy):
                continue
            try:
                with pyfits.open(bnch.path, 'readonly') as in_f:
                    kwds = { attrname: in_f[0].header.get(kwd, 'N/A')
                                  for attrname, kwd in self.keywords}
                bnch.update(kwds)
            except Exception as e:
                self.logger.warning("Error reading FITS keywords from '%s': %s" % (
                    bnch.path, str(e)))
                continue
        elapsed = time.time() - start_time
        self.logger.info("done scanning--scan time: %.2f sec" % (elapsed))

    def refresh(self):
        self.browse(self.curpath)

    def scan_headers(self):
        self.browse(self.curpath)

    def make_thumbs(self):
        path = self.curpath
        self.logger.info("Generating thumbnails for '%s'..." % (
            path))
        filelist = glob.glob(path)
        filelist.sort(key=lambda s: s.lower())

        if self.fitsimage is not None:
            fitsimage = self.fitsimage
        else:
            fitsimage = self.fv.getfocus_fitsimage()

        # find out our channel
        chname = self.fv.get_channelName(fitsimage)
        channel = self.fv.get_channelInfo(chname)

        for path in filelist:
            name = self.fv.name_image_from_path(path)
            info = Bunch.Bunch(name=name, path=path)
            self.fv.nongui_do(channel.add_image_info, info)

    def start(self):
        self.win = None
        self.browse(self.curpath)

    def pause(self):
        pass

    def resume(self):
        pass

    def stop(self):
        pass

    def redo(self, *args):
        return True

    def __str__(self):
        return 'fbrowser'

#END
