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

# gtk3 paints through cell renderers and a per-column data function;
# gtk4's ColumnView has neither, using a widget per cell -- so the
# renderer-level checks apply to gtk3 only.  The gtk4 equivalents live
# at the end of this module.
uses_renderers = 'gtk4' not in Widgets.__name__
needs_renderers = pytest.mark.skipif(
    not uses_renderers,
    reason="renderer-based check; gtk4 renders cells as widgets")


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
@needs_renderers
def test_cell_colour_applies(tree):
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 1)
    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red', bg='yellow',
                        bold=True)
    fn(column, cell, model, e1)
    assert _state(cell) == (True, True, True)


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
@needs_renderers
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
@needs_renderers
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
@needs_renderers
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
@needs_renderers
def test_clear_all_colors(tree):
    model, ob, e1, e2 = _iters(tree)
    column, cell, fn = _cell_and_fn(tree, 1)
    tree.set_cell_color(['ob1', 'e1'], 'seeing', fg='red')
    tree.set_table_color(fg='blue')
    tree.clear_all_colors()
    fn(column, cell, model, e1)
    assert _state(cell) == (False, False, False)


@pytest.mark.skipif(not has_colors, reason="backend has no TreeView colours")
@needs_renderers
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
@needs_renderers
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


@needs_renderers
def test_alternating_rows_are_painted_by_the_backend(app):
    """gtk3 has to paint its own stripes.

    ``set_rules_hint`` was how this worked, but GTK deprecated it in
    3.14 and the themes ignore it -- so a TreeView asked for alternating
    colours (FBrowser does) came out plain while the TableView, which
    already painted its own, looked right.
    """
    tree = Widgets.TreeView(use_alt_row_color=True)
    tree.setup_table([('Name', 'name')], 2, 'name')
    tree.set_tree({'ob1': {'e1': {'name': 'e1'}, 'e2': {'name': 'e2'}},
                   'ob2': {'e3': {'name': 'e3'}}})
    tree.expand_all(True)

    model = tree.tv.get_model()
    tree._invalidate_alt_index()
    tree._rebuild_alt_index(model)

    # striped by *visible* row, so an expanded child shifts what comes
    # after it -- a flat top-level index would get this wrong
    order = [tree._alt_index[key] for key in
             sorted(tree._alt_index, key=lambda k: [int(i)
                                                    for i in k.split(':')])]
    assert order == list(range(len(order))), \
        "visible rows are not numbered in order: %r" % (order,)
    assert len(order) == 5

    colours = [_render(tree, path, 'name').get_property('cell-background-rgba')
               for path in (['ob1'], ['ob1', 'e1'], ['ob1', 'e2'],
                            ['ob2'], ['ob2', 'e3'])]
    strings = [c.to_string() if c is not None else None for c in colours]
    assert all(strings[i] != strings[i + 1] for i in range(len(strings) - 1)), \
        "stripes do not alternate down the view: %r" % (strings,)


@needs_renderers
def test_alternating_rows_stay_off_when_not_asked_for(app):
    tree = Widgets.TreeView(use_alt_row_color=False)
    tree.setup_table([('Name', 'name')], 2, 'name')
    tree.set_tree({'ob1': {'e1': {'name': 'e1'}}})
    assert tree._alt_row_colors is False
    cell = _render(tree, ['ob1'], 'name')
    assert cell.get_property('cell-background-set') is False


@needs_renderers
def test_a_cell_colour_wins_over_the_stripe(app):
    tree = Widgets.TreeView(use_alt_row_color=True)
    tree.setup_table([('Name', 'name')], 2, 'name')
    tree.set_tree({'ob1': {'e1': {'name': 'e1'}}})
    tree.expand_all(True)
    tree.set_cell_color(['ob1', 'e1'], 'name', bg='red')
    cell = _render(tree, ['ob1', 'e1'], 'name')
    rgba = cell.get_property('cell-background-rgba')
    assert rgba is not None and rgba.red > 0.9 and rgba.green < 0.2, \
        "an explicit cell colour must beat the stripe: %r" % (
            rgba.to_string() if rgba else None,)


# -- gtk4 ColumnView --------------------------------------------------
#
# The gtk4 backend renders through real per-cell widgets rather than
# renderers, so these look at the widgets and the generated stylesheet.

is_gtk4 = 'gtk4' in Widgets.__name__
needs_gtk4 = pytest.mark.skipif(not is_gtk4,
                                reason="gtk4 ColumnView backend only")

if is_gtk4:
    from gi.repository import Gdk, Gtk, GLib


def _pump(n=60):
    ctx = GLib.MainContext.default()
    for _ in range(n):
        while ctx.pending():
            ctx.iteration(False)


