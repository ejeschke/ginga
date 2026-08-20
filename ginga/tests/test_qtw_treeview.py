"""Tests for the qt TreeView's handling of interior-row values.

An interior (parent) row may carry column data of its own.  Columns it
says nothing about stay blank and the first falls back to the node's
key, so a tree that supplies no interior values renders exactly as it
always did.
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
from ginga.qtw.QtHelp import QtGui  # noqa: E402


@pytest.fixture(scope='module')
def app():
    # NOTE: a second QApplication in one process comes up with no
    # screens attached, so reuse whatever another test module already
    # created rather than building a second ginga Application
    if QtGui.QApplication.instance() is None:
        Widgets.Application()
    return QtGui.QApplication.instance()


@pytest.fixture
def tree(app):
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Grade', 'grade'),
                      ('Seeing', 'seeing')], 2, 'name')
    return tree


def _row(tree, path):
    item = tree._path_to_item(path)
    return [item.text(i) for i in range(len(tree.datakeys))]


def test_interior_without_values_shows_its_key(tree):
    """The pre-existing behaviour, guarded."""
    tree.set_tree({'ob1': {'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    assert _row(tree, ['ob1']) == ['ob1', '', '']


def test_interior_values_inline(tree):
    """Primitives alongside the child dicts are the interior's own."""
    tree.set_tree({'ob1': {'name': 'OB-042', 'grade': 'A',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    assert _row(tree, ['ob1']) == ['OB-042', 'A', '']
    assert _row(tree, ['ob1', 'e1']) == ['e1', '', '0.6']


def test_interior_values_sentinel(tree):
    tree.set_tree({'ob1': {'__values__': {'name': 'OB-042', 'grade': 'A'},
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    assert _row(tree, ['ob1']) == ['OB-042', 'A', '']


def test_values_never_become_a_row(tree):
    """The bug this fixes: __values__ rendered as a child row, and the
    interior's data was not shown on the interior."""
    tree.set_tree({'ob1': {'__values__': {'name': 'OB-042'},
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    item = tree._path_to_item(['ob1'])
    kids = [item.child(i).text(0) for i in range(item.childCount())]
    assert kids == ['e1']
    assert '__values__' not in tree.shadow['ob1'].node


def test_inline_values_never_become_a_row(tree):
    tree.set_tree({'ob1': {'name': 'OB-042', 'grade': 'A',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    item = tree._path_to_item(['ob1'])
    kids = [item.child(i).text(0) for i in range(item.childCount())]
    assert kids == ['e1']


def test_update_tree_refreshes_interior_values(tree):
    tree.set_tree({'ob1': {'name': 'OB-042', 'grade': 'A',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    tree.update_tree({'ob1': {'name': 'OB-042', 'grade': 'B',
                              'e1': {'name': 'e1', 'grade': '',
                                     'seeing': '1.4'}}})
    assert _row(tree, ['ob1']) == ['OB-042', 'B', '']
    assert _row(tree, ['ob1', 'e1'])[2] == '1.4'


def test_getters_do_not_leak_the_sentinel(tree):
    """get_* results are iterated as children by existing callers, so
    they keep the shape they have always had."""
    tree.set_tree({'ob1': {'__values__': {'name': 'OB-042'},
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    res = tree.get_children()
    assert list(res.keys()) == ['ob1']
    assert '__values__' not in res['ob1']


def test_interior_colours_still_resolve(tree):
    """Interior rows are also a colour target."""
    from ginga.qtw.QtHelp import QtCore
    tree.set_tree({'ob1': {'name': 'OB-042',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    tree.set_cell_color(['ob1'], 'grade', fg='red')
    item = tree._path_to_item(['ob1'])
    idx = tree.datakeys.index('grade')
    assert item.data(idx, QtCore.Qt.ForegroundRole) is not None


# ----- per-column editing -------------------------------------------

def _editor(tree, path, col_key):
    """The editor Qt would create for a cell, or None if it refuses."""
    from ginga.qtw.QtHelp import QtGui
    item = tree._path_to_item(path)
    col = tree.datakeys.index(col_key)
    idx = tree.widget.indexFromItem(item, col)
    delegate = tree.widget.itemDelegate()
    editor = delegate.createEditor(tree.widget, QtGui.QStyleOptionViewItem(),
                                   idx)
    if editor is not None:
        editor.deleteLater()
    return editor


@pytest.fixture
def edit_tree(app):
    tree = Widgets.TreeView()
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='Seeing', key='seeing'),
        dict(label='Note', key='note', editable=True),
        dict(label='QA', key='qa', widget='combobox',
             choices=['', 'Good', 'Bad']),
    ], 2, 'name')
    # the interior supplies note and qa; the leaf supplies only note
    tree.set_tree({'ob1': {'name': 'OB-042', 'note': '', 'qa': 'Good',
                           'e1': {'name': 'e1', 'seeing': '0.6',
                                  'note': 'hi'}}})
    return tree


def test_only_editable_columns_get_an_editor(edit_tree):
    assert _editor(edit_tree, ['ob1'], 'note') is not None
    assert _editor(edit_tree, ['ob1'], 'name') is None
    assert _editor(edit_tree, ['ob1', 'e1'], 'seeing') is None


def _cell_widget(tree, path, col_key):
    item = tree._path_to_item(path)
    return tree.widget.itemWidget(item, tree.datakeys.index(col_key))


def test_widget_column_shows_a_live_control(edit_tree):
    """The control sits in the cell ready to use, as on the pg backend
    and the qt TableView -- not hidden behind a double-click."""
    from ginga.qtw.QtHelp import QtGui
    combo = _cell_widget(edit_tree, ['ob1'], 'qa')
    assert isinstance(combo, QtGui.QComboBox)
    assert [combo.itemText(i) for i in range(combo.count())] == \
        ['', 'Good', 'Bad']
    assert combo.currentText() == 'Good'


def test_no_control_where_the_row_did_not_supply_the_column(edit_tree):
    assert _cell_widget(edit_tree, ['ob1', 'e1'], 'qa') is None


def test_visible_key_confines_the_control(app):
    """A column can name a row field that gates its control, which is
    how a control is confined to parent rows."""
    tree = Widgets.TreeView()
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='QA', key='qa', widget='combobox',
             choices=['', 'Good'], visible_key='qa_ctl'),
    ], 2, 'name')
    tree.set_tree({'ob1': {'name': 'OB', 'qa': 'Good', 'qa_ctl': True,
                           'e1': {'name': 'e1', 'qa': '', 'qa_ctl': False}}})
    assert _cell_widget(tree, ['ob1'], 'qa') is not None
    assert _cell_widget(tree, ['ob1', 'e1'], 'qa') is None


def test_using_the_control_fires_cell_edited(edit_tree):
    got = []
    edit_tree.add_callback('cell_edited', lambda w, *args: got.append(args))
    combo = _cell_widget(edit_tree, ['ob1'], 'qa')
    combo.setCurrentText('Bad')
    combo.activated.emit(combo.currentIndex())      # as a user click would
    assert got == [(['ob1'], 'qa', 'Good', 'Bad')]


def test_a_refresh_updates_the_control_without_firing(edit_tree):
    """Re-reading the same value from a refresh is not a user edit."""
    got = []
    edit_tree.add_callback('cell_edited', lambda w, *args: got.append(args))
    edit_tree.update_tree({'ob1': {'name': 'OB-042', 'note': '',
                                   'qa': 'Bad',
                                   'e1': {'name': 'e1', 'seeing': '0.6',
                                          'note': 'hi'}}})
    combo = _cell_widget(edit_tree, ['ob1'], 'qa')
    assert combo.currentText() == 'Bad'
    assert got == []


def test_no_duplicate_editor_over_a_live_control(edit_tree):
    """The delegate must not open a second combobox on top of one."""
    assert _editor(edit_tree, ['ob1'], 'qa') is None


def test_interior_blank_filler_is_not_editable(edit_tree):
    """A column the row never supplied is padding, not content -- so an
    editable column is still refused there."""
    assert _editor(edit_tree, ['ob1', 'e1'], 'qa') is None


def test_supplied_but_empty_is_editable(edit_tree):
    """The interior's note is '' and must still be editable, or a row
    with no note yet could never be given one."""
    assert _editor(edit_tree, ['ob1'], 'note') is not None


def test_cell_edited_fires_with_the_portable_signature(edit_tree):
    got = []
    edit_tree.add_callback('cell_edited',
                           lambda w, *args: got.append(args))
    from ginga.qtw.QtHelp import QtGui
    item = edit_tree._path_to_item(['ob1'])
    col = edit_tree.datakeys.index('note')
    idx = edit_tree.widget.indexFromItem(item, col)
    delegate = edit_tree.widget.itemDelegate()
    editor = delegate.createEditor(edit_tree.widget,
                                   QtGui.QStyleOptionViewItem(), idx)
    editor.setText('a new note')
    delegate.setModelData(editor, edit_tree.widget.model(), idx)
    assert got == [(['ob1'], 'note', '', 'a new note')]
    assert item.text(col) == 'a new note'


def test_double_click_edits_instead_of_toggling(edit_tree):
    """Otherwise a double-click on a parent row just expands it."""
    assert edit_tree.widget.expandsOnDoubleClick() is False


def test_tuple_descriptors_still_work(app):
    """The portable form must behave exactly as it always did."""
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 2, 'name')
    tree.set_tree({'ob1': {'e1': {'name': 'e1', 'seeing': '0.6'}}})
    assert tree.datakeys == ['name', 'seeing']
    assert tree._col_editable == set()
    assert tree.widget.expandsOnDoubleClick() is True


def test_leaf_tolerates_a_missing_column(app):
    """A leaf that omits a column renders blank rather than raising."""
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 2, 'name')
    tree.set_tree({'ob1': {'e1': {'name': 'e1'}}})
    assert _row(tree, ['ob1', 'e1']) == ['e1', '']


# ----- the other embeddable cell widgets ----------------------------

@pytest.fixture
def widget_tree(app):
    tree = Widgets.TreeView()
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='Mute', key='mute', widget='checkbox'),
        dict(label='QA', key='qa', widget='combobox',
             choices=['', 'Good', 'Bad']),
        dict(label='Done', key='pct', widget='progress', min=0, max=100),
        dict(label='', key='go', widget='button', text='Reset'),
    ], 2, 'name')
    tree.set_tree({'ob1': {'name': 'OB', 'mute': True, 'qa': 'Good',
                           'pct': 40, 'go': None,
                           'e1': {'name': 'e1', 'mute': False, 'qa': '',
                                  'pct': 90, 'go': None}}})
    return tree


def test_every_widget_type_is_supported(widget_tree):
    """checkbox / combobox / progress / button, the same set the pg
    backend and the qt TableView take."""
    from ginga.qtw.QtHelp import QtGui
    expected = {'mute': QtGui.QCheckBox, 'qa': QtGui.QComboBox,
                'pct': QtGui.QProgressBar, 'go': QtGui.QPushButton}
    for col_key, cls in expected.items():
        for path in (['ob1'], ['ob1', 'e1']):
            assert isinstance(_cell_widget(widget_tree, path, col_key), cls)


def test_widget_values_are_bound(widget_tree):
    assert _cell_widget(widget_tree, ['ob1'], 'mute').isChecked() is True
    assert _cell_widget(widget_tree, ['ob1', 'e1'],
                        'mute').isChecked() is False
    assert _cell_widget(widget_tree, ['ob1'], 'pct').value() == 40
    assert _cell_widget(widget_tree, ['ob1'], 'go').text() == 'Reset'


def test_checkbox_and_combobox_fire_cell_edited_with_typed_values(
        widget_tree):
    """old_value must be the same type as new_value, or a caller
    comparing them sees a spurious change."""
    got = []
    widget_tree.add_callback('cell_edited', lambda w, *a: got.append(a))
    _cell_widget(widget_tree, ['ob1'], 'mute').setChecked(False)
    _cell_widget(widget_tree, ['ob1'], 'qa').setCurrentText('Bad')
    assert got == [(['ob1'], 'mute', True, False),
                   (['ob1'], 'qa', 'Good', 'Bad')]


def test_button_fires_cell_action(widget_tree):
    got = []
    widget_tree.add_callback('cell_action', lambda w, *a: got.append(a))
    _cell_widget(widget_tree, ['ob1'], 'go').click()
    assert got == [(['ob1'], 'go')]


def test_enabled_key_gates_the_control(app):
    tree = Widgets.TreeView()
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='Mute', key='mute', widget='checkbox',
             enabled_key='can_mute'),
    ], 2, 'name')
    tree.set_tree({'ob1': {'name': 'OB', 'mute': False, 'can_mute': True,
                           'e1': {'name': 'e1', 'mute': False,
                                  'can_mute': False}}})
    assert _cell_widget(tree, ['ob1'], 'mute').isEnabled() is True
    assert _cell_widget(tree, ['ob1', 'e1'], 'mute').isEnabled() is False


def test_refresh_updates_controls_without_firing(widget_tree):
    got = []
    widget_tree.add_callback('cell_edited', lambda w, *a: got.append(a))
    widget_tree.update_tree({'ob1': {'name': 'OB', 'mute': False,
                                     'qa': 'Bad', 'pct': 75, 'go': None,
                                     'e1': {'name': 'e1', 'mute': False,
                                            'qa': '', 'pct': 90,
                                            'go': None}}})
    assert _cell_widget(widget_tree, ['ob1'], 'mute').isChecked() is False
    assert _cell_widget(widget_tree, ['ob1'], 'qa').currentText() == 'Bad'
    assert _cell_widget(widget_tree, ['ob1'], 'pct').value() == 75
    assert got == []


def test_button_label_falls_back_to_the_column_text(app):
    """A row that carries no value for a button column still shows the
    column's own text.

    qt took any non-None value, so a row supplying '' rendered a blank
    button -- while the gtk backends fall back to the column's `text`.
    """
    tree = Widgets.TreeView()
    tree.setup_table([dict(label='Name', key='name'),
                      dict(label='', key='go', widget='button',
                           text='Delete')], 2, 'name')
    tree.set_tree({'ob1': {'name': 'OB', 'go': '',
                           'e1': {'name': 'e1', 'go': None},
                           'e2': {'name': 'e2', 'go': 'Other'}}})

    # empty string and None both mean "no value here"
    assert _cell_widget(tree, ['ob1'], 'go').text() == 'Delete'
    assert _cell_widget(tree, ['ob1', 'e1'], 'go').text() == 'Delete'
    # ...but a real value still wins
    assert _cell_widget(tree, ['ob1', 'e2'], 'go').text() == 'Other'


def test_table_button_label_falls_back_to_the_column_text(app):
    """Same for the TableView, which builds its cell widgets itself."""
    from ginga.qtw.QtHelp import QtGui

    table = Widgets.TableView(columns=[dict(label='Name', key='name'),
                                       dict(label='', key='go',
                                            widget='button',
                                            text='Delete')])
    table.set_rows([{'name': 'a', 'go': ''}, {'name': 'b', 'go': 'Other'}])

    def button(row):
        holder = table.get_widget().cellWidget(row, 1)
        assert holder is not None
        return holder.findChildren(QtGui.QPushButton)[0]

    assert button(0).text() == 'Delete'
    assert button(1).text() == 'Other'


def test_table_font_can_be_changed_after_construction(app):
    """The gtk and pg backends already took set_font; qt applied a font
    once at construction and had no way to change it."""
    table = Widgets.TableView(columns=[dict(label='A', key='a')])
    table.set_rows([{'a': 'x'}])

    table.set_font('Courier', 9)

    font = table.get_widget().font()
    assert font.pointSize() == 9
    assert table.fontsize == 9


# ----- programmatic selection is not user interaction ----------------


def _selection_watcher(widget):
    fired = []
    widget.add_callback('selected', lambda w, rows: fired.append(rows))
    return fired


def test_selecting_a_table_row_from_code_is_silent(app):
    table = Widgets.TableView(columns=[dict(label='A', key='a')])
    table.set_rows([{'a': 'a%d' % i} for i in range(3)])
    fired = _selection_watcher(table)

    table.select_path([0])
    table.select_paths([[1]])
    table.set_selected([2])
    table.select_all(True)
    table.clear_selection()
    table.select_all(False)

    assert fired == [], "a programmatic selection reported itself"


def test_a_user_selection_in_a_table_still_reports(app):
    table = Widgets.TableView(columns=[dict(label='A', key='a')])
    table.set_rows([{'a': 'a%d' % i} for i in range(3)])
    fired = _selection_watcher(table)

    # what a click does: the Qt widget's own selection machinery
    table.get_widget().selectRow(1)

    assert len(fired) == 1
    assert fired[0] == [{'a': 'a1'}]


def test_selecting_a_tree_row_from_code_is_silent(app, tree):
    tree.set_tree({'ob1': {'name': 'ob1'}, 'ob2': {'name': 'ob2'}})
    fired = _selection_watcher(tree)

    tree.select_path(['ob1'])
    tree.select_paths([['ob2']])
    tree.select_all(True)
    tree.clear_selection()

    assert fired == []


def test_two_tables_can_clear_each_other_without_ping_pong(app):
    """The case this contract exists for: two views that clear each
    other's selection would otherwise recurse and wipe both."""
    a = Widgets.TableView(columns=[dict(label='A', key='a')])
    b = Widgets.TableView(columns=[dict(label='A', key='a')])
    for t in (a, b):
        t.set_rows([{'a': 'a%d' % i} for i in range(3)])
    a.add_callback('selected', lambda w, rows: b.clear_selection())
    b.add_callback('selected', lambda w, rows: a.clear_selection())

    a.get_widget().selectRow(0)          # user picks in A
    assert len(a.get_selected()) == 1
    assert len(b.get_selected()) == 0

    b.get_widget().selectRow(2)          # user picks in B
    assert len(a.get_selected()) == 0
    assert len(b.get_selected()) == 1


def test_cell_action_names_the_row_by_path_or_values(app, tree):
    """A tree reports the clicked row by its path, a table by its row
    dict.  Every backend follows that split."""
    tree.setup_table([dict(label='Name', key='name'),
                      dict(label='', key='go', widget='button', text='Go')],
                     1, 'name')
    tree.set_tree({'ob1': {'name': 'ob1', 'go': None}})
    got = []
    tree.add_callback('cell_action', lambda w, *args: got.append(args))
    tree._cell_widget_clicked(tree._path_to_item(['ob1']),
                              tree.datakeys.index('go'))
    assert got == [(['ob1'], 'go')]

    table = Widgets.TableView(
        columns=[dict(label='A', key='a'),
                 dict(label='', key='go', widget='button', text='Go')])
    table.set_rows([{'a': 'a0', 'go': None}, {'a': 'a1', 'go': None}])
    got = []
    table.add_callback('cell_action', lambda w, *args: got.append(args))
    table._on_cell_widget_clicked(table._row_token(1), 'go')
    assert len(got) == 1
    row, col_key = got[0]
    assert isinstance(row, dict) and row['a'] == 'a1'
    assert col_key == 'go'
