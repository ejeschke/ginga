"""Tests for the catalog Star container.

A star is a bag of named fields that gets handed both to things that
expect a mapping (the TreeView widgets build a row from whatever keys a
node supplies) and to numpy (the Catalogs plugin filters a star list
against a shape).  Those two pull in opposite directions, which is what
these tests pin down.
"""

import numpy as np

from ginga.util.catalog import Star


def _stars(n=3):
    return [Star(name='s%d' % i, ra_deg=1.0 * i, dec_deg=2.0 * i)
            for i in range(n)]


class TestMappingProtocol:

    def test_item_access(self):
        star = Star(name='s0', mag=12.0)
        assert star['name'] == 's0'
        star['mag'] = 13.0
        assert star['mag'] == 13.0
        del star['mag']
        assert 'mag' not in star
        assert star.has_key('name')       # noqa

    def test_keys_values_items(self):
        star = Star(name='s0', mag=12.0)
        assert sorted(star.keys()) == ['mag', 'name']
        assert set(star.values()) == {'s0', 12.0}
        assert dict(star.items()) == {'name': 's0', 'mag': 12.0}

    def test_get_and_update(self):
        star = Star(name='s0')
        assert star.get('mag') is None
        assert star.get('mag', 99.0) == 99.0
        star.update(dict(mag=12.0))
        assert star['mag'] == 12.0
        star.clear()
        assert list(star.keys()) == []

    def test_a_star_converts_to_a_dict(self):
        """Which is how the widget backends read a row's columns; it
        goes through keys(), needing no __iter__."""
        assert dict(Star(name='s0', mag=12.0)) == {'name': 's0', 'mag': 12.0}


class TestNumpyTreatsAStarAsOneObject:

    def test_a_star_list_is_a_1d_object_array(self):
        """Star must stay un-sized and non-iterable: numpy unpacks
        anything it can walk, so adding __len__/__iter__ would turn a
        star list into a 2-D array of field names, and indexing one of
        those with a column key raises IndexError."""
        arr = np.array(_stars())

        assert arr.shape == (3,)
        assert arr.dtype == object
        assert arr[1]['ra_deg'] == 1.0

    def test_a_filtered_star_list_still_holds_stars(self):
        """What Catalogs.filter_results() does to keep the stars inside
        a shape."""
        stars = _stars()
        keep = np.array([True, False, True])

        picked = [stars[i] for i in np.flatnonzero(keep)]

        assert [star['name'] for star in picked] == ['s0', 's2']
