#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

import astropy.wcs as pywcs
from astropy.io import fits as pyfits
from astropy import coordinates, units

# Note: Relative import breaks test in PY2
from ginga.util.six.moves import map
from ginga.util.wcsmod import common

if hasattr(coordinates, 'SkyCoord'):
    try:
        import sunpy.coordinates  # noqa
    except ImportError:
        pass
    coord_types = [f.name for f in
                   coordinates.frame_transform_graph.frame_set]
else:
    coord_types = ['icrs', 'fk5', 'fk4', 'galactic']


class AstropyWCS(common.BaseWCS):
    """
    A WCS interface for astropy.wcs
    You need to install python module 'astropy'
    (http://pypi.python.org/pypi/astropy)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(AstropyWCS, self).__init__(logger)

        self.new_coords = False            # new astropy coordinate system

        if hasattr(coordinates, 'SkyCoord'):
            # v0.4 series astropy and later
            self.new_coords = True

        elif hasattr(coordinates, 'ICRS'):
            # v0.3 series astropy
            self.coord_table = {
                'icrs': coordinates.ICRS,
                'fk5': coordinates.FK5,
                'fk4': coordinates.FK4,
                'galactic': coordinates.Galactic,
            }

        else:
            # v0.2 series astropy
            self.coord_table = {
                'icrs': coordinates.ICRSCoordinates,
                'fk5': coordinates.FK5Coordinates,
                'fk4': coordinates.FK4Coordinates,
                'galactic': coordinates.GalacticCoordinates,
            }
        self.kind = 'astropy/WCSLIB'

    def load_header(self, header, fobj=None):
        try:
            # reconstruct a pyfits header, because otherwise we take an
            # incredible performance hit in astropy.wcs
            self.logger.debug("Reconstructing PyFITS header")
            self.header = pyfits.Header(header.items())

            self.logger.debug("Trying to make astropy-- wcs object")
            self.wcs = pywcs.WCS(self.header, fobj=fobj, relax=True)
            self.logger.debug("made astropy wcs object")

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
            pix = self.wcs.wcs_world2pix(skycrd, origin)

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

        if not self.new_coords:
            # convert to astropy coord
            try:
                fromclass = self.coord_table[self.coordsys]
            except KeyError:
                raise common.WCSError("No such coordinate system available: '%s'" % (
                    self.coordsys))

            coord = fromclass(ra_deg, dec_deg,
                              unit=(units.degree, units.degree))

            if (system is None) or (system == self.coordsys):
                return coord

            # Now give it back to the user in the system requested
            try:
                toclass = self.coord_table[system]
            except KeyError:
                raise common.WCSError("No such coordinate system available: '%s'" % (
                    system))

            coord = coord.transform_to(toclass)

        else:
            frameClass = coordinates.frame_transform_graph.lookup_name(
                self.coordsys)
            coord = frameClass(ra_deg * units.degree, dec_deg * units.degree)
            toClass = coordinates.frame_transform_graph.lookup_name(system)
            # Skip in input and output is the same (no realize_frame
            # call in astropy)
            if toClass != frameClass:
                coord = coord.transform_to(toClass)

        return coord

    def _deg(self, coord):
        # AstroPy changed the API so now we have to support more
        # than one--we don't know what version the user has installed!
        if hasattr(coord, 'degrees'):
            return coord.degrees
        else:
            return coord.degree

    def pixtosystem(self, idxs, system=None, coords='data'):
        if self.coordsys == 'pixel':
            x, y = self.pixtoradec(idxs, coords=coords)
            return (x, y)

        c = self.pixtocoords(idxs, system=system, coords=coords)
        if not self.new_coords:
            # older astropy
            return (self._deg(c.lonangle), self._deg(c.latangle))
        else:
            r = c.data
            return tuple(map(self._deg, [getattr(r, component)
                                         for component in r.components[:2]]))

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
            datapt = self.wcs.all_world2pix(wcspt, origin)
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

        if not self.new_coords:
            raise NotImplementedError

        else:
            frameClass = coordinates.frame_transform_graph.lookup_name(
                self.coordsys)
            ra_deg = wcspt[:, 0]
            dec_deg = wcspt[:, 1]
            coord = frameClass(ra_deg * units.degree, dec_deg * units.degree)
            toClass = coordinates.frame_transform_graph.lookup_name(system)
            # Skip if input and output is the same (no realize_frame
            # call in astropy)
            if toClass != frameClass:
                coord = coord.transform_to(toClass)

        return coord


# register our WCS with ginga
common.register_wcs('astropy', AstropyWCS, coord_types)
