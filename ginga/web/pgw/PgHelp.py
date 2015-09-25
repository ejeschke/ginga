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


DEFAULT_INTERVAL = 10

ConfigEvent = namedtuple("ConfigEvent", ["type", "id", "width", "height"])
InputEvent = namedtuple("InputEvent", ["type", "id", "x", "y", "button",
                                       "delta", "alt_key", "ctrl_key",
                                       "meta_key", "shift_key", "key_code"])
GestureEvent = namedtuple("GestureEvent", ["type", "id", "x", "y", "dx", "dy",
                                           "distance",
                                           "theta", "direction", "vx", "vy",
                                           "scale", "rotation", "isfirst",
                                           "isfinal"])


class PantographHandler(tornado.websocket.WebSocketHandler):

    def initialize(self, name, ioloop=None):
        self.name = name
        if ioloop is None:
            ioloop = IOLoop.current()
        self.my_ioloop = ioloop

        # self.settings defined in subclass
        print(self.settings)
        interval = self.settings.get("timer_interval", DEFAULT_INTERVAL)
        if self.name in self.settings:
            interval = self.settings[self.name].get("timer_interval", interval)
        self.interval = interval

        self.event_callbacks = {
            "setbounds": (self.on_canvas_init, ConfigEvent),
            "mousedown": (self.on_mouse_down, InputEvent),
            "mouseup": (self.on_mouse_up, InputEvent),
            "mousemove": (self.on_mouse_move, InputEvent),
            "mouseout": (self.on_mouse_out, InputEvent),
            "mouseover": (self.on_mouse_over, InputEvent),
            "mousewheel": (self.on_wheel, InputEvent),
            "DOMMouseScroll": (self.on_wheel, InputEvent),
            "wheel": (self.on_wheel, InputEvent),
            "click": (self.on_click, InputEvent),
            "dblclick": (self.on_dbl_click, InputEvent),
            "keydown": (self.on_key_down, InputEvent),
            "keyup": (self.on_key_up, InputEvent),
            "keypress": (self.on_key_press, InputEvent),
            "resize": (self.on_resize, InputEvent),
            "focus": (self.on_focus, InputEvent),
            "focusout": (self.on_blur, InputEvent),
            "blur": (self.on_blur, InputEvent),
            "drop": (self.on_drop, InputEvent),
            #"paste": (self.on_paste, InputEvent),
            "pinch": (self.on_pinch, GestureEvent),
            "rotate": (self.on_rotate, GestureEvent),
            "tap": (self.on_tap, GestureEvent),
            "pan": (self.on_pan, GestureEvent),
            "swipe": (self.on_swipe, GestureEvent),
            }

    def on_open(self, *args, **kwdargs):
        self.set_nodelay(True)

    def on_close(self):
        self.my_ioloop.remove_timeout(self.timeout)

    def on_message(self, raw_message):
        message = json.loads(raw_message)
        event_type = message.get("type")

        try:
            method, EventClass = self.event_callbacks[event_type]

        except KeyError:
            print("I don't know how to process '%s' events!" % (
                event_type))
            return

        method(EventClass(**message))

    def do_operation(self, operation, **kwargs):
        message = dict(kwargs, operation=operation)
        raw_message = json.dumps(message)
        self.write_message(raw_message)

    def draw(self, shape_type, **kwargs):
        shape = dict(kwargs, type=shape_type)
        self.do_operation("draw_canvas", shape=shape)

    def draw_rect(self, x, y, width, height, color = "#000", **extra):
        self.draw("rect", x=x, y=y, width=width, height=height,
                          lineColor=color, **extra)

    def fill_rect(self, x, y, width, height, color = "#000", **extra):
        self.draw("rect", x=x, y=y, width=width, height=height,
                          fillColor=color, **extra)

    def clear_rect(self, x, y, width, height, **extra):
        self.draw("clear", x=x, y=y, width=width, height=height, **extra)

    def draw_oval(self, x, y, width, height, color = "#000", **extra):
        self.draw("oval", x=x, y=y, width=width, height=height,
                          lineColor=color, **extra)

    def fill_oval(self, x, y, width, height, color = "#000", **extra):
        self.draw("oval", x=x, y=y, width=width, height=height,
                          fillColor=color, **extra)

    def draw_circle(self, x, y, radius, color = "#000", **extra):
        self.draw("circle", x=x, y=y, radius=radius,
                            lineColor=color, **extra)

    def fill_circle(self, x, y, radius, color = "#000", **extra):
        self.draw("circle", x=x, y=y, radius=radius,
                           fillColor=color, **extra)

    def draw_line(self, startX, startY, endX, endY, color = "#000", **extra):
        self.draw("line", startX=startX, startY=startY,
                          endX=endX, endY=endY, color=color, **extra)

    def fill_polygon(self, points, color = "#000", **extra):
        self.draw("polygon", points=points, fillColor=color, **extra)

    def draw_polygon(self, points, color = "#000", **extra):
        self.draw("polygon", points=points, lineColor=color, **extra)

    def draw_image(self, img_name, x, y, width=None, height=None,
                   buffer=None, **extra):
        if not (buffer is None):
            img_string = binascii.b2a_base64(buffer)
            if isinstance(img_string, bytes):
                img_string = img_string.decode("utf-8")
                #print("decoded bytes to utf-8")
            img_src = 'data:image/png;base64,' + img_string

        else:
            app_path = os.path.join("./images", img_name)
            handler_path = os.path.join("./images", self.name, img_name)

            if os.path.isfile(handler_path):
                img_src = os.path.join("/img", self.name, img_name)
            elif os.path.isfile(app_path):
                img_src = os.path.join("/img", img_name)
            else:
                raise FileNotFoundError("Could not find " + img_name)

        self.draw("image", src=img_src, x=x, y=y,
                           width=width, height=height, **extra)


    def timer_tick(self):
        self.update()
        self.do_operation("refresh_canvas")
        delta = datetime.timedelta(milliseconds = self.interval)
        self.timeout = self.my_ioloop.add_timeout(delta, self.timer_tick)

    def setup(self):
        pass

    def update(self):
        pass

    def on_canvas_init(self, event):
        self.width = event.width
        self.height = event.height
        # randomize the first timeout so we don't get every timer
        # expiring at the same time
        interval = random.randint(1, self.interval)
        delta = datetime.timedelta(milliseconds = interval)
        self.timeout = self.my_ioloop.add_timeout(delta, self.timer_tick)

        self.setup()
        self.do_operation("refresh_canvas")

    def on_mouse_down(self, event):
        pass

    def on_mouse_up(self, event):
        pass

    def on_mouse_move(self, event):
        pass

    def on_mouse_out(self, event):
        pass

    def on_mouse_over(self, event):
        pass

    def on_wheel(self, event):
        pass

    def on_click(self, event):
        pass

    def on_dbl_click(self, event):
        pass

    def on_key_down(self, event):
        pass

    def on_key_up(self, event):
        pass

    def on_key_press(self, event):
        pass

    def on_drop(self, event):
        pass

    def on_resize(self, event):
        pass

    def on_focus(self, event):
        pass

    def on_blur(self, event):
        pass

    def on_pinch(self, event):
        pass

    def on_rotate(self, event):
        pass

    def on_pan(self, event):
        pass

    def on_swipe(self, event):
        pass

    def on_tap(self, event):
        pass


WidgetEvent = namedtuple("WidgetEvent", ["type", "id", "value"])
TimerEvent = namedtuple("TimerEvent", ["type", "id", "value"])

class ApplicationHandler(tornado.websocket.WebSocketHandler):

    def initialize(self, name, app):
        #print(("initialize", name, app))
        self.name = name
        self.app = app
        self.app.ws_handler = self

        self.event_callbacks = {
            "activate": WidgetEvent,
            "setbounds": ConfigEvent,
            "mousedown": InputEvent,
            "mouseup": InputEvent,
            "mousemove": InputEvent,
            "mouseout": InputEvent,
            "mouseover": InputEvent,
            "mousewheel": InputEvent,
            "DOMMouseScroll": InputEvent,
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
            "pinch": GestureEvent,
            "rotate": GestureEvent,
            "tap": GestureEvent,
            "pan": GestureEvent,
            "swipe": GestureEvent,
            }

        #self.interval = 10
        interval = self.settings.get("timer_interval", DEFAULT_INTERVAL)
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

    def on_canvas_init(self, event):
        self.width = event.width
        self.height = event.height

        self.setup()
        self.do_operation("refresh_canvas")

    def update(self):
        self.do_operation("refresh_canvas")
