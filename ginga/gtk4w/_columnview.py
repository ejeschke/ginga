"""A ColumnView-based TreeView for the gtk4 backend.

``Gtk.TreeView`` and its cell renderers are deprecated in GTK4, and they
cannot host a real widget per cell -- which is why a combo box in a gtk3
tree only appears once you click it, while the qt and pg backends show
one outright.  ``Gtk.ColumnView`` replaces the whole arrangement:

===========================  ====================================
GtkTreeView                  GtkColumnView
===========================  ====================================
``Gtk.TreeStore(object)``    a ``GListModel`` of row objects
nested stores                ``Gtk.TreeListModel`` + expanders
cell renderer + data func    a factory per column, binding widgets
``set_sort_column_id``       a ``Gtk.Sorter`` per column
``Gtk.TreeSelection``        ``Single``/``MultiSelection``
``TreePath`` / ``TreeIter``  list positions and row objects
===========================  ====================================

The wrapper's public API is unchanged: the same ``setup_table`` /
``set_tree`` / ``get_selected`` / colour / editing calls as the other
backends, with paths still being lists of the caller's own keys.  Only
the machinery underneath differs.

This module holds the model and the row plumbing; the widget class
builds on it.
"""

from gi.repository import Gdk, GLib, GObject, Gio, Gtk

from ginga import colors

_CELL_WIDGETS = ('checkbox', 'combobox', 'progress', 'button')

from ginga.misc import Bunch
from ginga.util import treehelper
from ginga.gtk4w import GtkHelp


class Row(GObject.Object):
    """One row of the view.

    A GListModel can only hold GObjects, so the caller's dict of column
    values is carried by one of these.  The object's identity is the
    row's identity: it survives sorting and re-filtering, which is what
    lets a path, a colour override or a selection stay attached to the
    right row.
    """

    __gtype_name__ = 'GingaColumnViewRow'

    def __init__(self, key, values=None, parent=None, is_leaf=True):
        super().__init__()
        self.key = key
        # the caller's own dict for a leaf; for an interior, the values
        # it declared (which may be empty)
        self.values = {} if values is None else values
        self.parent = parent
        self.is_leaf = is_leaf
        # children are created lazily: Gtk.TreeListModel asks for them
        # only when a row is expanded
        self.children = None
        # the columns this row actually supplied, as opposed to the
        # blanks an interior is padded with.  Only supplied cells are
        # editable -- filler is not content.
        self.supplied = set(self.values.keys())

    # -- tree shape --

    def ensure_children(self):
        """The child model, created on first use."""
        if self.children is None and not self.is_leaf:
            self.children = Gio.ListStore.new(Row)
        return self.children

    def child(self, key):
        if self.children is None:
            return None
        for row in self.children:
            if row.key == key:
                return row
        return None

    def child_keys(self):
        if self.children is None:
            return []
        return [row.key for row in self.children]

    def remove_child(self, key):
        if self.children is None:
            return False
        for i, row in enumerate(self.children):
            if row.key == key:
                self.children.remove(i)
                return True
        return False

    # -- values --

    def update_values(self, values):
        """Replace this row's column data, keeping the object identity
        so anything attached to the row stays attached."""
        self.values.clear()
        self.values.update(values)
        self.supplied = set(values.keys())

    def get(self, col_key, default=''):
        return self.values.get(col_key, default)

    @property
    def path(self):
        """The row's key path, built from the chain of parents.

        Independent of position, so it is unaffected by sorting.
        """
        parts = []
        row = self
        while row is not None and row.key is not None:
            parts.append(row.key)
            row = row.parent
        parts.reverse()
        return parts

    def __repr__(self):
        kind = 'leaf' if self.is_leaf else 'node'
        return f'<Row {kind} {"/".join(self.path)}>'


def build_tree(tree_dict, levels, parent=None, store=None):
    """Turn a dict-tree into Row objects.

    `levels` is the depth at which nodes become leaves, matching
    ``setup_table``.  Interior nodes may carry their own column values
    (see :mod:`ginga.util.treehelper`), which do not become children.
    """
    if store is None:
        store = Gio.ListStore.new(Row)
    depth = 1 if parent is None else len(parent.path) + 1

    for key, node in (tree_dict or {}).items():
        if depth >= levels:
            row = Row(key, values=node, parent=parent, is_leaf=True)
            store.append(row)
            continue

        values, children = treehelper.split_node(node)
        row = Row(key, values=values, parent=parent, is_leaf=False)
        store.append(row)
        if children:
            build_tree(children, levels, parent=row,
                       store=row.ensure_children())
    return store


def merge_tree(store, tree_dict, levels, parent=None):
    """Add or update rows from `tree_dict` without disturbing the rest.

    Rows that already exist keep their object identity -- and with it
    their selection, expansion and colour overrides -- and simply take
    the new values.  Returns the rows that were newly created.
    """
    added = []
    depth = 1 if parent is None else len(parent.path) + 1

    for key, node in (tree_dict or {}).items():
        existing = None
        for row in store:
            if row.key == key:
                existing = row
                break

        if depth >= levels:
            if existing is None:
                row = Row(key, values=node, parent=parent, is_leaf=True)
                store.append(row)
                added.append(row)
            else:
                existing.update_values(node)
            continue

        values, children = treehelper.split_node(node)
        if existing is None:
            existing = Row(key, values=values, parent=parent, is_leaf=False)
            store.append(existing)
            added.append(existing)
        else:
            existing.update_values(values)
        if children:
            added.extend(merge_tree(existing.ensure_children(), children,
                                    levels, parent=existing))
    return added


def prune_tree(store, tree_dict, levels, parent=None):
    """Remove rows that `tree_dict` no longer mentions."""
    depth = 1 if parent is None else len(parent.path) + 1
    keys = set((tree_dict or {}).keys())
    removed = 0

    for row in list(store):
        if row.key not in keys:
            store.remove(_position_of(store, row))
            removed += 1
            continue
        if depth < levels and row.children is not None:
            _, children = treehelper.split_node(tree_dict[row.key])
            removed += prune_tree(row.children, children, levels,
                                  parent=row)
    return removed


def _position_of(store, row):
    for i, candidate in enumerate(store):
        if candidate is row:
            return i
    raise ValueError('row not in store')


def row_at_path(store, path):
    """Find a row by its key path, or None."""
    rows = store
    row = None
    for key in path:
        row = None
        for candidate in (rows or []):
            if candidate.key == key:
                row = candidate
                break
        if row is None:
            return None
        rows = row.children
    return row


def walk_rows(store, include_leaves=True, include_nodes=True):
    """Yield every row in the store, depth first."""
    for row in (store or []):
        if (row.is_leaf and include_leaves) or \
                (not row.is_leaf and include_nodes):
            yield row
        if row.children is not None:
            yield from walk_rows(row.children, include_leaves,
                                 include_nodes)


