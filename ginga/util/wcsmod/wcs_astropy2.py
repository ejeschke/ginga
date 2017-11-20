#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import absolute_import

import numpy as np

import astropy
import astropy.coordinates
import astropy.wcs as pywcs
import astropy.units as u  # noqa
from astropy.io import fits as pyfits

# Note: Relative import breaks test in PY2
from ginga.util.wcsmod import common

try:
    import sunpy.coordinates  # noqa
except ImportError:
    pass

coord_types = [f.name for f in
               astropy.coordinates.frame_transform_graph.frame_set]


class AstropyWCS2(common.BaseWCS):
    """
    Astropy 1.0+ WCS / Coordinate System
    """

    def __init__(self, logger):
        super(AstropyWCS2, self).__init__(logger)

        self.kind = 'astropy/WCSLIB2'

    def __get_coordsys(self):
        return self.coordsys

    def __set_coordsys(self, system):
        self.coordsys = system

    # We include this here to make this compatible with the other WCSs.
    #    "coordsys" is a bad name in astropy coordinates, and using the name
    #    `coordframe` internally makes it clearer what's going on (see
    #    :ref:`Astropy Coordinates Definitions <astropy:astropy-coordinates-definitions>`).
    #
    coordframe = property(__get_coordsys, __set_coordsys)

    def load_header(self, header, fobj=None):
        from astropy.wcs.utils import wcs_to_celestial_frame
        try:
            # reconstruct a pyfits header, because otherwise we take an
            # incredible performance hit in astropy.wcs
            self.header = pyfits.Header(header.items())

            self.logger.debug("Trying to make astropy wcs object")
            self.wcs = pywcs.WCS(self.header, fobj=fobj, relax=True)
            try:
                self.coordframe = wcs_to_celestial_frame(self.wcs)
            except ValueError:
                sysname = common.get_coord_system_name(self.header)
                if sysname in ('raw', 'pixel'):
                    self.coordframe = sysname
                else:
                    raise

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def valid_transform_frames(self):
        global coord_types

        frames = [f.name for f in
                  astropy.coordinates.frame_transform_graph.frame_set
                  if self.coordframe.is_transformable_to(f)]
        coord_types = frames

    def realize_frame_inplace(self, data):
        """
        Wrap frame.realize_frame_inplace, modify self.coordframe to reflect the
        new coords.

        .. note::
            This is really an ugly hack, which should be in BaseFrame.
            What it is doing is only changing the internal representation of
            the data in a Frame.

            This means that a new frame is not initialized, which is a
            substantial speed improvement.

        Parameters
        ----------
        data : tuple of Quantity
            The coordinate data (assumed unit spherical).

        """
        # If the representation is a subclass of Spherical we need to check for
        # the new _unit_representation attr to give the corresponding unit
        # spherical subclass.
        if (issubclass(self.coordframe.representation,
                       astropy.coordinates.SphericalRepresentation) and
                hasattr(self.coordframe.representation,
                        '_unit_representation')):
            rep = self.coordframe.representation._unit_representation(*data)

        elif issubclass(self.coordframe.representation,
                        astropy.coordinates.UnitSphericalRepresentation):
            rep = self.coordframe.representation(*data)

        else:
            rep = astropy.coordinates.UnitSphericalRepresentation(*data)

        if hasattr(self.coordframe, '_set_data'):
            self.coordframe._set_data(rep)
        else:
            self.coordframe._data = rep

            # need to reset the representation cache b/c we're changing reps
            # directly setting it instead of clearing the dict because it might
            # not exist at all if we're starting from an un-realized frame
            self.coordframe._rep_cache = {(rep.__class__.__name__, False): rep}

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
        return self._frametofloats(self.pixtonative(idxs, coords=coords))

    def pixtonative(self, idxs, coords='data'):
        """
        Convert the pixel value to the native coordinate frame of the header
        """
        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = np.array([idxs], np.float_)

        try:
            sky = self.wcs.all_pix2world(pixcrd, origin)[0] * u.deg
        except Exception as e:
            self.logger.error("Error calculating pixtonative: %s" % (str(e)))
            raise common.WCSError(e)

        # Update our frame with the new data
        self.realize_frame_inplace(sky)

        return self.coordframe

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        import astropy.units as u

        args = [ra_deg, dec_deg]
        if naxispath:
            args += [0] * len(naxispath)
        skycrd = u.Quantity(args, unit=u.deg)

        self.realize_frame_inplace(skycrd)

        return self.nativetopix(coords=coords, naxispath=naxispath)

    def nativetopix(self, coords='data', naxispath=None):
        """
        Take a frame in native coords and transform to pixel coordinates.
        """
        import astropy.units as u

        if coords == 'data':
            origin = 0
        else:
            origin = 1

        r = self.coordframe.data
        data = list([getattr(r, component).to(u.deg).value
                     for component in r.components[:2]])
        if naxispath:
            data += [0] * len(naxispath)
        data = np.array([data])
        pixels = self.wcs.wcs_world2pix(data, origin)[0][:2]

        return pixels

    def pixtocoords(self, idxs, system=None, coords='data'):

        if self.coordframe == 'raw':
            raise common.WCSError("No usable WCS")

        coord = self.pixtonative(idxs, coords=coords)

        if system is None:
            return coord

        toclass = astropy.coordinates.frame_transform_graph.lookup_name(system)

        transform = self.coordframe.is_transformable_to(toclass)
        if transform and transform != 'same':
            coord = coord.transform_to(toclass)
        else:
            self.logger.error(
                "Frame {} is not Transformable to {}, "
                "falling back to {}".format(
                    self.coordframe.name, toclass.name, self.coordframe.name))
#            self.prefs.set("wcs_coords", self.coordframe.name)

        return coord

    def pixtosystem(self, idxs, system=None, coords='data'):
        if self.coordframe == 'pixel':
            x, y = self.pixtoradec(idxs, coords=coords)
            return (x, y)

        c = self.pixtocoords(idxs, system=system, coords=coords)
        return self._frametofloats(c)

    def _frametofloats(self, frame):
        """
        Take any astropy coord frame and return the first two components as
        floats in a tuple.
        """
        r = frame.data
        return tuple([getattr(r, component).value for component in
                      r.components[:2]])


# register our WCS with ginga
common.register_wcs('astropy2', AstropyWCS2, coord_types)
