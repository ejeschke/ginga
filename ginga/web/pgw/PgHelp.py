import tornado.web
import tornado.websocket
import tornado.template
from tornado.ioloop import IOLoop

import random
import json
import os
import datetime
import binascii
from collections import namedtuple

## from . import templates

## LOADER = tornado.template.Loader(os.path.dirname(templates.__file__))

## class MainPageHandler(tornado.web.RequestHandler):
##     def initialize(self, name, url):
##         self.name = name
##         self.url = url
##     def get(self):
##         t = LOADER.load("index.html")

##         width = self.settings.get("canvasWidth", "fullWidth")
##         height = self.settings.get("canvasHeight", "fullHeight")

##         if self.name in self.settings:
##             width = self.settings[self.name].get("canvasWidth", width)
##             height = self.settings[self.name].get("canvasHeight", height)

##         ws_url = os.path.join(self.url, "socket")

##         self.write(t.generate(
##             title = self.name, url = self.url, ws_url = ws_url,
##             width = width, height = height))

DEFAULT_INTERVAL = 10

InputEvent = namedtuple("InputEvent", ["type", "x", "y", "button", "delta",
                                       "alt_key", "ctrl_key", "meta_key",
                                       "shift_key", "key_code"])
GestureEvent = namedtuple("GestureEvent", ["type", "x", "y", "dx", "dy",
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

        interval = self.settings.get("timer_interval", DEFAULT_INTERVAL)
        if self.name in self.settings:
            interval = self.settings[self.name].get("timer_interval", interval)
        self.interval = interval

        self.event_callbacks = {
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
            "blur": (self.on_blur, InputEvent),
            "drop": (self.on_drop, InputEvent),
            #"paste": (self.on_paste, InputEvent),
            "pinch": (self.on_pinch, GestureEvent),
            "rotate": (self.on_rotate, GestureEvent),
            "tap": (self.on_tap, GestureEvent),
            "pan": (self.on_pan, GestureEvent),
            "swipe": (self.on_swipe, GestureEvent),
            }

    def on_canvas_init(self, message):
        self.width = message["width"]
        self.height = message["height"]
        # randomize the first timeout so we don't get every timer
        # expiring at the same time
        interval = random.randint(1, self.interval)
        delta = datetime.timedelta(milliseconds = interval)
        self.timeout = self.my_ioloop.add_timeout(delta, self.timer_tick)

        self.setup()
        self.do_operation("refresh")

    def on_open(self, *args, **kwdargs):
        self.set_nodelay(True)

    def on_close(self):
        self.my_ioloop.remove_timeout(self.timeout)

    def on_message(self, raw_message):
        message = json.loads(raw_message)
        event_type = message.get("type")

        if event_type == "setbounds":
            self.on_canvas_init(message)
        else:
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
        self.do_operation("draw", shape=shape)

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
        if buffer is not None:
            imgString = binascii.b2a_base64(buffer)
            if isinstance(imgString, bytes):
                imgString = imgString.decode("utf-8")
            img_src = 'data:image/png;base64,' + imgString

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
        self.do_operation("refresh")
        delta = datetime.timedelta(milliseconds = self.interval)
        self.timeout = self.my_ioloop.add_timeout(delta, self.timer_tick)

    def setup(self):
        pass

    def update(self):
        pass

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
