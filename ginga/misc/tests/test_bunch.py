#
# test_bunch.py -- tests for ginga.misc.Bunch
#
import pickle

import pytest

from ginga.misc.Bunch import Bunch, caselessDict, threadSafeBunch


class TestBunch:

    def test_construct_kwargs(self):
        b = Bunch(a=1, b=2)
        assert b.a == 1 and b.b == 2
        assert b['a'] == 1 and b['b'] == 2

    def test_construct_indict(self):
        b = Bunch(inDict=dict(a=1, b=2))
        assert b.a == 1 and b['b'] == 2

    def test_construct_indict_and_kwargs(self):
        b = Bunch(inDict=dict(a=1), b=2)
        assert b.a == 1 and b.b == 2

    def test_construct_empty(self):
        b = Bunch()
        assert len(b) == 0

    def test_indict_is_copied(self):
        d = dict(a=1)
        b = Bunch(inDict=d)
        b.a = 99
        assert d['a'] == 1        # original not mutated

    def test_attr_get_set(self):
        b = Bunch(a=1)
        b.a = 5
        b.c = 7                   # new attr -> table entry
        assert b.a == 5 and b.c == 7
        assert b['c'] == 7

    def test_item_get_set_del(self):
        b = Bunch(a=1)
        b['b'] = 2
        assert b['b'] == 2 and b.b == 2
        del b['a']
        assert 'a' not in b

    def test_get_default(self):
        b = Bunch(a=1)
        assert b.get('a') == 1
        assert b.get('missing') is None
        assert b.get('missing', -1) == -1

    def test_getattr_explicit_default(self):
        # legacy explicit-call form: __getattr__(name, alt) -> alt on miss
        b = Bunch(a=1)
        assert b.__getattr__('a') == 1
        assert b.__getattr__('missing', 42) == 42

    def test_missing_attr_raises(self):
        b = Bunch(a=1)
        with pytest.raises(AttributeError):
            b.nope

    def test_setdefault(self):
        b = Bunch(a=1)
        assert b.setdefault('a', 9) == 1      # existing
        assert b.setdefault('b', 9) == 9      # new
        assert b.b == 9

    def test_keys_values_items(self):
        b = Bunch(a=1, b=2)
        assert set(b.keys()) == {'a', 'b'}
        assert set(b.values()) == {1, 2}
        assert set(b.items()) == {('a', 1), ('b', 2)}

    def test_update_store_setvals(self):
        b = Bunch(a=1)
        b.update(dict(b=2))
        b.store(dict(c=3))
        b.setvals(d=4)
        assert (b.a, b.b, b.c, b.d) == (1, 2, 3, 4)

    def test_contains_haskey(self):
        b = Bunch(a=1)
        assert 'a' in b and 'z' not in b
        assert b.has_key('a') and not b.has_key('z')

    def test_iter_len(self):
        b = Bunch(a=1, b=2)
        assert len(b) == 2
        assert set(iter(b)) == {'a', 'b'}

    def test_eq(self):
        assert Bunch(a=1, b=2) == Bunch(a=1, b=2)
        assert Bunch(a=1) != Bunch(a=2)
        assert Bunch(a=1) != dict(a=1)     # different class
        # symmetric and no KeyError when the key sets differ (was a bug:
        # the old __eq__ iterated only `other` and raised/answered asymmetrically)
        assert Bunch(a=1) != Bunch(a=1, b=2)
        assert Bunch(a=1, b=2) != Bunch(a=1)
        assert Bunch(a=1, b=2) != Bunch(a=1, b=3)

    def test_copy(self):
        b = Bunch(a=1)
        c = b.copy()
        c.a = 2
        assert b.a == 1 and c.a == 2

    def test_fetch_family(self):
        b = Bunch(a=1, b=2, c=3)
        d = dict(a=None, b=None)
        b.fetch(d)
        assert d == dict(a=1, b=2)
        assert b.fetchDict(dict(a=0, c=0)) == dict(a=1, c=3)
        assert b.fetchList(['b', 'c']) == [2, 3]

    def test_repr_roundtrip(self):
        b = Bunch(a=1, b=2)
        assert eval(repr(b)) == dict(a=1, b=2)

    def test_pickle_roundtrip(self):
        b = Bunch(a=1, b=2)
        b2 = pickle.loads(pickle.dumps(b))
        assert b2.a == 1 and b2.b == 2
        # non-literal values survive (the old repr()+literal_eval broke here)
        import datetime
        b3 = pickle.loads(pickle.dumps(Bunch(when=datetime.date(2020, 1, 2))))
        assert b3.when == datetime.date(2020, 1, 2)
        # internal state is restored, so a new attribute goes to the table
        b2.c = 3
        assert b2['c'] == 3

    def test_method_name_not_shadowed(self):
        # data stays in the table, so a key named like a method does not
        # break the method (mapped access still returns the data)
        b = Bunch(get=5, keys=6)
        assert b['get'] == 5 and b['keys'] == 6
        assert callable(b.get) and callable(b.keys)
        assert b.get('get') == 5

    def test_caseless(self):
        b = Bunch(caseless=True, Bar=4)
        assert b['BAR'] == 4 and b['bar'] == 4 and b.BaR == 4
        assert b.get('bAr') == 4
        assert b.setdefault('Bar', 99) == 4
        assert b.setdefault('New', 7) == 7 and b['NEW'] == 7


class TestCaselessDict:
    def test_basic(self):
        d = caselessDict(dict(Foo=1))
        d['Bar'] = 2
        assert d['FOO'] == 1 and d['bar'] == 2
        assert 'foo' in d and d.get('missing', -1) == -1


class TestThreadSafeBunch:
    def test_basic(self):
        b = threadSafeBunch(a=1)
        b.b = 2
        b['c'] = 3
        assert b.a == 1 and b.b == 2 and b['c'] == 3
        assert b.get('a') == 1 and b.get('z', -1) == -1
