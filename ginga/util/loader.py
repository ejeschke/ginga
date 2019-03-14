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


def get_fileinfo(self, filespec, dldir=None):
    """Break down a file specification into its components.

    Parameters
    ----------
    filespec : str
        The path of the file to load (can be a URL).

    dldir

    Returns
    -------
    res : `~ginga.misc.Bunch.Bunch`

    """
    if dldir is None:
        dldir = self.tmpdir

    # Get information about this file/URL
    info = iohelper.get_fileinfo(filespec, cache_dir=dldir)


# NOTE: for loader functions, kwargs can include 'idx', 'logger' and
#    loader-specific parameters like
def load_rgb(filepath, logger=None, **kwargs):
    loader = io_rgb.get_rgbloader(logger=logger)
    image = loader.load_file(filepath, **kwargs)
    return image


def load_fits(filepath, logger=None, **kwargs):
    loader = io_fits.get_fitsloader(logger=logger)
    numhdu = kwargs.pop('idx', None)
    image = loader.load_file(filepath, numhdu=numhdu, **kwargs)
    return image


def load_asdf(filepath, logger=None, **kwargs):
    from ginga.util import io_asdf
    data_obj = io_asdf.loader(filepath, logger, **kwargs)
    return data_obj


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
lc = io_fits.fitsLoaderClass
from ginga.AstroImage import AstroImage
lc.register_type('image', AstroImage)
from ginga.table.AstroTable import AstroTable
lc.register_type('table', AstroTable)

for mimetype in ['image/fits', 'image/x-fits']:
    add_loader(mimetype, load_fits, lc)

lc = io_asdf.ASDFFileHandler
for mimetype in ['image/asdf']:
    add_loader(mimetype, load_asdf, lc)

# ### RGB ###
lc = io_rgb.RGBFileHandler
for mimetype in ['image/jpeg', 'image/png', 'image/tiff', 'image/gif',
                 'image/ppm', 'image/pnm', 'image/pbm']:
    add_loader(mimetype, load_rgb, lc)
