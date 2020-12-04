#
# ImageViewMpl.py -- a backend for Ginga using a Matplotlib figure
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from io import BytesIO

# Matplotlib imports
import matplotlib
#from matplotlib.path import Path

from ginga import ImageView
from ginga import Mixins, Bindings

# NOTE: this import is necessary to register the 'ginga' projection
# used via matplotlib, even though the module is not directly
# referenced within this code
from . import transform  # noqa
from .CanvasRenderMpl import CanvasRenderer
from .MplHelp import Timer

# Override some matplotlib keyboard UI defaults
rc = matplotlib.rcParams
# TODO: figure out how to keep from overriding the user's desirable
# rcParams
rc.update(matplotlib.rcParamsDefault)
rc['keymap.fullscreen'] = 'f'    # toggling full screen
rc['keymap.home'] = 'home'       # home or reset mnemonic
rc['keymap.back'] = 'left'       # forward / backward keys to enable
rc['keymap.forward'] = 'right'   # left handed quick navigation
rc['keymap.pan'] = []            # pan mnemonic
rc['keymap.zoom'] = []           # zoom mnemonic
rc['keymap.save'] = 'ctrl+s'     # saving current figure
#rc['keymap.quit'] = 'ctrl+w'     # close the current figure
rc['keymap.grid'] = 'ctrl+g'     # switching on/off a grid in current axes
rc['keymap.yscale'] = []         # toggle scaling of y-axes ('log'/'linear')
rc['keymap.xscale'] = []         # toggle scaling of x-axes ('log'/'linear')
rc['keymap.all_axes'] = []       # enable all axes


MPL_V1 = matplotlib.__version__.startswith('1')


class ImageViewMplError(ImageView.ImageViewError):
    pass


