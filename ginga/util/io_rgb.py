#
# io_rgb.py -- RGB image file handling.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, time
import os, glob
import numpy
import mimetypes
import hashlib
from io import BytesIO

from ginga.util import paths
from ginga.util.six.moves import map, zip

try:
    # do we have Python Imaging Library available?
    import PIL.Image as PILimage
    from PIL.ExifTags import TAGS
    have_pil = True
except ImportError:
    have_pil = False

# We only need one of { have_pilutil, have_qtimage }, but both have
# their strengths
have_pilutil = False
have_qtimage = False
try:
    from scipy.misc import imresize, imsave, toimage, fromimage
    have_pilutil = True
except ImportError:
    pass

# Qt can be used as a replacement for PIL
if not have_pilutil:
    try:
        from ginga.qtw.QtHelp import QImage, QColor, QtCore
        have_qtimage = True
    except ImportError as e:
        pass

# EXIF library for getting metadata, in the case that we don't have PIL
try:
    import EXIF
    have_exif = True
except ImportError:
    have_exif = False

# How about color management (ICC profile) support?
try:
    import PIL.ImageCms as ImageCms
    have_cms = True
except ImportError:
    have_cms = False

# For testing...
#have_qtimage = False
#have_pilutil = False
#have_pil = False
#have_cms = False


class RGBFileHandler(object):

    def __init__(self, logger):
        self.logger = logger

    def load_file(self, filepath, header):
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
            # PIL seems to be the faster loader than QImage, and can
            # return EXIF info, where QImage will not.
            means = 'PIL'
            image = PILimage.open(filepath)

            try:
                info = image._getexif()
                for tag, value in info.items():
                    kwd = TAGS.get(tag, tag)
                    kwds[kwd] = value

            except Exception as e:
                self.logger.warn("Failed to get image metadata: %s" % (str(e)))

            # If we have a working color profile then handle any embedded
            # profile or color space information, if possible
            if have_cms and os.path.exists(profile['working']):
                # Assume sRGB image, unless we learn to the contrary
                in_profile = 'sRGB'
                try:
                    if 'icc_profile' in image.info:
                        self.logger.debug("image has embedded color profile")
                        buf_profile = image.info['icc_profile']
                        # Write out embedded profile (if needed)
                        prof_md5 = hashlib.md5(buf_profile).hexdigest()
                        in_profile = "/tmp/_image_%d_%s.icc" % (
                            os.getpid(), prof_md5)
                        if not os.path.exists(in_profile):
                            with open(in_profile, 'w') as icc_f:
                                icc_f.write(buf_profile)

                    # see if there is any EXIF tag about the colorspace
                    elif 'ColorSpace' in kwds:
                        csp = kwds['ColorSpace']
                        iop = kwds.get('InteroperabilityIndex', None)
                        if (csp == 0x2) or (csp == 0xffff):
                            # NOTE: 0xffff is really "undefined" and should be
                            # combined with a test of EXIF tag 0x0001
                            # ('InteropIndex') == 'R03', but PIL _getexif()
                            # does not return the InteropIndex
                            in_profile = 'AdobeRGB'
                            self.logger.debug("hmm..this looks like an AdobeRGB image")
                        elif csp == 0x1:
                            self.logger.debug("hmm..this looks like a sRGB image")
                            in_profile = 'sRGB'
                        else:
                            self.logger.debug("no color space metadata, assuming this is an sRGB image")

                    # if we have a valid profile, try the conversion
                    tr_key = (in_profile, 'working', rendering_intent)
                    if tr_key in icc_transform:
                        # We have am in-core transform already for this (faster)
                        image = convert_profile_pil_transform(image, icc_transform[tr_key],
                                                              inPlace=True)
                    else:
                        # Convert using profiles on disk (slower)
                        if in_profile in profile:
                            in_profile = profile[in_profile]
                        image = convert_profile_pil(image, in_profile,
                                                    profile['working'],
                                                    rendering_intent)
                    self.logger.info("converted from profile (%s) to profile (%s)" % (
                        in_profile, profile['working']))
                except Exception as e:
                    self.logger.error("Error converting from embedded color profile: %s" % (str(e)))
                    self.logger.warn("Leaving image unprofiled.")

            data_np = numpy.array(image)

        elif have_qtimage:
            # QImage doesn't give EXIF info, so use 3rd-party lib if available
            if have_exif:
                with open(filepath, 'rb') as in_f:
                    d = EXIF.process_file(in_f)
                kwds.update(d)

            means = 'QImage'
            qimage = QImage()
            qimage.load(filepath)
            data_np = qimage2numpy(qimage)

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
        contents = buf.getvalue()
        if output is None:
            buf.close()
        return contents

    def imresize(self, data, new_wd, new_ht, method='bilinear'):
        """Scale an image in numpy array _data_ to the specified width and
        height.  A smooth scaling is preferred.
        """
        old_ht, old_wd = data.shape[:2]
        start_time = time.time()

        if have_qtimage:
            # QImage method is slightly faster and gives a smoother looking
            # result than PIL
            means = 'QImage'
            qimage = numpy2qimage(data)
            if (old_wd != new_wd) or (old_ht != new_ht):
                # NOTE: there is a strange bug in qimage.scaled if the new
                # dimensions are exactly the same--so we check and only
                # scale if there is some difference
                qimage = qimage.scaled(new_wd, new_ht,
                                   transformMode=QtCore.Qt.SmoothTransformation)
                newdata = qimage2numpy(qimage)
            else:
                newdata = data

        elif have_pilutil:
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


