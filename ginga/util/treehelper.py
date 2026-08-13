"""Helpers for the dict-shaped trees the TreeView widgets consume.

A tree is a dict keyed by stable identifiers.  Leaf nodes are dicts of
column-key -> value.  An *interior* node holds its children, and may
also carry column values of its own -- so a parent row can show data
rather than only its key.

Two forms are accepted for those values, matching the pg backend:

* an explicit ``__values__`` entry::

      {'ob1': {'__values__': {'name': 'OB-042', 'grade': 'A'},
               'e1': {...}, 'e2': {...}}}

* or, more simply, primitive entries sitting alongside the child
  dicts -- dict-valued entries are children, everything else is the
  interior's own column data::

      {'ob1': {'name': 'OB-042', 'grade': 'A',
               'e1': {...}, 'e2': {...}}}

The second form needs no sentinel and is usually what you want; the
first exists for the ambiguous case of a column whose value is itself a
dict.

Interior values are optional: a node that supplies none renders blank
columns, with the first column falling back to the node's key, which is
how these widgets behaved before interior values were supported.

This lives here, rather than in each backend, so the qt, gtk and pg
wrappers cannot drift on the question of what counts as a child.
"""

VALUES_KEY = '__values__'

__all__ = ['VALUES_KEY', 'split_node', 'row_values']


def split_node(node):
    """Split an interior node into (own values, children).

    Both parts are dicts and either may be empty.  Only meaningful for
    interior nodes -- at leaf level the whole dict is column data, so
    the caller shouldn't split it (a leaf column value that happens to
    be a dict would otherwise look like a child).
    """
    if not isinstance(node, dict):
        return {}, {}

    if VALUES_KEY in node:
        values = node.get(VALUES_KEY) or {}
        children = {key: value for key, value in node.items()
                    if key != VALUES_KEY}
        return (dict(values) if isinstance(values, dict) else {}), children

    values = {}
    children = {}
    for key, value in node.items():
        if isinstance(value, dict):
            children[key] = value
        else:
            values[key] = value
    return values, children


def row_values(values, datakeys, key=None, blank=''):
    """Return the value to display for each of `datakeys`.

    Columns the node said nothing about come back as `blank`.  When
    `key` is given, it is the fallback for the *first* column, so an
    interior that supplies no values still shows its own name there --
    the behaviour these widgets have always had.
    """
    values = values or {}
    out = {}
    for i, datakey in enumerate(datakeys):
        if datakey in values:
            out[datakey] = values[datakey]
        elif i == 0 and key is not None:
            out[datakey] = key
        else:
            out[datakey] = blank
    return out
