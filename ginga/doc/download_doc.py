"""Tools for accessing HTML doc from RTD."""

import re

from ginga.GingaPlugin import GlobalPlugin, LocalPlugin
import ginga

__all__ = ['get_online_docs_url']

# base of our online documentation
rtd_base_url = "https://ginga.readthedocs.io/en/"


def get_online_docs_url(plugin=None):
    """
    Return URL to online documentation closest to this Ginga version.

    Parameters
    ----------
    plugin : obj or `None`
        Plugin object. If given, URL points to plugin doc directly.
        If this function is called from within plugin class,
        pass ``self`` here.

    Returns
    -------
    url : str
        URL to online documentation (top-level, if plugin == None).

    """
    ginga_ver = ginga.__version__
    if re.match(r'^v\d+\.\d+\.\d+$', ginga_ver):
        rtd_version = ginga_ver
    else:
        # default to latest
        rtd_version = 'latest'
    url = f"{rtd_base_url}{rtd_version}"
    if plugin is not None:
        plugin_name = str(plugin)
        if isinstance(plugin, GlobalPlugin):
            url += f'/manual/plugins_global/{plugin_name}.html'
        elif isinstance(plugin, LocalPlugin):
            url += f'/manual/plugins_local/{plugin_name}.html'

    return url
