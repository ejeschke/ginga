#
# wcs.py -- calculations based on world coordinate system.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""This module handles calculations based on world coordinate system."""
import math
import warnings
from collections import OrderedDict

import numpy as np

from ginga.misc import Bunch

__all__ = ['hmsToDeg', 'dmsToDeg', 'decTimeToDeg', 'degToHms', 'degToDms',
           'arcsecToDeg', 'hmsStrToDeg', 'dmsStrToDeg', 'ra_deg_to_str',
           'dec_deg_to_str', 'trans_coeff', 'eqToEq2000',
           'get_xy_rotation_and_scale', 'get_rotation_and_scale',
           'get_relative_orientation', 'simple_wcs', 'deg2fmt', 'dispos',
           'deltaStarsRaDecDeg1', 'deltaStarsRaDecDeg2', 'get_starsep_RaDecDeg',
           'add_offset_radec', 'get_RaDecOffsets', 'lon_to_deg', 'lat_to_deg',
           'raDegToString', 'decDegToString',
           ]


class WCSError(Exception):
    pass


degPerHMSHour = 15.0        # 360/24
degPerHMSMin = 0.25         # 360.0/24/60
degPerHMSSec = 1.0 / 240.0  # 360.0/24/60/60

degPerDmsMin = 1.0 / 60.0
degPerDmsSec = 1.0 / 3600.0

HMSHourPerDeg = 1.0 / 15.0
HMSMinPerDeg = 4.0
HMSSecPerDeg = 240.0


def hmsToDeg(h, m, s):
    """Convert RA hours, minutes, seconds into an angle in degrees."""
    return h * degPerHMSHour + m * degPerHMSMin + s * degPerHMSSec


def dmsToDeg(sign, deg, min, sec):
    """Convert dec sign, degrees, minutes, seconds into a signed angle in
    degrees."""
    return sign * (deg + min * degPerDmsMin + sec * degPerDmsSec)


def decTimeToDeg(sign_sym, deg, min, sec):
    """Convert dec sign, degrees, minutes, seconds into a signed angle in
    degrees.

    ``sign_sym`` may represent negative as either '-' or numeric -1."""
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
    rah = ra / degPerHMSHour
    ramin = (ra % degPerHMSHour) * HMSMinPerDeg
    rasec = (ra % degPerHMSMin) * HMSSecPerDeg
    return (int(rah), int(ramin), rasec)


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

    mnt, sec = divmod(dec * 3600, 60)
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
    if sign not in ('+', '-'):
        sign = '+'
        deg = sign_deg
    else:
        deg = sign_deg[1:]
    dec_deg = decTimeToDeg(sign, int(deg), int(min), float(sec))
    return dec_deg


def ra_deg_to_str(ra_deg, precision=3, format='%02d:%02d:%02d.%03d'):
    if ra_deg > 360.0:
        ra_deg = math.fmod(ra_deg, 360.0)
    ra_hour, ra_min, ra_sec = degToHms(ra_deg)

    frac_sec, ra_sec = math.modf(ra_sec)
    frac_sec = int(frac_sec * 10 ** precision)
    return format % (ra_hour, ra_min, ra_sec, frac_sec)


def dec_deg_to_str(dec_deg, precision=2, format='%s%02d:%02d:%02d.%02d'):
    sign, dec_degree, dec_min, dec_sec = degToDms(dec_deg)
    if sign > 0:
        sign_sym = '+'
    else:
        sign_sym = '-'
    frac_sec, dec_sec = math.modf(dec_sec)
    frac_s = int(frac_sec * 10 ** precision)
    return format % (sign_sym, int(dec_degree), int(dec_min), dec_sec,
                     frac_sec)


def trans_coeff(eq, x, y, z):
    """This function is provided by MOKA2 Development Team (1996.xx.xx)
    and used in SOSS system."""
    tt = (eq - 2000.0) / 100.0

    zeta = 2306.2181 * tt + 0.30188 * tt * tt + 0.017998 * tt * tt * tt
    zetto = 2306.2181 * tt + 1.09468 * tt * tt + 0.018203 * tt * tt * tt
    theta = 2004.3109 * tt - 0.42665 * tt * tt - 0.041833 * tt * tt * tt

    zeta = math.radians(zeta) / 3600.0
    zetto = math.radians(zetto) / 3600.0
    theta = math.radians(theta) / 3600.0

    p11 = (math.cos(zeta) * math.cos(theta) * math.cos(zetto) -
           math.sin(zeta) * math.sin(zetto))
    p12 = (-math.sin(zeta) * math.cos(theta) * math.cos(zetto) -
           math.cos(zeta) * math.sin(zetto))
    p13 = -math.sin(theta) * math.cos(zetto)
    p21 = (math.cos(zeta) * math.cos(theta) * math.sin(zetto) +
           math.sin(zeta) * math.cos(zetto))
    p22 = (-math.sin(zeta) * math.cos(theta) * math.sin(zetto) +
           math.cos(zeta) * math.cos(zetto))
    p23 = -math.sin(theta) * math.sin(zetto)
    p31 = math.cos(zeta) * math.sin(theta)
    p32 = -math.sin(zeta) * math.sin(theta)
    p33 = math.cos(theta)

    return (p11, p12, p13, p21, p22, p23, p31, p32, p33)


