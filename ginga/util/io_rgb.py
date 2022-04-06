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
from PIL import Image
from PIL.ExifTags import TAGS

from ginga.BaseImage import Header, ImageError
from ginga.util import iohelper, rgb_cms
from ginga.util.io import io_base
from ginga.misc import Bunch
from ginga import trcalc

try:
    # do we have opencv available?
    import cv2
    have_opencv = True
except ImportError:
    have_opencv = False

# exifread library for getting metadata, in case we are using OpenCv
try:
    import exifread
    have_exif = True
except ImportError:
    have_exif = False

# For testing...
#have_exif = False
#have_opencv = False


def load_file(filepath, idx=None, logger=None, **kwargs):
    """
    Load an object from a RGB file.

    """
    opener = RGBFileHandler(logger)
    return opener.load_file(filepath, **kwargs)


class BaseRGBFileHandler(io_base.BaseIOHandler):

    name = 'RGB'

    def __init__(self, logger):
        super(BaseRGBFileHandler, self).__init__(logger)

        self._path = None

        self.clr_mgr = rgb_cms.ColorManager(self.logger)

    def load_file(self, filespec, dstobj=None, **kwargs):
        info = iohelper.get_fileinfo(filespec)
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

        data_np = self.imload(filepath, metadata)

        dstobj.set_data(data_np, metadata=metadata)

        if dstobj.name is not None:
            dstobj.set(name=dstobj.name)
        else:
            name = iohelper.name_image_from_path(filepath, idx=None)
            dstobj.set(name=name)

        if 'order' in metadata:
            dstobj.order = metadata['order']
        dstobj.set(path=filepath, idx=None, image_loader=self.load_file)
        return dstobj

    def open_file(self, filespec, **kwargs):
        self._path = filespec
        return self

    def close(self):
        self._path = None

    def __len__(self):
        return 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def load_idx_cont(self, idx_spec, loader_cont_fn, **kwargs):

        # TODO: raise an error if idx_spec doesn't match a single image
        idx = 0
        if idx_spec is not None and idx_spec != '':
            idx = int(idx_spec)

        data_obj = self.load_idx(idx, **kwargs)

        # call continuation function
        loader_cont_fn(data_obj)

    def imload(self, filepath, metadata):
        """Load an image file, guessing the format, and return a numpy
        array containing an RGB image.  If EXIF keywords can be read
        they are returned in the metadata.
        """
        start_time = time.time()
        typ, enc = mimetypes.guess_type(filepath)
        if not typ:
            typ = 'image/jpeg'
        typ, subtyp = typ.split('/')
        self.logger.debug("MIME type is %s/%s" % (typ, subtyp))

        data_np = self._imload(filepath, metadata)

        end_time = time.time()
        self.logger.debug("loading time %.4f sec" % (end_time - start_time))
        return data_np

    def imresize(self, data, new_wd, new_ht, method='bilinear'):
        """Scale an image in numpy array _data_ to the specified width and
        height.  A smooth scaling is preferred.
        """
        start_time = time.time()

        newdata = self._imresize(data, new_wd, new_ht, method=method)

        end_time = time.time()
        self.logger.debug("scaling time %.4f sec" % (end_time - start_time))

        return newdata

    def get_thumb(self, filepath):
        if not have_exif:
            raise Exception("Install exifread to use this method")

        try:
            with open(filepath, 'rb') as in_f:
                info = exifread.process_file(in_f)
            buf = info['JPEGThumbnail']

        except Exception as e:
            return None

        image = Image.open(BytesIO(buf))
        data_np = np.array(image)
        return data_np

    def _getexif(self, filepath, kwds):
        if have_exif:
            try:
                with open(filepath, 'rb') as in_f:
                    info = exifread.process_file(in_f, details=False)
                if info is not None:
                    kwds.update(info)
                    o_tag = 'Image Orientation'
                    if o_tag in info:
                        val = info[o_tag].values[0]
                        kwds[o_tag] = val

            except Exception as e:
                self.logger.warning("Failed to get image metadata: %s" % (str(e)))

        else:
            self.logger.warning("Please install 'exifread' module to get image metadata")

    def get_buffer(self, data_np, header, format, output=None):
        """Get image as a buffer in (format).
        Format should be 'jpeg', 'png', etc.
        """
        image = Image.fromarray(data_np)
        buf = output
        if buf is None:
            buf = BytesIO()
        image.save(buf, format)
        return buf

    def get_directory(self):
        return self.hdu_db

    def get_info_idx(self, idx):
        return self.hdu_db[idx]


