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
        keys.append(tree._leaf_keys.get(id(model.get_value(it, 0))))
        it = model.iter_next(it)
    assert 'e3' in keys

    it = model.iter_children(ob)
    while tree._leaf_keys.get(id(model.get_value(it, 0))) != 'e1':
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
