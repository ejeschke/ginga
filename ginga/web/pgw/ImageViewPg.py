#
# ImageViewPg.py -- classes for the display of FITS files in web browsers
#                        using javascript/HTML5 canvas/websockets
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import threading
import time
import io

from ginga import Mixins, Bindings
from ginga.misc import log, Bunch
from ginga.canvas.mixins import DrawingMixin, CanvasMixin, CompoundMixin
from ginga.util.toolbox import ModeIndicator
from ginga.web.pgw import PgHelp


try:
    # See if we have aggdraw module--best choice
    from ginga.aggw.ImageViewAgg import ImageViewAgg as ImageView, \
         ImageViewAggError as ImageViewError

except ImportError:
    try:
        # No, hmm..ok, see if we have PIL module...
        from ginga.pilw.ImageViewPil import ImageViewPil as ImageView, \
             ImageViewPilError as ImageViewError

    except ImportError:
        try:
            # No dice. How about the OpenCv module?
            from ginga.cvw.ImageViewCv import ImageViewCv as ImageView, \
                 ImageViewCvError as ImageViewError

        except ImportError:
            # Fall back to mock--there will be no graphic overlays
            from ginga.mockw.ImageViewMock import ImageViewMock as ImageView, \
                 ImageViewMockError as ImageViewError


class ImageViewPgError(ImageViewError):
    pass

class ImageViewPg(ImageView):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.__init__(self, logger=logger,
                           rgbmap=rgbmap,
                           settings=settings)

        self.pgcanvas = None

        # format for rendering image on HTML5 canvas
        # NOTE: 'jpeg' has much better performance than 'png', but can show
        # some artifacts, especially noticeable with small text
        self.t_.setDefaults(html5_canvas_format='jpeg')

        #self.defer_redraw = False


    def set_widget(self, canvas):
        """Call this method with the widget that will be used
        for the display.
        """
        self.logger.debug("set widget canvas=%s" % canvas)
        self.pgcanvas = canvas
        #self.pgcanvas.set_viewer(self)

    def get_widget(self):
        return self.pgcanvas

    def update_image(self):
        self.logger.debug("update_image pgcanvas=%s" % self.pgcanvas)
        if self.pgcanvas is None:
            return

        try:
            self.logger.debug("getting image as buffer...")
            format = self.t_.get('html5_canvas_format', 'jpeg')
            buf = self.get_rgb_image_as_buffer(format=format, quality=90)
            self.logger.debug("got '%s' RGB image buffer, len=%d" % (
                format, len(buf)))

            self.pgcanvas.do_update(buf)

        except Exception as e:
            self.logger.error("Couldn't update canvas: %s" % (str(e)))

    def reschedule_redraw(self, time_sec):
        if not (self.pgcanvas is None):
            self.pgcanvas.reset_timer('redraw', time_sec)
        else:
            self.delayed_redraw()

    def set_cursor(self, cursor):
        if self.pgcanvas is None:
            return
        #self.pgcanvas.config(cursor=cursor)

    def onscreen_message(self, text, delay=None):
        if self.pgcanvas is None:
            return
        self.message = text
        self.redraw(whence=3)
        if delay:
            self.pgcanvas.reset_timer('msg', delay)

    def clear_onscreen_message(self):
        self.logger.debug("clearing message...")
        self.onscreen_message(None)

    def configure_window(self, width, height):
        self.configure_surface(width, height)

    def map_event(self, event):
        self.configure_window(event.width, event.height)
        self.redraw(whence=0)

    def resize_event(self, event):
        wd, ht = event.x, event.y
        # Not yet ready for prime-time--browser seems to mess with the
        # aspect ratio
        self.configure_window(wd, ht)
        self.redraw(whence=0)