class OpenCvFileHandler(BaseRGBFileHandler):

    name = 'OpenCv'

    def open_file(self, filespec, **kwargs):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise ImageError("File does not appear to be on disk: %s" % (
                info.url))

        self.fileinfo = info
        filepath = info.filepath

        self._path = filepath
        self.rgb_f = cv2.VideoCapture(filepath)
        # self.rgb_f.set(cv2.CAP_PROP_CONVERT_RGB, False)

        idx = 0
        extver_db = {}
        self.hdu_info = []
        self.hdu_db = {}
        numframes = int(self.rgb_f.get(cv2.CAP_PROP_FRAME_COUNT))
        self.logger.info("number of frames: {}".format(numframes))

        naxispath = [numframes]
        idx = 0
        name = "frame{}".format(idx)
        extver = 0
        # prepare a record of pertinent info about the HDU for
        # lookups by numerical index or (NAME, EXTVER)
        d = Bunch.Bunch(index=idx, name=name, extver=extver,
                        dtype='uint8', htype='N/A')
        self.hdu_info.append(d)
        # different ways of accessing this HDU:
        # by numerical index
        self.hdu_db[idx] = d
        # by (hduname, extver)
        key = (name, extver)
        if key not in self.hdu_db:
            self.hdu_db[key] = d

        self.extver_db = extver_db
        return self

    def close(self):
        self._path = None
        self.rgb_f = None

    def __len__(self):
        return len(self.hdu_info)

    def load_idx(self, idx, **kwargs):
        if self.rgb_f is None:
            raise ValueError("Please call open_file() first!")

        if idx is None:
            idx = 0

        metadata = dict()
        if idx == 0:
            data_np = self.imload(self.fileinfo.filepath, metadata)

        else:
            self.rgb_f.set(cv2.CAP_PROP_POS_FRAMES, idx)
            okay, data_np = self.rgb_f.read()
            if not okay:
                raise ValueError("Error reading index {}".format(idx))

            data_np = self._process_opencv_array(data_np, metadata,
                                                 self.fileinfo.filepath)

        from ginga.RGBImage import RGBImage
        data_obj = RGBImage(data_np=data_np, metadata=metadata,
                            logger=self.logger, order=metadata['order'])
        data_obj.io = self

        name = self.fileinfo.name + '[{}]'.format(idx)
        data_obj.set(name=name, path=self.fileinfo.filepath, idx=idx)

        return data_obj

    def save_file_as(self, filepath, data_np, header):
        # TODO: save keyword metadata!
        if not have_opencv:
            raise ImageError("Install 'opencv' to be able to save images")

        # First choice is OpenCv, because it supports high-bit depth
        # multiband images
        cv2.imwrite(filepath, data_np)

    def _imload(self, filepath, metadata):
        if not have_opencv:
            raise ImageError("Install 'opencv' to be able to load images")

        ## data_np = cv2.imread(filepath,
        ##                      cv2.IMREAD_ANYDEPTH + cv2.IMREAD_ANYCOLOR +
        ##                      cv2.IMREAD_IGNORE_ORIENTATION)
        #
        # OpenCv supports high-bit depth multiband images if you read like
        # this
        # NOTE: IMREAD_IGNORE_ORIENTATION does not seem to be obeyed here!
        data_np = cv2.imread(filepath,
                             cv2.IMREAD_UNCHANGED + cv2.IMREAD_IGNORE_ORIENTATION)

        return self._process_opencv_array(data_np, metadata, filepath)

    def _process_opencv_array(self, data_np, metadata, filepath):
        # opencv returns BGR images, whereas PIL and others return RGB
        if len(data_np.shape) >= 3 and data_np.shape[2] >= 3:
            if data_np.shape[2] == 3:
                order = 'BGR'
                dst_order = 'RGB'
            else:
                order = 'BGRA'
                dst_order = 'RGBA'
            data_np = trcalc.reorder_image(dst_order, data_np, order)
            metadata['order'] = dst_order

        kwds = metadata.get('header', None)
        if kwds is None:
            kwds = Header()
            metadata['header'] = kwds

        # OpenCv doesn't "do" image metadata, so we punt to exifread
        # library (if installed)
        self._getexif(filepath, kwds)

        # OpenCv added a feature to do auto-orientation when loading
        # (see https://github.com/opencv/opencv/issues/4344)
        # So reset these values to prevent auto-orientation from
        # happening later
        # NOTE: this is only needed if IMREAD_IGNORE_ORIENTATION is not
        # working
        kwds['Orientation'] = 1
        kwds['Image Orientation'] = 1

        # convert to working color profile, if can
        if self.clr_mgr.can_profile():
            data_np = self.clr_mgr.profile_to_working_numpy(data_np, kwds)

        return data_np

    def _imresize(self, data, new_wd, new_ht, method='bilinear'):
        # TODO: take into account the method parameter
        if not have_opencv:
            raise ImageError("Install 'opencv' to be able to resize RGB images")

        # First choice is OpenCv, because it supports high-bit depth
        # multiband images
        newdata = cv2.resize(data, dsize=(new_wd, new_ht),
                             interpolation=cv2.INTER_CUBIC)

        return newdata


