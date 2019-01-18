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

from ginga.misc import Bunch

magic_tester = None
try:
    import magic
    have_magic = True
    # it seems there are conflicting versions of a 'magic'
    # module for python floating around...*sigh*
    if not hasattr(magic, 'from_file'):
        # TODO: do this at program start only
        magic_tester = magic.open(magic.DEFAULT_MODE)
        magic_tester.load()

except (ImportError, Exception):
    have_magic = False


def guess_filetype(filepath):
    """Guess the type of a file."""
    # If we have python-magic, use it to determine file type
    typ = None
    if have_magic:
        try:
            # it seems there are conflicting versions of a 'magic'
            # module for python floating around...*sigh*
            if hasattr(magic, 'from_file'):
                typ = magic.from_file(filepath, mime=True)

            elif magic_tester is not None:
                descrip = magic_tester.file(filepath)
                if descrip.startswith("FITS image data"):
                    return ('image', 'fits')

        except Exception as e:
            pass

    # Some specific checks for file suffixes
    _fn = filepath.lower()
    if _fn.endswith('.fits'):
        typ = 'image/fits'

    elif _fn.endswith('.asdf'):
        typ = 'image/asdf'

    if typ is None:
        # if no magic, or magic fails, fall back to mimetypes
        try:
            typ, enc = mimetypes.guess_type(filepath)

        except Exception as e:
            # fail
            pass

    if typ:
        typ, subtyp = typ.split('/')
        return (typ, subtyp)

    raise ValueError("Can't determine file type of '%s'" % (filepath))


def get_fileinfo(filespec, cache_dir='/tmp', download=False):
    """
    Parse a file specification and return information about it.

    Returns
    -------
    res : list
        A list of `~ginga.misc.Bunch.Bunch` objects.

    """
    # Loads first science extension by default.
    # This prevents [None] to be loaded instead.
    idx = None
    name_ext = ''

    # User specified an HDU using bracket notation at end of path?
    match = re.match(r'^(.+)\[(.+)\]$', filespec)
    if match:
        filespec = match.group(1)
        idx = match.group(2)
        if ',' in idx:
            hduname, extver = idx.split(',')
            hduname = hduname.strip().upper()

            # User trying to match extver with wildcard!
            # NOTE: Only use Astropy FITS; Only works on local file.
            if extver == '*':
                if '*' in filespec:
                    raise NotImplementedError('Wildcards in both filename and'
                                              'extension not supported')
                from astropy.io import fits
                idx = []
                name_ext = []
                with fits.open(filespec) as pf:
                    for pf_ext in pf:
                        if pf_ext.name.upper() == hduname:
                            cur_idx = (hduname, int(pf_ext.ver))
                            idx.append(cur_idx)
                            name_ext.append("[%s,%d]" % cur_idx)
                if len(name_ext) == 0:
                    idx = hduname
                    name_ext = "[%s]" % idx
                elif len(name_ext) == 1:
                    idx = idx[0]
                    name_ext = name_ext[0]

            # Single extver
            else:
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
        urlinfo = urllib.parse.urlparse(filespec)
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
        url = pathlib.Path(os.path.abspath(filepath)).as_uri()

    ondisk = os.path.exists(filepath)

    dirname, fname = os.path.split(filepath)
    fname_pfx, fname_sfx = os.path.splitext(fname)
    res = []

    # For [name, *] case
    if isinstance(name_ext, list):
        for cur_idx, cur_name_ext in zip(idx, name_ext):
            name = fname_pfx + cur_name_ext
            res.append(Bunch.Bunch(filepath=filepath, url=url, numhdu=cur_idx,
                                   name=name, ondisk=ondisk))

    # Normal case
    else:
        name = fname_pfx + name_ext
        res.append(Bunch.Bunch(filepath=filepath, url=url, numhdu=idx,
                               name=name, ondisk=ondisk))

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
        res = get_fileinfo(name)
        if len(res) != 1:
            raise NotImplementedError('Wildcard in extension name not supported')
        info = res[0]
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
    return hashlib.sha1(s.encode()).hexdigest()


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
