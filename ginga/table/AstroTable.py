#
# AstroTable.py -- Abstraction of an generic astro table.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.util.six import iteritems

import numpy as np
from astropy.table import Table
from astropy.io import fits

from ginga.BaseImage import ViewerObjectBase, Header
from ginga.misc import Callback
from ginga.util import wcsmod, iohelper


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

    @classmethod
    def set_wcsClass(cls, klass):
        cls.wcsClass = klass

    def __init__(self, data_ap=None, metadata=None, logger=None, name=None,
                 wcsclass=wcsClass):

        ViewerObjectBase.__init__(self, logger=logger, metadata=metadata,
                                  name=name)

        self._data = data_ap

        # wcsclass specifies a pluggable WCS module
        if wcsclass is None:
            wcsclass = wcsmod.WCS
        self.wcs = wcsclass(self.logger)

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

    def get_minmax(self, noinf=False):
        # TODO: what should this mean for a table?
        return (0, 0)

    def load_hdu(self, hdu, fobj=None, **kwargs):
        self.clear_metadata()

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

    def load_file(self, filepath, numhdu=None, **kwargs):
        self.logger.debug("Loading file '%s' ..." % (filepath))
        self.clear_metadata()

        # These keywords might be provided but not used.
        kwargs.pop('allow_numhdu_override')
        kwargs.pop('memmap')

        info = iohelper.get_fileinfo(filepath)
        if numhdu is None:
            numhdu = info.numhdu

        try:
            with fits.open(filepath, 'readonly') as in_f:
                self.load_hdu(in_f[numhdu], **kwargs)

        except Exception as e:
            self.logger.error("Error reading table from file: {0}".format(
                str(e)))

        # Set the table name if no name currently exists for this table
        # TODO: should this *change* the existing name, if any?
        if self.name is not None:
            self.set(name=self.name)
        else:
            name = self.get('name', None)
            if name is None:
                name = info.name
                if ('[' not in name):
                    name += iohelper.get_hdu_suffix(numhdu)
                self.set(name=name)

        self.set(path=filepath, idx=numhdu)

    def get_thumbnail(self, length):
        thumb_np = np.eye(length)
        return thumb_np

#END