# --- Credit ---
#   the following function set by Hans Meine was found here:
#  http://kogs-www.informatik.uni-hamburg.de/~meine/software/vigraqt/qimage2ndarray.py
#
# see also a newer version at
#   http://kogs-www.informatik.uni-hamburg.de/~meine/software/qimage2ndarray/
#
def qimage2numpy(qimage):
    """Convert QImage to numpy.ndarray."""
    #print "FORMAT IS %s" % str(qimage.format())
    result_shape = (qimage.height(), qimage.width())
    temp_shape = (qimage.height(),
                  qimage.bytesPerLine() * 8 / qimage.depth())
    if qimage.format() in (QImage.Format_ARGB32_Premultiplied,
                              QImage.Format_ARGB32,
                              QImage.Format_RGB32):
        dtype = numpy.uint8
        result_shape += (4, )
        temp_shape += (4, )
    else:
        raise ValueError("qimage2numpy only supports 32bit and 8bit images")

    # FIXME: raise error if alignment does not match
    buf = qimage.bits()
    if hasattr(buf, 'asstring'):
        # Qt4
        buf = bytes(buf.asstring(qimage.numBytes()))
    else:
        # PySide
        buf = bytes(buf)
    result = numpy.frombuffer(buf, dtype).reshape(temp_shape)
    if result_shape != temp_shape:
        result = result[:,:result_shape[1]]

    # QImage loads the image as BGRA, we want RGB
    #res = numpy.dstack((result[:, :, 2], result[:, :, 1], result[:, :, 0]))
    res = numpy.empty((qimage.height(), qimage.width(), 3))
    res[:, :, 0] = result[:, :, 2]
    res[:, :, 1] = result[:, :, 1]
    res[:, :, 2] = result[:, :, 0]
    return res

def numpy2qimage(array):
    if numpy.ndim(array) == 2:
        return gray2qimage(array)
    elif numpy.ndim(array) == 3:
        return rgb2qimage(array)
    raise ValueError("can only convert 2D or 3D arrays")

def gray2qimage(gray):
    """Convert the 2D numpy array `gray` into a 8-bit QImage with a gray
    colormap.  The first dimension represents the vertical image axis.

    ATTENTION: This QImage carries an attribute `ndarray` with a
    reference to the underlying numpy array that holds the data. On
    Windows, the conversion into a QPixmap does not copy the data, so
    that you have to take care that the QImage does not get garbage
    collected (otherwise PyQt will throw away the wrapper, effectively
    freeing the underlying memory - boom!)."""
    if len(gray.shape) != 2:
        raise ValueError("gray2QImage can only convert 2D arrays")

    h, w = gray.shape
    bgra = numpy.empty((h, w, 4), numpy.uint8, 'C')
    bgra[...,0] = gray
    bgra[...,1] = gray
    bgra[...,2] = gray
    bgra[...,3].fill(255)
    fmt = QImage.Format_RGB32
    result = QImage(bgra.data, w, h, fmt)
    result.ndarray = bgra
    return result

def rgb2qimage(rgb):
    """Convert the 3D numpy array `rgb` into a 32-bit QImage.  `rgb` must
    have three dimensions with the vertical, horizontal and RGB image axes.

    ATTENTION: This QImage carries an attribute `ndarray` with a
    reference to the underlying numpy array that holds the data. On
    Windows, the conversion into a QPixmap does not copy the data, so
    that you have to take care that the QImage does not get garbage
    collected (otherwise PyQt will throw away the wrapper, effectively
    freeing the underlying memory - boom!)."""
    if len(rgb.shape) != 3:
        raise ValueError("rgb2QImage can only convert 3D arrays")
    if rgb.shape[2] not in (3, 4):
        raise ValueError("rgb2QImage can expects the last dimension to contain exactly three (R,G,B) or four (R,G,B,A) channels")

    h, w, channels = rgb.shape

    # Qt expects 32bit BGRA data for color images:
    bgra = numpy.empty((h, w, 4), numpy.uint8, 'C')
    bgra[...,0] = rgb[...,2]
    bgra[...,1] = rgb[...,1]
    bgra[...,2] = rgb[...,0]
    if rgb.shape[2] == 3:
        bgra[...,3].fill(255)
        fmt = QImage.Format_RGB32
    else:
        bgra[...,3] = rgb[...,3]
        fmt = QImage.Format_ARGB32

    result = QImage(bgra.data, w, h, fmt)
    result.ndarray = bgra
    return result

# --- end QImage to numpy conversion functions ---

# --- Color Management conversion functions ---

