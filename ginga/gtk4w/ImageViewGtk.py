#
# ImageViewGtk.py -- a backend for Ginga using Gtk widgets and Cairo
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys
import numpy as np

from ginga.gtk4w import GtkHelp
from ginga import ImageView, Mixins, Bindings
from ginga.cursors import cursor_info
from ginga.canvas import render

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import cairo

have_opengl = False
try:
    from ginga.opengl.GlHelp import get_transforms
    from ginga.opengl.glsl import req
    have_opengl = True
except ImportError:
    pass


class ImageViewGtkError(ImageView.ImageViewError):
    pass


class ImageViewGtk(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        if render is None:
            render = self.t_.get('render_widget', 'widget')
        self.wtype = render
        self.surface = None
        if self.wtype == 'widget':
            imgwin = Gtk.DrawingArea()

            imgwin.set_draw_func(self.draw_event, None)
            imgwin.connect("resize", self.configure_event)

            renderers = ['cairo', 'agg', 'pil', 'opencv']
            self.t_.set_defaults(renderer='cairo')
            if self.t_['renderer'] == 'opengl':
                # currently cannot use opengl renderer except with GLArea
                self.t_.set(renderer='cairo')

            if sys.byteorder == 'little':
                self.rgb_order = 'BGRA'
            else:
                self.rgb_order = 'RGBA'

        elif self.wtype == 'opengl':
            if not have_opengl:
                raise ImageViewGtkError("Please install 'pyopengl' to use render: '%s'" % (render))
            # NOTE: See https://gitlab.gnome.org/GNOME/gtk/issues/1270 for
            # an issue regarding a buggy GLX/Mesa driver for X11 on Linux;
            # if you experience non-GL widgets flashing when using the
            # opengl renderer then try setting the following environment
            # variable:
            #   GDK_GL=software-draw-surface
            #
            imgwin = Gtk.GLArea()
            imgwin.set_required_version(req.major, req.minor)
            imgwin.set_has_depth_buffer(False)
            imgwin.set_has_stencil_buffer(False)
            imgwin.set_auto_render(False)

            imgwin.connect('realize', self.on_realize_cb)
            imgwin.connect('render', self.on_render_cb)
            imgwin.connect("resize", self.configure_glarea_cb)

            renderers = ['opengl']
            # currently can only use opengl renderer with GLArea
            #self.t_.set_defaults(renderer='opengl')
            self.t_.set(renderer='opengl')
            self.rgb_order = 'RGBA'

            # we replace some transforms in the catalog for OpenGL rendering
            self.tform = get_transforms(self)

        else:
            raise ImageViewGtkError("Undefined render type: '%s'" % (render))

        imgwin.set_hexpand(True)
        imgwin.set_vexpand(True)
        self.imgwin = imgwin

        # see reschedule_redraw() method
        self._defer_task = GtkHelp.Timer()
        self._defer_task.add_callback('expired',
                                      lambda timer: self.delayed_redraw())
        self.msgtask = GtkHelp.Timer()
        self.msgtask.add_callback('expired',
                                  lambda timer: self.onscreen_message(None))

        self.renderer = None
        # Pick a renderer that can work with us
        preferred = self.t_['renderer']
        if preferred in renderers:
            renderers.remove(preferred)
        self.possible_renderers = [preferred] + renderers
        self.choose_best_renderer()

    def get_widget(self):
        return self.imgwin

    def choose_renderer(self, name):
        if self.wtype == 'opengl':
            if name != 'opengl':
                raise ValueError("Only possible renderer for this widget "
                                 "is 'opengl'")
        klass = render.get_render_class(name)
        self.renderer = klass(self)

        wd = max(1, self.imgwin.get_width())
        ht = max(1, self.imgwin.get_height())
        self.configure_window(wd, ht)

    def choose_best_renderer(self):
        for name in self.possible_renderers:
            try:
                self.choose_renderer(name)
                self.logger.info("best renderer available is '{}'".format(name))
                return
            except Exception as e:
                # uncomment to troubleshoot
                self.logger.error("Error choosing renderer '{}': {}".format(name, e),
                                  exc_info=True)
                continue

        raise ImageViewGtkError("No valid renderers available: {}".format(str(self.possible_renderers)))

    def get_plain_image_as_pixbuf(self):
        arr = self.getwin_array(order='RGB', dtype=np.uint8)
        pixbuf = GtkHelp.pixbuf_new_from_array(arr,
                                               GdkPixbuf.Colorspace.RGB,
                                               8)
        return pixbuf

    def get_plain_image_as_widget(self):
        """Returns a Gtk.Image widget of the images displayed.
        Does not include overlaid graphics.
        """
        pixbuf = self.get_plain_image_as_pixbuf()
        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def save_plain_image_as_file(self, filepath, format='png', quality=90):
        """Does not include overlaid graphics."""
        pixbuf = self.get_plain_image_as_pixbuf()
        options, values = [], []
        if format == 'jpeg':
            options.append('quality')
            values.append(str(quality))
        pixbuf.savev(filepath, format, options, values)

    def reschedule_redraw(self, time_sec):
        self._defer_task.stop()
        self._defer_task.start(time_sec)

    def _renderer_to_surface(self):

        if isinstance(self.renderer.surface, cairo.ImageSurface):
            # optimization when renderer is cairo:
            # the render already contains a surface we can copy from
            self.surface = self.renderer.surface

        else:
            # create a new surface from rendered array
            arr = self.renderer.get_surface_as_array(order=self.rgb_order)
            arr = np.ascontiguousarray(arr)

            daht, dawd, depth = arr.shape
            if dawd == 0 or daht == 0:
                # can happen if we get a draw event before widget is mapped
                return
            self.logger.debug("arr shape is %dx%dx%d" % (dawd, daht, depth))

            stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                                dawd)
            self.surface = cairo.ImageSurface.create_for_data(arr,
                                                              cairo.FORMAT_ARGB32,
                                                              dawd, daht, stride)

    def update_widget(self):
        if self.imgwin is None:
            return

        self.logger.debug("updating window")
        if self.wtype == 'opengl':
            self.imgwin.queue_render()
            return

        self._renderer_to_surface()

        has_window = self.imgwin.get_mapped()
        if has_window and self.surface is not None:
            imgwin_wd, imgwin_ht = self.get_window_size()

            self.imgwin.queue_draw()

    def draw_event(self, widget, cr, width, height, user_data):
        if self.surface is None:
            # window is not mapped/configured yet
            return
        #self.logger.debug("updating window from surface")
        # redraw the screen from backing surface
        cr.set_source_surface(self.surface, 0, 0)

        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def configure_window(self, width, height):
        self.logger.debug("window size reconfigured to %dx%d" % (
            width, height))
        self.configure(width, height)

    def configure_event(self, widget, width, height):
        # NOTE: this callback is only for the DrawingArea widget
        if self.surface is not None:
            # This is a workaround for a issue in Gtk
            # where we get multiple configure callbacks even though
            # the size hasn't changed.  We avoid creating a new surface
            # if there is an old surface with the exact same size.
            # This prevents some flickering of the display on focus events.
            wwd, wht = self.get_window_size()
            if (wwd == width) and (wht == height):
                return True

        self.logger.debug(f"allocation is {width}x{height}")
        self.configure_window(width, height)
        return True

    def configure_glarea_cb(self, widget, width, height):
        # NOTE: this callback is only for the GLArea (OpenGL) widget
        self.logger.debug("allocation is %dx%d" % (width, height))
        self.configure_window(width, height)
        return True

    def make_context_current(self):
        ctx = self.imgwin.get_context()
        if ctx is not None:
            ctx.make_current()
        return ctx

    def on_realize_cb(self, area):
        # NOTE: this callback is only for the GLArea (OpenGL) widget
        self.renderer.gl_initialize()

    def on_render_cb(self, area, ctx):
        # NOTE: this callback is only for the GLArea (OpenGL) widget
        self.renderer.gl_paint()

    def prepare_image(self, cvs_img, cache, whence):
        self.renderer.prepare_image(cvs_img, cache, whence)

    def set_cursor(self, cursor):
        self.imgwin.set_cursor(cursor)

    def make_cursor(self, iconpath, x, y, size=None):
        if size is None:
            def_px_size = self.settings.get('default_cursor_length', 16)
            size = (def_px_size, def_px_size)
        cursor = GtkHelp.make_cursor(self.imgwin, iconpath, x, y, size=size)
        return cursor

    def center_cursor(self):
        # NOTE: disp.warp_pointer() not supported in Gtk4
        pass

    def position_cursor(self, data_x, data_y):
        # NOTE: disp.warp_pointer() not supported in Gtk4
        pass

    def make_timer(self):
        return GtkHelp.Timer()

    def onscreen_message(self, text, delay=None, redraw=True):
        self.msgtask.stop()
        self.set_onscreen_message(text, redraw=redraw)
        if delay is not None:
            self.msgtask.start(delay)

    def take_focus(self):
        self.imgwin.grab_focus()


