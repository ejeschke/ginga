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
    """

    def __init__(self, viewer):
        self.viewer = viewer

        # set to false to disable
        self.visible = True

        self.fontsize = 12

        # for displaying modal keyboard state
        self.mode_obj = None
        bm = viewer.get_bindmap()
        bm.add_callback('mode-set', self.mode_change_cb)
        viewer.add_callback('configure', self._configure_cb)


    def mode_change_cb(self, bindmap, mode, modetype):
        # delete the old indicator
        obj = self.mode_obj
        self.mode_obj = None
        #canvas = self.viewer.get_canvas()
        canvas = self.viewer.private_canvas
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
            Rect = canvas.get_draw_class('rectangle')
            Compound = canvas.get_draw_class('compoundobject')

            if modetype == 'locked':
                text = '%s [L]' % (mode)
            elif modetype == 'softlock':
                text = '%s [SL]' % (mode)
            else:
                text = mode

            xsp, ysp = 4, 6
            wd, ht = self.viewer.get_window_size()
            wd, ht = int(wd), int(ht)
            if self.viewer._originUpper:
                x1, y1 = wd-self.fontsize*len(text), ht-self.fontsize
            else:
                # matplotlib case
                x1, y1 = wd-self.fontsize*len(text), self.fontsize

            o1 = Text(x1, y1, text,
                      fontsize=self.fontsize, color='yellow', coord='canvas')

            wd, ht = self.viewer.renderer.get_dimensions(o1)

            # yellow text on a black filled rectangle
            if self.viewer._originUpper:
                a1, b1, a2, b2 = x1-xsp, y1+ysp, x1+wd+xsp, y1-ht
            else:
                # matplotlib case
                a1, b1, a2, b2 = x1-xsp, y1-ysp, x1+wd+2*xsp, y1+ht+ysp
            o2 = Compound(Rect(a1, b1, a2, b2,
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


def generate_cfg_example(config_name, **kwargs):
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

    kwargs : dict
        Optional keywords for :func:`~astropy.utils.data.get_pkg_data_contents`.

    Returns
    -------
    docstr : str
        Docstring to be inserted into documentation.

    """
    cfgpath = 'examples/configs'  # Where it is in pkg data
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
