#
# loader.py -- upper level routines used to load data
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch
from ginga.util import iohelper, io_fits, io_rgb, io_asdf


def load_data(filespec, idx=None, logger=None, **kwargs):
    """Load data from a file.

    This call is used to load a data item from a filespec (path or URL)

    Parameters
    ----------
    filespec : str
        The path of the file to load (can be a URL).

    idx : int or string (optional)
        The index or name of the data unit in the file (e.g. an HDU name)

    logger : python logger (optional)
        A logger to record progress opening the item

    All other keyword parameters are passed to the opener chosen for
    the file type.

    Returns
    -------
    data_obj : a data object for a ginga viewer

    """
    global loader_registry

    info = iohelper.get_fileinfo(filespec)
    filepath = info.filepath

    if idx is None:
        idx = info.numhdu

    # Assume type to be a FITS image unless the MIME association says
    # it is something different.
    try:
        typ, subtyp = iohelper.guess_filetype(filepath)

    except Exception as e:
        if logger is not None:
            logger.warning("error determining file type: %s; "
                           "assuming 'image/fits'" % (str(e)))
        # Can't determine file type: assume and attempt FITS
        typ, subtyp = 'image', 'fits'

    if logger is not None:
        logger.debug("assuming file type: %s/%s'" % (typ, subtyp))
    try:
        loader_info = loader_registry['%s/%s' % (typ, subtyp)]
        data_loader = loader_info.loader

    except KeyError:
        # for now, assume that this is an unrecognized FITS file
        data_loader = load_fits

    data_obj = data_loader(filepath, idx=idx, logger=logger,
                           **kwargs)
    return data_obj


# For consistency with specific format loader modules (io_fits, etc).
load_file = load_data


# This contains a registry of upper-level loaders with their secondary
# loading functions
#
loader_registry = {}


def add_loader(mimetype, loader, opener):
    global loader_registry
    # TODO: can/should we store other preferences/customizations along
    # with the loader?
    loader_registry[mimetype] = Bunch.Bunch(loader=loader,
                                            opener=opener,
                                            mimetype=mimetype)


def get_opener(mimetype):
    bnch = loader_registry[mimetype]
    return bnch.opener


# built ins

# ### FITS ###
for mimetype in ['image/fits', 'image/x-fits']:
    add_loader(mimetype, io_fits.load_file, io_fits.fitsLoaderClass)

# ### ASDF ###
for mimetype in ['image/asdf']:
    add_loader(mimetype, io_asdf.load_file, io_asdf.ASDFFileHandler)

# ### RGB ###
for mimetype in ['image/jpeg', 'image/png', 'image/tiff', 'image/gif',
                 'image/ppm', 'image/pnm', 'image/pbm']:
    add_loader(mimetype, io_rgb.load_file, io_rgb.RGBFileHandler)
