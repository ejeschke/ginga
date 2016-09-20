#
# AstroTable.py -- Abstraction of an generic astro table.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import logging

import numpy as np
from astropy.table import Table
from astropy.io import fits

from ginga.misc import Callback
from ginga.util import iohelper


class TableError(Exception):
    pass


class AstroTable(Callback.Callbacks):

    def __init__(self, data_ap=None, metadata=None, logger=None, name=None):

        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('AstroTable')
        self._data = data_ap
        self.metadata = {}
        self.name = name
        # make sure a table has these attributes
        self.metadata.setdefault('name', None)

        # For callbacks
        for name in ('modified', ):
            self.enable_callback(name)

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

    def get(self, kwd, *args):
        if kwd in self.metadata:
            return self.metadata[kwd]
        else:
            # return a default if there is one
            if len(args) > 0:
                return args[0]
            raise KeyError(kwd)

    def __getitem__(self, kwd):
        return self.metadata[kwd]

    def update(self, kwds):
        self.metadata.update(kwds)

    def set(self, **kwds):
        self.update(kwds)

    def __setitem__(self, kwd, value):
        self.metadata[kwd] = value

    def clear_metadata(self):
        self.metadata = {}

    def get_header(self):
        # for compatibility with images--what should this contain?
        return {}

    def set_data(self, data_ap, metadata=None):
        """Use this method to SHARE (not copy) the incoming table.
        """
        self._data = data_ap

        if metadata:
            self.update_metadata(metadata)

        self.make_callback('modified')

    def load_hdu(self, hdu, fobj=None):
        self.clear_metadata()

        try:
            tbl = Table.read(hdu, format='fits')
            self._data = tbl

        except Exception as e:
            self.logger.error("Error reading table from hdu: {0}".format(
                str(e)))

    def load_file(self, filepath, numhdu=None,
                  allow_numhdu_override=True, memmap=None):
        self.logger.debug("Loading file '%s' ..." % (filepath))
        self.clear_metadata()

        info = iohelper.get_fileinfo(filepath)
        if numhdu is None:
            numhdu = info.numhdu

        try:
            with fits.open(filepath, 'readonly') as in_f:
                tbl = Table.read(in_f[numhdu], format='fits')
            self._data = tbl

        except Exception as e:
            self.logger.error("Error reading table from file: {0}".format(
                str(e)))

        # Set the table name if no name currently exists for this table
        # TODO: should this *change* the existing name, if any?
        if not (self.name is None):
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
