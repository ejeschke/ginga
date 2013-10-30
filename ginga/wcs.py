#
# wcs.py -- WCS calculations.
#
# Eric Jeschke (eric@naoj.org)
# Takeshi Inagaki
# Bruce Bon
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
We are lucky to have several possible choices for a python WCS package
compatible with Ginga: astlib, kapteyn and astropy.
kapteyn and astropy wrap Doug Calabretta's "WCSLIB", astLib wraps
Doug Mink's "wcstools".  Note that astlib requires pyfits (or astropy)
in order to create a WCS object.

To force the use of one, do:

    from ginga import wcs
    wcs.use('kapteyn')

before you load any images.  Otherwise Ginga will try to pick one for
you.
"""

import math
import re

import numpy

have_pyfits = False
try:
    from astropy.io import fits as pyfits
    have_pyfits = True
except ImportError:
    try:
        import pyfits
        have_pyfits = True
    except ImportError:
        pass

coord_types = []
wcs_configured = False


have_kapteyn = False
have_astlib = False
have_pywcs = False
have_astropy = False
WCS = None

class WCSError(Exception):
    pass


def use(wcspkg):
    global coord_types, wcs_configured, WCS, \
           have_kapteyn, kapwcs, \
           have_astlib, astWCS, astCoords, \
           have_astropy, pywcs, coordinates, units
    
    if wcspkg == 'kapteyn':
        try:
            from kapteyn import wcs as kapwcs
            coord_types = ['icrs', 'fk5', 'fk4', 'fk4-no-e', 'galactic']
            have_kapteyn = True
            wcs_configured = True
            WCS = KapteynWCS
            return True

        except ImportError:
            pass
        return False
    
    elif wcspkg == 'astlib':
        try:
            if not have_pyfits:
                raise WCSError("Need pyfits module to use astLib WCS")
            from astLib import astWCS, astCoords
            astWCS.NUMPY_MODE = True
            coord_types = ['j2000', 'b1950', 'galactic']
            have_astlib = True
            wcs_configured = True
            WCS = AstLibWCS
            return True

        except ImportError:
            pass
        return False

    elif wcspkg == 'astropy':
        # Assume we should have pyfits if we have astropy
        #if not have_pyfits:
        #    raise WCSError("Need pyfits module to use astLib WCS")
        try:
            import astropy.wcs as pywcs
            have_pywcs = True
        except ImportError:
            try:
                import pywcs
                have_pywcs = True
            except ImportError:
                pass

        try:
            from astropy import coordinates
            from astropy import units
            have_astropy = True
            wcs_configured = True
            coord_types = ['icrs', 'fk5', 'fk4', 'fk4-no-e', 'galactic']
            WCS = AstropyWCS
            return True

        except ImportError:
            pass
        return False

    elif wcspkg == 'barebones':
        WCS = BareBonesWCS
        
display_types = ['sexagesimal', 'degrees']

# for testing
#have_kapteyn = False
#have_astlib = False
#have_pywcs = False


class BaseWCS(object):

    def deg2fmt(self, ra_deg, dec_deg, format):

        rhr, rmn, rsec = degToHms(ra_deg)
        dsgn, ddeg, dmn, dsec = degToDms(dec_deg)

        if format == 'hms':
            return rhr, rmn, rsec, dsgn, ddeg, dmn, dsec

        elif format == 'str':
            ra_txt = '%02d:%02d:%06.3f' % (rhr, rmn, rsec)
            if dsgn < 0:
                dsgn = '-'
            else:
                dsgn = '+'
            dec_txt = '%s%02d:%02d:%05.2f' % (dsgn, ddeg, dmn, dsec)
            return ra_txt, dec_txt

    def fix_bad_headers(self):
        """Fix up bad headers that cause problems for WCSLIB.
        Subclass can override this method to fix up issues with the
        header for problem FITS files.
        """
        # WCSLIB doesn't like "nonstandard" units
        unit = self.header.get('CUNIT1', 'deg')
        if unit.upper() == 'DEGREE':
            self.header.update('CUNIT1', 'deg')
        unit = self.header.get('CUNIT2', 'deg')
        if unit.upper() == 'DEGREE':
            self.header.update('CUNIT2', 'deg')

    
class BareBonesWCS(BaseWCS):
    """A very basic WCS.  Assumes J2000, units in degrees, projection TAN.

    ***** NOTE *****:
    We strongly recommend that you install one of the 3rd party python
    WCS modules referred to at the top of this module, all of which are
    much more capable than BareBonesWCS.
    """

    def __init__(self, logger):
        super(BareBonesWCS, self).__init__()
        self.logger = logger
        self.header = {}
        self.coordsys = 'raw'
        self.kind = 'barebones'

    def load_header(self, header, fobj=None):
        self.header = {}
        for key, value in header.items():
            self.header[key] = value

        self.fix_bad_headers()
        self.coordsys = choose_coord_system(self.header)

    def get_keyword(self, key):
        return self.header[key]
        
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

    def pixtoradec(self, idxs, format='deg', coords='data'):
        """Convert a (x, y) pixel coordinate on the image to a (ra, dec)
        coordinate in space.

        Parameter (format):
        - if 'deg', then returns ra, dec as a 2-tuple of floats (in degrees)
        - if 'hms', then returns a 7-tuple of
               (rahr, ramin, rasec, decsign, decdeg, decmin, decsec)
        - if 'str', then returns ra, dec as a 2-tuple of strings in traditional
            ra/dec notation

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

        if format == 'deg':
            return ra_deg, dec_deg
        else:
            return self.deg2fmt(ra_deg, dec_deg, format)
    
   
    def radectopix(self, ra_deg, dec_deg, coords='data'):
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

        except Exception, e:
            raise WCSError("radectopix calculation error: %s" % str(e))

        # account for FITS->DATA space
        if coords == 'data':
            x, y = x - 1, y - 1
        return (x, y)

    def pixtocoords(self, idxs, system='icrs', coords='data'):
        return None
    

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
        self.coord_table = {
            'icrs': coordinates.ICRSCoordinates,
            'fk5': coordinates.FK5Coordinates,
            'fk4': coordinates.FK4Coordinates,
            'fk4-no-e': coordinates.FK4NoETermCoordinates,
            'galactic': coordinates.GalacticCoordinates,
            #'azel': coordinates.HorizontalCoordinates,
            }
        self.kind = 'astropy/WCSLIB'

    def load_header(self, header, fobj=None):
        if isinstance(header, pyfits.Header):
            self.header = header
        else:
            # pywcs only operates on pyfits headers
            self.header = pyfits.Header()
            for kwd in header.keys():
                try:
                    bnch = header.get_card(kwd)
                    self.header.update(kwd, bnch.value, comment=bnch.comment)
                except Exception, e:
                    self.logger.warn("Error setting keyword '%s': %s" % (
                            kwd, str(e)))

        self.fix_bad_headers()
        
        try:
            self.wcs = pywcs.WCS(self.header, fobj=fobj, relax=True)

            self.coordsys = choose_coord_system(self.header)
        except Exception, e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def get_keyword(self, key):
        return self.header[key]
        
    def pixtoradec(self, idxs, format='deg', coords='data'):

        if coords == 'data':
            origin = 0
        else:
            origin = 1
        pixcrd = numpy.array([idxs], numpy.float_)
        try:
            sky = self.wcs.wcs_pix2sky(pixcrd, origin)
            #sky = self.wcs.all_pix2sky(pixcrd, origin)
            # astropy only?
            #sky = self.wcs.all_pix2world(pixcrd, origin)

        except Exception, e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)
        
        ra_deg = float(sky[0, 0])
        dec_deg = float(sky[0, 1])

        if format == 'deg':
            return ra_deg, dec_deg

        else:
            return self.deg2fmt(ra_deg, dec_deg, format)
    
    def radectopix(self, ra_deg, dec_deg, coords='data'):

        if coords == 'data':
            origin = 0
        else:
            origin = 1

        skycrd = numpy.array([[ra_deg, dec_deg]], numpy.float_)
        try:
            pix = self.wcs.wcs_sky2pix(skycrd, origin)
            # Doesn't seem to be a all_sky2pix
            #pix = self.wcs.all_sky2pix(skycrd, origin)
            # astropy only?
            #pix = self.wcs.wcs_world2pix(skycrd, origin)

        except Exception, e:
            print ("Error calculating radectopix: %s" % (str(e)))
            raise WCSError(e)

        x = float(pix[0, 0])
        y = float(pix[0, 1])
        return (x, y)

    def pixtocoords(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

        if system == None:
            system = 'icrs'
            
        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, format='deg',
                                          coords=coords)
        self.logger.debug("ra, dec = %f, %f" % (ra_deg, dec_deg))
        
        # convert to astropy coord
        try:
            fromclass = self.coord_table[self.coordsys]
        except KeyError:
            raise WCSError("No such coordinate system available: '%s'" % (
                self.coordsys))
            
        coord = fromclass(ra_deg, dec_deg,
                          unit=(units.degree, units.degree))

        if (system == None) or (system == self.coordsys):
            return coord
            
        # Now give it back to the user in the system requested
        try:
            toclass = self.coord_table[system]
        except KeyError:
            raise WCSError("No such coordinate system available: '%s'" % (
                system))

        coord = coord.transform_to(toclass)
        return coord

    def _deg(self, coord):
        # AstroPy changed the API so now we have to support more 
        # than one--we don't know what version the user has installed!
        if hasattr(coord, 'degrees'):
            return coord.degrees
        else:
            return coord.degree
        
    def pixtosystem(self, idxs, system=None, coords='data'):
        c = self.pixtocoords(idxs, system=system, coords=coords)
       
        return (self._deg(c.lonangle), self._deg(c.latangle))


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
        if isinstance(header, pyfits.Header):
            self.header = header
        else:
            # astLib stores internally as pyfits header
            self.header = pyfits.Header()
            for kwd in header.keys():
                try:
                    bnch = header.get_card(kwd)
                    self.header.update(kwd, bnch.value, comment=bnch.comment)
                except Exception, e:
                    self.logger.warn("Error setting keyword '%s': %s" % (
                            kwd, str(e)))

        self.fix_bad_headers()
        
        try:
            self.wcs = astWCS.WCS(self.header, mode='pyfits')

            self.coordsys = self.choose_coord_system(self.header)
        except Exception, e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def choose_coord_system(self, header):
        """Return an appropriate key code for the axes coordinate system by
        examining the FITS header.
        """
        try:
            ctype = header['CTYPE1'].strip().upper()
        except KeyError:
            return 'raw'
            #raise WCSError("Cannot determine appropriate coordinate system from FITS header")

        match = re.match(r'^GLON\-.*$', ctype)
        if match:
            return 'galactic'

        ## match = re.match(r'^ELON\-.*$', ctype)
        ## if match:
        ##     return 'elliptic'

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
                        equinox = header['EQUINOX']
                        radecsys = 'FK5'
                    except KeyError:
                        radecsys = 'ICRS'

            radecsys = radecsys.strip().upper()
            if radecsys in ('IRCS', 'FK5'):
                return 'j2000'

            return 'b1950'

        #raise WCSError("Cannot determine appropriate coordinate system from FITS header")
        return 'j2000'

    def get_keyword(self, key):
        return self.header[key]
        
    def pixtoradec(self, idxs, format='deg', coords='data'):
        if coords == 'fits':
            # Via astWCS.NUMPY_MODE, we've forced pixels referenced from 0
            idxs = tuple(map(lambda x: x-1, idxs))

        try:
            ra_deg, dec_deg = self.wcs.pix2wcs(idxs[0], idxs[1])
            
        except Exception, e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)
        
        if format == 'deg':
            return ra_deg, dec_deg
        else:
            return self.deg2fmt(ra_deg, dec_deg, format)
    
    def radectopix(self, ra_deg, dec_deg, coords='data'):
        try:
            x, y = self.wcs.wcs2pix(ra_deg, dec_deg)

        except Exception, e:
            print ("Error calculating radectopix: %s" % (str(e)))
            raise WCSError(e)

        if coords == 'fits':
            # Via astWCS.NUMPY_MODE, we've forced pixels referenced from 0
            x, y = x+1, y+1

        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

        if system == None:
            system = 'j2000'
            
        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, format='deg',
                                          coords=coords)
        self.logger.debug("ra, dec = %f, %f" % (ra_deg, dec_deg))
        
        # convert to alternate coord
        try:
            fromsys = self.coordsys.upper()
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

    def load_header(self, header, fobj=None):
        # For kapteyn, header just needs to be duck-typed like a dict
        self.header = header
        self.fix_bad_headers()
        
        try:
            self.wcs = kapwcs.Projection(self.header,
                                         skyout=self._skyout)

            self.coordsys = choose_coord_system(self.header)
        except Exception, e:
            self.logger.error("Error making WCS object: %s" % (str(e)))
            self.wcs = None

    def get_keyword(self, key):
        return self.header[key]
        
    def pixtoradec(self, idxs, format='deg', coords='data'):
        # Kapteyn's WCS needs pixels referenced from 1
        if coords == 'data':
            idxs = tuple(map(lambda x: x+1, idxs))
        else:
            idxs = tuple(idxs)
            
        try:
            res = self.wcs.toworld(idxs)
            ra_deg, dec_deg = res[0], res[1]
            
        except Exception, e:
            self.logger.error("Error calculating pixtoradec: %s" % (str(e)))
            raise WCSError(e)
        
        if format == 'deg':
            return ra_deg, dec_deg
        else:
            return self.deg2fmt(ra_deg, dec_deg, format)
    
    def radectopix(self, ra_deg, dec_deg, coords='data'):
        try:
            pix = self.wcs.topixel((ra_deg, dec_deg))

        except Exception, e:
            print ("Error calculating radectopix: %s" % (str(e)))
            raise WCSError(e)

        if coords == 'data':
            # Kapteyn's WCS returns pixels referenced from 1
            pix = map(lambda x: x-1, pix)
            
        x, y = pix[0], pix[1]
        return (x, y)

    def pixtosystem(self, idxs, system=None, coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")

        if system == None:
            system = 'icrs'
            
        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, format='deg',
                                          coords=coords)
        self.logger.debug("ra, dec = %f, %f" % (ra_deg, dec_deg))
        
        # convert to alternate coord
        tran = kapwcs.Transformation(self._skyout, system)
        lon_deg, lat_deg = tran((ra_deg, dec_deg))

        return lon_deg, lat_deg


