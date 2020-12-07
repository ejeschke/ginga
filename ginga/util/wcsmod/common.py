#
# common.py -- common global functions for WCS calculations.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import re

import numpy as np

from ginga.misc import Bunch

__all__ = ['WCSError', 'BaseWCS', 'register_wcs', 'choose_coord_units',
           'get_coord_system_name', 'get_astropy_frame']

# Holds custom WCSes that are registered
custom_wcs = Bunch.caselessDict()

# Cache Astropy coordinate frames
astropy_coord_frames = {}


class WCSError(Exception):
    pass


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
        # We provide a list comprehension version for WCS packages that
        # don't support array operations.
        if naxispath:
            raise NotImplementedError

        return np.asarray([self.pixtoradec((pt[0], pt[1]), coords=coords)
                           for pt in datapt])

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
        # We provide a list comprehension version for WCS packages that
        # don't support array operations.
        if naxispath:
            raise NotImplementedError

        return np.asarray([self.radectopix(pt[0], pt[1], coords=coords)
                           for pt in wcspt])

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
        wcspt : array-like
            WCS coordinates in the format of
            ``[[ra0, dec0], [ra1, dec1], ..., [ran, decn]]``.

        """
        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

        raise NotImplementedError

    def get_keyword(self, key):
        return self.header[key]

    def get_keywords(self, *args):
        return [self.header[key] for key in args]

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


# ---------------- Help functions ---------------- #

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


def get_astropy_frame(to_class):
    """Obtain and instance of requested Astropy coordinates frame class.
    This instance is cached, if necessary.
    """
    global astropy_coord_frames

    cname = to_class.__name__
    if cname not in astropy_coord_frames:
        astropy_coord_frames[cname] = to_class()
    return astropy_coord_frames[cname]