def eqToEq2000(ra_deg, dec_deg, eq):
    """Convert Eq to Eq 2000."""
    ra_rad = math.radians(ra_deg)
    dec_rad = math.radians(dec_deg)

    x = math.cos(dec_rad) * math.cos(ra_rad)
    y = math.cos(dec_rad) * math.sin(ra_rad)
    z = math.sin(dec_rad)

    p11, p12, p13, p21, p22, p23, p31, p32, p33 = trans_coeff(eq, x, y, z)

    x0 = p11 * x + p21 * y + p31 * z
    y0 = p12 * x + p22 * y + p32 * z
    z0 = p13 * x + p23 * y + p33 * z

    new_dec = math.asin(z0)
    if x0 == 0.0:
        new_ra = math.pi / 2.0
    else:
        new_ra = math.atan(y0 / x0)

    if ((y0 * math.cos(new_dec) > 0.0 and x0 * math.cos(new_dec) <= 0.0) or
            (y0 * math.cos(new_dec) <= 0.0 and x0 * math.cos(new_dec) < 0.0)):
        new_ra += math.pi

    elif new_ra < 0.0:
        new_ra += 2.0 * math.pi

    #new_ra = new_ra * 12.0 * 3600.0 / math.pi
    new_ra_deg = new_ra * 12.0 / math.pi * 15.0

    #new_dec = new_dec * 180.0 * 3600.0 / math.pi
    new_dec_deg = new_dec * 180.0 / math.pi

    return (new_ra_deg, new_dec_deg)


def get_xy_rotation_and_scale(header):
    """
    CREDIT: See IDL code at
    http://www.astro.washington.edu/docs/idl/cgi-bin/getpro/library32.html?GETROT
    """

    def calc_from_cd(cd1_1, cd1_2, cd2_1, cd2_2):

        # TODO: Check if first coordinate in CTYPE is latitude
        # if (ctype EQ 'DEC-') or (strmid(ctype, 1) EQ 'LAT')  then $
        #    cd = reverse(cd,1)

        det = cd1_1 * cd2_2 - cd1_2 * cd2_1
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

        cd1_1, cd1_2 = cdelt1 * pc1_1, cdelt1 * pc1_2
        cd2_1, cd2_2 = cdelt2 * pc2_1, cdelt2 * pc2_2

        xrot, yrot, cdelt1, cdelt2 = calc_from_cd(cd1_1, cd1_2,
                                                  cd2_1, cd2_2)

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
    """Calculate rotation and CDELT."""
    ((xrot, yrot),
     (cdelt1, cdelt2)) = get_xy_rotation_and_scale(header)

    if math.fabs(xrot) - math.fabs(yrot) > skew_threshold:
        raise ValueError("Skew detected: xrot=%.4f yrot=%.4f" % (
            xrot, yrot))
    rot = yrot

    lonpole = float(header.get('LONPOLE', 180.0))
    if lonpole != 180.0:
        rot += 180.0 - lonpole

    return (rot, cdelt1, cdelt2)


def get_relative_orientation(image, ref_image):
    """Computes the relative orientation and scale of an image to a reference
    image.

    Parameters
    ----------
    image
        AstroImage based object

    ref_image
        AstroImage based object

    Returns
    -------
    result
        Bunch object containing the relative scale in x and y
        and the relative rotation in degrees.

    """
    # Get reference image rotation and scale
    header = ref_image.get_header()
    ((xrot_ref, yrot_ref),
     (cdelt1_ref, cdelt2_ref)) = get_xy_rotation_and_scale(header)

    scale_x, scale_y = math.fabs(cdelt1_ref), math.fabs(cdelt2_ref)

    # Get rotation and scale of image
    header = image.get_header()
    ((xrot, yrot),
     (cdelt1, cdelt2)) = get_xy_rotation_and_scale(header)

    # Determine relative scale of this image to the reference
    rscale_x = math.fabs(cdelt1) / scale_x
    rscale_y = math.fabs(cdelt2) / scale_y

    # Figure out rotation relative to our orientation
    rrot_dx, rrot_dy = xrot - xrot_ref, yrot - yrot_ref

    # Choose Y rotation as default
    rrot_deg = rrot_dy

    res = Bunch.Bunch(rscale_x=rscale_x, rscale_y=rscale_y,
                      rrot_deg=rrot_deg)
    return res


