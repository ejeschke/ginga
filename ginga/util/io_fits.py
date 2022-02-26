#
# io_fits.py -- Module wrapper for loading FITS files.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
There are two possible choices for a python FITS file reading package
compatible with Ginga: astropy and fitsio.

To force the use of one programmatically, do:

    from ginga.util import io_fits
    io_fits.use('package')

(replace 'package' with one of {'astropy', 'fitsio'}) before you load
any images.  Otherwise Ginga will try to pick one for you.
"""
import re
import numpy as np
import warnings

from ginga.AstroImage import AstroImage, AstroHeader
from ginga.table.AstroTable import AstroTable

from ginga.misc import Bunch
from ginga.util import iohelper
from ginga.util.io import io_base

fits_configured = False
fitsLoaderClass = None

try:
    from astropy.io import fits as pyfits
    from astropy.table import Table
    have_astropy = True
except ImportError:
    have_astropy = False

try:
    import fitsio
    have_fitsio = True
except ImportError as e:
    have_fitsio = False


class FITSError(Exception):
    pass


def use(fitspkg, raise_err=True):
    global fits_configured, fitsLoaderClass

    if fitspkg == 'astropy':
        if have_astropy:
            fitsLoaderClass = AstropyFitsFileHandler
            fits_configured = True
            return True

        elif raise_err:
            raise ImportError("Error importing 'astropy.io.fits'; "
                              "please check installation")

        return False

    elif fitspkg == 'fitsio':
        if have_fitsio:
            fitsLoaderClass = FitsioFileHandler
            fits_configured = True
            return True

        elif raise_err:
            raise ImportError("Error importing 'fitsio'; "
                              "please check installation")

        return False

    return False


class BaseFitsFileHandler(io_base.BaseIOHandler):

    # TODO: remove in a future version
    @classmethod
    def register_type(cls, name, klass):
        raise Exception("This method has been deprecated;"
                        "you don't need to call it anymore.")

    def __init__(self, logger):
        super(BaseFitsFileHandler, self).__init__(logger)

        self.fileinfo = None
        self.fits_f = None
        self.hdu_info = []
        self.hdu_db = {}
        self.extver_db = {}

    def get_factory(self):
        hdlr = self.__class__(self.logger)
        return hdlr

    def __len__(self):
        return len(self.hdu_info)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def load_idx(self, idx, **kwargs):
        if len(self) == 0:
            raise ValueError("Please call open_file() first!")

        return self.get_hdu(idx, **kwargs)

    def load_idx_cont(self, idx_spec, loader_cont_fn, **kwargs):
        """
        Parameters
        ----------
        idx_spec : str
            A string in the form of a pair of brackets enclosing some
            index expression matching HDUs in the file

        loader_cont_fn : func (data_obj) -> None
            A loader continuation function that takes a data object
            generated from loading an HDU and does something with it

        kwargs : optional keyword arguments
            Any optional keyword arguments are passed to the code that
            loads the data from the file
        """
        if len(self) == 0:
            raise ValueError("Please call open_file() first!")

        idx_lst = list(self.get_matching_indexes(idx_spec))
        if len(idx_lst) == 0:
            raise ValueError("Spec {} matches no data objects in file".format(idx_spec))

        for idx in idx_lst:
            try:
                dst_obj = self.load_idx(idx, **kwargs)

                loader_cont_fn(dst_obj)

            except Exception as e:
                self.logger.error("Error loading index '%s': %s" % (idx, str(e)),
                                  exc_info=True)

    def get_matching_indexes(self, idx_spec):
        """
        Parameters
        ----------
        idx_spec : str
            A string in the form of a pair of brackets enclosing some
            index expression matching HDUs in the file

        Returns
        -------
        result : list
            A list of HDU indexes that can be used to access each HDU
            matching the pattern
        """
        # if index is missing, assume to open the first HDU we know how
        # to do something with
        if idx_spec is None or idx_spec == '':
            idx, hdu = self.find_first_good_hdu()
            return [idx]

        if isinstance(idx_spec, int):
            return [idx_spec]

        match = re.match(r'^\[(.+)\]$', idx_spec)
        if not match:
            return []

        idx_spec = match.group(1).strip()
        if ',' in idx_spec:
            name, extver = idx_spec.split(',')
            name, extver = name.strip(), extver.strip()
        else:
            name, extver = idx_spec.strip(), None

        name = name.upper()

        if extver is None:
            if re.match(r'^\d+$', name):
                # index just names a single HDU by number
                return [int(name)]

            # <-- assume name is an HDU name and extver is 1
            extver = '1'

        # find all HDU's matching the name and extver
        idx_lst = []
        idx = 0
        for info in self.hdu_info:
            if name == '*' or name == info.name:
                if extver == '*' or extver == str(info.extver):
                    idx_lst.append(info.index)

        return idx_lst

    def get_directory(self):
        return self.hdu_db

    def get_info_idx(self, idx):
        return self.hdu_db[idx]


class AstropyFitsFileHandler(BaseFitsFileHandler):

    name = 'astropy.fits'

    def __init__(self, logger):
        if not have_astropy:
            raise FITSError(
                "Need astropy module installed to use this file handler")

        super(AstropyFitsFileHandler, self).__init__(logger)
        self.kind = 'pyfits'

    def copy_header(self, hdu, ahdr):
        """Copy a FITS header from an astropy.io.fits.PrimaryHDU object
        into a ginga.AstroImage.AstroHeader object.
        """
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

    def get_hdu_type(self, hdu):
        if isinstance(hdu, (pyfits.ImageHDU,
                            pyfits.CompImageHDU,
                            pyfits.PrimaryHDU,
                            )):
            return 'image'

        elif isinstance(hdu, (pyfits.TableHDU,
                              pyfits.BinTableHDU)):
            return 'table'

        return None

    def load_hdu(self, hdu, dstobj=None, fobj=None, naxispath=None,
                 save_primary_header=False, inherit_primary_header=False,
                 **kwargs):
        if fobj is None:
            fobj = self.fits_f

        save_primary_header = save_primary_header or inherit_primary_header
        # Set PRIMARY header
        if save_primary_header and fobj is not None:
            primary_hdr = AstroHeader()
            self.copy_header(fobj[0], primary_hdr)
        else:
            primary_hdr = None

        typ = self.get_hdu_type(hdu)
        if typ == 'image':

            if dstobj is None:
                dstobj = AstroImage(logger=self.logger)
            else:
                if not isinstance(dstobj, AstroImage):
                    raise ValueError("dstobj needs to be a type of AstroImage")
                dstobj.clear_metadata()

            # this seems to be necessary now for some fits files...
            try:
                hdu.verify('fix')

            except Exception as e:
                # Let's hope for the best!
                self.logger.warning("Problem verifying fits HDU: {}".format(e))

            # collect HDU header
            ahdr = dstobj.get_header()
            self.copy_header(hdu, ahdr)
            dstobj.set(primary_header=primary_hdr,
                       inherit_primary_header=inherit_primary_header)

            dstobj.setup_data(hdu.data, naxispath=naxispath)

            # Try to make a wcs object on the header
            wcs = getattr(dstobj, 'wcs', None)
            if wcs is not None:
                wcs.load_header(hdu.header, fobj=fobj)

        elif typ == 'table':
            # <-- data may be a table

            if hdu.name == 'ASDF':
                if dstobj is not None:
                    raise ValueError("It is not supported to load ASDF HDU with dstobj != None")

                self.logger.debug('Attempting to load {} extension from '
                                  'FITS'.format(hdu.name))
                from ginga.util.io import io_asdf
                opener = io_asdf.ASDFFileHandler(self.logger)
                return opener.load_asdf_hdu_in_fits(self.fits_f, hdu, **kwargs)

            if dstobj is None:
                dstobj = AstroTable(logger=self.logger)
            else:
                if not isinstance(dstobj, AstroTable):
                    raise ValueError("dstobj needs to be a type of AstroTable")
                dstobj.clear_metadata()

            dstobj.kind = 'table-astropy'

            self.logger.debug('Attempting to load table from FITS')

            ahdr = dstobj.get_header()
            self.copy_header(hdu, ahdr)
            dstobj.set(primary_header=primary_hdr,
                       inherit_primary_header=inherit_primary_header)

            if 'format' not in kwargs:
                kwargs['format'] = 'fits'

            try:
                data = Table.read(hdu, **kwargs)
                dstobj.set_data(data)
                dstobj.colnames = list(data.colnames)

            except Exception as e:
                self.logger.error("Error reading table from hdu: {0}".format(e),
                                  exc_info=True)

        else:
            raise FITSError("I don't know how to read this HDU")

        dstobj.io = self

        return dstobj

    def load_file(self, filespec, numhdu=None, dstobj=None, memmap=None,
                  save_primary_header=False, inherit_primary_header=False,
                  **kwargs):

        opener = self.get_factory()
        opener.open_file(filespec, memmap=memmap, **kwargs)
        try:
            return opener.get_hdu(
                numhdu, dstobj=dstobj,
                save_primary_header=save_primary_header,
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
            self.logger.warning("Problem verifying fits file '%s': %s" % (
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
                d.setvals(htype=tup[3], dtype=tup[6])
            self.hdu_info.append(d)
            # different ways of accessing this HDU:
            # by numerical index
            self.hdu_db[idx] = d
            # by (hduname, extver)
            key = (name, extver)
            if key not in self.hdu_db:
                self.hdu_db[key] = d
            idx += 1

        self.extver_db = extver_db
        return self

    def close(self):
        self.hdu_info = None
        self.hdu_db = {}
        self.extver_db = {}
        self.info = None
        fits_f = self.fits_f
        self.fits_f = None
        fits_f.close()

    def find_first_good_hdu(self):

        found_valid_hdu = False
        for i, d in enumerate(self.hdu_info):
            name = d.name
            hdu = self.fits_f[i]

            # rule out HDUs we can't deal with
            typ = self.get_hdu_type(hdu)
            if typ not in ('image', 'table'):
                continue

            if not isinstance(hdu.data, np.ndarray):
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

        return (numhdu, hdu)

    def get_hdu(self, numhdu, dstobj=None, **kwargs):

        if numhdu is None:
            numhdu, hdu = self.find_first_good_hdu()

        elif numhdu in self.hdu_db:
            d = self.hdu_db[numhdu]
            hdu = self.fits_f[d.index]
            # normalize the index
            numhdu = (d.name, d.extver)

        else:
            hdu = self.fits_f[numhdu]
            # normalize the hdu index, if possible
            name = hdu.name
            extver = hdu.ver
            _numhdu = (name, extver)
            if ((len(name) > 0) and (_numhdu in self.fits_f) and
                hdu is self.fits_f[_numhdu]):
                numhdu = _numhdu

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

    def fromHDU(self, hdu, ahdr):
        warnings.warn("fromHDU will be deprecated in the next release--"
                      "use copy_header instead",
                      DeprecationWarning)
        return self.copy_header(hdu, ahdr)


# TO BE DEPRECATED
PyFitsFileHandler = AstropyFitsFileHandler


class FitsioFileHandler(BaseFitsFileHandler):

    name = 'fitsio'

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
        self.hdu_info = []
        self.hdu_db = {}

    def copy_header(self, hdu, ahdr):
        """Copy a FITS header from an fitsio.hdu object
        into a ginga.AstroImage.AstroHeader object.
        """
        header = hdu.read_header()
        for d in header.records():
            if len(d['name']) == 0:
                continue
            ahdr.set_card(d['name'], d['value'], comment=d.get('comment', ''))

    def get_hdu_type(self, hdu):
        hduinfo = hdu.get_info()
        hdutype = hduinfo.get('hdutype', None)
        if hdutype == fitsio.IMAGE_HDU:
            return 'image'

        elif hdutype in (fitsio.ASCII_TBL, fitsio.BINARY_TBL):
            return 'table'

        return None

    def load_hdu(self, hdu, dstobj=None, fobj=None, naxispath=None,
                 save_primary_header=False, inherit_primary_header=False,
                 **kwargs):
        if fobj is None:
            fobj = self.fits_f

        save_primary_header = save_primary_header or inherit_primary_header
        # Set PRIMARY header
        if save_primary_header and fobj is not None:
            primary_hdr = AstroHeader()
            self.copy_header(fobj[0], primary_hdr)
        else:
            primary_hdr = None

        typ = self.get_hdu_type(hdu)

        if typ == 'image':
            # <-- data is an image
            if dstobj is None:
                dstobj = AstroImage(logger=self.logger)
            else:
                if not isinstance(dstobj, AstroImage):
                    raise ValueError("dstobj needs to be a type of AstroImage")
                dstobj.clear_metadata()

            ahdr = dstobj.get_header()
            self.copy_header(hdu, ahdr)
            dstobj.set(primary_header=primary_hdr,
                       inherit_primary_header=inherit_primary_header)

            data = hdu.read()

            dstobj.setup_data(data, naxispath=naxispath)

            # Try to make a wcs object on the header
            wcs = getattr(dstobj, 'wcs', None)
            if wcs is not None:
                # NOTE: WCS packages don't know what to do with fitsio objects
                wcs.load_header(ahdr.asdict(), fobj=None)

        elif typ == 'table':
            # <-- data is a table
            if dstobj is None:
                dstobj = AstroTable(logger=self.logger)
            else:
                if not isinstance(dstobj, AstroTable):
                    raise ValueError("dstobj needs to be a type of AstroTable")
                dstobj.clear_metadata()

            ahdr = dstobj.get_header()
            self.copy_header(hdu, ahdr)
            dstobj.set(primary_header=primary_hdr,
                       inherit_primary_header=inherit_primary_header)

            dstobj.kind = 'table-fitsio'

            data = hdu.read()
            dstobj.colnames = list(data.dtype.fields)
            dstobj.set_data(data)

        dstobj.io = self

        return dstobj

    def load_file(self, filespec, numhdu=None, dstobj=None, memmap=None,
                  save_primary_header=False, inherit_primary_header=False,
                  **kwargs):

        opener = self.get_factory()
        opener.open_file(filespec, memmap=memmap, **kwargs)
        try:
            return opener.get_hdu(
                numhdu, dstobj=dstobj,
                save_primary_header=save_primary_header,
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
            # figure out the EXTVER for this HDU
            #extver = hduinfo['extver']
            extver = extver_db.setdefault(name, 0)
            extver += 1
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
            key = (name, extver)
            if len(name) > 0 and extver >= 0 and key not in self.hdu_db:
                self.hdu_db[key] = d

        return self

    def close(self):
        self.hdu_info = []
        self.hdu_db = {}
        self.extver_db = {}
        self.info = None
        self.fits_f = None

    def find_first_good_hdu(self):

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

            if not isinstance(data, np.ndarray):
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

        return numhdu, hdu

    def get_hdu(self, numhdu, dstobj=None, **kwargs):

        if numhdu is None:
            numhdu, hdu = self.find_first_good_hdu()

        elif numhdu in self.hdu_db:
            d = self.hdu_db[numhdu]
            hdu = self.fits_f[d.index]
            # normalize the index
            numhdu = (d.name, d.extver)

        else:
            hdu = self.fits_f[numhdu]
            # normalize the hdu index, if possible
            hduinfo = hdu.get_info()
            name = hduinfo['extname']
            extver = hduinfo['extver']
            _numhdu = (name, extver)
            if ((len(name) > 0) and (_numhdu in self.fits_f) and
                hdu is self.fits_f[_numhdu]):
                numhdu = _numhdu

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
        raise NotImplementedError("This function is not implemented for the 'fitsio' wrapper")

    def write_fits(self, path, data, header):
        fits_f = fitsio.FITS(path, 'rw')

        hlist = []
        for key in header.keys():
            card = header.get_card(key)
            hlist.append(dict(name=key, value=card.value,
                              comment=card.comment))

        fits_f.write(data, header=hlist)
        fits_f.close()

    def save_as_file(self, filepath, data, header, **kwargs):
        self.write_fits(filepath, data, header, **kwargs)

    def fromHDU(self, hdu, ahdr):
        warnings.warn("fromHDU will be deprecated in the next release--"
                      "use copy_header instead",
                      DeprecationWarning)
        return self.copy_header(hdu, ahdr)


if not fits_configured:
    if have_astropy:
        # default
        fitsLoaderClass = AstropyFitsFileHandler

    elif have_fitsio:
        fitsLoaderClass = FitsioFileHandler


def get_fitsloader(kind=None, logger=None):
    if kind is not None:
        if kind == 'fitsio':
            return FitsioFileHandler(logger)
        else:
            return AstropyFitsFileHandler(logger)

    return fitsLoaderClass(logger)


def load_file(filepath, idx=None, logger=None, **kwargs):
    """
    Load an object from a FITS file.

    """
    opener = get_fitsloader(logger=logger)
    return opener.load_file(filepath, numhdu=idx, **kwargs)
