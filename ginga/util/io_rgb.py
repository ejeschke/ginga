#
# io_rgb.py -- RGB image file handling.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import time
import mimetypes
from io import BytesIO

import numpy as np

from ginga.BaseImage import Header, ImageError
from ginga.util import iohelper, rgb_cms

try:
    # do we have opencv available?
    import cv2
    have_opencv = True
except ImportError:
    have_opencv = False

try:
    # do we have Python Imaging Library available?
    import PIL.Image as PILimage
    from PIL.ExifTags import TAGS
    have_pil = True
except ImportError:
    have_pil = False

have_pilutil = False
try:
    from scipy.misc import imresize, imsave
    have_pilutil = True
except ImportError:
    pass

# piexif library for getting metadata, in the case that we don't have PIL
try:
    import piexif
    have_exif = True
except ImportError:
    have_exif = False

# For testing...
#have_pilutil = False
#have_pil = False
#have_cms = False
#have_exif = False
#have_opencv = False


class RGBFileHandler(object):

    def __init__(self, logger):
        self.logger = logger

        self.clr_mgr = rgb_cms.ColorManager(self.logger)

    def load_file(self, filespec, dstobj=None, **kwargs):
        res = iohelper.get_fileinfo(filespec)
        if len(res) != 1:
            raise NotImplementedError('Wildcard in extension not supported')
        info = res[0]
        if not info.ondisk:
            raise ValueError("File does not appear to be on disk: %s" % (
                info.url))

        filepath = info.filepath
        if dstobj is None:
            # Put here to avoid circular import
            from ginga.RGBImage import RGBImage
            dstobj = RGBImage(logger=self.logger)

        header = Header()
        metadata = {'header': header, 'path': filepath}

        data_np = self._imload(filepath, header)

        # TODO: set up the channel order correctly
        dstobj.set_data(data_np, metadata=metadata)

        if dstobj.name is not None:
            dstobj.set(name=dstobj.name)
        return dstobj

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

        if have_opencv:
            # First choice is OpenCv, because it supports high-bit depth
            # multiband images
            means = 'opencv'
            # funky indexing at the end is because opencv returns BGR
            # images, whereas PIL and others return RGB
            data_np = cv2.imread(filepath,
                                 cv2.IMREAD_ANYDEPTH +
                                 cv2.IMREAD_ANYCOLOR)[..., :: -1]

            # OpenCv doesn't "do" image metadata, so we punt to piexif
            # library (if installed)
            self.piexif_getexif(filepath, kwds)

            # OpenCv added a feature to do auto-orientation when loading
            # (see https://github.com/opencv/opencv/issues/4344)
            # So reset these values to prevent auto-orientation from
            # happening later
            kwds['Orientation'] = 1
            kwds['Image Orientation'] = 1

            # convert to working color profile, if can
            if self.clr_mgr.can_profile():
                data_np = self.clr_mgr.profile_to_working_numpy(data_np, kwds)

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

                elif have_exif:
                    self.piexif_getexif(image.info["exif"], kwds)

                else:
                    self.logger.warning("Please install 'piexif' module to get image metadata")

            except Exception as e:
                self.logger.warning("Failed to get image metadata: %s" % (str(e)))

            # convert to working color profile, if can
            if self.clr_mgr.can_profile():
                image = self.clr_mgr.profile_to_working_pil(image, kwds)

            # convert from PIL to numpy
            data_np = np.array(image)

        elif (typ == 'image') and (subtyp in ('x-portable-pixmap',
                                              'x-portable-greymap')):
            # Special opener for PPM files, preserves high bit depth
            means = 'built-in'
            data_np = open_ppm(filepath)

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
            raise Exception("Install piexif to use this method")

        try:
            info = piexif.load(filepath)
            buf = info['thumbnail']

        except Exception as e:
            return None

        image = PILimage.open(BytesIO(buf))
        data_np = np.array(image)
        return data_np

    def piexif_getexif(self, filepath, kwds):
        if have_exif:
            try:
                info = piexif.load(filepath)
                if info is not None:
                    # TODO: is there a more efficient way to do this than
                    # iterating in python?
                    for ifd in ["0th", "Exif", "GPS", "Interop", "1st"]:
                        if ifd in info:
                            for tag, value in info[ifd].items():
                                kwd = piexif.TAGS[ifd][tag].get('name', tag)
                                kwds[kwd] = value

            except Exception as e:
                self.logger.warning("Failed to get image metadata: %s" % (str(e)))

        else:
            self.logger.warning("Please install 'piexif' module to get image metadata")

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
    infile = open(filepath, 'rb')
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
    width, height = [int(x) for x in header.split()]
    header = infile.readline()

    # Get unit size
    maxval = int(header)
    if maxval <= 255:
        dtype = np.uint8
    elif maxval <= 65535:
        dtype = np.uint16
    #print width, height, maxval

    # read image
    if depth > 1:
        arr = np.fromfile(infile, dtype=dtype).reshape((height, width, depth))
    else:
        arr = np.fromfile(infile, dtype=dtype).reshape((height, width))

    if sys.byteorder == 'little':
        arr = arr.byteswap()
    return arr


def get_rgbloader(kind=None, logger=None):
    return RGBFileHandler(logger)

# END
