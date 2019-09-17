# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Module wrapper for loading HDF5 files.

.. note:: The API for this module is currently unstable
          and may change in a future release.

"""
import re
from collections import OrderedDict
import numpy as np

try:
    import h5py  # noqa
    have_h5py = True
except ImportError:
    have_h5py = False

from ginga.util import iohelper

__all__ = ['have_h5py', 'load_file', 'HDF5FileHandler']


def load_file(filepath, idx=None, logger=None, **kwargs):
    """
    Load an object from an H5PY file.
    See :func:`ginga.util.loader` for more info.

    """
    opener = HDF5FileHandler(logger)
    with opener.open_file(filepath):
        return opener.load_idx(idx, **kwargs)


class HDF5FileHandler(object):

    name = 'h5py'

    def __init__(self, logger):
        if not have_h5py:
            raise ValueError(
                "Need 'h5py' module installed to use this file handler")

        super(HDF5FileHandler, self).__init__()
        self.kind = 'hdf5'

        self.logger = logger
        self._f = None

    def get_indexes(self):
        return self._f.keys()

    def get_header(self, idx):
        items = [(key, val.decode() if isinstance(val, bytes) else val)
                 for key, val in self._f[idx].attrs.items()]
        return OrderedDict(items)

    def get_idx_type(self, idx):
        header = self.get_header(idx)
        if header.get('CLASS', None) in ['IMAGE']:
            return 'image'

        # TODO: is there a table spec for HDF5?

        return None

    def load_idx(self, idx, **kwargs):

        if idx is None:
            idx = self.find_first_good_idx()

        typ = self.get_idx_type(idx)
        if typ == 'image':
            from ginga import AstroImage, RGBImage

            header = self.get_header(idx)
            data_np = np.copy(self._f[idx].value)

            if 'PALETTE' in header:
                p_idx = header['PALETTE']
                p_data = self._f[p_idx].value
                data_np = p_data[data_np]
                image = RGBImage.RGBImage(logger=self.logger)
            else:
                image = AstroImage.AstroImage(logger=self.logger)
                image.update_keywords(header)

            image.set_data(data_np)

            name = iohelper.name_image_from_path(self._path, idx=idx)
            image.set(path=self._path, name=name, idx=idx,
                      image_loader=load_file)

            return image

        raise ValueError("I don't know how to read dataset '{}'".format(idx))

    def open_file(self, filespec, **kwargs):
        # open the HDF5 file and make a full inventory of what is
        # available to load
        info = iohelper.get_fileinfo(filespec)
        if not info.ondisk:
            raise ValueError("File does not appear to be on disk: %s" % (
                info.url))

        self._path = info.filepath

        self.logger.debug("Loading file '%s' ..." % (self._path))
        self._f = h5py.File(self._path, 'r', **kwargs)
        return self

    def close(self):
        _f = self._f
        self._f = None
        self._path = None
        _f.close()

    def __len__(self):
        if self._f is None:
            return 0
        return len(self._f)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def load_idx_cont(self, idx_spec, loader_cont_fn, **kwargs):
        if len(self) == 0:
            raise ValueError("Please call open_file() first!")

        idx_lst = self.get_matching_indexes(idx_spec)
        for idx in idx_lst:
            try:
                dst_obj = self.load_idx(idx, **kwargs)

                # call continuation function
                loader_cont_fn(dst_obj)

            except Exception as e:
                self.logger.error("Error loading index '%s': %s" % (idx, str(e)))

    def find_first_good_idx(self):

        for idx in self.get_indexes():

            # rule out Datasets we can't deal with
            typ = self.get_idx_type(idx)
            if typ not in ('image', 'table'):
                continue

            # Looks good, let's try it
            return idx

        return None

    def get_matching_indexes(self, idx_spec):
        """
        Parameters
        ----------
        idx_spec : str
            A string in the form of a pair of brackets enclosing some
            index expression matching Datasets in the file

        Returns
        -------
        result : list
            A list of indexes that can be used to access each Dataset
            matching the pattern
        """
        # if index is missing, assume to open the first Dataset we know how
        # to do something with
        if idx_spec is None or idx_spec == '':
            idx = self.find_first_good_idx()
            return [idx]

        match = re.match(r'^\[(.+)\]$', idx_spec)
        if not match:
            return []

        name = match.group(1).strip()
        if re.match(r'^\d+$', name):
            # index just names a single dataset by number
            # Assume this means by order in the list
            return [int(name)]

        # find all datasets matching the name
        # TODO: could do some kind of regular expression matching
        idx_lst = []
        idx = 0
        for d_name in self.get_indexes():
            if name == '*' or name == d_name:
                idx_lst.append(d_name)

        return idx_lst