class WcslibWCS(AstropyWCS):
    """DO NOT USE--this class name to be deprecated."""
    pass

# HELP FUNCTIONS

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
        return 'raw'
        #raise WCSError("Cannot determine appropriate coordinate system from FITS header")
    
    match = re.match(r'^GLON\-.*$', ctype)
    if match:
        return 'galactic'

    match = re.match(r'^ELON\-.*$', ctype)
    if match:
        return 'elliptic'

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
                    # EQUINOX defaults to 2000 unless RADESYS is FK4,
                    # in which case it defaults to 1950.
                    equinox = header['EQUINOX']
                    radecsys = 'FK5'
                except KeyError:
                    radecsys = 'ICRS'

        radecsys = radecsys.strip()

        return radecsys.lower()

    #raise WCSError("Cannot determine appropriate coordinate system from FITS header")
    return 'icrs'

def simple_wcs(px_x, px_y, ra_deg, dec_deg, px_scale_deg_px, pa_deg):
    """Calculate a set of WCS keywords for a 2D simple instrument FITS
    file with a 'standard' RA/DEC pixel projection.

    Parameters:
        px_x            : reference pixel of field in X (usually center of field)
        px_y            : reference pixel of field in Y (usually center of field)
        ra_deg          : RA (in deg) for the reference point
        dec_deg         : DEC (in deg) for the reference point
        px_scale_deg_px : pixel scale deg/pixel
        pa_deg          : position angle of the instrument (in deg)

    Returns a WCS object.  Use the to_header() method on it to get something
    interesting that you can use.
    """
    wcsobj = pywcs.WCS()

    # center of the projection
    wcsobj.wcs.crpix = [px_x, px_y]  # pixel position
    wcsobj.wcs.crval = [ra_deg, dec_deg]   # RA, Dec (degrees)

    # image scale in deg/pix
    wcsobj.wcs.cdelt = numpy.array([-1, 1]) * px_scale_deg_px

    # Position angle of north (radians E of N)
    pa = numpy.radians(pa_deg)
    cpa = numpy.cos(pa)
    spa = numpy.sin(pa)
    #wcsobj.wcs.pc = numpy.array([[-cpa, -spa], [-spa, cpa]])
    wcsobj.wcs.pc = numpy.array([[cpa, -spa], [spa, cpa]])

    return wcsobj