def simple_wcs(px_x, px_y, ra_deg, dec_deg, px_scale_deg_px, rot_deg,
               cdbase=[1, 1]):
    """Calculate a set of WCS keywords for a 2D simple instrument FITS
    file with a 'standard' RA/DEC pixel projection.

    Parameters
    ----------
    px_x
        (ZERO-based) reference pixel of field in X
        (usually center of field)

    px_y
        (ZERO-based) reference pixel of field in Y
        (usually center of field)

    ra_deg
        RA (in deg) for the reference point

    dec_deg
        DEC (in deg) for the reference point

    px_scale_deg_px
        Pixel scale (deg/pixel); can be a tuple for different x,y scales

    rot_deg
        Rotation angle of the field (in deg)

    cdbase
        CD base

    Returns
    -------
    res : dict
        Ordered dictionary object containing WCS headers.

    """
    # center of the projection
    crpix = (px_x + 1, px_y + 1)  # pixel position (WCS is 1 based)
    crval = (ra_deg, dec_deg)  # RA, Dec (degrees)

    # image scale in deg/pix
    cdelt = np.array(cdbase) * np.array(px_scale_deg_px)

    # Create rotation matrix for position angle of north (radians E of N)
    rot_rad = np.radians(rot_deg)
    cpa = np.cos(rot_rad)
    spa = np.sin(rot_rad)
    # a) clockwise rotation
    pc = np.array([[cpa, spa], [-spa, cpa]])
    # b) counter clockwise
    #pc = np.array([[cpa, -spa], [spa, cpa]])

    #cd = pc * cdelt

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
                       ('PC1_1', pc[0, 0]),
                       ('PC1_2', pc[0, 1]),
                       ('PC2_1', pc[1, 0]),
                       ('PC2_2', pc[1, 1])
                       ## ('CD1_1' , cd[0, 0]),
                       ## ('CD1_2' , cd[0, 1]),
                       ## ('CD2_1' , cd[1, 0]),
                       ## ('CD2_2' , cd[1, 1]),
                       ))
    return res


def deg2fmt(ra_deg, dec_deg, format):
    """Format coordinates."""

    rhr, rmn, rsec = degToHms(ra_deg)
    dsgn, ddeg, dmn, dsec = degToDms(dec_deg)

    if format == 'hms':
        return rhr, rmn, rsec, dsgn, ddeg, dmn, dsec

    elif format == 'str':
        frac_sec, rsec = math.modf(rsec)
        frac_sec = int(frac_sec * 1000)
        ra_txt = '%d:%02d:%02d.%03d' % (rhr, rmn, rsec, frac_sec)
        if dsgn < 0:
            dsgn = '-'
        else:
            dsgn = '+'
        frac_sec, dsec = math.modf(dsec)
        frac_s = int(frac_sec * 100)
        dec_txt = '%s%d:%02d:%02d.%02d' % (dsgn, ddeg, dmn, dsec, frac_sec)
        return ra_txt, dec_txt


def dispos(dra0, decd0, dra, decd):
    """Compute distance and position angle solving a spherical
    triangle (no approximations).

    Source/credit: Skycat
    Author: A.P. Martinez

    Parameters
    ----------
    dra0 : float
        Center RA in decimal degrees.

    decd0 : float
        Center DEC in decimal degrees.

    dra : float
        Point RA in decimal degrees.

    decd : float
        Point DEC in decimal degrees.

    Returns
    -------
    phi : float
        Phi in degrees (East of North).

    dist : float
        Distance in arcmin.

    """
    radian = 180.0 / math.pi

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
    cosd = sd0 * sd + cd0 * cd * cosda
    dist = math.acos(cosd)
    phi = 0.0
    if dist > 0.0000004:
        sind = math.sin(dist)
        cospa = (sd * cd0 - cd * sd0 * cosda) / sind
        #if cospa > 1.0:
        #    cospa=1.0
        if math.fabs(cospa) > 1.0:
            # 2005-06-02: fix from awicenec@eso.org
            cospa = cospa / math.fabs(cospa)
        sinpa = cd * math.sin(alf - alf0) / sind
        phi = math.acos(cospa) * radian
        if sinpa < 0.0:
            phi = 360.0 - phi
    dist *= radian
    dist *= 60.0
    if decd0 == 90.0:
        phi = 180.0
    if decd0 == -90.0:
        phi = 0.0
    return (phi, dist)


