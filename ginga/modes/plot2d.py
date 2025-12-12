#
# plot2d.py -- mode for manipulating 2D plots in PlotView based viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gw.PlotView import PlotViewBase
from ginga.misc import Bunch
from ginga.modes.mode_base import Mode


class Plot2DMode(Mode):
    """
    Plot2D Mode enables bindings that can set the pan position and zoom level
    (scale) in a Matplotlib plot viewer (ginga.gw.PlotView module).

    Enter the mode by
    -----------------
    * Space, then "p"

    Exit the mode by
    ----------------
    * Esc

    Default bindings in mode
    ------------------------
    * Shift + left click : set pan position
    * middle click : set pan position
    * scroll : zoom in/out
    * ctrl + scroll : zoom in/out X axis only
    * shift + scroll : zoom in/out Y axis only
    * alt + scroll : zoom in/out Y axis only
    * meta + scroll : zoom in/out at cursor
    """

    # Needs to be set by reference viewer (via set_shell_ref) before any
    # channel viewers are created
    fv = None

    @classmethod
    def set_shell_ref(cls, fv):
        cls.fv = fv

    @classmethod
    def is_compatible_viewer(cls, viewer):
        return isinstance(viewer, PlotViewBase)

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_plot2d=['__p', None, 'plot2d'],

            ms_showxy=['plot2d+nobtn'],
            ms_panset2d=['plot2d+middle', 'plot2d+shift+left'],

            sc_zoom2d=['plot2d+*+scroll'],
            #sc_zoom_x=['ctrl+scroll'],
            #sc_zoom_y=['shift+scroll'],

            #sc_zoom_origin=['meta+scroll'],
            plot_zoom_rate=1.2,
        )

        # for interactive features
        self.can = Bunch.Bunch(zoom=True, pan=True)

    @property
    def canpan(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('pan')

    @property
    def canzoom(self):
        bd = self.viewer.get_bindings()
        return bd.get_feature_allow('zoom')

    def __str__(self):
        return 'plot2d'

    def start(self):
        pass

    def stop(self):
        pass

    #####  SCROLL ACTION CALLBACKS #####

    def sc_zoom2d(self, viewer, event, msg=True):
        """Can be set as the callback function for the 'scroll'
        event to zoom the plot.
        """
        if not self.canzoom:
            return

        event.accept()
        # Matplotlib only gives us the number of steps of the scroll,
        # positive for up and negative for down.
        if event.amount > 0:
            delta = self.settings['plot_zoom_rate'] ** -2
        elif event.amount < 0:
            delta = self.settings['plot_zoom_rate'] ** 2

        delta_x = delta_y = delta
        if 'ctrl' in event.modifiers:
            # only horizontal
            delta_y = 1.0
        elif 'shift' in event.modifiers or 'alt' in event.modifiers:
            # only vertical
            # (shift works on Linux, but not Mac; alt works on Mac but
            #  not Linux....Grrr)
            delta_x = 1.0

        if 'meta' in event.modifiers or 'cmd' in event.modifiers:
            # cursor position
            cur_x, cur_y = event.data_x, event.data_y
            if None not in [cur_x, cur_y]:
                viewer.zoom_plot_at_cursor(cur_x, cur_y, delta_x, delta_y)
        else:
            viewer.zoom_plot(delta_x, delta_y)

        return True

    #####  MOUSE ACTION CALLBACKS #####

    def ms_showxy(self, viewer, event, data_x, data_y):
        """Motion event in the channel viewer window.  Show the pointing
        information under the cursor.
        """
        self.fv.showxy(viewer, data_x, data_y)
        return False

    def ms_panset2d(self, viewer, event, data_x, data_y, msg=True):
        """An interactive way to set the pan position.  The location
        (data_x, data_y) will be centered in the window.

        Can be set as the callback function for the 'button-press'
        event to pan the plot with middle-click.
        """
        if not self.canpan:
            return False

        event.accept()
        if event.state != 'down':
            return

        if not self.can.pan:
            return
        cur_x, cur_y = event.data_x, event.data_y

        if None not in [cur_x, cur_y]:
            viewer.set_pan(cur_x, cur_y)

        return True