degPerHMSHour = 15.0      #360/24
degPerHMSMin  = 0.25      #360.0/24/60
degPerHMSSec  = 1.0/240.0 #360.0/24/60/60

degPerDmsMin  = 1.0/60.0
degPerDmsSec  = 1.0/3600.0

HMSHourPerDeg = 1.0/15.0
HMSMinPerDeg  = 4.0
HMSSecPerDeg  = 240.0


def hmsToDeg(h, m, s):
    """Convert RA hours, minutes, seconds into an angle in degrees."""
    return h * degPerHMSHour + m * degPerHMSMin + s * degPerHMSSec

def dmsToDeg(sign, deg, min, sec):
    """Convert dec sign, degrees, minutes, seconds into a signed angle in degrees."""
    return sign * (deg + min * degPerDmsMin + sec * degPerDmsSec)

def decTimeToDeg(sign_sym, deg, min, sec):
    """Convert dec sign, degrees, minutes, seconds into a signed angle in degrees.
       sign_sym may represent negative as either '-' or numeric -1."""
    if sign_sym == -1 or sign_sym == '-':
        sign = -1
    else:
        sign = 1
    return dmsToDeg(sign, deg, min, sec)

def degToHms(ra):
    """Converts the ra (in degrees) to HMS three tuple.
    H and M are in integer and the S part is in float.
    """
    assert (ra >= 0.0), WCSError("RA (%f) is negative" % (ra))
    assert ra < 360.0, WCSError("RA (%f) > 360.0" % (ra))
    rah   = ra/degPerHMSHour
    ramin = (ra % degPerHMSHour) * HMSMinPerDeg
    rasec = (ra % degPerHMSMin)  * HMSSecPerDeg
    return  (int(rah), int(ramin), rasec)

