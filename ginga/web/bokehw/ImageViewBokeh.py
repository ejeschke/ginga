#
# ImageViewBokeh.py -- classes implementing a ginga viewer backend for Bokeh
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import time

import numpy as np

# Bokeh imports
from bokeh.plotting import curdoc
from bokeh.models import ColumnDataSource
from bokeh.io import push_notebook
from bokeh import events

from ginga import ImageView
from ginga.canvas import render
from ginga import Mixins, Bindings


class ImageViewBokehError(ImageView.ImageViewError):
    pass


class ImageViewBokeh(ImageView.ImageViewBase):
    """
    This version does all the graphical overlays on the server side.
    """

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        self.t_.set_defaults(renderer='cairo')

        # Our Bokeh plot
        self.figure = None
        # Holds the image on the plot
        self.bkimage = None
        self.d_src = None
        self._push_handle = None

        # NOTE: Bokeh manages it's Y coordinates by default with
        # the origin at the bottom (see base class)
        self.origin_upper = True
        self._invert_y = True

        # override, until we can get access to a timer
        self.defer_redraw = True
        self.rgb_order = 'RGBA'

        # For timing events
        self._msg_timer = 0
        self._defer_timer = 0

        self.renderer = None
        # Pick a renderer that can work with us
        renderers = ['cairo', 'agg', 'pil', 'opencv']
        preferred = self.t_['renderer']
        if preferred in renderers:
            renderers.remove(preferred)
        self.possible_renderers = [preferred] + renderers
        self.choose_best_renderer()

    def set_figure(self, figure, handle=None):
        """Call this with the Bokeh figure object."""
        self.figure = figure
        self.bkimage = None
        self._push_handle = handle

        self._setup_handlers(figure)

        wd = figure.plot_width
        ht = figure.plot_height

        self.configure_window(wd, ht)

        doc = curdoc()
        doc.add_periodic_callback(self.timer_cb, 20)
        self.logger.info("figure set")

    def get_figure(self):
        return self.figure

    def choose_renderer(self, name):
        klass = render.get_render_class(name)
        self.renderer = klass(self)

        #self.renderer.resize((wd, ht))

    def choose_best_renderer(self):
        for name in self.possible_renderers:
            try:
                self.choose_renderer(name)
                self.logger.info("best renderer available is '{}'".format(name))
                return
            except Exception as e:
                # uncomment to troubleshoot
                self.logger.info("can't choose renderer '{}': {}".format(name, e),
                                 exc_info=True)
                continue

        raise ImageViewBokehError("No valid renderers available: {}".format(str(self.possible_renderers)))

    def update_widget(self):
        if self.figure is None:
            return

        wd, ht = self.get_window_size()

        # Get surface as a numpy array
        data = self.renderer.get_surface_as_array(order='RGBA')

        # Casting as a 32-bit uint array type hopefully to get more
        # efficient JSON encoding en route to the browser
        data = data.view(dtype=np.uint32).reshape((ht, wd))

        data = np.flipud(data)

        dst_x = dst_y = 0

        # Create an Image_RGBA object in the plot
        if self.bkimage is None:
            self.d_src = ColumnDataSource({'image': [data]})
            self.bkimage = self.figure.image_rgba(image='image',
                                                  x=dst_x, y=dst_y,
                                                  dw=wd, dh=ht,
                                                  source=self.d_src)
            #self._setup_handlers(self.d_src)

        else:
            # note: get the data source (a ColumnDataSource) and update
            # the values
            self.logger.info("Updating image")
            update = dict(image=[data], x=[dst_x], y=[dst_y],
                          dw=[wd], dh=[ht])
            self.d_src.data = update

            if self._push_handle is not None:
                self.logger.info("pushing to notebook...")
                #self.d_src.push_notebook(self._push_handle)
                push_notebook(self._push_handle)
            self.logger.info("Image updated")

    def reschedule_redraw(self, time_sec):
        self._defer_timer = time.time() + time_sec

    def configure_window(self, width, height):
        self.configure_surface(width, height)

    def _setup_handlers(self, source):
        pass

    def set_cursor(self, cursor):
        pass

    def timer_cb(self, *args):
        self.logger.debug("timer")
        cur_time = time.time()
        if (self._defer_timer > 0) and (cur_time > self._defer_timer):
            self._defer_timer = 0
            self.logger.info("redrawing")
            self.delayed_redraw()

        if (self._msg_timer > 0) and (cur_time > self._msg_timer):
            self._msg_timer = 0
            self.set_onscreen_message(None)

    def onscreen_message(self, text, delay=None):
        if text is not None:
            self.set_onscreen_message(text)
        if delay:
            self._msg_timer = time.time() + delay

    def onscreen_message_off(self):
        self.set_onscreen_message(None)


