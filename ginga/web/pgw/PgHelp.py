#
# PgHelp.py -- web application threading help routines.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import tornado.web
import tornado.websocket
import tornado.template
from tornado.ioloop import IOLoop

import random
import json
import os, time
import datetime
import binascii
from collections import namedtuple

from ginga.misc import Bunch

default_interval = 10

ConfigEvent = namedtuple("ConfigEvent", ["type", "id", "width", "height"])
InputEvent = namedtuple("InputEvent", ["type", "id", "x", "y", "button",
                                       "delta", "alt_key", "ctrl_key",
                                       "meta_key", "shift_key", "key_code"])
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
            "resize": InputEvent,
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
            print("I don't know how to process '%s' events!" % (
                event_type))
            return

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

        delta = datetime.timedelta(milliseconds = self.interval)
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
