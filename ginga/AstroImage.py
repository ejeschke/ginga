#
# AstroImage.py -- Abstraction of an astronomical data image.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import math
import traceback

import numpy

from ginga.util import wcsmod, io_fits
from ginga.util import wcs, iqcalc
from ginga.BaseImage import BaseImage, ImageError, Header
from ginga.misc import Bunch
from ginga import trcalc
import ginga.util.six as six
from ginga.util.six.moves import map


class AstroHeader(Header):
    pass


class AstroImage(BaseImage):
    """
    Abstraction of an astronomical data (image).

    NOTE: this module is NOT thread-safe!
    """
    # class variables for WCS and IO can be set
    wcsClass = None
    ioClass = None

    @classmethod
    def set_wcsClass(cls, klass):
        cls.wcsClass = klass

    @classmethod
    def set_ioClass(cls, klass):
        cls.ioClass = klass

    def __init__(self, data_np=None, metadata=None, logger=None,
                 name=None, wcsclass=wcsClass, ioclass=ioClass,
                 inherit_primary_header=False):

        BaseImage.__init__(self, data_np=data_np, metadata=metadata,
                           logger=logger, name=name)

        # wcsclass specifies a pluggable WCS module
        if wcsclass is None:
            wcsclass = wcsmod.WCS
        self.wcs = wcsclass(self.logger)

        # ioclass specifies a pluggable IO module
        if ioclass is None:
            ioclass = io_fits.fitsLoaderClass
        self.io = ioclass(self.logger)
        self.io.register_type('image', self.__class__)

        self.inherit_primary_header = inherit_primary_header
        if self.inherit_primary_header:
            # User wants to inherit from primary header--this will hold it
            self._primary_hdr = AstroHeader()
        else:
            self._primary_hdr = None

        if metadata is not None:
            header = self.get_header()
            self.wcs.load_header(header)

        # For navigating multidimensional data
        self.naxispath = []
        self.revnaxis = []
        self._md_data = None

    def setup_data(self, data, naxispath=None):
        # initialize data attribute to something reasonable
        if data is None:
            data = numpy.zeros((0, 0))
        elif not isinstance(data, numpy.ndarray):
            data = numpy.zeros((0, 0))
        elif 0 in data.shape:
            data = numpy.zeros((0, 0))
        elif len(data.shape) < 2:
            # Expand 1D arrays into 1xN array
            data = data.reshape((1, data.shape[0]))

        # this is a handle to the full data array
        self._md_data = data

        # this will get reset in set_naxispath() if array is
        # multidimensional
        self._data = data

        if naxispath is None:
            naxispath = []

        # Set naxispath to drill down to first 2D data slice
        if len(naxispath) == 0:
            naxispath = ([0] * (len(data.shape) - 2))

        self.set_naxispath(naxispath)


    def load_hdu(self, hdu, fobj=None, naxispath=None,
                 inherit_primary_header=None):

        if self.io is None:
            # need image loader for the fromHDU() call below
            raise ImageError("No IO loader defined")

        self.clear_metadata()

        # collect HDU header
        ahdr = self.get_header()
        self.io.fromHDU(hdu, ahdr)

        # Set PRIMARY header
        if inherit_primary_header is None:
            inherit_primary_header = self.inherit_primary_header
        else:  # This ensures get_header() is consistent
            self.inherit_primary_header = inherit_primary_header

        if inherit_primary_header and (fobj is not None):
            if self._primary_hdr is None:
                self._primary_hdr = AstroHeader()

            self.io.fromHDU(fobj[0], self._primary_hdr)

        self.setup_data(hdu.data)

        # Try to make a wcs object on the header
        self.wcs.load_header(hdu.header, fobj=fobj)

    def load_file(self, filespec, **kwargs):

        if self.io is None:
            raise ImageError("No IO loader defined")

        self.io.load_file(filespec, dstobj=self, **kwargs)

    def load_data(self, data_np, naxispath=None, metadata=None):

        self.clear_metadata()

        self.setup_data(data_np, naxispath=naxispath)

        if metadata is not None:
            self.update_metadata(metadata)

    def load_buffer(self, buf, dims, dtype, byteswap=False,
                    naxispath=None, metadata=None):
        data = numpy.fromstring(buf, dtype=dtype)
        if byteswap:
            data.byteswap(True)
        data = data.reshape(dims)

        self.load_data(data, naxispath=naxispath, metadata=metadata)

    def get_mddata(self):
        return self._md_data

    def set_naxispath(self, naxispath):
        """Choose a slice out of multidimensional data.
        """
        revnaxis = list(naxispath)
        revnaxis.reverse()

        # construct slice view and extract it
        view = revnaxis + [slice(None), slice(None)]
        data = self.get_mddata()[view]

        if len(data.shape) != 2:
            raise ImageError(
                "naxispath does not lead to a 2D slice: {}".format(naxispath))

        self.naxispath = naxispath
        self.revnaxis = revnaxis

        self.set_data(data)

    def set_wcs(self, wcs):
        self.wcs = wcs

    def set_io(self, io):
        self.io = io

    def get_data_size(self):
        return self.get_size()

    def get_header(self, create=True):
        try:
            # By convention, the fits header is stored in a dictionary
            # under the metadata keyword 'header'
            hdr = self.metadata['header']

            if self.inherit_primary_header and self._primary_hdr is not None:
                # Inherit PRIMARY header for display but keep metadata intact
                displayhdr = AstroHeader()
                for key in hdr.keyorder:
                    card = hdr.get_card(key)
                    bnch = displayhdr.__setitem__(card.key, card.value)
                    bnch.comment = card.comment
                for key in self._primary_hdr.keyorder:
                    if key not in hdr:
                        card = self._primary_hdr.get_card(key)
                        bnch = displayhdr.__setitem__(card.key, card.value)
                        bnch.comment = card.comment
            else:
                # Normal, separate header
                displayhdr = hdr

        except KeyError as e:
            if not create:
                raise e
            hdr = AstroHeader()
            self.metadata['header'] = hdr
            displayhdr = hdr

        return displayhdr

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
        return list(map(self.get_keyword, args))

    def set_keyword(self, kwd, value, create=True):
        kwds = self.get_header(create=create)
        kwd = kwd.upper()
        if not create:
            prev = kwds[kwd]  # noqa, this raises KeyError
        kwds[kwd] = value

    def update_keywords(self, keyDict):
        hdr = self.get_header()
        # Upcase all keywords
        for kwd, val in keyDict.items():
            hdr[kwd.upper()] = val

        # Try to make a wcs object on the header
        if hasattr(self, 'wcs'):
            self.wcs.load_header(hdr)

    def set_keywords(self, **kwds):
        """Set an item in the fits header, if any."""
        return self.update_keywords(kwds)

    def update_data(self, data_np, metadata=None, astype=None):
        """DO NOT USE: this method will be deprecated!
        """
        self.set_data(data_np.copy(), metadata=metadata,
                      astype=astype)

    def update_metadata(self, key_dict):
        for key, val in key_dict.items():
            self.metadata[key] = val

        # refresh the WCS
        if hasattr(self, 'wcs'):
            header = self.get_header()
            self.wcs.load_header(header)

    def clear_all(self):
        # clear metadata and data
        super(AstroImage, self).clear_all()

        # unreference full data array
        self._md_data = self._data

    def transfer(self, other, astype=None):
        data = self._get_data()
        other.update_data(data, astype=astype)
        other.update_metadata(self.metadata)

    def copy(self, astype=None):
        data = self._get_data()
        other = AstroImage(data, logger=self.logger)
        self.transfer(other, astype=astype)
        return other

    def save_as_file(self, filepath, **kwdargs):
        data = self._get_data()
        header = self.get_header()
        self.io.save_as_file(filepath, data, header, **kwdargs)

    def pixtocoords(self, x, y, system=None, coords='data'):
        args = [x, y] + self.revnaxis
        return self.wcs.pixtocoords(args, system=system, coords=coords)

    def spectral_coord(self, coords='data'):
        args = [0, 0] + self.revnaxis
        return self.wcs.spectral_coord(args, coords=coords)

    def pixtoradec(self, x, y, format='deg', coords='data'):
        args = [x, y] + self.revnaxis
        ra_deg, dec_deg = self.wcs.pixtoradec(args, coords=coords)

        if format == 'deg':
            return ra_deg, dec_deg
        return wcs.deg2fmt(ra_deg, dec_deg, format)

    def radectopix(self, ra_deg, dec_deg, format='deg', coords='data'):
        if format != 'deg':
            # convert coordinates to degrees
            ra_deg = wcs.lon_to_deg(ra_deg)
            dec_deg = wcs.lat_to_deg(dec_deg)
        return self.wcs.radectopix(ra_deg, dec_deg, coords=coords,
                                   naxispath=self.revnaxis)

    # -----> TODO: merge into wcs.py ?
    #
    def get_starsep_XY(self, x1, y1, x2, y2):
        # source point
        ra_org, dec_org = self.pixtoradec(x1, y1)

        # destination point
        ra_dst, dec_dst = self.pixtoradec(x2, y2)

        return wcs.get_starsep_RaDecDeg(ra_org, dec_org, ra_dst, dec_dst)

    def calc_radius_xy(self, x, y, radius_deg):
        """Calculate a radius (in pixels) from the point (x, y) to a circle
        defined by radius in degrees.
        """
        # calculate ra/dec of x,y pixel
        ra_deg, dec_deg = self.pixtoradec(x, y)

        # Calculate position 1 degree from the given one
        # NOTE: this needs to add in DEC, not RA
        ra2_deg, dec2_deg = wcs.add_offset_radec(ra_deg, dec_deg,
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

    def add_offset_xy(self, x, y, delta_deg_x, delta_deg_y):
        # calculate ra/dec of x,y pixel
        ra_deg, dec_deg = self.pixtoradec(x, y)

        # add offsets
        ra2_deg, dec2_deg = wcs.add_offset_radec(ra_deg, dec_deg,
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
    #
    # <----- TODO: merge this into wcs.py ?

    def get_wcs_rotation_deg(self):
        header = self.get_header()
        (rot, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header)
        return rot

    def rotate(self, deg, update_wcs=False):
        #old_deg = self.get_wcs_rotation_deg()

        super(AstroImage, self).rotate(deg)

        # TODO: currently this is not working!
        ## if update_wcs:
        ##     self.wcs.rotate(deg)

    def mosaic_inline(self, imagelist, bg_ref=None, trim_px=None,
                      merge=False, allow_expand=True, expand_pad_deg=0.01,
                      max_expand_pct=None,
                      update_minmax=True, suppress_callback=False):
        """Drops new images into the current image (if there is room),
        relocating them according the WCS between the two images.
        """
        # Get our own (mosaic) rotation and scale
        header = self.get_header()
        ((xrot_ref, yrot_ref),
         (cdelt1_ref, cdelt2_ref)) = wcs.get_xy_rotation_and_scale(header)

        scale_x, scale_y = math.fabs(cdelt1_ref), math.fabs(cdelt2_ref)

        # drop each image in the right place in the new data array
        mydata = self._get_data()

        count = 1
        res = []
        for image in imagelist:
            name = image.get('name', 'image%d' % (count))
            count += 1

            data_np = image._get_data()

            # Calculate sky position at the center of the piece
            ctr_x, ctr_y = trcalc.get_center(data_np)
            ra, dec = image.pixtoradec(ctr_x, ctr_y)

            # User specified a trim?  If so, trim edge pixels from each
            # side of the array
            ht, wd = data_np.shape[:2]
            if trim_px:
                xlo, xhi = trim_px, wd - trim_px
                ylo, yhi = trim_px, ht - trim_px
                data_np = data_np[ylo:yhi, xlo:xhi, ...]
                ht, wd = data_np.shape[:2]

            # If caller asked us to match background of pieces then
            # get the median of this piece
            if bg_ref is not None:
                bg = iqcalc.get_median(data_np)
                bg_inc = bg_ref - bg
                data_np = data_np + bg_inc

            # Determine max/min to update our values
            if update_minmax:
                maxval = numpy.nanmax(data_np)
                minval = numpy.nanmin(data_np)
                self.maxval = max(self.maxval, maxval)
                self.minval = min(self.minval, minval)

            # Get rotation and scale of piece
            header = image.get_header()
            ((xrot, yrot),
             (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(header)
            self.logger.debug("image(%s) xrot=%f yrot=%f cdelt1=%f "
                              "cdelt2=%f" % (name, xrot, yrot, cdelt1, cdelt2))

            # scale if necessary
            # TODO: combine with rotation?
            if (not numpy.isclose(math.fabs(cdelt1), scale_x) or
                    not numpy.isclose(math.fabs(cdelt2), scale_y)):
                nscale_x = math.fabs(cdelt1) / scale_x
                nscale_y = math.fabs(cdelt2) / scale_y
                self.logger.debug("scaling piece by x(%f), y(%f)" % (
                    nscale_x, nscale_y))
                data_np, (ascale_x, ascale_y) = trcalc.get_scaled_cutout_basic(
                    data_np, 0, 0, wd-1, ht-1, nscale_x, nscale_y,
                    logger=self.logger)

            # Rotate piece into our orientation, according to wcs
            rot_dx, rot_dy = xrot - xrot_ref, yrot - yrot_ref

            flip_x = False
            flip_y = False

            # Optomization for 180 rotations
            if (numpy.isclose(math.fabs(rot_dx), 180.0) or
                    numpy.isclose(math.fabs(rot_dy), 180.0)):
                rotdata = trcalc.transform(data_np,
                                           flip_x=True, flip_y=True)
                rot_dx = 0.0
                rot_dy = 0.0
            else:
                rotdata = data_np

            # Finish with any necessary rotation of piece
            if not numpy.isclose(rot_dy, 0.0):
                rot_deg = rot_dy
                self.logger.debug("rotating %s by %f deg" % (name, rot_deg))
                rotdata = trcalc.rotate(rotdata, rot_deg,
                                        #rotctr_x=ctr_x, rotctr_y=ctr_y
                                        logger=self.logger)

            # Flip X due to negative CDELT1
            if numpy.sign(cdelt1) != numpy.sign(cdelt1_ref):
                flip_x = True

            # Flip Y due to negative CDELT2
            if numpy.sign(cdelt2) != numpy.sign(cdelt2_ref):
                flip_y = True

            if flip_x or flip_y:
                rotdata = trcalc.transform(rotdata,
                                           flip_x=flip_x, flip_y=flip_y)

            # Get size and data of new image
            ht, wd = rotdata.shape[:2]
            ctr_x, ctr_y = trcalc.get_center(rotdata)

            # Find location of image piece (center) in our array
            x0, y0 = self.radectopix(ra, dec)

            # Merge piece as closely as possible into our array
            # Unfortunately we lose a little precision rounding to the
            # nearest pixel--can't be helped with this approach
            x0, y0 = int(round(x0)), int(round(y0))
            self.logger.debug("Fitting image '%s' into mosaic at %d,%d" % (
                name, x0, y0))

            # This is for useful debugging info only
            my_ctr_x, my_ctr_y = trcalc.get_center(mydata)
            off_x, off_y = x0 - my_ctr_x, y0 - my_ctr_y
            self.logger.debug("centering offsets: %d,%d" % (off_x, off_y))

            # Sanity check piece placement
            xlo, xhi = x0 - ctr_x, x0 + wd - ctr_x
            ylo, yhi = y0 - ctr_y, y0 + ht - ctr_y
            assert (xhi - xlo == wd), \
                Exception("Width differential %d != %d" % (xhi - xlo, wd))
            assert (yhi - ylo == ht), \
                Exception("Height differential %d != %d" % (yhi - ylo, ht))

            mywd, myht = self.get_size()
            if xlo < 0 or xhi > mywd or ylo < 0 or yhi > myht:
                if not allow_expand:
                    raise Exception("New piece doesn't fit on image and "
                                    "allow_expand=False")

                # <-- Resize our data array to allow the new image

                # determine amount to pad expansion by
                expand_x = max(int(expand_pad_deg / scale_x), 0)
                expand_y = max(int(expand_pad_deg / scale_y), 0)

                nx1_off, nx2_off = 0, 0
                if xlo < 0:
                    nx1_off = abs(xlo) + expand_x
                if xhi > mywd:
                    nx2_off = (xhi - mywd) + expand_x
                xlo, xhi = xlo + nx1_off, xhi + nx1_off

                ny1_off, ny2_off = 0, 0
                if ylo < 0:
                    ny1_off = abs(ylo) + expand_y
                if yhi > myht:
                    ny2_off = (yhi - myht) + expand_y
                ylo, yhi = ylo + ny1_off, yhi + ny1_off

                new_wd = mywd + nx1_off + nx2_off
                new_ht = myht + ny1_off + ny2_off

                # sanity check on new mosaic size
                old_area = mywd * myht
                new_area = new_wd * new_ht
                expand_pct = new_area / old_area
                if ((max_expand_pct is not None) and
                        (expand_pct > max_expand_pct)):
                    raise Exception("New area exceeds current one by %.2f %%;"
                                    "increase max_expand_pct (%.2f) to allow" %
                                    (expand_pct*100, max_expand_pct))

                # go for it!
                new_data = numpy.zeros((new_ht, new_wd))
                # place current data into new data
                new_data[ny1_off:ny1_off+myht, nx1_off:nx1_off+mywd] = \
                    mydata
                self._data = new_data
                mydata = new_data

                if (nx1_off > 0) or (ny1_off > 0):
                    # Adjust our WCS for relocation of the reference pixel
                    crpix1, crpix2 = self.get_keywords_list('CRPIX1', 'CRPIX2')
                    kwds = dict(CRPIX1=crpix1 + nx1_off,
                                CRPIX2=crpix2 + ny1_off)
                    self.update_keywords(kwds)

            # fit image piece into our array
            try:
                if merge:
                    mydata[ylo:yhi, xlo:xhi, ...] += rotdata[0:ht, 0:wd, ...]
                else:
                    idx = (mydata[ylo:yhi, xlo:xhi, ...] == 0.0)
                    mydata[ylo:yhi, xlo:xhi, ...][idx] = \
                        rotdata[0:ht, 0:wd, ...][idx]

            except Exception as e:
                self.logger.error("Error fitting tile: %s" % (str(e)))
                raise

            res.append((xlo, ylo, xhi, yhi))

        # TODO: recalculate min and max values
        # Can't use usual techniques because it adds too much time to the
        # mosacing
        #self._set_minmax()

        # Notify watchers that our data has changed
        if not suppress_callback:
            self.make_callback('modified')

        return res

    def info_xy(self, data_x, data_y, settings):
        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = self.get_data_xy(int(data_x+0.5), int(data_y+0.5))

        except Exception as e:
            value = None

        system = settings.get('wcs_coords', None)
        format = settings.get('wcs_display', 'sexagesimal')
        ra_lbl, dec_lbl = six.unichr(945), six.unichr(948)

        # Calculate WCS coords, if available
        try:
            if self.wcs is None:
                self.logger.debug("No WCS for this image")
                ra_txt = dec_txt = 'NO WCS'

            elif self.wcs.coordsys == 'raw':
                self.logger.debug("No coordinate system determined")
                ra_txt = dec_txt = 'NO WCS'

            elif self.wcs.coordsys == 'pixel':
                args = [data_x, data_y] + self.revnaxis
                x, y = self.wcs.pixtosystem(args, system=system, coords='data')
                ra_txt = "%+.3f" % (x)
                dec_txt = "%+.3f" % (y)
                ra_lbl, dec_lbl = "X", "Y"

            else:
                args = [data_x, data_y] + self.revnaxis

                lon_deg, lat_deg = self.wcs.pixtosystem(
                    args, system=system, coords='data')

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
                    ra_lbl, dec_lbl = six.unichr(0x03BB), six.unichr(0x03B2)
                elif system == 'helioprojective':
                    ra_txt = "%+5.3f" % (lon_deg*3600)
                    dec_txt = "%+5.3f" % (lat_deg*3600)
                    ra_lbl, dec_lbl = "x-Solar", "y-Solar"

        except Exception as e:
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = dec_txt = 'BAD WCS'
            try:
                # log traceback, if possible
                (type_, value_, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))
            except Exception:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)

        info = Bunch.Bunch(itype='astro', data_x=data_x, data_y=data_y,
                           x=data_x, y=data_y,
                           ra_txt=ra_txt, dec_txt=dec_txt,
                           ra_lbl=ra_lbl, dec_lbl=dec_lbl,
                           value=value)
        return info

# END