def to_dict(rows):
    """Rebuild a plain dict-tree from Row objects.

    Used for the ``get_selected`` / ``get_children`` results, which keep
    the shape they have always had: children only, no interior values.
    """
    out = {}
    for row in rows:
        if row.is_leaf:
            out[row.key] = row.values
        else:
            out[row.key] = to_dict(row.children or [])
    return out


def insert_into(res_dict, row):
    """Place `row` in `res_dict` under its key path, as the older
    backends' ``_get_item`` did."""
    d = res_dict
    path = row.path
    for name in path[:-1]:
        d = d.setdefault(name, {})
    if row.is_leaf:
        d[path[-1]] = row.values
    else:
        d.setdefault(path[-1], {})
    return res_dict


def make_shadow(store):
    """A Bunch-based index mirroring the older backends' ``shadow``.

    Some callers reach into it, so it is reproduced rather than
    dropped; the rows themselves remain the source of truth.
    """
    shadow = {}
    for row in (store or []):
        shadow[row.key] = Bunch.Bunch(
            node=(row.values if row.is_leaf else make_shadow(row.children)),
            item=row, terminal=row.is_leaf)
    return shadow


class ColumnViewTreeMixin:
    """The GTK4 plumbing for a ColumnView-based tree.

    Kept apart from the wrapper class so this module needn't import
    Widgets (which would be circular).  The wrapper mixes it in and
    supplies ``WidgetBase``.
    """

    def _cv_init(self, selection='single', auto_expand=False,
                 sortable=False, use_alt_row_color=False):
        self.auto_expand = auto_expand
        self.sortable = sortable
        self.selection = selection
        self.levels = 1
        self.leaf_key = None
        self.leaf_idx = 0
        self.columns = []
        self.col_specs = []
        self.datakeys = []
        self.datatypes = []
        self._cell_labels = {}
        self._expansion_handlers = {}
        # colour overrides, resolved per cell at bind/refresh time
        self._cell_styles = {}
        self._row_styles = {}
        self._column_styles = {}
        self._table_style = None
        # per-column editing, filled in by setup_table
        self._col_editable = set()
        # cell-level selection, when the view is in a cell mode
        self._cell_selection = set()
        # guard: our own cell click selects a cell and must not be
        # taken for the user picking rows
        self._in_cell_click = False
        # generated colour classes: (fg, bg, bold) -> class name
        self._color_classes = {}
        self._color_rules = {}

        # the caller's rows
        self.store = Gio.ListStore.new(Row)
        # ... wrapped so GTK can expand them
        self.tree_model = Gtk.TreeListModel.new(
            self.store, False, auto_expand, self._child_model_for)

        # The view is built first so its sorter can be put in the model
        # chain.  Gtk.TreeListRowSorter is the piece that keeps the
        # hierarchy intact: it applies the column's sorter within each
        # level, so children stay under their own parent instead of
        # being flattened in with everyone else.
        self.cv = Gtk.ColumnView.new(None)
        self.row_sorter = Gtk.TreeListRowSorter.new(self.cv.get_sorter())
        self.sort_model = Gtk.SortListModel.new(self.tree_model,
                                                self.row_sorter)
        if selection == 'multiple':
            self.selection_model = Gtk.MultiSelection.new(self.sort_model)
        elif selection == 'multiple-cell':
            # cell selection sits on top of row selection rather than
            # replacing it, so a table in a cell mode can still have
            # its rows picked
            self.selection_model = Gtk.MultiSelection.new(self.sort_model)
        else:
            self.selection_model = Gtk.SingleSelection.new(self.sort_model)
            self.selection_model.set_autoselect(False)
            self.selection_model.set_can_unselect(True)
        self.cv.set_model(self.selection_model)
        self.cv.set_show_row_separators(False)
        self.cv.set_show_column_separators(False)
        if use_alt_row_color:
            self.cv.add_css_class('alternating')
        # cell cursor: (position, col_idx) in *display* order, for
        # keyboard navigation
        self._cursor = None
        if getattr(self, 'dragable', False):
            # GTK4 drags start from a DragSource controller; the payload
            # is built when the drag begins, by whoever listens for
            # 'drag-start'
            source = Gtk.DragSource()
            source.set_actions(Gdk.DragAction.COPY)
            source.connect('prepare', self._cv_drag_prepare_cb)
            self.cv.add_controller(source)

        keys = Gtk.EventControllerKey.new()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed', self._cv_key_pressed_cb)
        self.cv.add_controller(keys)
        self.cv.connect('activate', self._cv_activate_cb)
        self.cv.get_sorter().connect('changed',
                                     self._cv_sorter_changed_cb)
        self.selection_model.connect('selection-changed',
                                     self._cv_selection_cb)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(self.cv)
        self.widget = sw

    # -- model plumbing --

    @staticmethod
    def _child_model_for(item):
        """Hand GTK the children of a row, when it asks.

        Returning None marks a row as a leaf, which is what stops an
        expander appearing on it.
        """
        if item.is_leaf:
            return None
        return item.ensure_children()

    def _tree_row_for(self, row):
        """The Gtk.TreeListRow wrapping one of our rows, if it is
        currently on show."""
        for i in range(self.selection_model.get_n_items()):
            tree_row = self.selection_model.get_item(i)
            if tree_row is not None and tree_row.get_item() is row:
                return tree_row
        return None

    # -- columns --

    def setup_table(self, columns, levels, leaf_key):
        self.clear()
        self.columns = columns
        self.levels = levels
        self.leaf_key = leaf_key

        specs = [treehelper.normalize_column(col, i)
                 for i, col in enumerate(columns)]
        self.col_specs = specs
        self.datakeys = [spec['key'] for spec in specs]
        self.datatypes = [spec['type'] for spec in specs]
        self._col_editable = set(i for i, spec in enumerate(specs)
                                 if spec.get('editable'))
        self.leaf_idx = (self.datakeys.index(leaf_key)
                         if leaf_key in self.datakeys else 0)

        for column in list(self.cv.get_columns()):
            self.cv.remove_column(column)

        for i, spec in enumerate(specs):
            factory = Gtk.SignalListItemFactory()
            # the first column carries the expander, so the hierarchy
            # is visible there
            factory.connect('setup', self._cv_setup_cb, i, i == 0)
            factory.connect('bind', self._cv_bind_cb, i, i == 0)
            factory.connect('unbind', self._cv_unbind_cb, i)
            column = Gtk.ColumnViewColumn.new(spec['label'], factory)
            column.set_resizable(True)
            column.set_expand(spec.get('colwidth') is None)
            if self.sortable:
                column.set_sorter(self._make_column_sorter(i))
            self.cv.append_column(column)

    def _widget_kind(self, col_idx):
        spec = self.col_specs[col_idx]
        wtype = spec.get('widget')
        if wtype in _CELL_WIDGETS:
            return wtype
        # the older column types map onto widgets too: an icon column
        # holds a picture, a check column a toggle
        if spec.get('type') == 'icon':
            return 'icon'
        if spec.get('type') == 'check':
            return 'checkbox'
        if col_idx in self._col_editable:
            return 'text-edit'
        return 'text'

    def _cv_setup_cb(self, factory, list_item, col_idx, is_tree_column):
        """Build the cell's widget.

        This is where a ColumnView earns its keep: the cell holds a real
        control, so a combo box or a check button is usable straight
        away rather than appearing only once the cell is activated.
        """
        kind = self._widget_kind(col_idx)
        if kind == 'checkbox':
            widget = Gtk.CheckButton()
            widget.connect('toggled', self._cv_cell_changed_cb, col_idx)
        elif kind == 'combobox':
            choices = [str(c) for c in
                       (self.col_specs[col_idx].get('choices') or [])]
            widget = Gtk.DropDown.new_from_strings(choices)
            widget.connect('notify::selected', self._cv_cell_changed_cb,
                           col_idx)
        elif kind == 'icon':
            widget = Gtk.Image()
            widget.set_halign(Gtk.Align.CENTER)
        elif kind == 'progress':
            widget = Gtk.ProgressBar()
            widget.set_valign(Gtk.Align.CENTER)
        elif kind == 'button':
            widget = Gtk.Button()
            # sized to its label rather than filling the cell, so a row
            # colour shows around it as it does on the qt backend
            widget.set_halign(Gtk.Align.CENTER)
            widget.set_valign(Gtk.Align.CENTER)
            widget.connect('clicked', self._cv_cell_clicked_cb, col_idx)
        elif kind == 'text-edit':
            widget = Gtk.EditableLabel()
            widget.connect('notify::editing', self._cv_editing_done_cb,
                           col_idx)
        else:
            widget = Gtk.Label()
            widget.set_xalign(self._xalign_for(col_idx))
            widget.set_ellipsize(3)      # Pango.EllipsizeMode.END
            widget.set_hexpand(True)
            widget.set_halign(Gtk.Align.FILL)

        self._attach_cell_click(widget, col_idx)
        if is_tree_column:
            expander = Gtk.TreeExpander()
            expander.set_child(widget)
            list_item.set_child(expander)
        else:
            list_item.set_child(widget)

    def _cv_bind_cb(self, factory, list_item, col_idx, is_tree_column):
        tree_row = list_item.get_item()
        row = tree_row.get_item()
        child = list_item.get_child()
        if is_tree_column:
            child.set_list_row(tree_row)
            label = child.get_child()
            if tree_row.is_expandable():
                self._watch_expansion(tree_row)
        else:
            label = child

        # Remember the binding: a row's values can change while it is
        # on screen, and editing them in place does not re-run this
        # factory, so _refresh_bound_cells updates the widgets directly.
        self._cell_labels[(id(row), col_idx)] = (row, label)
        label._ginga_row = row
        self._apply_cell(row, col_idx, label)

    def _cv_unbind_cb(self, factory, list_item, col_idx):
        tree_row = list_item.get_item()
        if tree_row is not None:
            row = tree_row.get_item()
            self._cell_labels.pop((id(row), col_idx), None)
            if col_idx == 0:
                self._unwatch_expansion(tree_row)

    def _set_cell_text(self, row, col_idx, label):
        col_key = self.datakeys[col_idx]
        value = row.get(col_key, '')
        if value is None:
            value = ''
        # an interior with nothing to say in the first column shows its
        # own key, as these rows always have
        if col_idx == 0 and value == '' and col_key not in row.supplied:
            value = row.key

        label.set_text(str(value))

    def _refresh_bound_cells(self):
        """Push current values into the cells that are on screen."""
        for (_row_id, col_idx), (row, widget) in list(
                self._cell_labels.items()):
            self._apply_cell(row, col_idx, widget)

    def _xalign_for(self, col_idx):
        halign = (self.col_specs[col_idx].get('halign')
                  if col_idx < len(self.col_specs) else None)
        return {'right': 1.0, 'center': 0.5}.get(halign, 0.0)

    # -- contents --

    def clear(self):
        if getattr(self, 'store', None) is not None:
            self.store.remove_all()
        self._cell_labels = {}

    def set_tree(self, tree_dict):
        self.clear()
        build_tree(tree_dict, self.levels, store=self.store)
        if self.auto_expand:
            self.expand_all(True)

    def add_tree(self, tree_dict, expand_new=False):
        added = merge_tree(self.store, tree_dict, self.levels)
        if expand_new or self.auto_expand:
            for row in added:
                self._set_expanded(row, True)
        self._refresh_bound_cells()

    def update_tree(self, tree_dict, expand_new=False):
        prune_tree(self.store, tree_dict, self.levels)
        added = merge_tree(self.store, tree_dict, self.levels)
        if expand_new or self.auto_expand:
            for row in added:
                self._set_expanded(row, True)
        self._refresh_bound_cells()

    def _row_at(self, path):
        return row_at_path(self.store, path)

    def _path_for_row(self, row):
        """How a row is named to callers.

        A tree reports the key path; a flat table overrides this to
        report the row's index, as the qt and pg tables do.
        """
        return row.path

    # -- expansion --

    def _set_expanded(self, row, tf):
        tree_row = self._tree_row_for(row)
        if tree_row is not None:
            tree_row.set_expanded(tf)

    def expand_all(self, tf):
        # expanding reveals more rows, which may themselves expand, so
        # keep going until the count settles
        seen = -1
        while seen != self.selection_model.get_n_items():
            seen = self.selection_model.get_n_items()
            for i in range(seen):
                tree_row = self.selection_model.get_item(i)
                if tree_row is not None and tree_row.is_expandable():
                    tree_row.set_expanded(tf)
            if not tf:
                break

    # -- results --

    def get_children(self, status='all'):
        res_dict = {}
        for row in walk_rows(self.store, include_nodes=False):
            insert_into(res_dict, row)
        return res_dict

    def get_selected(self):
        res_dict = {}
        for row in self._selected_rows():
            if row.is_leaf:
                insert_into(res_dict, row)
        return res_dict

    def get_selected_paths(self):
        return [self._path_for_row(row) for row in self._selected_rows()]

    def _selected_rows(self):
        rows = []
        model = self.selection_model
        for i in range(model.get_n_items()):
            if model.is_selected(i):
                # NB: read from the same model the index came from --
                # positions are in sorted order, and the unsorted model
                # would hand back a different row entirely
                tree_row = model.get_item(i)
                if tree_row is not None:
                    rows.append(tree_row.get_item())
        return rows

    # -- callbacks --

    def _cv_drag_prepare_cb(self, source, x, y):
        """Build the drag payload from the current selection."""
        res_dict = self.get_selected()
        if not res_dict:
            # nothing selected yet -- take the row under the pointer
            row = self._row_at_point(x, y)
            if row is None:
                return None
            res_dict = {}
            insert_into(res_dict, row)
        from ginga.gtk4w.Widgets import DragPackage
        pkg = DragPackage(self.cv)
        self.make_callback('drag-start', pkg, res_dict)
        return pkg.content_provider()

    def _row_at_point(self, x, y):
        """The row whose cell covers a point in view coordinates."""
        for (_row_id, _col_idx), (row, widget) in self._cell_labels.items():
            ok, rect = widget.compute_bounds(self.cv)
            if not ok:
                continue
            if (rect.origin.x <= x < rect.origin.x + rect.size.width and
                    rect.origin.y <= y < rect.origin.y + rect.size.height):
                return row
        return None

    def _cv_activate_cb(self, view, position):
        tree_row = self.selection_model.get_item(position)
        if tree_row is None:
            return
        res_dict = {}
        insert_into(res_dict, tree_row.get_item())
        self.make_callback('activated', res_dict)

    def _cv_selection_cb(self, model, position, n_items):
        # picking rows drops any cell selection, the way picking a
        # column drops the row selection -- one selection at a time
        if (self._cell_mode() and self._cell_selection and
                not self._in_cell_click):
            for i in range(model.get_n_items()):
                if model.is_selected(i):
                    self._cell_selection = set()
                    self._refresh_bound_cells()
                    self.make_callback('cell_selected',
                                       self.get_selected_cells())
                    break
        self.make_callback('selected', self.get_selected())

    # -- keyboard navigation ------------------------------------------
    #
    # A ColumnView navigates by row: the arrow keys move the selection
    # up and down and that is all.  qt and pg tables give you a cell
    # cursor -- arrows and Tab walk cell to cell, Return or a printable
    # character starts editing -- so that is built here on top of the
    # bound cell widgets.

    def _editable_at(self, position, col_idx):
        """The editable widget of a cell, if that cell is on screen and
        takes edits."""
        if col_idx not in getattr(self, '_col_editable', ()):
            return None
        tree_row = self.selection_model.get_item(position)
        if tree_row is None:
            return None
        row = tree_row.get_item()
        entry = self._cell_labels.get((id(row), col_idx))
        if entry is None:
            return None
        widget = entry[1]
        return widget if isinstance(widget, Gtk.EditableLabel) else None

    def _cursor_cell(self):
        """The cursor as ``(position, col_idx)``, defaulting to the
        first selected row, or the first row."""
        if self._cursor is not None:
            return self._cursor
        position = None
        for i in range(self.selection_model.get_n_items()):
            if self.selection_model.is_selected(i):
                position = i
                break
        if position is None:
            position = 0 if self.selection_model.get_n_items() else None
        if position is None:
            return None
        return (position, 0)

    def set_cursor_cell(self, position, col_idx, edit=False):
        """Put the cell cursor on a cell, scroll it into view and give
        it the focus.  In a cell selection mode the cell is selected
        too, so the cursor is visible."""
        n_rows = self.selection_model.get_n_items()
        n_cols = len(self.datakeys)
        if n_rows == 0 or n_cols == 0:
            return False
        position = max(0, min(position, n_rows - 1))
        col_idx = max(0, min(col_idx, n_cols - 1))
        self._cursor = (position, col_idx)

        column = None
        columns = self.cv.get_columns()
        col_pos = col_idx + self._col_offset()
        if col_pos < columns.get_n_items():
            column = columns.get_item(col_pos)
        try:
            self.cv.scroll_to(position, column, Gtk.ListScrollFlags.FOCUS,
                              None)
        except TypeError:            # older pygobject signature
            self.cv.scroll_to(position, column, Gtk.ListScrollFlags.FOCUS)

        if self._cell_mode():
            tree_row = self.selection_model.get_item(position)
            if tree_row is not None:
                path = self._path_for_row(tree_row.get_item())
                self._cell_selection = set()
                self.select_cells([dict(path=path,
                                        col_key=self.datakeys[col_idx])])
                self.make_callback('cell_selected', self.get_selected_cells())

        widget = self._editable_at(position, col_idx)
        if widget is not None:
            widget.grab_focus()
            if edit:
                widget.start_editing()
        return True

    def _move_cursor(self, d_row, d_col, wrap=False):
        cur = self._cursor_cell()
        if cur is None:
            return False
        position, col_idx = cur
        n_rows = self.selection_model.get_n_items()
        n_cols = len(self.datakeys)
        position += d_row
        col_idx += d_col
        if wrap:
            # Tab runs off the end of a row onto the start of the next
            while col_idx < 0:
                col_idx += n_cols
                position -= 1
            while col_idx >= n_cols:
                col_idx -= n_cols
                position += 1
        if not (0 <= position < n_rows) or not (0 <= col_idx < n_cols):
            return False
        return self.set_cursor_cell(position, col_idx)

    def _seed_editor(self, widget, char):
        """Put a typed character into a cell's editor, replacing what
        was there -- typing over a cell replaces it, as in a
        spreadsheet."""
        if widget.get_text() != char:
            widget.set_text(char)
        delegate = widget.get_delegate()
        if delegate is not None:
            delegate.set_text(char)
            delegate.set_position(-1)
        return False

    def _cv_key_pressed_cb(self, controller, keyval, keycode, state):
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        # while a cell is being edited the entry owns the keyboard --
        # except for Tab, which commits and steps to the next cell the
        # way it does in a spreadsheet (Return and Escape the editable
        # label already handles itself)
        focus = self.cv.get_root() and self.cv.get_root().get_focus()
        if isinstance(focus, Gtk.Text):
            # Keys that leave the cell commit what was typed and move
            # the cursor, as in a spreadsheet.  Without this they fall
            # through to the ColumnView, which moves the *row*
            # selection and takes the focus away -- cancelling the
            # edit, so the cell appears to revert.  Left/Right stay
            # with the entry, moving the caret, and Escape still
            # cancels.
            moves = {Gdk.KEY_Tab: (0, 1), Gdk.KEY_ISO_Left_Tab: (0, -1),
                     Gdk.KEY_Up: (-1, 0), Gdk.KEY_KP_Up: (-1, 0),
                     Gdk.KEY_Down: (1, 0), Gdk.KEY_KP_Down: (1, 0),
                     Gdk.KEY_Return: (1, 0), Gdk.KEY_KP_Enter: (1, 0)}
            if keyval not in moves:
                return False
            d_row, d_col = moves[keyval]
            if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab) and shift:
                d_col = -d_col
            editor = focus
            while editor is not None and not isinstance(editor,
                                                        Gtk.EditableLabel):
                editor = editor.get_parent()
            if editor is None:
                return False
            editor.stop_editing(True)
            wrap = keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab)
            self._move_cursor(d_row, d_col, wrap=wrap)
            return True

        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK or
                    state & Gdk.ModifierType.META_MASK)
        if ctrl:
            # Clipboard, as the qt table binds it -- and only while the
            # view itself has the keyboard, so an open cell editor
            # keeps its own Ctrl+C/X/V for the text it holds (the
            # editing branch above has returned by then).
            clip = {Gdk.KEY_c: self.copy_selection,
                    Gdk.KEY_x: self.cut_selection,
                    Gdk.KEY_v: self.paste_selection}.get(
                        Gdk.keyval_to_lower(keyval))
            if clip is None:
                return False
            clip()
            return True

        if keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            return self._move_cursor(0, -1 if shift else 1, wrap=True)
        if keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            return self._move_cursor(0, -1)
        if keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            return self._move_cursor(0, 1)
        if keyval in (Gdk.KEY_Up, Gdk.KEY_KP_Up):
            return self._move_cursor(-1, 0)
        if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
            return self._move_cursor(1, 0)
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_F2):
            cur = self._cursor_cell()
            if cur is None:
                return False
            return self.set_cursor_cell(cur[0], cur[1], edit=True)

        # a printable character starts an edit, the way typing into a
        # spreadsheet does -- space included, so it replaces the cell
        # like any other character rather than activating the row
        char = chr(Gdk.keyval_to_unicode(keyval) or 0)
        if char and (char.isprintable() or char == ' '):
            cur = self._cursor_cell()
            if cur is None:
                return False
            widget = self._editable_at(cur[0], cur[1])
            if widget is None:
                return False
            # Seed the editor when it is genuinely up.  start_editing()
            # copies the cell's current text into the entry, and doing
            # it any earlier means that copy lands on top of the
            # character typed -- which reads as typing doing nothing.
            handler = []

            def on_editing(w, _pspec):
                if w.get_property('editing'):
                    self._seed_editor(w, char)
                    if handler:
                        w.disconnect(handler[0])
                        handler.clear()

            handler.append(widget.connect('notify::editing', on_editing))
            self.set_cursor_cell(cur[0], cur[1], edit=True)
            if widget.get_property('editing'):
                self._seed_editor(widget, char)
                if handler:
                    widget.disconnect(handler[0])
                    handler.clear()
            GLib.idle_add(self._seed_editor, widget, char)
            return True
        return False

    # -- selection and expansion --------------------------------------
    #
    # A TreeListModel only lists the rows currently on show, so a row
    # inside a collapsed parent has no position.  Anything that works by
    # position expands the ancestors first.

    def _position_of_row(self, row):
        for i in range(self.selection_model.get_n_items()):
            tree_row = self.selection_model.get_item(i)
            if tree_row is not None and tree_row.get_item() is row:
                return i
        return None

    def _expand_ancestors(self, row):
        chain = []
        parent = row.parent
        while parent is not None and parent.key is not None:
            chain.append(parent)
            parent = parent.parent
        for ancestor in reversed(chain):
            tree_row = self._tree_row_for(ancestor)
            if tree_row is not None:
                tree_row.set_expanded(True)

    def select_row_at(self, position):
        """Select the row at a display position, as a click on it
        would.  Used when the cell gesture claims the press."""
        if position is None or not (0 <= position <
                                    self.selection_model.get_n_items()):
            return
        self.selection_model.select_item(position, True)

    def select_path(self, path, state=True):
        row = self._row_at(path)
        if row is None:
            return
        self._expand_ancestors(row)
        pos = self._position_of_row(row)
        if pos is None:
            return
        if state:
            self.selection_model.select_item(pos, False)
        else:
            self.selection_model.unselect_item(pos)

    def select_paths(self, paths, state=True):
        for path in paths:
            self.select_path(path, state=state)

    def select_all(self, state=True):
        if state:
            self.selection_model.select_all()
        else:
            self.selection_model.unselect_all()

    def clear_selection(self):
        self.selection_model.unselect_all()

    def _set_expanded_path(self, path, tf):
        row = self._row_at(path)
        if row is None:
            return
        if tf:
            self._expand_ancestors(row)
        self._set_expanded(row, tf)

    def get_expanded(self):
        return self._rows_by_expansion(True)

    def get_collapsed(self):
        return self._rows_by_expansion(False)

    def _rows_by_expansion(self, expanded):
        res_dict = {}
        for i in range(self.selection_model.get_n_items()):
            tree_row = self.selection_model.get_item(i)
            if tree_row is None or not tree_row.is_expandable():
                continue
            if bool(tree_row.get_expanded()) is expanded:
                row = tree_row.get_item()
                for leaf in walk_rows(row.children or [],
                                      include_nodes=False):
                    insert_into(res_dict, leaf)
                res_dict.setdefault(row.key, {})
        return res_dict

    def _watch_expansion(self, tree_row):
        """Report expand/collapse the way the other backends do."""
        if tree_row in self._expansion_handlers:
            return
        handler = tree_row.connect('notify::expanded',
                                   self._cv_expanded_cb)
        self._expansion_handlers[tree_row] = handler

    def _unwatch_expansion(self, tree_row):
        handler = self._expansion_handlers.pop(tree_row, None)
        if handler is not None:
            try:
                tree_row.disconnect(handler)
            except (TypeError, ValueError):      # already finalised
                pass

    def _cv_expanded_cb(self, tree_row, _pspec):
        row = tree_row.get_item()
        if row is None:
            return
        name = 'expanded' if tree_row.get_expanded() else 'collapsed'
        self.make_callback(name, self._path_for_row(row))

    # -- sorting -------------------------------------------------------

    def _make_column_sorter(self, col_idx):
        """A sorter comparing one column's values.

        Gtk.TreeListRowSorter hands us the rows themselves, so this
        compares Row objects.  Blanks sort last either way, matching
        the other backends, so rows that say nothing about the sort
        column don't scatter through the order.
        """
        col_key = self.datakeys[col_idx]
        datatype = self.datatypes[col_idx]

        def compare(row_a, row_b, _data=None):
            a = row_a.get(col_key, '')
            b = row_b.get(col_key, '')
            if a == '' and b != '':
                return 1
            if b == '' and a != '':
                return -1
            if datatype in ('int', 'float', 'number'):
                try:
                    a, b = float(a), float(b)
                except (TypeError, ValueError):
                    a, b = str(a), str(b)
            else:
                a, b = str(a), str(b)
            return (a > b) - (a < b)

        return Gtk.CustomSorter.new(compare)

    def sort_on_column(self, i):
        columns = self.cv.get_columns()
        if 0 <= i < len(columns):
            self.cv.sort_by_column(columns[i], Gtk.SortType.ASCENDING)

    def _cv_sorter_changed_cb(self, sorter, _change):
        """Report a sort the way the other backends do: by column key
        and direction."""
        column = sorter.get_primary_sort_column()
        if column is None:
            return
        try:
            idx = list(self.cv.get_columns()).index(column)
        except ValueError:
            return
        ascending = (sorter.get_primary_sort_order() ==
                     Gtk.SortType.ASCENDING)
        self.make_callback('sorted', self.datakeys[idx], ascending)

    # -- navigation and geometry --------------------------------------

    def scroll_to_path(self, path):
        row = self._row_at(path)
        if row is None:
            return
        self._expand_ancestors(row)
        pos = self._position_of_row(row)
        if pos is not None:
            self.cv.scroll_to(pos, None, Gtk.ListScrollFlags.NONE, None)

    def scroll_to_end(self):
        n = self.selection_model.get_n_items()
        if n > 0:
            self.cv.scroll_to(n - 1, None, Gtk.ListScrollFlags.NONE, None)

    def set_column_width(self, i, width):
        columns = self.cv.get_columns()
        if 0 <= i < len(columns):
            columns[i].set_fixed_width(width)
            columns[i].set_expand(False)

    def set_column_widths(self, lwidths):
        for i, width in enumerate(lwidths):
            if width is not None:
                self.set_column_width(i, width)

    def get_column_widths(self):
        return [column.get_fixed_width() for column in self.cv.get_columns()]

    def set_optimal_column_widths(self):
        # ColumnView sizes columns itself; let it, by dropping any
        # fixed widths previously imposed
        for column in self.cv.get_columns():
            column.set_fixed_width(-1)
            column.set_expand(True)

    # -- colour overrides ----------------------------------------------
    #
    # Same API as the other backends, including the per-channel cascade
    # cell > row > column > table.  A cell here is a real label widget,
    # so the styling is applied to it directly (as Pango markup) rather
    # than by setting properties on a shared renderer.

    @staticmethod
    def _style_path(path):
        return tuple(path) if isinstance(path, (list, tuple)) else (path,)

    @staticmethod
    def _style_or_none(fg, bg, bold):
        if fg is None and bg is None and bold is None:
            return None
        return dict(fg=fg, bg=bg, bold=bold)

    def _resolve_style(self, row, col_key):
        fg = bg = bold = None
        path_key = tuple(self._path_for_row(row))
        for layer in (self._cell_styles.get((path_key, col_key)),
                      self._row_styles.get(path_key),
                      self._column_styles.get(col_key),
                      self._table_style):
            if not layer:
                continue
            if fg is None:
                fg = layer.get('fg')
            if bg is None:
                bg = layer.get('bg')
            if bold is None:
                bold = layer.get('bold')
        return fg, bg, bold

    @staticmethod
    def _css_color(value):
        """A colour Pango will accept, resolved the same way the other
        backends resolve it so the palettes agree."""
        if value is None:
            return None
        try:
            return colors.resolve_color(value, format='hex')
        except Exception:
            return str(value)

    def set_cell_color(self, path, col_key, fg=None, bg=None, bold=None):
        key = (self._style_path(path), col_key)
        style = self._style_or_none(fg, bg, bold)
        if style is None:
            self._cell_styles.pop(key, None)
        else:
            self._cell_styles[key] = style
        self._refresh_bound_cells()

    def set_row_color(self, path, fg=None, bg=None, bold=None):
        key = self._style_path(path)
        style = self._style_or_none(fg, bg, bold)
        if style is None:
            self._row_styles.pop(key, None)
        else:
            self._row_styles[key] = style
        self._refresh_bound_cells()

    def set_column_color(self, col_key, fg=None, bg=None, bold=None):
        style = self._style_or_none(fg, bg, bold)
        if style is None:
            self._column_styles.pop(col_key, None)
        else:
            self._column_styles[col_key] = style
        self._refresh_bound_cells()

    def set_table_color(self, fg=None, bg=None, bold=None):
        self._table_style = self._style_or_none(fg, bg, bold)
        self._refresh_bound_cells()

    def clear_cell_color(self, path, col_key):
        self._cell_styles.pop((self._style_path(path), col_key), None)
        self._refresh_bound_cells()

    def clear_row_color(self, path):
        self._row_styles.pop(self._style_path(path), None)
        self._refresh_bound_cells()

    def clear_column_color(self, col_key):
        self._column_styles.pop(col_key, None)
        self._refresh_bound_cells()

    def clear_all_colors(self):
        self._cell_styles = {}
        self._row_styles = {}
        self._column_styles = {}
        self._table_style = None
        self._refresh_bound_cells()

    def set_colors(self, spec):
        """Apply many overrides at once (see the pg backend's docs)."""
        if not isinstance(spec, dict):
            return
        if spec.get('clear'):
            self._cell_styles = {}
            self._row_styles = {}
            self._column_styles = {}
            self._table_style = None
        for entry in (spec.get('cells') or []):
            key = (self._style_path(entry.get('path')), entry.get('col_key'))
            style = self._style_or_none(entry.get('fg'), entry.get('bg'),
                                        entry.get('bold'))
            if style is None:
                self._cell_styles.pop(key, None)
            else:
                self._cell_styles[key] = style
        for entry in (spec.get('rows') or []):
            key = self._style_path(entry.get('path'))
            style = self._style_or_none(entry.get('fg'), entry.get('bg'),
                                        entry.get('bold'))
            if style is None:
                self._row_styles.pop(key, None)
            else:
                self._row_styles[key] = style
        for entry in (spec.get('columns') or []):
            style = self._style_or_none(entry.get('fg'), entry.get('bg'),
                                        entry.get('bold'))
            if style is None:
                self._column_styles.pop(entry.get('col_key'), None)
            else:
                self._column_styles[entry.get('col_key')] = style
        if 'table' in spec:
            table = spec.get('table') or {}
            self._table_style = self._style_or_none(
                table.get('fg'), table.get('bg'), table.get('bold'))
        self._refresh_bound_cells()

    def set_path_background(self, path, bgcolor, alpha=1.0):
        """Kept for the older API; a row-level background."""
        self.set_row_color(path, bg=bgcolor)

    def highlight_path(self, path, onoff, font_color='green'):
        """Kept for the older API; bold + colour on a whole row."""
        if onoff:
            self.set_row_color(path, fg=font_color, bold=True)
        else:
            self.clear_row_color(path)

    # -- binding values into the cell widgets --------------------------

    def _apply_cell(self, row, col_idx, widget):
        """Show this row's value for the column, and gate the control.

        Programmatic updates are marked so the signal handlers can tell
        a refresh from something the user did -- otherwise a periodic
        refresh would look like a stream of edits.
        """
        col_key = self.datakeys[col_idx]
        spec = self.col_specs[col_idx]
        value = row.get(col_key, '')
        supplied = col_key in row.supplied

        # a column the row never supplied is filler, not content
        visible = supplied
        vis_key = spec.get('visible_key')
        if visible and vis_key is not None:
            visible = bool(row.values.get(vis_key))

        widget._ginga_updating = True
        try:
            if isinstance(widget, Gtk.CheckButton):
                widget.set_active(bool(value))
                widget.set_visible(visible)
                widget.set_sensitive(self._cell_enabled(row, spec))
            elif isinstance(widget, Gtk.DropDown):
                choices = [str(c) for c in (spec.get('choices') or [])]
                text = '' if value is None else str(value)
                if text in choices:
                    widget.set_selected(choices.index(text))
                widget.set_visible(visible)
                widget.set_sensitive(self._cell_enabled(row, spec))
            elif isinstance(widget, Gtk.ProgressBar):
                widget.set_fraction(self._fraction(value, spec))
                widget.set_visible(visible)
            elif isinstance(widget, Gtk.Button):
                label = spec.get('text') or ''
                if value not in (None, ''):
                    label = str(value)
                widget.set_label(label)
                widget.set_visible(visible)
                widget.set_sensitive(self._cell_enabled(row, spec))
            elif isinstance(widget, Gtk.Image):
                # the caller hands us a GdkPixbuf, as the cell renderer
                # took; Gtk.Image.set_from_pixbuf is deprecated in GTK4,
                # so go through a texture (built without the equally
                # deprecated Gdk.Texture.new_for_pixbuf)
                if value in (None, ''):
                    widget.set_from_paintable(None)
                else:
                    try:
                        widget.set_from_paintable(
                            GtkHelp.texture_from_pixbuf(value))
                    except (TypeError, AttributeError):
                        # not a pixbuf -- an icon name, perhaps
                        widget.set_from_icon_name(str(value))
                widget.set_visible(visible or not supplied)
            elif isinstance(widget, Gtk.EditableLabel):
                widget.set_text(str(value))
                # supplied-but-empty stays editable: a row with no note
                # yet must still be able to get one
                widget.set_editable(supplied)
            else:
                self._set_cell_text(row, col_idx, widget)
            self._apply_cell_color(row, col_idx, widget)
            if self._cell_mode():
                self._mark_cell_selection(row, col_idx, widget)
        finally:
            widget._ginga_updating = False

    @staticmethod
    def _cell_enabled(row, spec):
        enabled_key = spec.get('enabled_key')
        if enabled_key is None:
            return True
        return bool(row.values.get(enabled_key, True))

    @staticmethod
    def _fraction(value, spec):
        lo = spec.get('min', 0) or 0
        hi = spec.get('max', 100)
        hi = 100 if hi is None else hi
        try:
            frac = (float(value) - float(lo)) / (float(hi) - float(lo))
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0
        return max(0.0, min(1.0, frac))

    # -- edits ---------------------------------------------------------

    def _cell_row_for(self, widget):
        return getattr(widget, '_ginga_row', None)

    def _report_edit(self, widget, col_idx, new_value):
        row = self._cell_row_for(widget)
        if row is None:
            return
        col_key = self.datakeys[col_idx]
        old_value = row.get(col_key, '')
        if new_value == old_value:
            return
        row.values[col_key] = new_value
        row.supplied.add(col_key)
        self.make_callback('cell_edited', self._path_for_row(row),
                           col_key, old_value, new_value)

    def _cv_cell_changed_cb(self, widget, *args):
        """A check button or drop-down was altered by the user."""
        if getattr(widget, '_ginga_updating', False):
            return
        col_idx = args[-1]
        if isinstance(widget, Gtk.CheckButton):
            self._report_edit(widget, col_idx, bool(widget.get_active()))
        else:
            spec = self.col_specs[col_idx]
            choices = [str(c) for c in (spec.get('choices') or [])]
            idx = widget.get_selected()
            if 0 <= idx < len(choices):
                self._report_edit(widget, col_idx, choices[idx])

    def _cv_editing_done_cb(self, widget, _pspec, col_idx):
        if getattr(widget, '_ginga_updating', False):
            return
        if widget.get_property('editing'):
            return          # editing has just started
        self._report_edit(widget, col_idx, widget.get_text())

    def _cv_cell_clicked_cb(self, widget, col_idx):
        row = self._cell_row_for(widget)
        if row is None:
            return
        self.make_callback('cell_action', self._path_for_row(row),
                           self.datakeys[col_idx])

    def set_column_editable(self, col, tf):
        idx = col if isinstance(col, int) else self.datakeys.index(col)
        if tf:
            self._col_editable.add(idx)
        else:
            self._col_editable.discard(idx)

    def set_editable(self, tf):
        if tf:
            self._col_editable = set(
                i for i, spec in enumerate(self.col_specs)
                if spec.get('widget') not in _CELL_WIDGETS and
                spec['type'] not in ('icon', 'check'))
        else:
            self._col_editable = set()

    # -- cell-level selection ------------------------------------------
    #
    # ColumnView selects rows, not cells, so this is built on clicks
    # landing in a cell's widget.  Selected cells are marked with a CSS
    # class rather than by any model state.

    def _cell_mode(self):
        return self.selection in ('single-cell', 'multiple-cell')

    def _attach_cell_click(self, widget, col_idx):
        gesture = Gtk.GestureClick.new()
        gesture.set_button(1)
        # CAPTURE, because an editable cell is a GtkEditableLabel and
        # its own click handling would otherwise take the press and
        # drop straight into the editor -- leaving no way to just put
        # the cursor on a cell, as the qt and pg tables do
        gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        gesture.connect('pressed', self._cv_cell_pressed_cb, widget,
                        col_idx)
        widget.add_controller(gesture)

    def _cv_cell_pressed_cb(self, gesture, n_press, x, y, widget, col_idx):
        self._in_cell_click = True
        try:
            self._cell_pressed(gesture, n_press, x, y, widget, col_idx)
        finally:
            self._in_cell_click = False

    def _cell_pressed(self, gesture, n_press, x, y, widget, col_idx):
        row = self._cell_row_for(widget)
        editing = (isinstance(widget, Gtk.EditableLabel) and
                   widget.get_property('editing'))
        if row is not None and not editing:
            # clicking a cell moves the keyboard cursor there, so
            # arrows and Tab carry on from where the user pointed
            position = self._position_of_row(row)
            if position is not None:
                self._cursor = (position, col_idx)
                if (not self._cell_mode() and
                        isinstance(widget, Gtk.EditableLabel)):
                    # we claim the press on editable cells, so GTK never
                    # makes the row selection a click would -- stand in
                    # for it here.  Elsewhere GTK still handles it (and
                    # the double click that goes with it).
                    self.select_row_at(position)

        if not editing and isinstance(widget, Gtk.EditableLabel):
            # An editable cell is a GtkEditableLabel, which would drop
            # straight into its editor on a click; claim the press so a
            # single click just places the cursor and a double click
            # opens the editor.  Only for editable cells: claiming it
            # everywhere stops ColumnView emitting 'activate', which is
            # how a double click opens a file in FBrowser.
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            widget.grab_focus()
            if n_press >= 2:
                widget.start_editing()

        if not self._cell_mode():
            return
        if row is None:
            return
        # picking a cell replaces what was selected, including rows --
        # the mirror of a header click clearing the cell selection
        if not self.selection_model.get_selection().is_empty():
            self.clear_selection()
        col_key = self.datakeys[col_idx]
        key = (tuple(self._path_for_row(row)), col_key)
        event = gesture.get_current_event()
        extend = False
        if event is not None:
            state = event.get_modifier_state()
            extend = bool(state & Gdk.ModifierType.CONTROL_MASK)
        if self.selection == 'single-cell' or not extend:
            self._cell_selection = {key}
        elif key in self._cell_selection:
            self._cell_selection.discard(key)
        else:
            self._cell_selection.add(key)
        self._refresh_bound_cells()
        self.make_callback('cell_selected', self.get_selected_cells())

    def get_selected_cells(self):
        """``[{path, col_key, value}, ...]`` for the selected cells."""
        out = []
        for path_key, col_key in sorted(self._cell_selection,
                                        key=lambda k: (k[0], k[1])):
            row = self._row_at(list(path_key))
            if row is None:
                continue
            out.append(dict(path=self._path_for_row(row), col_key=col_key,
                            value=row.get(col_key, '')))
        return out

    def select_cell(self, path, col_key, state=True):
        row = self._row_at(path)
        if row is None:
            return
        key = (tuple(self._path_for_row(row)), col_key)
        if state:
            if self.selection == 'single-cell':
                self._cell_selection = set()
            self._cell_selection.add(key)
        else:
            self._cell_selection.discard(key)
        self._refresh_bound_cells()

    def select_cells(self, cells, state=True):
        for cell in (cells or []):
            self.select_cell(cell.get('path'), cell.get('col_key'),
                             state=state)

    def clear_cell_selection(self):
        if self._cell_selection:
            self._cell_selection = set()
            self._refresh_bound_cells()

    def _apply_cell_color(self, row, col_idx, widget):
        """Colour a cell by style class.

        Markup would only tint the text run; a class puts the colour on
        the widget, so a background fills the cell as it does on the qt
        and gtk3 backends.

        The class goes on the ColumnView's own cell widget as well as on
        the control inside it.  A label fills its cell, but a button does
        not -- it is sized to its text, draws its own background over
        ours, and is missing altogether on a row that ``visible_key``
        gates off -- so colouring only the control would leave a
        row-coloured row with unpainted gaps.
        """
        fg, bg, bold = self._resolve_style(row, self.datakeys[col_idx])
        cls = (None if (fg is None and bg is None and bold is None)
               else self._color_class(fg, bg, bold))
        for w in (widget, self._cell_container(widget)):
            if w is None:
                continue
            previous = getattr(w, '_ginga_color_class', None)
            if previous is not None:
                w.remove_css_class(previous)
                w._ginga_color_class = None
            if cls is not None:
                w.add_css_class(cls)
                w._ginga_color_class = cls

    @staticmethod
    def _cell_container(widget):
        """The ColumnView cell widget holding ``widget``, if we can see
        it -- the control is a direct child of the cell, except in the
        tree column where a TreeExpander sits between the two."""
        w = widget
        for i in range(3):
            w = w.get_parent()
            if w is None:
                return None
            # GtkColumnViewCell is internal to gtk, so go by name
            if type(w).__name__.startswith('GtkColumnViewCell'):
                return w
        return None

    def _color_class(self, fg, bg, bold):
        """A CSS class for one colour combination, made on demand."""
        key = (fg, bg, bold)
        cls = self._color_classes.get(key)
        if cls is not None:
            return cls
        cls = 'ginga-color-%d' % (len(self._color_classes),)
        decls = []
        if fg is not None:
            decls.append('color: %s;' % (self._css_color(fg),))
        if bg is not None:
            decls.append('background-color: %s;' % (self._css_color(bg),))
        if bold is not None:
            decls.append('font-weight: %s;'
                         % ('bold' if bold else 'normal'))
        self._color_classes[key] = cls
        self._color_rules[cls] = ' '.join(decls)
        self._restyle()
        return cls

    def _restyle(self):
        """Rebuild the stylesheet; the wrapper owns it."""
        apply_css = getattr(self, '_apply_css', None)
        if apply_css is not None:
            apply_css()

    def _mark_cell_selection(self, row, col_idx, widget):
        """Show (or unshow) the selection on a cell's widget."""
        key = (tuple(self._path_for_row(row)), self.datakeys[col_idx])
        if key in self._cell_selection:
            widget.add_css_class('ginga-cell-selected')
        else:
            widget.remove_css_class('ginga-cell-selected')

    # -- clipboard -----------------------------------------------------

    def _selection_as_tsv(self):
        """The selection as tab-separated text, laid out as a grid."""
        if self._cell_selection:
            cells = self.get_selected_cells()
            rows = {}
            for cell in cells:
                rows.setdefault(tuple(cell['path']), {})[
                    cell['col_key']] = cell['value']
            col_order = [k for k in self.datakeys
                         if any(k in r for r in rows.values())]
            lines = []
            for path in sorted(rows):
                lines.append('\t'.join(str(rows[path].get(k, ''))
                                       for k in col_order))
            return '\n'.join(lines)

        lines = []
        for row in self._selected_rows():
            lines.append('\t'.join(str(row.get(k, ''))
                                   for k in self.datakeys))
        return '\n'.join(lines)

    def copy_selection(self):
        text = self._selection_as_tsv()
        display = Gdk.Display.get_default()
        if display is not None:
            display.get_clipboard().set(text)
        self.make_callback('copy', text)
        return text

    def cut_selection(self):
        """Copy, then blank the editable cells in the selection."""
        text = self.copy_selection()
        for cell in self.get_selected_cells():
            col_key = cell['col_key']
            idx = self.datakeys.index(col_key)
            if idx not in self._col_editable:
                continue
            row = self._row_at(cell['path'])
            if row is None:
                continue
            old = row.get(col_key, '')
            if old == '':
                continue
            row.values[col_key] = ''
            self.make_callback('cell_edited', self._path_for_row(row),
                               col_key, old, '')
        self._refresh_bound_cells()
        self.make_callback('cut', text)
        return text

    def paste_selection(self, text=None):
        """Paste tab-separated text over the selection.

        With no text, the system clipboard is read -- which GTK4 only
        offers asynchronously, so the paste lands once it arrives.
        """
        if text is None:
            display = Gdk.Display.get_default()
            if display is None:
                return
            display.get_clipboard().read_text_async(
                None, self._cv_paste_ready_cb)
            return
        self._apply_paste(text)

    def _cv_paste_ready_cb(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
        except GLib.Error:
            return
        if text is not None:
            self._apply_paste(text)

    def _apply_paste(self, text):
        anchors = self.get_selected_cells()
        if not anchors:
            return
        anchor = anchors[0]
        start_row = self._row_at(anchor['path'])
        start_col = self.datakeys.index(anchor['col_key'])
        rows = [row for row in walk_rows(self.store)]
        try:
            r0 = rows.index(start_row)
        except ValueError:
            return

        for dr, line in enumerate(text.split('\n')):
            if r0 + dr >= len(rows):
                break
            row = rows[r0 + dr]
            for dc, value in enumerate(line.split('\t')):
                col = start_col + dc
                if col >= len(self.datakeys):
                    break
                if col not in self._col_editable:
                    continue
                col_key = self.datakeys[col]
                old = row.get(col_key, '')
                if old == value:
                    continue
                row.values[col_key] = value
                row.supplied.add(col_key)
                self.make_callback('cell_edited', self._path_for_row(row),
                                   col_key, old, value)
        self._refresh_bound_cells()
        self.make_callback('paste', text)
