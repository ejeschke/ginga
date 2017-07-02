#
# io_rgb.py -- RGB image file handling.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, time
import numpy
import mimetypes
from io import BytesIO

from ginga.util import iohelper, rgb_cms
from ginga.util.six.moves import map, zip

try:
    # do we have Python Imaging Library available?
    import PIL.Image as PILimage
    from PIL.ExifTags import TAGS
    have_pil = True
except ImportError:
    have_pil = False

have_pilutil = False
try:
    from scipy.misc import imresize, imsave, toimage, fromimage
    have_pilutil = True
except ImportError:
    pass

# EXIF library for getting metadata, in the case that we don't have PIL
try:
    import EXIF
    have_exif = True
except ImportError:
    have_exif = False

# For testing...
#have_pilutil = False
#have_pil = False
#have_cms = False
#have_exif = False


class RGBFileHandler(object):

    def __init__(self, logger):
        self.logger = logger

        self.clr_mgr = rgb_cms.ColorManager(self.logger)

    def load_file(self, filespec, header):
        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise ValueError("File does not appear to be on disk: %s" % (
                info.url))

        filepath = info.filepath
        return self._imload(filepath, header)

    def save_file_as(self, filepath, data_np, header):
        if not have_pil:
            raise ImageError("Install PIL to be able to save images")

        # TODO: save keyword metadata!
        imsave(filepath, data_np)

    def _imload(self, filepath, kwds):
        """Load an image file, guessing the format, and return a numpy
        array containing an RGB image.  If EXIF keywords can be read
        they are returned in the dict _kwds_.
        """
        start_time = time.time()
        typ, enc = mimetypes.guess_type(filepath)
        if not typ:
            typ = 'image/jpeg'
        typ, subtyp = typ.split('/')
        self.logger.debug("MIME type is %s/%s" % (typ, subtyp))

        if (typ == 'image') and (subtyp in ('x-portable-pixmap',
                                            'x-portable-greymap')):
            # Special opener for PPM files, preserves high bit depth
            means = 'built-in'
            data_np = open_ppm(filepath)

        elif have_pil:
            means = 'PIL'
            image = PILimage.open(filepath)

            try:
                if hasattr(image, '_getexif'):
                    info = image._getexif()
                    if info is not None:
                        for tag, value in info.items():
                            kwd = TAGS.get(tag, tag)
                            kwds[kwd] = value

            except Exception as e:
                self.logger.warning("Failed to get image metadata: %s" % (str(e)))

            # convert to working color profile, if can
            if self.clr_mgr.can_profile():
                image = self.clr_mgr.profile_to_working_pil(image, kwds)

            # convert from PIL to numpy
            data_np = numpy.array(image)

        else:
            raise ImageError("No way to load image format '%s/%s'" % (
                typ, subtyp))

        end_time = time.time()
        self.logger.debug("loading (%s) time %.4f sec" % (
            means, end_time - start_time))
        return data_np

    def imload(self, filepath, kwds):
        return self._imload(filepath, kwds)

    def get_thumb(self, filepath):
        if not have_pil:
            raise Exception("Install PIL to use this method")
        if not have_exif:
            raise Exception("Install EXIF to use this method")

        with open(filepath, 'rb') as in_f:
            try:
                d = EXIF.process_file(in_f)
            except Exception as e:
                return None
        if 'JPEGThumbnail' in d:
            buf = d['JPEGThumbnail']
        # TODO: other possible encodings?
        else:
            return None

        image = PILimage.open(BytesIO.BytesIO(buf))
        data_np = numpy.array(image)
        return data_np

    def get_buffer(self, data_np, header, format, output=None):
        """Get image as a buffer in (format).
        Format should be 'jpeg', 'png', etc.
        """
        if not have_pil:
            raise Exception("Install PIL to use this method")
        image = PILimage.fromarray(data_np)
        buf = output
        if buf is None:
            buf = BytesIO()
        image.save(buf, format)
        return buf

    def imresize(self, data, new_wd, new_ht, method='bilinear'):
        """Scale an image in numpy array _data_ to the specified width and
        height.  A smooth scaling is preferred.
        """
        old_ht, old_wd = data.shape[:2]
        start_time = time.time()

        if have_pilutil:
            means = 'PIL'
            zoom_x = float(new_wd) / float(old_wd)
            zoom_y = float(new_ht) / float(old_ht)
            if (old_wd >= new_wd) or (old_ht >= new_ht):
                # data size is bigger, skip pixels
                zoom = max(zoom_x, zoom_y)
            else:
                zoom = min(zoom_x, zoom_y)

            newdata = imresize(data, zoom, interp=method)

        else:
            raise ImageError("No way to scale image smoothly")

        end_time = time.time()
        self.logger.debug("scaling (%s) time %.4f sec" % (
            means, end_time - start_time))

        return newdata


# UTILITY FUNCTIONS

def open_ppm(filepath):
    infile = open(filepath,'rb')
    # Get type: PPM or PGM
    header = infile.readline()
    ptype = header.strip().upper()
    if ptype == b'P5':
        depth = 1
    elif ptype == b'P6':
        depth = 3
    #print header

    # Get image dimensions
    header = infile.readline().strip()
    while header.startswith(b'#') or len(header) == 0:
        header = infile.readline().strip()

    #print(header)
    width, height = tuple(map(int, header.split()))
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
