from ginga.web.pgw.ImageViewPg import CanvasView
from ginga.web.pgw import Widgets
from ginga.misc import Bunch

class GingaViewer(Widgets.Canvas):
    """
    This class implements the server-side backend of the surface for a
    web-based Ginga viewer.  It uses a web socket to connect to an HTML5
    canvas with javascript callbacks in a web browser on the client.

    The viewer is created separately on the backend and connects to this
    surface via the set_viewer() method.
    """

    def __init__(self, viewer=None, width=600, height=600):
        super(GingaViewer, self).__init__(width=600, height=600)

        if viewer is None:
            viewer = CanvasView(logger)
        self.logger = viewer.logger

        self._configured = False

        self._pinching = False
        self._panning = False
        self._rotating = False

        self.set_viewer(viewer)

    def set_viewer(self, viewer):
        self.logger.debug("set_viewer called")
        self.viewer = viewer
        #self.logger = viewer.get_logger()

        self._dispatch_event_table = {
            "activate": self.ignore_event,
            "setbounds": self.map_event_cb,
            "mousedown": viewer.button_press_event,
            "mouseup": viewer.button_release_event,
            "mousemove": viewer.motion_notify_event,
            "mouseout": viewer.leave_notify_event,
            "mouseover": viewer.enter_notify_event,
            "mousewheel": viewer.scroll_event,
            "wheel": viewer.scroll_event,
            "click": self.ignore_event,
            "dblclick": self.ignore_event,
            "keydown": viewer.key_down_event,
            "keyup": viewer.key_up_event,
            "keypress": viewer.key_press_event,
            "resize": viewer.resize_event,
            "focus": lambda event: viewer.focus_event(event, True),
            "focusout": lambda event: viewer.focus_event(event, False),
            "blur": lambda event: viewer.focus_event(event, False),
            "drop": viewer.drop_event,
            "paste": self.ignore_event,
            "pinch": viewer.pinch_event,
            "rotate": viewer.rotate_event,
            "tap": viewer.tap_event,
            "pan": viewer.pan_event,
            "swipe": viewer.swipe_event,
            }

        self.add_timer('refresh', self.refresh_cb)
        self.add_timer('redraw', self.viewer.delayed_redraw)
        self.add_timer('msg', self.viewer.clear_onscreen_message)

        self.viewer.set_widget(self)

    def get_viewer(self):
        return self.viewer

    def ignore_event(self, event):
        pass

    def map_event_cb(self, event):
        self.viewer.map_event(event)
        self.reset_timer('refresh', 0.010)

    def refresh_cb(self, *args):
        app = self.get_app()
        app.do_operation('refresh_canvas', id=self.id)
        self.reset_timer('refresh', 0.010)

    def do_update(self, buf):
        self.clear_rect(0, 0, self.width, self.height)

        self.logger.debug("drawing image")
        self.draw_image(buf, 0, 0, self.width, self.height)
        self.logger.debug("drew image")

    def _cb_redirect(self, event):
        method = self._dispatch_event_table[event.type]
        try:
            method(event)

        except Exception as e:
            self.logger.error("error redirecting '%s' event: " % (
                event.type, str(e)))
            # TODO: dump traceback to debug log


#END
