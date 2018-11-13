#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np
from kapteyn import wcs as kapwcs

from ginga.util.wcsmod import common

coord_types = ['icrs', 'fk5', 'fk4', 'galactic', 'ecliptic']


class KapteynWCS(common.BaseWCS):
    """
    A WCS interface for kapteyn.wcs.Projection
    You need to install python module 'kapteyn'
    (http://www.astro.rug.nl/software/kapteyn/)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(KapteynWCS, self).__init__(logger)

        self.kind = 'kapteyn/WCSLIB'
        self._skyout = "equatorial icrs J2000.0"

        # see: https://github.com/astropy/coordinates-benchmark/blob/master/kapteyn/convert.py  # noqa
        self.conv_d = dict(fk5='fk5', fk4='fk4,J2000_OBS', icrs='icrs',
                           galactic='galactic', ecliptic='ecliptic,J2000')

    def load_header(self, header, fobj=None):
        # For kapteyn, header just needs to be duck-typed like a dict
        self.header = {}
        self.header.update(header.items())

        self.fix_bad_headers()

        try:
            self.logger.debug("Trying to make kapteyn wcs object")
            self.wcs = kapwcs.Projection(self.header,
                                         skyout=self._skyout)

            self.coordsys = common.get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def spectral_coord(self, idxs, coords='data'):
        # Kapteyn's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = tuple(map(lambda x: x + 1, idxs))
        else:
            idxs = tuple(idxs)

        try:
            res = self.wcs.toworld(idxs)
            if len(res) > 0:
                return res[self.wcs.specaxnum - 1]

        except Exception as e:
            self.logger.error(
                "Error calculating spectral coordinate: %s" % (str(e)))
            raise common.WCSError(e)

    def pixtoradec(self, idxs, coords='data'):
        # Kapteyn's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = tuple(map(lambda x: x + 1, idxs))
        else:
            idxs = tuple(idxs)
        # print("indexes=%s" % (str(idxs)))

        try:
            res = self.wcs.toworld(idxs)
            if ((self.wcs.lonaxnum is not None) and
                    (self.wcs.lataxnum is not None)):
                ra_deg = res[self.wcs.lonaxnum - 1]
                dec_deg = res[self.wcs.lataxnum - 1]
            else:
                ra_deg, dec_deg = res[0], res[1]

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise common.WCSError(e)

        return ra_deg, dec_deg

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        args = [ra_deg, dec_deg]
        if naxispath:
            args += [0] * len(naxispath)
        args = tuple(args)

        try:
            pix = self.wcs.topixel(args)

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise common.WCSError(e)

        if coords == 'data':
            # Kapteyn's WCS returns pixels referenced from 1
            pix = tuple(map(lambda x: x - 1, pix))

        x, y = pix[0], pix[1]
        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise common.WCSError("No usable WCS")

        if system is None:
            system = 'icrs'

        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, coords=coords)
        self.logger.debug("ra, dec = %f, %f" % (ra_deg, dec_deg))

        if self.coordsys == 'pixel':
            return (ra_deg, dec_deg)

        # convert to alternate coord
        spec = self.conv_d[system]
        tran = kapwcs.Transformation(self._skyout, spec)
        lon_deg, lat_deg = tran((ra_deg, dec_deg))

        return lon_deg, lat_deg

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):

        # force to array representation
        datapt = np.asarray(datapt)

        # Kapteyn's WCS needs pixels referenced from 1
        if coords == 'data':
            datapt = datapt + 1.0

        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                datapt = np.hstack((datapt, np.zeros((len(datapt), n))))

        try:
            wcspt = self.wcs.toworld(datapt)

        except Exception as e:
            self.logger.error(
                "Error calculating datapt_to_wcspt: %s" % (str(e)))
            raise common.WCSError(e)

        # TODO: swap axes if lon/lat reversed?
        ## if ((self.wcs.lonaxnum is not None) and
        ##         (self.wcs.lataxnum is not None)):

        return wcspt

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):

        # force to array representation
        wcspt = np.asarray(wcspt)

        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                wcspt = np.hstack((wcspt, np.zeros((len(wcspt), n))))

        try:
            datapt = self.wcs.topixel(wcspt)

        except Exception as e:
            self.logger.error(
                "Error calculating wcspt_to_datapt: %s" % (str(e)))
            raise common.WCSError(e)

        if coords == 'data':
            # Kapteyn's WCS returns pixels referenced from 1
            datapt = datapt - 1.0

        return datapt

    def datapt_to_system(self, datapt, system=None, coords='data',
                         naxispath=None):

        if self.coordsys == 'raw':
            raise common.WCSError("No usable WCS")

        if system is None:
            system = 'icrs'

        wcspt = self.datapt_to_wcspt(datapt, coords=coords,
                                     naxispath=naxispath)

        if self.coordsys == 'pixel':
            return wcspt

        # convert to alternate coord
        spec = self.conv_d[system]
        tran = kapwcs.Transformation(self._skyout, spec)

        return tran(wcspt)


# register our WCS with ginga
common.register_wcs('kapteyn', KapteynWCS, coord_types)
