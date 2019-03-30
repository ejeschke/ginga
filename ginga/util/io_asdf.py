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

__all__ = ['have_asdf', 'load_file', 'load_asdf', 'ASDFFileHandler']


def load_asdf(asdf_obj, data_key='data', wcs_key='wcs', header_key='meta'):
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


def load_file(filepath, idx=None, logger=None, **kwargs):
    """
    Load an object from an ASDF file.
    See :func:`ginga.util.loader` for more info.

    """
    # see ginga.util.loader module
    opener = ASDFFileHandler(logger)
    data_obj = opener.load_file(filepath, idx=idx, **kwargs)

    return data_obj


# for backward compatibility... TO BE DEPRECATED... DON'T USE
loader = load_file


class ASDFFileHandler(object):

    def __init__(self, logger):
        self.logger = logger
        self._path = None

    def load_file(self, filepath, idx=None, **kwargs):

        # TODO: support other types, like AstroTable
        data_obj = AstroImage.AstroImage(logger=self.logger)

        # TODO: idx may contain info about what part of the file to load
        with asdf.open(filepath) as asdf_f:

            # NOTE: currently, kwargs is not compatible with load_asdf()
            data, wcs, ahdr = load_asdf(asdf_f)

            data_obj.setup_data(data, naxispath=None)

            wcsinfo = wcsmod.get_wcs_class('astropy_ape14')
            data_obj.wcs = wcsinfo.wrapper_class(logger=self.logger)
            data_obj.wcs.wcs = wcs

            if wcs is not None:
                data_obj.wcs.coordsys = wcs.output_frame.name

        # set important metadata
        name = iohelper.name_image_from_path(filepath, idx=None)
        data_obj.set(path=filepath, name=name, idx=idx,
                     image_loader=self.load_file)

        return data_obj

    def load_asdf_hdu_in_fits(self, fits_f, hdu, **kwargs):
        """*** This is a special method that should only be called from
        WITHIN io_fits.py ***
        """

        # Handle ASDF embedded in FITS (see load_hdu() in io_fits.py)
        # TODO: Populate EXTNAME, EXTVER, NAXISn in ASDF meta
        #   from HDU?
        # TODO: How to read from all the different ASDF layouts?
        # TODO: Cache the ASDF object?

        # TODO: support other types, like AstroTable?
        data_obj = AstroImage.AstroImage(logger=self.logger)

        # TODO: hdu is ignored for now, but presumably this loader might
        # eventually want to check it
        with AsdfInFits.open(fits_f) as asdf_f:
            data, wcs, ahdr = load_asdf(asdf_f, **kwargs)

            data_obj.setup_data(data, naxispath=None)

            wcsinfo = wcsmod.get_wcs_class('astropy_ape14')
            data_obj.wcs = wcsinfo.wrapper_class(logger=self.logger)
            data_obj.wcs.wcs = wcs

            if wcs is not None:
                data_obj.wcs.coordsys = wcs.output_frame.name

        # metadata will be set back in io_fits
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
