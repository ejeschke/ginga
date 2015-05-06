#! /usr/bin/env python
#
# mosaic.py -- Example of quick and dirty mosaicing of FITS images
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Usage:
   $ ./mosaic.py -o output.fits input1.fits input2.fits ... inputN.fits
"""
from __future__ import print_function
import sys, os
import math

import numpy

from ginga import AstroImage
from ginga.util import wcs, io_fits, dp
from ginga.misc import log


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
        image0 = AstroImage.AstroImage(logger=logger)
        image0.load_file(filepath)
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

    cdbase = [numpy.sign(cdelt1), numpy.sign(cdelt2)]
    img_mosaic = dp.create_blank_image(ra_deg, dec_deg,
                                       fov_deg, px_scale, rot_deg,
                                       cdbase=cdbase,
                                       logger=logger)
    header = img_mosaic.get_header()
    (rot, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header)
    logger.debug("mosaic rot=%f cdelt1=%f cdelt2=%f" % (rot, cdelt1, cdelt2))

    logger.debug("Processing '%s' ..." % (name))
    tup = img_mosaic.mosaic_inline([ image0 ],
                                   allow_expand=expand)
    logger.debug("placement %s" % (str(tup)))

    count = 1
    for item in itemlist[1:]:
        if isinstance(item, AstroImage.AstroImage):
            image = item
            name = image.get('name', 'image%d' % (count))
        else:
            # Create and load the image
            filepath = item
            logger.info("Reading file '%s' ..." % (filepath))
            image = AstroImage.AstroImage(logger=logger)
            image.load_file(filepath)

        logger.debug("Inlining '%s' ..." % (name))
        tup = img_mosaic.mosaic_inline([ image ])
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

    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))

    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--fov", dest="fov", metavar="DEG",
                      type='float',
                      help="Set output field of view")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type='int',
                      help="Set logging level to LEVEL")
    optprs.add_option("-o", "--outfile", dest="outfile", metavar="FILE",
                      help="Write mosaic output to FILE")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")

    (options, args) = optprs.parse_args(sys.argv[1:])

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