def _shown(view, size=(500, 220)):
    """Realise a view, so its cells get bound and can be inspected."""
    win = Gtk.Window()
    win.set_default_size(*size)
    win.set_child(view.widget)
    win.present()
    _pump()
    return win


def _table(app, mode='multiple-cell', sortable=False, editable=('a', 'b')):
    table = Widgets.TableView(
        columns=[dict(label=key.upper(), key=key, editable=key in editable)
                 for key in ('a', 'b', 'c')],
        selection_mode=mode, sortable=sortable, show_row_numbers=True)
    table.set_rows([{'a': 'a%d' % i, 'b': 'b%d' % i, 'c': 'c%d' % i}
                    for i in (1, 2, 3)])
    return table


class _Gesture:
    """Stands in for the header's click gesture."""

    def __init__(self, state=0):
        self._state = state

    def get_current_event_state(self):
        return self._state


@needs_gtk4
def test_cell_background_leaves_the_selection_alone(app):
    # a cell background painted on every row hides the selection
    # highlight, and the text -- which does follow the selection --
    # goes invisible on it
    table = _table(app)
    css = table._css.to_string()
    assert 'row:not(:selected) > cell' in css
    assert '> row > cell {\n            background' not in css


@needs_gtk4
def test_editable_cell_is_not_painted_as_an_entry(app):
    # GtkEditableLabel is an entry: left alone it paints the theme's
    # entry background over the cell at rest
    table = _table(app)
    css = table._css.to_string()
    assert 'editablelabel:not(.editing)' in css
    idx = css.index('editablelabel:not(.editing)')
    # GTK normalises the value it parsed
    assert 'background-color: rgba(0,0,0,0)' in css[idx:idx + 400]


@needs_gtk4
def test_header_click_selects_a_column(app):
    table = _table(app)
    _shown(table)
    table._on_header_clicked(_Gesture(), 1, 0, 0, 1)
    assert {c['col_key'] for c in table.get_selected_cells()} == {'b'}
    assert len(table.get_selected_cells()) == 3

    # ctrl adds, shift extends, a plain click replaces
    table._on_header_clicked(_Gesture(Gdk.ModifierType.CONTROL_MASK),
                             1, 0, 0, 0)
    assert {c['col_key'] for c in table.get_selected_cells()} == {'a', 'b'}
    table._on_header_clicked(_Gesture(), 1, 0, 0, 0)
    table._on_header_clicked(_Gesture(Gdk.ModifierType.SHIFT_MASK),
                             1, 0, 0, 2)
    assert {c['col_key'] for c in table.get_selected_cells()} == \
        {'a', 'b', 'c'}


@needs_gtk4
def test_header_click_sorts_a_sortable_table_instead(app):
    # matches qt: sorting owns the plain click, modifiers select
    table = _table(app, sortable=True)
    _shown(table)
    table._on_header_clicked(_Gesture(), 1, 0, 0, 1)
    assert table.get_selected_cells() == []
    table._on_header_clicked(_Gesture(Gdk.ModifierType.CONTROL_MASK),
                             1, 0, 0, 1)
    assert {c['col_key'] for c in table.get_selected_cells()} == {'b'}


@needs_gtk4
def test_row_selection_mode_does_not_column_select(app):
    table = _table(app, mode='single')
    _shown(table)
    table._on_header_clicked(_Gesture(), 1, 0, 0, 1)
    assert table.get_selected_cells() == []


@needs_gtk4
def test_arrow_keys_walk_the_cell_cursor(app):
    table = _table(app)
    _shown(table)
    table.set_cursor_cell(0, 0)
    assert table._cursor == (0, 0)

    for keyval, want in ((Gdk.KEY_Right, (0, 1)),
                         (Gdk.KEY_Down, (1, 1)),
                         (Gdk.KEY_Left, (1, 0)),
                         (Gdk.KEY_Up, (0, 0))):
        assert table._cv_key_pressed_cb(None, keyval, 0, 0) is True
        assert table._cursor == want

    # the edges stop, and leave the key for the view
    assert table._cv_key_pressed_cb(None, Gdk.KEY_Up, 0, 0) is False
    assert table._cursor == (0, 0)


@needs_gtk4
def test_tab_wraps_onto_the_next_row(app):
    table = _table(app)
    _shown(table)
    table.set_cursor_cell(0, 0)
    for _ in range(3):
        table._cv_key_pressed_cb(None, Gdk.KEY_Tab, 0, 0)
    assert table._cursor == (1, 0)
    table._cv_key_pressed_cb(None, Gdk.KEY_ISO_Left_Tab, 0,
                             Gdk.ModifierType.SHIFT_MASK)
    assert table._cursor == (0, 2)