def convert_profile_pil(image_pil, inprof_path, outprof_path, intent_name,
                        inPlace=False):
    if not have_cms:
        return image_pil

    image_out = ImageCms.profileToProfile(image_pil, inprof_path,
                                          outprof_path,
                                          renderingIntent=intents[intent_name],
                                          outputMode='RGB', inPlace=inPlace,
                                          flags=0)
    if inPlace:
        return image_pil
    return image_out

def convert_profile_pil_transform(image_pil, transform, inPlace=False):
    if not have_cms:
        return image_pil

    image_out = ImageCms.applyTransform(image_pil, transform, inPlace)
    if inPlace:
        return image_pil
    return image_out

def convert_profile_numpy(image_np, inprof_path, outprof_path, intent_name):
    if (not have_pilutil) or (not have_cms):
        return image_np

    in_image_pil = toimage(image_np)
    out_image_pil = convert_profile_pil(in_image_pil,
                                        inprof_path, outprof_path, intent_name)
    image_out = fromimage(out_image_pil)
    return image_out

def convert_profile_numpy_transform(image_np, transform):
    if (not have_pilutil) or (not have_cms):
        return image_np

    in_image_pil = toimage(image_np)
    convert_profile_pil_transform(in_image_pil, transform, inPlace=True)
    image_out = fromimage(in_image_pil)
    return image_out

def get_transform_key(from_name, to_name, to_intent, proof_name,
                      proof_intent, flags):
    return (from_name, to_name, to_intent, proof_name, proof_intent,
            flags)

def get_transform(from_name, to_name, to_intent='perceptual',
                    proof_name=None, proof_intent=None,
                    use_black_pt=False):
    global icc_transform

    flags = 0
    if not (proof_name is None):
        flags |= ImageCms.SOFTPROOFING
    if use_black_pt:
        flags |= ImageCms.BLACKPOINTCOMPENSATION

    key = get_transform_key(from_name, to_name, to_intent, proof_name,
                            proof_intent, flags)

    try:
        output_transform = icc_transform[key]

    except KeyError:
        # try to build transform on the fly
        try:
            if not (proof_name is None):
                output_transform = ImageCms.buildProofTransform(
                    profile[from_name],
                    profile[to_name],
                    profile[proof_name],
                    'RGB', 'RGB',
                    renderingIntent=intents[to_intent],
                    proofRenderingIntent=intents[proof_intent],
                    flags=flags)
            else:
                output_transform = ImageCms.buildTransform(
                    profile[from_name],
                    profile[to_name],
                    'RGB', 'RGB',
                    renderingIntent=intents[to_intent],
                    flags=flags)

            icc_transform[key] = output_transform

        except Exception as e:
            raise Exception("Failed to build profile transform: %s" % (str(e)))

    return output_transform

def convert_profile_fromto(image_np, from_name, to_name,
                           to_intent='perceptual',
                           proof_name=None, proof_intent=None,
                           use_black_pt=False):

    try:
        output_transform = get_transform(from_name, to_name,
                                         to_intent=to_intent,
                                         proof_name=proof_name,
                                         proof_intent=proof_intent,
                                         use_black_pt=use_black_pt)

        out_np = convert_profile_numpy_transform(image_np, output_transform)
        return out_np

    except Exception as e:
        print(str(e))
        return image_np


def set_rendering_intent(intent):
    """
    Sets the color management attribute rendering intent.

    Parameters
    ----------
    intent: integer
      0: perceptual, 1: relative colorimetric, 2: saturation,
      3: absolute colorimetric
    """
    global rendering_intent
    rendering_intent = intent


basedir = paths.ginga_home

# Color Management configuration
profile = {}
rendering_intent = 'perceptual'
intents = dict(perceptual=0)

# Look up all the profiles the user has available
glob_pat = os.path.join(basedir, "profiles", "*.icc")
for path in glob.glob(glob_pat):
    dirname, filename = os.path.split(path)
    profname, ext = os.path.splitext(filename)
    profile[profname] = os.path.abspath(path)

# These are ones we are particularly interested in
for filename in ('working.icc', 'monitor.icc', 'sRGB.icc', 'AdobeRGB.icc'):
    profname, ext = os.path.splitext(filename)
    profile[profname] = os.path.join(basedir, "profiles", filename)

# Prepare common transforms
icc_transform = {}
# Build transforms for profile conversions for which we have profiles
if have_cms:

    intents = dict(absolute_colorimetric=ImageCms.INTENT_ABSOLUTE_COLORIMETRIC,
                   perceptual=ImageCms.INTENT_PERCEPTUAL,
                   relative_colorimetric=ImageCms.INTENT_RELATIVE_COLORIMETRIC,
                   saturation=ImageCms.INTENT_SATURATION)

    # # build input transforms
    # for inprof, outprof in [('sRGB', 'working'), ('AdobeRGB', 'working')]:
    #     for intent_name, intent_value in intents.items():
    #         if os.path.exists(profile[inprof]) and os.path.exists(profile[outprof]):
    #             get_transform(profile[inprof], profile[outprof])

def get_profiles():
    names = list(profile.keys())
    names.sort()
    return names

def get_intents():
    names = list(intents.keys())
    names.sort()
    return names

#END
