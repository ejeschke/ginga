#
# toolbox.py -- Goodies for enhancing a Ginga viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

# STDLIB
import io
import os
import warnings

# THIRD-PARTY
from astropy.utils.data import get_pkg_data_contents
from astropy.utils.exceptions import AstropyUserWarning


class ModeIndicator(object):
    """
    This class adds a mode status indicator to a viewer's lower right-hand
    corner.

    Usage:
    Instantiate this class with a Ginga ImageView{Toolkit} object as the
    sole constructor argument.  Save a reference to the mode indicator
    object somewhere so it doesn't get collected.

    NOTE: Please don't use this class--it's likely to be deprecated!
    Instead, use the show_mode_indicator() method provided by the
    ImageView class.
    """

    def __init__(self, viewer):
        self.viewer = viewer

        # set to false to disable
        self.visible = True

        self.fontsize = 12
        self.xpad = 8
        self.ypad = 4
        self.offset = 10

        # for displaying modal keyboard state
        self.mode_obj = None
        bm = viewer.get_bindmap()
        bm.add_callback('mode-set', self.mode_change_cb)
        viewer.add_callback('configure', self._configure_cb)


    def mode_change_cb(self, bindmap, mode, modetype):
        # delete the old indicator
        obj = self.mode_obj
        self.mode_obj = None
        canvas = self.viewer.get_private_canvas()
        if obj:
            try:
                canvas.delete_object(obj)
            except:
                pass

        if not self.visible:
            return True

        # if not one of the standard modifiers, display the new one
        if not mode in (None, 'ctrl', 'shift'):
            Text = canvas.get_draw_class('text')
            Polygon = canvas.get_draw_class('polygon')
            Compound = canvas.get_draw_class('compoundobject')

            if modetype == 'locked':
                text = '%s [L]' % (mode)
            elif modetype == 'softlock':
                text = '%s [SL]' % (mode)
            else:
                text = mode

            o1 = Text(0, 0, text,
                      fontsize=self.fontsize, color='yellow', coord='canvas')

            txt_wd, txt_ht = self.viewer.renderer.get_dimensions(o1)

            box_wd, box_ht = 2 * self.xpad + txt_wd, 2 * self.ypad + txt_ht
            win_wd, win_ht = self.viewer.get_window_size()
            x_base, y_base = win_wd - self.offset - box_wd, win_ht - self.offset - box_ht

            o1.x, o1.y = x_base + self.xpad, y_base + txt_ht + self.ypad

            # yellow text on a black filled rectangle
            cx1, cy1, cx2, cy2 = x_base, y_base, x_base + box_wd, y_base + box_ht
            poly_pts = ((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2))
            o2 = Compound(Polygon(poly_pts,
                               color='black', coord='canvas',
                               fill=True, fillcolor='black'),
                               o1)
            self.mode_obj = o2
            canvas.add(o2)

        return True

    def _configure_cb(self, view, width, height):
        # redraw the mode indicator since the window has been resized
        bm = view.get_bindmap()
        mode, modetype = bm.current_mode()
        self.mode_change_cb(bm, mode, modetype)


def trim_prefix(text, nchr):
    """Trim characters off of the beginnings of text lines.

    Parameters
    ----------
    text : str
        The text to be trimmed, with newlines (\n) separating lines

    nchr: int
        The number of spaces to trim off the beginning of a line if
        it starts with that many spaces

    Returns
    -------
    text : str
        The trimmed text
    """
    res = []
    for line in text.split('\n'):
        if line.startswith(' ' * nchr):
            line = line[nchr:]
        res.append(line)

    return '\n'.join(res)


def generate_cfg_example(config_name, cfgpath='examples/configs', **kwargs):
    """Generate config file documentation for a given config name.

    If found, it will be a Python code block of the contents.
    If not found, it will have a generic message that the config
    is not available.

    Parameters
    ----------
    config_name : str
        Config name that is attached to the configuration file.
        This is the same as input for ``prefs.createCategory()``.
        For example, ``'general'``, ``'channel_Image'``, or
        ``'plugin_Zoom'``.

    cfgpath : str
        Where it is within package data.

    kwargs : dict
        Optional keywords for :func:`~astropy.utils.data.get_pkg_data_contents`.

    Returns
    -------
    docstr : str
        Docstring to be inserted into documentation.

    """
    cfgname = config_name + '.cfg'

    try:
        cfgdata = get_pkg_data_contents(
            os.path.join(cfgpath, cfgname), **kwargs)
    except Exception as e:
        warnings.warn(str(e), AstropyUserWarning)
        return ''

    homepath = '~'  # Symbol for HOME for doc only, not actual code
    userfile = os.path.join(homepath, '.ginga', cfgname)

    docstring = io.StringIO()
    docstring.write("""It is customizable using ``{0}``, where ``{1}``
is your HOME directory:

.. code-block:: Python

""".format(userfile, homepath))

    for line in cfgdata.split('\n'):
        line = line.strip()

        if len(line) == 0:
            docstring.write('\n')  # Prevent trailing spaces
        else:
            docstring.write('  {0}\n'.format(line))

    return docstring.getvalue()

#END
