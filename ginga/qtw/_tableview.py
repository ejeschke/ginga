#
# _tableview.py -- QTableWidget-based TableView for the qt backend.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""QTableWidget-backed TableView.

Split out of ``ginga.qtw.Widgets`` (which still holds the QTreeWidget-based
``TreeView`` and everything else).  ``Widgets`` imports ``TableView`` from
here at the bottom of the module, so this module can import the shared
symbols (``WidgetBase``, ``_CellWrapper``, ``_CELL_WIDGETS``) back from it
without a cycle -- by the time the bottom import runs, those are defined.

Public API and callbacks match the previous QTreeWidget-based TableView and
the pgw TableView, so callers are unaffected.  QTableWidget gives, natively:
a current-cell cursor with arrow/Tab navigation, grid lines, a row-number
vertical header, rectangular / row / column selection, and *per-cell*
editability -- the things the QTreeWidget version had to emulate.
"""
from ginga.qtw.QtHelp import QtGui, QtCore, QFont
from ginga.qtw import QtHelp
from ginga.qtw.Widgets import (WidgetBase, WidgetError, _CellWrapper,
                               _CELL_WIDGETS)

__all__ = ['TableView', 'TableWidgetItem']


class TableWidgetItem(QtGui.QTableWidgetItem):
    """QTableWidgetItem with type-aware sort comparison.  The column's
    declared data type (stored on the owning table) makes integer/float/
    boolean columns sort numerically rather than lexically."""

    def __lt__(self, other):
        tbl = self.tableWidget()
        col = self.column()
        dtype = 'string'
        if tbl is not None and hasattr(tbl, '_ginga_coltypes'):
            dtype = tbl._ginga_coltypes.get(col, 'string')
        a, b = self.text(), other.text()
        try:
            if dtype in ('integer', 'int'):
                return int(a or 0) < int(b or 0)
            if dtype in ('float', 'number'):
                return float(a or 0) < float(b or 0)
            if dtype in ('boolean', 'bool'):
                truthy = ('1', 'true', 'yes', 'y', '✓')
                return (str(a).strip().lower() in truthy) < \
                       (str(b).strip().lower() in truthy)
        except (TypeError, ValueError):
            pass
        return a < b


class _CellEditDelegate(QtGui.QStyledItemDelegate):
    """Item delegate that lets the owning TableView implement the
    spreadsheet "enter mode": when an edit was begun by typing (as opposed
    to F2 / double-click), the arrow keys commit the edit and move the
    cursor instead of moving the caret.  Tab and Enter always commit+move.
    """

    def __init__(self, table):
        super().__init__(table.widget)
        self._table = table

    def eventFilter(self, editor, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if self._table._editor_key(editor, event):
                return True
        return super().eventFilter(editor, event)


class TableView(WidgetBase):
    """Flat, editable tabular view backed by ``QTableWidget``.

    See the module docstring.  Constructor options, methods and callbacks
    mirror ``ginga.web.pgw.Widgets.TableView``:

    * ``activated(table, row_dict, [row_index], col_key)`` -- double-click
    * ``selected(table, list_of_row_dicts)`` -- row-mode selection changed
    * ``cell_selected(table, [{path, col_key, value}, ...])`` -- the current
      cell moved (cursor) or the cell-mode selection changed
    * ``sorted(table, col_key, ascending)`` -- header sort
    * ``cell_edited(table, [row_index], col_key, old_value, new_value)``
    * ``cell_action(table, row_dict, col_key)`` -- a button cell was clicked
    * ``scrolled(table, h_pct, v_pct)``
    * ``copy/cut/paste(table, text)`` -- Ctrl+C / X / V
    """

    def __init__(self, columns=None, show_header=True,
                 selection_mode='single', alternate_row_colors=False,
                 show_grid=False, show_row_numbers=False,
                 sortable=False, allow_text_selection=False,
                 dragable=False):
        super().__init__()

        self._selection_mode_arg = selection_mode
        self.sortable = sortable
        self.dragable = dragable
        self.leaf_key = None
        self._show_row_numbers = bool(show_row_numbers)
        self._show_grid = bool(show_grid)
        self._allow_text_selection = bool(allow_text_selection)  # noqa
        # table-wide editable flag (set_editable); ORs with per-column
        self._editable_all = False

        self.font = self.get_font('sans', 10)
        self.fontsize = 10.0
        self.row_pad_px = 0
        self.col_pad_px = 0

        # normalised user column descriptors (col index == QTableWidget col)
        self._user_columns = []
        # col index -> {'editable'} membership, plus a col-index -> type map
        self._editable_cols = set()
        self._coltypes = {}

        # colour overrides.  Per-item entries survive sort (keyed by the
        # cell item's id, which QTableWidget preserves as it moves items);
        # column / table layers are resolved on top at apply time.
        #   self._overrides[id(item)] = {'cell': {...}|None, 'row': {...}|None}
        self._overrides = {}
        self._col_color_map = {}      # col_key -> {fg,bg,bold}
        self._table_color = None      # {fg,bg,bold} | None

        # embedded widget cells: (row_token, col_key) -> inner widget.  We
        # tag each row with a monotonic token (stored in UserRole+1 on its
        # items) so widget refs survive sort/insert/delete.
        self._cell_widgets = {}
        self._row_token_seq = 0

        tw = QtGui.QTableWidget()
        tw._ginga_coltypes = self._coltypes
        self.widget = tw
        tw.setFont(self.font)

        tw.setShowGrid(self._show_grid)
        tw.setAlternatingRowColors(alternate_row_colors)
        tw.setWordWrap(False)
        tw.horizontalHeader().setVisible(show_header)
        tw.verticalHeader().setVisible(self._show_row_numbers)

        # selection behaviour / mode
        is_cell_mode = self._is_cell_mode()
        if is_cell_mode:
            tw.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
            mode = (QtGui.QAbstractItemView.ExtendedSelection
                    if selection_mode == 'multiple-cell'
                    else QtGui.QAbstractItemView.SingleSelection)
        else:
            tw.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
            mode = {
                'single': QtGui.QAbstractItemView.SingleSelection,
                'multiple': QtGui.QAbstractItemView.ExtendedSelection,
                'none': QtGui.QAbstractItemView.NoSelection,
            }.get(selection_mode, QtGui.QAbstractItemView.SingleSelection)
        tw.setSelectionMode(mode)

        # spreadsheet editing: type-to-edit + F2 + double-click; Tab walks
        # cells.  The delegate + our own key handling add Delete-clear and
        # the "enter mode" arrow/Tab/Enter commit-and-move.
        tw.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked |
                           QtGui.QAbstractItemView.EditKeyPressed |
                           QtGui.QAbstractItemView.AnyKeyPressed)
        tw.setTabKeyNavigation(True)
        self._delegate = _CellEditDelegate(self)
        tw.setItemDelegate(self._delegate)
        # True while an edit that began by typing is open (enter mode).
        self._enter_mode = False
        # guards cell_edited during programmatic writes (we also blockSignals)
        self._populating = False

        tw.itemDoubleClicked.connect(self._activated_cb)
        tw.itemSelectionChanged.connect(self._selection_cb)
        tw.currentCellChanged.connect(self._current_cell_cb)
        tw.cellChanged.connect(self._cell_changed_cb)
        tw.horizontalHeader().sortIndicatorChanged.connect(
            self._sort_indicator_cb)
        tw.verticalScrollBar().valueChanged.connect(self._scroll_cb)
        tw.horizontalScrollBar().valueChanged.connect(self._scroll_cb)

        if self.dragable:
            tw.setDragEnabled(True)

        # our own key handling (Delete-clear, Ctrl+C/X/V, type-to-edit
        # bookkeeping): monkeypatch keyPressEvent (the ginga wrapper isn't a
        # QObject, so it can't be an event filter -- this mirrors how
        # TextArea in Widgets.py hooks keyPressEvent).
        tw.keyPressEvent = self._table_key_press
        self._apply_selection_palette()

        for cbname in ('selected', 'activated', 'cell_selected', 'cell_edited',
                       'cell_action', 'sorted', 'scrolled', 'changed',
                       'copy', 'cut', 'paste'):
            self.enable_callback(cbname)

        if columns is not None:
            self.set_columns(columns)

    def _is_cell_mode(self):
        return self._selection_mode_arg in ('single-cell', 'multiple-cell')

    # ------------------------------------------------------------------
    # column descriptor normalisation (kept identical to the pgw/old-qt side)
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_columns(columns):
        out = []
        for i, col in enumerate(columns):
            if isinstance(col, dict):
                key = col.get('key') or col.get('label') or f'col{i}'
                widget = col.get('widget')
                if widget is not None and widget not in _CELL_WIDGETS:
                    raise WidgetError(
                        f"unknown column widget {widget!r} "
                        f"(expected one of {_CELL_WIDGETS})")
                d = {
                    'label': col.get('label', key),
                    'key': key,
                    'type': col.get('type', 'string'),
                    'halign': col.get('halign'),
                    'editable': bool(col.get('editable', False)),
                    'widget': widget,
                    'choices': (list(col['choices'])
                                if 'choices' in col else None),
                    'min': col.get('min'),
                    'max': col.get('max'),
                    'text': col.get('text'),
                    'enabled_key': col.get('enabled_key'),
                    'visible_key': col.get('visible_key'),
                    'colwidth': col.get('colwidth'),
                }
            elif isinstance(col, (tuple, list)):
                label = col[0]
                key = col[1] if len(col) > 1 else label
                dtype = col[2] if len(col) > 2 else 'string'
                d = {'label': label, 'key': key, 'type': dtype,
                     'halign': None, 'editable': False, 'widget': None,
                     'choices': None, 'min': None, 'max': None, 'text': None,
                     'enabled_key': None, 'visible_key': None,
                     'colwidth': None}
            elif isinstance(col, str):
                d = {'label': col, 'key': col, 'type': 'string',
                     'halign': None, 'editable': False, 'widget': None,
                     'choices': None, 'min': None, 'max': None, 'text': None,
                     'enabled_key': None, 'visible_key': None,
                     'colwidth': None}
            else:
                raise WidgetError(f"unrecognised column descriptor: {col!r}")
            out.append(d)
        return out

    def _user_col_keys(self):
        return [c['key'] for c in self._user_columns]

    def _col_index(self, col_key):
        try:
            return self._user_col_keys().index(col_key)
        except ValueError:
            return None

    def _col_editable(self, c):
        col = self._user_columns[c]
        if col.get('widget') or col['type'] == 'icon':
            return False
        return self._editable_all or (c in self._editable_cols)

    def _format_value(self, col, value):
        if col['type'] in ('boolean', 'bool'):
            return '✓' if value else ''
        return '' if value is None else str(value)

    # ------------------------------------------------------------------
    # columns
    # ------------------------------------------------------------------
    def set_columns(self, columns):
        self._user_columns = self._normalise_columns(columns)
        self._editable_cols = {i for i, c in enumerate(self._user_columns)
                               if c.get('editable')}
        tw = self.widget
        self._populating = True
        blk = tw.blockSignals(True)
        try:
            tw.clear()
            tw.setRowCount(0)
            tw.setColumnCount(len(self._user_columns))
            tw.setHorizontalHeaderLabels(
                [c['label'] for c in self._user_columns])
            self._coltypes.clear()
            for i, c in enumerate(self._user_columns):
                self._coltypes[i] = c['type']
                if c.get('colwidth'):
                    try:
                        tw.setColumnWidth(i, int(c['colwidth']))
                    except (TypeError, ValueError):
                        pass
            tw.setSortingEnabled(self.sortable)
        finally:
            tw.blockSignals(blk)
            self._populating = False

    def setup_table(self, columns, levels, leaf_key):
        # compat shim; TableView is always flat (levels ignored)
        self.leaf_key = leaf_key
        self.set_columns(columns)

    def insert_column(self, idx, column):
        col, = self._normalise_columns([column])
        rows = self.get_rows()
        self._user_columns.insert(idx, col)
        for r in rows:
            r.setdefault(col['key'], '')
        self.set_columns(self._user_columns)
        self.set_rows(rows)

    def append_column(self, column):
        self.insert_column(len(self._user_columns), column)

    def delete_column(self, idx):
        if not (0 <= idx < len(self._user_columns)):
            raise WidgetError(f"column index {idx} out of range")
        removed = self._user_columns.pop(idx)
        rows = self.get_rows()
        for r in rows:
            r.pop(removed['key'], None)
        self.set_columns(self._user_columns)
        self.set_rows(rows)

    def set_column_editable(self, col_idx, tf):
        if tf:
            self._editable_cols.add(col_idx)
        else:
            self._editable_cols.discard(col_idx)
        self._apply_editable_flags_all()

    def set_editable(self, tf):
        """Make every text column editable (or revert to per-column)."""
        self._editable_all = bool(tf)
        self._apply_editable_flags_all()

    def get_column_count(self):
        return len(self._user_columns)

    def set_column_width(self, idx, width):
        self.widget.setColumnWidth(idx, width)

    def set_optimal_column_widths(self):
        self.widget.resizeColumnsToContents()

    def _apply_editable_flags_all(self):
        tw = self.widget
        for r in range(tw.rowCount()):
            for c in range(tw.columnCount()):
                item = tw.item(r, c)
                if item is None:
                    continue
                flags = item.flags() & ~QtCore.Qt.ItemIsEditable
                if self._col_editable(c):
                    flags |= QtCore.Qt.ItemIsEditable
                item.setFlags(flags)

    # ------------------------------------------------------------------
    # rows
    # ------------------------------------------------------------------
    def _row_to_dict(self, values):
        if isinstance(values, dict):
            return dict(values)
        if isinstance(values, (list, tuple)):
            return dict(zip(self._user_col_keys(), values))
        raise WidgetError(
            f"row must be a dict or sequence, got {type(values).__name__}")

    def set_rows(self, rows):
        tw = self.widget
        rows = list(rows)
        self._populating = True
        blk = tw.blockSignals(True)
        was_sorting = tw.isSortingEnabled()
        tw.setSortingEnabled(False)
        try:
            self._overrides.clear()
            self._cell_widgets.clear()
            tw.setRowCount(0)
            tw.setRowCount(len(rows))
            for r, row in enumerate(rows):
                self._populate_row(r, self._row_to_dict(row))
        finally:
            tw.setSortingEnabled(was_sorting)
            tw.blockSignals(blk)
            self._populating = False
        self._apply_all_colors()

    def set_data(self, data):
        from ginga.util import tablehelper
        if tablehelper.is_ndarray(data):
            data = tablehelper.rows_from_ndarray(data)
        self.set_rows(data)

    def set_table(self, table):
        from ginga.util import tablehelper
        self.set_columns(tablehelper.columns_from_table(table))
        self.set_rows(tablehelper.rows_from_table(table))

    def _new_row_token(self):
        self._row_token_seq += 1
        return self._row_token_seq

    def _populate_row(self, r, row_dict):
        """Create the cell items (and any widget cells) for visible row r."""
        tw = self.widget
        token = self._new_row_token()
        for c, col in enumerate(self._user_columns):
            val = row_dict.get(col['key'], '')
            item = TableWidgetItem()
            item.setData(QtCore.Qt.UserRole + 1, token)   # stable row token
            flags = item.flags() & ~QtCore.Qt.ItemIsEditable
            if self._col_editable(c):
                flags |= QtCore.Qt.ItemIsEditable
            if col.get('halign'):
                item.setTextAlignment(self._qt_align(col['halign']))
            if col.get('widget'):
                # widget cells host a real Qt widget; the item is just a
                # placeholder carrying the value in UserRole.
                item.setFlags(flags & ~QtCore.Qt.ItemIsEditable)
                item.setData(QtCore.Qt.UserRole, val)
                tw.setItem(r, c, item)
                self._install_widget_cell(r, c, col, val, row_dict, token)
            else:
                item.setFlags(flags)
                item.setText(self._format_value(col, val))
                item.setData(QtCore.Qt.UserRole, item.text())
                tw.setItem(r, c, item)
        if self._show_row_numbers:
            tw.setVerticalHeaderItem(r, QtGui.QTableWidgetItem(str(r + 1)))

    @staticmethod
    def _qt_align(halign):
        m = {'left': QtCore.Qt.AlignLeft, 'center': QtCore.Qt.AlignHCenter,
             'right': QtCore.Qt.AlignRight}
        return m.get(halign, QtCore.Qt.AlignLeft) | QtCore.Qt.AlignVCenter

    def append_row(self, values):
        self.insert_row(self.widget.rowCount(), values)

    def insert_row(self, idx, values):
        tw = self.widget
        was_sorting = tw.isSortingEnabled()
        blk = tw.blockSignals(True)
        self._populating = True
        tw.setSortingEnabled(False)
        try:
            tw.insertRow(idx)
            self._populate_row(idx, self._row_to_dict(values))
            if self._show_row_numbers:
                self._renumber_rows()
        finally:
            tw.setSortingEnabled(was_sorting)
            tw.blockSignals(blk)
            self._populating = False
        self._apply_all_colors()

    def delete_row(self, idx):
        tw = self.widget
        if not (0 <= idx < tw.rowCount()):
            raise WidgetError(f"row index {idx} out of range")
        # drop widget + override refs for this row's items
        for c in range(tw.columnCount()):
            item = tw.item(idx, c)
            if item is not None:
                self._overrides.pop(id(item), None)
        token = self._row_token(idx)
        for key in [k for k in self._cell_widgets if k[0] == token]:
            del self._cell_widgets[key]
        tw.removeRow(idx)
        if self._show_row_numbers:
            self._renumber_rows()

    def _renumber_rows(self):
        tw = self.widget
        for r in range(tw.rowCount()):
            tw.setVerticalHeaderItem(r, QtGui.QTableWidgetItem(str(r + 1)))

    def get_row_count(self):
        return self.widget.rowCount()

    def get_row(self, idx):
        if not (0 <= idx < self.widget.rowCount()):
            raise WidgetError(f"row index {idx} out of range")
        return self._row_at(idx)

    def get_rows(self):
        return [self._row_at(r) for r in range(self.widget.rowCount())]

    def _row_at(self, r):
        tw = self.widget
        d = {}
        token = self._row_token(r)
        for c, col in enumerate(self._user_columns):
            w = self._cell_widgets.get((token, col['key']))
            if w is not None:
                d[col['key']] = self._read_widget_value(col, w)
            else:
                item = tw.item(r, c)
                d[col['key']] = item.text() if item is not None else ''
        return d

    def _row_token(self, r):
        item = self.widget.item(r, 0)
        if item is not None:
            tok = item.data(QtCore.Qt.UserRole + 1)
            if tok is not None:
                return tok
        return ('_row', r)

    def set_cell(self, row, col, value):
        tw = self.widget
        if not (0 <= row < tw.rowCount()):
            raise WidgetError(f"row index {row} out of range")
        if not (0 <= col < len(self._user_columns)):
            raise WidgetError(f"column index {col} out of range")
        col_spec = self._user_columns[col]
        token = self._row_token(row)
        w = self._cell_widgets.get((token, col_spec['key']))
        blk = tw.blockSignals(True)
        try:
            if w is not None:
                w.blockSignals(True)
                try:
                    self._write_widget_value(col_spec, w, value)
                finally:
                    w.blockSignals(False)
                item = tw.item(row, col)
                if item is not None:
                    item.setData(QtCore.Qt.UserRole, value)
                return
            item = tw.item(row, col)
            text = self._format_value(col_spec, value)
            if item is None:
                item = TableWidgetItem()
                tw.setItem(row, col, item)
            item.setText(text)
            item.setData(QtCore.Qt.UserRole, text)
        finally:
            tw.blockSignals(blk)

    def clear(self):
        self._cell_widgets.clear()
        self._overrides.clear()
        self.widget.setRowCount(0)

    # ------------------------------------------------------------------
    # embedded widget cells
    # ------------------------------------------------------------------
    def _install_widget_cell(self, r, c, col, value, row_dict, token):
        visible_key = col.get('visible_key')
        if visible_key is not None and not row_dict.get(visible_key, True):
            return
        col_key = col['key']
        inner = self._make_cell_widget(col, value, r, col_key, token)
        enabled_key = col.get('enabled_key')
        if enabled_key is not None:
            inner.setEnabled(bool(row_dict.get(enabled_key, True)))
        container = self._wrap_cell_widget(inner, col)
        self._cell_widgets[(token, col_key)] = inner
        fg0, bg0, _b = self._resolve(self.widget.item(r, c), c)
        container.set_cell_color(fg0, bg0)
        self.widget.setCellWidget(r, c, container)

    @staticmethod
    def _wrap_cell_widget(inner, col):
        container = _CellWrapper()
        layout = QtGui.QHBoxLayout(container)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(0)
        if col.get('widget') == 'checkbox':
            layout.addStretch()
            layout.addWidget(inner)
            layout.addStretch()
        else:
            layout.addWidget(inner)
        return container

    def _make_cell_widget(self, col, value, r, col_key, token):
        wtype = col['widget']
        if wtype == 'checkbox':
            w = QtGui.QCheckBox()
            w.setChecked(bool(value))
            w.setStyleSheet('background: transparent;')
            w.stateChanged.connect(
                lambda _s, tk=token, ck=col_key:
                    self._on_cell_widget_changed(tk, ck))
            return w
        if wtype == 'combobox':
            w = QtGui.QComboBox()
            choices = col.get('choices') or []
            for ch in choices:
                w.addItem(str(ch))
            if value is not None and str(value) in [str(c) for c in choices]:
                w.setCurrentText(str(value))
            w.currentIndexChanged.connect(
                lambda _i, tk=token, ck=col_key:
                    self._on_cell_widget_changed(tk, ck))
            return w
        if wtype == 'progress':
            w = QtGui.QProgressBar()
            lo = col.get('min', 0) or 0
            hi = col.get('max', 100) if col.get('max') is not None else 100
            w.setRange(int(lo), int(hi))
            try:
                w.setValue(int(value) if value is not None else int(lo))
            except (TypeError, ValueError):
                w.setValue(int(lo))
            return w
        if wtype == 'button':
            label = str(value) if value is not None else (col.get('text') or '')
            w = QtGui.QPushButton(label)
            w.clicked.connect(
                lambda _c=False, tk=token, ck=col_key:
                    self._on_cell_widget_clicked(tk, ck))
            return w
        raise WidgetError(f"unknown cell widget type: {wtype!r}")

    def _read_widget_value(self, col, w):
        wtype = col['widget']
        if wtype == 'checkbox':
            return bool(w.isChecked())
        if wtype == 'combobox':
            return w.currentText()
        if wtype == 'progress':
            return int(w.value())
        if wtype == 'button':
            return w.text()
        return None

    def _write_widget_value(self, col, w, value):
        wtype = col['widget']
        if wtype == 'checkbox':
            w.setChecked(bool(value))
        elif wtype == 'combobox':
            if value is not None:
                w.setCurrentText(str(value))
        elif wtype == 'progress':
            try:
                w.setValue(int(value) if value is not None else w.minimum())
            except (TypeError, ValueError):
                pass
        elif wtype == 'button':
            if value is not None:
                w.setText(str(value))

    def _row_of_token(self, token):
        tw = self.widget
        for r in range(tw.rowCount()):
            if self._row_token(r) == token:
                return r
        return -1

    def _on_cell_widget_changed(self, token, col_key):
        w = self._cell_widgets.get((token, col_key))
        if w is None:
            return
        c = self._col_index(col_key)
        if c is None:
            return
        col = self._user_columns[c]
        r = self._row_of_token(token)
        if r < 0:
            return
        item = self.widget.item(r, c)
        new_value = self._read_widget_value(col, w)
        old_value = item.data(QtCore.Qt.UserRole) if item is not None else None
        if old_value == new_value:
            return
        if item is not None:
            item.setData(QtCore.Qt.UserRole, new_value)
        self.make_callback('cell_edited', [r], col_key, old_value, new_value)

    def _on_cell_widget_clicked(self, token, col_key):
        r = self._row_of_token(token)
        if r < 0:
            return
        self.make_callback('cell_action', self._row_at(r), col_key)

    # ------------------------------------------------------------------
    # selection
    # ------------------------------------------------------------------
    def _selected_rows(self):
        sm = self.widget.selectionModel()
        rows = {ix.row() for ix in sm.selectedRows()}
        if not rows:
            rows = {ix.row() for ix in self.widget.selectedIndexes()}
        return sorted(rows)

    def get_selected(self):
        return [self._row_at(r) for r in self._selected_rows()]

    def get_selected_paths(self):
        return [[r] for r in self._selected_rows()]

    def get_selected_cells(self):
        tw = self.widget
        out = []
        for ix in tw.selectedIndexes():
            c = ix.column()
            if not (0 <= c < len(self._user_columns)):
                continue
            item = tw.item(ix.row(), c)
            out.append({'path': [ix.row()],
                        'col_key': self._user_columns[c]['key'],
                        'value': item.text() if item is not None else ''})
        out.sort(key=lambda d: (d['path'][0],
                                self._user_col_keys().index(d['col_key'])))
        return out

    def select_cell(self, path, col_key, state=True):
        idx = self._resolve_to_row_index(path)
        c = self._col_index(col_key)
        if idx is None or c is None:
            return
        if not (0 <= idx < self.widget.rowCount()):
            return
        sm = self.widget.selectionModel()
        qmi = self.widget.model().index(idx, c)
        flag = (QtCore.QItemSelectionModel.Select if state
                else QtCore.QItemSelectionModel.Deselect)
        sm.select(qmi, flag)

    def select_cells(self, cells, state=True):
        for c in (cells or []):
            self.select_cell(c.get('path'), c.get('col_key'), state)

    def clear_cell_selection(self):
        self.widget.clearSelection()

    def set_selected(self, items):
        tw = self.widget
        tw.clearSelection()
        for it in items:
            idx = self._resolve_to_row_index(it)
            if idx is not None and 0 <= idx < tw.rowCount():
                tw.selectRow(idx)

    def select_path(self, path, state=True):
        idx = self._resolve_to_row_index(path)
        if idx is None or not (0 <= idx < self.widget.rowCount()):
            return
        if state:
            self.widget.selectRow(idx)
        else:
            for c in range(self.widget.columnCount()):
                item = self.widget.item(idx, c)
                if item is not None:
                    item.setSelected(False)

    def select_paths(self, paths, state=True):
        for p in paths:
            self.select_path(p, state)

    def select_all(self, state=True):
        if state:
            self.widget.selectAll()
        else:
            self.widget.clearSelection()

    def _resolve_to_row_index(self, item):
        if isinstance(item, int):
            return item
        if isinstance(item, (list, tuple)) and item:
            head = item[0]
            if isinstance(head, int):
                return head
            try:
                return int(head)
            except (TypeError, ValueError):
                return None
        if isinstance(item, dict) and self.leaf_key is not None:
            want = item.get(self.leaf_key)
            for i in range(self.widget.rowCount()):
                if self._row_at(i).get(self.leaf_key) == want:
                    return i
        return None

    # ------------------------------------------------------------------
    # colours (cell > row > column > table precedence)
    # ------------------------------------------------------------------
    def _resolve(self, item, c):
        fg = bg = bold = None
        col_key = (self._user_columns[c]['key']
                   if 0 <= c < len(self._user_columns) else None)

        def _absorb(d):
            nonlocal fg, bg, bold
            if not d:
                return
            if fg is None:
                fg = d.get('fg')
            if bg is None:
                bg = d.get('bg')
            if bold is None:
                bold = d.get('bold')

        ov = self._overrides.get(id(item)) if item is not None else None
        if ov:
            _absorb(ov.get('cell'))
            _absorb(ov.get('row'))
        _absorb(self._col_color_map.get(col_key))
        _absorb(self._table_color)
        return fg, bg, bold

    def _apply_color_to_cell(self, r, c):
        tw = self.widget
        item = tw.item(r, c)
        if item is None:
            return
        fg, bg, bold = self._resolve(item, c)
        item.setForeground(QtHelp.QBrush(QtHelp.QColor(fg)) if fg
                           else QtHelp.QBrush())
        item.setBackground(QtHelp.QBrush(QtHelp.QColor(bg)) if bg
                           else QtHelp.QBrush())
        font = item.font()
        font.setBold(bool(bold))
        item.setFont(font)
        container = tw.cellWidget(r, c)
        if isinstance(container, _CellWrapper):
            container.set_cell_color(fg, bg)

    def _apply_row_colors(self, r):
        for c in range(len(self._user_columns)):
            self._apply_color_to_cell(r, c)

    def _apply_all_colors(self):
        for r in range(self.widget.rowCount()):
            self._apply_row_colors(r)

    def _set_override(self, item, layer, spec):
        if item is None:
            return
        ov = self._overrides.setdefault(id(item), {'cell': None, 'row': None})
        ov[layer] = spec

    def set_cell_color(self, path, col_key, fg=None, bg=None, bold=None):
        idx = self._resolve_to_row_index(path)
        c = self._col_index(col_key)
        if idx is None or c is None:
            return
        item = self.widget.item(idx, c)
        spec = None if (fg is None and bg is None and bold is None) \
            else {'fg': fg, 'bg': bg, 'bold': bold}
        self._set_override(item, 'cell', spec)
        self._apply_color_to_cell(idx, c)

    def set_row_color(self, path, fg=None, bg=None, bold=None):
        idx = self._resolve_to_row_index(path)
        if idx is None:
            return
        spec = None if (fg is None and bg is None and bold is None) \
            else {'fg': fg, 'bg': bg, 'bold': bold}
        for c in range(len(self._user_columns)):
            self._set_override(self.widget.item(idx, c), 'row', spec)
        self._apply_row_colors(idx)

    def set_column_color(self, col_key, fg=None, bg=None, bold=None):
        c = self._col_index(col_key)
        if c is None:
            return
        self._col_color_map[col_key] = None if (
            fg is None and bg is None and bold is None) \
            else {'fg': fg, 'bg': bg, 'bold': bold}
        for r in range(self.widget.rowCount()):
            self._apply_color_to_cell(r, c)

    def set_table_color(self, fg=None, bg=None, bold=None):
        self._table_color = None if (fg is None and bg is None and
                                     bold is None) \
            else {'fg': fg, 'bg': bg, 'bold': bold}
        self._apply_all_colors()

    def clear_cell_color(self, path, col_key):
        self.set_cell_color(path, col_key, fg=None, bg=None)

    def clear_row_color(self, path):
        self.set_row_color(path, fg=None, bg=None)

    def clear_column_color(self, col_key):
        self.set_column_color(col_key, fg=None, bg=None)

    def clear_all_colors(self):
        self._overrides.clear()
        self._col_color_map.clear()
        self._table_color = None
        self._apply_all_colors()

    # ------------------------------------------------------------------
    # sort / scroll / display config
    # ------------------------------------------------------------------
    def set_sortable(self, tf):
        self.sortable = bool(tf)
        self.widget.setSortingEnabled(self.sortable)

    def sort_by_column(self, col, ascending=True):
        order = (QtCore.Qt.AscendingOrder if ascending
                 else QtCore.Qt.DescendingOrder)
        self.widget.sortItems(col, order)

    def scroll_to_path(self, path):
        idx = self._resolve_to_row_index(path)
        if idx is None or not (0 <= idx < self.widget.rowCount()):
            return
        item = self.widget.item(idx, 0)
        if item is not None:
            self.widget.scrollToItem(item)

    def scroll_to_end(self):
        n = self.widget.rowCount()
        if n:
            item = self.widget.item(n - 1, 0)
            if item is not None:
                self.widget.scrollToItem(item)

    def set_scroll_position(self, h_pct, v_pct):
        for bar, pct in ((self.widget.horizontalScrollBar(), h_pct),
                         (self.widget.verticalScrollBar(), v_pct)):
            bar.setValue(int(pct * bar.maximum()))

    def get_scroll_position(self):
        out = []
        for bar in (self.widget.horizontalScrollBar(),
                    self.widget.verticalScrollBar()):
            mx = bar.maximum()
            out.append(bar.value() / mx if mx else 0.0)
        return tuple(out)

    def set_show_grid(self, tf):
        self._show_grid = bool(tf)
        self.widget.setShowGrid(self._show_grid)

    def set_show_row_numbers(self, tf):
        self._show_row_numbers = bool(tf)
        self.widget.verticalHeader().setVisible(self._show_row_numbers)
        if self._show_row_numbers:
            self._renumber_rows()

    def set_header_font(self, font, size=10):
        """Set the column-header font.  Headers use the widget's default
        (non-bold) font unless set here; pass a bold font to embolden."""
        if not isinstance(font, QFont):
            font = self.get_font(font, size)
        self.widget.horizontalHeader().setFont(font)

    def _apply_selection_palette(self):
        palette = self.widget.palette()
        sel_bg = QtHelp.QColor('#2a64c8')
        sel_fg = QtHelp.QColor('white')
        palette.setColor(QtHelp.QPalette.Highlight, sel_bg)
        palette.setColor(QtHelp.QPalette.HighlightedText, sel_fg)
        palette.setColor(QtHelp.QPalette.Inactive,
                         QtHelp.QPalette.Highlight, sel_bg)
        palette.setColor(QtHelp.QPalette.Inactive,
                         QtHelp.QPalette.HighlightedText, sel_fg)
        self.widget.setPalette(palette)

    # ------------------------------------------------------------------
    # callbacks
    # ------------------------------------------------------------------
    def _activated_cb(self, item):
        r, c = item.row(), item.column()
        col_key = (self._user_columns[c]['key']
                   if 0 <= c < len(self._user_columns) else None)
        self.make_callback('activated', self._row_at(r), [r], col_key)

    def _selection_cb(self):
        if self._is_cell_mode():
            self.make_callback('cell_selected', self.get_selected_cells())
        else:
            self.make_callback('selected', self.get_selected())

    def _current_cell_cb(self, r, c, pr, pc):
        # the current cell IS the cursor; surface it as cell_selected
        if r < 0 or c < 0 or c >= len(self._user_columns):
            return
        item = self.widget.item(r, c)
        val = item.text() if item is not None else ''
        self.make_callback('cell_selected',
                           [{'path': [r], 'col_key': self._user_columns[c]['key'],
                             'value': val}])

    def _cell_changed_cb(self, r, c):
        if self._populating or c >= len(self._user_columns):
            return
        if not self._col_editable(c):
            return
        item = self.widget.item(r, c)
        if item is None:
            return
        new_value = item.text()
        old_value = item.data(QtCore.Qt.UserRole)
        item.setData(QtCore.Qt.UserRole, new_value)
        col_key = self._user_columns[c]['key']
        self.make_callback('cell_edited', [r], col_key, old_value, new_value)
        self.make_callback('changed')

    def _sort_indicator_cb(self, logical_index, order):
        if not (0 <= logical_index < len(self._user_columns)):
            return
        col_key = self._user_columns[logical_index]['key']
        asc = (order == QtCore.Qt.AscendingOrder)
        self.make_callback('sorted', col_key, asc)

    def _scroll_cb(self, _value):
        h, v = self.get_scroll_position()
        self.make_callback('scrolled', h, v)

    # ------------------------------------------------------------------
    # key handling: type-to-edit bookkeeping, Delete-clear, clipboard, and
    # the "enter mode" arrow/Tab/Enter commit-and-move (via the delegate)
    # ------------------------------------------------------------------
    def _table_key_press(self, event):
        tw = self.widget
        key = event.key()
        mods = event.modifiers()
        ctrl = bool(mods & (QtCore.Qt.ControlModifier |
                            QtCore.Qt.MetaModifier))
        if ctrl and key == QtCore.Qt.Key_C:
            self.copy_selection()
            return
        if ctrl and key == QtCore.Qt.Key_X:
            self.cut_selection()
            return
        if ctrl and key == QtCore.Qt.Key_V:
            self.paste_selection()
            return
        if key in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            if self._clear_current_cell():
                return
        # type-to-edit: remember we're entering "enter mode" so the delegate
        # turns arrow keys into commit-and-move; Qt's AnyKeyPressed trigger
        # (in the base keyPressEvent below) actually opens the editor.
        text = event.text()
        if (not ctrl and text and text.isprintable() and
                key not in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab)):
            self._enter_mode = True
        elif key == QtCore.Qt.Key_F2:
            self._enter_mode = False
        QtGui.QTableWidget.keyPressEvent(tw, event)

    def _current_editable(self):
        tw = self.widget
        r, c = tw.currentRow(), tw.currentColumn()
        if r < 0 or c < 0 or c >= len(self._user_columns):
            return None
        if not self._col_editable(c):
            return None
        return r, c

    def _clear_current_cell(self):
        rc = self._current_editable()
        if rc is None:
            return False
        r, c = rc
        item = self.widget.item(r, c)
        old = item.data(QtCore.Qt.UserRole) if item is not None else ''
        self.set_cell(r, c, '')
        self.make_callback('cell_edited', [r],
                           self._user_columns[c]['key'], old, '')
        return True

    def _editor_key(self, editor, event):
        """Called from the delegate's editor eventFilter.  Returns True if
        the key was consumed (commit-and-move)."""
        tw = self.widget
        key = event.key()
        r, c = tw.currentRow(), tw.currentColumn()

        def commit_move(dr, dc):
            self._commit_editor(editor)
            nr = min(max(r + dr, 0), tw.rowCount() - 1)
            nc = min(max(c + dc, 0), tw.columnCount() - 1)
            tw.setCurrentCell(nr, nc)
            self._enter_mode = False

        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            commit_move(1, 0)
            return True
        if key == QtCore.Qt.Key_Tab:
            commit_move(0, 1)
            return True
        if key == QtCore.Qt.Key_Backtab:
            commit_move(0, -1)
            return True
        if key == QtCore.Qt.Key_Escape:
            self._enter_mode = False
            return False       # let Qt cancel the edit
        if self._enter_mode and key in (
                QtCore.Qt.Key_Up, QtCore.Qt.Key_Down,
                QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
            d = {QtCore.Qt.Key_Up: (-1, 0), QtCore.Qt.Key_Down: (1, 0),
                 QtCore.Qt.Key_Left: (0, -1), QtCore.Qt.Key_Right: (0, 1)}[key]
            commit_move(*d)
            return True
        return False

    def _commit_editor(self, editor):
        # push the editor's value into the model and close it
        self.widget.commitData(editor)
        self.widget.closeEditor(
            editor, QtGui.QAbstractItemDelegate.NoHint)

    # ------------------------------------------------------------------
    # clipboard
    # ------------------------------------------------------------------
    def _build_selection_tsv(self):
        if self._is_cell_mode():
            cells = self.get_selected_cells()
            keyed = {(c['path'][0], c['col_key']):
                     ('' if c['value'] is None else str(c['value']))
                     for c in cells}
            if not keyed:
                return ''
            rows = sorted({r for (r, _) in keyed})
            user_keys = self._user_col_keys()
            cols_used = sorted({user_keys.index(k) for (_, k) in keyed
                                if k in user_keys})
            if not cols_used:
                return ''
            cmin, cmax = cols_used[0], cols_used[-1]
            lines = []
            for r in rows:
                lines.append('\t'.join(
                    keyed.get((r, user_keys[c]), '')
                    for c in range(cmin, cmax + 1)))
            return '\n'.join(lines)
        rows = sorted(p[0] for p in self.get_selected_paths())
        if not rows:
            return ''
        keys = self._user_col_keys()
        return '\n'.join(
            '\t'.join('' if self._row_at(r).get(k) is None
                      else str(self._row_at(r)[k]) for k in keys)
            for r in rows)

    def _selection_top_left(self):
        if self._is_cell_mode():
            cells = self.get_selected_cells()
            if not cells:
                return None
            user_keys = self._user_col_keys()
            return (min(c['path'][0] for c in cells),
                    min(user_keys.index(c['col_key']) for c in cells
                        if c['col_key'] in user_keys))
        paths = self.get_selected_paths()
        if not paths:
            return None
        return (min(p[0] for p in paths), 0)

    def copy_selection(self):
        tsv = self._build_selection_tsv()
        if not tsv:
            return
        QtGui.QApplication.clipboard().setText(tsv)
        self.make_callback('copy', tsv)

    def cut_selection(self):
        tsv = self._build_selection_tsv()
        if not tsv:
            return
        QtGui.QApplication.clipboard().setText(tsv)
        cells = (self.get_selected_cells() if self._is_cell_mode()
                 else [{'path': [r], 'col_key': k}
                       for p in self.get_selected_paths()
                       for r in [p[0]]
                       for k in self._user_col_keys()])
        for cell in cells:
            c = self._col_index(cell['col_key'])
            if c is None or not self._col_editable(c):
                continue
            r = cell['path'][0]
            item = self.widget.item(r, c)
            old = item.data(QtCore.Qt.UserRole) if item is not None else ''
            self.set_cell(r, c, '')
            self.make_callback('cell_edited', [r], cell['col_key'], old, '')
        self.make_callback('cut', tsv)

    def paste_selection(self):
        text = QtGui.QApplication.clipboard().text()
        if not text:
            return
        anchor = self._selection_top_left()
        if anchor is None:
            return
        anchor_row, anchor_col = anchor
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = text.split('\n')
        while lines and lines[-1] == '':
            lines.pop()
        n_cols = len(self._user_columns)
        n_rows = self.widget.rowCount()
        for i, line in enumerate(lines):
            r = anchor_row + i
            if r >= n_rows:
                break
            for j, val in enumerate(line.split('\t')):
                c = anchor_col + j
                if c >= n_cols:
                    break
                if not self._col_editable(c):
                    continue
                item = self.widget.item(r, c)
                old = item.data(QtCore.Qt.UserRole) if item is not None else ''
                self.set_cell(r, c, val)
                self.make_callback('cell_edited', [r],
                                   self._user_columns[c]['key'], old, val)
        self.make_callback('paste', text)

# END