def deltaStarsRaDecDeg1(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    """Spherical triangulation."""
    phi, dist = dispos(ra1_deg, dec1_deg, ra2_deg, dec2_deg)
    return arcsecToDeg(dist * 60.0)


def deltaStarsRaDecDeg2(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    ra1_rad = math.radians(ra1_deg)
    dec1_rad = math.radians(dec1_deg)
    ra2_rad = math.radians(ra2_deg)
    dec2_rad = math.radians(dec2_deg)

    sep_rad = math.acos(math.cos(90.0 - dec1_rad) * math.cos(90.0 - dec2_rad) +
                        math.sin(90.0 - dec1_rad) * math.sin(90.0 - dec2_rad) *
                        math.cos(ra1_rad - ra2_rad))
    res = math.degrees(sep_rad)
    return res


# Use spherical triangulation
deltaStarsRaDecDeg = deltaStarsRaDecDeg1
"""Use spherical triangulation."""


def get_starsep_RaDecDeg(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    """Calculate separation."""
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
    dec2 = math.atan2(sdecz + y * cdecz, math.sqrt(x * x + d * d))

    # back to degrees
    ra2_deg = math.degrees(ra2)
    dec2_deg = math.degrees(dec2)

    return (ra2_deg, dec2_deg)


def get_RaDecOffsets(ra1_deg, dec1_deg, ra2_deg, dec2_deg):
    """Calculate offset."""
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


def calc_midpoint_radec(ra1, dec1, ra2, dec2):
    delta_ra = ra2 - ra1
    bx = np.cos(dec2) * np.cos(delta_ra)
    by = np.cos(dec2) * np.sin(delta_ra)
    dec_term1 = np.sin(dec1) + np.sin(dec2)
    dec_term2 = np.sqrt(np.power((np.cos(dec1) + bx), 2) +
                        np.power(by, 2))
    dec_mid = np.arctan2(dec_term1, dec_term2)
    ra_mid = ra1 + np.arctan2(by, np.cos(dec1) + bx)
    return (ra_mid, dec_mid)


def lon_to_deg(lon):
    """Convert longitude to degrees."""
    if isinstance(lon, str) and (':' in lon):
        # TODO: handle other coordinate systems
        lon_deg = hmsStrToDeg(lon)
    else:
        lon_deg = float(lon)
    return lon_deg


def lat_to_deg(lat):
    """Convert latitude to degrees."""
    if isinstance(lat, str) and (':' in lat):
        # TODO: handle other coordinate systems
        lat_deg = dmsStrToDeg(lat)
    else:
        lat_deg = float(lat)
    return lat_deg


def get_ruler_distances(image, p1, p2):
    """Get the distance calculated between two points.  A Bunch of
    results is returned, containing pixel values and distance values
    if the image contains a valid WCS.
    """
    x1, y1 = p1[:2]
    x2, y2 = p2[:2]

    dx, dy = x2 - x1, y2 - y1
    res = Bunch.Bunch(x1=x1, y1=y1, x2=x2, y2=y2,
                      theta=np.arctan2(y2 - y1, x2 - x1),
                      dx_pix=dx, dy_pix=dy,
                      dh_pix=np.sqrt(dx**2 + dy**2),
                      ra_org=None, dec_org=None,
                      ra_dst=None, dec_dst=None,
                      ra_heel=None, dec_heel=None,
                      dx_deg=None, dy_deg=None, dh_deg=None)

    if image is not None and hasattr(image, 'wcs') and image.wcs is not None:
        # Calculate RA and DEC for the three points
        try:
            # origination point
            ra_org, dec_org = image.pixtoradec(x1, y1)
            res.ra_org, res.dec_org = ra_org, dec_org

            # destination point
            ra_dst, dec_dst = image.pixtoradec(x2, y2)
            res.ra_dst, res.dec_dst = ra_dst, dec_dst

            # "heel" point making a right triangle
            ra_heel, dec_heel = image.pixtoradec(x2, y1)
            res.ra_heel, res.dec_heel = ra_heel, dec_heel

            res.dh_deg = deltaStarsRaDecDeg(ra_org, dec_org,
                                            ra_dst, dec_dst)
            res.dx_deg = deltaStarsRaDecDeg(ra_org, dec_org,
                                            ra_heel, dec_heel)
            res.dy_deg = deltaStarsRaDecDeg(ra_heel, dec_heel,
                                            ra_dst, dec_dst)
        except Exception as e:
            pass

    return res


def get_starsep_XY(image, x1, y1, x2, y2):
    # source point
    ra_org, dec_org = image.pixtoradec(x1, y1)

    # destination point
    ra_dst, dec_dst = image.pixtoradec(x2, y2)

    return get_starsep_RaDecDeg(ra_org, dec_org, ra_dst, dec_dst)


def calc_radius_xy(image, x, y, radius_deg):
    """Calculate a radius (in pixels) from the point (x, y) to a circle
    defined by radius in degrees.
    """
    # calculate ra/dec of x,y pixel
    ra_deg, dec_deg = image.pixtoradec(x, y)

    # Calculate position 1 degree from the given one
    # NOTE: this needs to add in DEC, not RA
    ra2_deg, dec2_deg = add_offset_radec(ra_deg, dec_deg,
                                         0.0, 1.0)

    # Calculate the length of this segment--it is pixels/deg
    x2, y2 = image.radectopix(ra2_deg, dec2_deg)
    px_per_deg_e = math.sqrt(math.fabs(x2 - x)**2 + math.fabs(y2 - y)**2)

    # calculate radius based on desired radius_deg
    radius_px = px_per_deg_e * radius_deg
    return radius_px


def calc_radius_deg2pix(image, ra_deg, dec_deg, delta_deg,
                        equinox=None):
    x, y = image.radectopix(ra_deg, dec_deg, equinox=equinox)
    return calc_radius_xy(image, x, y, delta_deg)


def add_offset_xy(image, x, y, delta_deg_x, delta_deg_y):
    # calculate ra/dec of x,y pixel
    ra_deg, dec_deg = image.pixtoradec(x, y)

    # add offsets
    ra2_deg, dec2_deg = add_offset_radec(ra_deg, dec_deg,
                                         delta_deg_x, delta_deg_y)

    # then back to new pixel coords
    x2, y2 = image.radectopix(ra2_deg, dec2_deg)

    return (x2, y2)


def calc_radius_center(image, delta_deg):
    return calc_radius_xy(image,
                          float(image.width / 2.0),
                          float(image.height / 2.0),
                          delta_deg)


def calc_compass(image, x, y, len_deg_e, len_deg_n):

    # Get east and north coordinates
    xe, ye = add_offset_xy(image, x, y, len_deg_e, 0.0)
    xn, yn = add_offset_xy(image, x, y, 0.0, len_deg_n)

    return (x, y, xn, yn, xe, ye)


def calc_compass_radius(image, x, y, radius_px):
    xe, ye = add_offset_xy(image, x, y, 1.0, 0.0)
    xn, yn = add_offset_xy(image, x, y, 0.0, 1.0)

    # now calculate the length in pixels of those arcs
    # (planar geometry is good enough here)
    px_per_deg_e = math.sqrt(math.fabs(ye - y)**2 + math.fabs(xe - x)**2)
    px_per_deg_n = math.sqrt(math.fabs(yn - y)**2 + math.fabs(xn - x)**2)

    # now calculate the arm length in degrees for each arm
    # (this produces same-length arms)
    len_deg_e = radius_px / px_per_deg_e
    len_deg_n = radius_px / px_per_deg_n

    return calc_compass(image, x, y, len_deg_e, len_deg_n)


def calc_compass_center(image):
    # calculate center of data
    x = float(image.width) / 2.0
    y = float(image.height) / 2.0

    # radius we want the arms to be (approx 1/4 the smallest dimension)
    radius_px = float(min(image.width, image.height)) / 4.0

    return calc_compass_radius(image, x, y, radius_px)


# TO BE DEPRECATED

def raDegToString(ra_deg, format=None):
    warnings.warn("This function has been deprecated--"
                  "use ra_deg_to_str instead", DeprecationWarning)
    if format is None:
        return ra_deg_to_str(ra_deg)
    if ra_deg > 360.0:
        ra_deg = math.fmod(ra_deg, 360.0)

    ra_hour, ra_min, ra_sec = degToHms(ra_deg)
    return format % (ra_hour, ra_min, ra_sec)


def decDegToString(dec_deg, format=None):
    warnings.warn("This function has been deprecated--"
                  "use dec_deg_to_str instead", DeprecationWarning)
    if format is None:
        return dec_deg_to_str(dec_deg)
    sign, dec_degree, dec_min, dec_sec = degToDms(dec_deg)
    if sign > 0:
        sign_sym = '+'
    else:
        sign_sym = '-'
    return format % (sign_sym, int(dec_degree), int(dec_min), dec_sec)