class ImageViewEvent(ImageViewBokeh):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewBokeh.__init__(self, logger=logger, rgbmap=rgbmap,
                                settings=settings)

        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0

        # @$%&^(_)*&^ gnome!!
        self._keytbl = {
            'shift': 'shift_l',
            'control': 'control_l',
            'alt': 'alt_l',
            'win': 'super_l',
            '`': 'backquote',
            '"': 'doublequote',
            "'": 'singlequote',
            '\\': 'backslash',
            ' ': 'space',
            # NOTE: not working
            'escape': 'escape',
            'enter': 'return',
            # NOTE: not working
            'tab': 'tab',
            # NOTE: all Fn keys not working
            'f1': 'f1',
            'f2': 'f2',
            'f3': 'f3',
            'f4': 'f4',
            'f5': 'f5',
            'f6': 'f6',
            'f7': 'f7',
            'f8': 'f8',
            'f9': 'f9',
            'f10': 'f10',
            'f11': 'f11',
            'f12': 'f12',
        }

        # Define cursors for pick and pan
        #hand = openHandCursor()
        hand = 0
        self.define_cursor('pan', hand)
        #cross = thinCrossCursor('aquamarine')
        cross = 1
        self.define_cursor('pick', cross)

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'pan', 'press', 'tap',
                     ):
            self.enable_callback(name)

    def set_figure(self, figure, handle=None):
        super(ImageViewEvent, self).set_figure(figure, handle=handle)

    def _setup_handlers(self, source):
        fig = self.figure
        # TODO: lots of events that are supported by other backends!
        ## #connect("map_event", self.map_event)
        fig.on_event(events.MouseEnter, self.enter_notify_event)
        fig.on_event(events.MouseLeave, self.leave_notify_event)
        fig.on_event(events.MouseMove, self.motion_notify_event)
        ## #connect("focus_in_event", self.focus_event, True)
        ## #connect("focus_out_event", self.focus_event, False)
        ## connect("button_press_event", self.button_press_event)
        ## connect("button_release_event", self.button_release_event)
        ## connect("key_press_event", self.key_press_event)
        ## connect("key_release_event", self.key_release_event)
        fig.on_event(events.MouseWheel, self.scroll_event)
        fig.on_event(events.Tap, self.tap_event)
        #fig.on_event(events.Press, self.press_down_event)
        #fig.on_event(events.PressUp, self.press_up_event)
        # NOTE: currently using these for button press events
        fig.on_event(events.PanStart, self.pan_start_event)
        fig.on_event(events.Pan, self.pan_event)
        fig.on_event(events.PanEnd, self.pan_end_event)
        #fig.on_event(events.Pinch, self.pinch_event)

        self.logger.info("setup event handlers")

    def transkey(self, keyname):
        self.logger.debug("bokeh keyname='%s'" % (keyname))
        if keyname is None:
            return keyname
        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def get_key_table(self):
        return self._keytbl

    def focus_event(self, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, event):
        self.logger.info("entering widget...")
        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            self.focus_event(event, True)
        return self.make_callback('enter')

    def leave_notify_event(self, event):
        self.logger.info("leaving widget...")
        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            self.focus_event(event, False)
        return self.make_callback('leave')

    def key_press_event(self, event):
        keyname = event.key
        keyname = self.transkey(keyname)
        if keyname is not None:
            self.logger.debug("key press event, key=%s" % (keyname))
            return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_release_event(self, event):
        keyname = event.key
        keyname = self.transkey(keyname)
        if keyname is not None:
            self.logger.debug("key release event, key=%s" % (keyname))
            return self.make_ui_callback_viewer(self, 'key-release', keyname)

    def motion_notify_event(self, event):
        button = 0
        x, y = int(event.sx), int(event.sy)
        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        self.last_win_x, self.last_win_y = x, y
        data_x, data_y = self.check_cursor_location()

        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def scroll_event(self, event):
        x, y = int(event.x), int(event.y)

        # bokeh only gives us the number of steps of the scroll,
        # positive for up and negative for down.  No horizontal scrolling.
        direction = None
        if event.delta > 0:
            direction = 0.0
        elif event.delta < 0:
            direction = 180.0

        #amount = abs(event.delta) * 15.0
        amount = int(abs(event.delta))

        self.logger.info("scroll deg=%f direction=%f" % (
            amount, direction))

        self.last_win_x, self.last_win_y = x, y
        data_x, data_y = self.check_cursor_location()

        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback_viewer(self, 'scroll', direction, amount,
                                            data_x, data_y)

    def pinch_event(self, event):
        # no rotation (seemingly) in the Bokeh pinch event
        rot = 0.0
        scale = event.scale
        self.logger.debug("pinch gesture rot=%f scale=%f" % (rot, scale))

        return self.make_ui_callback_viewer(self, 'pinch', 'move', rot, scale)

    def pan_start_event(self, event):
        # event attrs: x, y, sx, sy
        x, y = int(event.sx), int(event.sy)
        button = 0x1
        self.last_win_x, self.last_win_y = x, y
        self.logger.debug("button down event at %dx%d, button=%x" % (x, y, button))
        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-press', button,
                                            data_x, data_y)

    def pan_event(self, event):
        # event attrs: x, y, sx, sy, delta_x, delta_y
        x, y = int(event.sx), int(event.sy)
        button = 0x1
        self.last_win_x, self.last_win_y = x, y

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def pan_end_event(self, event):
        # event attrs: x, y, sx, sy
        x, y = int(event.sx), int(event.sy)
        button = 0x1
        self.last_win_x, self.last_win_y = x, y

        data_x, data_y = self.check_cursor_location()

        self.logger.debug("button up event at %dx%d, button=%x" % (x, y, button))
        return self.make_ui_callback_viewer(self, 'button-release', button,
                                            data_x, data_y)

    def tap_event(self, event):
        x, y = int(event.x), int(event.y)
        button = 0
        self.logger.debug("tap event at %dx%d, button=%x" % (x, y, button))

        self.last_win_x, self.last_win_y = x, y
        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback('button-press', button, data_x, data_y)

    def press_down_event(self, event):
        x, y = int(event.x), int(event.y)
        self.logger.debug("press down event at %dx%d" % (x, y))

    def press_up_event(self, event):
        x, y = int(event.x), int(event.y)
        self.logger.debug("press up event at %dx%d" % (x, y))


class ImageViewZoom(Mixins.UIMixin, ImageViewEvent):

    # class variables for binding map and bindings can be set
    bindmapClass = Bindings.BindingMapper
    bindingsClass = Bindings.ImageViewBindings

    @classmethod
    def set_bindingsClass(cls, klass):
        cls.bindingsClass = klass

    @classmethod
    def set_bindmapClass(cls, klass):
        cls.bindmapClass = klass

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, rgbmap=rgbmap,
                                settings=settings)
        Mixins.UIMixin.__init__(self)

        self.ui_set_active(True, viewer=self)

        if bindmap is None:
            bindmap = ImageViewZoom.bindmapClass(self.logger)
        self.bindmap = bindmap
        bindmap.register_for_events(self)

        if bindings is None:
            bindings = ImageViewZoom.bindingsClass(self.logger)
        self.set_bindings(bindings)

    def get_bindmap(self):
        return self.bindmap

    def get_bindings(self):
        return self.bindings

    def set_bindings(self, bindings):
        self.bindings = bindings
        bindings.set_bindings(self)


class CanvasView(ImageViewZoom):

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger, settings=settings,
                               rgbmap=rgbmap,
                               bindmap=bindmap, bindings=bindings)

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas
