#
# toolkit.py -- module for customizing Ginga GUI toolkit version
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import importlib.util

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
        elif name == 'gtk4':
            name = 'gtk4'
            family = 'gtk4'
        assert name in ['gtk3', 'gtk4'], \
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
    return ['qt5', 'qt6', 'pyside2', 'pyside6', 'gtk3', 'pg']


def _installed(name):
    """Return True if module `name` is importable, without importing it."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        # a parent package that fails while locating the spec
        return False


def choose():
    """Select an available GUI toolkit and register it via use().

    Uses ``importlib.util.find_spec`` to check which backend is present
    before committing, so we don't import a backend wrapper (and
    initialize its whole GUI stack) merely to discover it is unavailable.
    The chosen backend is then registered so ``toolkit`` and ``family``
    are fully resolved.
    """
    # Qt is preferred.  find_spec tells us a binding is present without
    # importing anything; importing ginga.qtw.QtHelp then lets qtpy pick
    # the concrete binding (qt5/qt6/pyside2/pyside6, honoring $QT_API) and
    # record it through use().  If a binding's spec is present but it
    # won't actually import, fall through to the next toolkit.
    if any(_installed(mod) for mod in
           ('PyQt5', 'PyQt6', 'PySide2', 'PySide6')):
        try:
            from ginga.qtw import QtHelp  # noqa
            return
        except ImportError:
            pass

    # GTK next.  Both GTK3 and GTK4 are driven by PyGObject ('gi'), so
    # find_spec alone can't tell them apart; ask gi's typelib repository
    # which Gtk versions are installed (this loads the light 'gi' module
    # but not Gtk itself).  Prefer GTK3, matching the previous order.
    if _installed('gi'):
        import gi
        versions = set(gi.Repository.get_default().enumerate_versions('Gtk'))
        if '3.0' in versions:
            use('gtk3')
            return
        if '4.0' in versions:
            use('gtk4')
            return

    # Web (pgwidgets) backend as a last resort.  The remote/websocket
    # backend needs pgwidgets-python (imported as ``pgwidgets``), which in
    # turn is built on pgwidgets-js (``pgwidgets_js``); require both.
    if _installed('pgwidgets') and _installed('pgwidgets_js'):
        use('pg')
        return

    raise ImportError("no supported GUI toolkit (qt, gtk or pg) found")

# END
