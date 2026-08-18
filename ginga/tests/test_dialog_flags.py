"""A MessageDialog should float above the window that raised it.

``Dialog`` has defaulted to ``DIALOG_FLAGS_ONTOP`` in every backend, but
``MessageDialog`` overrode that default with 0 (qt) or None (gtk3, gtk4,
pg) -- both meaning "not on top" -- so an error or warning could end up
behind the window that raised it while an ordinary dialog could not.

Checked by signature, so it needs no display and covers every backend
that imports in the environment at hand.
"""

import importlib

import pytest

from ginga.gw.widget_helpers import DIALOG_FLAGS_ONTOP

BACKENDS = ['ginga.qtw.Widgets', 'ginga.gtk3w.Widgets', 'ginga.gtk4w.Widgets',
            'ginga.web.pgw.Widgets']


def _default_flags(cls):
    import inspect
    return inspect.signature(cls.__init__).parameters['flags'].default


# the pg backend documents flags as accepted-but-unused: a browser
# dialog is a DOM overlay that already renders over the page
WINDOWED = [name for name in BACKENDS if 'pgw' not in name]


@pytest.mark.parametrize('modname', WINDOWED)
def test_message_dialog_defaults_to_on_top(modname):
    try:
        mod = importlib.import_module(modname)
    except Exception as exc:                           # pragma: no cover
        pytest.skip("%s not importable: %s" % (modname, exc))

    flags = _default_flags(mod.MessageDialog)
    assert flags is not None, "MessageDialog flags default to None"
    assert flags & DIALOG_FLAGS_ONTOP, \
        "%s.MessageDialog does not default to on-top (flags=%r)" % (modname,
                                                                    flags)


@pytest.mark.parametrize('modname', BACKENDS)
def test_message_dialog_matches_dialog(modname):
    """...and it should not diverge from Dialog again."""
    try:
        mod = importlib.import_module(modname)
    except Exception as exc:                           # pragma: no cover
        pytest.skip("%s not importable: %s" % (modname, exc))

    assert _default_flags(mod.MessageDialog) == _default_flags(mod.Dialog)