@needs_gtk4
def test_unclaimed_ctrl_chords_pass_through(app):
    # Ctrl+C/X/V are the table's (see the clipboard tests); anything
    # else with Ctrl held is somebody else's business
    table = _table(app)
    _shown(table)
    table.set_cursor_cell(0, 0)
    for keyval in (Gdk.KEY_z, Gdk.KEY_a, Gdk.KEY_s):
        assert table._cv_key_pressed_cb(None, keyval, 0,
                                        Gdk.ModifierType.CONTROL_MASK) is \
            False


@needs_gtk4
# NB: parametrised by character, not keyval -- a Gdk.KEY_* in the
# decorator is evaluated at import time, where Gdk exists only under
# gtk4, and breaks collection everywhere else
@pytest.mark.parametrize('char', ['z', ' '])
def test_typing_starts_an_edit_seeded_with_the_character(app, char):
    keyval = Gdk.unicode_to_keyval(ord(char))
    # space counts as a character to type over a cell with, not as a
    # key that activates the row
    table = _table(app)
    _shown(table)
    table.set_cursor_cell(1, 0)
    widget = table._editable_at(1, 0)
    assert widget is not None
    table._cv_key_pressed_cb(None, keyval, 0, 0)
    _pump()
    assert widget.get_property('editing') is True
    assert widget.get_text() == char


@needs_gtk4
def test_return_starts_an_edit_and_a_plain_column_takes_none(app):
    table = _table(app)
    _shown(table)
    table.set_cursor_cell(2, 1)
    widget = table._editable_at(2, 1)
    table._cv_key_pressed_cb(None, Gdk.KEY_Return, 0, 0)
    _pump()
    assert widget.get_property('editing') is True

    assert table._editable_at(0, 2) is None
    # …but the cursor still moves through it
    table.set_cursor_cell(0, 2)
    assert table._cv_key_pressed_cb(None, Gdk.KEY_Down, 0, 0) is True


def _settle(ms=400):
    """Let a frame actually be drawn.

    Restyles land on the next frame and the frame clock only ticks
    inside a running main loop -- draining pending events reads back
    the *previous* frame, which quietly makes rendering checks pass.
    """
    loop = GLib.MainLoop()
    GLib.timeout_add(ms, lambda: (loop.quit(), False)[1])
    loop.run()


def _pixels(win):
    from gi.repository import GdkPixbuf
    snap = Gtk.Snapshot()
    win.do_snapshot(win, snap)
    node = snap.to_node()
    assert node is not None
    path = '/tmp/ginga_test_columnview.png'
    win.get_renderer().render_texture(node, None).save_to_png(path)
    return GdkPixbuf.Pixbuf.new_from_file(path)


def _at(pb, x, y):
    data = pb.get_pixels()
    off = y * pb.get_rowstride() + x * pb.get_n_channels()
    return tuple(data[off:off + 3])


@needs_gtk4
def test_alternating_shade_goes_on_the_cells(app):
    # cells are painted over the row, so a shade on the row never shows
    table = Widgets.TableView(columns=[dict(label='A', key='a'),
                                       dict(label='B', key='b')],
                              alternate_row_colors=True,
                              show_row_numbers=True)
    table.set_rows([{'a': 'a%d' % i, 'b': 'b%d' % i} for i in range(6)])
    win = _shown(table, size=(400, 220))
    _settle()
    pb = _pixels(win)
    # sample a clear patch of two adjacent rows
    bands = [_at(pb, int(pb.get_width() * 0.45), y)
             for y in (36, 56, 76, 96)]
    assert bands[0] != bands[1], "no alternating shade: %r" % (bands,)
    assert bands[0] == bands[2] and bands[1] == bands[3], \
        "shade does not alternate every other row: %r" % (bands,)


@needs_gtk4
def test_selected_column_is_actually_visible(app):
    # the editable-cell transparency rule out-specifies a bare
    # .ginga-cell-selected, and silently wiped the highlight
    table = _table(app)
    win = _shown(table, size=(520, 200))
    _settle()
    before = _pixels(win)
    table._on_header_clicked(_Gesture(), 1, 0, 0, 1)
    _settle()
    after = _pixels(win)

    width, height = after.get_width(), after.get_height()
    row_y = int(height * 0.25)
    changed = [x for x in range(10, width - 10, 5)
               if _at(before, x, row_y) != _at(after, x, row_y)]
    assert changed, "selecting a column changed nothing on screen"


