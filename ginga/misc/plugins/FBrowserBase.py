#
# FBrowserBase.py -- Base class for file browser plugin for fits viewer
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os, glob
import stat, time

from ginga.misc import Bunch
from ginga import GingaPlugin
from ginga import AstroImage
from ginga.util import paths
from ginga.util.six.moves import map, zip

try:
    from astropy.io import fits as pyfits
    have_astropy = True
except ImportError:
    have_astropy = False


class FBrowserBase(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(FBrowserBase, self).__init__(fv, fitsimage)

        keywords = [ ('Object', 'OBJECT'),
                     ('Date', 'DATE-OBS'),
                     ('Time UT', 'UT'),
                     ]
        columns = [('Name', 'name'),
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
                                  columns=columns)
        self.settings.load(onError='silent')

        homedir = self.settings.get('home_path', None)
        if homedir is None:
            homedir = paths.home
        self.curpath = os.path.join(homedir, '*')
        self.do_scanfits = self.settings.get('scan_fits_headers', False)
        self.scan_limit = self.settings.get('scan_limit', 100)
        self.keywords = self.settings.get('keywords', keywords)
        self.columns = self.settings.get('columns', columns)
        self.moving_cursor = False
        self.na_dict = { attrname: 'N/A' for colname, attrname in self.columns }

    def close(self):
        chname = self.fv.get_channelName(self.fitsimage)
        self.fv.stop_local_plugin(chname, str(self))
        return True

    def file_icon(self, bnch):
        if bnch.type == 'dir':
            pb = self.folderpb
        elif bnch.type == 'fits':
            pb = self.fitspb
        else:
            pb = self.filepb
        return pb

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
            self.fitsimage.make_callback('drag-drop', [uri])

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
                self.logger.warn("Number of files (%d) is greater than scan limit (%d)--skipping header scan" % (
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
                self.logger.warn("Error reading FITS keywords from '%s': %s" % (
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

        # find out our channel
        chname = self.fv.get_channelName(self.fitsimage)

        # Invoke the method in this channel's Thumbs plugin
        # TODO: don't expose gpmon!
        rsobj = self.fv.gpmon.getPlugin('Thumbs')
        self.fv.nongui_do(rsobj.make_thumbs, chname, filelist)

    def start(self):
        self.win = None
        self.browse(self.curpath)

    def pause(self):
        pass

    def resume(self):
        pass

    def stop(self):
        pass

    def redo(self):
        return True


#END
