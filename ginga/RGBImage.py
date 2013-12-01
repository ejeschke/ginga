#
# RGBImage.py -- Abstraction of an generic data image.
#
# Eric Jeschke (eric@naoj.org) 
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.util import io_rgb
from ginga.misc import Bunch
from ginga.BaseImage import BaseImage, ImageError, Header


class RGBImage(BaseImage):

    def __init__(self, data_np=None, metadata=None, 
                 logger=None, ioclass=io_rgb.RGBFileHandler):
        
        BaseImage.__init__(self, data_np=data_np, metadata=metadata,
                           logger=logger)
        
        self.io = ioclass(self.logger)

    def load_file(self, filepath):
        kwds = Header()
        metadata = { 'header': kwds, 'path': filepath }

        data_np = self.io.load_file(filepath, kwds)

        self.set_data(data_np, metadata=metadata)

    def save_file_as(self, filepath):
        data = self.get_data()
        hdr = self.get_header()
        self.io.save_file_as(filepath, data, header)

    def get_buffer(self, format, output=None):
        """Get image as a buffer in (format).
        Format should be 'jpeg', 'png', etc.
        """
        return self.io.get_buffer(self.get_data(), self.get_header(),
                                  format, output=output)

    def copy(self, astype=None):
        other = RGBImage()
        self.transfer(other, astype=astype)
        return other

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

        newdata = self.io.imresize(newdata, new_wd, new_ht, method=method)

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

        newdata = self.io.imresize(newdata, new_wd, new_ht, method=method)

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
            if (io_rgb.have_pilutil):
                method = 'bicubic'
            else:
                method = 'basic'
                
        if method == 'basic':
            return self.get_scaled_cutout_basic(x1, y1, x2, y2,
                                                scale_x, scale_y)

        return self.get_scaled_cutout_pil(x1, y1, x2, y2,
                                          scale_x, scale_y,
                                          method=method)

#END
