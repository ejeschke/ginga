#! /usr/bin/env python
#
# fits2pdf.py -- Image a FITS file as a PDF.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
   $ ./fits2pdf.py <fitsfile> <output.pdf>
"""
import sys, os
import logging

from ginga.cairow.ImageViewCairo import ImageViewCairo
import cairo
from ginga import AstroImage


STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

point_in = 1/72.0
point_cm = 0.0352777778

def main(options, args):

    logger = logging.getLogger("example1")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(STD_FORMAT)
    stderrHdlr = logging.StreamHandler()
    stderrHdlr.setFormatter(fmt)
    logger.addHandler(stderrHdlr)

    fi = ImageViewCairo(logger)
    fi.configure(500, 1000)

    # Load fits file
    filepath = args[0]
    image = AstroImage.AstroImage(logger=logger)
    image.load_file(filepath)

    # Make any adjustments to the image that we want
    fi.set_bg(1.0, 1.0, 1.0)
    fi.set_image(image)
    fi.auto_levels()
    fi.zoom_fit()
    fi.center_image()

    ht_pts = 11.0 / point_in
    wd_pts = 8.5 / point_in
    off_x, off_y = 0, 0
    
    outfilepath = args[1]
    out_f = open(outfilepath, 'w')
    surface = cairo.PDFSurface(out_f, wd_pts, ht_pts)
    # set pixels per inch
    surface.set_fallback_resolution(300, 300)
    surface.set_device_offset(off_x, off_y)
    try:
        fi.save_image_as_surface(surface)
        surface.show_page()
        surface.flush()
        surface.finish()
    finally:
        out_f.close()

    
if __name__ == '__main__':
    main(None, sys.argv[1:])
    
# END
