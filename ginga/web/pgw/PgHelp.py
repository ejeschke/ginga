#
# PgHelp.py -- web application threading help routines.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import re
import random
import json
import time
import datetime
import binascii
from collections import namedtuple
from io import BytesIO

import tornado.web
import tornado.websocket
import tornado.template
from tornado.ioloop import IOLoop

from ginga.misc import Bunch, Callback
from ginga.util import io_rgb
from ginga.fonts import font_asst

font_regex = re.compile(r'^(.+)\s+(\d+)$')

default_interval = 10

ConfigEvent = namedtuple("ConfigEvent", ["type", "id", "width", "height"])
InputEvent = namedtuple("InputEvent", ["type", "id", "x", "y", "button",
                                       "delta", "dx", "dy", "alt_key", "ctrl_key",
                                       "meta_key", "shift_key", "key_code",
                                       "key_name"])
GestureEvent = namedtuple("GestureEvent", ["type", "id", "x", "y", "dx", "dy",
                                           "distance",
                                           "theta", "direction", "vx", "vy",
                                           "scale", "rotation", "isfirst",
                                           "isfinal"])
WidgetEvent = namedtuple("WidgetEvent", ["type", "id", "value"])
TimerEvent = namedtuple("TimerEvent", ["type", "id", "value"])


class ApplicationHandler(tornado.websocket.WebSocketHandler):

    def initialize(self, name, app):
        self.name = name
        self.app = app
        self.app.add_ws_handler(self)

        self.event_callbacks = {
            "activate": WidgetEvent,
            "setbounds": ConfigEvent,
            "mousedown": InputEvent,
            "mouseup": InputEvent,
            "mousemove": InputEvent,
            "mouseout": InputEvent,
            "mouseover": InputEvent,
            "mousewheel": InputEvent,
            "wheel": InputEvent,
            "click": InputEvent,
            "dblclick": InputEvent,
            "keydown": InputEvent,
            "keyup": InputEvent,
            "keypress": InputEvent,
            "resize": ConfigEvent,
            "focus": InputEvent,
            "focusout": InputEvent,
            "blur": InputEvent,
            "drop": InputEvent,
            #"paste": InputEvent,
            # These are all Hammer.js events
            "pinch": GestureEvent,
            "pinchstart": GestureEvent,
            "pinchend": GestureEvent,
            "rotate": GestureEvent,
            "rotatestart": GestureEvent,
            "rotateend": GestureEvent,
            "pan": GestureEvent,
            "panstart": GestureEvent,
            "panend": GestureEvent,
            "tap": GestureEvent,
            "swipe": GestureEvent,
        }

        #self.interval = 10
        interval = self.settings.get("timer_interval", default_interval)
        if self.name in self.settings:
            interval = self.settings[self.name].get("timer_interval", interval)
        self.interval = interval

        # randomize the first timeout so we don't get every timer
        # expiring at the same time
        interval = random.randint(1, self.interval)
        delta = datetime.timedelta(milliseconds=interval)
        self.timeout = IOLoop.current().add_timeout(delta, self.timer_tick)

    def add_event_type(self, msg_type, event_class):
        self.event_callbacks[msg_type] = event_class

    def on_open(self, *args, **kwdargs):
        self.set_nodelay(True)

    def on_close(self):
        IOLoop.current().remove_timeout(self.timeout)

    def on_message(self, raw_message):
        message = json.loads(raw_message)
        event_type = message.get("type")

        try:
            event_class = self.event_callbacks[event_type]

        except KeyError:
            # Attempt to turn this into a widget event
            event_class = WidgetEvent

        event = event_class(**message)
        self.app.widget_event(event)

    def do_operation(self, operation, **kwargs):
        message = dict(kwargs, operation=operation)
        raw_message = json.dumps(message)
        self.write_message(raw_message)

    def timer_tick(self):
        event = TimerEvent(type="timer", id=0, value=time.time())
        # TODO: should exceptions thrown from this be caught and ignored
        self.app.widget_event(event)

        delta = datetime.timedelta(milliseconds=self.interval)
        self.timeout = IOLoop.current().add_timeout(delta, self.timer_tick)


class WindowHandler(tornado.web.RequestHandler):

    def initialize(self, name, url, app):
        self.app = app
        self.logger = app.logger
        self.logger.info("windowhandler initialize")
        self.name = name
        self.url = url

    def make_index(self, wids):
        template = '''
<!doctype html>
<html>
<head>
    <title>%(title)s</title>
</head>
<body>
%(content)s
</body>
</html>'''
        content = ["<ul>"]
        for wid in wids:
            content.append('''<li><a href="%s?id=%s">Window %s</a></li>''' % (
                self.url, wid, wid))
        content.append("</ul>")

        return template % dict(title="Window index", content=''.join(content))

    def get(self):
        self.logger.info("windowhandler get")
        # Collect arguments
        wid = self.get_argument('id', None)

        # Get window with this id
        wids = self.app.get_wids()
        if wid in wids:
            window = self.app.get_window(wid)
            output = window.render()

        else:
            output = self.make_index(wids)

        self.write(output)


class Timer(Callback.Callbacks):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, duration=0.0, mplcanvas=None):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

        self._timer = mplcanvas.new_timer()
        self._timer.single_shot = True
        self._timer.add_callback(self._redirect_cb)

        for name in ('expired', 'canceled'):
            self.enable_callback(name)

    def start(self, duration=None):
        """Start the timer.  If `duration` is not None, it should
        specify the time to expiration in seconds.
        """
        if duration is None:
            duration = self.duration

        self.set(duration)

    def set(self, duration):

        self.stop()

        # pg timer set in milliseconds
        time_ms = int(duration * 1000.0)
        self._timer.interval = time_ms
        self._timer.start()

    def _redirect_cb(self):
        self.make_callback('expired')

    def stop(self):
        try:
            self._timer.stop()
        except Exception:
            pass

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        self.stop()
        self.make_callback('canceled')

    clear = cancel


def get_image_src_from_buffer(img_buf, imgtype='png'):
    if not isinstance(img_buf, bytes):
        img_buf = img_buf.encode('latin1')
    img_string = binascii.b2a_base64(img_buf)
    if isinstance(img_string, bytes):
        img_string = img_string.decode("utf-8")
    return ('data:image/%s;base64,' % imgtype) + img_string


def get_icon(iconpath, size=None, format='png'):
    image = io_rgb.PILimage.open(iconpath)
    if size is not None:
        wd, ht = size
    else:
        wd, ht = 24, 24
    image = image.resize((wd, ht))

    img_buf = BytesIO()
    image.save(img_buf, format=format)

    icon = get_image_src_from_buffer(img_buf.getvalue(), imgtype=format)
    return icon


def font_info(font_str):
    """Extract font information from a font string, such as supplied to the
    'font' argument to a widget.
    """
    vals = font_str.split(';')
    point_size, style, weight = 8, 'normal', 'normal'
    family = vals[0]
    if len(vals) > 1:
        style = vals[1]
    if len(vals) > 2:
        weight = vals[2]

    match = font_regex.match(family)
    if match:
        family, point_size = match.groups()
        point_size = int(point_size)

    return Bunch.Bunch(family=family, point_size=point_size,
                       style=style, weight=weight)


def get_font(font_family, point_size):
    font_family = font_asst.resolve_alias(font_family, font_family)
    font_str = '%s %d' % (font_family, point_size)
    return font_info(font_str)


def load_font(font_name, font_file):
    # TODO!
    ## raise ValueError("Loading fonts dynamically is an unimplemented"
    ##                  " feature for pg back end")
    return font_name

# END