class GtkEventMixin(object):

    def __init__(self):
        imgwin = self.imgwin
        imgwin.set_can_focus(True)
        imgwin.set_focusable(True)
        #imgwin.set_focus_on_click(True)
        imgwin.connect("realize", self.map_event)
        event = Gtk.EventControllerFocus.new()
        event.connect("enter", self.focus_event, imgwin, True)
        imgwin.add_controller(event)
        event = Gtk.EventControllerFocus.new()
        event.connect("leave", self.focus_event, imgwin, False)
        imgwin.add_controller(event)
        event = Gtk.EventControllerMotion.new()
        event.connect("enter", self.enter_notify_event, imgwin)
        imgwin.add_controller(event)
        event = Gtk.EventControllerMotion.new()
        event.connect("leave", self.leave_notify_event, imgwin)
        imgwin.add_controller(event)
        event = Gtk.EventControllerMotion.new()
        event.connect("motion", self.motion_notify_event, imgwin)
        imgwin.add_controller(event)
        event = Gtk.GestureClick.new()
        event.connect("pressed", self.button_press_event, imgwin)
        # all buttons
        event.set_button(0)
        imgwin.add_controller(event)
        event = Gtk.GestureClick.new()
        event.connect("released", self.button_release_event, imgwin)
        event.set_button(0)
        imgwin.add_controller(event)
        event = Gtk.EventControllerKey.new()
        event.connect("key-pressed", self.key_press_event, imgwin)
        imgwin.add_controller(event)
        event = Gtk.EventControllerKey.new()
        event.connect("key-released", self.key_release_event, imgwin)
        imgwin.add_controller(event)
        event = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.BOTH_AXES |
            Gtk.EventControllerScrollFlags.KINETIC)
        event.connect("scroll", self.scroll_event, imgwin)
        imgwin.add_controller(event)

        # Set up widget as a drag and drop destination
        drop_tgt = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_tgt.connect('drop', self.on_dnd_drop)
        drop_tgt.connect('accept', self.on_dnd_accept)
        drop_tgt.connect('enter', self.on_dnd_enter)
        drop_tgt.connect('motion', self.on_dnd_motion)
        drop_tgt.connect('leave', self.on_dnd_leave)
        imgwin.add_controller(drop_tgt)

        # for gtk key handling
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
            'right': 'right',
            'left': 'left',
            'up': 'up',
            'down': 'down',
            'insert': 'insert',
            'delete': 'delete',
            'home': 'home',
            'end': 'end',
            'page_up': 'page_up',
            'page_down': 'page_down',
        }

        # Define cursors
        cursor_names = cursor_info.get_cursor_names()
        def_px_size = self.settings.get('default_cursor_length', 16)
        for curname in cursor_names:
            curinfo = cursor_info.get_cursor_info(curname)
            wd_px = int(curinfo.scale_width * def_px_size)
            ht_px = int(curinfo.scale_height * def_px_size)
            pt_x = int(curinfo.point_x_pct * wd_px)
            pt_y = int(curinfo.point_y_pct * ht_px)
            cur = self.make_cursor(curinfo.path, pt_x, pt_y,
                                   size=(wd_px, ht_px))
            self.define_cursor(curinfo.name, cur)

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     ):
            self.enable_callback(name)

    def transkey(self, keyname):
        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def get_key_table(self):
        return self._keytbl

    def map_event(self, widget):
        self.switch_cursor('pick')

        return self.make_callback('map')

    def focus_event(self, controller, widget, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, controller, x, y, widget):
        self.last_win_x, self.last_win_y = x, y

        self.check_cursor_location()

        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            widget.grab_focus()
        return self.make_callback('enter')

    def leave_notify_event(self, controller, widget):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, controller, keyval, keycode, state, widget):
        keyname = Gdk.keyval_name(keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_release_event(self, controller, keyval, keycode, state, widget):
        keyname = Gdk.keyval_name(keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-release', keyname)

    def button_press_event(self, gesture, whatsit, x, y, widget):
        self.last_win_x, self.last_win_y = x, y
        event_button = gesture.get_current_button()
        button = 0
        if event_button != 0:
            button |= 0x1 << (event_button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        return self.make_ui_callback_viewer(self, 'button-press', button,
                                            data_x, data_y)

    def button_release_event(self, gesture, whatsit, x, y, widget):
        self.last_win_x, self.last_win_y = x, y

        event_button = gesture.get_current_button()
        button = 0
        if event_button != 0:
            button |= 0x1 << (event_button - 1)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        return self.make_ui_callback_viewer(self, 'button-release', button,
                                            data_x, data_y)

    def motion_notify_event(self, motion, x, y, widget):
        button = 0
        self.last_win_x, self.last_win_y = x, y

        state = motion.get_current_event_state()
        if state & Gdk.ModifierType.BUTTON1_MASK:
            button |= 0x1
        elif state & Gdk.ModifierType.BUTTON2_MASK:
            button |= 0x2
        elif state & Gdk.ModifierType.BUTTON3_MASK:
            button |= 0x4
        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def scroll_event(self, controller, dx, dy, widget):
        event = controller.get_current_event()
        degrees, direction = GtkHelp.get_scroll_info(event)
        self.logger.debug("scroll deg=%f direction=%f" % (
            degrees, direction))

        # pointer location should have been recorded by motion_notify_event
        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'scroll', direction, degrees,
                                            data_x, data_y)

    def on_dnd_drop(self, drop_target, value, x, y):
        paths = [gdk_path.get_path() for gdk_path in value]
        self.logger.debug("dropped filename(s): %s" % (str(paths)))
        if len(paths) > 0:
            self.make_ui_callback_viewer(self, 'drag-drop', paths)

    def on_dnd_accept(self, drop, user_data):
        # TODO: double-check drop type
        return True

    def on_dnd_enter(self, drop_target, x, y):
        return Gdk.DragAction.COPY

    def on_dnd_motion(self, drop_target, x, y):
        return Gdk.DragAction.COPY

    def on_dnd_leave(self, user_data):
        # For possible future use
        pass


class ImageViewEvent(Mixins.UIMixin, GtkEventMixin, ImageViewGtk):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageViewGtk.__init__(self, logger=logger, rgbmap=rgbmap,
                              settings=settings, render=render)
        Mixins.UIMixin.__init__(self)
        GtkEventMixin.__init__(self)


class ImageViewZoom(ImageViewEvent):

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
                 render=None, bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, rgbmap=rgbmap,
                                settings=settings, render=render)

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
    """A Ginga viewer for viewing 2D slices of image data."""

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 render=None, bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger, settings=settings,
                               rgbmap=rgbmap, render=render,
                               bindmap=bindmap, bindings=bindings)

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas


