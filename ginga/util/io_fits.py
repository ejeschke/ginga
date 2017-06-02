#
# io_fits.py -- Module wrapper for loading FITS files.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
There are two possible choices for a python FITS file reading package
compatible with Ginga: astropy/pyfits and fitsio.  Both are based on
the CFITSIO library, although it seems that astropy's version has
changed quite a bit from the original, while fitsio is still tracking
the current version.

To force the use of one, do:

    from ginga.util import io_fits
    io_fits.use('package')

(replace 'package' with one of {'astropy', 'fitsio'}) before you load
any images.  Otherwise Ginga will try to pick one for you.
"""
import numpy

from ginga.misc import Bunch
from ginga.util import iohelper

fits_configured = False
fitsLoaderClass = None
have_astropy = False
have_fitsio = False


class FITSError(Exception):
    pass


def use(fitspkg, raise_err=True):
    global fits_configured, fitsLoaderClass, \
           have_astropy, pyfits, \
           have_fitsio, fitsio

    if fitspkg == 'astropy':
        try:
            from astropy.io import fits as pyfits
            have_astropy = True
            fitsLoaderClass = PyFitsFileHandler
            return True

        except ImportError:
            if raise_err:
                raise

        return False

    elif fitspkg == 'fitsio':
        try:
            import fitsio
            have_fitsio = True
            fitsLoaderClass = FitsioFileHandler
            return True

        except ImportError as e:
            if raise_err:
                raise
        return False

    return False


class BaseFitsFileHandler(object):

    def __init__(self, logger):
        super(BaseFitsFileHandler, self).__init__()

        self.logger = logger
        self.fileinfo = None
        self.fits_f = None
        self.hdu_info = []
        self.hdu_db = {}
        self.extver_db = {}
        self.factory_dict = {}

    def register_type(self, name, klass):
        self.factory_dict[name.lower()] = klass

    def get_factory(self):
        hdlr = self.__class__(self.logger)
        hdlr.factory_dict.update(self.factory_dict)
        return hdlr


class PyFitsFileHandler(BaseFitsFileHandler):

    def __init__(self, logger):
        if not have_astropy:
            raise FITSError(
                "Need astropy module installed to use this file handler")

        super(PyFitsFileHandler, self).__init__(logger)
        self.kind = 'pyfits'

    def fromHDU(self, hdu, ahdr):
        header = hdu.header
        if hasattr(header, 'cards'):
            # newer astropy.io.fits don't have ascardlist()
            for card in header.cards:
                if len(card.keyword) == 0:
                    continue
                ahdr.set_card(card.keyword, card.value, comment=card.comment)
        else:
            for card in header.ascardlist():
                if len(card.key) == 0:
                    continue
                ahdr.set_card(card.key, card.value, comment=card.comment)

    def load_hdu(self, hdu, dstobj=None, **kwargs):

        if isinstance(hdu, (pyfits.ImageHDU,
                            pyfits.CompImageHDU,
                            pyfits.PrimaryHDU,
                            )):
            # <-- data is an image

            if dstobj is None:
                # get model class for this type of object
                obj_class = self.factory_dict.get('image', None)
                if obj_class is None:
                    raise FITSError(
                        "I don't know how to load objects of kind 'image'")

                dstobj = obj_class(logger=self.logger)

            # For now, call back into the object to load it from pyfits-style
            # HDU in future migrate to storage-neutral format
            dstobj.load_hdu(hdu, **kwargs)

        elif isinstance(hdu, (pyfits.TableHDU,
                              pyfits.BinTableHDU)):
            # <-- data is a table

            if dstobj is None:
                # get model class for this type of object
                obj_class = self.factory_dict.get('table', None)
                if obj_class is None:
                    raise FITSError(
                        "I don't know how to load objects of kind 'table'")

                dstobj = obj_class(logger=self.logger)

            # For now, call back into the object to load it from pyfits-style
            # HDU in future migrate to storage-neutral format
            dstobj.load_hdu(hdu, **kwargs)

        else:
            raise FITSError("I don't know how to read this HDU")

        return dstobj

    def load_file(self, filespec, numhdu=None, dstobj=None, memmap=None,
                  **kwargs):
        inherit_primary_header = kwargs.pop('inherit_primary_header', False)
        opener = self.get_factory()
        opener.open_file(filespec, memmap=memmap, **kwargs)
        try:
            return opener.get_hdu(
                numhdu, dstobj=dstobj,
                inherit_primary_header=inherit_primary_header)
        finally:
            opener.close()

    def open_file(self, filespec, memmap=None, **kwargs):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise FITSError("File does not appear to be on disk: %s" % (
                info.url))

        self.fileinfo = info
        filepath = info.filepath

        self.logger.debug("Loading file '%s' ..." % (filepath))
        fits_f = pyfits.open(filepath, 'readonly', memmap=memmap)
        self.fits_f = fits_f

        # this seems to be necessary now for some fits files...
        try:
            fits_f.verify('fix')

        except Exception as e:
            # Let's hope for the best!
            self.logger.warn("Problem verifying fits file '%s': %s" % (
                filepath, str(e)))

        try:
            # this can fail for certain FITS files, with a "name undefined"
            # error bubbling up from astropy
            _hduinfo = fits_f.info(output=False)

        except Exception as e:
            # if so, this insures that name will be translated into the
            # HDU index below
            _hduinfo = tuple((None, '') for i in range(len(fits_f)))

        idx = 0
        extver_db = {}
        self.hdu_info = []
        self.hdu_db = {}

        for tup in _hduinfo:
            name = tup[1]
            # figure out the EXTVER for this HDU
            extver = extver_db.setdefault(name, 0)
            extver += 1
            extver_db[name] = extver

            # prepare a record of pertinent info about the HDU for
            # lookups by numerical index or (NAME, EXTVER)
            d = Bunch.Bunch(index=idx, name=name, extver=extver)
            if len(tup) > 5:
                d.setvals(htype=tup[2], dtype=tup[5])
            self.hdu_info.append(d)
            # different ways of accessing this HDU:
            # by numerical index
            self.hdu_db[idx] = d
            # by (hduname, extver)
            self.hdu_db[(name, extver)] = d
            idx += 1

        self.extver_db = extver_db

    def close(self):
        self.hdu_info = None
        self.hdu_db = {}
        self.extver_db = {}
        self.info = None
        self.fits_f = None

    def __len__(self):
        return len(self.hdu_info)

    def get_hdu(self, numhdu, dstobj=None, **kwargs):

        if numhdu is None:
            found_valid_hdu = False
            for i, d in enumerate(self.hdu_info):
                name = d.name
                hdu = self.fits_f[i]

                # rule out HDUs we can't deal with
                if not isinstance(hdu, (pyfits.ImageHDU,
                                        pyfits.CompImageHDU,
                                        pyfits.PrimaryHDU,
                                        pyfits.TableHDU,
                                        pyfits.BinTableHDU,
                                        )):
                    continue

                if not isinstance(hdu.data, numpy.ndarray):
                    # We need to open a numpy array
                    continue

                if 0 in hdu.data.shape:
                    # non-pixel or zero-length data hdu?
                    continue

                # Looks good, let's try it
                found_valid_hdu = True
                extver = d.extver
                _numhdu = (name, extver)
                if (len(name) == 0) or (_numhdu not in self.fits_f):
                    numhdu = i
                else:
                    numhdu = _numhdu
                break

            if not found_valid_hdu:
                # Load just the header
                hdu = self.fits_f[0]
                d = self.hdu_info[0]
                name = d.name
                extver = d.extver
                _numhdu = (name, extver)
                if (len(name) == 0) or (_numhdu not in self.fits_f):
                    numhdu = 0
                else:
                    numhdu = _numhdu

        elif isinstance(numhdu, (int, str)):
            hdu = self.fits_f[numhdu]
            name = hdu.name
            extver = hdu.ver
            _numhdu = (name, extver)
            if (len(name) > 0) and (_numhdu in self.fits_f):
                numhdu = _numhdu

        self.logger.debug("HDU index looks like: %s" % str(numhdu))
        if numhdu not in self.fits_f:
            info = self.hdu_db[numhdu]
            hdu = self.fits_f[info.index]
        else:
            hdu = self.fits_f[numhdu]

        dstobj = self.load_hdu(hdu, dstobj=dstobj, fobj=self.fits_f,
                               **kwargs)

        # Set the name if no name currently exists for this object
        # TODO: should this *change* the existing name, if any?
        name = dstobj.get('name', None)
        if name is None:
            name = self.fileinfo.name
            if '[' not in name:
                name += iohelper.get_hdu_suffix(numhdu)
            dstobj.set(name=name)

        dstobj.set(path=self.fileinfo.filepath, idx=numhdu)

        return dstobj

    def create_fits(self, data, header):
        fits_f = pyfits.HDUList()
        hdu = pyfits.PrimaryHDU()
        hdu.data = data

        for kwd in header.keys():
            card = header.get_card(kwd)
            hdu.header[card.key] = (card.value, card.comment)

        fits_f.append(hdu)
        return fits_f

    def write_fits(self, path, data, header, **kwargs):
        fits_f = self.create_fits(data, header)
        fits_f.writeto(path, **kwargs)
        fits_f.close()

    def save_as_file(self, filepath, data, header, **kwargs):
        self.write_fits(filepath, data, header, **kwargs)


class FitsioFileHandler(BaseFitsFileHandler):

    def __init__(self, logger):
        if not have_fitsio:
            raise FITSError(
                "Need fitsio module installed to use this file handler")

        super(FitsioFileHandler, self).__init__(logger)
        self.kind = 'fitsio'
        self.hdutypes = {fitsio.IMAGE_HDU: 'ImageHDU',
                         fitsio.BINARY_TBL: 'BinaryTBL',
                         fitsio.ASCII_TBL: 'AsciiTBL',
                         }

    def fromHDU(self, hdu, ahdr):
        header = hdu.read_header()
        for d in header.records():
            if len(d['name']) == 0:
                continue
            ahdr.set_card(d['name'], d['value'], comment=d.get('comment', ''))

    def load_hdu(self, hdu, dstobj=None, **kwargs):
        from ginga import AstroImage  # Put here to avoid circular import

        hduinfo = hdu.get_info()
        hdutype = hduinfo.get('hdutype', None)

        ahdr = AstroImage.AstroHeader()
        self.fromHDU(hdu, ahdr)

        metadata = dict(header=ahdr)
        data = hdu.read()

        if hdutype == fitsio.IMAGE_HDU:
            # <-- data is an image

            if dstobj is None:
                # get model class for this type of object
                obj_class = self.factory_dict.get('image', None)
                if obj_class is None:
                    raise FITSError(
                        "I don't know how to load objects of kind 'image'")

                dstobj = obj_class(logger=self.logger)

            dstobj.load_data(data, metadata=metadata)

        elif hdutype in (fitsio.ASCII_TBL, fitsio.BINARY_TBL):
            # <-- data is a table
            raise FITSError(
                "FITS tables are not yet readable using ginga/fitsio")

        return dstobj

    def load_file(self, filespec, numhdu=None, dstobj=None, memmap=None,
                  **kwargs):
        inherit_primary_header = kwargs.pop('inherit_primary_header', False)
        opener = self.get_factory()
        opener.open_file(filespec, memmap=memmap, **kwargs)
        try:
            return opener.get_hdu(
                numhdu, dstobj=dstobj,
                inherit_primary_header=inherit_primary_header)
        finally:
            opener.close()

    def open_file(self, filespec, memmap=None, **kwargs):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise FITSError("File does not appear to be on disk: %s" % (
                info.url))

        self.fileinfo = info
        filepath = info.filepath

        self.logger.debug("Loading file '%s' ..." % (filepath))
        fits_f = fitsio.FITS(filepath, memmap=memmap)
        self.fits_f = fits_f

        extver_db = {}
        self.extver_db = extver_db
        self.hdu_info = []
        self.hdu_db = {}

        for idx in range(len(fits_f)):
            hdu = fits_f[idx]
            hduinfo = hdu.get_info()
            name = hduinfo['extname']
            extver = hduinfo['extver']
            extver_db[name] = extver

            # prepare a record of pertinent info about the HDU for
            # lookups by numerical index or (NAME, EXTVER)
            d = Bunch.Bunch(index=idx, name=name, extver=extver)
            hdutype = self.hdutypes.get(hduinfo['hdutype'], 'UNKNOWN')
            d.setvals(htype=hdutype,
                      dtype=str(hduinfo.get('img_type', None)))
            self.hdu_info.append(d)
            # different ways of accessing this HDU:
            # by numerical index
            self.hdu_db[idx] = d
            # by (hduname, extver)
            self.hdu_db[(name, extver)] = d

    def close(self):
        self.hdu_info = None
        self.hdu_db = {}
        self.extver_db = {}
        self.info = None
        self.fits_f = None

    def __len__(self):
        return len(self.hdu_info)

    def get_hdu(self, numhdu, dstobj=None, **kwargs):

        if numhdu is None:
            found_valid_hdu = False
            for i, d in enumerate(self.hdu_info):
                name = d.name
                extver = d.extver
                hdu = self.fits_f[i]
                hduinfo = hdu.get_info()

                if not ('ndims' in hduinfo) or (hduinfo['ndims'] == 0):
                    # compressed FITS file or non-pixel data hdu?
                    continue

                if not hasattr(hdu, 'read'):
                    continue
                data = hdu.read()

                if not isinstance(data, numpy.ndarray):
                    # We need to open a numpy array
                    continue

                if 0 in data.shape:
                    # non-pixel or zero-length data hdu?
                    continue

                # Looks good, let's try it
                found_valid_hdu = True
                if len(name) == 0:
                    numhdu = i
                else:
                    numhdu = (name, extver)
                break

            if not found_valid_hdu:
                # Just load the header
                hdu = self.fits_f[0]
                d = self.hdu_info[0]
                name = d.name
                extver = d.extver
                if len(name) == 0:
                    numhdu = 0
                else:
                    numhdu = (name, extver)

        elif isinstance(numhdu, (int, str)):
            hdu = self.fits_f[numhdu]
            hduinfo = hdu.get_info()
            name = hduinfo['extname']
            extver = hduinfo['extver']
            if len(name) > 0:
                numhdu = (name, extver)

        self.logger.debug("HDU index looks like: %s" % str(numhdu))
        hdu = self.fits_f[numhdu]

        dstobj = self.load_hdu(hdu, dstobj=dstobj, fobj=self.fits_f,
                               **kwargs)

        # Set the name if no name currently exists for this object
        # TODO: should this *change* the existing name, if any?
        name = dstobj.get('name', None)
        if name is None:
            name = self.fileinfo.name
            if '[' not in name:
                name += iohelper.get_hdu_suffix(numhdu)
            dstobj.set(name=name)

        dstobj.set(path=self.fileinfo.filepath, idx=numhdu)

        return dstobj

    def create_fits(self, data, header):
        fits_f = pyfits.HDUList()
        hdu = pyfits.PrimaryHDU()
        hdu.data = data

        for kwd in header.keys():
            card = header.get_card(kwd)
            hdu.header.update(card.key, card.value, comment=card.comment)

        fits_f.append(hdu)
        return fits_f

    def write_fits(self, path, data, header):
        fits_f = fitsio.FITS(path, 'rw')

        fits_f = self.create_fits(data, header)
        fits_f.writeto(path, output_verify='fix')
        fits_f.close()

    def save_as_file(self, filepath, data, header, **kwargs):
        self.write_fits(filepath, data, header, **kwargs)


if not fits_configured:
    # default
    fitsLoaderClass = PyFitsFileHandler

    # try to use them in this order
    # astropy is faster
    for name in ('astropy', 'fitsio'):
        if use(name, raise_err=False):
            break


def get_fitsloader(kind=None, logger=None):
    return fitsLoaderClass(logger)

# END
