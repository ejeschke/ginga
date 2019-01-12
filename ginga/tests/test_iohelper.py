# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys

from ginga.util import iohelper

IS_WINDOWS = sys.platform.startswith('win')


def test_get_fileinfo_real_file():
    """Test behavior on real file."""
    bnch = iohelper.get_fileinfo(iohelper.__file__)
    assert bnch['ondisk']
    assert bnch['name'] == 'iohelper'
    assert bnch['numhdu'] is None
    # filepath and url are OS-dependent, hence the lax check here
    assert bnch['url'].startswith('file://')


def test_get_fileinfo_dummy_file():
    """Test behavior on dummy file."""

    # pathlib behaves differently depending on OS.
    if IS_WINDOWS:
        filename = r'C:\mypath\dummyfile.fits[1]'
        filepath = 'C:\\mypath\\dummyfile.fits'
        url = 'file:///C:/mypath/dummyfile.fits'
    else:
        filename = '/mypath/dummyfile.fits[1]'
        filepath = '/mypath/dummyfile.fits'
        url = 'file:///mypath/dummyfile.fits'

    bnch = iohelper.get_fileinfo(filename)
    assert not bnch['ondisk']
    assert bnch['name'] == 'dummyfile[1]'
    assert bnch['numhdu'] == 1
    assert bnch['filepath'] == filepath
    assert bnch['url'] == url
