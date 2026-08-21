"""Tests for the pgw (pgwidgets) backend wrappers.

These exercise the Python-side wrapper layer only -- the callback
redirects and the column/tree marshalling -- so no browser is needed.
The widgets queue their calls on a session that simply has no
connection attached.
"""

import logging

import pytest

try:
    import pgwidgets                         # noqa: F401
except Exception:                            # pragma: no cover
    pytest.skip("pgwidgets not available", allow_module_level=True)

# Import the backend directly rather than through ginga.gw.Widgets:
# that module binds a toolkit at import time, so which widget set it
# offers depends on whether some earlier import already fixed the
# family.  These tests are about the pg wrappers specifically.
from ginga.web.pgw import Widgets  # noqa: E402


@pytest.fixture(scope='module')
def app():
    # no servers are started (that happens in start()/mainloop()), so
    # the port is never bound
    return Widgets.Application(logger=logging.getLogger('test_pgw'),
                               port=25190)


@pytest.fixture
def sent(app):
    """Capture the messages the widgets queue for the browser."""
    msgs = []
    app.default_session._send = lambda msg, **kwargs: msgs.append(msg)
    return msgs


def _calls(msgs, method):
    return [m['args'] for m in msgs
            if isinstance(m, dict) and m.get('method') == method]


# ----- TreeView cell-level callbacks -------------------------------

def test_treeview_enables_cell_callbacks(app):
    """The cell-level callbacks are wired into ginga's callback layer
    rather than falling through to the raw pgwidgets registration."""
    tree = Widgets.TreeView()
    for name in ('cell_edited', 'cell_action', 'cell_selected',
                 'sorted', 'scrolled', 'copy', 'cut', 'paste'):
        assert name in tree.cb, f"{name} not enabled on the pgw TreeView"


def test_treeview_cell_edited_signature(app):
    """A tree's paths are already key lists, so the wrapping must not
    disturb them: (tree, path, col_key, old, new)."""
    tree = Widgets.TreeView()
    got = []
    tree.add_callback('cell_edited',
                      lambda *args: got.append(args))
    tree._cb_redirect_cell_edited(['ob1', 'exp2'], 'note', 'old', 'new')
    assert len(got) == 1
    w, path, col_key, old, new = got[0]
    assert w is tree
    assert path == ['ob1', 'exp2']
    assert (col_key, old, new) == ('note', 'old', 'new')


def test_treeview_cell_action_delivers_a_path(app):
    """A tree names the clicked row by its path, as the qt and gtk
    trees do -- pgwidgets-js sends both that and the row's values."""
    tree = Widgets.TreeView()
    got = []
    tree.add_callback('cell_action', lambda *args: got.append(args))
    tree._cb_redirect_cell_action(['ob1'], {'name': 'ob1', 'go': None}, 'go')
    assert len(got) == 1
    w, path, col_key = got[0]
    assert w is tree
    assert path == ['ob1']
    assert col_key == 'go'


def test_treeview_sorted_and_scrolled_pass_through(app):
    tree = Widgets.TreeView()
    got = []
    tree.add_callback('sorted', lambda *args: got.append(('sorted',) + args[1:]))
    tree.add_callback('scrolled',
                      lambda *args: got.append(('scrolled',) + args[1:]))
    tree._cb_redirect_sorted('seeing', False)
    tree._cb_redirect_scrolled(0.0, 0.5)
    assert got == [('sorted', 'seeing', False), ('scrolled', 0.0, 0.5)]


def test_treeview_clipboard_callbacks(app):
    tree = Widgets.TreeView()
    got = []
    for name in ('copy', 'cut', 'paste'):
        tree.add_callback(name, lambda w, tsv, n=name: got.append((n, tsv)))
    for name in ('copy', 'cut', 'paste'):
        tree._cb_redirect_clipboard('a\tb', name)
    assert got == [('copy', 'a\tb'), ('cut', 'a\tb'), ('paste', 'a\tb')]


# ----- TableView cell_action ---------------------------------------

def test_tableview_cell_action_row_values(app):
    """A table names the clicked row by its values, as the qt and gtk
    tables do -- the path pgwidgets-js also sends is dropped here."""
    table = Widgets.TableView(
        columns=[dict(label='A', key='a'),
                 dict(label='Go', key='go', widget='button', text='Go')])
    table.set_rows([{'a': 'one', 'go': None}, {'a': 'two', 'go': None}])
    got = []
    table.add_callback('cell_action', lambda *args: got.append(args))
    table._cb_redirect_cell_action(['row1'], {'a': 'two', 'go': None}, 'go')
    assert len(got) == 1
    w, row, col_key = got[0]
    assert w is table
    assert row == {'a': 'two', 'go': None}
    assert col_key == 'go'


# ----- setup_table column descriptors ------------------------------

