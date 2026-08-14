"""Menu icons in the gtk backends.

GTK4 renders a menu from a ``Gio.Menu`` model, so an item's icon is a
``GIcon`` rather than a widget.  Icons inside menus do render; a menu
*bar* entry shows its label only, and keeping the model-driven
``GtkPopoverMenuBar`` is deliberate -- a row of ``GtkMenuButton``s could
show an icon there but loses press-drag-release selection across the
bar.
"""

import importlib
import os

import pytest

pytest.importorskip('gi')

if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
    pytest.skip("gtk needs a display", allow_module_level=True)

Widgets = None
for _modname in ('ginga.gtk3w.Widgets', 'ginga.gtk4w.Widgets'):
    try:
        Widgets = importlib.import_module(_modname)
        break
    except Exception:                                  # pragma: no cover
        continue
if Widgets is None:                                    # pragma: no cover
    pytest.skip("no gtk backend importable", allow_module_level=True)

is_gtk4 = 'gtk4' in Widgets.__name__
needs_gtk4 = pytest.mark.skipif(not is_gtk4, reason="gtk4 menu model only")

if is_gtk4:
    from gi.repository import Gtk, GLib

import ginga                                           # noqa: E402

ICON = os.path.join(os.path.dirname(ginga.__file__), 'icons', 'language.svg')


@pytest.fixture(scope='module')
def app():
    return Widgets.Application()


def _settle(ms=350):
    loop = GLib.MainLoop()
    GLib.timeout_add(ms, lambda: (loop.quit(), False)[1])
    loop.run()


def _walk(widget, out=None):
    out = [] if out is None else out
    out.append(widget)
    child = widget.get_first_child()
    while child is not None:
        _walk(child, out)
        child = child.get_next_sibling()
    return out


def _menubar(app):
    top = app.make_window("menus")
    vbox = Widgets.VBox()
    menubar = Widgets.Menubar()
    vbox.add_widget(menubar, stretch=0)
    vbox.add_widget(Widgets.Label('body'), stretch=1)
    top.set_widget(vbox)
    top.resize(500, 250)
    top.show()
    _settle(400)
    return top, menubar


@needs_gtk4
def test_menu_items_carry_icons(app):
    assert os.path.exists(ICON)
    top, menubar = _menubar(app)
    menu = menubar.add_name("Language", iconpath=ICON, icon_only=True)
    item = menu.add_name("English", iconpath=ICON)
    sub = menu.add_menu("More", iconpath=ICON)
    sub.add_name("Deutsch")
    _settle(200)

    assert item.get_widget().get_attribute_value('icon', None) is not None, \
        "the menu item model carries no icon"

    popover = menu.get_widget()
    popover.set_parent(menubar.get_widget())
    popover.popup()
    _settle(400)
    images = [w for w in _walk(popover) if isinstance(w, Gtk.Image)]
    popover.popdown()
    assert len(images) >= 2, \
        "menu items did not render their icons (%d images)" % (len(images),)


@needs_gtk4
def test_set_icon_after_the_fact(app):
    top, menubar = _menubar(app)
    menu = menubar.add_name("Edit")
    item = menu.add_name("Cut")
    assert item.get_widget().get_attribute_value('icon', None) is None
    item.set_icon(ICON)
    assert item.get_widget().get_attribute_value('icon', None) is not None


@needs_gtk4
def test_menubar_stays_model_driven(app):
    """A menubar entry keeps its text, and the bar keeps its behaviour.

    Swapping GtkPopoverMenuBar for GtkMenuButtons would let the entry
    show an icon, at the cost of press-drag-release selection across
    the bar -- measured, and not worth it.
    """
    top, menubar = _menubar(app)
    menubar.add_name("File").add_name("Open")
    menubar.add_name("Language", iconpath=ICON, icon_only=True)
    _settle(200)

    bar = menubar.get_widget()
    assert isinstance(bar, Gtk.PopoverMenuBar)
    labels = [w.get_label() for w in _walk(bar) if isinstance(w, Gtk.Label)]
    assert 'Language' in labels, \
        "an icon-only bar entry must keep its text: %r" % (labels,)
    assert 'File' in labels
