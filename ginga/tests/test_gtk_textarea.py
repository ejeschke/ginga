"""Tests for TextArea scrolling in the gtk backends.

Only one GTK major version can be loaded into a process, so this module
uses whichever of gtk3/gtk4 is importable -- run it in each environment
to cover both.  Everything is skipped when gi or a display is missing.
"""

import importlib
import os

import pytest

pytest.importorskip('gi')

if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
    pytest.skip("gtk needs a display", allow_module_level=True)

# Import a backend directly rather than through ginga.gw.Widgets, which
# binds a toolkit at import time.
Widgets = None
for _modname in ('ginga.gtk3w.Widgets', 'ginga.gtk4w.Widgets'):
    try:
        Widgets = importlib.import_module(_modname)
        break
    except Exception:                                  # pragma: no cover
        continue
if Widgets is None:                                    # pragma: no cover
    pytest.skip("no gtk backend importable", allow_module_level=True)

from gi.repository import GLib            # noqa: E402

NUM_LINES = 200


def _pump():
    """Let gtk lay the view out; scroll_to_mark() is queued until then."""
    ctx = GLib.MainContext.default()
    for i in range(200):
        while ctx.pending():
            ctx.iteration(False)


@pytest.fixture(scope='module')
def app():
    return Widgets.Application()


@pytest.fixture
def area(app):
    top = app.make_window("test")
    area = Widgets.TextArea(editable=True, wrap=False)
    top.set_widget(area)
    top.resize(500, 200)
    area.set_text("\n".join("line %03d" % i for i in range(NUM_LINES)))
    top.show()
    _pump()
    yield area
    top.hide()


def _line_iter(area, lineno):
    buf = area.tw.get_buffer()
    res = buf.get_iter_at_line(lineno)
    # gtk4 returns a (found, iter) tuple, gtk3 just the iter
    return res[1] if isinstance(res, tuple) else res


def _line_y(area, lineno):
    """Vertical offset of a line within the view, in buffer coordinates."""
    rect = area.tw.get_iter_location(_line_iter(area, lineno))
    return rect.y + rect.height // 2


def _visible(area):
    rect = area.tw.get_visible_rect()
    return (rect.y, rect.y + rect.height)


def test_center_puts_the_line_in_the_middle_of_the_view(area):
    area.scroll_to_lineno(150, align='center')
    _pump()

    top, bottom = _visible(area)
    middle = (top + bottom) // 2
    height = area.tw.get_iter_location(_line_iter(area, 150)).height
    assert abs(_line_y(area, 150) - middle) <= 2 * height


def test_nearest_only_scrolls_as_far_as_it_has_to(area):
    # start at the top, so the line has to be scrolled *down* to
    area.scroll_to_lineno(0, align='top')
    _pump()

    area.scroll_to_lineno(150, align='nearest')
    _pump()

    top, bottom = _visible(area)
    y = _line_y(area, 150)
    # in view, but at the bottom rather than the middle
    assert top <= y <= bottom
    assert y > (top + bottom) // 2

    # a line already visible does not move the view at all
    before = _visible(area)
    area.scroll_to_lineno(150)
    _pump()
    assert _visible(area) == before


def test_top_puts_the_line_at_the_top_of_the_view(area):
    area.scroll_to_lineno(150, align='top')
    _pump()

    top, bottom = _visible(area)
    height = area.tw.get_iter_location(_line_iter(area, 150)).height
    assert abs(_line_y(area, 150) - top) <= 2 * height


def test_scroll_to_end_shows_the_last_line(area):
    area.scroll_to_end()
    _pump()

    top, bottom = _visible(area)
    assert top <= _line_y(area, NUM_LINES - 1) <= bottom


def test_a_lineno_past_the_end_is_clamped(area):
    area.scroll_to_lineno(NUM_LINES * 2, align='center')
    _pump()

    top, bottom = _visible(area)
    assert top <= _line_y(area, NUM_LINES - 1) <= bottom


def test_an_unknown_alignment_is_rejected(area):
    with pytest.raises(ValueError):
        area.scroll_to_lineno(10, align='middle')


def test_the_history_limit_trims_from_the_top(area):
    """set_limit() drops the oldest lines (gtk4's get_iter_at_line()
    returns a tuple, which this path has to unpack)."""
    area.set_limit(20)
    area.append_text("\n".join("extra %d" % i for i in range(5)))

    text = area.get_text()
    assert text is None or "line 000" not in text