def degToDms(dec):
    """Convert the dec, in degrees, to an (sign,D,M,S) tuple.
    D and M are integer, and sign and S are float.
    """
    assert dec <= 90, WCSError("DEC (%f) > 90.0" % (dec))
    assert dec >= -90, WCSError("DEC (%f) < -90.0" % (dec))

    if dec < 0.0:
        sign = -1.0
    else:
        sign = 1.0
    dec = dec * sign

    #mnt = (dec % 1.0) * 60.0
    #sec = (dec % (1.0/60.0)) * 3600.0
    # this calculation with return values produces conversion problem.
    # e.g. dec +311600.00 -> 31.2666666667 degree
    # deg=31 min=15 sec=60 instead deg=31 min=16 sec=0.0
    # bug fixed    
    mnt, sec = divmod(dec*3600, 60)
    deg, mnt = divmod(mnt, 60)

    return (int(sign), int(deg), int(mnt), sec)

def arcsecToDeg(arcsec):
    """Convert numeric arcseconds (aka DMS seconds) to degrees of arc.
    """
    return arcsec * degPerDmsSec

def hmsStrToDeg(ra):
    """Convert a string representation of RA into a float in degrees."""
    hour, min, sec = ra.split(':')
    ra_deg = hmsToDeg(int(hour), int(min), float(sec))
    return ra_deg
    
