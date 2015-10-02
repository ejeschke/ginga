#
# io_fits.py -- Module wrapper for loading FITS files.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
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

from ginga.util import iohelper

fits_configured = False
fitsLoaderClass = None
have_pyfits = False
have_fitsio = False

class FITSError(Exception):
    pass

def use(fitspkg, raise_err=True):
    global fits_configured, fitsLoaderClass, \
           have_pyfits, pyfits, \
           have_fitsio, fitsio

    if fitspkg == 'astropy':
        try:
            from astropy.io import fits as pyfits
            have_pyfits = True
            fitsLoaderClass = PyFitsFileHandler
            return True

        except ImportError:
            try:
                # maybe they have a standalone version of pyfits?
                import pyfits
                have_pyfits = True
                fitsLoaderClass = PyFitsFileHandler
                return True

            except ImportError as e:
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
    # Reserved for future use
    pass

class PyFitsFileHandler(BaseFitsFileHandler):

    def __init__(self, logger):
        super(PyFitsFileHandler, self).__init__()

        if not have_pyfits:
            raise FITSError("Need astropy or pyfits module installed to use this file handler")
        self.logger = logger
        self.kind = 'pyfits'

    def fromHDU(self, hdu, ahdr):
        header = hdu.header
        if hasattr(header, 'cards'):
            # newer astropy.io.fits don't have ascardlist()
            for card in header.cards:
                if len(card.keyword) == 0:
                    continue
                bnch = ahdr.__setitem__(card.keyword, card.value)
                bnch.comment = card.comment
        else:
            for card in header.ascardlist():
                if len(card.key) == 0:
                    continue
                bnch = ahdr.__setitem__(card.key, card.value)
                bnch.comment = card.comment

    def load_hdu(self, hdu, ahdr, fobj=None, naxispath=None):
        data = hdu.data
        if data is None:
            data = numpy.zeros((0, 0))
        elif not isinstance(data, numpy.ndarray):
            data = numpy.zeros((0, 0))
        elif 0 in data.shape:
            data = numpy.zeros((0, 0))
        elif len(data.shape) < 2:
            # Expand 1D arrays into 1xN array
            data = data.reshape((1, data.shape[0]))
        else:
            if naxispath is None:
                naxispath = []
            else:
                # Drill down naxispath
                for idx in naxispath:
                    data = data[idx]

        self.fromHDU(hdu, ahdr)
        return (data, naxispath)

    def load_file(self, filespec, ahdr, numhdu=None, naxispath=None,
                  phdr=None):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise FITSError("File does not appear to be on disk: %s" % (
                info.url))
        filepath = info.filepath

        self.logger.debug("Loading file '%s' ..." % (filepath))
        fits_f = pyfits.open(filepath, 'readonly')

        # this seems to be necessary now for some fits files...
        try:
            fits_f.verify('fix')
        except Exception as e:
            raise FITSError("Error loading fits file '%s': %s" % (
                filepath, str(e)))

        if numhdu is None:
            found_valid_hdu = False
            for numhdu in range(len(fits_f)):
                hdu = fits_f[numhdu]
                if (hdu.data is None) or (0 in hdu.data.shape):
                    # non-pixel or zero-length data hdu?
                    continue
                if not isinstance(hdu.data, numpy.ndarray):
                    # We need to open a numpy array
                    continue
                #print "data type is %s" % hdu.data.dtype.kind
                # Looks good, let's try it
                found_valid_hdu = True
                break

            if not found_valid_hdu:
                ## raise FITSError("No data HDU found that Ginga can open in '%s'" % (
                ##     filepath))
                # Load just the header
                numhdu = 0

        hdu = fits_f[numhdu]

        data, naxispath = self.load_hdu(hdu, ahdr, fobj=fits_f,
                                        naxispath=naxispath)

        # Read PRIMARY header
        if phdr is not None:
            self.fromHDU(fits_f[0], phdr)

        fits_f.close()
        return (data, numhdu, naxispath)

    def create_fits(self, data, header):
        fits_f = pyfits.HDUList()
        hdu = pyfits.PrimaryHDU()
        hdu.data = data

        for kwd in header.keys():
            card = header.get_card(kwd)
            hdu.header.update(card.key, card.value, comment=card.comment)

        fits_f.append(hdu)
        return fits_f

    def write_fits(self, path, data, header, **kwdargs):
        fits_f = self.create_fits(data, header)
        fits_f.writeto(path, **kwdargs)
        fits_f.close()

    def save_as_file(self, filepath, data, header, **kwdargs):
        self.write_fits(filepath, data, header, **kwdargs)


class FitsioFileHandler(BaseFitsFileHandler):

    def __init__(self, logger):
        super(FitsioFileHandler, self).__init__()

        if not have_fitsio:
            raise FITSError("Need fitsio module installed to use this file handler")
        self.logger = logger
        self.kind = 'fitsio'

    def fromHDU(self, hdu, ahdr):
        header = hdu.read_header()
        for d in header.records():
            if len(d['name']) == 0:
                continue
            bnch = ahdr.__setitem__(d['name'], d['value'])
            bnch.comment = d['comment']

    def load_hdu(self, hdu, ahdr, fobj=None, naxispath=None):
        data = hdu.read()
        if data is None:
            data = numpy.zeros((0, 0))
        elif not isinstance(data, numpy.ndarray):
            data = numpy.zeros((0, 0))
        elif 0 in data.shape:
            data = numpy.zeros((0, 0))
        elif len(data.shape) < 2:
            # Expand 1D arrays into 1xN array
            data = data.reshape((1, data.shape[0]))
        else:
            if naxispath is None:
                naxispath = []
            else:
                # Drill down naxispath
                for idx in naxispath:
                    data = data[idx]

        self.fromHDU(hdu, ahdr)
        return (data, naxispath)

    def load_file(self, filespec, ahdr, numhdu=None, naxispath=None,
                  phdr=None):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise FITSError("File does not appear to be on disk: %s" % (
                info.url))
        filepath = info.filepath

        self.logger.debug("Loading file '%s' ..." % (filepath))
        fits_f = fitsio.FITS(filepath)

        if numhdu is None:
            found_valid_hdu = False
            for numhdu in range(len(fits_f)):
                hdu = fits_f[numhdu]
                info = hdu.get_info()
                if not ('ndims' in info) or (info['ndims'] == 0):
                    # compressed FITS file or non-pixel data hdu?
                    continue
                #print "data type is %s" % hdu.data.dtype.kind
                # Looks good, let's try it
                found_valid_hdu = True
                break

            if not found_valid_hdu:
                ## raise FITSError("No data HDU found that Ginga can open in '%s'" % (
                ##     filepath))
                # Just load the header
                numhdu = 0

        hdu = fits_f[numhdu]

        data, naxispath = self.load_hdu(hdu, ahdr, fobj=fits_f,
                                        naxispath=naxispath)

        # Read PRIMARY header
        if phdr is not None:
            self.fromHDU(fits_f[0], phdr)

        fits_f.close()
        return (data, numhdu, naxispath)

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

    def save_as_file(self, filepath, data, header, **kwdargs):
        self.write_fits(filepath, data, header, **kwdargs)


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

#END
