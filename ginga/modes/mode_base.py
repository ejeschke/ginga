import math

from ginga.Bindings import ScrollEvent


class Mode:

    tag = '_$mode_indicator'

    def __init__(self, viewer, settings=None):
        super().__init__()

        self.viewer = viewer
        self.logger = viewer.get_logger()
        if settings is None:
            #settings = Settings.SettingGroup()
            settings = viewer.get_settings()
        self.settings = settings
        self.actions = dict()

        self._start_x = None
        self._start_y = None

    def get_settings(self):
        if self.settings is not None:
            return self.settings
        return self.viewer.get_settings()

    def start(self):
        raise NotImplementedError("subclass should implement this method")

    def stop(self):
        raise NotImplementedError("subclass should implement this method")

    def onscreen_message(self, msg, delay=None):
        #self.viewer.onscreen_message(msg, delay=delay)
        indic = self.get_mode_line()
        if msg is None:
            msg = ''
        indic.set_text(msg)
        self.viewer.redraw(whence=3)

    def get_mode_line(self):
        canvas = self.viewer.get_private_canvas()
        indic = canvas.get_object_by_tag(self.tag)
        return indic

    def get_win_xy(self, viewer):
        x, y = viewer.get_last_win_xy()

        if not viewer.window_has_origin_upper():
            wd, ht = viewer.get_window_size()
            y = ht - y

        return x, y

    def get_direction(self, direction, rev=False):
        """
        Translate a direction in compass degrees into 'up' or 'down'.
        """
        if (direction < 90.0) or (direction >= 270.0):
            if not rev:
                return 'up'
            else:
                return 'down'
        elif (90.0 <= direction < 270.0):
            if not rev:
                return 'down'
            else:
                return 'up'
        else:
            return 'none'

    def _pa_synth_scroll_event(self, event):

        dx, dy = float(event.delta_x), float(event.delta_y)
        amount = math.sqrt(dx ** 2.0 + dy ** 2.0)
        if dx == 0.0:
            if dy > 0:
                direction = 0.0
            else:
                direction = 180.0
        else:
            direction = math.atan(dy / dx)

        self.logger.debug("scroll amount=%f direction=%f" % (
            amount, direction))

        # synthesize a scroll event
        event = ScrollEvent(button=event.button, state=event.state,
                            mode=event.mode, modifiers=event.modifiers,
                            direction=direction, amount=amount,
                            data_x=event.data_x, data_y=event.data_y,
                            viewer=event.viewer)
        return event
