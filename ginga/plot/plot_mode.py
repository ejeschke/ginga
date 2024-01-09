#
# plot_mode.py -- mode for manipulating plots
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Plot Mode enables bindings for manipulating plots.

Enter the mode by
-----------------
Mode is set by the PlotAide

Exit the mode by
----------------
* Esc (but this is not recommended)

Default bindings in mode
------------------------
* x : toggle autoaxis X between ON and OFF
* y : toggle autoaxis Y between ON and OFF
* v : toggle autoaxis Y between VIS and OFF
* p : toggle autoaxis X between PAN and OFF
* scroll : zoom (scale) the plot in X
* Ctrl + scroll : zoom (scale) the plot in Y

"""
from ginga.modes.mode_base import Mode


class PlotMode(Mode):

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        # this get set to the associated PlotAide object
        self.aide = None

        self.actions = dict(
            dmod_plot=['__p', None, None],

            # NOTE: these only here to generate events. The events are
            # handled by the PlotAide object
            kp_plot_autoaxis_x=['plot+x'],
            kp_plot_autoaxis_y=['plot+y'],
            kp_plot_visible_y=['plot+v'],
            kp_plot_position_x=['plot+p'],

            sc_plot_zoom=['plot+scroll', 'plot+ctrl+scroll'],
            sc_plot_zoom_pan=['plot+pan', 'plot+ctrl+pan'])

    def __str__(self):
        return 'plot'

    def set_aide_ref(self, aide):
        self.aide = aide

    def assert_has_aide(self):
        if self.aide is None:
            raise ValueError("This viewer does not have a plot aide registered")

    def start(self):
        #self.viewer.switch_cursor('plot')
        pass

    def stop(self):
        #self.viewer.switch_cursor('pick')
        self.onscreen_message(None)

    def kp_plot_autoaxis_y(self, *args):
        """Callback invoked when the user presses 'y' in the viewer window.
        """
        self.assert_has_aide()
        autoaxis_y = self.aide.settings['autoaxis_y'] == 'on'
        self.aide.settings['autoaxis_y'] = 'off' if autoaxis_y else 'on'

    def kp_plot_visible_y(self, *args):
        """Callback invoked when the user presses 'v' in the viewer window.
        """
        self.assert_has_aide()
        autoaxis_y = self.aide.settings['autoaxis_y'] == 'vis'
        self.aide.settings['autoaxis_y'] = 'off' if autoaxis_y else 'vis'

    def kp_plot_autoaxis_x(self, *args):
        """Callback invoked when the user presses 'x' in the viewer window.
        """
        self.assert_has_aide()
        autoaxis_x = self.aide.settings['autoaxis_x'] == 'on'
        self.aide.settings['autoaxis_x'] = 'off' if autoaxis_x else 'on'

    def kp_plot_position_x(self, *args):
        """Callback invoked when the user presses 'p' in the viewer window.
        """
        self.assert_has_aide()
        autopan_x = self.aide.settings['autoaxis_x'] == 'pan'
        self.aide.settings['autoaxis_x'] = 'off' if autopan_x else 'pan'

    def sc_plot_zoom(self, viewer, event):
        """Callback called when the user scrolls in the viewer window.
        From this we generate a 'plot-zoom-x' or a 'plot-zoom-y' event.
        """
        self.assert_has_aide()
        bd = viewer.get_bindings()
        direction = bd.get_direction(event.direction)
        zoom_direction = 'in' if direction == 'up' else 'out'
        # default is to zoom the X axis unless CTRL is held down
        zoom_axis = 'y' if 'ctrl' in event.modifiers else 'x'
        event = 'plot-zoom-{}'.format(zoom_axis)
        # turn this into a zoom event for any callbacks registered for it
        self.aide.make_callback(event, zoom_direction)
        return True

    def scroll_plot_zoom_pan(self, viewer, event):
        """Callback called when the user pans in the viewer window
        (i.e. touchpad pan event); we turn this into a zoom event.
        """
        event = self._pa_synth_scroll_event(event)
        if event.state != 'move':
            return False
        self.scroll_plot_zoom(viewer, event)
        return True
