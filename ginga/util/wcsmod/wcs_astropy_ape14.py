#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np
from astropy import coordinates
from astropy import units as u
from astropy import wcs
from astropy.io import fits
from astropy.wcs import NoConvergence

from ginga.util.wcsmod import common

try:
    import gwcs  # noqa
    HAVE_GWCS = True
except ImportError:
    HAVE_GWCS = False

try:
    import sunpy.coordinates  # noqa
except ImportError:
    pass
coord_types = [f.name for f in
               coordinates.frame_transform_graph.frame_set]


class AstropyWCS(common.BaseWCS):
    """
    A WCS interface for astropy.wcs as defined by Astropy APE 14.
    You need to install python module 'astropy'
    (http://pypi.python.org/pypi/astropy) v3.1 or later
    if you want to use this version.

    """
    def __init__(self, logger):
        super(AstropyWCS, self).__init__(logger)
        self.kind = 'astropy/APE14'
        self.coordsys = 'raw'  # Remove when load_header() sorted out

        # NOTE: self.wcs magically set in loader right now.

    # TODO: This was copied from wcs_astropy.py. Modify to be compatible
    #       with both FITS WCS and GWCS. Needed so FITS WCS still displays
    #       if user chooses this WCSpkg because APE14 is supposed to be
    #       compatible with both. Nadia will have a PR for GWCS soon.
    def load_header(self, header, fobj=None):
        try:
            # reconstruct a FITS because otherwise we take an
            # incredible performance hit in astropy.wcs
            self.logger.debug("Reconstructing astropy.io.fits header")
            self.header = fits.Header(header.items())

            self.logger.debug("Trying to make astropy-- wcs object")
            self.wcs = wcs.WCS(self.header, fobj=fobj, relax=True)
            self.logger.debug("made astropy wcs object")

            self.coordsys = common.get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: {}".format(self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: {}".format(str(e)))
            self.wcs = None

    def load_nddata(self, ndd):
        try:
            # reconstruct a pyfits header, because otherwise we take an
            # incredible performance hit in astropy.wcs
            self.logger.debug("Reconstructing astropy.io.fits header")
            self.header = fits.Header(ndd.meta)

            if ndd.wcs is None:
                self.logger.debug("Trying to make astropy FITS WCS object")
                self.wcs = wcs.WCS(self.header, relax=True)
                self.logger.debug("made astropy wcs object")
            else:
                self.logger.debug("reused nddata wcs object")
                self.wcs = ndd.wcs

            if HAVE_GWCS and isinstance(self.wcs, gwcs.WCS):
                self.coordsys = self.wcs.output_frame.name
            else:  # FITS WCS
                self.coordsys = common.get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: {}".format(self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: {}".format(str(e)))
            self.wcs = None

    def spectral_coord(self, idxs, coords='data'):
        # NOTE: origin is always 0, coords unused.
        pixcrd = np.array([idxs], np.float_)
        try:
            sky = self.wcs.pixel_to_world(
                pixcrd[:, 0], pixcrd[:, 1], pixcrd[:, 2])
            return sky[1].value[0]

        except Exception as e:
            self.logger.error(
                "Error calculating spectral coordinate: {}".format(str(e)))
            raise common.WCSError(e)

    def pixtoradec(self, idxs, coords='data'):
        # NOTE: origin is always 0, coords unused.
        try:
            c = self.wcs.pixel_to_world(*idxs)
            if (isinstance(c, list) and
                    isinstance(c[0], coordinates.SkyCoord)):  # naxis > 2
                c = c[0]
        except Exception as e:
            self.logger.error(
                "Error calculating pixtoradec: {}".format(str(e)))
            raise common.WCSError(e)

        if isinstance(c, coordinates.SkyCoord):
            radec = (c.ra.deg, c.dec.deg)
        else:  # list of Quantity (e.g., from primary header)
            radec = (c[0].value, c[1].value)

        return radec

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        # NOTE: origin is always 0, coords unused.

        args = [ra_deg, dec_deg]
        if naxispath:
            args += [0] * len(naxispath)

        try:
            xy = self.wcs.world_to_pixel_values(*args)[:2]
        except NoConvergence:  # Fall back to pre-APE 14 calculations
            if coords == 'data':
                origin = 0
            else:
                origin = 1
            try:
                pix = self.wcs.wcs_world2pix(np.array([args], np.float_), origin)
            except Exception as e:
                self.logger.error(
                    "Error calculating radectopix: {}".format(str(e)))
                raise common.WCSError(e)
            xy = float(pix[0, 0]), float(pix[0, 1])
        except Exception as e:
            self.logger.error(
                "Error calculating radectopix: {}".format(str(e)))
            raise common.WCSError(e)

        return xy

    def pixtocoords(self, idxs, system=None, coords='data'):
        # NOTE: origin is always 0, coords unused.
        if self.coordsys == 'raw':
            raise common.WCSError("No usable WCS")

        if system is None:
            system = 'icrs'

        # Get a coordinates object based on ra/dec wcs transform
        coord = self.wcs.pixel_to_world(*idxs)
        if isinstance(coord, list):  # naxis > 2
            coord = coord[0]
        to_class = coordinates.frame_transform_graph.lookup_name(system)

        # Skip in input and output is the same (no realize_frame
        # call in astropy)
        if to_class != coord.name:
            coord = coord.transform_to(common.get_astropy_frame(to_class))

        return coord

    def pixtosystem(self, idxs, system=None, coords='data'):
        if self.coordsys == 'pixel':
            return self.pixtoradec(idxs, coords=coords)

        c = self.pixtocoords(idxs, system=system, coords=coords)
        r = c.data.represent_as(coordinates.UnitSphericalRepresentation)
        return r.lon.deg, r.lat.deg

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        # NOTE: origin is always 0, coords unused.
        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                datapt = np.hstack((datapt, np.zeros((len(datapt), n))))
        datapt = np.asarray(datapt)
        try:
            args = [datapt[:, i] for i in range(datapt.shape[1])]
            # NOTE: Ignores system transformation.
            wcspt = np.array(self.wcs.pixel_to_world_values(*args)).T
        except Exception as e:
            self.logger.error(
                "Error calculating datapt_to_wcspt: {}".format(str(e)))
            raise common.WCSError(e)

        return wcspt

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        # NOTE: origin is always 0, coords unused.
        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                wcspt = np.hstack((wcspt, np.zeros((len(wcspt), n))))
        wcspt = np.asarray(wcspt)
        try:
            args = [wcspt[:, i] for i in range(wcspt.shape[1])]
            # NOTE: Ignores system transformation.
            datapt = np.asarray(self.wcs.world_to_pixel_values(*args))[:2, :].T
        except Exception as e:
            self.logger.error(
                "Error calculating wcspt_to_datapt: {}".format(str(e)))
            raise common.WCSError(e)

        return datapt

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
        elif self.coordsys == 'world':
            coordsys = 'icrs'
        else:
            coordsys = self.coordsys

        if system is None:
            system = 'icrs'

        # Get a coordinates object based on ra/dec wcs transform
        wcspt = self.datapt_to_wcspt(datapt, coords=coords,
                                     naxispath=naxispath)
        frame_class = coordinates.frame_transform_graph.lookup_name(coordsys)
        ra_deg = wcspt[:, 0]
        dec_deg = wcspt[:, 1]
        coord = frame_class(ra_deg * u.degree, dec_deg * u.degree)
        to_class = coordinates.frame_transform_graph.lookup_name(system)

        # Skip in input and output is the same (no realize_frame
        # call in astropy)
        if to_class != frame_class:
            coord = coord.transform_to(common.get_astropy_frame(to_class))

        return coord


# register our WCS with ginga
common.register_wcs('astropy_ape14', AstropyWCS, coord_types)