@needs_gtk4
def test_editable_cells_are_not_painted_by_the_app_stylesheet(app):
    """A table inside a TabWidget must look like one that isn't.

    ``gtk_css`` paints the window chrome, and a descendant selector
    there (``notebook stack``) also matched the stack inside every
    GtkEditableLabel -- so every editable cell of a table in a tab was
    filled with the chrome grey, which also hid the row selection and
    the cell cursor underneath it.
    """
    top = app.make_window("cell paint")
    nb = Widgets.TabWidget()
    box = Widgets.VBox()
    table = Widgets.TableView(
        columns=[dict(label='A', key='a', editable=True),
                 dict(label='B', key='b', editable=True)],
        show_row_numbers=True, selection_mode='multiple-cell')
    table.set_rows([{'a': 'a%d' % i, 'b': 'b%d' % i} for i in range(6)])
    box.add_widget(table, stretch=1)
    nb.add_widget(box, title='tab')
    top.set_widget(nb)
    top.resize(500, 220)
    top.show()
    _settle()

    view = table.cv
    paintable = Gtk.WidgetPaintable.new(view)
    snap = Gtk.Snapshot()
    paintable.snapshot(snap, view.get_width(), view.get_height())
    node = snap.to_node()
    assert node is not None
    path = '/tmp/ginga_test_columnview_tab.png'
    top.get_widget().get_renderer().render_texture(
        node, None).save_to_png(path)
    from gi.repository import GdkPixbuf
    pb = GdkPixbuf.Pixbuf.new_from_file(path)

    row_y = 40
    assert _at(pb, 12, row_y) == _at(pb, int(pb.get_width() * 0.6), row_y), \
        "editable cell is painted differently from a row-number cell"


# -- real input -------------------------------------------------------
#
# Calling the handlers directly cannot tell you whether the events ever
# reach them: a click on an editable cell was being taken by the
# GtkEditableLabel, and a header click by the header's own gesture, so
# the cell cursor and column selection did nothing in a real
# application while every direct-call check passed.  These drive the
# widget with X events instead.  They need python-xlib and a display
# that allows XTEST, and skip otherwise.

