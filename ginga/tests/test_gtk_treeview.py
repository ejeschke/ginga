"""Tests for the gtk TreeView backends.

Only one GTK major version can be loaded into a process, so this module
uses whichever of gtk3/gtk4 is importable -- run it in each environment
to cover both.  Everything is skipped when gi or a display is missing,
which is the case in the plain test environment.

GTK paints cells through a per-column data function rather than by
storing attributes on an item, so the checks call those functions the
way GTK would and read back the renderer state.
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

has_colors = hasattr(Widgets.TreeView, 'set_cell_color')
# Interior-row values, per-column editing and widget cells arrived
# together; gtk4 gets them with its ColumnView migration.
has_descriptors = hasattr(Widgets.TreeView, '_row_supplied')

needs_descriptors = pytest.mark.skipif(
    not has_descriptors,
    reason="backend has no interior values / per-column editing yet")


@pytest.fixture(scope='module')
def app():
    return Widgets.Application()


@pytest.fixture
def tree(app):
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 2, 'name')
    tree.set_tree({'ob1': {'e1': {'name': 'e1', 'seeing': '0.6'},
                           'e2': {'name': 'e2', 'seeing': '0.9'}}})
    return tree


def _cell_and_fn(tree, col_idx):
    """The renderer for a column, plus the data function GTK calls."""
    column = tree.tv.get_columns()[col_idx]
    cell = column.get_cells()[0]
    fn = tree._mkcolfnN(col_idx, tree.datakeys[col_idx],
                        tree.datatypes[col_idx])
    return column, cell, fn


def _iters(tree):
    model = tree.tv.get_model()
    ob = model.get_iter_first()
    e1 = model.iter_children(ob)
    e2 = model.iter_next(e1)
    return model, ob, e1, e2


def _state(cell):
    return (cell.get_property('foreground-set'),
            cell.get_property('cell-background-set'),
            cell.get_property('weight-set'))


def test_batch_is_a_no_op_context_manager(app):
    """Defined on every backend so application code can use it
    unconditionally; only the pg backend actually coalesces."""
    label = Widgets.Label('x')
    with label.batch():
        label.set_text('inside')
    assert label.get_text() == 'inside'


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
def test_cell_colour_applies(tree):
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 1)
    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red', bg='yellow',
                        bold=True)
    fn(column, cell, model, e1)
    assert _state(cell) == (True, True, True)


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
def test_renderer_state_does_not_leak_between_rows(tree):
    """One renderer draws every row of its column, so a styled row must
    not leave its colour on the next, unstyled one."""
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 1)
    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red', bg='yellow',
                        bold=True)

    fn(column, cell, model, e1)
    assert _state(cell) == (True, True, True)
    fn(column, cell, model, e2)
    assert _state(cell) == (False, False, False)
    fn(column, cell, model, e1)
    fn(column, cell, model, ob)
    assert _state(cell) == (False, False, False)


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
def test_cascade_cell_over_row_over_column_over_table(tree):
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 0)

    tree.set_table_color(fg='blue')
    fn(column, cell, model, ob)
    table_fg = cell.get_property('foreground-rgba').to_string()

    tree.set_column_color('name', bg='green')
    fn(column, cell, model, ob)
    assert cell.get_property('foreground-rgba').to_string() == table_fg
    assert cell.get_property('cell-background-set') is True

    tree.set_row_color(['ob1'], fg='white')
    fn(column, cell, model, ob)
    assert cell.get_property('foreground-rgba').to_string() != table_fg


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
def test_clearing(tree):
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 1)

    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red')
    tree.clear_cell_color(['ob1', 'e1'], 'seeing')
    fn(column, cell, model, e1)
    assert _state(cell) == (False, False, False)

    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red')
    tree.set_cell_color(['ob1', 'e1'], 'seeing')      # all-None clears
    fn(column, cell, model, e1)
    assert _state(cell) == (False, False, False)


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
def test_clear_all_colors(tree):
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 1)
    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red')
    tree.set_table_color(fg='blue')
    tree.clear_all_colors()
    fn(column, cell, model, e1)
    assert _state(cell) == (False, False, False)


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
def test_colours_survive_a_refresh(tree):
    """update_tree keeps existing rows' colours, and a row added by it
    still resolves the inherited layers."""
    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red')
    tree.set_table_color(fg='blue')
    tree.update_tree({'ob1': {'e1': {'name': 'e1', 'seeing': '1.4'},
                              'e2': {'name': 'e2', 'seeing': '0.9'},
                              'e3': {'name': 'e3', 'seeing': '0.5'}}})
    model = tree.tv.get_model()
    ob = model.get_iter_first()
    column, cell, fn = _cell_and_fn(tree, 1)

    it = model.iter_children(ob)
    keys = []
    while it is not None:
        keys.append(tree._row_keys.get(id(model.get_value(it, 0))))
        it = model.iter_next(it)
    assert 'e3' in keys

    it = model.iter_children(ob)
    while tree._row_keys.get(id(model.get_value(it, 0))) != 'e1':
        it = model.iter_next(it)
    fn(column, cell, model, it)
    assert cell.get_property('foreground-set') is True


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
def test_set_colors_batch(tree):
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 1)
    tree.set_colors({'cells': [
        {'path': ['ob1', 'e1'], 'col_key': 'seeing', 'fg': 'red'},
        {'path': ['ob1', 'e2'], 'col_key': 'seeing', 'fg': 'green'}]})
    fn(column, cell, model, e1)
    assert cell.get_property('foreground-set') is True
    fn(column, cell, model, e2)
    assert cell.get_property('foreground-set') is True


# ----- interior row values ------------------------------------------

def _find(tree, path):
    """The model iter for a key path, resolved through the row index --
    tree paths would go stale as soon as the view is sorted."""
    model = tree.tv.get_model()
    it = model.get_iter_first()
    keys = list(path)
    while it is not None:
        if tree._row_keys.get(id(model.get_value(it, 0))) == keys[0]:
            if len(keys) == 1:
                return it
            keys = keys[1:]
            it = model.iter_children(it)
            continue
        it = model.iter_next(it)
    raise AssertionError(f"row {path} not found")


def _render(tree, path, col_key):
    """Run the column's data function on a row, as GTK would, and hand
    back the renderer it configured."""
    model = tree.tv.get_model()
    i = tree.datakeys.index(col_key)
    column = tree.tv.get_columns()[i]
    cell = column.get_cells()[0]
    tree._mkcolfnN(i, col_key, tree.datatypes[i])(column, cell, model,
                                                  _find(tree, path))
    return cell


def _row_text(tree, path):
    return [_render(tree, path, key).get_property('text')
            for key in tree.datakeys]


@pytest.fixture
def vtree(app):
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Grade', 'grade'),
                      ('Seeing', 'seeing')], 2, 'name')
    return tree


@needs_descriptors
def test_interior_without_values_shows_its_key(vtree):
    """The behaviour these rows have always had, guarded."""
    vtree.set_tree({'ob1': {'e1': {'name': 'e1', 'grade': '',
                                   'seeing': '0.6'}}})
    assert _row_text(vtree, ['ob1']) == ['ob1', '', '']


@needs_descriptors
def test_interior_values_inline_and_sentinel(vtree):
    vtree.set_tree({'ob1': {'name': 'OB-042', 'grade': 'A',
                            'e1': {'name': 'e1', 'grade': '',
                                   'seeing': '0.6'}}})
    assert _row_text(vtree, ['ob1']) == ['OB-042', 'A', '']

    vtree.set_tree({'ob1': {'__values__': {'name': 'OB-042', 'grade': 'B'},
                            'e1': {'name': 'e1', 'grade': '',
                                   'seeing': '0.6'}}})
    assert _row_text(vtree, ['ob1']) == ['OB-042', 'B', '']


@needs_descriptors
def test_values_never_become_a_row(vtree):
    """The bug this fixes: the values showed up as a child row."""
    vtree.set_tree({'ob1': {'__values__': {'name': 'OB-042'},
                            'e1': {'name': 'e1', 'grade': '',
                                   'seeing': '0.6'}}})
    model = vtree.tv.get_model()
    ob = model.get_iter_first()
    kids = []
    it = model.iter_children(ob)
    while it is not None:
        kids.append(vtree._row_keys.get(id(model.get_value(it, 0))))
        it = model.iter_next(it)
    assert kids == ['e1']


@needs_descriptors
def test_leaf_tolerates_a_missing_column(vtree):
    vtree.set_tree({'ob1': {'e1': {'name': 'e1'}}})
    assert _row_text(vtree, ['ob1', 'e1']) == ['e1', '', '']


@needs_descriptors
def test_update_refreshes_interior_values(vtree):
    vtree.set_tree({'ob1': {'name': 'OB', 'grade': 'A',
                            'e1': {'name': 'e1', 'grade': '',
                                   'seeing': '0.6'}}})
    vtree.update_tree({'ob1': {'name': 'OB', 'grade': 'C',
                               'e1': {'name': 'e1', 'grade': '',
                                      'seeing': '1.4'}}})
    assert _row_text(vtree, ['ob1'])[1] == 'C'
    assert _row_text(vtree, ['ob1', 'e1'])[2] == '1.4'


# ----- per-column editing and widget cells --------------------------

@pytest.fixture
def etree(app):
    tree = Widgets.TreeView()
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='Seeing', key='seeing'),
        dict(label='Note', key='note', editable=True),
        dict(label='Mute', key='mute', widget='checkbox'),
        dict(label='QA', key='qa', widget='combobox',
             choices=['', 'Good', 'Bad'], visible_key='qa_ctl'),
        dict(label='Done', key='pct', widget='progress', min=0, max=100),
    ], 2, 'name')
    tree.set_tree({'ob1': {'name': 'OB-042', 'note': '', 'mute': True,
                           'qa': 'Good', 'qa_ctl': True, 'pct': 40,
                           'e1': {'name': 'e1', 'seeing': '0.6',
                                  'note': 'hi', 'mute': False, 'pct': 90,
                                  'qa_ctl': False}}})
    return tree


@needs_descriptors
def test_renderer_per_widget_type(etree):
    kinds = {key: type(etree.tv.get_columns()[etree.datakeys.index(key)]
                       .get_cells()[0]).__name__
             for key in ('note', 'mute', 'qa', 'pct')}
    assert kinds == {'note': 'CellRendererText',
                     'mute': 'CellRendererToggle',
                     'qa': 'CellRendererCombo',
                     'pct': 'CellRendererProgress'}


@needs_descriptors
def test_editing_is_per_column(etree):
    assert _render(etree, ['ob1'], 'note').get_property('editable') is True
    assert _render(etree, ['ob1'], 'seeing').get_property('editable') is False


@needs_descriptors
def test_editing_is_refused_on_filler_cells(etree):
    """A column the row never supplied is padding, not content."""
    assert _render(etree, ['ob1', 'e1'], 'qa').get_property('visible') is False
    assert _render(etree, ['ob1'], 'qa').get_property('visible') is True


@needs_descriptors
def test_widget_values_are_bound(etree):
    assert _render(etree, ['ob1'], 'mute').get_property('active') is True
    assert _render(etree, ['ob1'], 'pct').get_property('value') == 40


@needs_descriptors
def test_cell_edited_reports_typed_values(etree):
    got = []
    etree.add_callback('cell_edited', lambda w, *a: got.append(a))
    model = etree.tv.get_model()
    where = model.get_string_from_iter(_find(etree, ['ob1']))
    etree._edited_cb(None, where, 'a new note', 'note',
                     etree.datakeys.index('note'))
    etree._toggled_cb(None, where, 'mute', etree.datakeys.index('mute'))
    assert got == [(['ob1'], 'note', '', 'a new note'),
                   (['ob1'], 'mute', True, False)]


@needs_descriptors
def test_button_cells_report_clicks(app):
    """GTK3 has no button renderer, so the click is located in the view
    rather than connected to a widget."""
    tree = Widgets.TreeView()
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='', key='go', widget='button', text='Reset',
             visible_key='can_go'),
    ], 2, 'name')
    tree.set_tree({'ob1': {'name': 'OB', 'go': None, 'can_go': True,
                           'e1': {'name': 'e1', 'go': None,
                                  'can_go': False}}})
    assert _render(tree, ['ob1'], 'go').get_property('text') == 'Reset'
    assert _render(tree, ['ob1'], 'go').get_property('visible') is True
    assert _render(tree, ['ob1', 'e1'], 'go').get_property('visible') is False

    got = []
    tree.add_callback('cell_action', lambda w, *a: got.append(a))
    model = tree.tv.get_model()
    column = tree.tv.get_columns()[tree.datakeys.index('go')]

    class _Ev:
        x = y = 1.0

    # nothing is realised off-screen, so aim the hit test ourselves
    tree.tv.get_path_at_pos = lambda x, y: (
        model.get_path(_find(tree, ['ob1'])), column, 1, 1)
    tree._on_tree_button_press(tree.tv, _Ev())
    assert got == [(['ob1'], 'go')]

    got.clear()
    tree.tv.get_path_at_pos = lambda x, y: (
        model.get_path(_find(tree, ['ob1', 'e1'])), column, 1, 1)
    tree._on_tree_button_press(tree.tv, _Ev())
    assert got == []
