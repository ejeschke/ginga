#
# wcs.py -- calculations based on world coordinate system.
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
from collections import OrderedDict
import numpy

class WCSError(Exception):
    pass


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
    rah   = ra / degPerHMSHour
    ramin = (ra % degPerHMSHour) * HMSMinPerDeg
    rasec = (ra % degPerHMSMin)  * HMSSecPerDeg
    return  (int(rah), int(ramin), rasec)

def degToDms(dec, isLatitude=True):
    """Convert the dec, in degrees, to an (sign,D,M,S) tuple.
    D and M are integer, and sign and S are float.
    """
    if isLatitude:
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
    if not sign in ('+', '-'):
        sign = '+'
        deg = sign_deg
    else:
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

def get_xy_rotation_and_scale(header):
    """
    CREDIT: See IDL code at
    # http://www.astro.washington.edu/docs/idl/cgi-bin/getpro/library32.html?GETROT
    """

    def calc_from_cd(cd1_1, cd1_2, cd2_1, cd2_2):

        # TODO: Check if first coordinate in CTYPE is latitude
        # if (ctype EQ 'DEC-') or (strmid(ctype, 1) EQ 'LAT')  then $
        #    cd = reverse(cd,1)

        det = cd1_1*cd2_2 - cd1_2*cd2_1
        if det < 0:
            sgn = -1
        else:
            sgn = 1
        ## if det > 0:
        ##     raise ValueError("Astrometry is for a right-handed coordinate system")

        if (cd2_1 == 0.0) or (cd1_2 == 0.0):
            # Unrotated coordinates?
            xrot = 0.0
            yrot = 0.0
            cdelt1 = cd1_1
            cdelt2 = cd2_2
        else:
            xrot = math.atan2(sgn * cd1_2, sgn * cd1_1)
            yrot = math.atan2(-cd2_1, cd2_2)

            cdelt1 = sgn * math.sqrt(cd1_1**2 + cd1_2**2)
            cdelt2 = math.sqrt(cd1_1**2 + cd2_1**2)

        return xrot, yrot, cdelt1, cdelt2

    def calc_from_crota():
        try:
            crota1 = float(header['CROTA1'])
            xrot = crota1
        except KeyError:
            xrot = None

        try:
            crota2 = float(header['CROTA2'])
            yrot = crota2
        except KeyError:
            yrot = 0.0

        if xrot is None:
            xrot = yrot

        cdelt1 = float(header.get('CDELT1', 1.0))
        cdelt2 = float(header.get('CDELT2', 1.0))

        return xrot, yrot, cdelt1, cdelt2

    # 1st, check for presence of PC matrix
    try:
        pc1_1 = header['PC1_1']
        pc1_2 = header['PC1_2']
        pc2_1 = header['PC2_1']
        pc2_2 = header['PC2_2']

        cdelt1 = float(header['CDELT1'])
        cdelt2 = float(header['CDELT2'])

        cd1_1, cd1_2 = pc1_1 * cdelt1, pc1_2 * cdelt1
        cd2_1, cd2_2 = pc2_1 * cdelt2, pc2_2 * cdelt2

        xrot, yrot, cdelt1p, cdelt2p = calc_from_cd(pc1_1, pc1_2,
                                                    pc2_1, pc2_2)

    except KeyError:
        # 2nd, check for presence of CD matrix
        try:
            cd1_1 = header['CD1_1']
            cd1_2 = header['CD1_2']
            cd2_1 = header['CD2_1']
            cd2_2 = header['CD2_2']
            xrot, yrot, cdelt1, cdelt2 = calc_from_cd(cd1_1, cd1_2,
                                                      cd2_1, cd2_2)

        except KeyError:
            # 3rd, check for presence of CROTA keyword
            #  (or default is north=up)
            xrot, yrot, cdelt1, cdelt2 = calc_from_crota()

    xrot, yrot = math.degrees(xrot), math.degrees(yrot)

    return ((xrot, yrot), (cdelt1, cdelt2))


def get_rotation_and_scale(header, skew_threshold=0.001):

    ((xrot, yrot),
     (cdelt1, cdelt2)) = get_xy_rotation_and_scale(header)

    #if xrot != yrot:
    if math.fabs(xrot - yrot) > skew_threshold:
        raise ValueError("Skew detected: xrot=%.4f yrot=%.4f" % (
            xrot, yrot))
    rot = yrot

    lonpole = float(header.get('LONPOLE', 180.0))
    if lonpole != 180.0:
        rot += 180.0 - lonpole

    return (rot, cdelt1, cdelt2)


