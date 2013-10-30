#
# RGBImage.py -- Abstraction of an generic data image.
#
# Eric Jeschke (eric@naoj.org) 
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, time
import numpy
import mimetypes
import os
import hashlib
import StringIO

try:
    # do we have Python Imaging Library available?
    import PIL.Image as PILimage
    from PIL.ExifTags import TAGS
    have_pil = True
except ImportError:
    have_pil = False

# We only need one of { have_pilutil, have_qtimage }, but both have
# their strengths
try:
    from  scipy.misc import pilutil, imsave
    have_pilutil = True
except ImportError:
    have_pilutil = False

# Qt can be used as a replacement for PIL
try:
    from ginga.qtw.QtHelp import QtCore, QtGui
    QImage, QColor = QtGui.QImage, QtGui.QColor
    have_qtimage = True
except ImportError, e:
    have_qtimage = False

# How about color management (ICC profile) support?
try:
    import PIL.ImageCms as ImageCms
    have_cms = True
except ImportError:
    have_cms = False

# EXIF library for getting metadata, in the case that we don't have PIL
try:
    import EXIF
    have_exif = True
except ImportError:
    have_exif = False

# For testing...
#have_qtimage = False
#have_pilutil = False
#have_pil = False
#have_cms = False

from ginga.misc import Bunch
from ginga.BaseImage import BaseImage, ImageError, Header

try:
    basedir = os.environ['GINGA_HOME']
except KeyError:
    basedir = os.path.join(os.environ['HOME'], '.ginga')

# Color Management configuration
profile = {}
for filename in ('working.icc', 'monitor.icc', 'sRGB.icc', 'AdobeRGB.icc'):
    profname, ext = os.path.splitext(filename)
    profile[profname] = os.path.join(basedir, "profiles", filename)

rendering_intent = 0

# Prepare common transforms
transform = {}
# Build transforms for profile conversions for which we have profiles
if have_cms:
    rendering_intent = ImageCms.INTENT_PERCEPTUAL

    for inprof, outprof in [('sRGB', 'working'), ('AdobeRGB', 'working'), ('working', 'monitor')]:
        if os.path.exists(profile[inprof]) and os.path.exists(profile[outprof]):
            transform[(inprof, outprof)] = ImageCms.buildTransform(profile[inprof],
                                                                   profile[outprof],
                                                                   'RGB', 'RGB',
                                                                   renderingIntent=rendering_intent,
                                                                   flags=0)


class RGBImage(BaseImage):

    def load_file(self, filepath):
        kwds = Header()
        metadata = { 'exif': {}, 'path': filepath }

        data_np = self._imload(filepath, kwds)

        self.set_data(data_np, metadata=metadata)
        self.set(exif=kwds)

    def save_file_as(self, filepath):
        if not have_pil:
            raise ImageError("Install PIL to be able to save images")

        data = self.get_data()
        imsave(filepath, data)


    def copy(self, astype=None):
        other = RGBImage()
        self.transfer(other, astype=astype)
        return other

    def get_buffer(self, format, output=None):
        """Get image as a buffer in (format).
        Format should be 'jpeg', 'png', etc.
        """
        if not have_pil:
            raise Exception("Install PIL to use this method")
        image = PILimage.fromarray(self.get_data())
        buf = output
        if buf == None:
            buf = StringIO.StringIO()
        image.save(buf, format)
        contents = buf.getvalue()
        if output == None:
            buf.close()
        return contents

    def has_alpha(self):
        order = self.get_order()
        return 'A' in order
    
    def get_scaled_cutout_wdht(self, x1, y1, x2, y2, new_wd, new_ht,
                                  method='bicubic'):
        # calculate dimensions of NON-scaled cutout
        old_wd = x2 - x1 + 1
        old_ht = y2 - y1 + 1
        self.logger.debug("old=%dx%d new=%dx%d" % (
            old_wd, old_ht, new_wd, new_ht))

        data = self.get_data()
        newdata = data[y1:y2+1, x1:x2+1]

        newdata = self._imresize(newdata, new_wd, new_ht, method=method)

        ht, wd = newdata.shape[:2]
        old_wd, old_ht = max(old_wd, 1), max(old_ht, 1)
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

        newdata = self._imresize(newdata, new_wd, new_ht, method=method)

        ht, wd = newdata.shape[:2]
        old_wd, old_ht = max(old_wd, 1), max(old_ht, 1)
        scale_x = float(wd) / old_wd
        scale_y = float(ht) / old_ht
        res = Bunch.Bunch(data=newdata, org_fac=1,
                          scale_x=scale_x, scale_y=scale_y)
        return res

    def get_scaled_cutout(self, x1, y1, x2, y2, scale_x, scale_y,
                          method=None):
        if method == None:
            #if (have_pilutil or have_qtimage):
            if (have_pilutil):
                method = 'bicubic'
            else:
                method = 'basic'
                
        if method == 'basic':
            return self.get_scaled_cutout_basic(x1, y1, x2, y2,
                                                scale_x, scale_y)

        return self.get_scaled_cutout_pil(x1, y1, x2, y2,
                                          scale_x, scale_y,
                                          method=method)
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

            except Exception, e:
                self.logger.warn("Failed to get image metadata: %s" % (str(e)))

            # If we have a working color profile then handle any embedded
            # profile or color space information, if possible
            if have_cms and os.path.exists(profile['working']):
                # Assume sRGB image, unless we learn to the contrary
                in_profile = 'sRGB'
                try:
                    if image.info.has_key('icc_profile'):
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
                    elif kwds.has_key('ColorSpace'):
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
                    tr_key = (in_profile, 'working')
                    if tr_key in transform:
                        # We have am in-core transform already for this (faster)
                        image = convert_profile_pil_transform(image, transform[tr_key],
                                                              inPlace=True)
                    else:
                        # Convert using profiles on disk (slower)
                        if in_profile in profile:
                            in_profile = profile[in_profile]
                        image = convert_profile_pil(image, in_profile,
                                                    profile['working'])
                    self.logger.info("converted from profile (%s) to profile (%s)" % (
                        in_profile, profile['working']))
                except Exception, e:
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

    def _imresize(self, data, new_wd, new_ht, method='bilinear'):
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

            newdata = pilutil.imresize(data, zoom, interp=method)

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

def convert_profile_pil(image_pil, inprof_path, outprof_path, inPlace=False):
    if not have_cms:
        return image_pil
    
    image_out = ImageCms.profileToProfile(image_pil, inprof_path,
                                          outprof_path, 
                                          renderingIntent=rendering_intent,
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

def convert_profile_numpy(image_np, inprof_path, outprof_path):
    if (not have_pilutil) or (not have_cms):
        return image_np

    in_image_pil = pilutil.toimage(image_np)
    out_image_pil = convert_profile_pil(in_image_pil,
                                        inprof_path, outprof_path)
    image_out = pilutil.fromimage(out_image_pil)
    return image_out

def convert_profile_numpy_transform(image_np, transform):
    if (not have_pilutil) or (not have_cms):
        return image_np

    in_image_pil = pilutil.toimage(image_np)
    convert_profile_pil_transform(in_image_pil, transform, inPlace=True)
    image_out = pilutil.fromimage(in_image_pil)
    return image_out

def have_monitor_profile():
    return ('working', 'monitor') in transform

def convert_profile_monitor(image_np):
    output_transform = transform[('working', 'monitor')]
    out_np = convert_profile_numpy_transform(image_np, output_transform)
    return out_np

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
    
#END
