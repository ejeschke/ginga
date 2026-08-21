"""Tests for the shared dict-tree helpers.

These decide what counts as a child and what counts as an interior
row's own column data, for every TreeView backend -- so they are worth
pinning independently of any one widget set.
"""

from ginga.util import treehelper


class TestSplitNode:

    def test_primitives_are_values_dicts_are_children(self):
        values, children = treehelper.split_node(
            {'name': 'OB-042', 'grade': 'A',
             'e1': {'name': 'e1'}, 'e2': {'name': 'e2'}})
        assert values == {'name': 'OB-042', 'grade': 'A'}
        assert sorted(children) == ['e1', 'e2']

    def test_a_mapping_interior_is_split_like_a_dict(self):
        """Bunch interiors predate interior values -- back when the
        widget only iterated a parent, any mapping would do."""
        from ginga.misc.Bunch import Bunch

        values, children = treehelper.split_node(
            Bunch(name='OB-042', e1=Bunch(name='e1'), e2={'name': 'e2'}))
        assert values == {'name': 'OB-042'}
        assert sorted(children) == ['e1', 'e2']

    def test_a_mapping_valued_column_needs_the_values_key(self):
        """A mapping alongside the children is read as a child; say so
        explicitly when it is really this row's own column value."""
        from ginga.misc.Bunch import Bunch

        values, children = treehelper.split_node(
            {'__values__': {'meta': Bunch(a=1)}, 'e1': {'name': 'e1'}})
        assert list(values) == ['meta']
        assert list(children) == ['e1']

    def test_not_a_mapping_at_all(self):
        assert treehelper.split_node('leaf') == ({}, {})
        assert treehelper.split_node(None) == ({}, {})

    def test_explicit_values_key(self):
        values, children = treehelper.split_node(
            {'__values__': {'name': 'OB-042'}, 'e1': {'name': 'e1'}})
        assert values == {'name': 'OB-042'}
        assert list(children) == ['e1']

    def test_values_key_wins_and_is_never_a_child(self):
        """The sentinel form allows a column whose value is a dict."""
        values, children = treehelper.split_node(
            {'__values__': {'meta': {'nested': 1}}, 'e1': {'name': 'e1'}})
        assert values == {'meta': {'nested': 1}}
        assert list(children) == ['e1']

    def test_no_values(self):
        values, children = treehelper.split_node({'e1': {'name': 'e1'}})
        assert values == {}
        assert list(children) == ['e1']

    def test_no_children(self):
        values, children = treehelper.split_node({'name': 'ob1'})
        assert values == {'name': 'ob1'}
        assert children == {}

    def test_empty_and_non_dict(self):
        assert treehelper.split_node({}) == ({}, {})
        assert treehelper.split_node(None) == ({}, {})
        assert treehelper.split_node('x') == ({}, {})

    def test_empty_values_key(self):
        values, children = treehelper.split_node(
            {'__values__': None, 'e1': {'name': 'e1'}})
        assert values == {}
        assert list(children) == ['e1']


class TestRowValues:

    datakeys = ['name', 'grade', 'seeing']

    def test_unsupplied_columns_are_blank(self):
        out = treehelper.row_values({'grade': 'A'}, self.datakeys)
        assert out == {'name': '', 'grade': 'A', 'seeing': ''}

    def test_key_is_the_first_column_fallback(self):
        """An interior that supplies nothing still shows its own name,
        which is how these rows behaved before interior values."""
        out = treehelper.row_values({}, self.datakeys, key='ob1')
        assert out == {'name': 'ob1', 'grade': '', 'seeing': ''}

    def test_supplied_first_column_wins_over_the_key(self):
        out = treehelper.row_values({'name': 'OB-042'}, self.datakeys,
                                    key='ob1')
        assert out['name'] == 'OB-042'

    def test_no_key_means_no_fallback(self):
        out = treehelper.row_values({}, self.datakeys)
        assert out['name'] == ''


class TestSuppliedKeys:

    datakeys = ['name', 'grade', 'seeing']

    def test_a_dict_reports_its_own_keys(self):
        assert treehelper.supplied_keys({'name': 'x', 'extra': 1}) == \
            {'name', 'extra'}

    def test_a_mapping_without_keys_is_probed_by_column(self):
        """catalog.Star used to be one of these: it answers ``in`` and
        ``[]`` but has no ``keys()``, and a tree full of them must not
        raise."""
        class Star:
            def __init__(self, **kwargs):
                self._d = kwargs

            def __contains__(self, key):
                return key in self._d

            def __getitem__(self, key):
                return self._d[key]

        star = Star(name='s0', seeing='0.6', extra=1)
        # only the columns we know to ask about come back
        assert treehelper.supplied_keys(star, self.datakeys) == \
            {'name', 'seeing'}

    def test_no_datakeys_means_nothing_to_probe(self):
        class Opaque:
            def __contains__(self, key):
                return True

        assert treehelper.supplied_keys(Opaque()) == set()
