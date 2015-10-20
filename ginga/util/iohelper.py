#
# iohelper.py -- misc routines used in manipulating files, paths and urls.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import re

from ginga.misc import Bunch
from ginga.util.six.moves import urllib_parse


def get_fileinfo(filespec, cache_dir='/tmp', download=False):
    """
    Parse a file specification and return information about it.
    """
    idx = None
    name_ext = ''

    # User specified an HDU using bracket notation at end of path?
    match = re.match(r'^(.+)\[(.+)\]$', filespec)
    if match:
        filespec = match.group(1)
        idx = match.group(2)
        if ',' in idx:
            hduname, extver = idx.split(',')
            hduname = hduname.strip()
            extver = int(extver)
            idx = (hduname, extver)
            name_ext = "[%s,%d]" % idx
        else:
            if re.match(r'^\d+$', idx):
                idx = int(idx)
                name_ext = "[%d]" % idx
            else:
                idx = idx.strip()
                name_ext = "[%s]" % idx
    else:
        filespec = filespec

    url = filespec
    filepath = None

    # Does this look like a URL?
    match = re.match(r"^(\w+)://(.+)$", filespec)
    if match:
        urlinfo = urllib_parse.urlparse(filespec)
        if urlinfo.scheme == 'file':
            # local file
            filepath = urlinfo.path
            match = re.match(r"^/(\w+\:)", filepath)
            if match:
                # This is a windows path with a drive letter?
                # strip the leading slash
                # NOTE: this seems like it should not be necessary and might
                # break some cases
                filepath = filepath[1:]

        else:
            path, filename = os.path.split(urlinfo.path)
            filepath = os.path.join(cache_dir, filename)

    else:
        # Not a URL
        filepath = filespec
        url = "file://" + filepath

    ondisk = os.path.exists(filepath)

    dirname, fname = os.path.split(filepath)
    fname_pfx, fname_sfx = os.path.splitext(fname)
    name = fname_pfx + name_ext

    res = Bunch.Bunch(filepath=filepath, url=url, numhdu=idx,
                      name=name, ondisk=ondisk)
    return res


def name_image_from_path(path, idx=None):
    (path, filename) = os.path.split(path)
    # Remove trailing .extension
    (name, ext) = os.path.splitext(filename)
    #if '.' in name:
    #    name = name[:name.rindex('.')]
    if idx is not None:
        if isinstance(idx, tuple):
            assert len(idx) == 2, ValueError("idx tuple len (%d) != 2" % (
                len(idx)))
            hduname, extver = idx
            hduname = hduname.strip()
            extver = int(extver)
            name += "[%s,%d]" % idx
        else:
            if isinstance(idx, str):
                name += "[%s]" % idx.strip()
            else:
                name += "[%d]" % idx
    return name