class ImageViewMpl(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)
        # Our Figure
        self.figure = None
        # Our Axes
        self.ax_img = None
        self.ax_util = None
        # Holds the image on ax_img
        self.mpimage = None

        # NOTE: matplotlib manages it's Y coordinates by default with
        # the origin at the bottom (see base class)
        self.origin_upper = False

        self.img_fg = (1.0, 1.0, 1.0)
        self.img_bg = (0.5, 0.5, 0.5)

        self.in_axes = False
        # Matplotlib expects RGBA data for color images
        self.rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

        # For timing events
        self._msg_timer = None
        self._defer_timer = None

    def set_figure(self, figure):
        """Call this with the matplotlib Figure() object."""
        self.figure = figure

        ax = self.figure.add_axes((0, 0, 1, 1), frame_on=False,
                                  zorder=0.0,
                                  #viewer=self,
                                  #projection='ginga'
                                  )
        #ax = fig.add_subplot(111)
        self.ax_img = ax
        # We don't want the axes cleared every time plot() is called
        if MPL_V1:
            # older versions of matplotlib
            ax.hold(False)
        # TODO: is this needed, since frame_on == False?
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        #ax.patch.set_alpha(0.0)
        ax.patch.set_visible(False)
        #ax.autoscale(enable=True, tight=True)
        ax.autoscale(enable=False)

        # Add an overlapped axis for drawing graphics
        newax = self.figure.add_axes(self.ax_img.get_position(),
                                     sharex=ax, sharey=ax,
                                     frame_on=False,
                                     zorder=1.0,
                                     #viewer=self,
                                     #projection='ginga'
                                     )
        if MPL_V1:
            newax.hold(True)
        newax.autoscale(enable=False)
        newax.get_xaxis().set_visible(False)
        newax.get_yaxis().set_visible(False)
        self.ax_util = newax

        # Create timers
        self._msg_timer = None
        self._defer_timer = None

        if hasattr(figure.canvas, 'new_timer'):
            self._msg_timer = Timer(mplcanvas=figure.canvas)
            self._msg_timer.add_callback('expired',
                                         lambda timer: self.onscreen_message(None))

            self._defer_timer = Timer(mplcanvas=figure.canvas)
            self._defer_timer.add_callback('expired',
                                           lambda timer: self.delayed_redraw())

        canvas = figure.canvas
        if hasattr(canvas, 'viewer'):
            canvas.set_viewer(self)
        else:
            canvas.mpl_connect("resize_event", self._resize_cb)

        # Because we don't know if resize callback works with all backends
        left, bottom, wd, ht = self.ax_img.bbox.bounds
        self.configure_window(wd, ht)

    def get_figure(self):
        return self.figure

    def set_widget(self, canvas):
        if hasattr(canvas, 'viewer'):
            canvas.set_viewer(self)

    def get_widget(self):
        return self.figure.canvas

    def calculate_aspect(self, shape, extent):
        dx = abs(extent[1] - extent[0]) / float(shape[1])
        dy = abs(extent[3] - extent[2]) / float(shape[0])
        return dx / dy

    def render_image1(self, data, order, win_coord):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.

        NOTE: this version uses a Figure.FigImage to render the image.
        """
        self.logger.debug("redraw surface")
        if self.figure is None:
            return
        ## left, bottom, width, height = self.ax_img.bbox.bounds
        ## self._imgwin_wd, self._imgwin_ht = width, height

        # Grab the RGB array for the current image and place it in the
        # matplotlib figure axis
        dst_x = dst_y = 0

        # fill background color
        ## rect = self.figure.patch
        ## rect.set_facecolor(self.img_bg)

        # attempt 1: using a FigureImage (non-scaled)
        if self.mpimage is None:
            self.mpimage = self.figure.figimage(data, xo=dst_x, yo=dst_y,
                                                origin='upper')

        else:
            # note: this is not a typo--these offsets have a different
            # attribute name than in the constructor ('ox' vs. 'xo')
            self.mpimage.ox = dst_x
            self.mpimage.oy = dst_y
            self.mpimage.set_data(data)

    def render_image2(self, arr, order, win_coord):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.

        NOTE: this version renders the image in an Axes with imshow().
        """
        self.logger.debug("redraw surface")
        if self.figure is None:
            return

        ## left, bottom, width, height = self.ax_img.bbox.bounds
        ## self._imgwin_wd, self._imgwin_ht = width, height

        # Grab the RGB array for the current image and place it in the
        # matplotlib figure axis

        # Get the data extents
        x0, y0 = 0, 0
        y1, x1 = arr.shape[:2]
        flipx, flipy, swapxy = self.get_transforms()
        if swapxy:
            x0, x1, y0, y1 = y0, y1, x0, x1

        extent = (x0, x1, y1, y0)
        self.logger.debug("extent=%s" % (str(extent)))

        # Calculate aspect ratio
        aspect = self.calculate_aspect(arr.shape, extent)

        if self.mpimage is None:
            img = self.ax_img.imshow(arr, interpolation='none',
                                     origin="upper",
                                     vmin=0, vmax=255,
                                     extent=extent,
                                     aspect=aspect)
            self.mpimage = img

        else:
            self.mpimage.set_data(arr)
            self.ax_img.set_aspect(aspect)
            self.mpimage.set_extent(extent)
            #self.ax_img.relim()

    def render_image(self, data, order, win_coord):
        # Ugly, ugly hack copied from matplotlib.lines to cause line
        # objects to recompute their cached transformed_path
        # Other mpl artists don't seem to have this affliction
        for ax in self.figure.axes:
            if not (ax in (self.ax_img, self.ax_util)):
                if hasattr(ax, "lines"):
                    for line in ax.lines:
                        try:
                            line._transformed_path.invalidate()
                        except AttributeError:
                            pass

        # render_image1() currently seems a little faster
        if self.in_axes:
            self.render_image2(data, order, win_coord)
        else:
            self.render_image1(data, order, win_coord)

        # clear utility axis
        self.ax_util.cla()

        # force an update of the figure
        self.figure.canvas.draw()

        # Set the axis limits
        # TODO: should we do this only for those who have autoaxis=True?
        ## x0, y0, x1, y1 = self.get_datarect()
        ## for ax in self.figure.axes:
        ##     ax.set_xlim(x0, x1)
        ##     ax.set_ylim(y0, y1)

    def configure_window(self, width, height):
        self.configure(width, height)

    def _resize_cb(self, event):
        wd, ht = event.width, event.height
        self.logger.debug("canvas resized %dx%d" % (wd, ht))
        self.configure_window(wd, ht)

    def add_axes(self):
        ax = self.figure.add_axes(self.ax_img.get_position(),
                                  frame_on=False,
                                  zorder=1.0,
                                  viewer=self,
                                  projection='ginga')
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        return ax

    def get_png_image_as_buffer(self, output=None):
        """DO NOT USE: *** TO BE DEPRECATED ***
        Use get_rgb_image_as_buffer() instead.
        """
        return self.get_rgb_image_as_buffer(output=output, format='png')

    def get_rgb_image_as_buffer(self, output=None, format='png', quality=90):
        if self.figure is None:
            raise ImageViewMplError("No matplotlib figure defined")

        obuf = output
        if obuf is None:
            obuf = BytesIO()

        self.figure.savefig(obuf, format=format, pad_inches=0)
        if output is not None:
            return None
        return obuf

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        buf = self.get_rgb_image_as_buffer(format=format, quality=quality)
        return buf.getvalue()

    def update_widget(self):
        # force an update of the figure
        if self.figure is not None and self.figure.canvas is not None:
            self.figure.canvas.draw()
        pass

    def set_cursor(self, cursor):
        pass

    def onscreen_message(self, text, delay=None, redraw=True):
        if self._msg_timer is not None:
            self._msg_timer.stop()

        self.set_onscreen_message(text, redraw=redraw)

        if self._msg_timer is not None and delay is not None:
            self._msg_timer.start(delay)

    def reschedule_redraw(self, time_sec):
        if self._defer_timer is None:
            self.delayed_redraw()
            return

        self._defer_timer.stop()
        self._defer_timer.start(time_sec)


