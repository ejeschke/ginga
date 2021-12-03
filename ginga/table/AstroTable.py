#
# AstroTable.py -- Abstraction of an generic astro table.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.BaseImage import ViewerObjectBase, Header
from ginga.util import wcsmod


class TableError(Exception):
    pass


class AstroTableHeader(Header):
    pass


class AstroTable(ViewerObjectBase):
    """Abstraction of an astronomical data (table).

    .. note:: This module is NOT thread-safe!

    """
    # class variables for WCS can be set
    wcsClass = None
    ioClass = None

    @classmethod
    def set_wcsClass(cls, klass):
        cls.wcsClass = klass

    @classmethod
    def set_ioClass(cls, klass):
        cls.ioClass = klass

    def __init__(self, data_ap=None, metadata=None, logger=None, name=None,
                 wcsclass=wcsClass, ioclass=ioClass):

        ViewerObjectBase.__init__(self, logger=logger, metadata=metadata,
                                  name=name)

        self._data = data_ap
        self.naxispath = []
        self.colnames = []

        # TODO: How to handle table with WCS data? For example, spectrum
        #       table may store dispersion solution as WCS.
        # wcsclass specifies a pluggable WCS module
        if wcsclass is None:
            wcsclass = wcsmod.WCS
        self.wcs = wcsclass(self.logger)

        # ioclass specifies a pluggable IO module
        if ioclass is None:
            from ginga.util import io_fits
            ioclass = io_fits.fitsLoaderClass
        self.io = ioclass(self.logger)

    @property
    def rows(self):
        tab_a = self._get_data()
        return len(tab_a)

    @property
    def columns(self):
        return len(self.colnames)

    def get_size(self):
        return (self.columns, self.rows)

    def get_data(self):
        return self._data

    def _get_data(self):
        return self._data

    def get_header(self, create=True, **kwargs):
        try:
            # By convention, the fits header is stored in a dictionary
            # under the metadata keyword 'header'
            displayhdr = self.metadata['header']

        except KeyError as e:
            if not create:
                raise e
            displayhdr = AstroTableHeader()
            self.metadata['header'] = displayhdr

        return displayhdr

    def set_data(self, data_ap, metadata=None):
        """Use this method to SHARE (not copy) the incoming table.
        """
        self._data = data_ap

        if metadata:
            self.update_metadata(metadata)

        self.make_callback('modified')

    def clear_all(self):
        # clear metadata
        super(AstroTable, self).clear_all()

        # unreference data
        self._data = None

    def get_minmax(self, noinf=False):
        # TODO: what should this mean for a table?
        return (0, 0)

    def load_hdu(self, hdu, fobj=None, **kwargs):
        if self.io is None:
            raise TableError("No IO loader defined")

        self.io.load_hdu(hdu, fobj=fobj, dstobj=self, **kwargs)

        # TODO: Try to make a wcs object on the header
        #self.wcs.load_header(hdu.header, fobj=fobj)

    def load_file(self, filespec, **kwargs):
        if self.io is None:
            raise TableError("No IO loader defined")

        self.io.load_file(filespec, dstobj=self, **kwargs)

    def get_thumbnail(self, length):
        thumb_np = np.eye(length)
        return thumb_np
