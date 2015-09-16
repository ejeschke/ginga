#
# ImageViewTk.py -- classes for the display of FITS files in Tk surfaces
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy

import PIL.Image as PILimage
import PIL.ImageTk as PILimageTk

from ginga import Mixins, Bindings, colors
from ginga.canvas.mixins import DrawingMixin, CanvasMixin, CompoundMixin
from ginga.util.toolbox import ModeIndicator

try:
    # See if we have aggdraw module--best choice
    from ginga.aggw.ImageViewAgg import ImageViewAgg as ImageView, \
         ImageViewAggError as ImageViewError

except ImportError:
    try:
        # No, hmm..ok, see if we have opencv module...
        from ginga.cvw.ImageViewCv import ImageViewCv as ImageView, \
             ImageViewCvError as ImageViewError

    except ImportError:
        try:
            # No dice. How about the PIL module?
            from ginga.pilw.ImageViewPil import ImageViewPil as ImageView, \
                 ImageViewPilError as ImageViewError

        except ImportError:
            # Fall back to mock--there will be no graphic overlays
            from ginga.mockw.ImageViewMock import ImageViewMock as ImageView, \
                 ImageViewMockError as ImageViewError


class ImageViewTkError(ImageViewError):
    pass

class ImageViewTk(ImageView):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.__init__(self, logger=logger,
                           rgbmap=rgbmap,
                           settings=settings)

        self.tkcanvas = None
        self.tkphoto = None

        self.msgtask = None

        # see reschedule_redraw() method
        self._defer_task = None

    def set_widget(self, canvas):
        """Call this method with the Tkinter canvas that will be used
        for the display.
        """
        self.tkcanvas = canvas

        canvas.bind("<Configure>", self._resize_cb)
        width = canvas.winfo_width()
        height = canvas.winfo_height()

        self.configure_window(width, height)

    def get_widget(self):
        return self.tkcanvas

    def update_image(self):
        if self.tkcanvas is None:
            return

        cr = self.tkcanvas

        # remove all old items from the canvas
        items = cr.find_all()
        for item in items:
            cr.delete(item)

        wd, ht = self.get_window_size()

        # Get surface as a numpy array
        surface = self.get_surface()
        if isinstance(surface, numpy.ndarray):
            arr8 = surface
        else:
            arr8 = numpy.fromstring(surface.tostring(), dtype=numpy.uint8)
            arr8 = arr8.reshape((ht, wd, 4))

        # make a Tk photo image and stick it to the canvas
        image = PILimage.fromarray(arr8)
        photo = PILimageTk.PhotoImage(image)
        # hang on to a reference otherwise it gets gc'd
        self.tkphoto = photo

        cr.create_image(0, 0, anchor='nw', image=photo)

        # is this necessary?
        cr.config(scrollregion=cr.bbox('all'))

    def reschedule_redraw(self, time_sec):
        if self.tkcanvas is not None:
            try:
                self.tkcanvas.after_cancel(self._defer_task)
            except:
                pass
            time_ms = int(time_sec * 1000)
            self._defer_task = self.tkcanvas.after(time_ms,
                                                   self.delayed_redraw)

    def configure_window(self, width, height):
        self.configure_surface(width, height)

    def _resize_cb(self, event):
        self.configure_window(event.width, event.height)

    def set_cursor(self, cursor):
        if self.tkcanvas is None:
            return
        self.tkcanvas.config(cursor=cursor)

    def onscreen_message(self, text, delay=None):
        if self.tkcanvas is None:
            return
        if self.msgtask:
            try:
                self.tkcanvas.after_cancel(self.msgtask)
            except:
                pass
        self.message = text
        self.redraw(whence=3)
        if delay:
            ms = int(delay * 1000.0)
            self.msgtask = self.tkcanvas.after(ms,
                                              lambda: self.onscreen_message(None))


