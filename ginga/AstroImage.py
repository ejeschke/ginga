#
# AstroImage.py -- Abstraction of an astronomical data image.
#
# Eric Jeschke (eric@naoj.org) 
# Takeshi Inagaki
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import math
import logging
# TEMP
import time

import numpy

from ginga import iqcalc, wcs, fits
from ginga.BaseImage import BaseImage, ImageError, Header
from ginga.misc import Bunch


class AstroImage(BaseImage):
    """
    Abstraction of an astronomical data (image).
    
    NOTE: this module is NOT thread-safe!
    """

    def __init__(self, data_np=None, metadata=None, wcsclass=None,
                 logger=None):
        if not wcsclass:
            wcsclass = wcs.WCS
        self.wcs = wcsclass(logger)

        BaseImage.__init__(self, data_np=data_np, metadata=metadata,
                           logger=logger)
        
        self.iqcalc = iqcalc.IQCalc(logger=logger)
        self.naxispath = []
        self.revnaxis = []

    def load_hdu(self, hdu, fobj=None, naxispath=None):
        self.naxispath = []
        self.revnaxis = []

        data = hdu.data
        if len(data.shape) < 2:
            # Expand 1D arrays into 1xN array
            data = data.reshape((1, data.shape[0]))
        else:
            # Drill down to 2D data slice
            if not naxispath:
                naxispath = ([0] * (len(data.shape)-2))
            self.naxispath = naxispath
            self.revnaxis = list(naxispath)
            self.revnaxis.reverse()

            for idx in naxispath:
                data = data[idx]

        self.set_data(data)

        # Load in FITS header
        self.clear_metadata()
        hdr = self.get_header()
        hdr.fromHDU(hdu)
        
        # Try to make a wcs object on the header
        self.wcs.load_header(hdu.header, fobj=fobj)

    def load_file(self, filepath, numhdu=None, naxispath=None):
        self.logger.debug("Loading file '%s' ..." % (filepath))
        self.clear_metadata()

        self.set(path=filepath)
        ahdr = self.get_header()

        loader = fits.get_fitsloader(logger=self.logger)

        data, naxispath = loader.load_file(filepath, ahdr, numhdu=numhdu,
                                           naxispath=naxispath)
        self.naxispath = naxispath
        self.revnaxis = list(naxispath)
        self.revnaxis.reverse()

        self.set_data(data)
        
        # Try to make a wcs object on the header
        # TODO: in order to do more sophisticated WCS (e.g. distortion
        #   correction) that requires info in additional headers we need
        #   to pass additional information to the wcs class
        #self.wcs.load_header(hdu.header, fobj=fobj)
        self.wcs.load_header(ahdr)

        # Set the name to the filename (minus extension) if no name
        # currently exists for this image
        name = self.get('name', None)
        if name == None:
            dirpath, filename = os.path.split(filepath)
            name, ext = os.path.splitext(filename)
            self.set(name=name)
        

    def load_buffer(self, data, dims, dtype, byteswap=False,
                    metadata=None, redraw=True):
        data = numpy.fromstring(data, dtype=dtype)
        if byteswap:
            data.byteswap(True)
        data = data.reshape(dims)
        self.set_data(data, metadata=metadata)

    def copy_data(self):
        data = self.get_data()
        return data.copy()
        
    def get_data_xy(self, x, y):
        data = self.get_data()
        assert (x >= 0) and (y >= 0), \
               ImageError("Indexes out of range: (x=%d, y=%d)" % (
            x, y))
        return data[y, x]
        
    def get_data_size(self):
        data = self.get_data()
        width, height = self._get_dims(data)
        return (width, height)

        
    def get_header(self, create=True):
        try:
            # By convention, the fits header is stored in a dictionary
            # under the metadata keyword 'header'
            hdr = self.metadata['header']
        except KeyError, e:
            if not create:
                raise e
            #hdr = {}
            hdr = AstroHeader()
            self.metadata['header'] = hdr
        return hdr
        
    def get_keyword(self, kwd, *args):
        """Get an item from the fits header, if any."""
        try:
            kwds = self.get_header()
            return kwds[kwd]
        except KeyError:
            # return a default if there is one
            if len(args) > 0:
                return args[0]
            raise KeyError(kwd)

    def get_keywords_list(self, *args):
        return map(self.get_keyword, args)
    
    def set_keyword(self, kwd, value, create=True):
        kwds = self.get_header(create=create)
        kwd = kwd.upper()
        if not create:
            prev = kwds[kwd]
        kwds[kwd] = value
        
    def update_keywords(self, keyDict):
        hdr = self.get_header()
        # Upcase all keywords
        for kwd, val in keyDict.items():
            hdr[kwd.upper()] = val

        # Try to make a wcs object on the header
        self.wcs.load_header(hdr)

    def set_keywords(self, **kwds):
        """Set an item in the fits header, if any."""
        return self.update_keywords(kwds)
        
        
    def update_data(self, data_np, metadata=None, astype=None):
        """Use this method to make a private copy of the incoming array.
        """
        self.set_data(data_np.copy(), metadata=metadata,
                      astype=astype)
        
        
    def update_metadata(self, keyDict):
        for key, val in keyDict.items():
            self.metadata[key] = val

        # refresh the WCS
        header = self.get_header()
        self.wcs.load_header(header)

    def clear_metadata(self):
        self.metadata = {}

    def update_hdu(self, hdu, fobj=None, astype=None):
        self.update_data(hdu.data, astype=astype)
        #self.update_keywords(hdu.header)
        hdr = self.get_header(create=True)
        hdr.fromHDU(hdu)

        # Try to make a wcs object on the header
        self.wcs.load_header(hdu.header, fobj=fobj)

    def update_file(self, path, index=0, astype=None):
        fits_f = wcs.pyfits.open(path, 'readonly')
        self.update_hdu(fits_f[index], fobj=fits_f, astype=astype)
        fits_f.close()

    def get_iqcalc(self):
        return self.iqcalc
    
    def transfer(self, other, astype=None):
        data = self.get_data()
        other.update_data(data, astype=astype)
        other.update_metadata(self.metadata)
        
    def copy(self, astype=None):
        data = self.get_data()
        other = AstroImage(data, logger=self.logger)
        self.transfer(other, astype=astype)
        return other
        
    def cutout_cross(self, x, y, radius):
        """Cut two data subarrays that have a center at (x, y) and with
        radius (radius) from (data).  Returns the starting pixel (x0, y0)
        of each cut and the respective arrays (xarr, yarr).
        """
        data = self.get_data()
        n = radius
        ht, wd = self.height, self.width
        x0, x1 = max(0, x-n), min(wd-1, x+n)
        y0, y1 = max(0, y-n), min(ht-1, y+n)
        xarr = data[y, x0:x1+1]
        yarr = data[y0:y1+1, x]
        return (x0, y0, xarr, yarr)


    def qualsize(self, x1=None, y1=None, x2=None, y2=None, radius=5,
                 bright_radius=2, fwhm_radius=15, threshold=None, 
                 minfwhm=2.0, maxfwhm=50.0, minelipse=0.5,
                 edgew=0.01):

        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        data = self.cutout_data(x1, y1, x2, y2, astype='float32')

        start_time = time.time()
        qs = self.iqcalc.pick_field(data, peak_radius=radius,
                                    bright_radius=bright_radius,
                                    fwhm_radius=fwhm_radius,
                                    threshold=threshold,
                                    minfwhm=minfwhm, maxfwhm=maxfwhm,
                                    minelipse=minelipse, edgew=edgew)

        elapsed = time.time() - start_time
        
        # Add back in offsets into image to get correct values with respect
        # to the entire image
        qs.x += x1
        qs.y += y1
        qs.objx += x1
        qs.objy += y1
        print "e: obj=%f,%f fwhm=%f sky=%f bright=%f (%f sec)" % (
            qs.objx, qs.objy, qs.fwhm, qs.skylevel, qs.brightness, elapsed)

        return qs
     

    def create_fits(self):
        fits_f = wcs.pyfits.HDUList()
        hdu = wcs.pyfits.PrimaryHDU()
        data = self.get_data()
        # if sys.byteorder == 'little':
        #     data = data.byteswap()
        hdu.data = data

        header = self.get_header()

        deriver = self.get('deriver', None)
        if deriver:
            deriver.deriveAll(self)
            keylist = deriver.get_keylist()
        else:
            keylist = header.get_keyorder()

        if not keylist:
            keylist = header.keys()

        errlist = []
        for kwd in keylist:
            try:
                if deriver:
                    comment = deriver.get_comment(kwd)
                else:
                    comment = ""
                hdu.header.update(kwd, header[kwd], comment=comment)
            except Exception, e:
                errlist.append((kwd, str(e)))

        fits_f.append(hdu)
        return fits_f
    
    def write_fits(self, path, output_verify='fix'):
        fits_f = self.create_fits()
        return fits_f.writeto(path, output_verify=output_verify)
        
    def save_file_as(self, filepath):
        self.write_fits(filepath)

    def pixtocoords(self, x, y, system=None, coords='data'):
        args = [x, y] + self.revnaxis
        return self.wcs.pixtocoords(args, system=system, coords=coords)
    
    def deg2fmt(self, ra_deg, dec_deg, format):

        rhr, rmn, rsec = wcs.degToHms(ra_deg)
        dsgn, ddeg, dmn, dsec = wcs.degToDms(dec_deg)

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

    def pixtoradec(self, x, y, format='deg', coords='data'):
        args = [x, y] + self.revnaxis
        ra_deg, dec_deg = self.wcs.pixtoradec(args, coords=coords)

        if format == 'deg':
            return ra_deg, dec_deg
        return self.deg2fmt(ra_deg, dec_deg, format)
    
    def radectopix(self, ra_deg, dec_deg, coords='data'):
        return self.wcs.radectopix(ra_deg, dec_deg, coords=coords,
                                   naxispath=self.revnaxis)

    def dispos(self, dra0, decd0, dra, decd):
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


    def deltaStarsRaDecDeg1(self, ra1_deg, dec1_deg, ra2_deg, dec2_deg):
        phi, dist = self.dispos(ra1_deg, dec1_deg, ra2_deg, dec2_deg)
        return wcs.arcsecToDeg(dist*60.0)

    def deltaStarsRaDecDeg2(self, ra1_deg, dec1_deg, ra2_deg, dec2_deg):
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
    
    def get_starsep_RaDecDeg(self, ra1_deg, dec1_deg, ra2_deg, dec2_deg):
        sep = self.deltaStarsRaDecDeg(ra1_deg, dec1_deg, ra2_deg, dec2_deg)
        ## self.logger.debug("sep=%.3f ra1=%f dec1=%f ra2=%f dec2=%f" % (
        ##     sep, ra1_deg, dec1_deg, ra2_deg, dec2_deg))
        sgn, deg, mn, sec = wcs.degToDms(sep)
        if deg != 0:
            txt = '%02d:%02d:%06.3f' % (deg, mn, sec)
        else:
            txt = '%02d:%06.3f' % (mn, sec)
        return txt
        
    def get_starsep_XY(self, x1, y1, x2, y2):
        # source point
        ra_org, dec_org = self.pixtoradec(x1, y1)

        # destination point
        ra_dst, dec_dst = self.pixtoradec(x2, y2)

        return self.get_starsep_RaDecDeg(ra_org, dec_org, ra_dst, dec_dst)

    def get_RaDecOffsets(self, ra1_deg, dec1_deg, ra2_deg, dec2_deg):
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

    def calc_radius_xy(self, x, y, radius_deg):
        """Calculate a radius (in pixels) from the point (x, y) to a circle
        defined by radius in degrees.
        """
        # calculate ra/dec of x,y pixel
        ra_deg, dec_deg = self.pixtoradec(x, y)

        # Calculate position 1 degree from the given one
        # NOTE: this needs to add in DEC, not RA
        ra2_deg, dec2_deg = self.add_offset_radec(ra_deg, dec_deg,
                                                  0.0, 1.0)

        # Calculate the length of this segment--it is pixels/deg
        x2, y2 = self.radectopix(ra2_deg, dec2_deg)
        px_per_deg_e = math.sqrt(math.fabs(x2-x)**2 + math.fabs(y2-y)**2)

        # calculate radius based on desired radius_deg
        radius_px = px_per_deg_e * radius_deg
        return radius_px
        
    def calc_radius_deg2pix(self, ra_deg, dec_deg, delta_deg,
                            equinox=None):
        x, y = self.radectopix(ra_deg, dec_deg, equinox=equinox)
        return self.calc_radius_xy(x, y, delta_deg)
        
    def add_offset_radec(self, ra_deg, dec_deg, delta_deg_ra, delta_deg_dec):
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
        
    def add_offset_xy(self, x, y, delta_deg_x, delta_deg_y):
        # calculate ra/dec of x,y pixel
        ra_deg, dec_deg = self.pixtoradec(x, y)

        # add offsets
        ra2_deg, dec2_deg = self.add_offset_radec(ra_deg, dec_deg,
                                                  delta_deg_x, delta_deg_y)

        # then back to new pixel coords
        x2, y2 = self.radectopix(ra2_deg, dec2_deg)
        
        return (x2, y2)

    def calc_radius_center(self, delta_deg):
        return self.calc_radius_xy(float(self.width / 2.0),
                                   float(self.height / 2.0),
                                   delta_deg)
        
        
    def calc_compass(self, x, y, len_deg_e, len_deg_n):

        # Get east and north coordinates
        xe, ye = self.add_offset_xy(x, y, len_deg_e, 0.0)
        xe = int(round(xe))
        ye = int(round(ye))
        xn, yn = self.add_offset_xy(x, y, 0.0, len_deg_n)
        xn = int(round(xn))
        yn = int(round(yn))
        
        return (x, y, xn, yn, xe, ye)
       
    def calc_compass_radius(self, x, y, radius_px):
        xe, ye = self.add_offset_xy(x, y, 1.0, 0.0)
        xn, yn = self.add_offset_xy(x, y, 0.0, 1.0)

        # now calculate the length in pixels of those arcs
        # (planar geometry is good enough here)
        px_per_deg_e = math.sqrt(math.fabs(ye - y)**2 + math.fabs(xe - x)**2)
        px_per_deg_n = math.sqrt(math.fabs(yn - y)**2 + math.fabs(xn - x)**2)

        # now calculate the arm length in degrees for each arm
        # (this produces same-length arms)
        len_deg_e = radius_px / px_per_deg_e
        len_deg_n = radius_px / px_per_deg_n

        return self.calc_compass(x, y, len_deg_e, len_deg_n)
       
    def calc_compass_center(self):
        # calculate center of data
        x = float(self.width) / 2.0
        y = float(self.height) / 2.0

        # radius we want the arms to be (approx 1/4 the smallest dimension)
        radius_px = float(min(self.width, self.height)) / 4.0

        return self.calc_compass_radius(x, y, radius_px)

    def mosaic1(self, imagelist):

        image0 = imagelist[0]
        xmin, ymin, xmax, ymax = 0, 0, 0, 0

        idxs = []
        for image in imagelist:
            wd, ht = image.get_size()
            # for each image calculate ra/dec in the corners
            for x, y in ((0, 0), (wd-1, 0), (wd-1, ht-1), (0, ht-1)):
                ra, dec = image.pixtoradec(x, y)
                # and then calculate the pixel position relative to the
                # base image
                x0, y0 = image0.radectopix(ra, dec)
                #x0, y0 = int(x0), int(y0)
                x0, y0 = int(round(x0)), int(round(y0))

                if (x == 0) and (y == 0):
                    idxs.append((x0, y0, x0+wd, y0+ht))
                
                # running calculation of min and max pixel coordinates
                xmin, ymin = min(xmin, x0), min(ymin, y0)
                xmax, ymax = max(xmax, x0), max(ymax, y0)

        # calc necessary dimensions of final image
        width, height = xmax-xmin+1, ymax-ymin+1

        # amount of offset to add to each image
        xoff, yoff = abs(min(0, xmin)), abs(min(0, ymin))

        self.logger.debug("new image=%dx%d offsets x=%f y=%f" % (
            width, height, xoff, yoff))

        # new array to hold the mosaic
        newdata = numpy.zeros((height, width))
        metadata = {}

        # drop each image in the right place
        cnt = 0
        for image in imagelist:
            wd, ht = image.get_size()
            data = image.get_data()

            (xi, yi, xj, yj) = idxs.pop(0)
            xi, yi, xj, yj = xi+xoff, yi+yoff, xj+xoff, yj+yoff

            #newdata[yi:yj, xi:xj] = data[0:ht, 0:wd]
            newdata[yi:(yi+ht), xi:(xi+wd)] = data[0:ht, 0:wd]

            if cnt == 0:
                metadata = image.get_metadata()
                crpix1 = image.get_keyword('CRPIX1') + xoff
                crpix2 = image.get_keyword('CRPIX2') + yoff

        # Create new image with reference pixel updated
        newimage = AstroImage(newdata, metadata=metadata,
                              logger=self.logger)
        newimage.update_keywords({ 'CRPIX1': crpix1,
                                   'CRPIX2': crpix2 })
        return newimage

    def get_wcs_rotation_deg(self):
        header = self.get_header()
        rot, cdelt1, cdelt2 = wcs.get_rotation_and_scale(header)
        return rot

    def rotate(self, deg, update_wcs=False):
        #old_deg = self.get_wcs_rotation_deg()

        super(AstroImage, self).rotate(deg)

        if update_wcs:
            self.wcs.rotate(deg)

    def match_wcs(self, img_coords, ref_coords):
        """Adjust WCS (CRVAL{1,2} and CD{1,2}_{1,2}) using a rotation
        and linear offset so that ``img_coords`` matches ``ref_coords``.

        Parameters
        ----------
        img_coords: seq like
            list of (ra, dec) coords in input image
        ref_coords: seq like
            list of reference coords to match
        """
        header = self.get_header()
        wcsClass = self.wcs.__class__
        wcs_m = wcs.WcsMatch(header, wcsClass, img_coords, ref_coords)
        res = wcs_m.calc_match()
        return wcs_m, res
        
    def mosaic(self, filelist):
        """Creates a new mosaic image from the images in filelist.
        """

        image0 = AstroImage(logger=self.logger)
        image0.load_file(filelist[0])

        xmin, ymin, xmax, ymax = 0, 0, 0, 0

        idxs = []
        for filepath in filelist:
            # Create and load the image
            self.logger.debug("Examining file '%s' ..." % (filepath))
            image = AstroImage(logger=self.logger)
            image.load_file(filepath)

            wd, ht = image.get_size()
            # for each image calculate ra/dec in the corners
            for x, y in ((0, 0), (wd-1, 0), (wd-1, ht-1), (0, ht-1)):

                # for each image calculate ra/dec in the corners
                ra, dec = image.pixtoradec(x, y)
                # and then calculate the pixel position relative to the
                # base image
                x0, y0 = image0.radectopix(ra, dec)
                x0, y0 = int(round(x0)), int(round(y0))

                # running calculation of min and max pixel coordinates
                xmin, ymin = min(xmin, x0), min(ymin, y0)
                xmax, ymax = max(xmax, x0), max(ymax, y0)
                 
        # calc necessary dimensions of final image
        width, height = xmax-xmin+1, ymax-ymin+1
        slop = 0
        width, height = width+slop, height+slop

        # amount of offset to add to each image
        xoff, yoff = abs(min(0, xmin)), abs(min(0, ymin))

        pa_deg = image0.get_wcs_rotation_deg()

        metadata = image0.get_metadata()
        header = image0.get_header()
        ## for kwd in ('CD1_1', 'CD1_2', 'CD2_1', 'CD2_2'):
        ##     try:
        ##         del header[kwd]
        ##     except KeyError:
        ##         pass
        
        # new array to hold the mosaic
        self.logger.debug("Creating empty mosaic image of %dx%d" % (
            (width, height)))
        newdata = numpy.zeros((height, width))

        # Create new image with empty data
        mosaic = AstroImage(newdata, metadata=metadata,
                            logger=self.logger)
        pa = numpy.radians(pa_deg)
        cpa = numpy.cos(pa)
        spa = numpy.sin(pa)
        mosaic.update_keywords({ 'NAXIS1': width,
                                 'NAXIS2': height,
                                 'PC1_1': cpa,
                                 'PC1_2': -spa,
                                 'PC2_1': spa,
                                 'PC2_2': cpa,
                                 })

        # Update the WCS reference pixel with the relocation info
        crpix1 = mosaic.get_keyword('CRPIX1')
        crpix2 = mosaic.get_keyword('CRPIX2')
        crpix1n, crpix2n = crpix1 + xoff, crpix2 + yoff
        self.logger.debug("CRPIX %f,%f -> %f,%f" % (
            crpix1, crpix2, crpix1n, crpix2n))
        mosaic.update_keywords({ 'CRPIX1': crpix1n,
                                 'CRPIX2': crpix2n })

        # drop each image in the right place in the new data array
        for filepath in filelist:
            # Create and load the image
            image = AstroImage(logger=self.logger)
            image.load_file(filepath)

            mosaic.mosaic_inline([ image ])
        
        header = mosaic.get_header()
        kwds = list(header.keys())
        kwds.sort()
        return mosaic
    
    def mosaic_inline(self, imagelist):
        """Drops new images into the current image (if there is room),
        relocating them according the WCS between the two images.
        """
        # For determining our orientation
        ra0, dec0 = self.pixtoradec(0, 0)
        ra1, dec1 = self.pixtoradec(self.width-1, self.height-1)

        rot_ref = self.get_wcs_rotation_deg()

        # drop each image in the right place in the new data array
        newdata = self.get_data()
        for image in imagelist:
            name = image.get('name', 'NoName')

            # Rotate image into our orientation, according to wcs
            rot_deg = image.get_wcs_rotation_deg()
            rot_deg = rot_ref - rot_deg
            ## self.logger.debug("rotating %s by %f deg" % (name, rot_deg))
            image.rotate(rot_deg, update_wcs=True)

            # Get size and data of new image
            wd, ht = image.get_size()
            data = image.get_data()

            # Find location of image piece and place it correctly in ours
            ra, dec = image.pixtoradec(0, 0)
                
            x0, y0 = self.radectopix(ra, dec)
            #self.logger.debug("0,0 -> %f,%f" % (x0, y0))
            # losing WCS precision!
            x0, y0 = int(round(x0)), int(round(y0))
            self.logger.debug("Fitting image '%s' into mosaic at %d,%d" % (
                name, x0, y0))

            try:
                newdata[y0:(y0+ht), x0:(x0+wd)] += data[0:ht, 0:wd]
            except Exception, e:
                self.logger.error("Failed to place image '%s': %s" % (
                    name, str(e)))

        self.make_callback('modified')

    def info_xy(self, data_x, data_y, settings):
        # Note: FITS coordinates are 1-based, whereas numpy FITS arrays
        # are 0-based
        fits_x, fits_y = data_x + 1, data_y + 1

        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = self.get_data_xy(int(data_x+0.5), int(data_y+0.5))

        except Exception, e:
            value = None

        system = settings.get('wcs_coords', None)
        format = settings.get('wcs_display', 'sexagesimal')
        ra_lbl, dec_lbl = unichr(945), unichr(948)
                    
        # Calculate WCS coords, if available
        ts = time.time()
        try:
            if (self.wcs == None) or (self.wcs.coordsys == 'raw'):
                ra_txt = dec_txt = 'NO WCS'

            else:
                args = [data_x, data_y] + self.revnaxis
    
                lon_deg, lat_deg = self.wcs.pixtosystem(#(data_x, data_y),
                    args,
                                                        system=system,
                                                        coords='data')

                if format == 'sexagesimal':
                    if system in ('galactic', 'ecliptic'):
                        sign, deg, min, sec = wcs.degToDms(lon_deg,
                                                           isLatitude=False)
                        ra_txt = '+%03d:%02d:%06.3f' % (deg, min, sec)
                    else:
                        deg, min, sec = wcs.degToHms(lon_deg)
                        ra_txt = '%02d:%02d:%06.3f' % (deg, min, sec)

                    sign, deg, min, sec = wcs.degToDms(lat_deg)
                    if sign < 0:
                        sign = '-'
                    else:
                        sign = '+'
                    dec_txt = '%s%02d:%02d:%06.3f' % (sign, deg, min, sec)

                else:
                    ra_txt = '%+10.7f' % (lon_deg)
                    dec_txt = '%+10.7f' % (lat_deg)

                if system == 'galactic':
                    ra_lbl, dec_lbl = "l", "b"
                elif system == 'ecliptic':
                    ra_lbl, dec_lbl = u"\u03BB", u"\u03B2"

        except Exception, e:
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        te = time.time() - ts
        #print "time elapsed: %.4f" % te

        info = Bunch.Bunch(itype='astro', data_x=data_x, data_y=data_y,
                           fits_x=fits_x, fits_y=fits_y,
                           x=fits_x, y=fits_y,
                           ra_txt=ra_txt, dec_txt=dec_txt,
                           ra_lbl=ra_lbl, dec_lbl=dec_lbl,
                           value=value)
        return info


class AstroHeader(Header):

    def fromHDU(self, hdu):
        header = hdu.header
        if hasattr(header, 'cards'):
            #newer astropy.io.fits don't have ascardlist
            for card in header.cards:
                bnch = self.__setitem__(card.key, card.value)
                bnch.comment = card.comment
        else:
            for card in header.ascardlist():
                bnch = self.__setitem__(card.key, card.value)
                bnch.comment = card.comment


#END
