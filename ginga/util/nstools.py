#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Tools for shared Ginga namespace.

These can be used by other developer writing plugins
under the same Ginga namespace but in a separate package.
"""

# STDLIB
import os


# Like astropy.utils.data.get_pkg_data_filename() but not quite.
def get_pkg_data_filename(data_name, package_name='ginga'):
    """Get package data filename in shared namespace.

    Parameters
    ----------
    data_name : str
        Data path and filename. For example: ``'data/mydata.txt'``

    package_name : str
        The default value of ``'ginga'`` assumes data files
        are in ``ginga/data`` directory.

    Returns
    -------
    data_fn : str
        Path to package data filename, if found.

    """
    data_name = os.path.normpath(data_name)
    data_fn = ''

    # Traverse through packages in shared namespace.
    # Get the first match.
    for path in __import__(package_name).__path__:
        fn = os.path.join(path, data_name)
        if os.path.isfile(fn):
            data_fn = fn
            break

    return data_fn


def find_custom_ginga_plugins(toolkit, include_home=True):
    """Return a list of custom plugins in Ginga namespace.
    Plugins that are part of Ginga's core distribution are
    ignored.

    This assumes that shared namespace plugins only exist
    in the following sub-directories:

    1. ``ginga/gtk/plugins``
    2. ``ginga/qt/plugins``
    3. ``ginga/misc/plugins``

    GTK and Qt plugins are mutually exclusive, while
    miscellaneous plugins can be used by either one.

    Parameters
    ----------
    toolkit : {'gtk', 'qt'}
        Toolkit to use. ``'misc'`` is automatically included
        regardless.

    include_home : bool
        Also search in ``~/.ginga/plugins`` directory.

    Returns
    -------
    plugins : dict
        Dictionary mapping module prefix to associated custom
        plugins.

    Raises
    ------
    ValueError
        Invalid toolkit.

    """
    toolkit = toolkit.lower()
    if toolkit not in ('gtk', 'qt'):
        raise ValueError('Toolkit must be GTK or Qt')

    plugins = {}
    paths = __import__('ginga').__path__

    # No custom plugins
    if len(paths) < 2:
        return plugins

    # Identify core distribution path
    coremod = __import__('ginga.Control')  # Only core has this?
    corepath = os.path.dirname(coremod.__file__)

    # Find custom plugins in shared namespace.
    # TODO: How to separate global and local plugins?
    for path in paths:
        if path == corepath:
            continue

        for s in os.walk(path):
            dirpath = s[0]
            if 'plugins' not in dirpath:
                continue
            if toolkit in dirpath:
                pfx = 'ginga.{0}.plugins'.format(toolkit)
            elif 'misc' in dirpath:
                pfx = 'ginga.misc.plugins'
            else:
                continue

            # Extract plugin names (*py and *pyc give duplicates)
            pnames = set(os.path.splitext(fn)[0] for fn in s[-1]
                         if '__init__' not in fn)

            # Exclude empty list
            if len(pnames) == 0:
                continue

            # Update dictionary
            if pfx in plugins:
                plugins[pfx].union(pnames)
            else:
                plugins[pfx] = pnames

    # Search HOME (*py and *pyc give duplicates)
    if include_home:
        home = os.path.join(os.path.expanduser('~'), '.ginga', 'plugins')
        if os.path.isdir(home):
            pnames = set(os.path.splitext(fn)[0] for fn in os.listdir(home))
            if len(pnames) > 0:  # Exclude empty list
                plugins[''] = pnames

    # Convert set to sorted list
    for pfx in plugins:
        plugins[pfx] = sorted(plugins[pfx])

    return plugins

# END
