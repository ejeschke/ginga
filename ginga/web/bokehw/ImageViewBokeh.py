#
# ImageViewBokeh.py -- classes implementing a ginga viewer backend for Bokeh
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import time
from io import BytesIO

import numpy as np

# Bokeh imports
from bokeh.plotting import curdoc
#from bokeh.models import BoxSelectTool, TapTool
#from bokeh.models import PanTool
from bokeh.models import ColumnDataSource
#from bokeh.client import push_session
from bokeh.io import push_notebook
# from bokeh.events import (MouseEnter, MouseLeave, MouseMove, MouseWheel,
#                           Pan, PanEnd, PanStart, Pinch, PinchEnd, PinchStart,
#                           Press, Tap, DoubleTap, SelectionGeometry)
from bokeh.events import (MouseEnter, MouseLeave, MouseMove, MouseWheel,
                          Tap)

from ginga import ImageView
from ginga import Mixins, Bindings
from ginga.web.bokehw.CanvasRenderBokeh import CanvasRenderer

# TODO: is this the right place for this call?
#session = push_session(curdoc())

try:
    # See if we have aggdraw module--best choice
    from ginga.aggw.ImageViewAgg import ImageViewAgg as ImageViewSS
    from ginga.aqqw.ImageViewAgg import ImageViewAggError as ImageViewError

except ImportError:
    try:
        # No, hmm..ok, see if we have opencv module...
        from ginga.cvw.ImageViewCv import ImageViewCv as ImageViewSS
        from ginga.cvw.ImageViewCv import ImageViewCvError as ImageViewError

    except ImportError:
        try:
            # No dice. How about the PIL module?
            from ginga.pilw.ImageViewPil import ImageViewPil as ImageViewSS
            from ginga.pilw.ImageViewPil import ImageViewPilError as ImageViewError

        except ImportError:
            # Fall back to mock--there will be no graphic overlays
            from ginga.mockw.ImageViewMock import ImageViewMock as ImageViewSS
            from ginga.mockw.ImageViewMock import ImageViewMockError as ImageViewError


## class ImageViewBokehError(ImageView.ImageViewError):
##     pass
class ImageViewBokehError(ImageViewError):
    pass


class ImageViewBokeh(ImageViewSS):
    """
    This version does all the graphical overlays on the server side.
    """

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewSS.__init__(self, logger=logger,
                             rgbmap=rgbmap,
                             settings=settings)

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

        # For timing events
        self._msg_timer = 0
        self._defer_timer = 0

    def set_figure(self, figure, handle=None):
        """Call this with the Bokeh figure object."""
        self.figure = figure
        self.bkimage = None
        self._push_handle = handle

        wd = figure.plot_width
        ht = figure.plot_height

        self.configure_window(wd, ht)

        doc = curdoc()
        #self.logger.info(str(dir(doc)))
        doc.add_periodic_callback(self.timer_cb, 50)
        self.logger.info("figure set")

    def get_figure(self):
        return self.figure

    def update_image(self):
        if self.figure is None:
            return

        wd, ht = self.get_window_size()

        # Get surface as a numpy array
        surface = self.get_surface()
        if isinstance(surface, np.ndarray):
            arr8 = surface
        else:
            arr8 = np.fromstring(surface.tobytes(), dtype=np.uint8)
            # extend array with alpha channel if missing
            if len(arr8) < ht * wd * 4:
                arr8 = arr8.reshape((ht, wd, 3))
            else:
                arr8 = arr8.reshape((ht, wd, 4))

        if arr8.shape[2] == 3:
            # extend array with alpha channel if missing
            alpha = np.full((ht, wd, 1), 255, dtype=np.uint8)
            arr8 = np.concatenate((arr8, alpha), axis=2)

        # Casting as a 32-bit uint array type hopefully to get more
        # efficient JSON encoding en route to the browser
        data = arr8.view(dtype=np.uint32).reshape((ht, wd))

        data = np.flipud(data)

        dst_x = dst_y = 0

        # Create an Image_RGBA object in the plot
        if self.bkimage is None:
            self.d_src = ColumnDataSource({'image': [data]})
            self.bkimage = self.figure.image_rgba(image='image',
                                                  x=dst_x, y=dst_y,
                                                  dw=wd, dh=ht,
                                                  source=self.d_src)
            self._setup_handlers(self.d_src)

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


