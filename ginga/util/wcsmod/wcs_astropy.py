#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

import astropy.wcs as pywcs
from astropy.io import fits as pyfits
from astropy import coordinates, units

from ginga.util.wcsmod import common

try:
    import sunpy.coordinates  # noqa
except ImportError:
    pass
coord_types = [f.name for f in
               coordinates.frame_transform_graph.frame_set]


class AstropyWCS(common.BaseWCS):
    """
    A WCS interface for astropy.wcs
    You need to install python module 'astropy'
    (http://pypi.python.org/pypi/astropy)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(AstropyWCS, self).__init__(logger)
        self.kind = 'astropy/WCSLIB'

    def load_header(self, header, fobj=None):
        try:
            # reconstruct a pyfits header, because otherwise we take an
            # incredible performance hit in astropy.wcs
            self.logger.debug("Reconstructing astropy.io.fits header")
            self.header = pyfits.Header(header.items())

            self.logger.debug("Trying to make astropy-- wcs object")
            self.wcs = pywcs.WCS(self.header, fobj=fobj, relax=True)
            self.logger.debug("made astropy wcs object")

            self.coordsys = common.get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def load_nddata(self, ndd):
        try:
            # reconstruct a pyfits header, because otherwise we take an
            # incredible performance hit in astropy.wcs
            self.logger.debug("Reconstructing astropy.io.fits header")
            self.header = pyfits.Header(ndd.meta)

            if ndd.wcs is None:
                self.logger.debug("Trying to make astropy FITS WCS object")
                self.wcs = pywcs.WCS(self.header, relax=True)
                self.logger.debug("made astropy wcs object")
            else:
                self.logger.debug("reused nddata wcs object")
                self.wcs = ndd.wcs

            self.coordsys = common.get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def spectral_coord(self, idxs, coords='data'):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = np.array([idxs], np.float_)
        try:
            sky = self.wcs.all_pix2world(pixcrd, origin)
            return float(sky[0, 2])

        except Exception as e:
            self.logger.error(
                "Error calculating spectral coordinate: %s" % (str(e)))
            raise common.WCSError(e)

    def pixtoradec(self, idxs, coords='data'):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = np.array([idxs], np.float_)
        try:
            # sky = self.wcs.wcs_pix2sky(pixcrd, origin)
            # sky = self.wcs.all_pix2sky(pixcrd, origin)
            # astropy only?
            sky = self.wcs.all_pix2world(pixcrd, origin)

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise common.WCSError(e)

        ra_deg = float(sky[0, 0])
        dec_deg = float(sky[0, 1])

        return ra_deg, dec_deg

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):

        if coords == 'data':
            origin = 0
        else:
            origin = 1

        args = [ra_deg, dec_deg]
        if naxispath:
            args += [0] * len(naxispath)
        skycrd = np.array([args], np.float_)

        try:
            pix = self.wcs.all_world2pix(skycrd, origin, maxiter=20,
                                         detect_divergence=True, quiet=False)

        except pywcs.NoConvergence as e:
            pix = e.best_solution

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise common.WCSError(e)

        x = float(pix[0, 0])
        y = float(pix[0, 1])
        return (x, y)

    def pixtocoords(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise common.WCSError("No usable WCS")

        if system is None:
            system = 'icrs'

        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, coords=coords)
        self.logger.debug("ra, dec = %f, %f" % (ra_deg, dec_deg))

        frame_class = coordinates.frame_transform_graph.lookup_name(
            self.coordsys)
        coord = frame_class(ra_deg * units.degree, dec_deg * units.degree)
        to_class = coordinates.frame_transform_graph.lookup_name(system)
        # Skip in input and output is the same (no realize_frame
        # call in astropy)
        if to_class != frame_class:
            coord = coord.transform_to(common.get_astropy_frame(to_class))

        return coord

    def pixtosystem(self, idxs, system=None, coords='data'):
        if self.coordsys == 'pixel':
            return self.pixtoradec(idxs, coords=coords)

        c = self.pixtocoords(idxs, system=system, coords=coords)
        r = c.data.represent_as(coordinates.UnitSphericalRepresentation)
        return r.lon.deg, r.lat.deg

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                datapt = np.hstack((datapt, np.zeros((len(datapt), n))))
        try:
            wcspt = self.wcs.all_pix2world(datapt, origin)
        except Exception as e:
            self.logger.error(
                "Error calculating datapt_to_wcspt: %s" % (str(e)))
            raise common.WCSError(e)

        return wcspt

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                wcspt = np.hstack((wcspt, np.zeros((len(wcspt), n))))
        try:
            datapt = self.wcs.all_world2pix(wcspt, origin, maxiter=20,
                                            detect_divergence=True, quiet=False)

        except pywcs.NoConvergence as e:
            datapt = e.best_solution

        except Exception as e:
            self.logger.error(
                "Error calculating wcspt_to_datapt: %s" % (str(e)))
            raise common.WCSError(e)

        return datapt[:, :2]

    def datapt_to_system(self, datapt, system=None, coords='data',
                         naxispath=None):
        """
        Map points to given coordinate system.

        Parameters
        ----------
        datapt : array-like
            Pixel coordinates in the format of
            ``[[x0, y0, ...], [x1, y1, ...], ..., [xn, yn, ...]]``.

        system : str or None, optional, default to 'icrs'
            Coordinate system name.

        coords : 'data' or None, optional, default to 'data'
            Expresses whether the data coordinate is indexed from zero

        naxispath : list-like or None, optional, defaults to None
            A sequence defining the pixel indexes > 2D, if any

        Returns
        -------
        coord : SkyCoord

        """
        if self.coordsys == 'raw':
            raise common.WCSError("No usable WCS")

        if system is None:
            system = 'icrs'

        wcspt = self.datapt_to_wcspt(datapt, coords=coords,
                                     naxispath=naxispath)

        frame_class = coordinates.frame_transform_graph.lookup_name(
            self.coordsys)
        ra_deg = wcspt[:, 0]
        dec_deg = wcspt[:, 1]
        coord = frame_class(ra_deg * units.degree, dec_deg * units.degree)
        to_class = coordinates.frame_transform_graph.lookup_name(system)
        # Skip if input and output is the same (no realize_frame
        # call in astropy)
        if to_class != frame_class:
            coord = coord.transform_to(common.get_astropy_frame(to_class))

        return coord


# register our WCS with ginga
common.register_wcs('astropy', AstropyWCS, coord_types)
