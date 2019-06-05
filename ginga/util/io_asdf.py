# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Module wrapper for loading ASDF files.

.. note:: The API for this module is currently unstable
          and may change in a future release.

"""
import numpy as np

try:
    import asdf  # noqa
    have_asdf = True
except ImportError:
    have_asdf = False

from ginga.util import iohelper

__all__ = ['have_asdf', 'load_asdf', 'ASDFFileHandler']


def load_asdf(asdf_obj, data_key='sci', wcs_key='wcs', header_key='meta'):
    """
    Load from an ASDF object.

    Parameters
    ----------
    asdf_obj : obj
        ASDF or ASDF-in-FITS object.

    data_key, wcs_key, header_key : str
        Key values to specify where to find data, WCS, and header
        in ASDF.

    Returns
    -------
    data : ndarray or `None`
        Image data, if found.

    wcs : obj or `None`
        GWCS object or models, if found.

    ahdr : dict
        Header containing metadata.

    """
    asdf_keys = asdf_obj.keys()

    if wcs_key in asdf_keys:
        wcs = asdf_obj[wcs_key]
    else:
        wcs = None

    if header_key in asdf_keys:
        ahdr = asdf_obj[header_key]
    else:
        ahdr = {}

    # TODO: What about non-image ASDF data, such as table?
    if data_key in asdf_keys:
        data = np.asarray(asdf_obj[data_key])
    else:
        data = None

    return data, wcs, ahdr


def loader(filepath, logger=None, **kwargs):
    """
    Load an object from an ASDF file.
    See :func:`ginga.util.loader` for more info.

    TODO: kwargs may contain info about what part of the file to load
    """
    # see ginga.util.loader module
    # TODO: return an AstroTable if loading a table, etc.
    #   for now, assume always an image
    from ginga import AstroImage
    image = AstroImage.AstroImage(logger=logger)

    with asdf.open(filepath) as asdf_f:
        #image.load_asdf(asdf_f, **kwargs)
        image.load_asdf(asdf_f)

    return image


class ASDFFileHandler(object):

    def __init__(self, logger):
        self.logger = logger
        self._path = None

    def load_file(self, filepath, idx=None, **kwargs):

        data_obj = loader(filepath, logger=self.logger, **kwargs)

        # set important metadata
        name = iohelper.name_image_from_path(filepath, idx=None)
        data_obj.set(path=filepath, name=name, idx=idx,
                     image_loader=self.load_file)

        return data_obj

    def open_file(self, filepath, **kwargs):
        # TODO: this should open the ASDF file and make a full inventory
        # of what is available to load
        self._path = filepath
        return self

    def close(self):
        # TODO: this should close the ASDF file
        self._path = None

    def __len__(self):
        return 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def load_idx_cont(self, idx_spec, loader_cont_fn, **kwargs):
        if self._path is None:
            raise ValueError("Please call open_file() first!")

        # TODO: idx_spec names some path to an ASDF object
        data_obj = self.load_file(self._path, idx=None, **kwargs)

        # call continuation function
        loader_cont_fn(data_obj)
