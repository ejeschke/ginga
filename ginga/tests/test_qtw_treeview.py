"""Tests for the qt TreeView's handling of interior-row values.

An interior (parent) row may carry column data of its own.  Columns it
says nothing about stay blank and the first falls back to the node's
key, so a tree that supplies no interior values renders exactly as it
always did.
"""

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

pytest.importorskip('qtpy')

# Import the backend directly: ginga.gw.Widgets binds a toolkit at
# import time, so what it offers depends on whether an earlier import
# already fixed the family.
from ginga.qtw import Widgets  # noqa: E402


@pytest.fixture(scope='module')
def app():
    return Widgets.Application()


@pytest.fixture
def tree(app):
    tree = Widgets.TreeView()
    tree.setup_table([('Name', 'name'), ('Grade', 'grade'),
                      ('Seeing', 'seeing')], 2, 'name')
    return tree


def _row(tree, path):
    item = tree._path_to_item(path)
    return [item.text(i) for i in range(len(tree.datakeys))]


def test_interior_without_values_shows_its_key(tree):
    """The pre-existing behaviour, guarded."""
    tree.set_tree({'ob1': {'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    assert _row(tree, ['ob1']) == ['ob1', '', '']


def test_interior_values_inline(tree):
    """Primitives alongside the child dicts are the interior's own."""
    tree.set_tree({'ob1': {'name': 'OB-042', 'grade': 'A',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    assert _row(tree, ['ob1']) == ['OB-042', 'A', '']
    assert _row(tree, ['ob1', 'e1']) == ['e1', '', '0.6']


def test_interior_values_sentinel(tree):
    tree.set_tree({'ob1': {'__values__': {'name': 'OB-042', 'grade': 'A'},
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    assert _row(tree, ['ob1']) == ['OB-042', 'A', '']


def test_values_never_become_a_row(tree):
    """The bug this fixes: __values__ rendered as a child row, and the
    interior's data was not shown on the interior."""
    tree.set_tree({'ob1': {'__values__': {'name': 'OB-042'},
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    item = tree._path_to_item(['ob1'])
    kids = [item.child(i).text(0) for i in range(item.childCount())]
    assert kids == ['e1']
    assert '__values__' not in tree.shadow['ob1'].node


def test_inline_values_never_become_a_row(tree):
    tree.set_tree({'ob1': {'name': 'OB-042', 'grade': 'A',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    item = tree._path_to_item(['ob1'])
    kids = [item.child(i).text(0) for i in range(item.childCount())]
    assert kids == ['e1']


def test_update_tree_refreshes_interior_values(tree):
    tree.set_tree({'ob1': {'name': 'OB-042', 'grade': 'A',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    tree.update_tree({'ob1': {'name': 'OB-042', 'grade': 'B',
                              'e1': {'name': 'e1', 'grade': '',
                                     'seeing': '1.4'}}})
    assert _row(tree, ['ob1']) == ['OB-042', 'B', '']
    assert _row(tree, ['ob1', 'e1'])[2] == '1.4'


def test_getters_do_not_leak_the_sentinel(tree):
    """get_* results are iterated as children by existing callers, so
    they keep the shape they have always had."""
    tree.set_tree({'ob1': {'__values__': {'name': 'OB-042'},
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    res = tree.get_children()
    assert list(res.keys()) == ['ob1']
    assert '__values__' not in res['ob1']


def test_interior_colours_still_resolve(tree):
    """Interior rows are also a colour target."""
    from ginga.qtw.QtHelp import QtCore
    tree.set_tree({'ob1': {'name': 'OB-042',
                           'e1': {'name': 'e1', 'grade': '',
                                  'seeing': '0.6'}}})
    tree.set_cell_color(['ob1'], 'grade', fg='red')
    item = tree._path_to_item(['ob1'])
    idx = tree.datakeys.index('grade')
    assert item.data(idx, QtCore.Qt.ForegroundRole) is not None
