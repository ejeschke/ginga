"""Helpers for the dict-shaped trees the TreeView widgets consume.

A tree is a dict keyed by stable identifiers.  Leaf nodes are dicts of
column-key -> value.  An *interior* node holds its children, and may
also carry column values of its own -- so a parent row can show data
rather than only its key.

"Dict" is meant loosely throughout: any mapping-like object will do
(see `is_mapping`), which is how these trees have always been filled --
``Bunch`` interiors and ``catalog.Star`` leaves are both common.

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

__all__ = ['VALUES_KEY', 'is_mapping', 'split_node', 'row_values',
           'supplied_keys', 'normalize_column']


def is_mapping(obj):
    """Is `obj` dict-like enough to be a node of one of these trees?

    Deliberately duck-typed rather than ``isinstance(obj, dict)``: these
    widgets have always been filled with mapping-like objects that are
    not dicts -- ``Bunch`` interiors, ``catalog.Star`` leaves -- and the
    tree walk only ever iterated them and indexed into them.  The
    ``collections.abc.Mapping`` ABC is no help either, since neither of
    those registers as one.
    """
    return hasattr(obj, 'keys') and hasattr(obj, '__getitem__')


def split_node(node):
    """Split an interior node into (own values, children).

    Both parts are dicts and either may be empty.  Only meaningful for
    interior nodes -- at leaf level the whole dict is column data, so
    the caller shouldn't split it (a leaf column value that happens to
    be a dict would otherwise look like a child).

    A mapping-valued entry counts as a child.  When an interior really
    does have a column whose value is a mapping, name its own values
    explicitly with ``__values__``.
    """
    if not is_mapping(node):
        return {}, {}

    if VALUES_KEY in node:
        own = node[VALUES_KEY]
        children = {key: node[key] for key in node.keys()
                    if key != VALUES_KEY}
        return (dict(own) if is_mapping(own) else {}), children

    values = {}
    children = {}
    for key in node.keys():
        value = node[key]
        if is_mapping(value):
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


def supplied_keys(node, datakeys=()):
    """Which columns `node` actually supplied.

    Leaf nodes are normally dicts, but a caller is free to hand these
    widgets any mapping-like object -- ginga's own Catalogs plugin fills
    a tree with ``catalog.Star`` instances -- so fall back to probing
    the known columns when there is no ``keys()`` to ask.
    """
    if is_mapping(node):
        return set(node.keys())
    return set(key for key in datakeys if key in node)


def normalize_column(col, index=0):
    """Normalise a column descriptor to a dict.

    Accepts the portable ``(label, key[, type])`` tuple, a bare string,
    or the full dict form the pg backend takes -- so ``editable``,
    ``widget`` / ``choices``, ``visible_key`` and ``enabled_key``
    survive on their way to a desktop backend instead of being dropped.
    """
    if isinstance(col, dict):
        key = col.get('key') or col.get('label') or f'col{index}'
        dtype = col.get('type') or ('icon' if key == 'icon' else 'str')
        if dtype == 'string':
            dtype = 'str'
        spec = dict(col)
        spec.update(label=col.get('label', key), key=key, type=dtype)
        return spec

    if isinstance(col, str):
        return dict(label=col, key=col,
                    type=('icon' if col == 'icon' else 'str'))

    label = col[0]
    key = col[1] if len(col) > 1 else label
    dtype = col[2] if len(col) > 2 else ('icon' if key == 'icon' else 'str')
    return dict(label=label, key=key, type=dtype)
