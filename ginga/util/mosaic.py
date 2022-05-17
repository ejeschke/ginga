#
# mosaic.py -- Classes for quick and dirty mosaicing of FITS images
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import time
import warnings

import numpy as np

from ginga import AstroImage, trcalc
from ginga.util import wcs, loader, dp, iqcalc
from ginga.util import io_fits
from ginga.misc import Callback, Settings


def get_warp_indexes(shape_in, wcs_in, wcs_out):
    """Get numpy index arrays to warp an image into another projection.

    For every pixel coordinate for numpy array shape ``shape_in``,
    convert to wcs coordinates according to ``wcs_in`` and then back
    to pixel coordinates according to ``wcs_out``.

    Parameters
    ----------
    shape_in : numpy ndarray shape
        The shape of the array to be projected

    wcs_in : subclass of `~ginga.util.wcsmod.common.BaseWCS`
        Ginga WCS wrapper that is associated with the input array

    wcs_out : subclass of `~ginga.util.wcsmod.common.BaseWCS`
        Ginga WCS wrapper that is associated with the output

    Returns
    -------
    Returns a 3-tuple (old_pts, coords, new_pts), where all three
    arrays are Nx2
    """
    ht, wd = shape_in[:2]
    yi, xi = np.mgrid[0:ht, 0:wd]
    old_pts = np.array((xi.ravel(), yi.ravel())).T

    # convert data coords of pixels as sky coords
    coords = wcs_in.datapt_to_wcspt(old_pts)

    # calc these sky points in data x, y according to the *wcs_ref*
    new_pts = wcs_out.wcspt_to_datapt(coords)

    return (old_pts, coords, new_pts)


def warp_image(data_in, wcs_in, wcs_out, fill=None, pixel_radius=1):
    """Warp image in 2D numpy array ``data`` to a new array.

    Warps ``data_in`` using ``wcs_in`` and projecting into ``wcs_out``.
    The resulting array may have empty pixels which are initially filled
    with ``fill`` and then computed from the median value of surrounding
    pixels at a radius of ``pixel_radius``.

    Parameters
    ----------
    data_in : numpy 2D ndarray
        The array to be warped (projected)

    wcs_in : subclass of `~ginga.util.wcsmod.common.BaseWCS`
        Ginga WCS wrapper that is associated with the input array

    wcs_out : subclass of `~ginga.util.wcsmod.common.BaseWCS`
        Ginga WCS wrapper that is associated with the output

    fill : scalar value or `None` (optional, defaults to `None`)
        The value to initially fill the new output image array

    pixel_radius : `int` (optional, defaults to 1)
        The pixel radius to use for collecting values to fill empty pixels

    Returns
    -------
    Returns a 5-tuple (data_out, old_pts, coords, new_pts, out_pts).
    ``data_out`` is the warped image, with an alpha mask layer attached.
    ``out_pts`` is a Nx2 array describing the relocated pixels in data_out.

    See ``get_warp_indexes`` for discussion of the ``old_pts``, ``coords``
    and ``new_pts`` return values.
    """
    old_pts, coords, new_pts = get_warp_indexes(data_in.shape, wcs_in, wcs_out)

    # round to nearest int
    new_pts = np.rint(new_pts).astype(int)

    # get bounds of array values
    mn, mx = trcalc.get_bounds(new_pts)

    # subtract minimums to turn pixel coordinates into offsets
    out_pts = new_pts - mn

    # np fancy indexing to warp array as necessary
    x, y = old_pts.T
    nx, ny = out_pts.T

    if fill is None:
        # select a suitable fill value if one is not provided
        if issubclass(data_in.dtype.type, np.floating):
            fill = np.nan
        else:
            fill = 0

    # allocate new array
    new_wd, new_ht = mx - mn + np.array((1, 1))
    data_out = np.full((new_ht, new_wd, 2), fill, dtype=data_in.dtype)

    # prepare mask, will be True where there are empty pixels in the image
    mask = np.full(data_out.shape[:2], True, dtype=bool)
    mask[ny, nx] = False

    # fill alpha layer with zeros where we have empty pixels and ones
    # otherwise
    data_out[..., 1][mask] = 0
    data_out[..., 1][~mask] = 1

    # warp the data into the destination image
    data_out[ny, nx, 0] = data_in[y, x]

    if pixel_radius > 0:
        # fill in holes in output image with median values of surrounding
        # pixels  NOTE: this also fills in alpha layer values
        y, x = np.where(mask)
        pr = pixel_radius
        offsets = [(x, y)
                   for x in range(-pr, pr + 1) for y in range(-pr, pr + 1)]
        offsets.remove((0, 0))
        _arrs = [data_out[_y, _x]
                 for _x, _y in [((x + offsets[i][0]).clip(0, new_wd - 1),
                                 (y + offsets[i][1]).clip(0, new_ht - 1))
                                for i in range(len(offsets))]]

        with warnings.catch_warnings():
            # we can get a "RuntimeWarning: All-NaN slice encountered"
            # which is ok as we simply let this resolve to NaN
            warnings.simplefilter("ignore")
            vals = np.nanmedian(np.dstack(_arrs), axis=2)
        _arrs = None   # deref arrays
        data_out[y, x] = vals

    # finally multipy alpha layer by mx_v to achieve full opacity where it
    # is wanted
    mn_v, mx_v = trcalc.get_minmax_dtype(data_out.dtype)
    data_out[..., 1] *= mx_v

    return (data_out, old_pts, coords, new_pts, out_pts)


