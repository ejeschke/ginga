#! /usr/bin/env python
#
# mosaic.py -- Example of quick and dirty mosaicing of FITS images
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Usage:
   $ ./mosaic.py -o output.fits input1.fits input2.fits ... inputN.fits
"""

import os
import math
import time

import numpy as np

from ginga import AstroImage, trcalc
from ginga.util import wcs, loader, dp, iqcalc
from ginga.util import io_fits
from ginga.misc import log, Callback


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
        x0, y0 = int(np.round(x0)), int(np.round(y0))
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


def main(options, args):

    logger = log.get_logger(name="mosaic", options=options)

    img_mosaic = mosaic(logger, args, fov_deg=options.fov)

    if options.outfile:
        outfile = options.outfile
        io_fits.use('astropy')

        logger.info("Writing output to '%s'..." % (outfile))
        try:
            os.remove(outfile)
        except OSError:
            pass

        img_mosaic.save_as_file(outfile)


class CanvasMosaicer(Callback.Callbacks):

    def __init__(self, logger):
        super(CanvasMosaicer, self).__init__()

        self.logger = logger

        self.ingest_count = 0
        # holds processed images to be inserted into mosaic image
        self.total_images = 0

        # options
        self.annotate = False
        self.annotate_color = 'pink'
        self.annotate_fontsize = 10.0
        self.match_bg = False
        self.center_image = True

        # these are updated in prepare_mosaic() and represent measurements
        # on the reference image
        self.bg_ref = 0.0
        self.xrot_ref, self.yrot_ref = 0.0, 0.0
        self.cdelt1_ref, self.cdelt2_ref = 1.0, 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.limits = None
        self.ref_image = None

        for name in ['progress', 'finished']:
            self.enable_callback(name)

    def prepare_mosaic(self, ref_image):
        """Prepare a new (blank) mosaic image based on the pointing of
        the parameter image
        """
        self.ref_image = ref_image

        # if user requesting us to match backgrounds, then calculate
        # median of root image and save it
        if self.match_bg:
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

    def ingest_one(self, canvas, image):
        """prepare an image to be dropped in the right place in the canvas.
        """
        self.ingest_count += 1
        count = self.ingest_count
        name = image.get('name', 'image{}'.format(count))

        data_np = image._get_data()
        if 0 in data_np.shape:
            self.logger.info("Skipping image with zero length axis")
            return

        ht, wd = data_np.shape

        # If caller asked us to match background of pieces then
        # fix up this data
        if self.match_bg:
            bg = iqcalc.get_median(data_np)
            bg_inc = self.bg_ref - bg
            data_np = data_np + bg_inc

        # Calculate sky position at the center of the piece
        ctr_x, ctr_y = trcalc.get_center(data_np)
        ra, dec = image.pixtoradec(ctr_x, ctr_y, coords='data')

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

        # Merge piece as closely as possible into our array
        # Unfortunately we lose a little precision rounding to the
        # nearest pixel--can't be helped with this approach
        x0, y0 = int(np.round(x0)), int(np.round(y0))
        self.logger.debug("Fitting image '%s' into mosaic at %f,%f" % (
            name, x0, y0))

        # update limits
        xlo, xhi = x0 - ctr_x, x0 + ctr_x
        ylo, yhi = y0 - ctr_y, y0 + ctr_y

        new_image.set(xpos=xlo, ypos=ylo, name=name)

        _xlo, _ylo, = self.limits[0]
        _xhi, _yhi, = self.limits[1]
        _xlo, _ylo = min(_xlo, xlo), min(_ylo, ylo)
        _xhi, _yhi = max(_xhi, xhi), max(_yhi, yhi)
        self.limits = ((_xlo, _ylo), (_xhi, _yhi))

        self.plot_image(canvas, new_image)

        self.make_callback('progress', 'fitting',
                           float(count) / self.total_images)

    def plot_image(self, canvas, image):
        name = image.get('name', 'noname'),
        # TODO: figure out where/why name gets encased in a tuple
        name = name[0]

        dc = canvas.get_draw_classes()
        xpos, ypos = image.get_list('xpos', 'ypos')
        img = dc.NormImage(xpos, ypos, image)
        img.is_data = True
        canvas.add(img, redraw=False)

        if self.annotate:
            wd, ht = image.get_size()
            ## pts = [(xpos, ypos), (xpos + wd, ypos),
            ##        (xpos + wd, ypos + ht), (xpos, ypos + ht)]
            ## box = self.dc.Polygon(pts, color='pink')
            text = dc.Text(xpos + 10, ypos + ht * 0.5, name,
                           color=self.annotate_color,
                           fontsize=self.annotate_fontsize,
                           fontscale=True)
            canvas.add(text, redraw=False)

    def reset(self):
        self.ref_image = None

    def mosaic(self, viewer, images, canvas=None):
        self.total_images = len(images)
        self.ingest_count = 0
        if self.total_images == 0:
            return

        self.make_callback('progress', 'fitting', 0.0)
        t1 = time.time()

        if canvas is None:
            canvas = viewer.get_canvas()

        with viewer.suppress_redraw:
            # If there is no current mosaic then prepare a new one
            if self.ref_image is None:
                ref_image = images.pop(0)
                self.ingest_count += 1
                self.prepare_mosaic(ref_image)

                canvas.delete_all_objects(redraw=False)
                # first image is loaded in the usual way
                viewer.set_image(ref_image)
                self.limits = viewer.get_limits()

            self.logger.info("fitting tiles...")

            for image in images:
                self.ingest_one(canvas, image)
                pct = self.ingest_count / self.total_images
                self.make_callback('progress', 'fitting', pct)

            self.logger.info("finishing...")
            self.make_callback('progress', 'finishing', 0.0)

            viewer.set_limits(self.limits)
            if self.center_image:
                viewer.center_image()
            canvas.update_canvas(whence=0)

        self.process_elapsed = time.time() - t1
        self.logger.info("mosaic done. process=%.4f (sec)" % (
            self.process_elapsed))

        self.make_callback('finished', self.process_elapsed)
