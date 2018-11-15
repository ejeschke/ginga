#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np
from astropy import coordinates

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
    A WCS interface for astropy.wcs as defined by Astropy APE 14.
    You need to install python module 'astropy'
    (http://pypi.python.org/pypi/astropy) v3.1 or later
    if you want to use this version.

    """
    def __init__(self, logger):
        super(AstropyWCS, self).__init__(logger)
        self.kind = 'astropy/APE14'

        # NOTE: self.wcs magically set in loader right now.
        # TODO: Implement load_header

    # TODO: Use coords?
    def pixtoradec(self, idxs, coords='data'):
        coord = self.wcs.pixel_to_world(*idxs)
        return coord.ra.deg, coord.dec.deg

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        coord = coordinates.SkyCoord(ra_deg, dec_deg, unit='deg')
        return self.wcs.world_to_pixel(coord)

    def pixtocoords(self, idxs, system=None, coords='data'):
        if self.coordsys == 'raw':
            raise common.WCSError("No usable WCS")

        if system is None:
            system = 'icrs'

        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, coords=coords)
        self.logger.debug("ra, dec = {}, {}".format(ra_deg, dec_deg))

        frame_class = coordinates.frame_transform_graph.lookup_name(
            self.coordsys)
        coord = frame_class(ra_deg, dec_deg, unit='deg')
        to_class = coordinates.frame_transform_graph.lookup_name(system)
        # Skip in input and output is the same (no realize_frame
        # call in astropy)
        if to_class != frame_class:
            coord = coord.transform_to(to_class)

        return coord

    # TODO: Remove this
    def _deg(self, coord):
        # AstroPy changed the API so now we have to support more
        # than one--we don't know what version the user has installed!
        if hasattr(coord, 'degrees'):
            return coord.degrees
        else:
            return coord.degree

    def pixtosystem(self, idxs, system=None, coords='data'):
        if self.coordsys == 'pixel':
            return self.pixtoradec(idxs, coords=coords)

        c = self.pixtocoords(idxs, system=system, coords=coords)
        r = c.data
        return tuple(map(self._deg, [getattr(r, component)
                                     for component in r.components[:2]]))

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                datapt = np.hstack((datapt, np.zeros((len(datapt), n))))
        try:
            wcspt = self.wcs.pixel_to_world(datapt)
        except Exception as e:
            self.logger.error(
                "Error calculating datapt_to_wcspt: {}".format(str(e)))
            raise common.WCSError(e)

        return wcspt

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        if naxispath is not None:
            n = len(naxispath)
            if n > 0:
                wcspt = np.hstack((wcspt, np.zeros((len(wcspt), n))))
        try:
            datapt = self.wcs.world_to_pixel(wcspt)
        except Exception as e:
            self.logger.error(
                "Error calculating wcspt_to_datapt: %s" % (str(e)))
            raise common.WCSError(e)

        return datapt[:, :2]


# register our WCS with ginga
common.register_wcs('astropy_ape14', AstropyWCS, coord_types)