def simple_wcs(px_x, px_y, ra_deg, dec_deg, px_scale_deg_px, rot_deg,
               cdbase=[1, 1]):
    """Calculate a set of WCS keywords for a 2D simple instrument FITS
    file with a 'standard' RA/DEC pixel projection.

    Parameters:
        px_x            : (ZERO-based) reference pixel of field in X
                                (usually center of field)
        px_y            : (ZERO-based) reference pixel of field in Y
                                (usually center of field)
        ra_deg          : RA (in deg) for the reference point
        dec_deg         : DEC (in deg) for the reference point
        px_scale_deg_px : pixel scale (deg/pixel)
        rot_deg         : rotation angle of the field (in deg)

    Returns an ordered dictionary object containing WCS headers.
    """
    # center of the projection
    crpix = (px_x+1, px_y+1)  # pixel position (WCS is 1 based)
    crval = (ra_deg, dec_deg) # RA, Dec (degrees)

    # image scale in deg/pix
    cdelt = numpy.array(cdbase) * px_scale_deg_px

    # Create rotation matrix for position angle of north (radians E of N)
    rot_rad = numpy.radians(rot_deg)
    cpa = numpy.cos(rot_rad)
    spa = numpy.sin(rot_rad)
    # a) clockwise rotation
    pc = numpy.array([[cpa, spa], [-spa, cpa]])
    # b) counter clockwise
    #pc = numpy.array([[cpa, -spa], [spa, cpa]])

    cd = pc * cdelt

    res = OrderedDict((('CRVAL1', crval[0]),
                       ('CRVAL2', crval[1]),
                       ('CRPIX1', crpix[0]),
                       ('CRPIX2', crpix[1]),
                       ('CUNIT1', 'deg'),
                       ('CUNIT2', 'deg'),
                       ('CTYPE1', 'RA---TAN'),
                       ('CTYPE2', 'DEC--TAN'),
                       ('RADESYS', 'FK5'),
                       # Either PC + CDELT or CD should appear
                       # PC + CDELT seems to be the preferred approach
                       # according to the Calabretta papers
                       ('CDELT1', cdelt[0]),
                       ('CDELT2', cdelt[1]),
                       ('PC1_1' , pc[0, 0]),
                       ('PC1_2' , pc[0, 1]),
                       ('PC2_1' , pc[1, 0]),
                       ('PC2_2' , pc[1, 1])
                       ## ('CD1_1' , cd[0, 0]),
                       ## ('CD1_2' , cd[0, 1]),
                       ## ('CD2_1' , cd[1, 0]),
                       ## ('CD2_2' , cd[1, 1]),
                       ))
    return res

def deg2fmt(ra_deg, dec_deg, format):

    rhr, rmn, rsec = degToHms(ra_deg)
    dsgn, ddeg, dmn, dsec = degToDms(dec_deg)

    if format == 'hms':
        return rhr, rmn, rsec, dsgn, ddeg, dmn, dsec

    elif format == 'str':
        #ra_txt = '%02d:%02d:%06.3f' % (rhr, rmn, rsec)
        ra_txt = '%d:%02d:%06.3f' % (rhr, rmn, rsec)
        if dsgn < 0:
            dsgn = '-'
        else:
            dsgn = '+'
        #dec_txt = '%s%02d:%02d:%05.2f' % (dsgn, ddeg, dmn, dsec)
        dec_txt = '%s%d:%02d:%05.2f' % (dsgn, ddeg, dmn, dsec)
        return ra_txt, dec_txt