class ImageViewEvent(ImageViewMpl):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewMpl.__init__(self, logger=logger, rgbmap=rgbmap,
                              settings=settings)

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
            'right': 'right',
            'left': 'left',
            'up': 'up',
            'down': 'down',
            'insert': 'insert',
            'delete': 'delete',
            'home': 'home',
            'end': 'end',
            'pageup': 'page_up',
            'pagedown': 'page_down',
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

        connect = figure.canvas.mpl_connect
        #connect("map_event", self.map_event)
        #connect("focus_in_event", self.focus_event, True)
        #connect("focus_out_event", self.focus_event, False)
        connect("figure_enter_event", self.enter_notify_event)
        connect("figure_leave_event", self.leave_notify_event)
        #connect("axes_enter_event", self.enter_notify_event)
        #connect("axes_leave_event", self.leave_notify_event)
        connect("motion_notify_event", self.motion_notify_event)
        connect("button_press_event", self.button_press_event)
        connect("button_release_event", self.button_release_event)
        connect("key_press_event", self.key_press_event)
        connect("key_release_event", self.key_release_event)
        connect("scroll_event", self.scroll_event)

        # TODO: drag-drop event

    def transkey(self, keyname):
        self.logger.debug("matplotlib keyname='%s'" % (keyname))
        if keyname is None:
            return keyname
        try:
            key = keyname.lower()
            if 'shift+' in key:
                key = key.replace('shift+', '')
            if 'ctrl+' in key:
                key = key.replace('ctrl+', '')
            return self._keytbl[key]

        except KeyError:
            return keyname

    def get_key_table(self):
        return self._keytbl

    def focus_event(self, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, event):
        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            self.focus_event(event, True)
        return self.make_callback('enter')

    def leave_notify_event(self, event):
        self.logger.debug("leaving widget...")
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

    def button_press_event(self, event):
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if event.button in (1, 2, 3):
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-press', button,
                                            data_x, data_y)

    def button_release_event(self, event):
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if event.button in (1, 2, 3):
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-release', button,
                                            data_x, data_y)

    def motion_notify_event(self, event):
        button = 0
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y

        if event.button in (1, 2, 3):
            button |= 0x1 << (event.button - 1)
        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()
        self.logger.debug("motion event at DATA %dx%d" % (data_x, data_y))

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def scroll_event(self, event):
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y

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

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'scroll', direction, amount,
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