class ScrolledView(Gtk.Grid):
    """A class that can take a viewer as a parameter and add scroll bars
    that respond to the pan/zoom levels.
    """

    def __init__(self, viewer, parent=None):
        self.viewer = viewer
        super(ScrolledView, self).__init__()

        GtkHelp.set_border_width(self, 0)
        self.set_row_spacing(0)
        self.set_column_spacing(0)

        self._adjusting = False
        self._scrolling = False
        self.pad = 20
        self.sb_thickness = 20
        self.rng_x = 100.0
        self.rng_y = 100.0
        self._bar_status = dict(horizontal='on', vertical='on')

        # reparent the viewer widget
        self.v_w = viewer.get_widget()
        self.attach(self.v_w, 0, 0, 1, 1)

        self.hsb = Gtk.Scrollbar(orientation=Gtk.Orientation.HORIZONTAL)
        self.hsb.set_size_request(-1, self.sb_thickness)
        adj = self.hsb.get_adjustment()
        adj.connect('value-changed', self._scroll_contents)
        self.vsb = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)
        self.vsb.set_size_request(self.sb_thickness, -1)
        adj = self.vsb.get_adjustment()
        adj.connect('value-changed', self._scroll_contents)

        self.viewer.add_callback('redraw', self._calc_scrollbars)
        self.viewer.add_callback('limits-set',
                                 lambda v, l: self._calc_scrollbars(v, 0))

        self._calc_scrollbars(self.viewer, 0)

    def get_widget(self):
        return self

    def _calc_scrollbars(self, viewer, whence):
        """Calculate and set the scrollbar handles from the pan and
        zoom positions.
        """
        if self._scrolling or whence > 0:
            return

        # flag that suppresses a cyclical callback
        self._adjusting = True
        try:
            res = self.viewer.calc_pan_pct(pad=self.pad)
            if res is None:
                return

            page_x, page_y = (float(res.thm_pct_x * 100),
                              float(res.thm_pct_y * 100))
            self.rng_x, self.rng_y = 100 - page_x, 100 - page_y
            val_x, val_y = (float(res.pan_pct_x * self.rng_x),
                            float((1.0 - res.pan_pct_y) * self.rng_y))

            upper_x, upper_y = 100.0, 100.0

            adj = self.hsb.get_adjustment()
            adj.configure(val_x, 0.0, upper_x, 1.0, page_x, page_x)
            self.hsb.set_adjustment(adj)
            adj = self.vsb.get_adjustment()
            adj.configure(val_y, 0.0, upper_y, 1.0, page_y, page_y)
            self.vsb.set_adjustment(adj)

        finally:
            self._adjusting = False
        return True

    def _scroll_contents(self, adj):
        """Called when the scroll bars are adjusted by the user.
        """
        if self._adjusting:
            return True

        self._scrolling = True
        try:
            pos_x = self.hsb.get_adjustment().get_value()
            pos_y = self.vsb.get_adjustment().get_value()

            pct_x = pos_x / float(self.rng_x)
            # invert Y pct because of orientation of scrollbar
            pct_y = 1.0 - (pos_y / float(self.rng_y))

            self.viewer.pan_by_pct(pct_x, pct_y, pad=self.pad)

            # This shouldn't be necessary, but seems to be
            self.viewer.redraw(whence=0)

        finally:
            self._scrolling = False

        return True

    def scroll_bars(self, horizontal='on', vertical='on'):
        # TODO: 'auto' setting working the same as 'on'--fix
        self._bar_status.update(dict(horizontal=horizontal,
                                     vertical=vertical))
        if horizontal in ('on', 'auto'):
            self.attach(self.hsb, 0, 1, 1, 1)
            self.hsb.show()
        elif horizontal == 'off':
            self.remove(self.hsb)
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (horizontal))

        if vertical in ('on', 'auto'):
            self.attach(self.vsb, 1, 0, 1, 1)
            self.vsb.show()
        elif vertical == 'off':
            self.remove(self.vsb)
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (vertical))

    def get_scroll_bars_status(self):
        return self._bar_status
