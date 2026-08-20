"""Tests for the qt TextSource's scrolling and caret appearance.

Scrolling to a line/ref must not disturb what the caller just selected
(a search selects its match and *then* scrolls to it), and the caller
can ask for the target line to be centered rather than merely brought
into view.
"""

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    import qtpy                              # noqa: F401
except Exception:                            # pragma: no cover
    # qtpy can be installed without a usable binding, which raises
    # ImportError rather than ModuleNotFoundError
    pytest.skip("no usable qt binding", allow_module_level=True)

# Import the backend directly: ginga.gw.Widgets binds a toolkit at
# import time, so what it offers depends on whether an earlier import
# already fixed the family.
from ginga.qtw import Widgets  # noqa: E402
from ginga.qtw.QtHelp import QtGui, QTextCursor  # noqa: E402

NUM_LINES = 200


@pytest.fixture(scope='module')
def app():
    # NOTE: a second QApplication in one process comes up with no
    # screens attached, so reuse whatever another test module already
    # created rather than building a second ginga Application
    if QtGui.QApplication.instance() is None:
        Widgets.Application()
    return QtGui.QApplication.instance()


def _lay_out(widget):
    """Give a widget a size and let qt lay it out.

    Shown on its own rather than inside a window from make_window(),
    which needs a screen -- there isn't always one under the offscreen
    platform plugin.
    """
    w = widget.get_widget()
    w.resize(500, 200)
    w.show()
    QtGui.QApplication.instance().processEvents()


@pytest.fixture
def text(app):
    tw = Widgets.TextSource(editable=True, wrap='none')
    tw.set_font('Monospace', 10)
    tw.set_text("\n".join("line %03d: the quick brown fox" % i
                          for i in range(NUM_LINES)))
    _lay_out(tw)
    yield tw
    tw.get_widget().hide()


def _cursor_y(tw, ref):
    """Viewport y of the line holding `ref` (its vertical center)."""
    editor = tw.widget.get_internal_text_widget()
    cursor = QTextCursor(editor.document())
    cursor.setPosition(ref.get_offset())
    return editor.cursorRect(cursor).center().y()


def test_scrolling_to_a_ref_keeps_the_selection(text):
    start, end = text.find_all("fox")[120]
    text.set_selection_range(start, end)

    text.scroll_to_ref(start, align='center')

    assert text.has_selection()
    bounds = text.get_selection_bounds()
    assert text.get_text_range(*bounds) == "fox"


def test_scrolling_to_a_lineno_keeps_the_selection(text):
    start, end = text.find_all("quick")[120]
    text.set_selection_range(start, end)

    text.scroll_to_lineno(start.get_line(), align='center')

    assert text.has_selection()


def test_center_puts_the_line_in_the_middle_of_the_view(text):
    start, end = text.find_all("brown")[150]

    text.scroll_to_ref(start, align='center')

    editor = text.widget.get_internal_text_widget()
    middle = editor.viewport().height() // 2
    # within a line height of the middle
    assert abs(_cursor_y(text, start) - middle) <= editor.fontMetrics().height()


def test_nearest_only_scrolls_as_far_as_it_has_to(text):
    editor = text.widget.get_internal_text_widget()
    height = editor.viewport().height()
    start, end = text.find_all("brown")[150]

    text.scroll_to_ref(start, align='nearest')

    # brought into view, but at the bottom rather than the middle
    y = _cursor_y(text, start)
    assert 0 <= y <= height
    assert y > height // 2

    # a line already visible does not move the view at all
    before = editor.verticalScrollBar().value()
    text.scroll_to_lineno(start.get_line())
    assert editor.verticalScrollBar().value() == before


def test_cursor_style_defaults_to_the_toolkit_caret(text):
    editor = text.widget.get_internal_text_widget()

    assert text.get_cursor_style() == ('line', None)
    assert editor.cursorWidth() == 1


def test_setting_a_cursor_color_takes_over_the_caret(text):
    editor = text.widget.get_internal_text_widget()

    text.set_cursor_style('block', color='indianred')

    assert text.get_cursor_style() == ('block', 'indianred')
    # qt's own caret is switched off; we paint ours instead
    assert editor.cursorWidth() == 0

    text.set_cursor_style()
    assert text.get_cursor_style() == ('line', None)
    assert editor.cursorWidth() == 1


def test_a_block_caret_is_as_wide_as_the_character_under_it(text):
    editor = text.widget.get_internal_text_widget()
    text.set_cursor_style('block', color='indianred')

    text.set_cursor(text.get_ref_line_start(10))

    space = editor.fontMetrics().horizontalAdvance(' ')
    assert editor._caret_rect().width() == space

    # ... and a line caret stays narrow
    text.set_cursor_style('line', color='indianred')
    assert editor._caret_rect().width() == 2


def test_an_unknown_cursor_style_is_rejected(text):
    with pytest.raises(ValueError):
        text.set_cursor_style('underline', color='indianred')


def test_an_unknown_alignment_is_rejected(text):
    with pytest.raises(ValueError):
        text.scroll_to_lineno(10, align='middle')


# ----- the plain TextArea gets the same scrolling API ------------------

@pytest.fixture
def area(app):
    area = Widgets.TextArea(editable=True, wrap=False)
    area.set_text("\n".join("line %03d" % i for i in range(NUM_LINES)))
    _lay_out(area)
    yield area
    area.get_widget().hide()


def _area_line_y(area, lineno):
    cursor = QTextCursor(area.tw.document())
    cursor.setPosition(area.tw.document().findBlockByLineNumber(lineno).position())
    return area.tw.cursorRect(cursor).center().y()


def test_textarea_centers_a_line(area):
    area.scroll_to_lineno(150, align='center')

    middle = area.tw.viewport().height() // 2
    assert abs(_area_line_y(area, 150) - middle) <= area.tw.fontMetrics().height()


def test_textarea_nearest_only_scrolls_as_far_as_it_has_to(area):
    height = area.tw.viewport().height()
    # setting the text leaves the view at the end, so start from the top
    # and let the line be scrolled *down* to
    area.scroll_to_lineno(0, align='top')

    area.scroll_to_lineno(150)

    y = _area_line_y(area, 150)
    assert 0 <= y <= height
    assert y > height // 2

    before = area.tw.verticalScrollBar().value()
    area.scroll_to_lineno(150)
    assert area.tw.verticalScrollBar().value() == before


def test_textarea_scroll_to_end_shows_the_last_line(area):
    area.scroll_to_end()

    y = _area_line_y(area, NUM_LINES - 1)
    assert 0 <= y <= area.tw.viewport().height()


def test_textarea_rejects_an_unknown_alignment(area):
    with pytest.raises(ValueError):
        area.scroll_to_lineno(10, align='middle')
