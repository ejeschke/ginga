#
# wcsmod.py -- module wrapper for WCS calculations.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
We are fortunate to have several possible choices for a python WCS package
compatible with Ginga: astlib, kapteyn, starlink and astropy.
kapteyn and astropy wrap Mark Calabretta's "WCSLIB", astLib wraps
Jessica Mink's "wcstools", and I'm not sure what starlink uses (their own?).

Note that astlib requires pyfits (or astropy) in order to create a WCS
object from a FITS header.

To force the use of one, do:

.. code-block:: python

    from ginga.util import wcsmod
    wcsmod.use('kapteyn')

before you load any images.  Otherwise Ginga will try to pick one for
you.

Note that you can register custom WCS types using the register_wcs()
function.
"""

import math
import re
import numpy as np

from ginga.misc import Bunch
from ginga.util.six.moves import map

__all__ = ['use', 'BaseWCS', 'AstropyWCS2', 'AstropyWCS', 'AstLibWCS',
           'KapteynWCS', 'StarlinkWCS', 'BareBonesWCS', 'choose_coord_units',
           'get_coord_system_name', 'register_wcs']

# Module variables that get configured at module load time
# or when use() is called
coord_types = []
display_types = ['sexagesimal', 'degrees']
wcs_configured = False

have_kapteyn = False
have_astlib = False
have_pywcs = False
have_astropy = False
have_starlink = False

WCS = None
"""Alias to the chosen WCS system."""

# Holds custom WCSes that are registered
custom_wcs = Bunch.caselessDict()

# try to load them in this order until we find one that works.
# If none can be loaded, we default to the BareBones dummy WCS
wcs_try_order = ('kapteyn', 'astropy', 'astropy2', 'starlink', 'astlib')


class WCSError(Exception):
    pass


def use(wcspkg, raise_err=True):
    """Choose WCS package."""
    global coord_types, wcs_configured, WCS
    global have_kapteyn, kapwcs
    global have_astlib, astWCS, astCoords
    global have_starlink, Ast, Atl
    global have_astropy, pywcs, pyfits, astropy, coordinates, units

    if wcspkg == 'kapteyn':
        try:
            from kapteyn import wcs as kapwcs
            coord_types = ['icrs', 'fk5', 'fk4', 'galactic', 'ecliptic']
            have_kapteyn = True
            wcs_configured = True
            WCS = KapteynWCS
            return True

        except ImportError as e:
            if raise_err:
                raise
        return False

    elif wcspkg == 'starlink':
        try:
            import starlink.Ast as Ast
            import starlink.Atl as Atl
            coord_types = ['icrs', 'fk5', 'fk4', 'galactic', 'ecliptic']
            have_starlink = True
            wcs_configured = True
            WCS = StarlinkWCS
            return True

        except ImportError as e:
            if raise_err:
                raise
        return False

    elif wcspkg == 'astlib':
        try:
            from astLib import astWCS, astCoords
            # astlib requires pyfits (or astropy) in order
            # to create a WCS object from a FITS header.
            try:
                from astropy.io import fits as pyfits
            except ImportError:
                try:
                    import pyfits
                except ImportError:
                    raise ImportError("Need pyfits module to use astLib WCS")

            astWCS.NUMPY_MODE = True
            coord_types = ['j2000', 'b1950', 'galactic']
            have_astlib = True
            wcs_configured = True
            WCS = AstLibWCS
            return True

        except ImportError as e:
            if raise_err:
                raise
        return False

    elif wcspkg == 'astropy2':
        try:
            import astropy

            from distutils.version import LooseVersion
            if LooseVersion(astropy.__version__) <= LooseVersion('1'):
                raise ImportError(
                    "astropy2 wrapper requires version 1 of astropy")

            import astropy.coordinates
            import astropy.wcs as pywcs
            from astropy.io import fits as pyfits
            import astropy.units as u  # noqa

        except ImportError:
            if raise_err:
                raise
            return False

        have_pywcs = True
        have_astropy = True
        wcs_configured = True
        WCS = AstropyWCS2

        try:
            import sunpy.coordinates
        except ImportError:
            pass

        coord_types = [f.name for f in
                       astropy.coordinates.frame_transform_graph.frame_set]

        return True

    elif wcspkg == 'astropy':
        try:
            import astropy.wcs as pywcs
            from astropy.io import fits as pyfits
            have_pywcs = True
        except ImportError:
            try:
                import pywcs
                have_pywcs = True  # noqa
            except ImportError as e:
                if raise_err:
                    raise
                return False

        try:
            from astropy import coordinates
            from astropy import units
            have_astropy = True
            wcs_configured = True
            WCS = AstropyWCS

            if hasattr(coordinates, 'SkyCoord'):
                try:
                    import sunpy.coordinates  # noqa
                except ImportError:
                    pass
                coord_types = [f.name for f in
                               coordinates.frame_transform_graph.frame_set]
            else:
                coord_types = ['icrs', 'fk5', 'fk4', 'galactic']

            return True

        except ImportError as e:
            if raise_err:
                raise
        return False

    elif wcspkg == 'barebones':
        coord_types = ['pixel']
        WCS = BareBonesWCS
        wcs_configured = True
        return True

    elif wcspkg in custom_wcs:
        # Custom WCS installed?
        bnch = custom_wcs[wcspkg]
        WCS = bnch.wrapper_class
        coord_types = bnch.coord_types
        wcs_configured = True
        return True

    return False


def register_wcs(name, wrapper_class, coord_types):
    """
    Register a custom WCS wrapper.

    Parameters
    ----------
    name : str
        The name of the custom WCS wrapper

    wrapper_class : subclass of `~ginga.util.wcsmod.BaseWCS`
        The class implementing the WCS wrapper

    coord_types : list of str
        List of names of coordinate types supported by the WCS
    """
    global custom_wcs
    custom_wcs[name] = Bunch.Bunch(name=name,
                                   wrapper_class=wrapper_class,
                                   coord_types=coord_types)


class BaseWCS(object):
    """Base class for WCS."""

    def __init__(self, logger):
        self.logger = logger
        # The header (or WCS parts thereof) that is in a format readable
        # by the WCS package used by the wrapper.
        self.header = None
        # Internal object holding the wrapped WCS object.  This should
        # be None if no valid WCS could be created by the WCS package.
        self.wcs = None
        # Name of the coordinate system defined by the keywords in
        # the header.  "raw" means no system that ginga understands.
        # See types returned by get_coord_system_name()
        self.coordsys = 'raw'

    def load_header(self, header, fobj=None):
        """
        Initializes the internal package WCS from the keywords in
        the WCS header.

        Parameters
        ----------
        header : dict-like
            A dictionary like object mapping WCS keywords to values.

        fobj : object, optional
            A handle to the open object used to load the image.

        This method is called to create and initialize a wrapped WCS
        object from WCS keywords.  It typically will set self.header
        as needed and from that initialize self.wcs

        If the WCS creation fails, self.wcs should be set to None and
        a WCSError raised.

        The value of `fobj` depends on the method used to open the file,
        but will usually be an open handle to the file (e.g. astropy.io.fits)
        """
        pass

    def spectral_coord(self, idxs, coords='data'):
        """
        Map data (pixel) indexes into an element of the WCS coordinate.

        Parameters
        ----------
        idxs : tuple-like
            A sequence of indexes making up a data coordinate

        coords : 'data' or None, optional, default to 'data'
            Expresses whether the data coordinate is indexed from zero

        See `pixtoradec` for discussion of the `idxs` and `coords`
        parameters.

        Returns
        -------
        The spectral coordinate resolved from the wrapped WCS.

        This is usually the WCS value in the third axis of the coordinate
        system defined by the WCS for multidimensional (i.e. > 2D) data.
        """
        pass

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        """
        Convert multiple data points to WCS.

        Parameters
        ----------
        datapt : array-like
            Pixel coordinates in the format of
            ``[[x0, y0, ...], [x1, y1, ...], ..., [xn, yn, ...]]``.

        coords : 'data' or None, optional, default to 'data'
            Expresses whether the data coordinate is indexed from zero.

        naxispath : list-like or None, optional, defaults to None
            A sequence defining the pixel indexes > 2D, if any.

        Returns
        -------
        wcspt : array-like
            WCS coordinates in the format of
            ``[[ra0, dec0], [ra1, dec1], ..., [ran, decn]]``.

        """
        pass

    def pixtoradec(self, idxs, coords='data'):
        """
        Map pixel indexes into a sky coordinate in the WCS system
        defined by the header.

        Parameters
        ----------
        idxs : tuple-like
            A sequence of indexes making up a data coordinate

        coords : 'data' or None, optional, default to 'data'
            Expresses whether the data coordinate is indexed from zero

        This method returns part of the world coordinates for the data
        (e.g. pixel) coordinate specified by `idxs`.

        `idxs` is expressed as a sequence of floating point values,
        usually representing (possibly fractional) pixel values.

        The `coords` parameter should be consulted to determine whether
        to increment the constituents of the data coordinate, depending
        on the API for the wrapped WCS.  If coords == 'data', then the
        indexes originate at 0, otherwise they can be assumed to originate
        from 1.

        Returns
        -------
        Returns a 2-tuple containing the WCS converted values in the
        first two axes of the coordinate system defined by the WCS
        (e.g. (ra_deg, dec_deg) as floats).
        """
        pass

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        """
        Convert multiple WCS to data points.

        Parameters
        ----------
        wcspt : array-like
            WCS coordinates in the format of
            ``[[ra0, dec0, ...], [ra1, dec1, ...], ..., [ran, decn, ...]]``.

        coords : 'data' or None, optional, default to 'data'
            Expresses whether the data coordinate is indexed from zero.

        naxispath : list-like or None, optional, defaults to None
            A sequence defining the pixel indexes > 2D, if any.

        Returns
        -------
        datapt : array-like
            Pixel coordinates in the format of
            ``[[x0, y0], [x1, y1], ..., [xn, yn]]``.

        """
        pass

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        """
        Map a sky coordinate in the WCS system defined by the header
        into pixel indexes.

        Parameters
        ----------
        ra_deg : float
            First coordinate

        dec_deg : float
            Second coordinate

        coords : 'data' or None, optional, defaults to 'data'
            Expresses whether to return coordinates indexed from zero

        naxispath : list-like or None, optional, defaults to None
            A sequence defining the pixel indexes > 2D, if any

        This method returns the 2D data (e.g. pixel) coordinate for the
        world coordinate defined by (ra_deg, dec_deg) + [0]*len(naxispath)

        ra_deg and dec_deg are expressed in degrees (float) and prepended
        to the naxispath, which is usually provided only for dimensions > 2D.

        The `coords` parameter should be consulted to determine whether
        to return the values of the data coordinates at origin 0 or 1.
        If coords == 'data', then the values should be returned at 0
        origin.

        Returns
        -------
        Returns a 2-tuple containing the data (pixel) values in the
        first two axes of the data coordinate system defined by the WCS
        (e.g. (x, y) as floats).
        """
        pass

    def pixtosystem(self, idxs, system=None, coords='data'):
        """
        Map pixel values into a sky coordinate in a named system.

        Parameters
        ----------
        idxs : tuple-like
            A sequence of indexes making up a data coordinate

        system : str or None
            A string naming a coordinate system

        coords : 'data' or None, optional, default to 'data'
            Expresses whether the data coordinate is indexed from zero

        See `pixtoradec` for discussion of the `idxs` and `coords`
        parameters.

        `system` names a coordinate system in which the results are
        expected.  For example, the wrapped WCS may express a coordinate
        system in "fk5" and the `system` parameter is "galactic".

        This call differs from pixtoradec() in that it may need to do
        a secondary mapping from the image's default coordinate system
        to the `system` one.

        Returns
        -------
        Returns a 2-tuple containing the WCS converted values in the
        first two axes of the coordinate system defined by `system`
        (e.g. (ra_deg, dec_deg) as floats).
        """
        pass

    def datapt_to_coords(self, datapt, system=None, coords='data',
                         naxispath=None):
        """This is specific to :class:`AstropyWCS`."""
        raise NotImplementedError

    def get_keyword(self, key):
        return self.header[key]

    def get_keywords(self, *args):
        return list(map(lambda key: self.header[key], args))

    def fix_bad_headers(self):
        """
        Fix up bad headers that cause problems for the wrapped WCS
        module.

        Subclass can override this method to fix up issues with the
        header for problem FITS files.
        """
        # WCSLIB doesn't like "nonstandard" units
        unit = self.header.get('CUNIT1', 'deg')
        if unit.upper() == 'DEGREE':
            # self.header.update('CUNIT1', 'deg')
            self.header['CUNIT1'] = 'deg'
        unit = self.header.get('CUNIT2', 'deg')
        if unit.upper() == 'DEGREE':
            # self.header.update('CUNIT2', 'deg')
            self.header['CUNIT2'] = 'deg'

    def has_valid_wcs(self):
        return self.wcs is not None


class AstropyWCS2(BaseWCS):
    """
    Astropy 1.0+ WCS / Coordinate System
    """

    def __init__(self, logger):
        super(AstropyWCS2, self).__init__(logger)
        self.kind = 'astropy/WCSLIB'
        self.coordframe = 'raw'

    @property
    def coordsys(self):
        """
        We include this here to make this compatible with the other WCSs.  But
        "coordsys" is a bad name in astropy coordinates, and using the name
        `coordframe` internally makes it clearer what's going on (see
        :ref:`Astropy Coordinates Definitions <astropy:astropy-coordinates-definitions>`).
        """  # noqa
        return self.coordframe

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
                sysname = get_coord_system_name(self.header)
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
            raise WCSError(e)

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        raise NotImplementedError

    def pixtoradec(self, idxs, coords='data'):
        return self._frametofloats(self.pixtonative(idxs, coords=coords))

    def pixtonative(self, idxs, coords='data'):
        """
        Convert the pixel value to the native coordinate frame of the header
        """
        import astropy.units as u

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = np.array([idxs], np.float_)

        try:
            sky = self.wcs.all_pix2world(pixcrd, origin)[0] * u.deg
        except Exception as e:
            self.logger.error("Error calculating pixtonative: %s" % (str(e)))
            raise WCSError(e)

        # Update our frame with the new data
        self.realize_frame_inplace(sky)

        return self.coordframe

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        raise NotImplementedError

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
            raise WCSError("No usable WCS")

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


class AstropyWCS(BaseWCS):
    """
    A WCS interface for astropy.wcs
    You need to install python module 'astropy'
    (http://pypi.python.org/pypi/astropy)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(AstropyWCS, self).__init__(logger)

        if not have_astropy:
            raise WCSError("Please install module 'astropy' first!")
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

            self.coordsys = get_coord_system_name(self.header)
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
            raise WCSError(e)

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
            raise WCSError(e)

        return wcspt

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
            raise WCSError(e)

        ra_deg = float(sky[0, 0])
        dec_deg = float(sky[0, 1])

        return ra_deg, dec_deg

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
            raise WCSError(e)

        return datapt[:, :2]

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
            # pix = self.wcs.wcs_sky2pix(skycrd, origin)
            # Doesn't seem to be a all_sky2pix
            # pix = self.wcs.all_sky2pix(skycrd, origin)
            # astropy only?
            pix = self.wcs.wcs_world2pix(skycrd, origin)

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise WCSError(e)

        x = float(pix[0, 0])
        y = float(pix[0, 1])
        return (x, y)

    def datapt_to_coords(self, datapt, system=None, coords='data',
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
            raise WCSError("No usable WCS")

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
            # Skip in input and output is the same (no realize_frame
            # call in astropy)
            if toClass != frameClass:
                coord = coord.transform_to(toClass)

        return coord

    def pixtocoords(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

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
                raise WCSError("No such coordinate system available: '%s'" % (
                    self.coordsys))

            coord = fromclass(ra_deg, dec_deg,
                              unit=(units.degree, units.degree))

            if (system is None) or (system == self.coordsys):
                return coord

            # Now give it back to the user in the system requested
            try:
                toclass = self.coord_table[system]
            except KeyError:
                raise WCSError("No such coordinate system available: '%s'" % (
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


class AstLibWCS(BaseWCS):
    """
    A WCS interface for astLib.astWCS.WCS
    You need to install python module 'astLib'
    (http://sourceforge.net/projects/astlib)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(AstLibWCS, self).__init__(logger)

        if not have_astlib:
            raise WCSError("Please install package 'astLib' first!")
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
        coordsys = get_coord_system_name(header)
        coordsys = coordsys.upper()
        if coordsys in ('FK4',):
            return 'b1950'
        elif coordsys in ('FK5', 'ICRS'):
            return 'j2000'
        elif coordsys in ('PIXEL',):
            return 'pixel'

        #raise WCSError("Cannot determine appropriate coordinate system from FITS header")  # noqa
        return 'j2000'

    def spectral_coord(self, idxs, coords='data'):
        raise WCSError("This feature not supported by astWCS")

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        raise NotImplementedError

    def pixtoradec(self, idxs, coords='data'):
        if coords == 'fits':
            # Via astWCS.NUMPY_MODE, we've forced pixels referenced from 0
            idxs = tuple(map(lambda x: x-1, idxs))

        try:
            ra_deg, dec_deg = self.wcs.pix2wcs(idxs[0], idxs[1])

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)

        return ra_deg, dec_deg

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        raise NotImplementedError

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        try:
            x, y = self.wcs.wcs2pix(ra_deg, dec_deg)

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise WCSError(e)

        if coords == 'fits':
            # Via astWCS.NUMPY_MODE, we've forced pixels referenced from 0
            x, y = x+1, y+1

        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

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
            raise WCSError(
                "Error converting between coordinate systems "
                "'%s' and '%s': %s" % (fromsys, tosys, str(e)))

        return (lon_deg, lat_deg)


class KapteynWCS(BaseWCS):
    """
    A WCS interface for kapteyn.wcs.Projection
    You need to install python module 'kapteyn'
    (http://www.astro.rug.nl/software/kapteyn/)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(KapteynWCS, self).__init__(logger)

        if not have_kapteyn:
            raise WCSError("Please install package 'kapteyn' first!")
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

            self.coordsys = get_coord_system_name(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def spectral_coord(self, idxs, coords='data'):
        # Kapteyn's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = tuple(map(lambda x: x+1, idxs))
        else:
            idxs = tuple(idxs)

        try:
            res = self.wcs.toworld(idxs)
            if len(res) > 0:
                return res[self.wcs.specaxnum-1]

        except Exception as e:
            self.logger.error(
                "Error calculating spectral coordinate: %s" % (str(e)))
            raise WCSError(e)

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        raise NotImplementedError

    def pixtoradec(self, idxs, coords='data'):
        # Kapteyn's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = tuple(map(lambda x: x+1, idxs))
        else:
            idxs = tuple(idxs)
        # print("indexes=%s" % (str(idxs)))

        try:
            res = self.wcs.toworld(idxs)
            if ((self.wcs.lonaxnum is not None) and
                    (self.wcs.lataxnum is not None)):
                ra_deg = res[self.wcs.lonaxnum-1]
                dec_deg = res[self.wcs.lataxnum-1]
            else:
                ra_deg, dec_deg = res[0], res[1]

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)

        return ra_deg, dec_deg

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        raise NotImplementedError

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        args = [ra_deg, dec_deg]
        if naxispath:
            args += [0] * len(naxispath)
        args = tuple(args)

        try:
            pix = self.wcs.topixel(args)

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise WCSError(e)

        if coords == 'data':
            # Kapteyn's WCS returns pixels referenced from 1
            pix = tuple(map(lambda x: x-1, pix))

        x, y = pix[0], pix[1]
        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

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


class StarlinkWCS(BaseWCS):
    """
    A WCS interface for Starlink
    You need to install python module 'starlink-pyast'
    (http://www.astro.rug.nl/software/kapteyn/)
    if you want to use this version.

    """
    def __init__(self, logger):
        super(StarlinkWCS, self).__init__(logger)

        if not have_starlink:
            raise WCSError("Please install package 'starlink-pyast' first!")
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

            self.coordsys = get_coord_system_name(self.header)
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
            idxs = np.array(map(lambda x: x+1, idxs))
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
            raise WCSError(e)

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        raise NotImplementedError

    def pixtoradec(self, idxs, coords='data'):
        # Starlink's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = np.array(list(map(lambda x: x+1, idxs)))
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
            ra_deg, dec_deg = math.degrees(ra_rad), math.degrees(dec_rad)
            # print(ra_deg, dec_deg)

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)

        return ra_deg, dec_deg

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        raise NotImplementedError

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        try:
            # sky coords to pixel (in the WCS specified transform)
            ra_rad, dec_rad = math.radians(ra_deg), math.radians(dec_deg)
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
            raise WCSError(e)

        if coords == 'data':
            # Starlink's WCS returns pixels referenced from 1
            x, y = x-1, y-1

        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

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
        ra_rad, dec_rad = math.radians(ra_deg), math.radians(dec_deg)
        res = end_trans.tran([[ra_rad], [dec_rad]], 1)
        lon_rad, lat_rad = res[0][0], res[1][0]
        lon_deg, lat_deg = math.degrees(lon_rad), math.degrees(lat_rad)

        return lon_deg, lat_deg


class BareBonesWCS(BaseWCS):
    """A dummy placeholder WCS.

    .. note::
        To get WCS functionality, please install one of the 3rd party python
        WCS modules referred to at the top of this module.

    """
    def __init__(self, logger):
        super(BareBonesWCS, self).__init__(logger)
        self.kind = 'barebones'

    def load_header(self, header, fobj=None):
        self.coordsys = 'pixel'

    def spectral_coord(self, idxs, coords='data'):
        raise WCSError("This feature not supported by BareBonesWCS")

    def datapt_to_wcspt(self, datapt, coords='data', naxispath=None):
        raise NotImplementedError

    def pixtoradec(self, idxs, coords='data'):
        px_x, px_y = idxs[:2]
        px_x, px_y = px_x + 1.0, px_y + 1.0
        return (px_x, px_y)

    def wcspt_to_datapt(self, wcspt, coords='data', naxispath=None):
        raise NotImplementedError

    def radectopix(self, px_x, px_y, coords='data', naxispath=None):
        # px_x, px_y = px_x - 1.0, px_y - 1.0
        return (px_x, px_y)

    def pixtosystem(self, idxs, system=None, coords='data'):
        return self.pixtoradec(idxs, coords=coords)


class WcslibWCS(AstropyWCS):
    """DO NOT USE--this class name to be deprecated."""
    pass


# ---------------- Help functions ---------------- #

def choose_coord_units(header):
    """Return the appropriate key code for the units value for the axes by
    examining the FITS header.
    """
    cunit = header['CUNIT1']
    match = re.match(r'^deg\s*$', cunit)
    if match:
        return 'degree'

    # raise WCSError("Don't understand units '%s'" % (cunit))
    return 'degree'


def get_coord_system_name(header):
    """Return an appropriate key code for the axes coordinate system by
    examining the FITS header.
    """
    try:
        ctype = header['CTYPE1'].strip().upper()
    except KeyError:
        try:
            # see if we have an "RA" header
            ra = header['RA']  # noqa
            try:
                equinox = float(header['EQUINOX'])
                if equinox < 1984.0:
                    radecsys = 'FK4'
                else:
                    radecsys = 'FK5'
            except KeyError:
                radecsys = 'ICRS'
            return radecsys.lower()

        except KeyError:
            return 'raw'

    match = re.match(r'^GLON\-.*$', ctype)
    if match:
        return 'galactic'

    match = re.match(r'^ELON\-.*$', ctype)
    if match:
        return 'ecliptic'

    match = re.match(r'^RA\-\-\-.*$', ctype)
    if match:
        hdkey = 'RADECSYS'
        try:
            radecsys = header[hdkey]

        except KeyError:
            try:
                hdkey = 'RADESYS'
                radecsys = header[hdkey]
            except KeyError:
                # missing keyword
                # RADESYS defaults to IRCS unless EQUINOX is given
                # alone, in which case it defaults to FK4 prior to 1984
                # and FK5 after 1984.
                try:
                    equinox = float(header['EQUINOX'])
                    if equinox < 1984.0:
                        radecsys = 'FK4'
                    else:
                        radecsys = 'FK5'
                except KeyError:
                    radecsys = 'ICRS'

        radecsys = radecsys.strip()

        return radecsys.lower()

    match = re.match(r'^HPLN\-.*$', ctype)
    if match:
        return 'helioprojective'

    match = re.match(r'^HGLT\-.*$', ctype)
    if match:
        return 'heliographicstonyhurst'

    match = re.match(r'^PIXEL$', ctype)
    if match:
        return 'pixel'

    match = re.match(r'^LINEAR$', ctype)
    if match:
        return 'pixel'

    #raise WCSError("Cannot determine appropriate coordinate system from FITS header")  # noqa
    return 'icrs'


if not wcs_configured:
    # default
    WCS = BareBonesWCS

    for name in wcs_try_order:
        try:
            if use(name, raise_err=False):
                break

        except Exception as e:
            continue

# END
