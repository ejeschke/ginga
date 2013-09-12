#
# wcs.py -- "Bare Bones" WCS calculations.
#
# Eric Jeschke (eric@naoj.org)
# Takeshi Inagaki
# Bruce Bon
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import re

try:
    from astropy.io import fits as pyfits
except ImportError:
    import pyfits
import numpy

have_pywcs = False
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
    coord_types = ['icrs', 'fk5', 'fk4', 'fk4-no-e', 'galactic']
    coord_table = {
        'icrs': coordinates.ICRSCoordinates,
        'fk5': coordinates.FK5Coordinates,
        'fk4': coordinates.FK4Coordinates,
        'fk4-no-e': coordinates.FK4NoETermCoordinates,
        'galactic': coordinates.GalacticCoordinates,
        #'azel': coordinates.HorizontalCoordinates,
        # TODO:
        #'elliptic': ??,
        }

except ImportError:
    have_astropy = False
    coord_types = [ ]
    coord_table = { }

display_types = ['sexagesimal', 'degrees']

class WCSError(Exception):
    pass


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
        """Subclass can override this method to fix up issues with the
        header for problem FITS files.
        """
        pass

    
class BareBonesWCS(BaseWCS):
    """A very basic WCS.  Assumes J2000, units in degrees, projection TAN.

    We recommend that you install python module 'pywcs':

        http://pypi.python.org/pypi/pywcs

    and then you can use the class WcslibWCS (below) instead, which supports
    many more projections.  Note that pywcs is much more strict about the
    correctness of the FITS WCS headers.
    """

    def __init__(self, logger):
        super(BareBonesWCS, self).__init__()
        self.logger = logger
        self.header = {}
        self.coordsys = 'raw'

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
    

class WcslibWCS(BaseWCS):
    """A WCS interface for astropy.wcs (a wrapper for Mark Calabretta's
    WCSLIB).   You need to install python module 'astropy'

        http://pypi.python.org/pypi/astropy

    or the older library 'pywcs' if you want to use this version.
    """

    def __init__(self, logger):
        super(WcslibWCS, self).__init__()

        if not have_pywcs:
            raise WCSError("Please install module 'astropy' first!")
        self.logger = logger
        self.header = None
        self.wcs = None
        self.coordsys = 'raw'

    def fix_bad_headers(self):
        """Fix up bad headers that cause problems for pywcs/wcslib.
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
        
        #self.wcs = pywcs.WCS(self.header, relax=True)
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

    def pixtocoords(self, idxs, system='icrs', coords='data'):

        if self.coordsys == 'raw':
            raise WCSError("No usable WCS")
            
        # Get a coordinates object based on ra/dec wcs transform
        ra_deg, dec_deg = self.pixtoradec(idxs, format='deg',
                                          coords=coords)
        self.logger.debug("ra, dec = %f, %f" % (ra_deg, dec_deg))
        
        # convert to astropy coord
        try:
            fromclass = coord_table[self.coordsys]
        except KeyError:
            raise WCSError("No such coordinate system available: '%s'" % (
                self.coordsys))
            
        coord = fromclass(ra_deg, dec_deg,
                          unit=(units.degree, units.degree))

        if (system == None) or (system == self.coordsys):
            return coord
            
        # Now give it back to the user in the system requested
        try:
            toclass = coord_table[system]
        except KeyError:
            raise WCSError("No such coordinate system available: '%s'" % (
                system))

        coord = coord.transform_to(toclass)
        return coord

# Supply a WCS depending on what is installed
if have_pywcs:
    class WCS(WcslibWCS):
        pass

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


else:
    class WCS(BareBonesWCS):
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
                    equinox = header['EQUINOX']
                    radecsys = 'FK5'
                except KeyError:
                    radecsys = 'ICRS'

        radecsys = radecsys.strip()

        return radecsys.lower()

    #raise WCSError("Cannot determine appropriate coordinate system from FITS header")
    return 'icrs'

# TODO: refactor all of this to use astropy module

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

#END
