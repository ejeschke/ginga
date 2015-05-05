#
# RemoteImage.py -- Mixin for images that live on a remote server
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

from ginga.AstroImage import AstroImage, AstroHeader

class RemoteImage(AstroImage):

    def __init__(self, proxy, metadata=None, logger=None,
                 #wcsclass=wcsClass, ioclass=ioClass,
                 inherit_primary_header=False):

        self._proxy = proxy
        self._shape = tuple([])
        self.id = None

        AstroImage.__init__(self, data_np=None, metadata=metadata,
                            logger=logger, #wcsclass=wcsClass, ioclass=ioClass,
                            inherit_primary_header=inherit_primary_header)
        self._data = None

    @property
    def shape(self):
        return self._shape

    def load_file(self, filepath, numhdu=None, naxispath=None):
        self.id = filepath
        shape, header = self._proxy.load_file(filepath, numhdu=numhdu,
                                              naxispath=naxispath)
        self._shape = shape

        ahdr = { key: header[key]['value'] for key in header.keys() }
        # this will set our local wcs
        self.update_keywords(ahdr)

    def _set_minmax(self, noinf=False):
        self.minval, self.maxval = self._proxy.get_minmax(self.id, noinf=False)
        (self.minval_noinf,
         self.maxval_noinf) = self._proxy.get_minmax(self.id, noinf=True)

    def _get_data(self):
        if self._data is None:
            self._data = self._proxy.get_data(self.id)
        return self._data

    def _slice(self, view):
        """
        Send view to remote server and do slicing there.
        """
        if self._data is not None:
            return self._data[view]
        return self._proxy.get_view(self.id, view)

    def get_data_xy(self, x, y):
        # TODO: cache some points for faster response?
        return self._proxy.get_data_xy(self.id, x, y)

    def get_pixels_on_line(self, x1, y1, x2, y2):
        return self._proxy.get_pixels_on_line(self.id, x1, y1, x2, y2)
