#
# tablehelper.py -- feed ginga TableView widgets from astropy Tables / numpy
#
# The TableView wrappers (qtw / gtk3w / gtk4w / web.pgw) all build on
# set_columns() + set_rows(), so these converters just produce the column
# descriptors and row lists those methods already accept.
#
# astropy is intentionally NOT imported here: a Table is handled duck-typed
# (needs only ``.colnames`` and ``table[name]`` column access), so importing
# this module never drags in astropy.
#
import numpy as np

# numpy dtype.kind -> TableView column type (drives display/sort).  Anything
# unrecognised (datetime, object, bytes, ...) falls back to 'string'.
_KIND_TO_TYPE = {'i': 'int', 'u': 'int', 'f': 'float', 'b': 'bool'}


def _col_type(col):
    dt = getattr(col, 'dtype', None)
    return _KIND_TO_TYPE.get(getattr(dt, 'kind', None), 'string')


def _col_values(col):
    # native python list; masked entries come back as None
    if hasattr(col, 'tolist'):
        return col.tolist()
    return list(col)


def _colnames(table):
    # astropy Table exposes .colnames; pandas DataFrame exposes .columns.
    # (astropy also has a .columns mapping, so check .colnames first.)  This
    # is all duck-typed -- neither astropy nor pandas is imported here.
    names = getattr(table, 'colnames', None)
    if names is not None:
        return list(names)
    return list(table.columns)


def columns_from_table(table):
    """Build TableView column descriptors from an astropy Table or a pandas
    DataFrame.

    The column name becomes both the key and the label; the type is inferred
    from the column's dtype.  Duck-typed: works with anything exposing
    ``.colnames``/``.columns`` and ``table[name]``.
    """
    return [dict(label=name, key=name, type=_col_type(table[name]))
            for name in _colnames(table)]


def rows_from_table(table):
    """Return an astropy Table's (or pandas DataFrame's) contents as a list of
    row dicts keyed by column name (values converted to native python types)."""
    names = _colnames(table)
    cols = [_col_values(table[name]) for name in names]
    return [dict(zip(names, vals)) for vals in zip(*cols)]


def rows_from_ndarray(data):
    """Convert a numpy array into TableView rows.

    * structured / record array -> list of dicts keyed by field name
    * 2-D array -> list of positional rows (mapped to columns in order)
    * 1-D array -> list of single-value rows

    Values are converted to native python types (via ``tolist``), so numpy
    scalars don't leak into the widget / JSON layers.
    """
    if data.dtype.names is not None:
        names = data.dtype.names
        return [dict(zip(names, rec)) for rec in data.tolist()]
    if data.ndim <= 1:
        return [[v] for v in data.tolist()]
    return data.tolist()


def is_ndarray(data):
    """True if ``data`` looks like a numpy array (duck-typed on dtype+ndim),
    so callers can decide to route it through :func:`rows_from_ndarray`
    without importing numpy themselves."""
    return isinstance(data, np.ndarray)

#END
