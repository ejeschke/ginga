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
    numhdu = None

    # User specified an HDU using bracket notation at end of path?
    match = re.match(r'^(.+)\[(\d+)\]$', filespec)
    if match:
        filespec = match.group(1)
        numhdu = int(match.group(2))
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

    res = Bunch.Bunch(filepath=filepath, url=url, numhdu=numhdu,
                      ondisk=ondisk)
    return res


def name_image_from_path(path, idx=None):
    (path, filename) = os.path.split(path)
    # Remove trailing .extension
    (name, ext) = os.path.splitext(filename)
    #if '.' in name:
    #    name = name[:name.rindex('.')]
    if idx is not None:
        name = '%s[%d]' % (name, idx)
    return name