def dispos(dra0, decd0, dra, decd):
    """
    Source/credit: Skycat

    dispos computes distance and position angle solving a spherical
    triangle (no approximations)
    INPUT        :coords in decimal degrees
    OUTPUT       :dist in arcmin, returns phi in degrees (East of North)
    AUTHOR       :a.p.martinez
    Parameters:
      dra0: center RA  decd0: center DEC  dra: point RA  decd: point DEC

    Returns:
      distance in arcmin
    """
    radian = 180.0/math.pi

    # coord transformed in radians
    alf = dra / radian
    alf0 = dra0 / radian
    del_ = decd / radian
    del0 = decd0 / radian

    sd0 = math.sin(del0)
    sd = math.sin(del_)
    cd0 = math.cos(del0)
    cd = math.cos(del_)
    cosda = math.cos(alf - alf0)
    cosd = sd0*sd + cd0*cd*cosda
    dist = math.acos(cosd)
    phi = 0.0
    if dist > 0.0000004:
        sind = math.sin(dist)
        cospa = (sd*cd0 - cd*sd0*cosda)/sind
        #if cospa > 1.0:
        #    cospa=1.0
        if math.fabs(cospa) > 1.0:
            # 2005-06-02: fix from awicenec@eso.org
            cospa = cospa/math.fabs(cospa)
        sinpa = cd*math.sin(alf-alf0)/sind
        phi = math.acos(cospa)*radian
        if sinpa < 0.0:
            phi = 360.0-phi
    dist *= radian
    dist *= 60.0
    if decd0 == 90.0:
        phi = 180.0
    if decd0 == -90.0:
        phi = 0.0
    return (phi, dist)


def deltaStarsRaDecDeg1(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    phi, dist = dispos(ra1_deg, dec1_deg, ra2_deg, dec2_deg)
    return arcsecToDeg(dist*60.0)

def deltaStarsRaDecDeg2(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    ra1_rad = math.radians(ra1_deg)
    dec1_rad = math.radians(dec1_deg)
    ra2_rad = math.radians(ra2_deg)
    dec2_rad = math.radians(dec2_deg)

    sep_rad = math.acos(math.cos(90.0-dec1_rad) * math.cos(90.0-dec2_rad) +
                        math.sin(90.0-dec1_rad) * math.sin(90.0-dec2_rad) *
                        math.cos(ra1_rad - ra2_rad))
    res = math.degrees(sep_rad)
    return res

# Use spherical triangulation
deltaStarsRaDecDeg = deltaStarsRaDecDeg1

def get_starsep_RaDecDeg(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    sep = deltaStarsRaDecDeg(ra1_deg, dec1_deg, ra2_deg, dec2_deg)
    sgn, deg, mn, sec = degToDms(sep)
    if deg != 0:
        txt = '%02d:%02d:%06.3f' % (deg, mn, sec)
    else:
        txt = '%02d:%06.3f' % (mn, sec)
    return txt

def add_offset_radec(ra_deg, dec_deg, delta_deg_ra, delta_deg_dec):
    """
    Algorithm to compute RA/Dec from RA/Dec base position plus tangent
    plane offsets.
    """
    # To radians
    x = math.radians(delta_deg_ra)
    y = math.radians(delta_deg_dec)
    raz = math.radians(ra_deg)
    decz = math.radians(dec_deg)

    sdecz = math.sin(decz)
    cdecz = math.cos(decz)

    d = cdecz - y * sdecz

    ra2 = math.atan2(x, d) + raz
    # Normalize ra into the range 0 to 2*pi
    twopi = math.pi * 2
    ra2 = math.fmod(ra2, twopi)
    if ra2 < 0.0:
        ra2 += twopi
    dec2 = math.atan2(sdecz + y * cdecz, math.sqrt(x*x + d*d))

    # back to degrees
    ra2_deg = math.degrees(ra2)
    dec2_deg = math.degrees(dec2)

    return (ra2_deg, dec2_deg)

def get_RaDecOffsets(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    delta_ra_deg = ra1_deg - ra2_deg
    adj = math.cos(math.radians(dec2_deg))
    if delta_ra_deg > 180.0:
        delta_ra_deg = (delta_ra_deg - 360.0) * adj
    elif delta_ra_deg < -180.0:
        delta_ra_deg = (delta_ra_deg + 360.0) * adj
    else:
        delta_ra_deg *= adj

    delta_dec_deg = dec1_deg - dec2_deg
    return (delta_ra_deg, delta_dec_deg)

def lon_to_deg(lon):
    if isinstance(lon, str) and (':' in lon):
        # TODO: handle other coordinate systems
        lon_deg = hmsStrToDeg(lon)
    else:
        lon_deg = float(lon)

def lat_to_deg(lat):
    if isinstance(lat, str) and (':' in lat):
        # TODO: handle other coordinate systems
        lat_deg = dmsStrToDeg(lat)
    else:
        lat_deg = float(lat)

#END
