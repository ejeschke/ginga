#
# AstroTable.py -- Abstraction of an generic astro table.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np
from astropy.table import Table

from ginga.BaseImage import ViewerObjectBase, Header
from ginga.misc import Callback
from ginga.util import wcsmod, iohelper, io_fits
from ginga.util.six import iteritems

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

        # wcsclass specifies a pluggable WCS module
        if wcsclass is None:
            wcsclass = wcsmod.WCS
        self.wcs = wcsclass(self.logger)

        # ioclass specifies a pluggable IO module
        if ioclass is None:
            ioclass = io_fits.fitsLoaderClass
        self.io = ioclass(self.logger)
        self.io.register_type('table', self.__class__)

        # TODO: How to handle table with WCS data? For example, spectrum
        #       table may store dispersion solution as WCS.
        #if metadata is not None:
        #    header = self.get_header()
        #    self.wcs.load_header(header)

    @property
    def rows(self):
        tab_a = self._get_data()
        return len(tab_a)

    @property
    def columns(self):
        tab_a = self._get_data()
        return len(tab_a.colnames)

    def get_size(self):
        return (self.columns, self.rows)

    def get_data(self):
        return self._data

    def _get_data(self):
        return self._data

    def get_header(self, create=True):
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
        self.clear_metadata()

        # These keywords might be provided but not used.
        if 'inherit_primary_header' in kwargs:
            kwargs.pop('inherit_primary_header')

        ahdr = self.get_header()

        if 'format' not in kwargs:
            kwargs['format'] = 'fits'

        try:
            self._data = Table.read(hdu, **kwargs)
            ahdr.update(hdu.header)

        except Exception as e:
            self.logger.error("Error reading table from hdu: {0}".format(
                str(e)))

        # TODO: Try to make a wcs object on the header
        #self.wcs.load_header(hdu.header, fobj=fobj)

    def load_file(self, filespec, **kwargs):
        if self.io is None:
            raise TableError("No IO loader defined")

        self.io.load_file(filespec, dstobj=self, **kwargs)

    def get_thumbnail(self, length):
        thumb_np = np.eye(length)
        return thumb_np

#END
