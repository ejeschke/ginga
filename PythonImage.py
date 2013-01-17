#
# PythonImage.py -- Abstraction of an generic data image.
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Sun Jan 13 22:53:48 HST 2013
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import numpy
import mimetypes
try:
    # do we have Python Imaging Library available?
    import PIL.Image as Image
    from PIL.ExifTags import TAGS
    have_pil = True
except ImportError:
    have_pil = False

try:
    import scipy.misc.pilutil as pilutil
    have_pilutil = True
except ImportError:
    have_pilutil = False

try:
    # How about color management (ICC profile) support?
    import ImageCms
    have_cms = True
except ImportError:
    have_cms = False

import Bunch
from BaseImage import BaseImage, ImageError

class PythonImage(BaseImage):

    def load_file(self, filepath):
        kwds = {}
        metadata = { 'exif': {} }        
        typ, enc = mimetypes.guess_type(filepath)
        if not typ:
            typ = 'image/jpeg'
        typ, subtyp = typ.split('/')
        self.logger.info("MIME type is %s/%s" % (typ, subtyp))
        if (typ == 'image') and (subtyp in ('x-portable-pixmap',
                                            'x-portable-greymap')):
            # Special opener for PPM files
            data_np = open_ppm(filepath)
                
        elif have_pil:
            image = Image.open(filepath)
            ## if have_cms:
            ##     image = ImageCms.profileToProfile(image, in_profile,
            ##                                       working_profile)
            data_np = numpy.array(image)

            try:
                info = image._getexif()
                for tag, value in info.items():
                    kwd = TAGS.get(tag, tag)
                    kwds[kwd] = value
            except Exception, e:
                self.logger.error("Failed to get image metadata: %s" % (
                    str(e)))
        else:
            raise Exception("No way to load image format '%s/%s'" % (
                typ, subtyp))
            
        self.set_data(data_np, metadata=metadata)
        self.set(exif=kwds)
        
    def copy(self, astype=None):
        other = PythonImage()
        self.transfer(other, astype=astype)
        return other
        
    def get_scaled_cutout_wdht(self, x1, y1, x2, y2, new_wd, new_ht,
                                  method='bicubic'):
        # calculate dimensions of NON-scaled cutout
        old_wd = x2 - x1 + 1
        old_ht = y2 - y1 + 1
        self.logger.debug("old=%dx%d new=%dx%d" % (
            old_wd, old_ht, new_wd, new_ht))

        data = self.get_data()
        newdata = data[y1:y2+1, x1:x2+1]

        zoom_x = float(new_wd) / float(old_wd)
        zoom_y = float(new_ht) / float(old_ht)
        if (old_wd >= new_wd) or (old_ht >= new_ht):
            # data size is bigger, skip pixels
            zoom = max(zoom_x, zoom_y)
        else:
            zoom = min(zoom_x, zoom_y)

        newdata = pilutil.imresize(newdata, zoom, interp=method)

        ht, wd = newdata.shape[:2]
        scale_x = float(wd) / old_wd
        scale_y = float(ht) / old_ht
        res = Bunch.Bunch(data=newdata, org_fac=1,
                          scale_x=scale_x, scale_y=scale_y)
        return res

    def get_scaled_cutout_pil(self, x1, y1, x2, y2, scale_x, scale_y,
                                  method='bicubic'):
        # calculate dimensions of NON-scaled cutout
        old_wd = x2 - x1 + 1
        old_ht = y2 - y1 + 1
        new_wd = int(round(scale_x * old_wd))
        new_ht = int(round(scale_y * old_ht))
        self.logger.debug("old=%dx%d new=%dx%d" % (
            old_wd, old_ht, new_wd, new_ht))

        data = self.get_data()
        newdata = data[y1:y2+1, x1:x2+1]

        zoom_x = float(new_wd) / float(old_wd)
        zoom_y = float(new_ht) / float(old_ht)
        if (old_wd >= new_wd) or (old_ht >= new_ht):
            # data size is bigger, skip pixels
            zoom = max(zoom_x, zoom_y)
        else:
            zoom = min(zoom_x, zoom_y)

        newdata = pilutil.imresize(newdata, zoom, interp=method)

        ht, wd = newdata.shape[:2]
        scale_x = float(wd) / old_wd
        scale_y = float(ht) / old_ht
        res = Bunch.Bunch(data=newdata, org_fac=1,
                          scale_x=scale_x, scale_y=scale_y)
        return res

    def get_scaled_cutout(self, x1, y1, x2, y2, scale_x, scale_y,
                          method='bicubic'):
        if method == 'basic':
            return self.get_scaled_cutout_basic(x1, y1, x2, y2,
                                                scale_x, scale_y)

        return self.get_scaled_cutout_pil(x1, y1, x2, y2,
                                          scale_x, scale_y,
                                          method=method)

def open_ppm(filepath):
    infile = open(filepath,'r')
    # Get type: PPM or PGM
    header = infile.readline()
    ptype = header.strip().upper()
    if ptype == 'P5':
        depth = 1
    elif ptype == 'P6':
        depth = 3
    #print header

    # Get image dimensions
    header = infile.readline().strip()
    while header.startswith('#') or len(header) == 0:
        header = infile.readline().strip()
        
    print header
    width, height = map(int, header.split())
    header = infile.readline()

    # Get unit size
    maxval = int(header)
    if maxval <= 255:
        dtype = numpy.uint8
    elif maxval <= 65535:
        dtype = numpy.uint16
    #print width, height, maxval

    # read image
    if depth > 1:
        arr = numpy.fromfile(infile, dtype=dtype).reshape((height, width,
                                                           depth))
    else:
        arr = numpy.fromfile(infile, dtype=dtype).reshape((height, width))
        
    if sys.byteorder == 'little':
        arr = arr.byteswap()
    return arr


#END
