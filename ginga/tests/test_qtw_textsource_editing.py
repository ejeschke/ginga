"""Tests for editing in the qt TextSource: undo/redo and the clipboard.

Qt's native undo stack is disabled in favour of the TextModel's, so the
widget itself has to route the Undo/Redo keys and the Undo/Redo items of
its context menu to the model.  Typing is grouped into word-sized undo
steps.  Copied text goes to the clipboard without its highlighting.
"""

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

try:
    import qtpy                              # noqa: F401
except Exception:                            # pragma: no cover
    pytest.skip("no usable qt binding", allow_module_level=True)

from ginga.qtw import Widgets  # noqa: E402
from ginga.qtw.QtHelp import QtGui, QtCore  # noqa: E402
from qtpy.QtTest import QTest  # noqa: E402
from qtpy.QtGui import QContextMenuEvent  # noqa: E402

Key = QtCore.Qt.Key
CTRL = QtCore.Qt.KeyboardModifier.ControlModifier

TEXT = "hello world\nline two\n"


@pytest.fixture(scope='module')
def app():
    if QtGui.QApplication.instance() is None:
        Widgets.Application()
    return QtGui.QApplication.instance()


@pytest.fixture
def ts(app):
    ts = Widgets.TextSource(editable=True, wrap='none')
    ts.set_text(TEXT)
    tw = ts.widget.tw
    tw.resize(400, 200)
    tw.show()
    tw.setFocus()
    app.processEvents()
    return ts


def _put_cursor(ts, pos):
    tw = ts.widget.tw
    cur = tw.textCursor()
    cur.setPosition(pos)
    tw.setTextCursor(cur)


def _undo_steps(ts):
    return [(old, new) for _s, old, new, _b, _a in ts.widget._undo_stack]


def _menu_state(ts, monkeypatch, trigger=None):
    """Open the context menu; return {action name: enabled}, optionally
    triggering one of the actions."""
    seen = {}

    def fake_exec(menu, *args):
        for action in menu.actions():
            name = action.objectName()
            if name in ('edit-undo', 'edit-redo'):
                seen[name] = action.isEnabled()
                if name == trigger:
                    action.trigger()

    monkeypatch.setattr(QtGui.QMenu, 'exec', fake_exec)
    vp = ts.widget.tw.viewport()
    pt = QtCore.QPoint(5, 5)
    ev = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pt,
                           vp.mapToGlobal(pt))
    QtGui.QApplication.sendEvent(vp, ev)
    return seen


def test_typing_is_grouped_by_word(ts):
    _put_cursor(ts, 5)
    QTest.keyClicks(ts.widget.tw, "ab  cd")
    assert _undo_steps(ts) == [('', 'ab  '), ('', 'cd')]


def test_a_newline_is_a_step_of_its_own(ts):
    _put_cursor(ts, 5)
    QTest.keyClicks(ts.widget.tw, "ab")
    QTest.keyClick(ts.widget.tw, Key.Key_Return)
    QTest.keyClicks(ts.widget.tw, "cd")
    assert _undo_steps(ts) == [('', 'ab'), ('', '\n'), ('', 'cd')]


def test_runs_of_backspace_and_delete_are_one_step_each(ts):
    _put_cursor(ts, 5)
    for _ in range(3):
        QTest.keyClick(ts.widget.tw, Key.Key_Backspace)
    _put_cursor(ts, 0)
    for _ in range(2):
        QTest.keyClick(ts.widget.tw, Key.Key_Delete)
    assert _undo_steps(ts) == [('llo', ''), ('he', '')]


def test_ctrl_z_and_ctrl_y_undo_and_redo(ts):
    tw = ts.widget.tw
    _put_cursor(ts, 5)
    QTest.keyClicks(tw, "ab cd")
    edited = ts.get_text()
    # bounded loops: if the keys were not routed to the model these would
    # never terminate
    for _ in range(20):
        QTest.keyClick(tw, Key.Key_Z, CTRL)
    assert ts.get_text() == TEXT
    for _ in range(20):
        QTest.keyClick(tw, Key.Key_Y, CTRL)
    assert ts.get_text() == edited
    assert tw.toPlainText() == ts.get_text()


def test_context_menu_undo_redo_follow_the_model(ts, monkeypatch):
    assert _menu_state(ts, monkeypatch) == {'edit-undo': False,
                                            'edit-redo': False}
    _put_cursor(ts, 5)
    QTest.keyClicks(ts.widget.tw, "ab")
    assert _menu_state(ts, monkeypatch, trigger='edit-undo') == {
        'edit-undo': True, 'edit-redo': False}
    assert ts.get_text() == TEXT
    assert _menu_state(ts, monkeypatch, trigger='edit-redo') == {
        'edit-undo': False, 'edit-redo': True}
    assert ts.get_text().startswith("helloab ")


def test_a_typed_edit_in_a_run_of_equal_characters_lands_at_the_cursor(ts):
    # Typing a space before "  bb" could be diffed at offset 2, 3 or 4;
    # refs and tags must see it where it was typed.
    ts.set_text("aa  bb")
    ref = ts.create_ref(3, gravity='left')
    _put_cursor(ts, 2)
    QTest.keyClick(ts.widget.tw, Key.Key_Space)
    assert ts.get_text() == "aa   bb"
    assert ref.get_offset() == 4


def test_copy_and_cut_put_plain_text_only_on_the_clipboard(ts):
    tw = ts.widget.tw
    ts.create_tag('red', foreground='red')
    ts.apply_tag('red', ts.create_ref(0), ts.create_ref(5))
    clipboard = QtGui.QApplication.clipboard()
    cur = tw.textCursor()
    cur.setPosition(0)
    cur.setPosition(5, cur.MoveMode.KeepAnchor)
    tw.setTextCursor(cur)
    QTest.keyClick(tw, Key.Key_C, CTRL)
    assert clipboard.text() == "hello"
    assert not clipboard.mimeData().hasHtml()
    QTest.keyClick(tw, Key.Key_X, CTRL)
    assert clipboard.text() == "hello"
    assert not clipboard.mimeData().hasHtml()
    assert ts.get_text() == TEXT[5:]
    QTest.keyClick(tw, Key.Key_V, CTRL)
    assert ts.get_text() == TEXT
    assert tw.toPlainText() == TEXT
