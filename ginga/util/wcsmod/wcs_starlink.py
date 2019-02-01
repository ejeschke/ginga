#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import starlink.Ast as Ast
import starlink.Atl as Atl  # noqa

import numpy as np

from ginga.util.wcsmod import common

coord_types = ['icrs', 'fk5', 'fk4', 'galactic', 'ecliptic']


class StarlinkWCS(common.BaseWCS):
    """
    A WCS interface for Starlink
    You need to install python module 'starlink-pyast'
    (http://www.astro.rug.nl/software/kapteyn/)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(StarlinkWCS, self).__init__(logger)

        self.kind = 'starlink'

    def load_header(self, header, fobj=None):
        self.header = {}
        self.header.update(header.items())

        self.fix_bad_headers()

        source = []
        for key, value in header.items():
            source.append("%-8.8s= %-70.70s" % (key, repr(value)))

        # following https://gist.github.com/dsberry/4171277 to get a
        # usable WCS in Ast

        try:
            self.logger.debug("Trying to make starlink wcs object")
            # read in the header and create the default WCS transform
            # adapter = Atl.PyFITSAdapter(hdu)
            # fitschan = Ast.FitsChan(adapter)
            fitschan = Ast.FitsChan(source)
            self.wcs = fitschan.read()
            # self.wcs is a FrameSet, with a Mapping
            # self.wcs.Report = True

            self.coordsys = common.get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

        try:
            # define a transform from this destination frame to icrs/j2000
            refframe = self.wcs.getframe(2)
            toframe = Ast.SkyFrame("System=ICRS, Equinox=J2000")
            self.icrs_trans = refframe.convert(toframe)

        except Exception as e:
            self.logger.error("Error making ICRS transform: %s" % (str(e)))

    def spectral_coord(self, idxs, coords='data'):
        # Starlink's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = np.array(map(lambda x: x + 1, idxs))
        else:
            idxs = np.array(idxs)

        try:
            # pixel to sky coords (in the WCS specified transform)
            arrs = [[idxs[i]] for i in range(len(idxs))]
            res = self.wcs.tran(arrs, 1)
            return res[2][0]

        except Exception as e:
            self.logger.error(
                "Error calculating spectral coordinate: %s" % (str(e)))
            raise common.WCSError(e)

    def pixtoradec(self, idxs, coords='data'):
        # Starlink's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = np.array(list(map(lambda x: x + 1, idxs)))
        else:
            idxs = np.array(idxs)

        try:
            # pixel to sky coords (in the WCS specified transform)
            arrs = [[idxs[i]] for i in range(len(idxs))]
            res = self.wcs.tran(arrs, 1)

            if self.coordsys not in ('pixel', 'raw'):
                # whatever sky coords to icrs coords
                res = self.icrs_trans.tran(res, 1)
            # TODO: what if axes are inverted?
            ra_rad, dec_rad = res[0][0], res[1][0]
            ra_deg, dec_deg = np.degrees(ra_rad), np.degrees(dec_rad)
            # print(ra_deg, dec_deg)

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise common.WCSError(e)

        return ra_deg, dec_deg

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        try:
            # sky coords to pixel (in the WCS specified transform)
            ra_rad, dec_rad = np.radians(ra_deg), np.radians(dec_deg)
            # TODO: what if spatial axes are inverted?
            args = [ra_rad, dec_rad]
            if naxispath:
                args += [0] * len(naxispath)
            arrs = [[args[i]] for i in range(len(args))]
            # 0 as second arg -> inverse transform
            res = self.wcs.tran(arrs, 0)
            x, y = res[0][0], res[1][0]

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise common.WCSError(e)

        if coords == 'data':
            # Starlink's WCS returns pixels referenced from 1
            x, y = x - 1, y - 1

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
            # these will actually be x, y pixel values
            return (ra_deg, dec_deg)

        # define a transform from reference (icrs/j2000) to user's end choice
        refframe = self.icrs_trans.getframe(2)
        toframe = Ast.SkyFrame("System=%s, Epoch=2000.0" % (system.upper()))
        end_trans = refframe.convert(toframe)

        # convert to alternate coord
        ra_rad, dec_rad = np.radians(ra_deg), np.radians(dec_deg)
        res = end_trans.tran([[ra_rad], [dec_rad]], 1)
        lon_rad, lat_rad = res[0][0], res[1][0]
        lon_deg, lat_deg = np.degrees(lon_rad), np.degrees(lat_rad)

        return lon_deg, lat_deg

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):

        # force to array representation
        datapt = np.asarray(datapt)

        # Starlink's WCS needs pixels referenced from 1
        if coords == 'data':
            datapt = datapt + 1.0

        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                datapt = np.hstack((datapt, np.zeros((len(datapt), n))))

        try:
            # 1 as second arg -> regular transform
            wcspt = self.wcs.tran(datapt.T, 1)

            if self.coordsys not in ('pixel', 'raw'):
                # whatever sky coords to icrs coords
                wcspt = self.icrs_trans.tran(wcspt, 1)

        except Exception as e:
            self.logger.error(
                "Error calculating datapt_to_wcspt: %s" % (str(e)))
            raise common.WCSError(e)

        # Starlink returns angles in radians
        wcspt = np.degrees(wcspt.T)
        return wcspt

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):

        # force to array representation
        wcspt = np.asarray(wcspt)

        # Starlink works on angles in radians
        wcspt = np.radians(wcspt)

        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                wcspt = np.hstack((wcspt, np.zeros((len(wcspt), n))))

        try:
            # 0 as second arg -> inverse transform
            datapt = self.wcs.tran(wcspt.T, 0)

        except Exception as e:
            self.logger.error(
                "Error calculating wcspt_to_datapt: %s" % (str(e)))
            raise common.WCSError(e)

        if coords == 'data':
            # Starlink's WCS returns pixels referenced from 1
            datapt = datapt - 1.0

        return datapt.T

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

        # define a transform from reference (icrs/j2000) to user's end choice
        refframe = self.icrs_trans.getframe(2)
        toframe = Ast.SkyFrame("System=%s, Epoch=2000.0" % (system.upper()))
        end_trans = refframe.convert(toframe)

        # convert to alternate coord
        wcspt = np.radians(wcspt)
        wcspt = end_trans.tran(wcspt.T, 1)
        wcspt = np.degrees(wcspt)

        return wcspt.T


# register our WCS with ginga
common.register_wcs('starlink', StarlinkWCS, coord_types)
