#
# wcsmod -- module wrapper for WCS calculations.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
We are fortunate to have several possible choices for a python WCS package
compatible with Ginga: astlib, kapteyn, starlink and astropy.
kapteyn and astropy wrap Mark Calabretta's "WCSLIB", astLib wraps
Jessica Mink's "wcstools", and I'm not sure what starlink uses (their own?).

Note that astlib requires pyfits (or astropy) in order to create a WCS
object from a FITS header.

To force the use of one, do:

.. code-block:: python

    from ginga.util import wcsmod
    wcsmod.use('kapteyn')

before you load any images.  Otherwise Ginga will try to pick one for
you.

Note that you can register custom WCS types using:

.. code-block:: python

    from ginga.util.wcsmod.common import register_wcs
    register_wcs('mywcs', MyWCSClass, list_of_coord_types)

Look at the implemented WCS wrappers for details.
"""
import sys
import os.path
import glob

from ginga.misc.ModuleManager import my_import

from . import common

__all__ = ['get_wcs_class']

# Module variables that get configured at module load time
# or when use() is called
wcs_configured = False

WCS = None
"""Alias to the chosen WCS system."""

# Holds names of coordinate types
coord_types = []

display_types = ['sexagesimal', 'degrees']

# try to load them in this order until we find one that works.
# If none can be loaded, we default to the BareBones dummy WCS
wcs_try_order = ('astropy', 'astropy_ape14', 'kapteyn', 'starlink', 'astlib',
                 'barebones')

wcs_home = os.path.split(sys.modules[__name__].__file__)[0]


def use(wcspkg, raise_err=True):
    """Choose WCS package."""
    global coord_types, wcs_configured, WCS

    if wcspkg not in common.custom_wcs:
        # Try to dynamically load WCS
        modname = 'wcs_%s' % (wcspkg)
        path = os.path.join(wcs_home, '%s.py' % (modname))
        try:
            my_import(modname, path)
        except ImportError as e:
            if raise_err:
                raise e
            return False

    if wcspkg in common.custom_wcs:
        bnch = common.custom_wcs[wcspkg]
        WCS = bnch.wrapper_class
        coord_types = bnch.coord_types
        wcs_configured = True
        return True

    return False


# configure at least one WCS wrapper

if not wcs_configured:
    # Try some preconfigured names
    for name in wcs_try_order:
        if use(name, raise_err=False):
            break

if not wcs_configured:
    wcs_path = os.path.join(wcs_home, 'wcs_*.py')

    # look up WCS wrappers we have in this directory
    for path in glob.glob(wcs_path):
        dirname, filename = os.path.split(path)
        modname, ext = os.path.splitext(filename)
        modname = modname[4:]   # strip off "wcs_"
        if use(name, raise_err=False):
            break


def get_wcs_wrappers():
    return list(common.custom_wcs.keys())


def get_wcs_class(name):
    """Get a WCS class corresponding to the registered name.
    Will raise a KeyError if a class of the given name does not exist.
    """
    return common.custom_wcs[name]

# END
