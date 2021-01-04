#
# ImageViewGtk.py -- a backend for Ginga using Gtk widgets and Cairo
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys
import os
import numpy as np

from ginga.gtk3w import GtkHelp
from ginga import ImageView, Mixins, Bindings
from ginga.util.paths import icondir
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

            imgwin.connect("draw", self.draw_event)
            imgwin.connect("configure-event", self.configure_event)
            # According to some things I've read, this is not recommended
            # for Gtk 3+, but not confirmed that it is truly not needed
            imgwin.set_events(Gdk.EventMask.EXPOSURE_MASK)
            # prevents some flickering
            imgwin.set_double_buffered(True)
            imgwin.set_app_paintable(True)
            # prevents extra redraws, because we manually redraw on a size
            # change
            imgwin.set_redraw_on_allocate(False)

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
        self.imgwin = imgwin
        self.imgwin.show_all()

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

        rect = self.imgwin.get_allocation()
        x, y, wd, ht = rect.x, rect.y, rect.width, rect.height
        self.configure_window(wd, ht)

    def choose_best_renderer(self):
        for name in self.possible_renderers:
            try:
                self.choose_renderer(name)
                self.logger.info("best renderer available is '{}'".format(name))
                return
            except Exception as e:
                # uncomment to troubleshoot
                ## self.logger.error("Error choosing renderer '{}': {}".format(name, e),
                ##                   exc_info=True)
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

        win = self.imgwin.get_window()
        if win is not None and self.surface is not None:
            imgwin_wd, imgwin_ht = self.get_window_size()

            self.imgwin.queue_draw_area(0, 0, imgwin_wd, imgwin_ht)

            # Process expose events right away so window is responsive
            # to scrolling
            win.process_updates(True)

    def draw_event(self, widget, cr):
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

    def configure_event(self, widget, event):
        # NOTE: this callback is only for the DrawingArea widget
        rect = widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height

        if self.surface is not None:
            # This is a workaround for a strange bug in Gtk 3
            # where we get multiple configure callbacks even though
            # the size hasn't changed.  We avoid creating a new surface
            # if there is an old surface with the exact same size.
            # This prevents some flickering of the display on focus events.
            wwd, wht = self.get_window_size()
            if (wwd == width) and (wht == height):
                return True

        self.logger.debug("allocation is %d,%d %dx%d" % (
            x, y, width, height))
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
        win = self.imgwin.get_window()
        if win is not None:
            win.set_cursor(cursor)

    def make_cursor(self, iconpath, x, y):
        cursor = GtkHelp.make_cursor(self.imgwin, iconpath, x, y)
        return cursor

    def center_cursor(self):
        if self.imgwin is None:
            return
        win = self.imgwin.get_window()
        if win is None:
            return
        win_x, win_y = self.get_center()
        _, scrn_x, scrn_y = win.get_origin()
        scrn_x, scrn_y = scrn_x + win_x, scrn_y + win_y

        # set the cursor position
        disp = win.get_display()
        screen = win.get_screen()
        disp.warp_pointer(screen, scrn_x, scrn_y)

    def position_cursor(self, data_x, data_y):
        if self.imgwin is None:
            return
        win = self.imgwin.get_window()
        if win is None:
            return
        win_x, win_y = self.get_canvas_xy(data_x, data_y)
        _, scrn_x, scrn_y = win.get_origin()
        scrn_x, scrn_y = scrn_x + win_x, scrn_y + win_y

        # set the cursor position
        disp = win.get_display()
        screen = win.get_screen()
        disp.warp_pointer(screen, scrn_x, scrn_y)

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
        imgwin.connect("map_event", self.map_event)
        imgwin.connect("focus_in_event", self.focus_event, True)
        imgwin.connect("focus_out_event", self.focus_event, False)
        imgwin.connect("enter_notify_event", self.enter_notify_event)
        imgwin.connect("leave_notify_event", self.leave_notify_event)
        imgwin.connect("motion_notify_event", self.motion_notify_event)
        imgwin.connect("button_press_event", self.button_press_event)
        imgwin.connect("button_release_event", self.button_release_event)
        imgwin.connect("key_press_event", self.key_press_event)
        imgwin.connect("key_release_event", self.key_release_event)
        imgwin.connect("scroll_event", self.scroll_event)
        mask = imgwin.get_events()
        imgwin.set_events(mask |
                          Gdk.EventMask.ENTER_NOTIFY_MASK |
                          Gdk.EventMask.LEAVE_NOTIFY_MASK |
                          Gdk.EventMask.FOCUS_CHANGE_MASK |
                          Gdk.EventMask.STRUCTURE_MASK |
                          Gdk.EventMask.BUTTON_PRESS_MASK |
                          Gdk.EventMask.BUTTON_RELEASE_MASK |
                          Gdk.EventMask.KEY_PRESS_MASK |
                          Gdk.EventMask.KEY_RELEASE_MASK |
                          Gdk.EventMask.POINTER_MOTION_MASK |
                          Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                          Gdk.EventMask.SCROLL_MASK)

        # Set up widget as a drag and drop destination
        targets = Gtk.TargetList.new([])
        targets.add_text_targets(GtkHelp.DND_TARGET_TYPE_TEXT)
        targets.add_uri_targets(GtkHelp.DND_TARGET_TYPE_URIS)
        imgwin.drag_dest_set(Gtk.DestDefaults.ALL, [],
                             Gdk.DragAction.COPY)
        imgwin.drag_dest_set_target_list(targets)

        imgwin.connect("drag-data-received", self.drop_event_cb)
        imgwin.connect("drag-motion", self.drag_motion_cb)
        imgwin.connect("drag-drop", self.drag_drop_cb)

        # @$%&^(_)*&^ gnome!!
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
        for curname, filename in (('pan', 'openHandCursor.png'),
                                  ('pick', 'thinCrossCursor.png')):
            path = os.path.join(icondir, filename)
            cur = self.make_cursor(path, 8, 8)
            self.define_cursor(curname, cur)

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

    def map_event(self, widget, event):
        #super(GtkEventMixin, self).configure_event(widget, event)
        self.configure_event(widget, event)

        self.switch_cursor('pick')

        return self.make_callback('map')

    def focus_event(self, widget, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, widget, event):
        self.last_win_x, self.last_win_y = event.x, event.y

        self.check_cursor_location()

        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            widget.grab_focus()
        return self.make_callback('enter')

    def leave_notify_event(self, widget, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, widget, event):
        # without this we do not get key release events if the focus
        # changes to another window
        #Gdk.keyboard_grab(widget.get_window(), False, event.time)
        #widget.grab_add()
        keyname = Gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_release_event(self, widget, event):
        #Gdk.keyboard_ungrab(event.time)
        #widget.grab_remove()
        keyname = Gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-release', keyname)

    def button_press_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-press', button,
                                            data_x, data_y)

    def button_release_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-release', button,
                                            data_x, data_y)

    def motion_notify_event(self, widget, event):
        button = 0
        if event.is_hint:
            tup = event.window.get_pointer()
            xx, x, y, state = tup
        else:
            x, y, state = event.x, event.y, event.state
        self.last_win_x, self.last_win_y = x, y

        if state & Gdk.ModifierType.BUTTON1_MASK:
            button |= 0x1
        elif state & Gdk.ModifierType.BUTTON2_MASK:
            button |= 0x2
        elif state & Gdk.ModifierType.BUTTON3_MASK:
            button |= 0x4
        # self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def scroll_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y

        # NOTE: for future use in distinguishing mouse wheel vs.
        # trackpad events
        dev = event.get_source_device()
        src = 'mouse'
        if dev is not None:
            _src = dev.get_source()
            if _src == Gdk.InputSource.TOUCHPAD:
                src == 'touchpad'

        degrees, direction = GtkHelp.get_scroll_info(event)
        self.logger.debug("scroll deg=%f direction=%f" % (
            degrees, direction))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'scroll', direction, degrees,
                                            data_x, data_y)

    def drag_drop_cb(self, widget, context, x, y, time):
        self.logger.debug("drag_drop_cb initiated")
        # initiates a drop
        success = False
        targets = context.list_targets()
        for mimetype in targets:
            if str(mimetype) in ("text/thumb", "text/plain", "text/uri-list"):
                Gdk.drop_reply(context, True, time)
                success = True
                return success

        self.logger.debug("dropped format type did not match known types")
        Gdk.drop_reply(context, False, time)
        return True

    def drag_motion_cb(self, widget, context, x, y, time):
        self.logger.debug("drag_motion_cb initiated")
        # checks whether a drop is possible
        targets = context.list_targets()
        for mimetype in targets:
            if str(mimetype) in ("text/thumb", "text/plain", "text/uri-list"):
                Gdk.drag_status(context, Gdk.DragAction.COPY, time)
                return True

        Gdk.drag_status(context, 0, time)
        self.logger.debug("drag_motion_cb done")
        return False

    def drop_event_cb(self, widget, context, x, y, selection, info, time):
        self.logger.debug("drop event initiated")

        if selection is None or selection.get_length() == 0:
            return

        paths = []
        if info == GtkHelp.DND_TARGET_TYPE_TEXT:
            # selection contains text
            buf = selection.get_text().strip()
            if '\r\n' in buf:
                # windows
                paths = buf.split('\r\n')
            else:
                paths = buf.split('\n')
        elif info == GtkHelp.DND_TARGET_TYPE_URIS:
            # selection contains URIs
            paths = selection.get_uris()
        else:
            self.logger.error("Dropped selection type ({}) is not recognized!".format(info))
            return

        self.logger.debug("dropped filename(s): %s" % (str(paths)))

        if len(paths) > 0:
            self.make_ui_callback_viewer(self, 'drag-drop', paths)

        return True


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