class PillowFileHandler(BaseRGBFileHandler):

    name = 'Pillow'

    def open_file(self, filespec, **kwargs):

        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise ImageError("File does not appear to be on disk: %s" % (
                info.url))

        self.fileinfo = info
        filepath = info.filepath

        self._path = filepath
        self.rgb_f = Image.open(filepath)

        idx = 0
        extver_db = {}
        self.hdu_info = []
        self.hdu_db = {}
        numframes = getattr(self.rgb_f, 'n_frames', 1)
        self.logger.info("number of frames: {}".format(numframes))

        for idx in range(numframes):
            name = "frame{}".format(idx)
            extver = 0
            # prepare a record of pertinent info about the HDU for
            # lookups by numerical index or (NAME, EXTVER)
            d = Bunch.Bunch(index=idx, name=name, extver=extver,
                            dtype='uint8', htype='N/A')
            self.hdu_info.append(d)
            # different ways of accessing this HDU:
            # by numerical index
            self.hdu_db[idx] = d
            # by (hduname, extver)
            key = (name, extver)
            if key not in self.hdu_db:
                self.hdu_db[key] = d

        self.extver_db = extver_db
        return self

    def close(self):
        self._path = None
        self.rgb_f = None

    def __len__(self):
        return len(self.hdu_info)

    def save_file_as(self, filepath, data_np, header):
        # TODO: save keyword metadata!
        img = Image.fromarray(data_np)

        # pillow is not happy saving images to JPG with an alpha channel
        img = img.convert('RGB')

        img.save(filepath)

    def load_idx(self, idx, **kwargs):
        if self.rgb_f is None:
            raise ValueError("Please call open_file() first!")

        # "seek" functionality does not seem to be working for all the
        # versions of Pillow we are encountering
        #self.rgb_f.seek(idx)
        image = self.rgb_f

        kwds = Header()
        metadata = dict(header=kwds)

        try:
            self._get_header(image, kwds)
        except Exception as e:
            self.logger.warning("Failed to get image metadata: %s" % (str(e)))

        # convert to working color profile, if can
        if self.clr_mgr.can_profile():
            image = self.clr_mgr.profile_to_working_pil(image, kwds)

        # convert from PIL to numpy
        data_np = np.array(image)

        from ginga.RGBImage import RGBImage
        data_obj = RGBImage(data_np=data_np, metadata=metadata,
                            logger=self.logger, order=image.mode)
        data_obj.io = self

        name = self.fileinfo.name + '[{}]'.format(idx)
        data_obj.set(name=name, path=self.fileinfo.filepath, idx=idx,
                     header=kwds)

        return data_obj

    def _get_header(self, image, kwds):
        if hasattr(image, '_getexif'):
            info = image._getexif()
            if info is not None:
                for tag, value in info.items():
                    kwd = TAGS.get(tag, tag)
                    kwds[kwd] = value

        else:
            self.logger.warning("can't get EXIF data; no _getexif() method")

        # is there an embedded color profile?
        if 'icc_profile' in image.info:
            kwds['icc_profile'] = image.info['icc_profile']

    def _imload(self, filepath, metadata):
        image = Image.open(filepath)

        kwds = metadata.get('header', None)
        if kwds is None:
            kwds = Header()
            metadata['header'] = kwds

        try:
            self._get_header(image, kwds)
        except Exception as e:
            self.logger.warning("Failed to get image metadata: {!r}".format(e))

        # convert to working color profile, if can
        if self.clr_mgr.can_profile():
            image = self.clr_mgr.profile_to_working_pil(image, kwds)

        # convert from PIL to numpy
        data_np = np.array(image)
        metadata['order'] = image.mode
        return data_np

    def _imresize(self, data, new_wd, new_ht, method='bilinear'):
        # TODO: take into account the method parameter

        img = Image.fromarray(data)
        img = img.resize((new_wd, new_ht), Image.BICUBIC)
        newdata = np.array(img)

        return newdata


