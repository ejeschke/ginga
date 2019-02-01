#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from astLib import astWCS, astCoords
# astlib requires pyfits (or astropy) in order
# to create a WCS object from a FITS header.
from astropy.io import fits as pyfits

from ginga.util.wcsmod import common

astWCS.NUMPY_MODE = True

coord_types = ['j2000', 'b1950', 'galactic']


class AstLibWCS(common.BaseWCS):
    """
    A WCS interface for astLib.astWCS.WCS
    You need to install python module 'astLib'
    (http://sourceforge.net/projects/astlib)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(AstLibWCS, self).__init__(logger)

        self.kind = 'astlib/wcstools'

    def load_header(self, header, fobj=None):
        self.header = {}
        self.header.update(header.items())

        self.fix_bad_headers()

        try:
            # reconstruct a pyfits header
            hdr = pyfits.Header(header.items())

            self.logger.debug("Trying to make astLib wcs object")
            self.wcs = astWCS.WCS(hdr, mode='pyfits')

            self.coordsys = self.get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def get_coord_system_name(self, header):
        coordsys = common.get_coord_system_name(header)
        coordsys = coordsys.upper()
        if coordsys in ('FK4',):
            return 'b1950'
        elif coordsys in ('FK5', 'ICRS'):
            return 'j2000'
        elif coordsys in ('PIXEL',):
            return 'pixel'

        #raise common.WCSError("Cannot determine appropriate coordinate system from FITS header")  # noqa
        return 'j2000'

    def spectral_coord(self, idxs, coords='data'):
        raise common.WCSError("This feature not supported by astWCS")

    def pixtoradec(self, idxs, coords='data'):
        if coords == 'fits':
            # Via astWCS.NUMPY_MODE, we've forced pixels referenced from 0
            idxs = tuple(map(lambda x: x - 1, idxs))

        try:
            ra_deg, dec_deg = self.wcs.pix2wcs(idxs[0], idxs[1])

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise common.WCSError(e)

        return ra_deg, dec_deg

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        try:
            x, y = self.wcs.wcs2pix(ra_deg, dec_deg)

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise common.WCSError(e)

        if coords == 'fits':
            # Via astWCS.NUMPY_MODE, we've forced pixels referenced from 0
            x, y = x + 1, y + 1

        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise common.WCSError("No usable WCS")

        if system is None:
            system = 'j2000'

        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, coords=coords)
        self.logger.debug("ra, dec = %f, %f" % (ra_deg, dec_deg))

        # convert to alternate coord
        try:
            fromsys = self.coordsys.upper()

            if fromsys == 'PIXEL':
                # these are really pixel values
                return (ra_deg, dec_deg)

            tosys = system.upper()

            if fromsys == 'B1950':
                equinox = 1950.0
            else:
                equinox = 2000.0

            lon_deg, lat_deg = astCoords.convertCoords(fromsys, tosys,
                                                       ra_deg, dec_deg,
                                                       equinox)
        except Exception as e:
            raise common.WCSError(
                "Error converting between coordinate systems "
                "'%s' and '%s': %s" % (fromsys, tosys, str(e)))

        return (lon_deg, lat_deg)


# register our WCS with ginga
common.register_wcs('astlib', AstLibWCS, coord_types)
