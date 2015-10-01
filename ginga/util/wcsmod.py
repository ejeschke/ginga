#
# wcsmod.py -- module wrapper for WCS calculations.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
We are fortunate to have several possible choices for a python WCS package
compatible with Ginga: astlib, kapteyn, starlink and astropy.
kapteyn and astropy wrap Doug Calabretta's "WCSLIB", astLib wraps
Doug Mink's "wcstools", and I'm not sure what starlink uses (their own?).

Note that astlib requires pyfits (or astropy) in order to create a WCS
object from a FITS header.

To force the use of one, do:

    from ginga.util import wcsmod
    wcsmod.use('kapteyn')

before you load any images.  Otherwise Ginga will try to pick one for
you.
"""

import math
import re
import numpy
from ginga.util.six.moves import map, zip

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

class WCSError(Exception):
    pass

def use(wcspkg, raise_err=True):
    global coord_types, wcs_configured, WCS, \
           have_kapteyn, kapwcs, \
           have_astlib, astWCS, astCoords, \
           have_starlink, Ast, Atl, \
           have_astropy, pywcs, pyfits, astropy, coordinates, units

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
        except ImportError:
            if raise_err:
                raise

        from distutils.version import LooseVersion
        if LooseVersion(astropy.__version__) <= LooseVersion('1'):
            return False

        import astropy.coordinates
        import astropy.wcs as pywcs
        from astropy.io import fits as pyfits
        import astropy.units as u
        from astropy.version import version

        have_pywcs = True
        have_astropy = True
        wcs_configured = True
        WCS = AstropyWCS2

        try:
            import sunpy.coordinates
        except ImportError:
            pass

        coord_types = [f.name for f in astropy.coordinates.frame_transform_graph.frame_set]

        return True


    elif wcspkg == 'astropy':
        try:
            import astropy.wcs as pywcs
            from astropy.io import fits as pyfits
            have_pywcs = True
        except ImportError:
            try:
                import pywcs
                have_pywcs = True
            except ImportError as e:
                if raise_err:
                    raise

        try:
            from astropy import coordinates
            from astropy import units
            have_astropy = True
            wcs_configured = True
            WCS = AstropyWCS

            if hasattr(coordinates, 'SkyCoord'):
                try:
                    import sunpy.coordinates
                except ImportError:
                    pass
                coord_types = [f.name for f in coordinates.frame_transform_graph.frame_set]
            else:
                coord_types = ['icrs', 'fk5', 'fk4', 'galactic']

            return True

        except ImportError as e:
            if raise_err:
                raise
        return False

    elif wcspkg == 'barebones':
        coord_types = ['fk5']
        WCS = BareBonesWCS
        wcs_configured = True
        return True

    return False


class BaseWCS(object):

    def get_keyword(self, key):
        return self.header[key]

    def get_keywords(self, *args):
        return list(map(lambda key: self.header[key], args))

    def fix_bad_headers(self):
        """Fix up bad headers that cause problems for WCSLIB.
        Subclass can override this method to fix up issues with the
        header for problem FITS files.
        """
        # WCSLIB doesn't like "nonstandard" units
        unit = self.header.get('CUNIT1', 'deg')
        if unit.upper() == 'DEGREE':
            #self.header.update('CUNIT1', 'deg')
            self.header['CUNIT1'] = 'deg'
        unit = self.header.get('CUNIT2', 'deg')
        if unit.upper() == 'DEGREE':
            #self.header.update('CUNIT2', 'deg')
            self.header['CUNIT2'] = 'deg'

    def has_valid_wcs(self):
        return self.wcs != None


class AstropyWCS2(BaseWCS):
    """
    Astropy 1.0+ WCS / Coordinate System
    """

    def __init__(self, logger):
        super(AstropyWCS2, self).__init__()
        self.kind = 'astropy/WCSLIB'
        self.logger = logger
        self.header = None
        self.wcs = None
        self.coordframe = None


    def load_header(self, header, fobj=None):
        from astropy.wcs.utils import wcs_to_celestial_frame
        # reconstruct a pyfits header, because otherwise we take an
        # incredible performance hit in astropy.wcs
        self.header = pyfits.Header(header.items())

        try:
            self.logger.debug("Trying to make astropy wcs object")
            self.wcs = pywcs.WCS(self.header, fobj=fobj, relax=True)
            self.coordframe = wcs_to_celestial_frame(self.wcs)

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def vaild_transform_frames(self):
        global coord_types

        frames = [f.name for f in astropy.coordinates.frame_transform_graph.frame_set
                  if self.coordframe.is_transformable_to(f)]
        coord_types = frames

    def realize_frame(self, data):
        """
        Wrap frame.realize_frame, modify self.coordframe to reflect the
        new coords.

        Parameters
        ----------

        data : tuple of `astropy.units.Quantity`
            The coordinate data (assumed unit spherical)

        Returns
        -------
        None

        Notes
        -----

        This is really an ugly hack, which should be in BaseFrame. What it is
        doing is only changing the internal representation of the data in a Frame.
        This means that a new frame is not initilized, which is a substantial
        speed improvement.
        """
        # If the representation is a subclass of Spherical we need to check for
        # the new _unitrep attr to give the corresponding unit spherical subclass.
        if (issubclass(self.coordframe.representation,
                       astropy.coordinates.SphericalRepresentation) and
            hasattr(self.coordframe.representation, '_unitrep')):
            rep = self.coordframe.representation._unitrep(*data)

        elif issubclass(self.coordframe.representation,
                        astropy.coordinates.UnitSphericalRepresentation):
            rep = self.coordframe.representation(*data)

        else:
            self.logger.info("Falling back to UnitSphericalRepresentation"
                             " from {}".format(self.coordframe.representation))
            rep = astropy.coordinates.UnitSphericalRepresentation(*data)

        if hasattr(self.coordframe._set_data, '_set_data'):
            self.coordframe._set_data(rep)
        else:
            self.coordframe._data = rep
            self.coordframe._rep_cache[self.coordframe._data.__class__.__name__,
                                       False] = self.coordframe._data

#            This will eventually work, once upstream PR is complete.
#            self.coordframe = self.coordframe.realize_frame(rep, copy=False)


    def spectral_coord(self, idxs, coords='data'):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = numpy.array([idxs], numpy.float_)
        try:
            sky = self.wcs.all_pix2world(pixcrd, origin)
            return float(sky[0, 2])

        except Exception as e:
            self.logger.error("Error calculating spectral coordinate: %s" % (str(e)))
            raise WCSError(e)


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
        pixcrd = numpy.array([idxs], numpy.float_)

        try:
            sky = self.wcs.all_pix2world(pixcrd, origin)[0] * u.deg
        except Exception as e:
            self.logger.error("Error calculating pixtonative: %s" % (str(e)))
            raise WCSError(e)

        # Update our frame with the new data
        self.realize_frame(sky)

        return self.coordframe


    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        import astropy.units as u

        args = [ra_deg, dec_deg]
        if naxispath:
            args += [0] * len(naxispath)
        skycrd = u.Quantity(args, unit=u.deg)

        self.realize_frame(skycrd)

        return self.nativetopix(coords=coords, naxispath=naxispath)


    def nativetopix(self, coords='data',naxispath=None):
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
        data = numpy.array([data])
        pixels = self.wcs.wcs_world2pix(data, origin)[0][:2]

        return pixels


    def pixtocoords(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

        coord = self.pixtonative(idxs, coords=coords)

        if system is None:
            return coord

        toclass = astropy.coordinates.frame_transform_graph.lookup_name(system)

        transform = self.coordframe.is_transformable_to(toclass)
        if transform and transform != 'same':
            coord = coord.transform_to(toclass)
        else:
            self.logger.error("Frame {} is not Transformable to {}, falling back to {}".format(self.coordframe.name, toclass.name, self.coordframe.name))
#            self.prefs.set("wcs_coords", self.coordframe.name)

        return coord


    def pixtosystem(self, idxs, system=None, coords='data'):
        if self.coordsys == 'pixel':
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
        return tuple([getattr(r, component).value for component in r.components[:2]])


class AstropyWCS(BaseWCS):
    """A WCS interface for astropy.wcs
    You need to install python module 'astropy'

        http://pypi.python.org/pypi/astropy

    if you want to use this version.
    """

    def __init__(self, logger):
        super(AstropyWCS, self).__init__()

        if not have_astropy:
            raise WCSError("Please install module 'astropy' first!")
        self.logger = logger
        self.header = None
        self.wcs = None
        self.coordsys = 'raw'
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
        # reconstruct a pyfits header, because otherwise we take an
        # incredible performance hit in astropy.wcs
        self.header = pyfits.Header(header.items())

        try:
            self.logger.debug("Trying to make astropy-- wcs object")
            self.wcs = pywcs.WCS(self.header, fobj=fobj, relax=True)
            self.logger.debug("made astropy wcs object")

            self.coordsys = choose_coord_system(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))
        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def spectral_coord(self, idxs, coords='data'):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = numpy.array([idxs], numpy.float_)
        try:
            sky = self.wcs.all_pix2world(pixcrd, origin)
            return float(sky[0, 2])

        except Exception as e:
            self.logger.error("Error calculating spectral coordinate: %s" % (str(e)))
            raise WCSError(e)

    def pixtoradec(self, idxs, coords='data'):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = numpy.array([idxs], numpy.float_)
        try:
            #sky = self.wcs.wcs_pix2sky(pixcrd, origin)
            #sky = self.wcs.all_pix2sky(pixcrd, origin)
            # astropy only?
            sky = self.wcs.all_pix2world(pixcrd, origin)

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)

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
        skycrd = numpy.array([args], numpy.float_)

        try:
            #pix = self.wcs.wcs_sky2pix(skycrd, origin)
            # Doesn't seem to be a all_sky2pix
            #pix = self.wcs.all_sky2pix(skycrd, origin)
            # astropy only?
            pix = self.wcs.wcs_world2pix(skycrd, origin)

        except Exception as e:
            self.logger.error("Error calculating radectopix: %s" % (str(e)))
            raise WCSError(e)

        x = float(pix[0, 0])
        y = float(pix[0, 1])
        return (x, y)

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
            frameClass = coordinates.frame_transform_graph.lookup_name(self.coordsys)
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
    """A WCS interface for astLib.astWCS.WCS
    You need to install python module 'astLib'

        http://sourceforge.net/projects/astlib

    if you want to use this version.
    """

    def __init__(self, logger):
        super(AstLibWCS, self).__init__()

        if not have_astlib:
            raise WCSError("Please install package 'astLib' first!")
        self.logger = logger
        self.header = None
        self.wcs = None
        self.coordsys = 'raw'
        self.kind = 'astlib/wcstools'

    def load_header(self, header, fobj=None):
        self.header = {}
        self.header.update(header.items())

        self.fix_bad_headers()

        # reconstruct a pyfits header
        hdr = pyfits.Header(header.items())
        try:
            self.logger.debug("Trying to make astLib wcs object")
            self.wcs = astWCS.WCS(hdr, mode='pyfits')

            self.coordsys = self.choose_coord_system(self.header)
            self.logger.debug("Coordinate system is: %s" % (self.coordsys))

        except Exception as e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def choose_coord_system(self, header):
        coordsys = choose_coord_system(header)
        coordsys = coordsys.upper()
        if coordsys in ('FK4',):
            return 'b1950'
        elif coordsys in ('FK5', 'ICRS'):
            return 'j2000'
        elif coordsys in ('PIXEL',):
            return 'pixel'

        #raise WCSError("Cannot determine appropriate coordinate system from FITS header")
        return 'j2000'

    def spectral_coord(self, idxs, coords='data'):
        raise WCSError("This feature not supported by astWCS")

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
            raise WCSError("Error converting between coordinate systems '%s' and '%s': %s" % (
                fromsys, tosys, str(e)))

        return (lon_deg, lat_deg)


class KapteynWCS(BaseWCS):
    """A WCS interface for kapteyn.wcs.Projection
    You need to install python module 'kapteyn'

        http://www.astro.rug.nl/software/kapteyn/

    if you want to use this version.
    """

    def __init__(self, logger):
        super(KapteynWCS, self).__init__()

        if not have_kapteyn:
            raise WCSError("Please install package 'kapteyn' first!")
        self.logger = logger
        self.header = None
        self.wcs = None
        self.coordsys = 'raw'
        self.kind = 'kapteyn/WCSLIB'
        self._skyout = "equatorial icrs J2000.0"

        # see: https://github.com/astropy/coordinates-benchmark/blob/master/kapteyn/convert.py
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

            self.coordsys = choose_coord_system(self.header)
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
            self.logger.error("Error calculating spectral coordinate: %s" % (str(e)))
            raise WCSError(e)

    def pixtoradec(self, idxs, coords='data'):
        # Kapteyn's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = tuple(map(lambda x: x+1, idxs))
        else:
            idxs = tuple(idxs)
        #print "indexes=%s" % (str(idxs))

        try:
            res = self.wcs.toworld(idxs)
            if (self.wcs.lonaxnum is not None) and (self.wcs.lataxnum is not None):
                ra_deg, dec_deg = res[self.wcs.lonaxnum-1], res[self.wcs.lataxnum-1]
            else:
                ra_deg, dec_deg = res[0], res[1]

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)

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
    """A WCS interface for Starlink
    You need to install python module 'starlink-pyast'

        http://www.astro.rug.nl/software/kapteyn/

    if you want to use this version.
    """

    def __init__(self, logger):
        super(StarlinkWCS, self).__init__()

        if not have_starlink:
            raise WCSError("Please install package 'starlink-pyast' first!")
        self.logger = logger
        self.header = None
        self.wcs = None
        self.coordsys = 'raw'
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
            #adapter = Atl.PyFITSAdapter(hdu)
            #fitschan = Ast.FitsChan(adapter)
            fitschan = Ast.FitsChan(source)
            self.wcs = fitschan.read()
            # self.wcs is a FrameSet, with a Mapping
            #self.wcs.Report = True

            self.coordsys = choose_coord_system(self.header)
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
            idxs = numpy.array(map(lambda x: x+1, idxs))
        else:
            idxs = numpy.array(idxs)

        try:
            # pixel to sky coords (in the WCS specified transform)
            arrs = [ [idxs[i]] for i in range(len(idxs)) ]
            res = self.wcs.tran(arrs, 1)
            return res[2][0]

        except Exception as e:
            self.logger.error("Error calculating spectral coordinate: %s" % (str(e)))
            raise WCSError(e)

    def pixtoradec(self, idxs, coords='data'):
        # Starlink's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = numpy.array(list(map(lambda x: x+1, idxs)))
        else:
            idxs = numpy.array(idxs)

        try:
            # pixel to sky coords (in the WCS specified transform)
            arrs = [ [idxs[i]] for i in range(len(idxs)) ]
            res = self.wcs.tran(arrs, 1)

            if self.coordsys not in ('pixel', 'raw'):
                # whatever sky coords to icrs coords
                res = self.icrs_trans.tran(res, 1)
            # TODO: what if axes are inverted?
            ra_rad, dec_rad = res[0][0], res[1][0]
            ra_deg, dec_deg = math.degrees(ra_rad), math.degrees(dec_rad)
            #print ra_deg, dec_deg

        except Exception as e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)

        return ra_deg, dec_deg

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        try:
            # sky coords to pixel (in the WCS specified transform)
            ra_rad, dec_rad = math.radians(ra_deg), math.radians(dec_deg)
            # TODO: what if spatial axes are inverted?
            args = [ra_rad, dec_rad]
            if naxispath:
                args += [0] * len(naxispath)
            arrs = [ [args[i]] for i in range(len(args)) ]
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
    """A very basic WCS.  Assumes J2000, units in degrees, projection TAN.

    ***** NOTE *****:
    We strongly recommend that you install one of the 3rd party python
    WCS modules referred to at the top of this module, all of which are
    much more capable than BareBonesWCS.
    ****************
    """

    def __init__(self, logger):
        super(BareBonesWCS, self).__init__()
        self.logger = logger
        self.header = {}
        self.coordsys = 'raw'
        self.kind = 'barebones'
        self.wcs = True

    def load_header(self, header, fobj=None):
        self.header = {}
        self.header.update(header.items())

        self.fix_bad_headers()
        self.coordsys = choose_coord_system(self.header)

    # WCS calculations
    def get_reference_pixel(self):
        x = float(self.get_keyword('CRPIX1'))
        y = float(self.get_keyword('CRPIX2'))
        return x, y

    def get_physical_reference_pixel(self):
        xv = float(self.get_keyword('CRVAL1'))
        yv = float(self.get_keyword('CRVAL2'))
        assert 0.0 <= xv < 360.0, \
               WCSError("CRVAL1 out of range: %f" % (xv))

        assert -90.0 <= yv <= 90.0, \
               WCSError("CRVAL2 out of range: %f" % (yv))
        return xv, yv

    def get_pixel_coordinates(self):
        try:
            cd11 = float(self.get_keyword('CD1_1'))
            cd12 = float(self.get_keyword('CD1_2'))
            cd21 = float(self.get_keyword('CD2_1'))
            cd22 = float(self.get_keyword('CD2_2'))

        except Exception as e:
            cdelt1 = float(self.get_keyword('CDELT1'))
            cdelt2 = float(self.get_keyword('CDELT2'))
            try:
                cd11 = float(self.get_keyword('PC1_1')) * cdelt1
                cd12 = float(self.get_keyword('PC1_2')) * cdelt1
                cd21 = float(self.get_keyword('PC2_1')) * cdelt2
                cd22 = float(self.get_keyword('PC2_2')) * cdelt2
            except KeyError:
                cd11 = float(self.get_keyword('PC001001')) * cdelt1
                cd12 = float(self.get_keyword('PC001002')) * cdelt1
                cd21 = float(self.get_keyword('PC002001')) * cdelt2
                cd22 = float(self.get_keyword('PC002002')) * cdelt2

        return (cd11, cd12, cd21, cd22)

    def spectral_coord(self, idxs, coords='data'):
        raise WCSError("This feature not supported by BareBonesWCS")

    def pixtoradec(self, idxs, coords='data'):
        """Convert a (x, y) pixel coordinate on the image to a (ra, dec)
        coordinate in space.

        Parameter (coords):
        - if 'data' then x, y coordinates are interpreted as 0-based
        - otherwise coordinates are interpreted as 1-based (traditional FITS)
        """
        x, y = idxs[:2]

        # account for DATA->FITS coordinate space
        if coords == 'data':
            x, y = x + 1, y + 1

        crpix1, crpix2 = self.get_reference_pixel()
        crval1, crval2 = self.get_physical_reference_pixel()
        cd11, cd12, cd21, cd22 = self.get_pixel_coordinates()

        ra_deg = (cd11 * (x - crpix1) + cd12 *
                 (y - crpix2)) / math.cos(math.radians(crval2)) + crval1
        dec_deg = cd21 * (x - crpix1) + cd22 * (y - crpix2) + crval2

        return ra_deg, dec_deg

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        """Convert a (ra_deg, dec_deg) space coordinates to (x, y) pixel
        coordinates on the image.  ra and dec are expected as floats in
        degrees.

        Parameter (coords):
        - if 'data' then x, y coordinates are returned as 0-based
        - otherwise coordinates are returned as 1-based (traditional FITS)
        """
        crpix1, crpix2 = self.get_reference_pixel()
        crval1, crval2 = self.get_physical_reference_pixel()
        cd11, cd12, cd21, cd22 = self.get_pixel_coordinates()

        # reverse matrix
        rmatrix = (cd11 * cd22) - (cd12 * cd21)

        if not cmp(rmatrix, 0.0):
            raise WCSError("WCS Matrix Error: check values")

        # Adjust RA as necessary
        if (ra_deg - crval1) > 180.0:
            ra_deg -= 360.0
        elif (ra_deg - crval1) < -180.0:
            ra_deg += 360.0

        try:
            x = (cd22 * math.cos(crval2 * math.pi/180.0) *
                 (ra_deg - crval1) - cd12 *
                 (dec_deg - crval2))/rmatrix + crpix1
            y = (cd11 * (dec_deg - crval2) - cd21 *
                 math.cos(crval2 * math.pi/180.0) *
                 (ra_deg - crval1))/rmatrix + crpix2

        except Exception as e:
            raise WCSError("radectopix calculation error: %s" % str(e))

        # account for FITS->DATA space
        if coords == 'data':
            x, y = x - 1, y - 1
        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):
        return self.pixtoradec(idxs, coords=coords)


class WcslibWCS(AstropyWCS):
    """DO NOT USE--this class name to be deprecated."""
    pass


################## Help functions ##################

def choose_coord_units(header):
    """Return the appropriate key code for the units value for the axes by
    examining the FITS header.
    """
    cunit = header['CUNIT1']
    match = re.match(r'^deg\s*$', cunit)
    if match:
        return 'degree'

    #raise WCSError("Don't understand units '%s'" % (cunit))
    return 'degree'


def choose_coord_system(header):
    """Return an appropriate key code for the axes coordinate system by
    examining the FITS header.
    """
    try:
        ctype = header['CTYPE1'].strip().upper()
    except KeyError:
        try:
            # see if we have an "RA" header
            ra = header['RA']
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
            #raise WCSError("Cannot determine appropriate coordinate system from FITS header")

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

    #raise WCSError("Cannot determine appropriate coordinate system from FITS header")
    return 'icrs'


if not wcs_configured:
    # default
    WCS = BareBonesWCS

    # try to use them in this order
    order = ('kapteyn', 'starlink', 'astlib', 'astropy', 'astropy2')
    for name in order:
        try:
            if use(name, raise_err=False):
                break

        except Exception as e:
            continue


#END