class PPMFileHandler(BaseRGBFileHandler):

    name = 'PPM'

    def _imload(self, filepath, metadata):
        return open_ppm(filepath)


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

    # Get image dimensions
    header = infile.readline().strip()
    while header.startswith(b'#') or len(header) == 0:
        header = infile.readline().strip()

    width, height = [int(x) for x in header.split()]
    header = infile.readline()

    # Get unit size
    maxval = int(header)
    if maxval <= 255:
        dtype = np.uint8
    elif maxval <= 65535:
        dtype = np.uint16

    # read image
    if depth > 1:
        arr = np.fromfile(infile, dtype=dtype).reshape((height, width, depth))
    else:
        arr = np.fromfile(infile, dtype=dtype).reshape((height, width))

    if sys.byteorder == 'little':
        arr = arr.byteswap()
    return arr


from collections.abc import Sequence, Iterator


class VideoAccess(Sequence, Iterator):
    def __init__(self):
        super(Sequence, self).__init__()

        self.rgb_f = None
        self.idx = -1
        self.shape = (0, 0, 0)

    def open(self, filepath):
        self.rgb_f = cv2.VideoCapture(filepath)
        # self.rgb_f.set(cv2.CAP_PROP_CONVERT_RGB, False)

        self.idx = 0

        # Get width and height of frames and resize window
        width = int(self.rgb_f.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.rgb_f.get(cv2.CAP_PROP_FRAME_HEIGHT))
        depth = int(self.rgb_f.get(cv2.CAP_PROP_FRAME_COUNT))
        self.shape = (width, height, depth)

        return self

    def read(self, idx):
        self.rgb_f.set(cv2.CAP_PROP_POS_FRAMES, idx)
        okay, data_np = self.rgb_f.read()
        if not okay:
            raise ValueError("Error reading index {}".format(idx))

        data_np = data_np[..., :: -1]
        return data_np

    def __next__(self):
        self.idx += 1
        if self.idx == self.shape[2]:
            raise StopIteration("Reached the end of frames")
        return self.read(self.idx)

    def __getitem__(self, idx):
        return self.read(idx)

    def __len__(self):
        return self.shape[2]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # hopefully this closes the object
        self.rgb_f = None
        return False


RGBFileHandler = PillowFileHandler

# END
