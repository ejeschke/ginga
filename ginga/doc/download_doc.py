"""Download rendered HTML doc from RTD."""

import os
import shutil
import sys
import zipfile

from astropy.utils.data import download_file, _find_pkg_data_path

__all__ = ['get_doc']


def _download_latest_zip(**kwargs):
    """
    Download and extract latest HTML ZIP from RTD to installed doc data path.
    Download is skipped if content already exists.

    Parameters
    ----------
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

    data_path = os.path.dirname(
        _find_pkg_data_path('help.html', package='ginga.doc'))
    index_html = os.path.join(data_path, 'index.html')

    if os.path.isfile(index_html):
        return index_html

    url = 'https://readthedocs.org/projects/ginga/downloads/htmlzip/latest/'
    local_path = download_file(url, **kwargs)

    with zipfile.ZipFile(local_path, 'r') as zf:
        zf.extractall(data_path)

    # RTD makes an undesirable sub-directory, so move everything there
    # up one level and delete it.
    subdir = os.path.join(data_path, 'ginga-latest')
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
    url : str
        URL to local documentation, if available, or online.

    """
    from ginga.GingaPlugin import GlobalPlugin, LocalPlugin

    if isinstance(plugin, GlobalPlugin):
        plugin_page = 'plugins_global'
        plugin_name = str(plugin)
    elif isinstance(plugin, LocalPlugin):
        plugin_page = 'plugins_local'
        plugin_name = str(plugin)
    else:
        plugin_page = None
        plugin_name = None

    try:
        index_html = _download_latest_zip()

    # Download failed, use online resource
    except Exception:
        url = 'https://ginga.readthedocs.io/en/latest/'

        if plugin_name is not None:
            url += '{}/{}.html'.format(plugin_page, plugin_name)

    # Use local resource
    # https://github.com/rtfd/readthedocs.org/issues/2803
    else:
        pfx = 'file:'
        url = '{}{}'.format(pfx, index_html)

        if plugin_name is not None:
            url += '#{}'.format(plugin_name)

    return url
