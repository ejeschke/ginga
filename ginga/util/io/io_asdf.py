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
    from asdf.fits_embed import AsdfInFits
    have_asdf = True
except ImportError:
    have_asdf = False

from ginga import AstroImage
from ginga.util import iohelper, wcsmod
from ginga.util.io import io_base
# need this specific WCS for ASDF loads
from ginga.util.wcsmod import wcs_astropy_ape14   # noqa

__all__ = ['have_asdf', 'load_file', 'load_asdf', 'load_from_asdf',
           'ASDFFileHandler']


def load_from_asdf(asdf_obj, data_key='data', wcs_key='wcs', header_key='meta'):
    """
    Load from an ASDF object.  This method is primarily used internally
    to extract the correct parts of an ASDF file to reconstruct an image
    with WCS and metadata.

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
    elif wcs_key in asdf_obj[header_key]:
        wcs = asdf_obj[header_key][wcs_key]
    else:
        wcs = None

    if header_key in asdf_keys:
        ahdr = asdf_obj[header_key]
    else:
        ahdr = {}

    # TODO: What about non-image ASDF data, such as table?
    if data_key in asdf_keys:
        data = np.asarray(asdf_obj[data_key])
    # TODO: This hack is so earlier test files would still
    # load, but we need to make customization easier so
    # we can remove this hack.
    elif 'sci' in asdf_keys:
        data = np.asarray(asdf_obj['sci'])
    else:
        data = None

    return data, wcs, ahdr


def load_asdf(asdf_obj, idx=None, logger=None):
    """
    Load data from an open ASDF object.

    Parameters
    ----------
    asdf_obj : obj
        ASDF or ASDF-in-FITS object.

    idx : None
        Currently unused. Reserved for future use to identify specific
        data set of an ASDF object containing the data of interest.

    logger : python logging object
        Currently unused. Reserved for future use in logging

    Returns
    -------
    data : ndarray or `None`
        Image data, if found.

    wcs : obj or `None`
        GWCS object or models, if found.

    ahdr : dict
        Header containing metadata.

    """
    # TODO: support other types, like AstroTable, if ASDF can contain them
    data_obj = AstroImage.AstroImage(logger=logger)

    # TODO: idx may contain info about what part of the file to load
    #  e.g. should we pass as 'data_key' parameter?
    data, wcs, ahdr = load_from_asdf(asdf_obj)

    data_obj.setup_data(data, naxispath=None)

    wcsinfo = wcsmod.get_wcs_class('astropy_ape14')
    data_obj.wcs = wcsinfo.wrapper_class(logger=logger)
    data_obj.wcs.wcs = wcs

    if wcs is not None:
        data_obj.wcs.coordsys = wcs.output_frame.name

    return data_obj


def load_file(filepath, idx=None, logger=None, **kwargs):
    """
    Load an object from an ASDF file.
    See :func:`ginga.util.loader` for more info.

    """
    # see ginga.util.loader module
    opener = ASDFFileHandler(logger)
    data_obj = opener.load_file(filepath, idx=idx, **kwargs)

    return data_obj


class ASDFFileHandler(io_base.BaseIOHandler):

    name = 'asdf'

    def __init__(self, logger):
        super(ASDFFileHandler, self).__init__(logger)

        self._path = None

    def load_asdf(self, asdf_f, idx=None, **kwargs):

        data_obj = load_asdf(asdf_f, idx=idx, logger=self.logger)

        # set important metadata
        # TODO: is it possible to set the name without a filename?
        data_obj.set(idx=idx)
        data_obj.io = self

        return data_obj

    def load_asdf_hdu_in_fits(self, fits_f, hdu, **kwargs):
        """*** This is a special method that should only be called from
        WITHIN io_fits.py to open up ASDF-embedded-in-FITS ***
        """

        # Handle ASDF embedded in FITS (see load_hdu() in io_fits.py)
        # TODO: Populate EXTNAME, EXTVER, NAXISn in ASDF meta
        #   from HDU?
        # TODO: How to read from all the different ASDF layouts?
        # TODO: Cache the ASDF object?

        # TODO: hdu is ignored for now, but presumably this loader might
        # eventually want to check it
        with AsdfInFits.open(fits_f) as asdf_f:
            data_obj = self.load_asdf(asdf_f, logger=self.logger, **kwargs)

        # metadata will be hopefully be set back in io_fits
        return data_obj

    def load_file(self, filepath, idx=None, **kwargs):

        with asdf.open(filepath) as asdf_f:
            data_obj = load_asdf(asdf_f, idx=idx, logger=self.logger)

        # set important metadata
        name = iohelper.name_image_from_path(filepath, idx=None)
        data_obj.set(path=filepath, name=name, idx=idx,
                     image_loader=load_file)
        data_obj.io = self

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

    def load_idx(self, idx, **kwargs):
        if self._path is None:
            raise ValueError("Please call open_file() first!")

        return self.load_file(self._path, idx=idx, **kwargs)

    def load_idx_cont(self, idx_spec, loader_cont_fn, **kwargs):

        data_obj = self.load_idx(None, **kwargs)

        # call continuation function
        loader_cont_fn(data_obj)
