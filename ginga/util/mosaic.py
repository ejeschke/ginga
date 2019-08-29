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

import sys
import os
import math

import numpy as np

from ginga import AstroImage, trcalc
from ginga.util import wcs, loader, dp, iqcalc
from ginga.util import io_fits
from ginga.misc import log


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
        x0, y0 = baseimage.radectopix(ra, dec)

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
                            CRPIX2=crpix2 + ny1_off)
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


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    usage = "usage: %prog [options] [args]"
    argprs = ArgumentParser(usage=usage)

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--fov", dest="fov", metavar="DEG",
                        type=float,
                        help="Set output field of view")
    argprs.add_argument("--log", dest="logfile", metavar="FILE",
                        help="Write logging output to FILE")
    argprs.add_argument("--loglevel", dest="loglevel", metavar="LEVEL",
                        type=int,
                        help="Set logging level to LEVEL")
    argprs.add_argument("-o", "--outfile", dest="outfile", metavar="FILE",
                        help="Write mosaic output to FILE")
    argprs.add_argument("--stderr", dest="logstderr", default=False,
                        action="store_true",
                        help="Copy logging also to stderr")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print("%s profile:" % sys.argv[0])
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