class ImageViewEvent(ImageViewPg):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewPg.__init__(self, logger=logger, rgbmap=rgbmap,
                             settings=settings)

        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0
        # Does widget accept focus when mouse enters window
        self.follow_focus = True

        self._button = 0

        # @$%&^(_)*&^ javascript!!
        self._keytbl = {
            16: 'shift_l',
            #'shift_r': 'shift_r',
            17: 'control_l',
            #'control_r': 'control_r',
            18: 'alt_l',
            #'alt_r': 'alt_r',
            'super_l': 'super_l',
            'super_r': 'super_r',
            'meta_right': 'meta_right',
            ord('~'): '~',
            # borrow ~ for escape for use in browser
            #ord('~'): 'escape',
            ord('`'): 'backquote',
            ord('!'): '!',
            ord('@'): '@',
            ord('#'): '#',
            ord('%'): '%',
            ord('^'): '^',
            ord('&'): '&',
            ord('*'): '*',
            ord('$'): '$',
            ord('('): '(',
            ord(')'): ')',
            ord('_'): '_',
            ord('-'): '-',
            ord('+'): '+',
            ord('='): '=',
            ord('{'): '{',
            ord('}'): '}',
            ord('['): '[',
            ord(']'): ']',
            ord('|'): '|',
            ord(':'): ':',
            ord(';'): ';',
            ord('"'): 'doublequote',
            ord("'"): 'singlequote',
            ord('\\'): 'backslash',
            ord('<'): '<',
            ord('>'): '>',
            ord(','): ',',
            ord('.'): '.',
            ord('?'): '?',
            ord('/'): '/',
            ord(' '): 'space',
            27: 'escape',
            13: 'return',
            9: 'tab',
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

        self._browser_problem_keys = ('shift_l', 'control_l', 'escape',
                                      'tab')
        # Define cursors for pick and pan
        #hand = openHandCursor()
        hand = 'fleur'
        self.define_cursor('pan', hand)
        cross = 'cross'
        self.define_cursor('pick', cross)

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'rotate', 'pan', 'swipe', 'tap'):
            self.enable_callback(name)

    def set_widget(self, canvas):
        super(ImageViewEvent, self).set_widget(canvas)

        ## canvas.bind("<Enter>", self.enter_notify_event)
        ## canvas.bind("<Leave>", self.leave_notify_event)
        ## canvas.bind("<FocusIn>", lambda evt: self.focus_event(evt, True))
        ## canvas.bind("<FocusOut>", lambda evt: self.focus_event(evt, False))
        ## canvas.bind("<KeyPress>", self.key_press_event)
        ## canvas.bind("<KeyRelease>", self.key_release_event)
        ## #canvas.bind("<Map>", self.map_event)
        ## # scroll events in tk are overloaded into the button press events
        ## canvas.bind("<ButtonPress>", self.button_press_event)
        ## canvas.bind("<ButtonRelease>", self.button_release_event)
        ## canvas.bind("<Motion>", self.motion_notify_event)

        # TODO: Set up widget as a drag and drop destination

        return self.make_callback('map')

    def transkey(self, keycode):
        self.logger.info("key code in js '%d'" % (keycode))
        try:
            return self._keytbl[keycode]

        except KeyError:
            return chr(keycode)

    def get_keyTable(self):
        return self._keytbl

    def set_follow_focus(self, tf):
        self.follow_focus = tf

    def focus_event(self, event, hasFocus):
        self.logger.debug("focus event: focus=%s" % (hasFocus))
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, event):
        self.logger.debug("entering widget...")
        ## if self.follow_focus:
        ##     self.pgcanvas.focus_set()
        return self.make_callback('enter')

    def leave_notify_event(self, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, event):
        keycode = event.key_code
        keyname = self.transkey(keycode)
        self.logger.info("key press event, key=%s" % (keyname))
        return self.make_ui_callback('key-press', keyname)

    def key_down_event(self, event):
        keycode = event.key_code
        keyname = self.transkey(keycode)
        self.logger.info("key press event, key=%s" % (keyname))
        # special hack for modifiers
        if keyname in self._browser_problem_keys:
            return self.make_ui_callback('key-press', keyname)
        return False

    def key_up_event(self, event):
        keycode = event.key_code
        keyname = self.transkey(keycode)
        self.logger.info("key release event, key=%s" % (keyname))
        # special hack for modifiers
        if keyname in self._browser_problem_keys:
            return self.make_ui_callback('key-release', keyname)
        return False

    def button_press_event(self, event):
        x = event.x; y = event.y
        button = 0
        button |= 0x1 << event.button
        self._button = button
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = 0
        button |= 0x1 << event.button
        self._button = 0
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-release', button, data_x, data_y)

    def get_last_win_xy(self):
        return (self.last_win_x, self.last_win_y)

    def get_last_data_xy(self):
        return (self.last_data_x, self.last_data_y)

    def motion_notify_event(self, event):
        #button = 0
        button = self._button
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y

        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('motion', button, data_x, data_y)

    def scroll_event(self, event):
        x, y = event.x, event.y
        delta = event.delta
        self.last_win_x, self.last_win_y = x, y

        # 15 deg is standard 1-click turn for a wheel mouse
        # delta usually returns +/- 1.0
        numDegrees = abs(delta) * 15.0

        direction = 0.0
        if delta > 0:
            direction = 0.0
        elif delta < 0:
            direction = 180.0
        self.logger.debug("scroll deg=%f direction=%f" % (
            numDegrees, direction))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('scroll', direction, numDegrees,
                                  data_x, data_y)

    def drop_event(self, event):
        data = event.delta
        self.logger.info("data=%s" % (str(data)))
        paths = data.split('\n')
        self.logger.info("dropped text(s): %s" % (str(paths)))
        return self.make_ui_callback('drag-drop', paths)


    def pinch_event(self, event):
        self.logger.info("pinch: event=%s" % (str(event)))
        state = 'move'
        if event.type == 'pinchstart' or event.isfirst:
            state = 'start'
        elif event.type == 'pinchend' or event.isfinal:
            state = 'end'
        rot = event.theta
        scale = event.scale
        self.logger.info("pinch gesture rot=%f scale=%f state=%s" % (
            rot, scale, state))

        return self.make_ui_callback('pinch', state, rot, scale)

    def rotate_event(self, event):
        state = 'move'
        if event.type == 'rotatestart' or event.isfirst:
            state = 'start'
        elif event.type == 'rotateend' or event.isfinal:
            state = 'end'
        rot = event.theta
        self.logger.debug("rotate gesture rot=%f state=%s" % (
            rot, state))

        return self.make_ui_callback('rotate', state, rot)

    def pan_event(self, event):
        state = 'move'
        if event.type == 'panstart' or event.isfirst:
            state = 'start'
        elif event.type == 'panend' or event.isfinal:
            state = 'end'
        # TODO: need to know which ones to flip
        dx, dy = -event.dx, event.dy
        self.logger.info("pan gesture dx=%f dy=%f state=%s" % (
            dx, dy, state))

        return self.make_ui_callback('pan', state, dx, dy)

    def swipe_event(self, event):
        if event.isfinal:
            state = 'end'
            self.logger.info("swipe gesture event=%s" % (str(event)))
            ## self.logger.debug("swipe gesture hdir=%s vdir=%s" % (
            ##     hdir, vdir))
            ## return self.make_ui_callback('swipe', state, hdir, vdir)

    def tap_event(self, event):
        if event.isfinal:
            state = 'end'
            self.logger.info("tap gesture event=%s" % (str(event)))

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


class ImageViewCanvas(ImageViewZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger,
                               rgbmap=rgbmap,
                               settings=settings,
                               bindmap=bindmap,
                               bindings=bindings)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self)

        # we are both a viewer and a canvas
        self.set_canvas(self, private_canvas=self)

        self._mi = ModeIndicator(self)


#END
