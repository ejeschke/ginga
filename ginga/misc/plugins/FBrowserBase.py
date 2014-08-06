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


class FBrowserBase(GingaPlugin.LocalPlugin):

    def __init__(self, fv, fitsimage):
        # superclass defines some variables for us, like logger
        super(FBrowserBase, self).__init__(fv, fitsimage)

        self.keywords = ['OBJECT', 'UT']
        self.columns = [('Name', 'name'),
                        ('Size', 'st_size'),
                        ('Mode', 'st_mode'),
                        ('Last Changed', 'st_mtime')
                        ]
        
        self.jumpinfo = []
        homedir = paths.home
        self.curpath = os.path.join(homedir, '*')
        self.do_scanfits = False
        self.moving_cursor = False


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

        try:
            filestat = os.stat(path)
            bnch = Bunch.Bunch(path=path, name=filename, type=ftype,
                               st_mode=filestat.st_mode, st_size=filestat.st_size,
                               st_mtime=filestat.st_mtime)
        except OSError as e:
            # TODO: identify some kind of error with this path
            bnch = Bunch.Bunch(path=path, name=filename, type=ftype,
                               st_mode=0, st_size=0,
                               st_mtime=0)
            
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
        filelist.sort(key=str.lower)
        filelist.insert(0, os.path.join(dirname, '..'))

        self.jumpinfo = list(map(self.get_info, filelist))
        self.curpath = path

        if self.do_scanfits:
            self.scan_fits()
            
        self.makelisting(path)

    def scan_fits(self):
        for bnch in self.jumpinfo:
            if not bnch.type == 'fits':
                continue
            if 'kwds' not in bnch:
                try:
                    in_f = AstroImage.pyfits.open(bnch.path, 'readonly')
                    try:
                        kwds = {}
                        for kwd in self.keywords:
                            kwds[kwd] = in_f[0].header.get(kwd, 'N/A')
                        bnch.kwds = kwds
                    finally:
                        in_f.close()
                except Exception as e:
                    continue

    def refresh(self):
        self.browse(self.curpath)
        
    def scan_headers(self):
        self.browse(self.curpath)
        
    def make_thumbs(self):
        path = self.curpath
        self.logger.info("Generating thumbnails for '%s'..." % (
            path))
        filelist = glob.glob(path)
        filelist.sort(key=str.lower)

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
