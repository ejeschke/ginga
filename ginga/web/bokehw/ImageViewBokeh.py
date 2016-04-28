#
# ImageViewBokeh.py -- classes implementing a ginga viewer backend for Bokeh
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys, re
import numpy
import threading
import math
from io import BytesIO

# Bokeh imports
from bokeh.plotting import figure, show, curdoc
from bokeh.models import BoxSelectTool, TapTool, PanTool
#from bokeh.client import push_session
#from bokeh.io import push_notebook

from ginga import ImageView
from ginga import Mixins, Bindings, colors
from ginga.web.bokehw.CanvasRenderBokeh import CanvasRenderer
from ginga.util.heaptimer import TimerHeap

# TODO: is this the right place for this call?
#session = push_session(curdoc())

try:
    # See if we have aggdraw module--best choice
    from ginga.aggw.ImageViewAgg import ImageViewAgg as ImageViewSS, \
         ImageViewAggError as ImageViewError

except ImportError:
    try:
        # No, hmm..ok, see if we have opencv module...
        from ginga.cvw.ImageViewCv import ImageViewCv as ImageViewSS, \
             ImageViewCvError as ImageViewError

    except ImportError:
        try:
            # No dice. How about the PIL module?
            from ginga.pilw.ImageViewPil import ImageViewPil as ImageViewSS, \
                 ImageViewPilError as ImageViewError

        except ImportError:
            # Fall back to mock--there will be no graphic overlays
            from ginga.mockw.ImageViewMock import ImageViewMock as ImageViewSS, \
                 ImageViewMockError as ImageViewError



## class ImageViewBokehError(ImageView.ImageViewError):
##     pass
class ImageViewBokehError(ImageViewError):
    pass

class ImageViewBokeh2(ImageViewSS):
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
        self._push_server = False

        # NOTE: Bokeh manages it's Y coordinates by default with
        # the origin at the bottom (see base class)
        self._originUpper = False

        # override, until we can get access to a timer
        #self.defer_redraw = False

        self.msgtask = None
        # see reschedule_redraw() method
        self._defer_task = None


    def set_figure(self, figure):
        """Call this with the Bokeh figure object."""
        self.figure = figure
        self.bkimage = None

        wd = figure.plot_width
        ht = figure.plot_height

        self.configure_window(wd, ht)

    def get_figure(self):
        return self.figure

    def update_image(self):
        if self.figure is None:
            return

        wd, ht = self.get_window_size()

        # Get surface as a numpy array
        surface = self.get_surface()
        if isinstance(surface, numpy.ndarray):
            arr8 = surface
        else:
            arr8 = numpy.fromstring(surface.tostring(), dtype=numpy.uint8)
            arr8 = arr8.reshape((ht, wd, 4))

        # Bokeh expects a 32-bit uint array type
        view = arr8.view(dtype=numpy.uint32).reshape((ht, wd))

        dst_x = dst_y = 0

        # Create an Image_RGBA object in the plot
        if self.bkimage is None:
            self.bkimage = self.figure.image_rgba(image=[view],
                                                  x=[dst_x], y=[dst_y],
                                                  dw=[wd], dh=[ht])
            d_src = self.bkimage.data_source
            self._setup_handlers(d_src)

        else:
            # note: get the data source (a ColumnDataSource) and update
            # the values
            d_src = self.bkimage.data_source
            d_src.data["image"] = [view]
            d_src.data["x"] = [dst_x]
            d_src.data["y"] = [dst_y]
            d_src.data["dw"] = [wd]
            d_src.data["dh"] = [ht]

        if self._push_server:
            try:
                #self.bkimage.data_source.push_notebook()
                #push_notebook()
                cursession().store_objects(d_src)

            except Exception as e:
                self.logger.warning("Can't update bokeh plot: %s" % (str(e)))


    def reschedule_redraw(self, time_sec):
        if self.figure is not None:
            ## try:
            ##     self.figure.after_cancel(self._defer_task)
            ## except:
            ##     pass
            time_ms = int(time_sec * 1000)
            ## self._defer_task = self.figure.after(time_ms,
            ##                                        self.delayed_redraw)

    def configure_window(self, width, height):
        self.configure_surface(width, height)

    def _setup_handlers(self, source):
        pass

    def set_cursor(self, cursor):
        if self.figure is None:
            return

    def onscreen_message(self, text, delay=None):
        if self.figure is None:
            return
        ## if self.msgtask:
        ##     try:
        ##         self.figure.after_cancel(self.msgtask)
        ##     except:
        ##         pass
        self.message = text
        self.redraw(whence=3)
        if delay:
            ms = int(delay * 1000.0)
            ## self.msgtask = self.figure.after(ms,
            ##                                   lambda: self.onscreen_message(None))