def test_setup_table_accepts_tuples(app, sent):
    tree = Widgets.TreeView()
    del sent[:]
    tree.setup_table([('Name', 'name'), ('Kind', 'kind', 'str'),
                      ('', 'icon')], 2, 'name')
    columns, = _calls(sent, 'set_columns')[-1:]
    assert columns[0] == [
        {'label': 'Name', 'key': 'name', 'type': 'string'},
        {'label': 'Kind', 'key': 'kind', 'type': 'string'},
        # an 'icon' data key is an icon column, matching qt/gtk
        {'label': '', 'key': 'icon', 'type': 'icon'},
    ]
    assert tree.datakeys == ['name', 'kind', 'icon']


def test_setup_table_accepts_dict_columns(app, sent):
    """Full descriptors pass through, so editable/widget columns can be
    declared without a second set_columns() call."""
    tree = Widgets.TreeView()
    del sent[:]
    tree.setup_table([
        dict(label='Name', key='name'),
        dict(label='Note', key='note', editable=True, colwidth='2fr'),
        dict(label='QA', key='qa', widget='combobox',
             choices=['Good', 'Bad'], visible_key='qa_ctl'),
    ], 2, 'name')
    columns, = _calls(sent, 'set_columns')[-1:]
    name, note, qa = columns[0]
    assert name == {'label': 'Name', 'key': 'name', 'type': 'string'}
    assert note['editable'] is True
    assert note['colwidth'] == '2fr'
    assert qa['widget'] == 'combobox'
    assert qa['choices'] == ['Good', 'Bad']
    assert qa['visible_key'] == 'qa_ctl'
    assert tree.datakeys == ['name', 'note', 'qa']


def test_setup_table_dict_key_defaults(app, sent):
    """A descriptor may give only a label, or only a key."""
    tree = Widgets.TreeView()
    del sent[:]
    tree.setup_table([dict(label='Name'), dict(key='kind')], 1, 'name')
    columns, = _calls(sent, 'set_columns')[-1:]
    assert columns[0] == [
        {'label': 'Name', 'key': 'Name', 'type': 'string'},
        {'label': 'kind', 'key': 'kind', 'type': 'string'},
    ]


# ----- add_tree parent ---------------------------------------------

def test_add_tree_merges_at_root_by_default(app, sent):
    tree = Widgets.TreeView()
    del sent[:]
    tree.add_tree({'ob1': {'exp1': {'name': 'x'}}})
    assert _calls(sent, 'add_tree')[-1] == [{'ob1': {'exp1': {'name': 'x'}}},
                                            None]


def test_add_tree_honors_parent(app, sent):
    """Merging under an existing node needs the parent path; without it
    a caller has to fall back to add_item() per child."""
    tree = Widgets.TreeView()
    del sent[:]
    tree.add_tree({'exp3': {'name': 'x'}}, parent=['ob1'])
    assert _calls(sent, 'add_tree')[-1] == [{'exp3': {'name': 'x'}}, ['ob1']]


# ----- batched colour application -----------------------------------

def test_treeview_set_colors_passes_through(app, sent):
    """A tree's paths need no conversion, so the spec goes as-is."""
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 2, 'name')
    del sent[:]
    tree.set_colors(dict(cells=[dict(path=['ob1', 'e1'], col_key='seeing',
                                     fg='red')]))
    spec, = _calls(sent, 'set_colors')[-1]
    assert spec['cells'][0]['path'] == ['ob1', 'e1']


def test_tableview_set_colors_converts_row_indices(app, sent):
    """The single-cell calls take integer row indices, so the batch has
    to as well -- pgwidgets keys rows as 'row0', 'row1', ..."""
    table = Widgets.TableView(columns=[dict(label='A', key='a')])
    table.set_rows([{'a': 'one'}, {'a': 'two'}])
    del sent[:]
    table.set_colors(dict(cells=[dict(path=[1], col_key='a', fg='red')],
                          rows=[dict(path=[0], bg='grey')]))
    spec, = _calls(sent, 'set_colors')[-1]
    assert spec['cells'][0]['path'] == ['row1']
    assert spec['rows'][0]['path'] == ['row0']


# ----- batch context manager ----------------------------------------

def test_widget_batch_coalesces(app, sent):
    """The pg backend buffers a block's calls into one batch message."""
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 2, 'name')
    tree.set_tree({'ob1': {'name': 'ob1', 'seeing': '0.6'}})
    del sent[:]
    with tree.batch():
        tree.set_cell(['ob1'], 'seeing', '1.4')
        tree.set_cell_color(['ob1'], 'seeing', fg='red')
    batches = [m for m in sent if m.get('type') == 'batch']
    assert len(batches) == 1
    assert [m for m in sent if m.get('type') == 'call'] == []


def test_batch_is_available_on_every_widget(app):
    """Application code should be able to use it unconditionally, so it
    lives on the widget base rather than on the tree alone."""
    for w in (Widgets.TreeView(), Widgets.Label('x'), Widgets.Button('b')):
        with w.batch():
            pass


# ----- text widget scrolling and caret --------------------------------