class ScrolledView(Gtk.Table):
    """A class that can take a viewer as a parameter and add scroll bars
    that respond to the pan/zoom levels.
    """

    def __init__(self, viewer, parent=None):
        self.viewer = viewer
        super(ScrolledView, self).__init__(rows=2, columns=2)

        self.set_border_width(0)
        self.set_row_spacings(0)
        self.set_col_spacings(0)

        self._adjusting = False
        self._scrolling = False
        self.pad = 20
        self.sb_thickness = 20
        self.rng_x = 100.0
        self.rng_y = 100.0
        self._bar_status = dict(horizontal='on', vertical='on')

        xoptions = Gtk.AttachOptions.EXPAND | Gtk.AttachOptions.FILL
        yoptions = Gtk.AttachOptions.EXPAND | Gtk.AttachOptions.FILL

        # reparent the viewer widget
        self.v_w = viewer.get_widget()
        self.attach(self.v_w, 0, 1, 0, 1,
                    xoptions=xoptions, yoptions=yoptions,
                    xpadding=0, ypadding=0)

        self.hsb = Gtk.HScrollbar()
        self.hsb.set_round_digits(4)
        self.hsb.set_size_request(-1, self.sb_thickness)
        self.hsb.connect('value-changed', self._scroll_contents)
        self.vsb = Gtk.VScrollbar()
        self.vsb.set_round_digits(4)
        self.vsb.set_size_request(self.sb_thickness, -1)
        self.vsb.connect('value-changed', self._scroll_contents)

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
            bd = self.viewer.get_bindings()
            res = bd.calc_pan_pct(self.viewer, pad=self.pad)
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
            pos_x = self.hsb.get_value()
            pos_y = self.vsb.get_value()

            pct_x = pos_x / float(self.rng_x)
            # invert Y pct because of orientation of scrollbar
            pct_y = 1.0 - (pos_y / float(self.rng_y))

            bd = self.viewer.get_bindings()
            bd.pan_by_pct(self.viewer, pct_x, pct_y, pad=self.pad)

            # This shouldn't be necessary, but seems to be
            self.viewer.redraw(whence=0)

        finally:
            self._scrolling = False

        return True

    def scroll_bars(self, horizontal='on', vertical='on'):
        self._bar_status.update(dict(horizontal=horizontal,
                                     vertical=vertical))
        if horizontal in ('on', 'auto'):
            self.attach(self.hsb, 0, 1, 1, 2,
                        xoptions=Gtk.AttachOptions.FILL, yoptions=0,
                        xpadding=0, ypadding=0)
            self.hsb.show()
        elif horizontal == 'off':
            self.remove(self.hsb)
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (horizontal))

        if vertical in ('on', 'auto'):
            self.attach(self.vsb, 1, 2, 0, 1,
                        xoptions=0, yoptions=Gtk.AttachOptions.FILL,
                        xpadding=0, ypadding=0)
            self.vsb.show()
        elif vertical == 'off':
            self.remove(self.vsb)
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (vertical))

    def get_scroll_bars_status(self):
        return self._bar_status
