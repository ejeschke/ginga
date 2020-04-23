#
# ImageViewMock.py -- a backend for Ginga using a mock renderer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os

from ginga import ImageView, Mixins, Bindings
from ginga.util.io_rgb import RGBFileHandler
from ginga.mockw.CanvasRenderMock import CanvasRenderer
from ginga.util.paths import icondir


class ImageViewMockError(ImageView.ImageViewError):
    pass


class ImageViewMock(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)

        # Set this to the order in which you want channels stacked
        # in the numpy array delivered for writing to the off-screen
        # pixmap for your widget set
        self.rgb_order = 'BGRA'

        self.renderer = CanvasRenderer(self)

        # This holds the off-screen pixel map.  It's creation is usually
        # deferred until we know the final size of the window.
        self.pixmap = None
        # This holds the native image RGB or canvas widget. You should
        # create it here
        self.imgwin = None

        # override default
        #self.defer_redraw = False
        self.rgb_fh = RGBFileHandler(self.logger)

    def get_widget(self):
        """
        Call this method to extract the widget to pack into your GUI
        when you are building the viewer into things.
        """
        return self.imgwin

    def get_surface(self):
        # for compatibility with agg and opencv backends
        surface = self.getwin_array(order=self.rgb_order)
        return surface

    def configure_window(self, width, height):
        """
        This method is called by the event handler when the
        size of the window changes (or it can be called manually).
        We allocate an off-screen pixmap of the appropriate size
        and inform the superclass of our window size.
        """
        self.configure(width, height)

    def reschedule_redraw(self, time_sec):
        # stop any pending redraws, if possible
        # ...

        # schedule a call to delayed_redraw() in time_sec seconds
        # DO NOT BLOCK!
        # ...
        pass

    def update_widget(self):
        if (not self.pixmap) or (not self.imgwin):
            return

        self.logger.debug("updating window from pixmap")
        # invalidate the display and force a refresh from
        # offscreen pixmap

    def set_cursor(self, cursor):
        if self.imgwin:
            # set the cursor on self.imgwin
            pass

    def make_cursor(self, iconpath, x, y):
        # return a cursor in the widget set's instance type
        # iconpath usually refers to a PNG file and x/y is the
        # cursor hot spot
        cursorw = None
        return cursorw

    def take_focus(self):
        # have the widget grab the keyboard focus
        pass


class ImageViewEvent(ImageViewMock):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewMock.__init__(self, logger=logger, rgbmap=rgbmap,
                               settings=settings)

        # Make any calls to map UI events on self.imgwin to methods
        # in this object. These events include focus, mouse up/down,
        # mouse movement, wheel movement, key up/down, trackpad
        # gestures
        #...

        # Define cursors
        for curname, filename in (('pan', 'openHandCursor.png'),
                                  ('pick', 'thinCrossCursor.png')):
            path = os.path.join(icondir, filename)
            cur = self.make_cursor(path, 8, 8)
            self.define_cursor(curname, cur)

        # key table mapping characters produced by the key down events
        # to our "standard" ASCII character names
        self._keytbl = {
            '`': 'backquote',
            '"': 'doublequote',
            "'": 'singlequote',
            '\\': 'backslash',
            ' ': 'space',
        }

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'pan', 'swipe', 'tap'):
            self.enable_callback(name)

    def transkey(self, keycode, keyname):
        """
        Translate a keycode/keyname in the widget set to a ginga
        standard ASCII symbol.

        left control key: 'control_l'
        right control key: 'control_r' ('control_l' is also ok)
        left shift key: 'shift_l'
        right shift key: 'shift_r' ('shift_l' is also ok)
        left alternate key: 'alt_l'
        right alternate key: 'alt_r' ('alt_l' is also ok)
        escape key: 'escape'
        'windows' key or 'control' key on macs: 'meta_right'
        function keys: 'f1', 'f2', etc.
        """
        self.logger.debug("keycode=%d keyname='%s'" % (
            keycode, keyname))

        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def get_key_table(self):
        return self._keytbl

    def map_event(self, widget, event):
        """
        Called when the window is mapped to the screen.
        Adjust method signature as appropriate for callback.
        """
        #self.configure_window(width, height)
        return self.make_callback('map')

    def focus_event(self, widget, event, hasFocus):
        """
        Called when the window gets focus.
        Adjust method signature as appropriate for callback.
        """
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, widget, event):
        """
        Called when the mouse cursor enters the window.
        Adjust method signature as appropriate for callback.
        """
        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            # set focus on widget
            pass
        return self.make_callback('enter')

    def leave_notify_event(self, widget, event):
        """
        Called when the mouse cursor leaves the window.
        Adjust method signature as appropriate for callback.
        """
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, widget, event):
        """
        Called when a key is pressed and the window has the focus.
        Adjust method signature as appropriate for callback.
        """
        # get keyname or keycode and translate to ginga standard
        # keyname =
        # keycode =
        keyname = ''  # self.transkey(keyname, keycode)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_release_event(self, widget, event):
        """
        Called when a key is released after being pressed.
        Adjust method signature as appropriate for callback.
        """
        # get keyname or keycode and translate to ginga standard
        # keyname =
        # keycode =
        keyname = ''  # self.transkey(keyname, keycode)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-release', keyname)

    def button_press_event(self, widget, event):
        """
        Called when a mouse button is pressed in the widget.
        Adjust method signature as appropriate for callback.
        """
        x, y = event.x, event.y

        # x, y = coordinates where the button was pressed
        self.last_win_x, self.last_win_y = x, y

        button = 0
        # Prepare a button mask with bits set as follows:
        #     left button: 0x1
        #   middle button: 0x2
        #    right button: 0x4
        # Others can be added as appropriate
        self.logger.debug("button down event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-press', button,
                                            data_x, data_y)

    def button_release_event(self, widget, event):
        """
        Called when a mouse button is released after being pressed.
        Adjust method signature as appropriate for callback.
        """
        x, y = event.x, event.y

        # x, y = coordinates where the button was released
        self.last_win_x, self.last_win_y = x, y

        button = 0
        # prepare button mask as in button_press_event()

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-release', button,
                                            data_x, data_y)

    def motion_notify_event(self, widget, event):
        """
        Called when a mouse cursor is moving in the widget.
        Adjust method signature as appropriate for callback.
        """
        x, y = event.x, event.y

        # x, y = coordinates of cursor
        self.last_win_x, self.last_win_y = x, y

        button = 0
        # prepare button mask as in button_press_event()

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def scroll_event(self, widget, event):
        """
        Called when a mouse is turned in the widget (and maybe for
        finger scrolling in the trackpad).
        Adjust method signature as appropriate for callback.
        """
        x, y = event.x, event.y
        num_degrees = 0
        direction = 0

        # x, y = coordinates of mouse
        self.last_win_x, self.last_win_y = x, y

        # calculate number of degrees of scroll and direction of scroll
        # both floats in the 0-359.999 range
        # num_degrees =
        # direction =
        self.logger.debug("scroll deg=%f direction=%f" % (
            num_degrees, direction))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'scroll', direction,
                                            num_degrees, data_x, data_y)

    def drop_event(self, widget, event):
        """
        Called when a drop (drag/drop) event happens in the widget.
        Adjust method signature as appropriate for callback.
        """
        # make a call back with a list of URLs that were dropped
        #self.logger.debug("dropped filename(s): %s" % (str(paths)))
        #self.make_ui_callback_viewer(self, 'drag-drop', paths)
        raise NotImplementedError


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

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, settings=settings,
                                rgbmap=rgbmap)
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


#END
