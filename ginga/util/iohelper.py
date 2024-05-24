#
# iohelper.py -- misc routines used in manipulating files, paths and urls.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import re
import hashlib
import mimetypes
import pathlib
import urllib.parse
import tempfile

import puremagic

from ginga.misc import Bunch
from ginga.util.paths import ginga_home, ginga_pkgdir

# load local mime types overrides, if present
ginga_mimetypes = os.path.join(ginga_pkgdir,
                               "examples", "configs", "mime.types")
if os.path.exists(ginga_mimetypes):
    mimetypes.init(files=[ginga_mimetypes])

local_mimetypes = os.path.join(ginga_home, "mime.types")
if os.path.exists(local_mimetypes):
    mimetypes.init(files=[local_mimetypes])


# NOTE: this is a shortcut list of extensions in which we trust the
# extension over the mimetype that might be returned by the Python
# 'mimetypes' module.  You can add an extension here if the loaders
# can reliably load it and it is not recognized properly by 'mimetypes'
known_types = {
    '.fit': 'image/fits',
    '.fits': 'image/fits',
    '.fits.gz': 'image/fits',
    '.fits.fz': 'image/fits',
    '.asdf': 'image/asdf',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.tif': 'image/tiff',
    '.tiff': 'image/tiff',
    '.gif': 'image/gif',
    '.png': 'image/png',
    '.ppm': 'image/ppm',
    '.pnm': 'image/pnm',
    '.pbm': 'image/pbm',
}


def guess_filetype(filepath):
    """Guess the type of a file."""
    typ = None

    # Some specific checks for known file suffixes
    _fn = filepath.lower()
    for key, mimetype in known_types.items():
        if _fn.endswith(key):
            typ = mimetype
            break

    if typ is None:
        try:
            # Try to check using magic!
            typ = puremagic.from_file(filepath, mime=True)

            if isinstance(typ, str) and ';' in typ:
                typ, enc = typ.split(';')

        except Exception as e:
            typ = None

    if typ is None:
        # if magic fails, fall back to mimetypes
        try:
            typ, enc = mimetypes.guess_type(filepath)

        except Exception as e:
            # fail
            pass

    if typ:
        typ, subtyp = typ.split('/')
        return (typ, subtyp)

    raise ValueError("Can't determine file type of '%s'" % (filepath))


def get_download_path(uri, filename, cache_dir):

    # TODO: cache file by uri and timestamp
    filepath = os.path.join(cache_dir, filename)

    # find a free local copy of the file
    count, tmpfile = 1, filepath
    while os.path.exists(tmpfile):
        pfx, sfx = os.path.splitext(filepath)
        tmpfile = pfx + '_' + str(count) + sfx
        count += 1
    return tmpfile


def get_fileinfo(filespec, cache_dir=None):
    """
    Parse a file specification and return information about it.
    """
    if cache_dir is None:
        cache_dir = tempfile.gettempdir()

    # Loads first science extension by default.
    # This prevents [None] to be loaded instead.
    idx = None
    name_ext = ''

    # User specified an index using bracket notation at end of path?
    match = re.match(r'^(.+)\[(.+)\]$', filespec)
    if match:
        filespec = match.group(1)
        idx = match.group(2)
        if ',' in idx:
            hduname, extver = idx.split(',')
            hduname = hduname.strip()
            if re.match(r'^\d+$', extver):
                extver = int(extver)
                idx = (hduname, extver)
                name_ext = "[%s,%d]" % idx
            else:
                idx = idx.strip()
                name_ext = "[%s]" % idx
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
        urlinfo = urllib.parse.urlparse(filespec)
        if urlinfo.scheme == 'file':
            # local file
            filepath = str(pathlib.Path(urlinfo.path))

        else:
            path, filename = os.path.split(urlinfo.path)
            filepath = get_download_path(url, filename, cache_dir)

    else:
        # Not a URL
        filepath = filespec
        url = pathlib.Path(os.path.abspath(filepath)).as_uri()

    ondisk = os.path.exists(filepath)

    dirname, fname = os.path.split(filepath)
    fname_pfx, fname_sfx = os.path.splitext(fname)
    name = fname_pfx + name_ext

    res = Bunch.Bunch(filepath=filepath, url=url, numhdu=idx,
                      name=name, idx=name_ext, ondisk=ondisk)
    return res


def get_hdu_suffix(idx):
    if idx is None:
        return ''

    if isinstance(idx, tuple):
        assert len(idx) == 2, ValueError("idx tuple len (%d) != 2" % (
            len(idx)))
        hduname, extver = idx
        hduname = hduname.strip()
        extver = int(extver)
        if len(hduname) > 0:
            return "[%s,%d]" % (hduname, extver)
        else:
            return "[%d]" % extver

    if isinstance(idx, str):
        return "[%s]" % idx.strip()

    return "[%d]" % idx


def name_image_from_path(path, idx=None):
    (path, filename) = os.path.split(path)
    # Remove trailing .extension
    (name, ext) = os.path.splitext(filename)
    #if '.' in name:
    #    name = name[:name.rindex('.')]
    if idx is not None:
        name += get_hdu_suffix(idx)
    return name


def shorten_name(name, char_limit, side='right'):
    """Shorten `name` if it is longer than `char_limit`.
    If `side` == "right" then the right side of the name is shortened;
    if "left" then the left side is shortened.
    In either case, the suffix of the name is preserved.
    """
    # TODO: A more elegant way to do this?
    if char_limit is not None and len(name) > char_limit:
        info = get_fileinfo(name)
        if info.numhdu is not None:
            i = name.rindex('[')
            s = (name[:i], name[i:])
            len_sfx = len(s[1])
            len_pfx = char_limit - len_sfx - 4 + 1
            if len_pfx > 0:
                if side == 'right':
                    name = '{0}...{1}'.format(s[0][:len_pfx], s[1])
                elif side == 'left':
                    name = '...{0}{1}'.format(s[0][-len_pfx:], s[1])
            else:
                name = '...{0}'.format(s[1])
        else:
            len1 = char_limit - 3 + 1
            if side == 'right':
                name = '{0}...'.format(name[:len1])
            elif side == 'left':
                name = '...{0}'.format(name[-len1:])

    return name


def gethex(s):
    return hashlib.sha1(s.encode()).hexdigest()  # nosec


def get_thumbpath(thumbdir, path, makedir=True):
    if path is None:
        return None

    path = os.path.abspath(path)
    dirpath, filename = os.path.split(path)

    if not os.path.exists(thumbdir):
        if not makedir:
            raise ValueError("Thumb directory does not exist: %s" % (
                thumbdir))

        try:
            os.makedirs(thumbdir)
            # Write meta file
            metafile = os.path.join(thumbdir, "meta")
            with open(metafile, 'w') as out_f:
                out_f.write("srcdir: %s\n" % (dirpath))

        except OSError as e:
            raise Exception("Could not make thumb directory '%s': %s" % (
                thumbdir, str(e)))

    # Get location of thumb
    modtime = os.stat(path).st_mtime
    thumb_fname = gethex("%s.%s" % (filename, modtime))
    thumbpath = os.path.join(thumbdir, thumb_fname + ".jpg")
    return thumbpath
