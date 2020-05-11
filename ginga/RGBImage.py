#
# RGBImage.py -- Abstraction of an generic data image.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.util import io_rgb
from ginga.BaseImage import BaseImage, ImageError


class RGBImage(BaseImage):

    def __init__(self, data_np=None, metadata=None,
                 logger=None, name=None, order=None,
                 ioclass=io_rgb.RGBFileHandler):

        BaseImage.__init__(self, data_np=data_np, metadata=metadata,
                           logger=logger, order=order, name=name)

        self.io = ioclass(self.logger)
        self.hasAlpha = 'A' in self.order

    def set_color(self, r, g, b):
        # TODO: handle other sizes
        ch_max = np.iinfo(self._data.dtype).max
        red = self.get_slice('R')
        red[:] = int(ch_max * r)
        grn = self.get_slice('G')
        grn[:] = int(ch_max * g)
        blu = self.get_slice('B')
        blu[:] = int(ch_max * b)

    def load_file(self, filespec, **kwargs):
        if self.io is None:
            raise ImageError("No IO loader defined")

        self.io.load_file(filespec, dstobj=self, **kwargs)

    def load_data(self, data_np, metadata=None):
        self.clear_metadata()
        self.set_data(data_np, metadata=metadata)

        if self.name is not None:
            self.set(name=self.name)

    def save_as_file(self, filepath):
        data = self._get_data()
        data = data.astype(np.uint8)
        hdr = self.get_header()
        self.io.save_file_as(filepath, data, hdr)

    def get_buffer(self, format, output=None):
        """Get image as a buffer in (format).
        Format should be 'jpeg', 'png', etc.
        """
        return self.io.get_buffer(self._get_data(), self.get_header(),
                                  format, output=output)

    def copy(self, astype=None):
        other = RGBImage()
        self.transfer(other, astype=astype)
        return other

    def has_alpha(self):
        order = self.get_order()
        return 'A' in order

    def insert_alpha(self, pos, alpha):
        if not self.has_alpha():
            order = list(self.order)
            l = [self.get_slice(c) for c in order]
            wd, ht = self.get_size()
            a = np.zeros((ht, wd), dtype=self._data.dtype)
            a.fill(alpha)
            l.insert(pos, a)
            self._data = np.dstack(l)
            order.insert(pos, 'A')
            self.order = ''.join(order)
