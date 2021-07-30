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
        interval = random.randint(1, self.interval)  # nosec
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

    def __init__(self, duration=0.0, app=None):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        if app is None:
            raise ValueError("please provide `app` argument")
        self.app = app
        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()
        self.deadline = None
        self.start_time = 0.0
        self.end_time = 0.0

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

        self.start_time = time.time()
        # this attribute is used externally to manage the timer
        self.deadline = self.start_time + duration
        self.end_time = self.deadline
        self.app.add_timer(self)

    def is_set(self):
        return self.deadline is not None

    def cond_set(self, time_sec):
        if not self.is_set():
            # TODO: probably a race condition here
            self.set(time_sec)

    def elapsed_time(self):
        return time.time() - self.start_time

    def time_left(self):
        return max(0.0, self.time_end - time.time())

    def get_deadline(self):
        return self.time_end

    def expire(self):
        """This method is called externally to expire the timer."""
        self.stop()
        self.make_callback('expired')

    def stop(self):
        self.deadline = None
        self.app.remove_timer(self)

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


def get_native_image(imgpath, format='png'):
    print('image path', imgpath)
    image = io_rgb.PILimage.open(imgpath)

    img_buf = BytesIO()
    image.save(img_buf, format=format)

    return img_buf.getvalue()


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
