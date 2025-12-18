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
    * shift + scroll : zoom in/out Y axis only (On MacOS, trackpad only)
    * alt + scroll(mouse) : zoom in/out Y axis only (Option key on Macs)
    * alt + scroll : zoom in/out at cursor

    Keystroke bindings
    ------------------

    Zooming
    -------
    * equals : zoom in one zoom level
    * ctrl + equals : zoom in X axis one zoom level
    * plus (shift + equals) : zoom in Y axis one zoom level
    * minus : zoom out one zoom level
    * ctrl + minus : zoom out X axis one zoom level
    * underscore (shift + minus): zoom out Y axis one zoom level
    * 9 : zoom out maintaining cursor position
    * ctrl + 9 : zoom out X axis maintaining cursor position
    * left paren (shift + 9): zoom out Y axis maintaining cursor position
    * 0 : zoom in maintaining cursor position
    * ctrl + 0 : zoom in X axis maintaining cursor position
    * right paren (shift + 0): zoom in Y axis maintaining cursor position
    * backquote : zoom X and Y axes to fit window
    * 1 : zoom X axis only to fit window
    * 2 : zoom Y axis only to fit window
    * k : set lower X range to X value at cursor
    * l : set upper X range to X value at cursor
    * K : set lower Y range to Y value at cursor
    * L : set upper Y range to Y value at cursor

    Panning
    -------
    * left arrow : pan left
    * right arrow : pan right
    * up arrow : pan up
    * down arrow : pan down

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

            sc_zoom2d=['plot2d+scroll'],
            sc_zoom2d_x=['plot2d+ctrl+scroll'],
            sc_zoom2d_y=['plot2d+shift+scroll'],
            sc_zoom2d_cursor=['plot2d+win+scroll'],

            kp_pan_left=['plot2d+left'],
            kp_pan_right=['plot2d+right'],
            kp_pan_up=['plot2d+up'],
            kp_pan_down=['plot2d+down'],

            kp_zoom_in=['plot2d+='],
            kp_zoom_in_x=['plot2d+ctrl+='],
            kp_zoom_in_y=['plot2d+shift++'],
            kp_zoom_out=['plot2d+-'],
            kp_zoom_out_x=['plot2d+ctrl+-'],
            kp_zoom_out_y=['plot2d+shift+_'],

            kp_zoom_cursor_in=['plot2d+0'],
            kp_zoom_cursor_in_x=['plot2d+ctrl+0'],
            kp_zoom_cursor_in_y=['plot2d+shift+)'],
            kp_zoom_cursor_out=['plot2d+9'],
            kp_zoom_cursor_out_x=['plot2d+ctrl+9'],
            kp_zoom_cursor_out_y=['plot2d+shift+('],

            kp_zoom_fit=['plot2d+backquote'],
            kp_zoom_fit_x=['plot2d+1'],
            kp_zoom_fit_y=['plot2d+2'],

            kp_cut_x_lo=['plot2d+k'],
            kp_cut_x_hi=['plot2d+l'],
            kp_cut_y_lo=['plot2d+K'],
            kp_cut_y_hi=['plot2d+L'],

            plot_zoom_rate=1.2,
            plot_pan_pct=0.10,
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

    def __zoom(self, viewer, delta_x, delta_y, origin=None):

        if origin is not None:
            cur_x, cur_y = origin
            if None not in origin:
                viewer.zoom_plot_at_cursor(cur_x, cur_y, delta_x, delta_y)
        else:
            viewer.zoom_plot(delta_x, delta_y)

        return True

    def __zoom2d(self, viewer, event, axis='xy', origin=None):
        if not self.canzoom:
            return False

        event.accept()
        # Matplotlib only gives us the number of steps of the scroll,
        # positive for up and negative for down.
        if event.amount > 0:
            delta = self.settings['plot_zoom_rate'] ** -2
        elif event.amount < 0:
            delta = self.settings['plot_zoom_rate'] ** 2

        delta_x = delta_y = delta
        if axis == 'x':
            # only horizontal
            delta_y = 1.0
        elif axis == 'y':
            # only vertical
            delta_x = 1.0

        return self.__zoom(viewer, delta_x, delta_y, origin=origin)

    def sc_zoom2d(self, viewer, event):
        """Can be set as the callback function for the 'scroll'
        event to zoom the plot.
        """
        return self.__zoom2d(viewer, event)

    def sc_zoom2d_x(self, viewer, event):
        return self.__zoom2d(viewer, event, axis='x')

    def sc_zoom2d_y(self, viewer, event):
        return self.__zoom2d(viewer, event, axis='y')

    def sc_zoom2d_cursor(self, viewer, event):
        return self.__zoom2d(viewer, event,
                             origin=(event.data_x, event.data_y))

    def sc_zoom2d_cursor_x(self, viewer, event):
        return self.__zoom2d(viewer, event, axis='x',
                             origin=(event.data_x, event.data_y))

    def sc_zoom2d_cursor_y(self, viewer, event):
        return self.__zoom2d(viewer, event, axis='y',
                             origin=(event.data_x, event.data_y))

    #####  MOUSE ACTION CALLBACKS #####

    def ms_showxy(self, viewer, event, data_x, data_y):
        """Motion event in the channel viewer window.  Show the pointing
        information under the cursor.
        """
        self.fv.showxy(viewer, data_x, data_y)
        return False

    def ms_panset2d(self, viewer, event, data_x, data_y):
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

        if None not in [data_x, data_y]:
            viewer.set_pan(data_x, data_y)

        return True

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_zoom_out(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta = self.settings['plot_zoom_rate'] ** 2
        delta_x = delta_y = delta
        return self.__zoom(viewer, delta_x, delta_y)

    def kp_zoom_out_x(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = self.settings['plot_zoom_rate'] ** 2
        delta_y = 1.0
        return self.__zoom(viewer, delta_x, delta_y)

    def kp_zoom_out_y(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = 1.0
        delta_y = self.settings['plot_zoom_rate'] ** 2
        return self.__zoom(viewer, delta_x, delta_y)

    def kp_zoom_in(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta = self.settings['plot_zoom_rate'] ** -2
        delta_x = delta_y = delta
        return self.__zoom(viewer, delta_x, delta_y)

    def kp_zoom_in_x(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = self.settings['plot_zoom_rate'] ** -2
        delta_y = 1.0
        return self.__zoom(viewer, delta_x, delta_y)

    def kp_zoom_in_y(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = 1.0
        delta_y = self.settings['plot_zoom_rate'] ** -2
        return self.__zoom(viewer, delta_x, delta_y)

    def kp_zoom_cursor_out(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta = self.settings['plot_zoom_rate'] ** 2
        delta_x = delta_y = delta
        return self.__zoom(viewer, delta_x, delta_y, origin=(data_x, data_y))

    def kp_zoom_cursor_out_x(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = self.settings['plot_zoom_rate'] ** 2
        delta_y = 1.0
        return self.__zoom(viewer, delta_x, delta_y, origin=(data_x, data_y))

    def kp_zoom_cursor_out_y(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = 1.0
        delta_y = self.settings['plot_zoom_rate'] ** 2
        return self.__zoom(viewer, delta_x, delta_y, origin=(data_x, data_y))

    def kp_zoom_cursor_in(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta = self.settings['plot_zoom_rate'] ** -2
        delta_x = delta_y = delta
        return self.__zoom(viewer, delta_x, delta_y, origin=(data_x, data_y))

    def kp_zoom_cursor_in_x(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = self.settings['plot_zoom_rate'] ** -2
        delta_y = 1.0
        return self.__zoom(viewer, delta_x, delta_y, origin=(data_x, data_y))

    def kp_zoom_cursor_in_y(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        delta_x = 1.0
        delta_y = self.settings['plot_zoom_rate'] ** -2
        return self.__zoom(viewer, delta_x, delta_y, origin=(data_x, data_y))

    def kp_zoom_fit(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        viewer.zoom_fit(axis='xy')

    def kp_zoom_fit_x(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        viewer.zoom_fit(axis='x')

    def kp_zoom_fit_y(self, viewer, event, data_x, data_y):
        if not self.canzoom:
            return False
        event.accept()
        viewer.zoom_fit(axis='y')

    def kp_pan_left(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        pct = self.settings['plot_pan_pct']
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        x_rng = abs(x_hi - x_lo)
        x_delta, y_delta = -(x_rng * pct), 0.0
        viewer.pan_delta(x_delta, y_delta)

    def kp_pan_right(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        pct = self.settings['plot_pan_pct']
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        x_rng = abs(x_hi - x_lo)
        x_delta, y_delta = (x_rng * pct), 0.0
        viewer.pan_delta(x_delta, y_delta)

    def kp_pan_up(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        pct = self.settings['plot_pan_pct']
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        y_rng = abs(y_hi - y_lo)
        x_delta, y_delta = 0.0, (y_rng * pct)
        viewer.pan_delta(x_delta, y_delta)

    def kp_pan_down(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        pct = self.settings['plot_pan_pct']
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        y_rng = abs(y_hi - y_lo)
        x_delta, y_delta = 0.0, -(y_rng * pct)
        viewer.pan_delta(x_delta, y_delta)

    def kp_cut_x_lo(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        viewer.set_ranges(x_range=(data_x, x_hi))

    def kp_cut_x_hi(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        viewer.set_ranges(x_range=(x_lo, data_x))

    def kp_cut_y_lo(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        viewer.set_ranges(y_range=(data_y, y_hi))

    def kp_cut_y_hi(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        (x_lo, x_hi), (y_lo, y_hi) = viewer.get_ranges()
        viewer.set_ranges(y_range=(y_lo, data_y))