def mosaic_inline(baseimage, imagelist, bg_ref=None, trim_px=None,
                  merge=False, allow_expand=True, expand_pad_deg=0.01,
                  max_expand_pct=None,
                  update_minmax=True, suppress_callback=False):
    """Drops new images into the image `baseimage` (if there is room),
    relocating them according the WCS between the two images.
    """
    # Get our own (mosaic) rotation and scale
    header = baseimage.get_header()
    ((xrot_ref, yrot_ref),
     (cdelt1_ref, cdelt2_ref)) = wcs.get_xy_rotation_and_scale(header)

    scale_x, scale_y = math.fabs(cdelt1_ref), math.fabs(cdelt2_ref)

    # drop each image in the right place in the new data array
    mydata = baseimage._get_data()

    count = 1
    res = []
    for image in imagelist:
        name = image.get('name', 'image%d' % (count))
        count += 1

        data_np = image._get_data()
        if 0 in data_np.shape:
            baseimage.logger.info("Skipping image with zero length axis")
            continue

        # Calculate sky position at the center of the piece
        ctr_x, ctr_y = trcalc.get_center(data_np)
        ra, dec = image.pixtoradec(ctr_x, ctr_y, coords='data')

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
            maxval = np.nanmax(data_np)
            minval = np.nanmin(data_np)
            baseimage.maxval = max(baseimage.maxval, maxval)
            baseimage.minval = min(baseimage.minval, minval)

        # Get rotation and scale of piece
        header = image.get_header()
        ((xrot, yrot),
         (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(header)
        baseimage.logger.debug("image(%s) xrot=%f yrot=%f cdelt1=%f "
                               "cdelt2=%f" % (name, xrot, yrot, cdelt1, cdelt2))

        # scale if necessary
        # TODO: combine with rotation?
        if (not np.isclose(math.fabs(cdelt1), scale_x) or
            not np.isclose(math.fabs(cdelt2), scale_y)):
            nscale_x = math.fabs(cdelt1) / scale_x
            nscale_y = math.fabs(cdelt2) / scale_y
            baseimage.logger.debug("scaling piece by x(%f), y(%f)" % (
                nscale_x, nscale_y))
            data_np, (ascale_x, ascale_y) = trcalc.get_scaled_cutout_basic(
                data_np, 0, 0, wd - 1, ht - 1, nscale_x, nscale_y,
                logger=baseimage.logger)

        # Rotate piece into our orientation, according to wcs
        rot_dx, rot_dy = xrot - xrot_ref, yrot - yrot_ref

        flip_x = False
        flip_y = False

        # Optomization for 180 rotations
        if (np.isclose(math.fabs(rot_dx), 180.0) or
            np.isclose(math.fabs(rot_dy), 180.0)):
            rotdata = trcalc.transform(data_np,
                                       flip_x=True, flip_y=True)
            rot_dx = 0.0
            rot_dy = 0.0
        else:
            rotdata = data_np

        # Finish with any necessary rotation of piece
        if not np.isclose(rot_dy, 0.0):
            rot_deg = rot_dy
            baseimage.logger.debug("rotating %s by %f deg" % (name, rot_deg))
            rotdata = trcalc.rotate(rotdata, rot_deg,
                                    #rotctr_x=ctr_x, rotctr_y=ctr_y
                                    logger=baseimage.logger)

        # Flip X due to negative CDELT1
        if np.sign(cdelt1) != np.sign(cdelt1_ref):
            flip_x = True

        # Flip Y due to negative CDELT2
        if np.sign(cdelt2) != np.sign(cdelt2_ref):
            flip_y = True

        if flip_x or flip_y:
            rotdata = trcalc.transform(rotdata,
                                       flip_x=flip_x, flip_y=flip_y)

        # Get size and data of new image
        ht, wd = rotdata.shape[:2]
        ctr_x, ctr_y = trcalc.get_center(rotdata)

        # Find location of image piece (center) in our array
        x0, y0 = baseimage.radectopix(ra, dec, coords='data')

        # Merge piece as closely as possible into our array
        # Unfortunately we lose a little precision rounding to the
        # nearest pixel--can't be helped with this approach
        x0, y0 = int(np.rint(x0)), int(np.rint(y0))
        baseimage.logger.debug("Fitting image '%s' into mosaic at %d,%d" % (
            name, x0, y0))

        # This is for useful debugging info only
        my_ctr_x, my_ctr_y = trcalc.get_center(mydata)
        off_x, off_y = x0 - my_ctr_x, y0 - my_ctr_y
        baseimage.logger.debug("centering offsets: %d,%d" % (off_x, off_y))

        # Sanity check piece placement
        xlo, xhi = x0 - ctr_x, x0 + wd - ctr_x
        ylo, yhi = y0 - ctr_y, y0 + ht - ctr_y
        assert (xhi - xlo == wd), \
            Exception("Width differential %d != %d" % (xhi - xlo, wd))
        assert (yhi - ylo == ht), \
            Exception("Height differential %d != %d" % (yhi - ylo, ht))

        mywd, myht = baseimage.get_size()
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
                                (expand_pct * 100, max_expand_pct))

            # go for it!
            new_data = np.zeros((new_ht, new_wd))
            # place current data into new data
            new_data[ny1_off:ny1_off + myht, nx1_off:nx1_off + mywd] = \
                mydata
            baseimage._data = new_data
            mydata = new_data

            if (nx1_off > 0) or (ny1_off > 0):
                # Adjust our WCS for relocation of the reference pixel
                crpix1, crpix2 = baseimage.get_keywords_list('CRPIX1', 'CRPIX2')
                kwds = dict(CRPIX1=crpix1 + nx1_off,
                            CRPIX2=crpix2 + ny1_off,
                            NAXIS1=new_wd, NAXIS2=new_ht)
                baseimage.update_keywords(kwds)

        # fit image piece into our array
        try:
            if merge:
                mydata[ylo:yhi, xlo:xhi, ...] += rotdata[0:ht, 0:wd, ...]
            else:
                idx = (mydata[ylo:yhi, xlo:xhi, ...] == 0.0)
                mydata[ylo:yhi, xlo:xhi, ...][idx] = \
                    rotdata[0:ht, 0:wd, ...][idx]

        except Exception as e:
            baseimage.logger.error("Error fitting tile: %s" % (str(e)))
            raise

        res.append((xlo, ylo, xhi, yhi))

    # TODO: recalculate min and max values
    # Can't use usual techniques because it adds too much time to the
    # mosacing
    #baseimage._set_minmax()

    # Notify watchers that our data has changed
    if not suppress_callback:
        baseimage.make_callback('modified')

    return res


def mosaic(logger, itemlist, fov_deg=None):
    """
    Parameters
    ----------
    logger : logger object
        a logger object passed to created AstroImage instances
    itemlist : sequence like
        a sequence of either filenames or AstroImage instances
    """

    if isinstance(itemlist[0], AstroImage.AstroImage):
        image0 = itemlist[0]
        name = image0.get('name', 'image0')
    else:
        # Assume it is a file and load it
        filepath = itemlist[0]
        logger.info("Reading file '%s' ..." % (filepath))
        image0 = loader.load_data(filepath, logger=logger)
        name = filepath

    ra_deg, dec_deg = image0.get_keywords_list('CRVAL1', 'CRVAL2')
    header = image0.get_header()
    (rot_deg, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header)
    logger.debug("image0 rot=%f cdelt1=%f cdelt2=%f" % (rot_deg,
                                                        cdelt1, cdelt2))

    px_scale = math.fabs(cdelt1)
    expand = False
    if fov_deg is None:
        # TODO: calculate fov?
        expand = True

    cdbase = [np.sign(cdelt1), np.sign(cdelt2)]
    img_mosaic = dp.create_blank_image(ra_deg, dec_deg,
                                       fov_deg, px_scale, rot_deg,
                                       cdbase=cdbase,
                                       logger=logger)
    header = img_mosaic.get_header()
    (rot, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header)
    logger.debug("mosaic rot=%f cdelt1=%f cdelt2=%f" % (rot, cdelt1, cdelt2))

    logger.debug("Processing '%s' ..." % (name))
    tup = mosaic_inline(img_mosaic, [image0], allow_expand=expand)
    logger.debug("placement %s" % (str(tup)))

    count = 1
    for item in itemlist[1:]:
        if isinstance(item, AstroImage.AstroImage):
            image = item
        else:
            # Create and load the image
            filepath = item
            logger.info("Reading file '%s' ..." % (filepath))
            image = io_fits.load_file(filepath, logger=logger)

        name = image.get('name', 'image%d' % (count))

        logger.debug("Inlining '%s' ..." % (name))
        tup = mosaic_inline(img_mosaic, [image])
        logger.debug("placement %s" % (str(tup)))
        count += 1

    logger.info("Done.")
    return img_mosaic


class ImageMosaicer(Callback.Callbacks):
    """Class for creating mosaics in a `~ginga.AstroImage.AstroImage`.

    Individual tiles are transformed and inserted into the right place
    in the image ndarray.  The array can be automatically enlarged as
    necessary to accomodate the new tiles.

    Typical usage:

    >>> mosaicer = ImageMosaicer(logger)
    >>> mosaicer.mosaic(images)

    where ``images`` is a list of `~ginga.AstroImage.AstroImage` that
    should be plotted in ``viewer``.
    """
    def __init__(self, logger, settings=None):
        super(ImageMosaicer, self).__init__()

        self.logger = logger

        self.ingest_count = 0
        # holds processed images to be inserted into mosaic image
        self.total_images = 0
        self.image_list = []

        # options
        if settings is None:
            settings = Settings.SettingGroup(name='mosaicer',
                                             logger=self.logger)
        self.t_ = settings
        self.t_.set_defaults(fov_deg=0.2,
                             match_bg=False, trim_px=0, merge=False,
                             mosaic_hdus=False, skew_limit=0.1,
                             allow_expand=True, expand_pad_deg=0.01,
                             reuse_image=False, mosaic_method='simple',
                             update_minmax=True, max_expand_pct=None,
                             annotate_images=False, annotate_color='pink',
                             annotate_fontsize=10.0, ann_fits_kwd=None,
                             ann_tag_pfx='ann_')

        # these are updated in prepare_mosaic() and represent measurements
        # on the reference image
        self.bg_ref = 0.0
        self.xrot_ref, self.yrot_ref = 0.0, 0.0
        self.cdelt1_ref, self.cdelt2_ref = 1.0, 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.baseimage = None

        for name in ['progress', 'finished']:
            self.enable_callback(name)

    def get_settings(self):
        return self.t_

    def prepare_mosaic(self, ref_image):
        """Prepare a new (blank) mosaic image based on the pointing of
        the reference image ``ref_image``.
        Returns a `~ginga.AstroImage.AstroImage`

        This method is typically called internally.
        """
        # if user requesting us to match backgrounds, then calculate
        # median of root image and save it
        data_np = ref_image.get_data()
        dtype = data_np.dtype
        #dtype = None
        if issubclass(dtype.type, np.floating):
            fill = np.nan
        else:
            fill = 0
        fov_deg = self.t_['fov_deg']

        if self.t_['match_bg']:
            self.bg_ref = iqcalc.get_median(data_np)

        header = ref_image.get_header()
        ra_deg, dec_deg = header['CRVAL1'], header['CRVAL2']

        (rot_deg, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header,
                                                               skew_threshold=self.t_['skew_limit'])
        self.logger.debug("ref_image rot=%f cdelt1=%f cdelt2=%f" % (rot_deg,
                                                                    cdelt1, cdelt2))

        # Prepare pixel scale for each axis
        px_scale = (math.fabs(cdelt1), math.fabs(cdelt2))
        cdbase = [np.sign(cdelt1), np.sign(cdelt2)]

        if not self.t_['reuse_image'] or self.baseimage is None:
            self.logger.debug("creating blank image to hold mosaic")
            # GC old mosaic
            self.baseimage = None

            self.baseimage = dp.create_blank_image(ra_deg, dec_deg,
                                                   fov_deg, px_scale, rot_deg,
                                                   cdbase=cdbase,
                                                   logger=self.logger,
                                                   pfx='mosaic',
                                                   dtype=dtype,
                                                   alpha=0, fill=fill)
        else:
            # <-- reuse image (faster)
            self.logger.debug("Reusing previous mosaic image")
            dp.recycle_image(self.baseimage, ra_deg, dec_deg,
                             fov_deg, px_scale, rot_deg,
                             cdbase=cdbase,
                             logger=self.logger,
                             pfx='mosaic', alpha=0, fill=fill)

        header = self.baseimage.get_header()

        # TODO: handle skew (differing rotation for each axis)?
        (rot_xy, cdelt_xy) = wcs.get_xy_rotation_and_scale(header)
        self.logger.debug("ref image rot_x=%f rot_y=%f cdelt1=%f cdelt2=%f" % (
            rot_xy[0], rot_xy[1], cdelt_xy[0], cdelt_xy[1]))

        # Store base image rotation and scale
        self.xrot_ref, self.yrot_ref = rot_xy
        self.cdelt1_ref, self.cdelt2_ref = cdelt_xy
        self.scale_x = math.fabs(cdelt_xy[0])
        self.scale_y = math.fabs(cdelt_xy[1])

        return self.baseimage

    def ingest_image(self, image):
        """Ingest an image, transform it and merge it in the right place in
        the image array.

        This method is typically called internally.
        """
        self.ingest_count += 1
        count = self.ingest_count
        tag = 'image{}'.format(count)
        name = image.get('name', tag)

        data_np = image._get_data()
        if 0 in data_np.shape:
            self.logger.info("Skipping image with zero length axis")
            return

        # Calculate sky position at the center of the piece
        ctr_x, ctr_y = trcalc.get_center(data_np)
        ra, dec = image.pixtoradec(ctr_x, ctr_y, coords='data')
        self.image_list.append((name, tag, ra, dec))

        # User specified a trim?  If so, trim edge pixels from each
        # side of the array
        ht, wd = data_np.shape[:2]
        if self.t_['trim_px'] is not None:
            xlo, xhi = self.t_['trim_px'], wd - self.t_['trim_px']
            ylo, yhi = self.t_['trim_px'], ht - self.t_['trim_px']
            data_np = data_np[ylo:yhi, xlo:xhi, ...]
            ht, wd = data_np.shape[:2]

        # If caller asked us to match background of pieces then
        # fix up this data
        if self.t_['match_bg']:
            bg = iqcalc.get_median(data_np)
            bg_inc = self.bg_ref - bg
            data_np = data_np + bg_inc

        # Determine max/min to update our values
        if self.t_['update_minmax']:
            maxval = np.nanmax(data_np)
            minval = np.nanmin(data_np)
            self.baseimage.maxval = max(self.baseimage.maxval, maxval)
            self.baseimage.minval = min(self.baseimage.minval, minval)

        # Get rotation and scale of piece
        header = image.get_header()
        ((xrot, yrot),
         (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(header)
        self.logger.debug("image(%s) xrot=%f yrot=%f cdelt1=%f "
                          "cdelt2=%f" % (name, xrot, yrot, cdelt1, cdelt2))

        # scale if necessary to scale of reference image
        if (not np.isclose(math.fabs(cdelt1), self.scale_x) or
            not np.isclose(math.fabs(cdelt2), self.scale_y)):
            nscale_x = math.fabs(cdelt1) / self.scale_x
            nscale_y = math.fabs(cdelt2) / self.scale_y
            self.logger.debug("scaling piece by x(%f), y(%f)" % (
                nscale_x, nscale_y))
            data_np, (ascale_x, ascale_y) = trcalc.get_scaled_cutout_basic(
                #data_np, 0, 0, wd - 1, ht - 1, nscale_x, nscale_y,
                data_np, 0, 0, wd, ht, nscale_x, nscale_y,
                logger=self.logger)

        mydata = self.baseimage._get_data()
        method = self.t_['mosaic_method']

        if method == 'simple':
            self.logger.debug("plotting by rotating/flipping image by WCS")
            # CASE 1: simple rotation and flips
            # Rotate piece into our orientation, according to wcs
            rot_dx, rot_dy = xrot - self.xrot_ref, yrot - self.yrot_ref

            flip_x = False
            flip_y = False

            # Optomization for 180 rotations
            if (np.isclose(math.fabs(rot_dx), 180.0) or
                np.isclose(math.fabs(rot_dy), 180.0)):
                rotdata = trcalc.transform(data_np,
                                           flip_x=True, flip_y=True)
                rot_dx = 0.0
                rot_dy = 0.0
            else:
                rotdata = data_np

            # convert to same type as basedata
            rotdata = rotdata.astype(mydata.dtype)

            # add an alpha layer
            minv, maxv = trcalc.get_minmax_dtype(rotdata.dtype)
            rotdata = trcalc.add_alpha(rotdata, alpha=maxv)

            # Finish with any necessary rotation of piece
            if not np.isclose(rot_dy, 0.0):
                rot_deg = rot_dy
                self.logger.debug("rotating %s by %f deg" % (name, rot_deg))
                rotdata = trcalc.rotate(rotdata, rot_deg,
                                        #rotctr_x=ctr_x, rotctr_y=ctr_y,
                                        logger=self.logger, pad=0)

            # Flip X due to negative CDELT1
            if np.sign(cdelt1) != np.sign(self.cdelt1_ref):
                flip_x = True

            # Flip Y due to negative CDELT2
            if np.sign(cdelt2) != np.sign(self.cdelt2_ref):
                flip_y = True

            if flip_x or flip_y:
                rotdata = trcalc.transform(rotdata,
                                           flip_x=flip_x, flip_y=flip_y)

            # Get size and data of new image
            ht, wd = rotdata.shape[:2]
            ctr_x, ctr_y = trcalc.get_center(rotdata)

            # Find location of image piece (center) in our array
            x0, y0 = self.baseimage.radectopix(ra, dec, coords='data')

            # Merge piece as closely as possible into our array
            # Unfortunately we lose a little precision rounding to the
            # nearest pixel--can't be helped with this approach
            x0, y0 = int(np.rint(x0)), int(np.rint(y0))
            self.logger.debug("Fitting image '%s' into mosaic at %f,%f" % (
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

        elif method == 'warp':
            # convert to same type as basedata
            data_np = data_np.astype(mydata.dtype)

            self.logger.debug("plotting by warping image according to WCS")
            # CASE 2: user wants precise transformation of image using WCS
            dst, old_pts, coords, new_pts, dst_pts = warp_image(data_np,
                                                                image.wcs,
                                                                self.baseimage.wcs)

            # Merge piece as closely as possible into our array
            # Unfortunately we lose a little precision rounding to the
            # nearest pixel--can't be helped with this approach
            xlo, ylo = np.rint(new_pts[0] - dst_pts[0]).astype(int)
            self.logger.debug("Fitting image '%s' into mosaic at %f,%f" % (
                name, xlo, ylo))

            ht, wd = dst.shape[:2]
            xhi, yhi = xlo + wd, ylo + ht

            rotdata = dst

        else:
            raise ValueError(f"don't understand mosaic method '{method}'")

        #-----------
        mywd, myht = self.baseimage.get_size()
        if xlo < 0 or xhi > mywd or ylo < 0 or yhi > myht:
            if not self.t_['allow_expand']:
                raise Exception("New piece doesn't fit on image and "
                                "allow_expand=False")

            # <-- Resize our data array to allow the new image

            # determine amount to pad expansion by
            expand_x = max(int(self.t_['expand_pad_deg'] / self.scale_x), 0)
            expand_y = max(int(self.t_['expand_pad_deg'] / self.scale_y), 0)

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
            if ((self.t_['max_expand_pct'] is not None) and
                    (expand_pct > self.t_['max_expand_pct'])):
                raise Exception("New area exceeds current one by %.2f %%;"
                                "increase max_expand_pct (%.2f) to allow" %
                                (expand_pct * 100, self.t_['max_expand_pct']))

            # go for it!
            #new_data = np.zeros((new_ht, new_wd))
            new_data = np.full((new_ht, new_wd, 2), np.nan, dtype=mydata.dtype)
            new_data[..., 1] = 0.0

            # place current data into new data
            new_data[ny1_off:ny1_off + myht, nx1_off:nx1_off + mywd] = mydata
            self.baseimage._data = new_data
            mydata = new_data

            if (nx1_off > 0) or (ny1_off > 0):
                # Adjust our WCS for relocation of the reference pixel
                crpix1, crpix2 = self.baseimage.get_keywords_list('CRPIX1', 'CRPIX2')
                kwds = dict(CRPIX1=crpix1 + nx1_off,
                            CRPIX2=crpix2 + ny1_off,
                            NAXIS1=new_wd, NAXIS2=new_ht)
                self.baseimage.update_keywords(kwds)

        # fit image piece into our array
        try:
            if self.t_['merge']:
                mydata[ylo:yhi, xlo:xhi, ...] += rotdata[0:ht, 0:wd, ...]
            else:
                mask = (mydata[ylo:yhi, xlo:xhi, 1] <= 0.0)
                mydata[ylo:yhi, xlo:xhi, ...][mask] = rotdata[0:ht, 0:wd, ...][mask]

        except Exception as e:
            self.logger.error("Error fitting tile: %s" % (str(e)))
            raise

        return (xlo, ylo, xhi, yhi)

    def ingest_one(self, image):
        """Ingest an image in the right place in the image array.

        This method is typically called internally.
        """
        llur = self.ingest_image(image)

        self.make_callback('progress', 'fitting',
                           float(self.ingest_count) / self.total_images)

    def reset(self):
        """Prepare for a new mosaic.
        The next call to ```mosaic`` will create a new mosaic.
        """
        self.baseimage = None
        self.image_list = []
        self.ingest_count = 0
        self.total_images = 0

    def annotate_images(self, canvas):
        tagpfx = self.t_['ann_tag_pfx']
        tags = canvas.get_tags_by_tag_pfx(tagpfx)
        canvas.delete_objects_by_tag(tags, redraw=False)

        if self.t_['annotate_images']:
            dc = canvas.get_draw_classes()
            for name, tag, ra, dec in self.image_list:
                x, y = self.baseimage.radectopix(ra, dec)
                text = dc.Text(x, y, name,
                               color=self.t_['annotate_color'],
                               fontsize=self.t_['annotate_fontsize'],
                               fontscale=True)
                tag = tagpfx + tag
                canvas.add(text, tag=tag, redraw=False)

        canvas.update_canvas(whence=3)

    def mosaic(self, images, ev_intr=None):
        """Create a mosaic of ``images``.

        Returns a `~ginga.AstroImage.AstroImage`
        """
        num_images = len(images)
        if num_images == 0:
            return
        self.total_images += num_images

        self.make_callback('progress', 'fitting', 0.0)
        t1 = time.time()

        # If there is no current mosaic then prepare a new one
        if self.baseimage is None:
            ref_image = images[0]
            self.prepare_mosaic(ref_image)

        self.logger.info("fitting tiles...")

        for image in images:
            if ev_intr is not None and ev_intr.is_set():
                raise Exception("interrupted by user")
            self.ingest_one(image)

        self.logger.info("finishing...")
        self.make_callback('progress', 'finishing', 0.0)

        self.process_elapsed = time.time() - t1
        self.logger.info("mosaic done. process=%.4f (sec)" % (
            self.process_elapsed))

        self.make_callback('finished', self.process_elapsed)

        return self.baseimage


class CanvasMosaicer(Callback.Callbacks):
    """Class for creating collages on a Ginga canvas.

    A collage is sort of like a mosaic, except that instead of creating a
    large image array, individual tiles are transformed and plotted on a
    canvas.

    Typical usage:

    >>> collager = CanvasMosaicer(logger)
    >>> collager.mosaic(viewer, images)

    where ``images`` is a list of `~ginga.AstroImage.AstroImage` that
    should be plotted in ``viewer``.
    """
    def __init__(self, logger, settings=None):
        super(CanvasMosaicer, self).__init__()

        self.logger = logger

        if settings is None:
            settings = Settings.SettingGroup(name='collager',
                                             logger=self.logger)
        # options
        self.t_ = settings
        self.t_.set_defaults(annotate_images=False, annotate_color='pink',
                             annotate_fontsize=10.0, ann_fits_kwd=None,
                             ann_tag_pfx='ann_',
                             match_bg=False, collage_method='simple',
                             center_image=False)

        self.ingest_count = 0
        # holds processed images to be inserted into mosaic image
        self.total_images = 0

        # these are updated in prepare_mosaic() and represent measurements
        # on the reference image
        self.bg_ref = 0.0
        self.xrot_ref, self.yrot_ref = 0.0, 0.0
        self.cdelt1_ref, self.cdelt2_ref = 1.0, 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.limits = None
        self.ref_image = None
        self.image_list = []

        for name in ['progress', 'finished']:
            self.enable_callback(name)

    def get_settings(self):
        return self.t_

    def prepare_mosaic(self, ref_image):
        """Prepare for a new mosaic image based on the pointing of
        the reference image ``ref_image``.

        This method is typically called internally.
        """
        self.ref_image = ref_image

        # if user requesting us to match backgrounds, then calculate
        # median of root image and save it
        if self.t_['match_bg']:
            data_np = ref_image.get_data()
            self.bg_ref = iqcalc.get_median(data_np)

        header = ref_image.get_header()

        # TODO: handle skew (differing rotation for each axis)?
        (rot_xy, cdelt_xy) = wcs.get_xy_rotation_and_scale(header)
        self.logger.debug("ref image rot_x=%f rot_y=%f cdelt1=%f cdelt2=%f" % (
            rot_xy[0], rot_xy[1], cdelt_xy[0], cdelt_xy[1]))

        # Store base image rotation and scale
        self.xrot_ref, self.yrot_ref = rot_xy
        self.cdelt1_ref, self.cdelt2_ref = cdelt_xy
        self.scale_x = math.fabs(cdelt_xy[0])
        self.scale_y = math.fabs(cdelt_xy[1])
        self.limits = ((0, 0), (0, 0))

    def _get_name_tag(self, image):
        self.ingest_count += 1
        tag = 'image{}'.format(self.ingest_count)

        ann_fits_kwd = self.t_['ann_fits_kwd']
        if ann_fits_kwd is not None:
            header = image.get_header()
            name = str(header[ann_fits_kwd])
        else:
            name = image.get('name', tag)

        tag = image.get('tag', tag)
        return (name, tag)

    def transform_image(self, image):
        """Prepare ``image`` to be plotted in the right place according to
        the reference image WCS.  A new image is returned.

        This method is typically called internally.
        """
        name, tag = self._get_name_tag(image)

        data_np = image._get_data()
        if 0 in data_np.shape:
            self.logger.info("Skipping image with zero length axis")
            return

        ht, wd = data_np.shape

        # If caller asked us to match background of pieces then
        # fix up this data
        if self.t_['match_bg']:
            bg = iqcalc.get_median(data_np)
            bg_inc = self.bg_ref - bg
            data_np = data_np + bg_inc

        # Calculate sky position at the center of the piece
        ctr_x, ctr_y = trcalc.get_center(data_np)
        ra, dec = image.pixtoradec(ctr_x, ctr_y, coords='data')
        self.image_list.append((name, tag, ra, dec))

        # Get rotation and scale of piece
        header = image.get_header()
        ((xrot, yrot),
         (cdelt1, cdelt2)) = wcs.get_xy_rotation_and_scale(header)
        self.logger.debug("image(%s) xrot=%f yrot=%f cdelt1=%f "
                          "cdelt2=%f" % (name, xrot, yrot, cdelt1, cdelt2))

        # scale if necessary to scale of reference image
        if (not np.isclose(math.fabs(cdelt1), self.scale_x) or
            not np.isclose(math.fabs(cdelt2), self.scale_y)):
            nscale_x = math.fabs(cdelt1) / self.scale_x
            nscale_y = math.fabs(cdelt2) / self.scale_y
            self.logger.debug("scaling piece by x(%f), y(%f)" % (
                nscale_x, nscale_y))
            data_np, (ascale_x, ascale_y) = trcalc.get_scaled_cutout_basic(
                #data_np, 0, 0, wd - 1, ht - 1, nscale_x, nscale_y,
                data_np, 0, 0, wd, ht, nscale_x, nscale_y,
                logger=self.logger)

        method = self.t_['collage_method']

        if method == 'simple':
            self.logger.debug("plotting by rotating/flipping image by WCS")
            # CASE 1: simple rotation and flips
            # Rotate piece into our orientation, according to wcs
            rot_dx, rot_dy = xrot - self.xrot_ref, yrot - self.yrot_ref

            flip_x = False
            flip_y = False

            # Optomization for 180 rotations
            if (np.isclose(math.fabs(rot_dx), 180.0) or
                np.isclose(math.fabs(rot_dy), 180.0)):
                rotdata = trcalc.transform(data_np,
                                           flip_x=True, flip_y=True)
                rot_dx = 0.0
                rot_dy = 0.0
            else:
                rotdata = data_np

            # Finish with any necessary rotation of piece
            ignore_alpha = False
            if not np.isclose(rot_dy, 0.0):
                rot_deg = rot_dy
                minv, maxv = trcalc.get_minmax_dtype(rotdata.dtype)
                rotdata = trcalc.add_alpha(rotdata, alpha=maxv)
                self.logger.debug("rotating %s by %f deg" % (name, rot_deg))
                rotdata = trcalc.rotate(rotdata, rot_deg,
                                        #rotctr_x=ctr_x, rotctr_y=ctr_y,
                                        logger=self.logger, pad=0)
                ignore_alpha = True

            # Flip X due to negative CDELT1
            if np.sign(cdelt1) != np.sign(self.cdelt1_ref):
                flip_x = True

            # Flip Y due to negative CDELT2
            if np.sign(cdelt2) != np.sign(self.cdelt2_ref):
                flip_y = True

            if flip_x or flip_y:
                rotdata = trcalc.transform(rotdata,
                                           flip_x=flip_x, flip_y=flip_y)

            # new wrapper for transformed image
            metadata = dict(header=header, ignore_alpha=ignore_alpha)
            new_image = AstroImage.AstroImage(data_np=rotdata, metadata=metadata)

            # Get size and data of new image
            ht, wd = rotdata.shape[:2]
            ctr_x, ctr_y = trcalc.get_center(rotdata)

            # Find location of image piece (center) in our array
            x0, y0 = self.ref_image.radectopix(ra, dec, coords='data')

            #x0, y0 = int(np.round(x0)), int(np.round(y0))
            self.logger.debug("Fitting image '%s' into mosaic at %f,%f" % (
                name, x0, y0))

            # update limits
            xlo, xhi = x0 - ctr_x, x0 + ctr_x
            ylo, yhi = y0 - ctr_y, y0 + ctr_y

        elif method == 'warp':
            # Need to convert to float for this type
            data_np = data_np.astype(np.float32)

            self.logger.debug("plotting by warping image according to WCS")
            # CASE 2: user wants precise transformation of image using WCS
            dst, old_pts, coords, new_pts, dst_pts = warp_image(data_np,
                                                                image.wcs,
                                                                self.ref_image.wcs)

            # new wrapper for transformed image
            metadata = dict(header=header, ignore_alpha=True)
            new_image = AstroImage.AstroImage(data_np=dst, metadata=metadata)

            # find x, y at which to plot image
            xlo, ylo = new_pts[0] - dst_pts[0]
            self.logger.debug("Fitting image '%s' into mosaic at %f,%f" % (
                name, xlo, ylo))

            new_ht, new_wd = dst.shape[:2]
            xhi, yhi = xlo + new_wd, ylo + new_ht

        else:
            raise ValueError(f"don't understand mosaic method '{method}'")

        new_image.set(xpos=xlo, ypos=ylo, name=name, tag=tag)

        # calculate new limits of canvas
        _xlo, _ylo, = self.limits[0]
        _xhi, _yhi, = self.limits[1]
        _xlo, _ylo = min(_xlo, xlo), min(_ylo, ylo)
        _xhi, _yhi = max(_xhi, xhi), max(_yhi, yhi)
        self.limits = ((_xlo, _ylo), (_xhi, _yhi))

        return new_image

    def annotate_images(self, canvas):
        tagpfx = self.t_['ann_tag_pfx']
        tags = canvas.get_tags_by_tag_pfx(tagpfx)
        canvas.delete_objects_by_tag(tags, redraw=False)

        if self.t_['annotate_images']:
            dc = canvas.get_draw_classes()
            for name, tag, ra, dec in self.image_list:
                x, y = self.ref_image.radectopix(ra, dec)
                text = dc.Text(x, y, name,
                               color=self.t_['annotate_color'],
                               fontsize=self.t_['annotate_fontsize'],
                               fontscale=True)
                tag = tagpfx + tag
                canvas.add(text, tag=tag, redraw=False)

        canvas.update_canvas(whence=3)

    def plot_image(self, canvas, image):
        """Plot a new image created by ``transform_image()`` on ``canvas``.

        This is typically called internally.
        """
        dc = canvas.get_draw_classes()
        xpos, ypos, name, tag = image.get_list('xpos', 'ypos',
                                               'name', 'tag')
        img = dc.NormImage(xpos, ypos, image)
        img.is_data = True
        canvas.add(img, tag=tag, redraw=False)

    def reset(self):
        """Prepare for a new mosaic.
        The next call to ```mosaic`` will create a new mosaic.
        """
        self.ref_image = None
        self.ingest_count = 0
        self.total_images = 0
        self.image_list = []

    def ingest_one(self, canvas, image):
        """Plot ``image`` in the right place on the ``canvas``.

        This is typically called internally.
        """
        new_image = self.transform_image(image)

        self.plot_image(canvas, new_image)

        self.make_callback('progress', 'fitting',
                           float(self.ingest_count) / self.total_images)

    def mosaic(self, viewer, images, canvas=None, ev_intr=None):
        """Plot a mosaic of ``images`` in ``viewer`` on ``canvas``.
        If ``canvas`` is `None` the viewer's default canvas is used.
        """
        images = list(images)    # because we might pop(0)
        num_images = len(images)
        if num_images == 0:
            return
        self.total_images += num_images

        self.make_callback('progress', 'fitting', 0.0)
        t1 = time.time()

        if canvas is None:
            canvas = viewer.get_canvas()

        with viewer.suppress_redraw:
            # If there is no current mosaic then prepare a new one
            if self.ref_image is None:
                ref_image = images.pop(0)
                name, tag = self._get_name_tag(ref_image)
                self.prepare_mosaic(ref_image)

                # TODO: delete only items we may have added
                canvas.delete_all_objects(redraw=False)
                # first image is loaded in the usual way
                viewer.set_image(ref_image)
                self.limits = viewer.get_limits()

                # save position of reference image for annotation
                name, tag = self._get_name_tag(ref_image)
                wd, ht = ref_image.get_size()
                ctr_x, ctr_y = wd * 0.5, ht * 0.5
                ctr_ra, ctr_dec = ref_image.pixtoradec(ctr_x, ctr_y)
                self.image_list.append((name, tag, ctr_ra, ctr_dec))

            self.logger.info("fitting tiles...")

            for image in images:
                time.sleep(0)
                if ev_intr is not None and ev_intr.is_set():
                    raise Exception("interrupted by user")
                self.ingest_one(canvas, image)

            self.logger.info("finishing...")
            self.annotate_images(canvas)
            self.make_callback('progress', 'finishing', 0.0)

            viewer.set_limits(self.limits)
            if self.t_['center_image']:
                viewer.center_image()
            canvas.update_canvas(whence=0)

        self.process_elapsed = time.time() - t1
        self.logger.info("collage done. process=%.4f (sec)" % (
            self.process_elapsed))

        self.make_callback('finished', self.process_elapsed)
