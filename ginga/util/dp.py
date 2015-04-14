
# dp.py -- Data pipeline and reduction routines
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
import os

from collections import OrderedDict

from ginga import AstroImage
from ginga.util import wcs

# counter used to name anonymous images
prefixes = dict(dp=0)


def get_image_name(image, pfx='dp'):
    global prefixes
    name = image.get('name', None)
    if name is None:
        if not pfx in prefixes:
            prefixes[pfx] = 0
        name = 'dp%d' % (prefixes[pfx])
        prefixes[pfx] += 1
        image.set(name=name)
    return name


def make_image(data_np, oldimage, header, pfx='dp'):
    # Prepare a new image with the numpy array as data
    image = AstroImage.AstroImage()
    image.set_data(data_np)
    # Set the header to be the old image header updated
    # with items from the new header
    oldhdr = oldimage.get_header()
    oldhdr.update(header)
    image.update_keywords(oldhdr)
    # give the image a name
    get_image_name(image, pfx=pfx)
    return image


def create_blank_image(ra_deg, dec_deg, fov_deg, px_scale, rot_deg,
                       cdbase=[1, 1], logger=None, pfx='dp'):

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

    bytes_needed = numpy.dtype(numpy.float32).itemsize * height * width
    bytes_free = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    if bytes_needed >= bytes_free:
        raise MemoryError('{0} MB needed but {1} MB available'.format(
            bytes_needed * 1e-6, bytes_free * 1e-6))

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
    image = AstroImage.AstroImage(data, logger=logger)
    image.update_keywords(header)
    # give the image a name
    get_image_name(image, pfx=pfx)

    return image


def make_flat(imglist, bias=None):

    flats = [ image.get_data() for image in imglist ]
    flatarr = numpy.array(flats)
    # Take the median of the individual frames
    flat = numpy.median(flatarr, axis=0)

    # Normalize flat
    # mean or median?
    #norm = numpy.mean(flat.flat)
    norm = numpy.median(flat.flat)
    flat = flat / norm
    # no zero divisors
    flat[flat == 0.0] = 1.0

    img_flat = make_image(flat, imglist[0], {}, pfx='flat')
    return img_flat

def make_bias(imglist):

    biases = [ image.get_data() for image in imglist ]
    biasarr = numpy.array(biases)
    # Take the median of the individual frames
    bias = numpy.median(biasarr, axis=0)

    img_bias = make_image(bias, imglist[0], {}, pfx='bias')
    return img_bias


def add(image1, image2):
    data1_np = image1.get_data()
    data2_np = image2.get_data()

    result = data1_np + data2_np
    image = make_image(result, image1, {}, pfx='add')
    return image


def subtract(image1, image2):
    data1_np = image1.get_data()
    data2_np = image2.get_data()

    result = data1_np - data2_np
    image = make_image(result, image1, {}, pfx='sub')
    return image


def divide(image1, image2):
    data1_np = image1.get_data()
    data2_np = image2.get_data()

    result = data1_np / data2_np
    image = make_image(result, image1, {}, pfx='div')
    return image


# END