def dmsStrToDeg(dec):
    """Convert a string representation of DEC into a float in degrees."""
    sign_deg, min, sec = dec.split(':')
    sign = sign_deg[0:1]
    deg = sign_deg[1:] 
    dec_deg = decTimeToDeg(sign, int(deg), int(min), float(sec))
    return dec_deg

def raDegToString(ra_deg, format='%02d:%02d:%06.3f'):
    if ra_deg > 360.0:
        ra_deg = math.fmod(ra_deg, 360.0)
        
    ra_hour, ra_min, ra_sec = degToHms(ra_deg)
    return format % (ra_hour, ra_min, ra_sec)
    
def decDegToString(dec_deg, format='%s%02d:%02d:%05.2f'):
    sign, dec_degree, dec_min, dec_sec = degToDms(dec_deg)
    if sign > 0:
        sign_sym = '+'
    else:
        sign_sym = '-'
    return format % (sign_sym, int(dec_degree), int(dec_min), dec_sec)
    
# this function is provided by MOKA2 Development Team (1996.xx.xx)
#   and used in SOSS system
def trans_coeff (eq, x, y, z):
       
    tt = (eq - 2000.0) / 100.0
    
    zeta = 2306.2181*tt+0.30188*tt*tt+0.017998*tt*tt*tt
    zetto = 2306.2181*tt+1.09468*tt*tt+0.018203*tt*tt*tt
    theta = 2004.3109*tt-0.42665*tt*tt-0.041833*tt*tt*tt
    
    zeta = math.radians(zeta) / 3600.0
    zetto = math.radians(zetto) / 3600.0
    theta = math.radians(theta) / 3600.0
    
    
    p11 = math.cos(zeta)*math.cos(theta)*math.cos(zetto)-math.sin(zeta)*math.sin(zetto)
    p12 = -math.sin(zeta)*math.cos(theta)*math.cos(zetto)-math.cos(zeta)*math.sin(zetto)
    p13 = -math.sin(theta)*math.cos(zetto)
    p21 = math.cos(zeta)*math.cos(theta)*math.sin(zetto)+math.sin(zeta)*math.cos(zetto)
    p22 = -math.sin(zeta)*math.cos(theta)*math.sin(zetto)+math.cos(zeta)*math.cos(zetto)
    p23 = -math.sin(theta)*math.sin(zetto)
    p31 = math.cos(zeta)*math.sin(theta)
    p32 = -math.sin(zeta)*math.sin(theta)
    p33 = math.cos(theta)
    
    return (p11,p12,p13, p21, p22, p23, p31,p32, p33)