def test_textsource_scrolls_by_ref_with_an_alignment(app, sent):
    """A search centers its match: the alignment rides along with the
    offset the ref resolves to."""
    text = Widgets.TextSource()
    text.set_text("\n".join("line %d" % i for i in range(50)))
    ref = text.get_ref_line_start(20)
    del sent[:]

    text.scroll_to_ref(ref, align='center')

    offset, align = _calls(sent, '_scrollToOffset')[-1]
    assert offset == ref.get_offset()
    assert align == 'center'


def test_textsource_scrolls_to_a_lineno_with_an_alignment(app, sent):
    text = Widgets.TextSource()
    text.set_text("\n".join("line %d" % i for i in range(50)))
    del sent[:]

    text.scroll_to_lineno(20, align='center')
    offset, align = _calls(sent, '_scrollToOffset')[-1]
    assert offset == text.get_ref_line_start(20).get_offset()
    assert align == 'center'

    # the default leaves the view where it is if the line is visible
    text.scroll_to_lineno(20)
    assert _calls(sent, '_scrollToOffset')[-1][1] == 'nearest'


def test_textsource_rejects_an_unknown_alignment(app):
    text = Widgets.TextSource()
    with pytest.raises(ValueError):
        text.scroll_to_lineno(1, align='middle')


def test_textsource_cursor_style_is_pushed_and_remembered(app, sent):
    text = Widgets.TextSource()
    assert text.get_cursor_style() == ('line', None)
    del sent[:]

    text.set_cursor_style('block', color='indianred')

    assert _calls(sent, 'set_cursor_style')[-1] == ['block', 'indianred']
    assert text.get_cursor_style() == ('block', 'indianred')


def test_textsource_cursor_style_survives_a_reconnect(app, sent):
    """A browser that (re)connects gets the caret styling replayed along
    with the rest of the model."""
    text = Widgets.TextSource()
    text.set_cursor_style('block', color='indianred')
    del sent[:]

    text._reconstruct_model()

    assert _calls(sent, 'set_cursor_style')[-1] == ['block', 'indianred']


def test_textsource_rejects_an_unknown_cursor_style(app):
    text = Widgets.TextSource()
    with pytest.raises(ValueError):
        text.set_cursor_style('underline', color='indianred')


def test_textarea_scrolls_to_a_lineno_with_an_alignment(app, sent):
    """The plain TextArea gets the same scrolling API as TextSource."""
    area = Widgets.TextArea()
    area.set_text("\n".join("line %d" % i for i in range(50)))
    del sent[:]

    area.scroll_to_lineno(20, align='center')

    assert _calls(sent, 'scroll_to_lineno')[-1] == [20, 'center']


# ----- API the qt and gtk trees already had --------------------------

def test_treeview_column_widths_can_be_set_positionally(app, sent):
    """qt/gtk take a list of widths by position; pgwidgets names a
    column by its key."""
    tree = Widgets.TreeView()
    tree.setup_table([('A', 'a'), ('B', 'b')], 1, 'a')
    del sent[:]

    tree.set_column_widths([100, None, 999])

    assert _calls(sent, 'set_column_width') == [['a', 100]]


def test_treeview_sorts_by_column_index(app, sent):
    tree = Widgets.TreeView()
    tree.setup_table([('A', 'a'), ('B', 'b')], 1, 'a')
    del sent[:]

    tree.sort_on_column(1)

    assert _calls(sent, 'sort_by_column') == [['b', True]]


def test_treeview_path_background_fills_the_row(app, sent):
    tree = Widgets.TreeView()
    tree.setup_table([('A', 'a')], 1, 'a')
    tree.set_tree({'r0': {'a': 'r0'}})
    del sent[:]

    tree.set_path_background(['r0'], '#ff0000')

    path, fg, bg, bold = _calls(sent, 'set_row_color')[-1]
    assert path == ['r0'] and bg == '#ff0000'


def test_treeview_reports_its_column_widths(app, sent):
    """qt and gtk could report column widths; pgwidgets-js now can too."""
    tree = Widgets.TreeView()
    tree.setup_table([('A', 'a'), ('B', 'b')], 1, 'a')
    del sent[:]

    tree.get_column_widths()

    assert _calls(sent, 'get_column_widths') == [[]]


def test_treeview_flattens_mapping_nodes_for_the_browser(app, sent):
    """A tree may be filled with mapping-like objects that aren't dicts
    -- ``Bunch`` interiors, ``catalog.Star`` leaves -- but only plain
    JSON crosses to the browser, which splits values from children by
    the same rules on its side."""
    import json

    from ginga.misc.Bunch import Bunch
    from ginga.util.catalog import Star

    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Seeing', 'seeing')], 2, 'name')
    del sent[:]

    tree.set_tree({'ob1': Bunch(name='OB-042',
                                e1=Star(name='e1', seeing='0.6'),
                                e2={'name': 'e2', 'seeing': '0.9'})})

    args = _calls(sent, 'set_tree')[-1]
    assert args == [{'ob1': {'name': 'OB-042',
                             'e1': {'name': 'e1', 'seeing': '0.6'},
                             'e2': {'name': 'e2', 'seeing': '0.9'}}}]
    # a Star used to reach the encoder intact, which raised a TypeError
    json.dumps(args)
