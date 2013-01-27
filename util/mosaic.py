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
import sys, os
import logging

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
projectHome = os.path.join(moduleHome, '..')
sys.path.insert(0, projectHome)

import AstroImage

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

def mosaic(paths, logger, outfile=None):
    images = []
    for p in paths:
        image = AstroImage.AstroImage(logger=logger)
        image.load_file(p)
        images.append(image)

    mosaic = image.mosaic(images)

    if outfile:
        try:
            os.remove(outfile)
        except:
            pass
        logger.info("Writing mosaic file to %s ..." % (outfile))
        mosaic.write_fits(outfile)
        
        
def main(options, args):

    logger = logging.getLogger("mosaic")
    logger.setLevel(options.loglevel)
    fmt = logging.Formatter(STD_FORMAT)
    if options.logfile:
        fileHdlr  = logging.handlers.RotatingFileHandler(options.logfile)
        fileHdlr.setLevel(options.loglevel)
        fileHdlr.setFormatter(fmt)
        logger.addHandler(fileHdlr)

    if options.logstderr:
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setLevel(options.loglevel)
        stderrHdlr.setFormatter(fmt)
        logger.addHandler(stderrHdlr)

    if len(args) > 0:
        mosaic(args, logger, outfile=options.outfile)
        
    
if __name__ == "__main__":
   
    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))
    
    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type='int', default=logging.INFO,
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