@needs_gtk4
def test_clicks_and_keys_reach_the_view(app, request):
    xlib = pytest.importorskip('Xlib')
    from Xlib import display as xdisplay, X
    from Xlib.ext import xtest
    try:
        xd = xdisplay.Display()
        if not xd.query_extension('XTEST'):
            pytest.skip("no XTEST extension")
    except Exception as exc:                           # pragma: no cover
        pytest.skip("cannot open X display: %s" % (exc,))
    assert xlib is not None
    # ginga's test config turns warnings into errors, so the X
    # connection has to be handed back rather than left to the GC
    request.addfinalizer(xd.close)

    top = app.make_window("input")
    nb = Widgets.TabWidget()
    box = Widgets.VBox()
    table = Widgets.TableView(
        columns=[dict(label=key.upper(), key=key, editable=True)
                 for key in ('a', 'b', 'c')],
        selection_mode='multiple-cell', show_row_numbers=True)
    table.set_rows([{'a': 'a%d' % i, 'b': 'b%d' % i, 'c': 'c%d' % i}
                    for i in range(6)])
    box.add_widget(table, stretch=1)
    nb.add_widget(box, title='tab')
    top.set_widget(nb)
    top.resize(700, 300)
    top.show()
    _settle(600)
    win = top.get_widget()

    def at_widget(widget):
        res = widget.translate_coordinates(win, widget.get_width() // 2,
                                           widget.get_height() // 2)
        px, py = res[1:] if len(res) == 3 else res
        return int(px), int(py)

    def click(x, y, presses=1):
        xtest.fake_input(xd, X.MotionNotify, x=x, y=y)
        xd.sync()
        for _ in range(presses):
            xtest.fake_input(xd, X.ButtonPress, 1)
            xtest.fake_input(xd, X.ButtonRelease, 1)
        xd.sync()
        _settle(300)

    # Other tests leave windows mapped, and without a window manager
    # the keyboard focus does not follow our new one -- point X at it
    # explicitly, or the key events land somewhere else entirely.
    try:
        import gi
        gi.require_version('GdkX11', '4.0')
        from gi.repository import GdkX11               # noqa: F401
        xid = win.get_surface().get_xid()
        xd.sync()
        xd.create_resource_object('window', xid).set_input_focus(
            X.RevertToParent, X.CurrentTime)
        xd.sync()
    except Exception:                                  # pragma: no cover
        pass

    def key(keysym):
        code = xd.keysym_to_keycode(keysym)
        xtest.fake_input(xd, X.KeyPress, code)
        xtest.fake_input(xd, X.KeyRelease, code)
        xd.sync()
        _settle(300)

    # every header must select its own column: numbering them when the
    # gestures are attached binds them to a header GTK has not rebuilt
    # yet, and each click then lands one column to the left
    table.select_path([2])
    _settle(200)
    # NB: by screen position.  The header's child order is not the
    # column order -- the row-number title is created last and sits
    # leftmost -- so indexing the children picks the wrong column, in
    # the widget and in a test written the same way.
    for user_col, col_key in enumerate(('a', 'b', 'c')):
        titles = table._titles_in_view_order()
        click(*at_widget(titles[user_col + table._col_offset()]))
        assert {c['col_key'] for c in table.get_selected_cells()} == \
            {col_key}, "header %d selected the wrong column" % (user_col,)
    assert len(table.get_selected_cells()) == 6, \
        "column selection should cover every row"
    assert table.get_selected_paths() == [], \
        "a column selection should clear the selected rows"

    cell = None
    for (_rid, col_idx), (row, widget) in table._cell_labels.items():
        if col_idx == 1 and table._path_for_row(row) == [1]:
            cell = widget
            break
    assert cell is not None
    table.select_path([4])
    _settle(200)
    click(*at_widget(cell))
    assert table._cursor == (1, 1), "a real click did not place the cursor"
    assert not cell.get_property('editing'), \
        "a single click should place the cursor, not open the editor"
    assert table.get_selected_paths() == [], \
        "clicking a cell must select the cell and clear the row selection"

    key(0xff53)                                        # Right
    assert table._cursor == (1, 2), "arrow key did not move the cursor"
    key(0xff09)                                        # Tab
    assert table._cursor == (2, 0), "Tab did not move the cursor"

    # typing straight after a click replaces the cell, as in the qt and
    # pg tables -- no double click needed to get at the editor
    click(*at_widget(cell))
    _settle(200)
    key(0x078)                                         # 'x'
    editor = table._editable_at(*table._cursor)
    assert editor.get_property('editing'), "typing did not open the editor"
    assert editor.get_text() == 'x', \
        "typing should replace the cell, got %r" % (editor.get_text(),)
    # arrowing out of an open editor commits and moves by *cell*.
    # Left to GTK the key reaches the ColumnView, which moves the row
    # selection and takes the focus -- so the edit is cancelled and the
    # cell appears to revert to its old value.
    edits = []
    table.add_callback('cell_edited', lambda *args: edits.append(args[1:]))
    before = table._cursor
    key(0xff52)                                        # Up
    assert not editor.get_property('editing'), "Up did not commit the edit"
    assert table._cursor == (before[0] - 1, before[1]), \
        "Up moved to %r, wanted the cell above %r" % (table._cursor, before)
    assert table.get_selected_paths() == [], \
        "Up selected a row instead of moving the cell cursor"
    assert table.get_row(before[0])[table.datakeys[before[1]]] == 'x', \
        "the typed value was not committed"
    assert edits, "committing an edit fired no cell_edited callback"

    # one selection at a time, in both directions
    titles = table._titles_in_view_order()
    click(*at_widget(titles[1 + table._col_offset()]))
    assert table.get_selected_cells(), "column selection did not take"
    table.select_path([3])
    _settle(200)
    assert table.get_selected_cells() == [], \
        "selecting a row should clear the column selection"


@needs_gtk4
def test_clipboard_keys_are_bound(app):
    """Ctrl+C / Ctrl+X / Ctrl+V drive the clipboard, as in qt.

    Checked at the key handler rather than through X, so it runs
    without python-xlib; the end-to-end version is below.
    """
    table = _table(app)
    _shown(table)
    seen = {}
    for name in ('copy', 'cut'):
        table.add_callback(name,
                           lambda w, text, n=name: seen.setdefault(n, text))
    table.select_cells([dict(path=[0], col_key='a'),
                        dict(path=[1], col_key='a')])

    ctrl = Gdk.ModifierType.CONTROL_MASK
    assert table._cv_key_pressed_cb(None, Gdk.KEY_c, 0, ctrl) is True
    assert seen.get('copy') == 'a1\na2'

    assert table._cv_key_pressed_cb(None, Gdk.KEY_x, 0, ctrl) is True
    assert seen.get('cut') == 'a1\na2'
    assert table.get_row(0)['a'] == '' and table.get_row(1)['a'] == '', \
        "cut should blank the editable cells it copied"

    # a chord we don't own is left to the view
    assert table._cv_key_pressed_cb(None, Gdk.KEY_z, 0, ctrl) is False


@needs_gtk4
def test_paste_lands_from_the_anchor_cell(app):
    table = _table(app)
    _shown(table)
    pasted = []
    table.add_callback('paste', lambda w, text: pasted.append(text))
    table.select_cells([dict(path=[1], col_key='a')])
    table.paste_selection('one\ttwo\nthree\tfour')

    assert table.get_row(1)['a'] == 'one'
    assert table.get_row(1)['b'] == 'two'
    assert table.get_row(2)['a'] == 'three'
    assert table.get_row(2)['b'] == 'four'
    assert table.get_row(0)['a'] == 'a1', "paste should start at the anchor"
    assert pasted == ['one\ttwo\nthree\tfour']


@needs_gtk4
def test_clipboard_keys_end_to_end(app, request):
    xlib = pytest.importorskip('Xlib')
    from Xlib import display as xdisplay, X
    from Xlib.ext import xtest
    try:
        xd = xdisplay.Display()
        if not xd.query_extension('XTEST'):
            pytest.skip("no XTEST extension")
    except Exception as exc:                           # pragma: no cover
        pytest.skip("cannot open X display: %s" % (exc,))
    assert xlib is not None
    request.addfinalizer(xd.close)

    top = app.make_window("clipboard")
    table = _table(app)
    top.set_widget(table)
    top.resize(500, 240)
    top.show()
    _settle(500)

    try:
        import gi
        gi.require_version('GdkX11', '4.0')
        from gi.repository import GdkX11               # noqa: F401
        xid = top.get_widget().get_surface().get_xid()
        xd.sync()
        xd.create_resource_object('window', xid).set_input_focus(
            X.RevertToParent, X.CurrentTime)
        xd.sync()
    except Exception:                                  # pragma: no cover
        pass

    def chord(keysym):
        ctrl_code = xd.keysym_to_keycode(0xffe3)
        code = xd.keysym_to_keycode(keysym)
        xtest.fake_input(xd, X.KeyPress, ctrl_code)
        xtest.fake_input(xd, X.KeyPress, code)
        xtest.fake_input(xd, X.KeyRelease, code)
        xtest.fake_input(xd, X.KeyRelease, ctrl_code)
        xd.sync()
        _settle(400)

    copied = []
    table.add_callback('copy', lambda w, text: copied.append(text))
    table.set_cursor_cell(0, 0)
    table.select_cells([dict(path=[0], col_key='a'),
                        dict(path=[1], col_key='a')])
    _settle(200)

    chord(0x063)                                       # Ctrl+C
    assert copied == ['a1\na2'], "Ctrl+C did not reach the view"

    chord(0x078)                                       # Ctrl+X
    assert table.get_row(0)['a'] == '' and table.get_row(1)['a'] == ''

    table.select_cells([dict(path=[2], col_key='a')])
    table._cell_selection = {((2,), 'a')}
    _settle(200)
    chord(0x076)                                       # Ctrl+V
    _settle(600)                    # the clipboard read is asynchronous
    assert table.get_row(2)['a'] == 'a1', "Ctrl+V did not paste"


@needs_gtk4
def test_dragable_tree_offers_a_file_list(app):
    """FBrowser drags files out to a viewer.

    The viewer's drop target takes ``Gdk.FileList``, so that is what the
    drag has to offer; the payload itself comes from whoever listens for
    ``drag-start``.
    """
    tree = Widgets.TreeView(selection='multiple', dragable=True)
    tree.setup_table([('Name', 'name')], 1, 'name')
    tree.set_tree({'one.fits': {'name': 'one.fits', 'path': '/tmp/one.fits'}})
    _shown(tree)

    sources = [c for c in tree.cv.observe_controllers()
               if isinstance(c, Gtk.DragSource)]
    assert sources, "dragable=True installed no drag source"

    seen = []

    def drag_cb(widget, pkg, res_dict):
        seen.append(res_dict)
        pkg.set_uris(['file://' + info['path']
                      for info in res_dict.values()])

    tree.add_callback('drag-start', drag_cb)
    tree.select_path(['one.fits'])
    provider = tree._cv_drag_prepare_cb(sources[0], 5, 5)

    assert seen, '"drag-start" was never fired'
    assert provider is not None, 'the drag carried nothing'
    formats = provider.ref_formats().to_string()
    assert 'GdkFileList' in formats, \
        "a viewer accepts GdkFileList; got %r" % (formats,)


@needs_gtk4
def test_double_click_activates_a_row(app, request):
    """A double click has to reach ColumnView's own activation.

    Claiming the press on every cell -- which an editable cell needs, so
    a click doesn't fall into its editor -- stops that signal, and
    double-clicking a file in FBrowser silently does nothing.
    """
    xlib = pytest.importorskip('Xlib')
    from Xlib import display as xdisplay, X
    from Xlib.ext import xtest
    try:
        xd = xdisplay.Display()
        if not xd.query_extension('XTEST'):
            pytest.skip("no XTEST extension")
    except Exception as exc:                           # pragma: no cover
        pytest.skip("cannot open X display: %s" % (exc,))
    assert xlib is not None
    request.addfinalizer(xd.close)

    top = app.make_window("activate")
    tree = Widgets.TreeView(selection='single')
    tree.setup_table([('Name', 'name')], 1, 'name')
    tree.set_tree({'one.fits': {'name': 'one.fits', 'path': '/tmp/one.fits'}})
    top.set_widget(tree)
    top.resize(400, 200)
    top.show()
    _settle(500)

    opened = []
    tree.add_callback('activated', lambda w, res: opened.append(res))

    cell = None
    for (_rid, col_idx), (row, widget) in tree._cell_labels.items():
        if col_idx == 0:
            cell = widget
    assert cell is not None
    res = cell.translate_coordinates(top.get_widget(), cell.get_width() / 2,
                                     cell.get_height() / 2)
    x, y = (res[1:] if len(res) == 3 else res)
    xtest.fake_input(xd, X.MotionNotify, x=int(x), y=int(y))
    xd.sync()
    for _ in range(2):
        xtest.fake_input(xd, X.ButtonPress, 1)
        xtest.fake_input(xd, X.ButtonRelease, 1)
    xd.sync()
    _settle(500)

    assert opened, "double click did not activate the row"
    assert 'one.fits' in opened[0]


@needs_gtk4
@pytest.mark.parametrize('with_parent', [False, True])
def test_dialogs_can_be_shown(app, with_parent):
    """A dialog with a parent is a notebook page, not a window.

    ``show()`` worked on any widget; its GTK4 replacement ``present()``
    is defined on windows only, so the parented form -- which is what
    the reference viewer's quit confirmation uses -- raised
    AttributeError.
    """
    top = app.make_window("dialog host")
    top.resize(400, 200)
    top.show()
    _settle(200)

    parent = top if with_parent else None
    dialog = Widgets.MessageDialog(title="Confirm", modal=True,
                                   parent=parent, autoclose=False,
                                   buttons=[("Cancel", False),
                                            ("Confirm", True)])
    dialog.set_message('question', "Really?")
    dialog.show()                       # must not raise
    _settle(200)
    dialog.hide()


# -- a row colour has to reach the cells that hold a control ----------


@needs_renderers
def test_a_gated_off_widget_cell_still_carries_the_row_colour(app):
    """A renderer switched off draws nothing, its cell background
    included, so a row that ``visible_key`` gates the control off used
    to show an unpainted gap in an otherwise coloured row.  A blank
    stand-in renderer takes the cell on exactly those rows."""
    tree = Widgets.TreeView()
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='', key='go', widget='button', text='Reset',
             visible_key='can_go'),
    ], 2, 'name')
    tree.set_tree({'ob1': {'name': 'OB', 'go': None, 'can_go': True,
                           'e1': {'name': 'e1', 'go': None,
                                  'can_go': False}}})
    tree.set_row_color(['ob1'], bg='red')
    tree.set_row_color(['ob1', 'e1'], bg='red')

    column = tree.tv.get_columns()[tree.datakeys.index('go')]
    control, filler = column.get_cells()

    model = tree.tv.get_model()
    idx = tree.datakeys.index('go')
    fn = tree._mk_gate_filler_colfn('go', tree._col_widgets[idx])

    # the row that shows the control paints through the control itself
    fn(column, filler, model, _find(tree, ['ob1']))
    assert filler.get_property('visible') is False
    assert _render(tree, ['ob1'], 'go').get_property(
        'cell-background-set') is True

    # ...and the row that hides it paints through the stand-in
    fn(column, filler, model, _find(tree, ['ob1', 'e1']))
    assert filler.get_property('visible') is True
    assert filler.get_property('cell-background-set') is True
    assert filler.get_property('text') == ''