class ImageViewBokeh(ImageView.ImageViewBase):
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
        self._push_server = False

        self.defer_redraw = False

        # NOTE: Bokeh manages it's Y coordinates by default with
        # the origin at the bottom (see base class)
        self._originUpper = False

        self.img_fg = (1.0, 1.0, 1.0)
        self.img_bg = (0.5, 0.5, 0.5)

        self.message = None

        # Bokeh expects RGBA data for color images
        self._rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

        # cursors
        self.cursor = {}

        # For timing events
        self._msg_timer = None
        self._defer_timer = None

        self.t_.setDefaults(show_pan_position=False,
                            onscreen_ff='Sans Serif')

    def set_figure(self, figure):
        """Call this with the Bokeh figure object."""
        self.figure = figure
        self.bkimage = None

        wd = figure.plot_width
        ht = figure.plot_height

        #figure.responsive = True

        # set background color
        #figure.background_fill = self.img_bg

        self.configure_window(wd, ht)

        #self._defer_timer = curdoc().add_periodic_callback(self.timer_cb, 50)

    def get_figure(self):
        return self.figure

    def get_rgb_order(self):
        return self._rgb_order

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.

        NOTE: this version uses a Figure.FigImage to render the image.
        """
        self.logger.debug("redraw surface")
        if self.figure is None:
            return

        # Grab the RGB array for the current image and place it in the
        # Bokeh image
        data = self.getwin_array(order=self._rgb_order)
        ht, wd = data.shape[:2]

        # Bokeh expects a 32-bit uint array type
        view = data.view(dtype=numpy.uint32).reshape((ht, wd))

        dst_x = dst_y = 0

        # Create an Image_RGBA object in the plot
        if self.bkimage is None:
            self.bkimage = self.figure.image_rgba(image=[view],
                                                  x=[dst_x], y=[dst_y],
                                                  dw=[wd], dh=[ht])
            d_src = self.bkimage.data_source
            self._setup_handlers(d_src)

        else:
            # note: get the data source (a ColumnDataSource) and update
            # the values
            d_src = self.bkimage.data_source
            d_src.data["image"] = [view]
            d_src.data["x"] = [dst_x]
            d_src.data["y"] = [dst_y]
            d_src.data["dw"] = [wd]
            d_src.data["dh"] = [ht]


        # Draw a cross in the center of the window in debug mode
        if self.t_['show_pan_position']:
            # size of cross is 4% of max window dimensions
            size = int(max(ht, wd) * 0.04)

            ctr_x, ctr_y = self.get_center()
            self.figure.cross(x=[ctr_x], y=[ctr_y],
                              size=size, color='red', line_width=1)

        # render message if there is one currently
        if self.message:
            y = (ht // 3) * 2
            x = (wd // 2)
            self.figure.text(x=[x], y=[y], text=[self.message],
                             text_font_size='24', text_baseline='middle',
                             text_color='white',
                             text_align='center')

        if self._push_server:
            # force an update of the figure
            try:
                cursession().store_objects(d_src)
                # TODO: if and when to use this?
                #self.bkimage.data_source.push_notebook()
                #push_notebook()

            except Exception as e:
                self.logger.warning("Can't update bokeh plot: %s" % (str(e)))


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
        qimg = self.figure.write_to_png(ibuf)
        return ibuf

    def update_image(self):
        pass

    def set_cursor(self, cursor):
        pass

    def define_cursor(self, ctype, cursor):
        self.cursor[ctype] = cursor

    def get_cursor(self, ctype):
        return self.cursor[ctype]

    def switch_cursor(self, ctype):
        self.set_cursor(self.cursor[ctype])

    def set_fg(self, r, g, b):
        self.img_fg = (r, g, b)
        self.redraw(whence=3)

    def onscreen_message(self, text, delay=None):
        ## try:
        ##     self._msg_timer.stop()
        ## except:
        ##     pass

        self.message = text
        self.redraw(whence=3)

        if delay:
            time_ms = int(delay * 1000.0)
            ## self._msg_timer.interval = time_ms
            ## self._msg_timer.start()

    def onscreen_message_off(self):
        return self.onscreen_message(None)

    def reschedule_redraw(self, time_sec):

        if self._defer_timer is None:
            self.delayed_redraw()
            return

        ## try:
        ##     self._defer_timer.stop()
        ## except:
        ##     pass

        time_ms = int(time_sec * 1000)
        try:
            self._defer_timer.interval = time_ms
            self._defer_timer.start()

        except Exception as e:
            self.logger.warning("Exception starting timer: %s; "
                                "using unoptomized redraw" % (str(e)))
            self.delayed_redraw()

    def show_pan_mark(self, tf):
        self.t_.set(show_pan_position=tf)
        self.redraw(whence=3)

    def timer_cb(self, *args):
        self.logger.info("timer")


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
        # Does widget accept focus when mouse enters window
        self.enter_focus = self.t_.get('enter_focus', True)

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
                     ):
            self.enable_callback(name)

    def set_figure(self, figure):
        super(ImageViewEvent, self).set_figure(figure)

    def _setup_handlers(self, source):
        #source.on_change('selected', self, 'select_event_cb')
        source.on_change('selected', self.select_event_cb)

        ## self._box_select_tool = self.figure.select(dict(type=BoxSelectTool))
        ## self._box_select_tool.select_every_mousemove = True
        self._pan_tool = self.figure.select(dict(type=PanTool))
        #self._pan_tool.select_every_mousemove = True

        ## connect = figure.canvas.mpl_connect
        ## #connect("map_event", self.map_event)
        ## #connect("focus_in_event", self.focus_event, True)
        ## #connect("focus_out_event", self.focus_event, False)
        ## connect("figure_enter_event", self.enter_notify_event)
        ## connect("figure_leave_event", self.leave_notify_event)
        ## #connect("axes_enter_event", self.enter_notify_event)
        ## #connect("axes_leave_event", self.leave_notify_event)
        ## connect("motion_notify_event", self.motion_notify_event)
        ## connect("button_press_event", self.button_press_event)
        ## connect("button_release_event", self.button_release_event)
        ## connect("key_press_event", self.key_press_event)
        ## connect("key_release_event", self.key_release_event)
        ## connect("scroll_event", self.scroll_event)

        # TODO: drag-drop event
        pass

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

    def set_enter_focus(self, tf):
        self.enter_focus = tf

    def focus_event(self, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, event):
        if self.enter_focus:
            self.focus_event(event, True)
        return self.make_callback('enter')

    def leave_notify_event(self, event):
        self.logger.debug("leaving widget...")
        if self.enter_focus:
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
        x, y = event.x, event.y
        button = 0
        if event.button in (1, 2, 3):
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, event):
        x, y = event.x, event.y
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
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y

        if event.button in (1, 2, 3):
            button |= 0x1 << (event.button - 1)
        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y
        self.logger.debug("motion event at DATA %dx%d" % (data_x, data_y))

        return self.make_ui_callback('motion', button, data_x, data_y)

    def scroll_event(self, event):
        x, y = event.x, event.y

        # Matplotlib only gives us the number of steps of the scroll,
        # positive for up and negative for down.  No horizontal scrolling.
        direction = None
        if event.step > 0:
            direction = 0.0
        elif event.step < 0:
            direction = 180.0

        amount = abs(event.step) * 15.0

        self.logger.debug("scroll deg=%f direction=%f" % (
            amount, direction))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('scroll', direction, amount,
                                  data_x, data_y)

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



#END
