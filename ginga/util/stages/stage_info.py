# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
import os.path
import glob
import importlib
import inspect

from . import base


def get_stage_catalog(logger):
    """Return a dictionary containing all the stages that could be loaded.
    """
    stage_catalog = dict()
    thisdir, _ = os.path.split(base.__file__)
    for pypath in glob.glob(os.path.join(thisdir, "*.py")):
        _, pyfile = os.path.split(pypath)
        modname, _ext = os.path.splitext(pyfile)
        try:
            mod = importlib.import_module('ginga.util.stages.' + modname)

        except ImportError as e:
            logger.error("Couldn't import '{}': {}".format(modname, e))
            continue

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (inspect.isclass(attr) and issubclass(attr, base.Stage) and
                attr is not base.Stage):
                name = getattr(attr, '_stagename', str(attr).lower())
                if not name.startswith('viewer-'):
                    # for now, do not include viewer
                    stage_catalog[name] = attr

    return stage_catalog
