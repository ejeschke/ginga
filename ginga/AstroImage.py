#
# AstroImage.py -- Abstraction of an astronomical data image.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import traceback
import warnings
from collections import OrderedDict

import numpy as np

from ginga.util import wcs, wcsmod
from ginga.BaseImage import BaseImage, ImageError, Header


class AstroHeader(Header):
    pass


class AstroImage(BaseImage):
    """
    Abstraction of an astronomical data (image).

    NOTE: this module is NOT thread-safe!
    """
    # class variables for WCS and IO can be set
    wcsClass = None
    ioClass = None

    @classmethod
    def set_wcsClass(cls, klass):
        cls.wcsClass = klass

    @classmethod
    def set_ioClass(cls, klass):
        cls.ioClass = klass

    def __init__(self, data_np=None, metadata=None, logger=None,
                 name=None, wcsclass=None, ioclass=None,
                 inherit_primary_header=False, save_primary_header=True):

        BaseImage.__init__(self, data_np=data_np, metadata=metadata,
                           logger=logger, name=name)

        # wcsclass specifies a pluggable WCS module
        if wcsclass is None:
            if self.wcsClass is None:
                wcsclass = wcsmod.WCS
            else:
                wcsclass = self.wcsClass
        self.wcs = wcsclass(self.logger)

        # ioclass specifies a pluggable IO module
        if ioclass is None:
            if self.ioClass is None:
                from ginga.util import io_fits
                ioclass = io_fits.fitsLoaderClass
            else:
                ioclass = self.ioClass

        self.io = ioclass(self.logger)

        self.inherit_primary_header = inherit_primary_header
        self.save_primary_header = inherit_primary_header or save_primary_header
        if self.save_primary_header:
            # User wants to save/inherit from primary header--this will hold it
            self._primary_hdr = AstroHeader()
        else:
            self._primary_hdr = None

        if metadata is not None:
            header = self.get_header()
            self.wcs.load_header(header)

        # For navigating multidimensional data
        self.naxispath = []
        self.revnaxis = []
        self._md_data = None

    def setup_data(self, data, naxispath=None):
        # initialize data attribute to something reasonable
        if data is None:
            data = np.zeros((0, 0))
        elif not isinstance(data, np.ndarray):
            data = np.zeros((0, 0))
        elif 0 in data.shape:
            data = np.zeros((0, 0))

        # this is a handle to the full data array
        self._md_data = data
        self.axisdim = data.shape

        # this will get reset in set_naxispath() if array is
        # multidimensional
        self._data = self._md_data

        if naxispath is None:
            naxispath = []

        # Set naxispath to drill down to first 2D data slice
        if len(naxispath) == 0:
            naxispath = ([0] * (len(data.shape) - 2))

        self.set_naxispath(naxispath)

    def load_hdu(self, hdu, fobj=None, naxispath=None,
                 inherit_primary_header=None):

        # this seems to be necessary now for some fits files...
        try:
            hdu.verify('fix')

        except Exception as e:
            # Let's hope for the best!
            self.logger.warning("Problem verifying fits HDU: {}".format(e))

        self.clear_metadata()

        # collect HDU header
        ahdr = self.get_header()
        self._copy_hdu_header(hdu, ahdr)

        # Set PRIMARY header
        if inherit_primary_header is None:
            inherit_primary_header = self.inherit_primary_header
        else:  # This ensures get_header() is consistent
            self.inherit_primary_header = inherit_primary_header

        save_primary_header = (self.save_primary_header or
                               inherit_primary_header)
        if save_primary_header and (fobj is not None):
            if self._primary_hdr is None:
                self._primary_hdr = AstroHeader()

            self._copy_hdu_header(fobj[0], self._primary_hdr)

        self.setup_data(hdu.data, naxispath=naxispath)

        # Try to make a wcs object on the header
        if hasattr(self, 'wcs') and self.wcs is not None:
            self.wcs.load_header(hdu.header, fobj=fobj)

    def load_nddata(self, ndd, naxispath=None):
        """Load from an astropy.nddata.NDData object.
        """
        self.clear_metadata()

        # Make a header based on any NDData metadata
        ahdr = self.get_header()
        ahdr.update(ndd.meta)

        self.setup_data(ndd.data, naxispath=naxispath)

        if ndd.wcs is None:
            # no wcs in ndd obj--let's try to make one from the header
            self.wcs = wcsmod.WCS(logger=self.logger)
            self.wcs.load_header(ahdr)
        else:
            # already have a valid wcs in the ndd object
            # we assume it needs an astropy compatible wcs
            wcsinfo = wcsmod.get_wcs_class('astropy')
            self.wcs = wcsinfo.wrapper_class(logger=self.logger)
            self.wcs.load_nddata(ndd)

    def load_file(self, filespec, **kwargs):

        if self.io is None:
            raise ImageError("No IO loader defined")

        self.io.load_file(filespec, dstobj=self, **kwargs)

    def load_data(self, data_np, naxispath=None, metadata=None):

        self.clear_metadata()

        self.setup_data(data_np, naxispath=naxispath)

        if metadata is not None:
            self.update_metadata(metadata)

    def load_buffer(self, buf, dims, dtype, byteswap=False,
                    naxispath=None, metadata=None):
        data = np.frombuffer(buf, dtype=dtype)
        if byteswap:
            data.byteswap(True)
        data = data.reshape(dims)

        self.load_data(data, naxispath=naxispath, metadata=metadata)

    def get_mddata(self):
        return self._md_data

    def set_naxispath(self, naxispath):
        """Choose a slice out of multidimensional data.
        """
        revnaxis = list(naxispath)
        revnaxis.reverse()

        # construct slice view and extract it
        ndim = min(self.ndim, 2)
        view = tuple(revnaxis + [slice(None)] * ndim)
        data = self.get_mddata()[view]

        if len(data.shape) not in (1, 2):
            raise ImageError(
                "naxispath does not lead to a 1D or 2D slice: {}".format(naxispath))

        self.naxispath = naxispath
        self.revnaxis = revnaxis

        self.set_data(data)

    def set_wcs(self, wcs):
        self.wcs = wcs

    def set_io(self, io):
        self.io = io

    def get_data_size(self):
        return self.get_size()

    def get_header(self, create=True, include_primary_header=None):
        try:
            # By convention, the fits header is stored in a dictionary
            # under the metadata keyword 'header'
            hdr = self.metadata['header']

            if include_primary_header is None:
                include_primary_header = self.inherit_primary_header

            if include_primary_header and self._primary_hdr is not None:
                # Inherit PRIMARY header for display but keep metadata intact
                displayhdr = AstroHeader()
                for key in hdr.keyorder:
                    card = hdr.get_card(key)
                    bnch = displayhdr.__setitem__(card.key, card.value)
                    bnch.comment = card.comment
                for key in self._primary_hdr.keyorder:
                    if key not in hdr:
                        card = self._primary_hdr.get_card(key)
                        bnch = displayhdr.__setitem__(card.key, card.value)
                        bnch.comment = card.comment
            else:
                # Normal, separate header
                displayhdr = hdr

        except KeyError as e:
            if not create:
                raise e
            hdr = AstroHeader()
            self.metadata['header'] = hdr
            displayhdr = hdr

        return displayhdr

    def get_keyword(self, kwd, *args):
        """Get an item from the fits header, if any."""
        try:
            kwds = self.get_header()
            return kwds[kwd]
        except KeyError:
            # return a default if there is one
            if len(args) > 0:
                return args[0]
            raise KeyError(kwd)

    def get_keywords_list(self, *args):
        return list(map(self.get_keyword, args))

    def set_keyword(self, kwd, value, create=True):
        kwds = self.get_header(create=create)
        kwd = kwd.upper()
        if not create:
            prev = kwds[kwd]  # noqa, this raises KeyError
        kwds[kwd] = value

    def update_keywords(self, key_dict):
        hdr = self.get_header()
        # Upcase all keywords
        for kwd, val in key_dict.items():
            hdr[kwd.upper()] = val

        # Try to make a wcs object on the header
        if hasattr(self, 'wcs') and self.wcs is not None:
            self.wcs.load_header(hdr)

    def set_keywords(self, **kwds):
        """Set an item in the fits header, if any."""
        return self.update_keywords(kwds)

    def update_data(self, data_np, metadata=None, astype=None):
        """DO NOT USE: this method will be deprecated!
        """
        self.set_data(data_np.copy(), metadata=metadata,
                      astype=astype)

    def update_metadata(self, key_dict):
        for key, val in key_dict.items():
            self.metadata[key] = val

        # refresh the WCS
        if hasattr(self, 'wcs') and self.wcs is not None:
            header = self.get_header()
            self.wcs.load_header(header)

    def has_primary_header(self):
        return self._primary_hdr is not None

    def clear_all(self):
        # clear metadata and data
        super(AstroImage, self).clear_all()

        # unreference full data array
        self._md_data = self._data

    def transfer(self, other, astype=None):
        data = self._get_data()
        other.update_data(data, astype=astype)
        other.update_metadata(self.metadata)

    def copy(self, astype=None):
        data = self._get_data()
        other = AstroImage(data, logger=self.logger)
        self.transfer(other, astype=astype)
        return other

    def as_nddata(self, nddata_class=None):
        "Return a version of ourself as an astropy.nddata.NDData object"
        if nddata_class is None:
            from astropy.nddata import NDData
            nddata_class = NDData

        # transfer header, preserving ordering
        ahdr = self.get_header()
        header = OrderedDict(ahdr.items())
        data = self.get_mddata()

        wcs = None
        if hasattr(self, 'wcs') and self.wcs is not None:
            # for now, assume self.wcs wraps an astropy wcs object
            wcs = self.wcs.wcs

        ndd = nddata_class(data, wcs=wcs, meta=header)
        return ndd

    def as_hdu(self):
        "Return a version of ourself as an astropy.io.fits.PrimaryHDU object"
        from astropy.io import fits

        # transfer header, preserving ordering
        ahdr = self.get_header()
        header = fits.Header(ahdr.items())
        data = self.get_mddata()

        hdu = fits.PrimaryHDU(data=data, header=header)
        return hdu

    def _copy_hdu_header(self, hdu, ahdr):
        """Copy a FITS header from an astropy.io.fits.PrimaryHDU object
        into a ginga.AstroImage.AstroHeader object.
        """
        header = hdu.header
        for card in header.cards:
            if len(card.keyword) == 0:
                continue
            ahdr.set_card(card.keyword, card.value, comment=card.comment)

    def astype(self, type_name):
        """Convert AstroImage object to some other kind of object.
        """
        if type_name == 'nddata':
            return self.as_nddata()

        if type_name == 'hdu':
            return self.as_hdu()

        raise ValueError("Unrecognized conversion type '%s'" % (type_name))

    def save_as_file(self, filepath, **kwdargs):
        data = self._get_data()
        header = self.get_header()
        self.io.save_as_file(filepath, data, header, **kwdargs)

    def pixtocoords(self, x, y, system=None, coords='data'):
        args = [x, y] + self.revnaxis
        return self.wcs.pixtocoords(args, system=system, coords=coords)

    def spectral_coord(self, coords='data'):
        args = [0, 0] + self.revnaxis
        return self.wcs.spectral_coord(args, coords=coords)

    def pixtoradec(self, x, y, format='deg', coords='data'):
        args = [x, y] + self.revnaxis
        ra_deg, dec_deg = self.wcs.pixtoradec(args, coords=coords)

        if format == 'deg':
            return ra_deg, dec_deg
        return wcs.deg2fmt(ra_deg, dec_deg, format)

    def radectopix(self, ra_deg, dec_deg, format='deg', coords='data'):
        if format != 'deg':
            # convert coordinates to degrees
            ra_deg = wcs.lon_to_deg(ra_deg)
            dec_deg = wcs.lat_to_deg(dec_deg)
        return self.wcs.radectopix(ra_deg, dec_deg, coords=coords,
                                   naxispath=self.revnaxis)

    # -----> TODO:
    #   This section has been merged into ginga.util.wcs or
    #   ginga.util.mosaic .  Deprecate it here.
    #
    def get_starsep_XY(self, x1, y1, x2, y2):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.get_starsep_XY(self, x1, y1, x2, y2)

    def calc_radius_xy(self, x, y, radius_deg):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.calc_radius_xy(self, x, y, radius_deg)

    def calc_radius_deg2pix(self, ra_deg, dec_deg, delta_deg,
                            equinox=None):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.calc_radius_deg2pix(self, ra_deg, dec_deg, delta_deg,
                                       equinox=equinox)

    def add_offset_xy(self, x, y, delta_deg_x, delta_deg_y):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.add_offset_xy(self, x, y, delta_deg_x, delta_deg_y)

    def calc_radius_center(self, delta_deg):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.calc_radius_center(self, delta_deg)

    def calc_compass(self, x, y, len_deg_e, len_deg_n):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.calc_compass(self, x, y, len_deg_e, len_deg_n)

    def calc_compass_radius(self, x, y, radius_px):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.calc_compass_radius(self, x, y, radius_px)

    def calc_compass_center(self):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.wcs",
                      PendingDeprecationWarning)
        return wcs.calc_compass_center(self)

    def get_wcs_rotation_deg(self):
        warnings.warn("This function has been deprecated--"
                      "use get_rotation_and_scale in ginga.util.wcs",
                      PendingDeprecationWarning)
        header = self.get_header()
        (rot, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header)
        return rot

    def mosaic_inline(self, imagelist, bg_ref=None, trim_px=None,
                      merge=False, allow_expand=True, expand_pad_deg=0.01,
                      max_expand_pct=None,
                      update_minmax=True, suppress_callback=False):
        warnings.warn("This function has been deprecated--"
                      "use the version in ginga.util.mosaic",
                      PendingDeprecationWarning)
        from ginga.util import mosaic
        return mosaic.mosaic_inline(self, imagelist, bg_ref=bg_ref,
                                    trim_px=trim_px, merge=merge,
                                    allow_expand=allow_expand,
                                    expand_pad_deg=expand_pad_deg,
                                    max_expand_pct=max_expand_pct,
                                    update_minmax=update_minmax,
                                    suppress_callback=suppress_callback)
    #
    # <----- TODO: deprecate

    def info_xy(self, data_x, data_y, settings):
        info = super(AstroImage, self).info_xy(data_x, data_y, settings)

        system = settings.get('wcs_coords', None)
        format = settings.get('wcs_display', 'sexagesimal')
        ra_lbl, dec_lbl = chr(945), chr(948)

        # Calculate WCS coords, if available
        try:
            if self.wcs is None:
                self.logger.debug("No WCS for this image")
                ra_txt = dec_txt = 'NO WCS'

            elif self.wcs.coordsys == 'raw':
                self.logger.debug("No coordinate system determined")
                ra_txt = dec_txt = 'NO WCS'

            elif self.wcs.coordsys == 'pixel':
                args = [data_x, data_y] + self.revnaxis
                x, y = self.wcs.pixtosystem(args, system=system, coords='data')
                ra_txt = "%+.3f" % (x)
                dec_txt = "%+.3f" % (y)
                ra_lbl, dec_lbl = "X", "Y"

            else:
                args = [data_x, data_y] + self.revnaxis

                lon_deg, lat_deg = self.wcs.pixtosystem(
                    args, system=system, coords='data')

                if format == 'sexagesimal':
                    if system in ('galactic', 'ecliptic'):
                        sign, deg, min, sec = wcs.degToDms(lon_deg,
                                                           isLatitude=False)
                        ra_txt = '+%03d:%02d:%06.3f' % (deg, min, sec)
                    else:
                        deg, min, sec = wcs.degToHms(lon_deg)
                        ra_txt = '%02d:%02d:%06.3f' % (deg, min, sec)

                    sign, deg, min, sec = wcs.degToDms(lat_deg)
                    if sign < 0:
                        sign = '-'
                    else:
                        sign = '+'
                    dec_txt = '%s%02d:%02d:%06.3f' % (sign, deg, min, sec)

                else:
                    ra_txt = '%+10.7f' % (lon_deg)
                    dec_txt = '%+10.7f' % (lat_deg)

                if system == 'galactic':
                    ra_lbl, dec_lbl = "l", "b"
                elif system == 'ecliptic':
                    ra_lbl, dec_lbl = chr(0x03BB), chr(0x03B2)
                elif system == 'helioprojective':
                    ra_txt = "%+5.3f" % (lon_deg * 3600)
                    dec_txt = "%+5.3f" % (lat_deg * 3600)
                    ra_lbl, dec_lbl = "x-Solar", "y-Solar"

        except Exception as e:
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = dec_txt = 'BAD WCS'
            try:
                # log traceback, if possible
                (type_, value_, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))
            except Exception:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)

        info.update(dict(itype='astro', ra_txt=ra_txt, dec_txt=dec_txt,
                         ra_lbl=ra_lbl, dec_lbl=dec_lbl))
        return info

# END
