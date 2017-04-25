"""Download rendered HTML doc from RTD."""
from __future__ import absolute_import, division, print_function
from ginga.util.six.moves import urllib

import os
import shutil
import sys
import zipfile

from astropy.utils import minversion
from astropy.utils.data import download_file, _find_pkg_data_path

__all__ = ['get_doc']


def _find_rtd_version():
    """Find closest RTD doc version."""
    vstr = 'latest'
    try:
        import ginga
        from bs4 import BeautifulSoup
    except ImportError:
        return vstr

    # No active doc build before this release, just use latest.
    if not minversion(ginga, '2.6.0'):
        return vstr

    # Get RTD download listing.
    with urllib.request.urlopen(
            'https://readthedocs.org/projects/ginga/downloads/') as r:
        soup = BeautifulSoup(r, 'html.parser')

    # Compile a list of available HTML doc versions for download.
    all_rtd_vernums = []
    for link in soup.find_all('a'):
        href = link.get('href')
        if 'htmlzip' not in href:
            continue
        s = href.split('/')[-2]
        if s.startswith('v'):  # Ignore latest and stable
            all_rtd_vernums.append(s)
    all_rtd_vernums.sort(reverse=True)

    # Find closest match.
    ginga_ver = ginga.__version__
    for rtd_ver in all_rtd_vernums:
        if ginga_ver > rtd_ver[1:]:  # Ignore "v" in comparison
            break
        else:
            vstr = rtd_ver

    return vstr


def _download_rtd_zip(rtd_version=None, **kwargs):
    """
    Download and extract HTML ZIP from RTD to installed doc data path.
    Download is skipped if content already exists.

    Parameters
    ----------
    rtd_version : str or `None`
        RTD version to download; e.g., "latest", "stable", or "v2.6.0".
        If not given, download closest match to software version.

    kwargs : dict
        Keywords for :func:`astropy.utils.data.download_file`.

    Returns
    -------
    index_html : str
        Path to local "index.html".

    """
    # TODO: Add Windows support.
    if sys.platform.startswith('win'):
        raise OSError('Windows is not supported')

    if rtd_version is None:
        rtd_version = _find_rtd_version()

    data_path = os.path.dirname(
        _find_pkg_data_path('help.html', package='ginga.doc'))
    index_html = os.path.join(data_path, 'index.html')

    # There is a previous download of documentation; Do nothing.
    # There is no check if downloaded version is outdated; The idea is that
    # this folder would be empty again when installing new version.
    if os.path.isfile(index_html):
        return index_html

    url = ('https://readthedocs.org/projects/ginga/downloads/htmlzip/'
           '{}/'.format(rtd_version))
    local_path = download_file(url, **kwargs)

    with zipfile.ZipFile(local_path, 'r') as zf:
        zf.extractall(data_path)

    # RTD makes an undesirable sub-directory, so move everything there
    # up one level and delete it.
    subdir = os.path.join(data_path, 'ginga-{}'.format(rtd_version))
    for s in os.listdir(subdir):
        src = os.path.join(subdir, s)
        if os.path.isfile(src):
            shutil.copy(src, data_path)
        else:  # directory
            shutil.copytree(src, os.path.join(data_path, s))
    shutil.rmtree(subdir)

    if not os.path.isfile(index_html):
        raise OSError(
            '{} is missing; Ginga doc download failed'.format(index_html))

    return index_html


def get_doc(plugin=None):
    """
    Return URL to documentation. Attempt download if does not exist.

    Parameters
    ----------
    plugin : obj or `None`
        Plugin object. If given, URL points to plugin doc directly.
        If this function is called from within plugin class,
        pass ``self`` here.

    Returns
    -------
    url : str or `None`
        URL to local documentation, if available.

    """
    from ginga.GingaPlugin import GlobalPlugin, LocalPlugin

    if isinstance(plugin, GlobalPlugin):
        # plugin_page = 'plugins_global'
        plugin_name = str(plugin)
    elif isinstance(plugin, LocalPlugin):
        # plugin_page = 'plugins_local'
        plugin_name = str(plugin)
    else:
        # plugin_page = None
        plugin_name = None

    try:
        index_html = _download_rtd_zip()

    # Download failed, use online resource
    except Exception:
        url = 'https://ginga.readthedocs.io/en/latest/'

        if plugin_name is not None:
            # This redirects to online doc.
            # url += '{}/{}.html'.format(plugin_page, plugin_name)
            # This displays plugin docstring.
            url = None

    # Use local resource
    else:
        pfx = 'file:'
        url = '{}{}'.format(pfx, index_html)

        # https://github.com/rtfd/readthedocs.org/issues/2803
        if plugin_name is not None:
            url += '#{}'.format(plugin_name)

    return url