class ImageViewEvent(ImageViewTk):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewTk.__init__(self, logger=logger, rgbmap=rgbmap,
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

        # @$%&^(_)*&^ tk!!
        self._keytbl = {
            'shift_l': 'shift_l',
            'shift_r': 'shift_r',
            'control_l': 'control_l',
            'control_r': 'control_r',
            'alt_l': 'alt_l',
            'alt_r': 'alt_r',
            'super_l': 'super_l',
            'super_r': 'super_r',
            'meta_right': 'meta_right',
            'asciitilde': '~',
            'grave': 'backquote',
            'exclam': '!',
            'at': '@',
            'numbersign': '#',
            'percent': '%',
            'asciicircum': '^',
            'ampersand': '&',
            'asterisk': '*',
            'dollar': '$',
            'parenleft': '(',
            'parenright': ')',
            'underscore': '_',
            'minus': '-',
            'plus': '+',
            'equal': '=',
            'braceleft': '{',
            'braceright': '}',
            'bracketleft': '[',
            'bracketright': ']',
            'bar': '|',
            'colon': ':',
            'semicolon': ';',
            'quotedbl': 'doublequote',
            'apostrophe': 'singlequote',
            'backslash': 'backslash',
            'less': '<',
            'greater': '>',
            'comma': ',',
            'period': '.',
            'question': '?',
            'slash': '/',
            'space': 'space',
            'escape': 'escape',
            'return': 'return',
            'tab': 'tab',
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
        hand = 'fleur'
        self.define_cursor('pan', hand)
        cross = 'cross'
        self.define_cursor('pick', cross)

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     ):
            self.enable_callback(name)

    def set_widget(self, canvas):
        super(ImageViewEvent, self).set_widget(canvas)

        canvas.bind("<Enter>", self.enter_notify_event)
        canvas.bind("<Leave>", self.leave_notify_event)
        canvas.bind("<FocusIn>", lambda evt: self.focus_event(evt, True))
        canvas.bind("<FocusOut>", lambda evt: self.focus_event(evt, False))
        canvas.bind("<KeyPress>", self.key_press_event)
        canvas.bind("<KeyRelease>", self.key_release_event)
        #canvas.bind("<Map>", self.map_event)
        # scroll events in tk are overloaded into the button press events
        canvas.bind("<ButtonPress>", self.button_press_event)
        canvas.bind("<ButtonRelease>", self.button_release_event)
        canvas.bind("<Motion>", self.motion_notify_event)

        # TODO: Set up widget as a drag and drop destination

        return self.make_callback('map')

    def transkey(self, keyname):
        self.logger.debug("key name in tk '%s'" % (keyname))
        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def get_keyTable(self):
        return self._keytbl

    def set_follow_focus(self, tf):
        self.follow_focus = tf

    def focus_event(self, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, event):
        if self.follow_focus:
            self.tkcanvas.focus_set()
        return self.make_callback('enter')

    def leave_notify_event(self, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, event):
        # without this we do not get key release events if the focus
        # changes to another window
        self.tkcanvas.grab_set_global()

        keyname = event.keysym
        keyname = self.transkey(keyname)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback('key-press', keyname)

    def key_release_event(self, event):
        self.tkcanvas.grab_release()

        keyname = event.keysym
        keyname = self.transkey(keyname)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback('key-release', keyname)

    def button_press_event(self, event):
        x = event.x; y = event.y
        button = 0
        if event.num != 0:
            # some kind of wierd convention for scrolling, shoehorned into
            # Tk, I guess
            if event.num in (4, 5):
                direction = 0.0   # up
                if event.num == 5:
                    # down
                    direction = 180.0
                # 15 deg is standard 1-click turn for a wheel mouse
                numDegrees = 15.0
                self.logger.debug("scroll deg=%f direction=%f" % (
                    numDegrees, direction))

                data_x, data_y = self.get_data_xy(x, y)
                self.last_data_x, self.last_data_y = data_x, data_y

                return self.make_ui_callback('scroll', direction, numDegrees,
                                          data_x, data_y)

            button |= 0x1 << (event.num - 1)
        self._button = button
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = 0
        if event.num != 0:
            if event.num in (4, 5):
                return False

            button |= 0x1 << (event.num - 1)
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

        # num = event.num
        # if num == 1:
        #     button |= 0x1
        # elif num == 2:
        #     button |= 0x2
        # elif num == 3:
        #     button |= 0x4
        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('motion', button, data_x, data_y)

    ## def drop_event(self, widget, context, x, y, selection, targetType,
    ##                time):
    ##     if targetType != self.TARGET_TYPE_TEXT:
    ##         return False
    ##     paths = selection.data.split('\n')
    ##     self.logger.debug("dropped filename(s): %s" % (str(paths)))
    ##     return self.make_ui_callback('drag-drop', paths)


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


class ImageViewCanvasError(ImageViewTkError):
    pass

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