class ImageViewBokeh2(ImageView.ImageViewBase):
    """
    This version does all the graphical overlays on the client side.
    """

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)
        # Our Bokeh plot
        self.figure = None
        # Holds the image on the plot
        self.bkimage = None
        self.d_src = None
        self._push_handle = None

        self.defer_redraw = True

        # NOTE: Bokeh manages it's Y coordinates by default with
        # the origin at the bottom (see base class)
        self.origin_upper = True
        self._invert_y = False

        self.img_fg = (1.0, 1.0, 1.0)
        self.img_bg = (0.5, 0.5, 0.5)

        # Bokeh expects RGBA data for color images
        self.rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

        # cursors
        self.cursor = {}

        # For timing events
        self._msg_timer = None
        self._defer_timer = None

        self.t_.set_defaults(show_pan_position=False,
                             onscreen_ff='Sans Serif')

    def set_figure(self, figure, handle=None):
        """Call this with the Bokeh figure object."""
        self.figure = figure
        self.bkimage = None
        self._push_handle = handle

        wd = figure.plot_width
        ht = figure.plot_height

        self.configure_window(wd, ht)

        doc = curdoc()
        self.logger.info(str(dir(doc)))
        #doc.add_periodic_callback(self.timer_cb, 100)
        self.logger.info("figure set")

    def get_figure(self):
        return self.figure

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.

        NOTE: this version uses a Figure.FigImage to render the image.
        """
        pass

    def configure_window(self, width, height):
        self.configure(width, height)

    def _setup_handlers(self, source):
        pass

    def _resize_cb(self, event):
        wd, ht = event.width, event.height
        self.logger.debug("canvas resized %dx%d" % (wd, ht))
        self.configure_window(wd, ht)

    def get_png_image_as_buffer(self, output=None):
        ibuf = output
        if ibuf is None:
            ibuf = BytesIO()
        self.figure.write_to_png(ibuf)
        return ibuf

    def update_image(self):
        self.logger.debug("redraw surface")
        if self.figure is None:
            return

        # Grab the RGB array for the current image and place it in the
        # Bokeh image
        data = self.getwin_array(order=self.rgb_order)
        ht, wd = data.shape[:2]

        # Casting as a 32-bit uint array type hopefully to get more
        # efficient JSON encoding en route to the browser
        data = data.view(dtype=np.uint32).reshape((ht, wd))

        dst_x = dst_y = 0

        try:
            # Create an Image_RGBA object in the plot
            if self.bkimage is None:
                self.d_src = ColumnDataSource({'image': [data]})
                self.bkimage = self.figure.image_rgba(image='image',
                                                      x=dst_x, y=dst_y,
                                                      dw=wd, dh=ht,
                                                      source=self.d_src)
                self._setup_handlers(self.d_src)

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

        except Exception as e:
            self.logger.error("Error updating image: %s" % (str(e)))
            return

    def set_cursor(self, cursor):
        pass

    def onscreen_message(self, text, delay=None):
        doc = curdoc()
        try:
            doc.remove_timeout_callback(self._msg_timer)
        except Exception:
            pass

        if text is not None:
            self.set_onscreen_message(text)

        msec = int(delay * 1000.0)
        if delay:
            self._msg_timer = curdoc().add_timeout_callback(
                self.onscreen_message_off, msec)

    def onscreen_message_off(self):
        self.set_onscreen_message(None)

    def reschedule_redraw(self, time_sec):
        doc = curdoc()
        try:
            doc.remove_timeout_callback(self._defer_timer)
        except Exception:
            pass
        msec = int(time_sec * 1000.0)
        self._defer_timer = curdoc().add_timeout_callback(self.timer_cb,
                                                          msec)
        #self.logger.info("redrawing")
        #self.delayed_redraw()

    def show_pan_mark(self, tf):
        self.t_.set(show_pan_position=tf)
        self.redraw(whence=3)

    def timer_cb(self, *args):
        self.logger.info("redrawing")
        self.delayed_redraw()


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
        source.on_change('selected', self.select_event_cb)

        ## self._box_select_tool = self.figure.select(dict(type=BoxSelectTool))
        ## self._box_select_tool.select_every_mousemove = True
        #self._pan_tool = self.figure.select(dict(type=PanTool))
        #self._pan_tool.select_every_mousemove = True

        fig = self.figure
        ## #connect("map_event", self.map_event)
        fig.on_event(MouseEnter, self.enter_notify_event)
        fig.on_event(MouseLeave, self.leave_notify_event)
        fig.on_event(MouseMove, self.motion_notify_event)
        ## #connect("focus_in_event", self.focus_event, True)
        ## #connect("focus_out_event", self.focus_event, False)
        ## connect("button_press_event", self.button_press_event)
        ## connect("button_release_event", self.button_release_event)
        ## connect("key_press_event", self.key_press_event)
        ## connect("key_release_event", self.key_release_event)
        fig.on_event(MouseWheel, self.scroll_event)
        fig.on_event(Tap, self.tap_event)
        #fig.on_event(Press, self.press_event)
        #fig.on_event(PanStart, self.pan_start_event)
        #fig.on_event(Pan, self.pan_event)
        #fig.on_event(Pinch, self.pinch_event)

        # TODO: drag-drop event
        self.logger.info("setup event handlers")

    def transkey(self, keyname):
        self.logger.debug("matplotlib keyname='%s'" % (keyname))
        if keyname is None:
            return keyname
        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def get_keyTable(self):
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
            return self.make_ui_callback('key-press', keyname)

    def key_release_event(self, event):
        keyname = event.key
        keyname = self.transkey(keyname)
        if keyname is not None:
            self.logger.debug("key release event, key=%s" % (keyname))
            return self.make_ui_callback('key-release', keyname)

    def button_press_event(self, event):
        x, y = int(event.x), int(event.y)
        button = 0
        ## if event.button in (1, 2, 3):
        ##     button |= 0x1 << (event.button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, event):
        x, y = int(event.x), int(event.y)
        button = 0
        if event.button in (1, 2, 3):
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-release', button, data_x, data_y)

    def select_event_cb(self, attrname, old_val, new_val):
        print("select cb: %s <-- %s" % (attrname, str(new_val)))
        self.logger.info("select cb: %s <-- %s" % (attrname, str(new_val)))

    def get_last_win_xy(self):
        return (self.last_win_x, self.last_win_y)

    def get_last_data_xy(self):
        return (self.last_data_x, self.last_data_y)

    def motion_notify_event(self, event):
        button = 0
        x, y = int(event.x), int(event.y)
        self.last_win_x, self.last_win_y = x, y

        ## if event.button in (1, 2, 3):
        ##     button |= 0x1 << (event.button - 1)
        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y
        self.logger.info("motion event at DATA %dx%d" % (data_x, data_y))

        return self.make_ui_callback('motion', button, data_x, data_y)

    def scroll_event(self, event):
        x, y = int(event.x), int(event.y)

        # Matplotlib only gives us the number of steps of the scroll,
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

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('scroll', direction, amount,
                                     data_x, data_y)

    def pinch_event(self, event):
        # no rotation (seemingly) in the Bokeh pinch event
        rot = 0.0
        scale = event.scale
        self.logger.debug("pinch gesture rot=%f scale=%f" % (rot, scale))

        return self.make_ui_callback('pinch', 'move', rot, scale)

    def pan_start_event(self, event):
        dx, dy = int(event.delta_x), int(event.delta_y)
        self.logger.debug("pan gesture dx=%f dy=%f" % (dx, dy))

        return self.make_ui_callback('pan', 'start', dx, dy)

    def pan_event(self, event):
        dx, dy = int(event.delta_x), int(event.delta_y)
        self.logger.debug("pan gesture dx=%f dy=%f" % (dx, dy))

        return self.make_ui_callback('pan', 'move', dx, dy)

    def tap_event(self, event):
        x, y = int(event.x), int(event.y)
        button = 0
        ## if event.button in (1, 2, 3):
        ##     button |= 0x1 << (event.button - 1)
        self.logger.debug("tap event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def press_event(self, event):
        x, y = int(event.x), int(event.y)
        self.logger.debug("press event at %dx%d" % (x, y))


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

        self.ui_setActive(True)

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

# END