@needs_gtk4
def test_a_row_colour_fills_a_button_cell(app):
    """The colour goes on the ColumnView's cell, not just the control:
    a button is sized to its label, draws its own background over ours,
    and is missing altogether where ``visible_key`` gates it off."""
    table = Widgets.TableView(
        columns=[dict(label='A', key='a'),
                 dict(label='', key='go', widget='button', text='Reset',
                      visible_key='can_go')])
    table.set_rows([{'a': 'a0', 'go': None, 'can_go': True},
                    {'a': 'a1', 'go': None, 'can_go': False}])
    # only the second row is coloured, so we can find it on screen
    table.set_row_color([1], bg='#ff0000')
    win = _shown(table, size=(400, 160))
    _settle()
    pb = _pixels(win)

    width, height = pb.get_width(), pb.get_height()
    red = (255, 0, 0)
    text_x = int(width * 0.2)
    rows = [y for y in range(2, height - 2) if _at(pb, text_x, y) == red]
    assert rows, "the row colour did not paint at all"

    y = rows[len(rows) // 2]
    button_x = int(width * 0.9)
    assert _at(pb, button_x, y) == red, \
        "the button column was left unpainted on a coloured row"


# ----- programmatic selection is not user interaction ----------------


def test_selecting_a_table_row_from_code_is_silent(app):
    """Selecting from code does not fire 'selected' on any backend --
    the caller already knows what it did, and two views that clear each
    other's selection would otherwise ping-pong."""
    table = Widgets.TableView(columns=[dict(label='A', key='a')])
    table.set_rows([{'a': 'a%d' % i} for i in range(3)])
    fired = []
    table.add_callback('selected', lambda w, rows: fired.append(rows))

    table.select_path([0])
    table.select_paths([[1]])
    table.set_selected([2])
    table.select_all(True)
    table.clear_selection()
    table.select_all(False)

    assert fired == [], "a programmatic selection reported itself"


def test_selecting_a_tree_row_from_code_is_silent(app):
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name')], 1, 'name')
    tree.set_tree({'ob1': {'name': 'ob1'}, 'ob2': {'name': 'ob2'}})
    fired = []
    tree.add_callback('selected', lambda w, rows: fired.append(rows))

    tree.select_path(['ob1'])
    tree.select_paths([['ob2']])
    tree.select_all(True)
    tree.clear_selection()

    assert fired == []


def test_a_table_reports_a_clicked_button_by_its_row(app):
    """cell_action names the clicked row by its values on a table (and
    by its path on a tree) -- the same split on every backend."""
    table = Widgets.TableView(
        columns=[dict(label='A', key='a'),
                 dict(label='', key='go', widget='button', text='Go')])
    table.set_rows([{'a': 'a0', 'go': None}, {'a': 'a1', 'go': None}])
    got = []
    table.add_callback('cell_action', lambda w, *args: got.append(args))

    if is_gtk4:
        _shown(table)
        _pump()
        for (_rid, col_idx), (row, widget) in list(table._cell_labels.items()):
            if col_idx == 1 and table._index_of(row) == 1:
                table._cv_cell_clicked_cb(widget, 1)
                break
    else:
        # gtk3 locates the click in the view; nothing is realised
        # off-screen, so aim the hit test ourselves
        model = table.tv.get_model()
        column = table.tv.get_columns()[table._col_offset() + 1]
        table.tv.get_path_at_pos = lambda x, y: (
            model.get_path(model.iter_nth_child(None, 1)), column, 1, 1)

        class _Ev:
            button = 1
            x = y = 1.0

        table._on_tv_button_press_for_widget_cells(table.tv, _Ev())

    assert len(got) == 1, "the click was not reported"
    row, col_key = got[0]
    assert isinstance(row, dict), "a table must report the row, not a path"
    assert row['a'] == 'a1'
    assert col_key == 'go'


def test_tree_editability_can_be_changed_after_setup(app):
    """set_editable / set_column_editable reach the renderers that
    setup_table already built (the qt, gtk4 and pg trees took these)."""
    tree = Widgets.TreeView()
    tree.setup_table([('A', 'a'), ('B', 'b')], 1, 'a')
    tree.set_tree({'r0': {'a': 'r0', 'b': 'x'}})

    def editable(i):
        # gtk3 keeps a table-wide flag beside the per-column set;
        # gtk4 folds the flag into the set
        return getattr(tree, 'editable', False) or i in tree._col_editable

    tree.set_editable(True)
    assert editable(0) and editable(1)

    tree.set_editable(False)
    assert not editable(0) and not editable(1)

    tree.set_column_editable(1, True)
    assert editable(1) and not editable(0)

    tree.set_column_editable('b', False)
    assert not editable(1)


@needs_renderers
def test_tree_says_it_has_no_cell_mode(app):
    """gtk3's TreeView selects rows; the cell API is declared so a
    caller is told, rather than meeting an AttributeError."""
    tree = Widgets.TreeView()
    tree.setup_table([('A', 'a')], 1, 'a')
    for call in (lambda: tree.select_cell(['r0'], 'a'),
                 lambda: tree.select_cells([]),
                 lambda: tree.clear_cell_selection(),
                 lambda: tree.get_selected_cells(),
                 lambda: tree.copy_selection(),
                 lambda: tree.cut_selection(),
                 lambda: tree.paste_selection()):
        with pytest.raises(NotImplementedError):
            call()


def test_a_leaf_node_need_not_be_a_plain_dict(app):
    """ginga's own Catalogs plugin fills a tree with catalog.Star
    objects rather than dicts, so a leaf only has to behave like a
    mapping."""
    from ginga.util.catalog import Star

    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 1, 'name')
    tree.set_tree({'s0': Star(name='s0', seeing='0.6')})
    tree.select_path(['s0'])
    assert list(tree.get_selected().keys()) == ['s0']

    # ... and it survives a second pass over the same key
    tree.update_tree({'s0': Star(name='s0', seeing='0.9')})
    assert list(tree.get_selected().keys()) == ['s0']


def test_an_interior_node_need_not_be_a_plain_dict(app):
    """These trees were filled with Bunch interiors long before an
    interior could carry values of its own, when the widget did nothing
    with a parent but iterate it."""
    from ginga.misc.Bunch import Bunch

    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 2, 'name')
    tree.set_tree({'ob1': Bunch(name='OB-042',
                                e1=Bunch(name='e1', seeing='0.6'),
                                e2={'name': 'e2', 'seeing': '0.9'})})

    tree.expand_all(True)
    tree.select_path(['ob1', 'e2'])
    assert list(tree.get_selected().keys()) == ['ob1']