def eqToEq2000(ra_deg, dec_deg, eq):
           
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)
    
    x = math.cos(dec_rad) * math.cos(ra_rad) 
    y = math.cos(dec_rad) * math.sin(ra_rad)
    z = math.sin(dec_rad) 
    
    p11, p12, p13, p21, p22, p23, p31, p32, p33 = trans_coeff (eq, x, y, z)
    
    x0 = p11*x + p21*y + p31*z
    y0 = p12*x + p22*y + p32*z
    z0 = p13*x + p23*y + p33*z
    
    new_dec = math.asin(z0)
    if x0 == 0.0:
        new_ra = math.pi / 2.0
    else:
        new_ra = math.atan( y0/x0 )
        
    if ((y0*math.cos(new_dec) > 0.0 and x0*math.cos(new_dec) <= 0.0)  or  
        (y0*math.cos(new_dec) <= 0.0 and x0*math.cos(new_dec) < 0.0) ):
            new_ra += math.pi
            
    elif new_ra < 0.0:
        new_ra += 2.0*math.pi
        
    #new_ra = new_ra * 12.0 * 3600.0 / math.pi
    new_ra_deg = new_ra * 12.0 / math.pi * 15.0
   
    #new_dec = new_dec * 180.0 * 3600.0 / math.pi
    new_dec_deg = new_dec * 180.0 / math.pi
 
    return (new_ra_deg, new_dec_deg)

# default
WCS = BareBonesWCS

# try to use them in this order
for name in ('kapteyn', 'pyast', 'astropy'):
    if use(name):
        break

#END
