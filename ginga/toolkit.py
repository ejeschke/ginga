#
# toolkit.py -- module for customizing Ginga GUI toolkit version
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

toolkit = 'choose'
family = None


class ToolKitError(Exception):
    pass


def use(name):
    """
    Set the name of the GUI toolkit we should use.
    """
    global toolkit, family

    name = name.lower()

    if name.startswith('choose'):
        pass

    elif name.startswith('qt') or name.startswith('pyside'):
        family = 'qt'
        if name == 'qt':
            name = 'qt5'
        if name not in ('qt5', 'pyside2', 'qt6', 'pyside6'):
            raise ToolKitError("ToolKit '%s' not supported!" % (name))

    elif name.startswith('gtk'):
        # default for "gtk" is gtk3
        if name in ('gtk', 'gtk3'):
            name = 'gtk3'
            family = 'gtk3'
        assert name in ['gtk3'], \
            ToolKitError("ToolKit '%s' not supported!" % (name))

    elif name.startswith('tk'):
        family = 'tk'
        assert name in ('tk', ), \
            ToolKitError("ToolKit '%s' not supported!" % (name))

    elif name.startswith('pg'):
        family = 'pg'
        assert name in ('pg', ), \
            ToolKitError("ToolKit '%s' not supported!" % (name))

    else:
        ToolKitError("ToolKit '%s' not supported!" % (name))

    toolkit = name


def get_toolkit():
    return toolkit


def get_family():
    return family


def get_rv_toolkits():
    """Returns a list of reference viewer supported toolkits."""
    return ['qt4', 'qt5', 'pyside', 'pyside2', 'gtk3', 'pg']


def choose():
    try:
        from ginga.qtw import QtHelp  # noqa
    except ImportError:
        try:
            from ginga.gtkw3 import GtkHelp  # noqa
        except ImportError:
            raise ImportError("qt or gtk variants not found")

# END
