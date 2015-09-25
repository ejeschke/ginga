#
# ImageViewMock.py -- classes for the display of FITS files in mock widgets
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import numpy
from io import BytesIO

from ginga import ImageView, Mixins, Bindings
from ginga.util.io_rgb import RGBFileHandler
from ginga.mockw.CanvasRenderMock import CanvasRenderer

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
icon_dir = os.path.abspath(os.path.join(moduleHome, '..', 'icons'))


class ImageViewMockError(ImageView.ImageViewError):
    pass


class ImageViewMock(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)

        # Set this to the order in which you want channels stacked
        # in the numpy array delivered for writing to the off-screen
        # pixmap for your widget set
        self._rgb_order = 'BGRA'

        self.renderer = CanvasRenderer(self)

        self.t_.setDefaults(show_pan_position=False,
                            onscreen_ff='Sans Serif')

        self.message = None
        # This holds the off-screen pixel map.  It's creation is usually
        # deferred until we know the final size of the window.
        self.pixmap = None
        # This holds the native image RGB or canvas widget. You should
        # create it here
        self.imgwin = None

        # cursors
        self.cursor = {}

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
        surface = self.getwin_array(order=self._rgb_order)
        return surface

    def get_rgb_order(self):
        return self._rgb_order

    def _render_offscreen(self, drawable, data, dst_x, dst_y,
                          width, height):
        # NOTE [A]
        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        # fill pixmap with background color
        imgwin_wd, imgwin_ht = self.get_window_size()
        # fillRect(Rect(0, 0, imgwin_wd, imgwin_ht), bgclr)

        # draw image data from buffer to offscreen pixmap at
        # (dst_x, dst_y) with size (width x height)
        ## painter.drawImage(Rect(dst_x, dst_y, width, height),
        ##                   data,
        ##                   Rect(0, 0, width, height))

        # Draw a cross in the center of the window in debug mode
        if self.t_['show_pan_position']:
            ctr_x, ctr_y = self.get_center()
            #painter.drawLine(ctr_x - 10, ctr_y, ctr_x + 10, ctr_y)
            #painter.drawLine(ctr_x, ctr_y - 10, ctr_x, ctr_y + 10)

        # render self.message
        if self.message:
            y = ((imgwin_ht // 3) * 2) - (ht // 2)
            x = (imgwin_wd // 2) - (wd // 2)
            #painter.drawText(x, y, message)


    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the offscreen pixmap.
        """
        self.logger.debug("redraw pixmap=%s" % (self.pixmap))
        if self.pixmap is None:
            return
        self.logger.debug("drawing to pixmap")

        # Prepare array for rendering
        arr = rgbobj.get_array(self._rgb_order)
        (height, width) = arr.shape[:2]

        return self._render_offscreen(self.pixmap, arr, dst_x, dst_y,
                                      width, height)

    def configure_window(self, width, height):
        """
        This method is called by the event handler when the
        size of the window changes (or it can be called manually).
        We allocate an off-screen pixmap of the appropriate size
        and inform the superclass of our window size.
        """
        self.configure_surface(width, height)

    def configure_surface(self, width, height):
        self.logger.debug("window size reconfigured to %dx%d" % (
            width, height))
        # TODO: allocate pixmap of width x height
        self.pixmap = None

        self.configure(width, height)

    def get_rgb_image_as_buffer(self, output=None, format='png',
                                quality=90):
        # copy pixmap to buffer
        data_np = self.getwin_array(order=self.get_rgb_order())
        header = {}
        fmt_buf = self.rgb_fh.get_buffer(data_np, header, format,
                                         output=output)
        return fmt_buf

    def get_image_as_buffer(self, output=None):
        return self.get_rgb_image_as_buffer(self, output=output)

    def get_image_as_array(self):
        return self.getwin_array(order=self.get_rgb_order())

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        buf = self.get_rgb_image_as_buffer(format=format, quality=quality)
        return buf

    def get_rgb_image_as_widget(self, output=None, format='png',
                                quality=90):
        imgwin_wd, imgwin_ht = self.get_window_size()
        # copy pixmap to native widget type
        # ...
        # image_w = self.pixmap.copy(0, 0, imgwin_wd, imgwin_ht)
        image_w = None

        return image_w

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        img_w = self.get_rgb_image_as_widget()
        # assumes that the image widget has some method for saving to
        # a file
        res = img_w.save(filepath, format=format, quality=quality)

    def get_image_as_widget(self):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        arr = self.getwin_array(order=self._rgb_order)

        # convert numpy array to native image widget
        image_w = self._get_wimage(arr)
        return image_w

    def save_image_as_file(self, filepath, format='png', quality=90):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        img_w = self.get_image_as_widget()
        # assumes that the image widget has some method for saving to
        # a file
        res = qimg.save(filepath, format=format, quality=quality)

    def reschedule_redraw(self, time_sec):
        # stop any pending redraws, if possible
        # ...

        # schedule a call to delayed_redraw() in time_sec seconds
        # DO NOT BLOCK!
        # ...
        pass

    def update_image(self):
        if (not self.pixmap) or (not self.imgwin):
            return

        self.logger.debug("updating window from pixmap")
        # invalidate the display and force a refresh from
        # offscreen pixmap

    def set_cursor(self, cursor):
        if self.imgwin:
            # set the cursor on self.imgwin
            pass

    def define_cursor(self, ctype, cursor):
        self.cursor[ctype] = cursor

    def get_cursor(self, ctype):
        return self.cursor[ctype]

    def switch_cursor(self, ctype):
        self.set_cursor(self.cursor[ctype])

    def _get_wimage(self, arr_np):
        """Convert the numpy array (which is in our expected order)
        to a native image object in this widget set.
        """
        return result

    def _get_color(self, r, g, b):
        """Convert red, green and blue values specified in floats with
        range 0-1 to whatever the native widget color object is.
        """
        clr = (r, g, b)
        return clr

    def onscreen_message(self, text, delay=None):
        # stop any scheduled updates of the message

        # set new message text
        self.message = text
        self.redraw(whence=3)

        if delay:
            # schedule a call to onscreen_message_off after
            # `delay` sec
            pass

    def onscreen_message_off(self):
        return self.onscreen_message(None)

    def show_pan_mark(self, tf):
        self.t_.set(show_pan_position=tf)
        self.redraw(whence=3)


class ImageViewEvent(ImageViewMock):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewMock.__init__(self, logger=logger, rgbmap=rgbmap,
                               settings=settings)

        # Make any calls to map UI events on self.imgwin to methods
        # in this object. These events include focus, mouse up/down,
        # mouse movement, wheel movement, key up/down, trackpad
        # gestures
        #...

        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0
        # Does widget accept focus when mouse enters window
        self.follow_focus = True

        # Define cursors
        for curname, filename in (('pan', 'openHandCursor.png'),
                               ('pick', 'thinCrossCursor.png')):
            path = os.path.join(icon_dir, filename)
            cur = make_cursor(path, 8, 8)
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

    def get_keyTable(self):
        return self._keytbl

    def set_follow_focus(self, tf):
        self.follow_focus = tf

    def map_event(self, widget, event):
        """
        Called when the window is mapped to the screen.
        Adjust method signature as appropriate for callback.
        """
        self.configure_window(width, height)
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
        if self.follow_focus:
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
        keyname = self.transkey(keyname, keycode)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback('key-press', keyname)

    def key_release_event(self, widget, event):
        """
        Called when a key is released after being pressed.
        Adjust method signature as appropriate for callback.
        """
        # get keyname or keycode and translate to ginga standard
        # keyname =
        # keycode =
        keyname = self.transkey(keyname, keycode)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback('key-release', keyname)

    def button_press_event(self, widget, event):
        """
        Called when a mouse button is pressed in the widget.
        Adjust method signature as appropriate for callback.
        """
        # x, y = coordinates where the button was pressed

        button = 0
        # Prepare a button mask with bits set as follows:
        #     left button: 0x1
        #   middle button: 0x2
        #    right button: 0x4
        # Others can be added as appropriate
        self.logger.debug("button down event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, widget, event):
        """
        Called when a mouse button is released after being pressed.
        Adjust method signature as appropriate for callback.
        """
        # x, y = coordinates where the button was released

        button = 0
        # prepare button mask as in button_press_event()

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-release', button, data_x, data_y)

    def get_last_win_xy(self):
        return (self.last_win_x, self.last_win_y)

    def get_last_data_xy(self):
        return (self.last_data_x, self.last_data_y)

    def motion_notify_event(self, widget, event):
        """
        Called when a mouse cursor is moving in the widget.
        Adjust method signature as appropriate for callback.
        """
        # x, y = coordinates of cursor
        self.last_win_x, self.last_win_y = x, y

        button = 0
        # prepare button mask as in button_press_event()

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('motion', button, data_x, data_y)

    def scroll_event(self, widget, event):
        """
        Called when a mouse is turned in the widget (and maybe for
        finger scrolling in the trackpad).
        Adjust method signature as appropriate for callback.
        """
        # x, y = coordinates of mouse
        self.last_win_x, self.last_win_y = x, y

        # calculate number of degrees of scroll and direction of scroll
        # both floats in the 0-359.999 range
        # numDegrees =
        # direction =
        self.logger.debug("scroll deg=%f direction=%f" % (
            numDegrees, direction))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('scroll', direction, numDegrees,
                                  data_x, data_y)

    def drop_event(self, widget, event):
        """
        Called when a drop (drag/drop) event happens in the widget.
        Adjust method signature as appropriate for callback.
        """
        # make a call back with a list of URLs that were dropped
        self.logger.debug("dropped filename(s): %s" % (str(paths)))
        self.make_ui_callback('drag-drop', paths)


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


def make_cursor(iconpath, x, y):
    # return a cursor in the widget set's instance type
    # iconpath usually refers to a PNG file and x/y is the
    # cursor hot spot
    cursorw = None
    return cursorw

#END
