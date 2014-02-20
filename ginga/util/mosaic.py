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
import sys, os
import math
from collections import OrderedDict

import numpy

from ginga import AstroImage
from ginga.util import wcs, io_fits
from ginga.misc import log


def create_blank_image(ra_deg, dec_deg, fov_deg, px_scale, rot_deg,
                       cdbase=[1, 1], logger=None):

    # ra and dec in traditional format
    ra_txt = wcs.raDegToString(ra_deg, format='%02d:%02d:%06.3f')
    dec_txt = wcs.decDegToString(dec_deg, format='%s%02d:%02d:%05.2f')

    # Create a dummy sh image
    imagesize = int(round(fov_deg / px_scale))
    # round to an even size
    if imagesize % 2 != 0:
        imagesize += 1
    ## # round to an odd size
    ## if imagesize % 2 == 0:
    ##     imagesize += 1
    width = height = imagesize
    data = numpy.zeros((height, width), dtype=numpy.float32)

    crpix = float(imagesize // 2)
    header = OrderedDict((('SIMPLE', True),
                          ('BITPIX', -32),
                          ('EXTEND', True),
                          ('NAXIS', 2),
                          ('NAXIS1', imagesize),
                          ('NAXIS2', imagesize),
                          ('RA', ra_txt),
                          ('DEC', dec_txt),
                          ('EQUINOX', 2000.0),
                          ('OBJECT', 'MOSAIC'),
                          ('LONPOLE', 180.0),
                          ))

    # Add basic WCS keywords
    wcshdr = wcs.simple_wcs(crpix, crpix, ra_deg, dec_deg, px_scale,
                            rot_deg, cdbase=cdbase)
    header.update(wcshdr)

    # Create image container
    image = AstroImage.AstroImage(data, wcsclass=wcs.WCS,
                                  logger=logger)
    image.update_keywords(header)

    return image


def mosaic(logger, filelist, outfile=None, fov_deg=None):

    filepath = filelist[0]
    logger.info("Reading file '%s' ..." % (filepath))
    image0 = AstroImage.AstroImage(logger=logger)
    image0.load_file(filelist[0])

    ra_deg, dec_deg = image0.get_keywords_list('CRVAL1', 'CRVAL2')
    header = image0.get_header()
    (rot_deg, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header)
    logger.debug("image0 rot=%f cdelt1=%f cdelt2=%f" % (rot_deg,
                                                        cdelt1, cdelt2))

    px_scale = math.fabs(cdelt1)
    if fov_deg == None:
        # TODO: calculate fov!
        fov_deg = 1.0
        
    #cdbase = [numpy.sign(cdelt1), numpy.sign(cdelt2)]
    cdbase = [1, 1]
    img_mosaic = create_blank_image(ra_deg, dec_deg,
                                    fov_deg, px_scale, rot_deg,
                                    cdbase=cdbase,
                                    logger=logger)
    header = img_mosaic.get_header()
    (rot, cdelt1, cdelt2) = wcs.get_rotation_and_scale(header)
    logger.debug("mosaic rot=%f cdelt1=%f cdelt2=%f" % (rot, cdelt1, cdelt2))

    logger.debug("Processing '%s' ..." % (filepath))
    tup = img_mosaic.mosaic_inline([ image0 ])
    logger.debug("placement %s" % (str(tup)))

    for filepath in filelist[1:]:
        # Create and load the image
        logger.info("Reading file '%s' ..." % (filepath))
        image = AstroImage.AstroImage(logger=logger)
        image.load_file(filepath)

        logger.debug("Inlining '%s' ..." % (filepath))
        tup = img_mosaic.mosaic_inline([ image ])
        logger.debug("placement %s" % (str(tup)))

    if outfile:
        io_fits.use('astropy')
        logger.info("Writing output to '%s'..." % (outfile))
        try:
            os.remove(outfile)
        except OSError:
            pass
        img_mosaic.save_as_file(outfile)

    logger.info("Done.")
        
    
def main(options, args):

    logger = log.get_logger(name="mosaic", options=options)

    mosaic(logger, args, fov_deg=options.fov,
           outfile=options.outfile)
        

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

        print "%s profile:" % sys.argv[0]
        profile.run('main(options, args)')


    else:
        main(options, args)

# END
