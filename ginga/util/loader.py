#
# loader.py -- upper level routines used to load data
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Bunch
from ginga.util import iohelper, compat


# Holds all openers keyed by name
loader_registry = dict()


# Holds all openers keyed by MIME type
loader_by_mimetype = dict()


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
        msg = "error determining file type of '{}': {}".format(filepath, e)
        if logger is not None:
            logger.warning(msg)
        raise ValueError(msg)

    mimetype = '%s/%s' % (typ, subtyp)
    logger.debug("determined MIME type: {}'".format(mimetype))

    openers = get_openers(mimetype)
    if len(openers) == 0:
        msg = "No openers found for type '{}'".format(mimetype)
        if logger is not None:
            logger.warning(msg)
        raise ValueError(msg)

    opener = openers[0].opener(logger)
    with opener.open_file(filepath) as opn_f:
        data_obj = opener.load_idx(idx, **kwargs)

    return data_obj


# For consistency with specific format loader modules (io_fits, etc).
load_file = load_data


def add_opener(opener, mimetypes, priority=0, note=''):
    """Add an opener to the registry of file openers.

    Parameters
    ----------
    opener : subclass of `~ginga.util.io.io_base.BaseIOHandler`
        a class that implements an opener

    mimetypes : list of str
        a sequence of the MIME types this opener can handle

    priority : int
        a priority that ranks this opener compared to others registered
        for the same MIME types.  The lower the number (negative ok) the
        higher the priority.  Default: 0

    note : str
        a short note that will be displayed to describe the opener
        in GUIs
    """
    global loader_by_mimetype, loader_registry
    if opener.name in loader_registry:
        loader_rec = loader_registry[opener.name]
    else:
        loader_rec = Bunch.Bunch(name=opener.name, opener=opener,
                                 mimetypes=mimetypes, priority=priority,
                                 note=note)
        loader_registry[opener.name] = loader_rec

    for mimetype in mimetypes:
        bnchs = loader_by_mimetype.setdefault(mimetype, [])
        if loader_rec not in bnchs:
            bnchs.append(loader_rec)
            bnchs.sort(key=lambda bnch: bnch.priority)


def get_opener(name):
    """Returns the opener named by `name`
    """
    global loader_registry
    return loader_registry[name]


def get_openers(mimetype):
    """Returns a list of openers that are registered that can open `mimetype`
    files, with all but the best (matching) priority removed.
    """
    global loader_by_mimetype
    bnchs = loader_by_mimetype.setdefault(mimetype, [])
    if len(bnchs) <= 1:
        return bnchs

    # if there is more than one possible opener, return the list of
    # those that have the best (i.e. lowest) equal priority
    priority = min([bnch.priority for bnch in bnchs])
    return [bnch for bnch in bnchs if bnch.priority <= priority]


def get_all_openers():
    """Return a sequence of all known openers.
    """
    return loader_registry.values()


def discover_loaders():
    group = 'ginga_loaders'
    discovered_loaders = compat.ep_get(group)
    for entry_point in discovered_loaders:
        try:
            opener_class = entry_point.load()
            try:
                opener_class.check_availability()
            except Exception as e:
                continue

            add_opener(opener_class, opener_class.mimetypes,
                       note=opener_class.__doc__)

        except Exception as e:
            print("Error trying to load entry point %s: %s" % (
                str(entry_point), str(e)))


if len(loader_registry) == 0:
    discover_loaders()
