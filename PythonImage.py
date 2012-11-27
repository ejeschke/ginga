#
# PythonImage.py -- Abstraction of an generic data image.
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Mon Nov 26 20:43:28 HST 2012
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

class PythonImage(object):

    def __init__(self, data_np=None, metadata=None, logger=None):
        self.logger = logger
        if data_np == None:
            data_np = numpy.zeros((1, 1))
        self.data = data_np
        self.maxval = numpy.nanmax(data_np)
        self.minval = numpy.nanmin(data_np)
        self.metadata = {}
        if metadata:
            self.update_metadata(metadata)

        self._set_minmax()

    @property
    def width(self):
        # NOTE: numpy stores data in column-major layout
        return self.data.shape[1]
        
    @property
    def height(self):
        # NOTE: numpy stores data in column-major layout
        return self.data.shape[0]

    def get_size(self):
        return (self.width, self.height)
    
    def get_data(self):
        return self.data
        
    def copy_data(self):
        return self.get_data()
        
    def get_data_xy(self, x, y):
        #val = self.idata.getpixel((x, y))
        val = self.data[y, x]
        return val
        
    def get_data_size(self):
        return self.get_size()

    def get_metadata(self):
        return self.metadata.copy()
        
    def get_header(self):
        return self.get('exif')
        
    def get(self, kwd, *args):
        if self.metadata.has_key(kwd):
            return self.metadata[kwd]
        else:
            # return a default if there is one
            if len(args) > 0:
                return args[0]
            raise KeyError(kwd)
        
    def get_list(self, *args):
        return map(self.get, args)
    
    def __getitem__(self, kwd):
        return self.metadata[kwd]
        
    def update(self, kwds):
        self.metadata.update(kwds)
        
    def set(self, **kwds):
        self.update(kwds)
        
    def __setitem__(self, kwd, value):
        self.metadata[kwd] = value
        
    def set_data(self, data_np, metadata=None, astype=None):
        """Use this method to SHARE (not copy) the incoming array.
        """
        if astype:
            data = data_np.astype(astype)
        else:
            data = data_np
        self.data = data

        if metadata:
            self.update_metadata(metadata)
            
        self._set_minmax()

    def _set_minmax(self):
        self.maxval = numpy.nanmax(self.data)
        self.minval = numpy.nanmin(self.data)

        # TODO: see if there is a faster way to ignore infinity
        if numpy.isfinite(self.maxval):
            self.maxval_noinf = self.maxval
        else:
            self.maxval_noinf = numpy.nanmax(self.data[numpy.isfinite(self.data)])
        
        if numpy.isfinite(self.minval):
            self.minval_noinf = self.minval
        else:
            self.minval_noinf = numpy.nanmin(self.data[numpy.isfinite(self.data)])
        
    def get_minmax(self, noinf=False):
        if not noinf:
            return (self.minval, self.maxval)
        else:
            return (self.minval_noinf, self.maxval_noinf)

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
        
    def update_metadata(self, keyDict):
        for key, val in keyDict.items():
            self.metadata[key] = val

    def transfer(self, other, astype=None):
        other.set_data(self.data, metadata=self.metadata, astype=astype)
        
    def copy(self, astype=None):
        other = PythonImage()
        self.transfer(other, astype=astype)
        return other
        
    def cutout_data(self, x1, y1, x2, y2, astype=None):
        """cut out data area based on coords. 
        """
        data = self.get_data()
        data = data[y1:y2, x1:x2]
        if astype:
            data = data.astype(astype)
        return data
  
    def cutout_adjust(self, x1, y1, x2, y2, astype=None):
        dx = x2 - x1
        dy = y2 - y1
        
        if x1 < 0:
            x1 = 0; x2 = dx
        else:
            if x2 >= self.width:
                x2 = self.width
                x1 = x2 - dx
                
        if y1 < 0:
            y1 = 0; y2 = dy
        else:
            if y2 >= self.height:
                y2 = self.height
                y1 = y2 - dy

        data = self.cutout_data(x1, y1, x2, y2, astype=astype)
        return (data, x1, y1, x2, y2)

    def cutout_radius(self, x, y, radius, astype=None):
        return self.cutout_adjust(x-radius, y-radius,
                                  x+radius+1, y+radius+1,
                                  astype=astype)

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
