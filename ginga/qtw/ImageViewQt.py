#
# ImageViewQt.py -- a backend for Ginga using Qt widgets
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import tempfile
from functools import partial

import numpy as np

from ginga import ImageView, Mixins, Bindings
from ginga.util.paths import icondir
from ginga.qtw.QtHelp import (QtGui, QtCore, QImage, QPixmap, QCursor,
                              QPainter, QOpenGLWidget, QSurfaceFormat,
                              Timer, get_scroll_info, get_painter)

from .CanvasRenderQt import CanvasRenderer

have_opengl = False
try:
    from ginga.opengl.CanvasRenderGL import CanvasRenderer as OpenGLRenderer
    from ginga.opengl.GlHelp import get_transforms
    from ginga.opengl.glsl import req

    have_opengl = True
except ImportError:
    pass

# set to True to debug window painting
DEBUG_MODE = False


class ImageViewQtError(ImageView.ImageViewError):
    pass


class RenderGraphicsView(QtGui.QGraphicsView):

    def __init__(self, *args, **kwdargs):
        super(RenderGraphicsView, self).__init__(*args, **kwdargs)

        self.viewer = None
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

    def drawBackground(self, painter, rect):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        pixmap = self.viewer.pixmap
        if pixmap is None:
            return
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1 + 1
        height = y2 - y1 + 1

        # redraw the screen from backing pixmap
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, pixmap, rect)

    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1 + 1
        height = y2 - y1 + 1

        self.viewer.configure_window(width, height)

    def sizeHint(self):
        width, height = 300, 300
        if self.viewer is not None:
            width, height = self.viewer.get_desired_size()
        return QtCore.QSize(width, height)


class RenderWidget(QtGui.QWidget):

    def __init__(self, *args, **kwdargs):
        super(RenderWidget, self).__init__(*args, **kwdargs)

        self.viewer = None
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        pixmap = self.viewer.pixmap
        if pixmap is None:
            return
        rect = event.rect()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1 + 1
        height = y2 - y1 + 1

        # redraw the screen from backing pixmap
        painter = QPainter(self)
        #painter = get_painter(self)
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, pixmap, rect)
        if DEBUG_MODE:
            qimage = pixmap.toImage()
            save_debug_image(qimage, 'final_image.png', format='png')

    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1 + 1
        height = y2 - y1 + 1

        self.viewer.configure_window(width, height)
        #self.update()

    def sizeHint(self):
        width, height = 300, 300
        if self.viewer is not None:
            width, height = self.viewer.get_desired_size()
        return QtCore.QSize(width, height)


class RenderGLWidget(QOpenGLWidget):

    @staticmethod
    def _on_destroyed(d):
        viewer, d['viewer'] = d['viewer'], None
        viewer.imgwin = None

    def __init__(self, *args, **kwdargs):
        QOpenGLWidget.__init__(self, *args, **kwdargs)

        self.viewer = None

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.destroyed.connect(partial(RenderGLWidget._on_destroyed,
                                       self.__dict__))

        # ensure we are using correct version of opengl
        fmt = QSurfaceFormat()
        fmt.setVersion(req.major, req.minor)
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        #fmt.setDefaultFormat(fmt)
        self.setFormat(fmt)

    def initializeGL(self):
        self.viewer.renderer.gl_initialize()

    def resizeGL(self, width, height):
        self.viewer.configure_window(width, height)

    def paintGL(self):
        self.viewer.renderer.gl_paint()

    def sizeHint(self):
        width, height = 300, 300
        if self.viewer is not None:
            width, height = self.viewer.get_desired_size()
        return QtCore.QSize(width, height)


class ImageViewQt(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)

        if render is None:
            render = self.t_.get('render_widget', 'widget')
        self.wtype = render
        if self.wtype == 'widget':
            self.imgwin = RenderWidget()
        elif self.wtype == 'scene':
            self.scene = QtGui.QGraphicsScene()
            self.imgwin = RenderGraphicsView(self.scene)
        elif self.wtype == 'opengl':
            if not have_opengl:
                raise ImageViewQtError("Please install 'pyopengl' to use render: '%s'" % (render))
            self.imgwin = RenderGLWidget()
        else:
            raise ImageViewQtError("Undefined render type: '%s'" % (render))
        self.imgwin.viewer = self
        self.pixmap = None
        self.qimg_fmt = QImage.Format_RGB32
        # find out optimum format for backing store
        #self.qimg_fmt = QPixmap(1, 1).toImage().format()

        if self.wtype == 'opengl':
            if not have_opengl:
                raise ValueError("OpenGL imports failed")
            self.rgb_order = 'RGBA'
            self.renderer = OpenGLRenderer(self)
            # we replace some transforms in the catalog for OpenGL rendering
            self.tform = get_transforms(self)
        else:
            # Qt needs this to be in BGR(A)
            self.rgb_order = 'BGRA'
            # default renderer is Qt one
            self.renderer = CanvasRenderer(self, surface_type='qpixmap')

        self.msgtimer = Timer()
        self.msgtimer.add_callback('expired',
                                   lambda timer: self.onscreen_message_off())

        # For optomized redrawing
        self._defer_task = Timer()
        self._defer_task.add_callback('expired',
                                      lambda timer: self.delayed_redraw())

    def get_widget(self):
        return self.imgwin

    def configure_window(self, width, height):
        self.logger.debug("window size reconfigured to %dx%d" % (
            width, height))

        if hasattr(self, 'scene'):
            # By default, a QGraphicsView comes with a 1-pixel margin
            # You will get scrollbars unless you account for this
            # See http://stackoverflow.com/questions/3513788/qt-qgraphicsview-without-scrollbar
            width, height = width - 2, height - 2
            self.scene.setSceneRect(1, 1, width - 2, height - 2)

        # tell renderer about our new size
        #self.renderer.resize((width, height))

        if self.wtype == 'opengl':
            pass

        elif isinstance(self.renderer.surface, QPixmap):
            # optimization when Qt is used as the renderer:
            # renderer surface is already a QPixmap
            self.pixmap = self.renderer.surface

        else:
            # If we need to build a new pixmap do it here.  We allocate one
            # twice as big as necessary to prevent having to reinstantiate it
            # all the time.  On Qt this causes unpleasant flashing in the display.
            if ((self.pixmap is None) or (self.pixmap.width() < width) or
                    (self.pixmap.height() < height)):
                pixmap = QPixmap(width * 2, height * 2)
                self.pixmap = pixmap

        self.configure(width, height)

    def get_rgb_image_as_widget(self):
        arr = self.renderer.get_surface_as_array(order=self.rgb_order)
        image = self._get_qimage(arr, self.qimg_fmt)
        return image

    def get_plain_image_as_widget(self):
        """Returns a QImage of the drawn images.
        Does not include overlaid graphics.
        """
        arr = self.getwin_array(order=self.rgb_order)
        image = self._get_qimage(arr, self.qimg_fmt)
        return image

    def save_plain_image_as_file(self, filepath, format='png', quality=90):
        """Does not include overlaid graphics.
        """
        qimg = self.get_plain_image_as_widget()
        qimg.save(filepath, format=format, quality=quality)

    def reschedule_redraw(self, time_sec):
        self._defer_task.stop()
        self._defer_task.start(time_sec)

    def make_context_current(self):
        ctx = self.imgwin.context()
        self.imgwin.makeCurrent()
        return ctx

    def prepare_image(self, cvs_img, cache, whence):
        self.renderer.prepare_image(cvs_img, cache, whence)

    def update_widget(self):
        if self.imgwin is None:
            return

        if self.wtype == 'opengl':
            pass

        elif isinstance(self.renderer.surface, QPixmap):
            # optimization when Qt is used as the renderer:
            # if renderer surface is already an offscreen QPixmap
            # then we can update the window directly from it
            if self.pixmap is not self.renderer.surface:
                self.pixmap = self.renderer.surface

            if DEBUG_MODE:
                qimage = self.pixmap.toImage()
                save_debug_image(qimage, 'offscreen_image.png', format='png')

        else:
            if self.pixmap is None:
                return

            if isinstance(self.renderer.surface, QImage):
                # optimization when Qt is used as the renderer:
                # renderer surface is already a QImage
                qimage = self.renderer.surface

            else:
                # otherwise, get the render surface as an array and
                # convert to a QImage
                try:
                    arr = self.renderer.get_surface_as_array(order='BGRA')
                    qimage = self._get_qimage(arr, QImage.Format_RGB32)

                except Exception as e:
                    self.logger.error("Error from renderer: %s" % (str(e)))
                    return

            # copy image from renderer to offscreen pixmap
            painter = get_painter(self.pixmap)

            size = self.pixmap.size()
            width, height = size.width(), size.height()

            # draw image data from buffer to offscreen pixmap
            painter.drawImage(QtCore.QRect(0, 0, width, height),
                              qimage,
                              QtCore.QRect(0, 0, width, height))

            if DEBUG_MODE:
                save_debug_image(qimage, 'offscreen_image.png', format='png')

        self.logger.debug("updating window from pixmap")
        if hasattr(self, 'scene'):
            imgwin_wd, imgwin_ht = self.get_window_size()
            self.scene.invalidate(0, 0, imgwin_wd, imgwin_ht,
                                  QtGui.QGraphicsScene.BackgroundLayer)
        else:
            self.imgwin.update()

    def _get_qimage(self, rgb_data, format):
        rgb_data = np.ascontiguousarray(rgb_data)
        ht, wd, channels = rgb_data.shape

        result = QImage(rgb_data.data, wd, ht, format)
        # Need to hang on to a reference to the array
        result.ndarray = rgb_data
        return result

    def set_cursor(self, cursor):
        if self.imgwin is not None:
            self.imgwin.setCursor(cursor)

    def make_cursor(self, iconpath, x, y):
        image = QImage()
        image.load(iconpath)
        pm = QPixmap(image)
        return QCursor(pm, x, y)

    def center_cursor(self):
        if self.imgwin is None:
            return
        win_x, win_y = self.get_center()
        w_pt = QtCore.QPoint(win_x, win_y)
        s_pt = self.imgwin.mapToGlobal(w_pt)

        # set the cursor position
        cursor = self.imgwin.cursor()
        cursor.setPos(s_pt)

    def position_cursor(self, data_x, data_y):
        if self.imgwin is None:
            return
        win_x, win_y = self.get_canvas_xy(data_x, data_y)
        w_pt = QtCore.QPoint(win_x, win_y)
        s_pt = self.imgwin.mapToGlobal(w_pt)

        # set the cursor position
        cursor = self.imgwin.cursor()
        cursor.setPos(s_pt)

    def make_timer(self):
        return Timer()

    def onscreen_message(self, text, delay=None, redraw=True):
        self.msgtimer.stop()
        self.set_onscreen_message(text, redraw=redraw)
        if delay is not None:
            self.msgtimer.start(delay)

    def take_focus(self):
        self.imgwin.setFocus()


class RenderMixin(object):

    def showEvent(self, event):
        self.viewer.map_event(self, event)

    def focusInEvent(self, event):
        self.viewer.focus_event(self, event, True)

    def focusOutEvent(self, event):
        self.viewer.focus_event(self, event, False)

    def enterEvent(self, event):
        self.viewer.enter_notify_event(self, event)

    def leaveEvent(self, event):
        self.viewer.leave_notify_event(self, event)

    def keyPressEvent(self, event):
        # without this we do not get key release events if the focus
        # changes to another window
        #self.grabKeyboard()
        self.viewer.key_press_event(self, event)

    def keyReleaseEvent(self, event):
        #self.releaseKeyboard()
        self.viewer.key_release_event(self, event)

    def mousePressEvent(self, event):
        self.viewer.button_press_event(self, event)

    def mouseReleaseEvent(self, event):
        self.viewer.button_release_event(self, event)

    def mouseMoveEvent(self, event):
        self.viewer.motion_notify_event(self, event)

    def wheelEvent(self, event):
        self.viewer.scroll_event(self, event)

    def event(self, event):
        # This method is a hack necessary to support trackpad gestures
        # on Qt4 because it does not support specific method overrides.
        # Instead we have to override the generic event handler, look
        # explicitly for gesture events.
        if event.type() == QtCore.QEvent.Gesture:
            return self.viewer.gesture_event(self, event)
        return super(RenderMixin, self).event(event)

    def dragEnterEvent(self, event):
        #if event.mimeData().hasFormat('text/plain'):
        #    event.accept()
        #else:
        #    event.ignore()
        event.accept()

    def dragMoveEvent(self, event):
        #if event.mimeData().hasFormat('text/plain'):
        #    event.accept()
        #else:
        #    event.ignore()
        event.accept()

    def dropEvent(self, event):
        self.viewer.drop_event(self, event)


class RenderWidgetZoom(RenderMixin, RenderWidget):
    pass


class RenderGraphicsViewZoom(RenderMixin, RenderGraphicsView):
    pass


class RenderGLWidgetZoom(RenderMixin, RenderGLWidget):
    pass


class QtEventMixin(object):

    def __init__(self):
        imgwin = self.imgwin
        imgwin.setFocusPolicy(QtCore.Qt.FocusPolicy(
                              QtCore.Qt.TabFocus |
                              QtCore.Qt.ClickFocus |
                              QtCore.Qt.StrongFocus |
                              QtCore.Qt.WheelFocus))
        imgwin.setMouseTracking(True)
        imgwin.setAcceptDrops(True)
        # enable gesture handling
        imgwin.grabGesture(QtCore.Qt.PinchGesture)
        # Some of these are not well supported (read "just don't get
        # recognized") by Qt and aren't the same as standard platform
        # trackpad gestures anyway
        #imgwin.grabGesture(QtCore.Qt.PanGesture)
        #imgwin.grabGesture(QtCore.Qt.SwipeGesture)
        #imgwin.grabGesture(QtCore.Qt.TapGesture)
        #imgwin.grabGesture(QtCore.Qt.TapAndHoldGesture)

        # Define cursors
        for curname, filename in (('pan', 'openHandCursor.png'),
                                  ('pick', 'thinCrossCursor.png')):
            path = os.path.join(icondir, filename)
            cur = self.make_cursor(path, 8, 8)
            self.define_cursor(curname, cur)

        # @$%&^(_)*&^ qt!!
        self._keytbl = {
            '`': 'backquote',
            '"': 'doublequote',
            "'": 'singlequote',
            '\\': 'backslash',
            ' ': 'space',
        }
        self._fnkeycodes = [QtCore.Qt.Key_F1, QtCore.Qt.Key_F2,
                            QtCore.Qt.Key_F3, QtCore.Qt.Key_F4,
                            QtCore.Qt.Key_F5, QtCore.Qt.Key_F6,
                            QtCore.Qt.Key_F7, QtCore.Qt.Key_F8,
                            QtCore.Qt.Key_F9, QtCore.Qt.Key_F10,
                            QtCore.Qt.Key_F11, QtCore.Qt.Key_F12,
                            ]

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'pan',  # 'swipe', 'tap'
                     ):
            self.enable_callback(name)

    def transkey(self, keycode, keyname):
        self.logger.debug("keycode=%d keyname='%s'" % (
            keycode, keyname))
        if keycode in [QtCore.Qt.Key_Control]:
            return 'control_l'
        if keycode in [QtCore.Qt.Key_Shift]:
            return 'shift_l'
        if keycode in [QtCore.Qt.Key_Alt]:
            return 'alt_l'
        if keycode in [QtCore.Qt.Key_Up]:
            return 'up'
        if keycode in [QtCore.Qt.Key_Down]:
            return 'down'
        if keycode in [QtCore.Qt.Key_Left]:
            return 'left'
        if keycode in [QtCore.Qt.Key_Right]:
            return 'right'
        if keycode in [QtCore.Qt.Key_PageUp]:
            return 'page_up'
        if keycode in [QtCore.Qt.Key_PageDown]:
            return 'page_down'
        if keycode in [QtCore.Qt.Key_Home]:
            return 'home'
        if keycode in [QtCore.Qt.Key_End]:
            return 'end'
        if keycode in [QtCore.Qt.Key_Insert]:
            return 'insert'
        if keycode in [QtCore.Qt.Key_Delete]:
            return 'delete'
        # if keycode in [QtCore.Qt.Key_Super_L]:
        #     return 'super_l'
        # if keycode in [QtCore.Qt.Key_Super_R]:
        #     return 'super_r'
        if keycode in [QtCore.Qt.Key_Escape]:
            return 'escape'
        # Control key on Mac keyboards and "Windows" key under Linux
        if keycode in [16777250]:
            return 'meta_right'
        if keycode in self._fnkeycodes:
            index = self._fnkeycodes.index(keycode)
            return 'f%d' % (index + 1)

        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def get_key_table(self):
        return self._keytbl

    def map_event(self, widget, event):
        rect = widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1 + 1
        height = y2 - y1 + 1

        self.switch_cursor('pick')

        self.configure_window(width, height)
        return self.make_callback('map')

    def focus_event(self, widget, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def _get_pos(self, event):
        if hasattr(event, 'position'):
            pos = event.position()
            return pos.x(), pos.y()
        else:
            pos = event.pos()
            return pos.x(), pos.y()

    def enter_notify_event(self, widget, event):
        self.last_win_x, self.last_win_y = self._get_pos(event)
        self.check_cursor_location()

        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            widget.setFocus()
        return self.make_callback('enter')

    def leave_notify_event(self, widget, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, widget, event):
        keyname = event.key()
        keyname2 = "%s" % (event.text())
        keyname = self.transkey(keyname, keyname2)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_release_event(self, widget, event):
        keyname = event.key()
        keyname2 = "%s" % (event.text())
        keyname = self.transkey(keyname, keyname2)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-release', keyname)

    def button_press_event(self, widget, event):
        buttons = event.buttons()
        x, y = self._get_pos(event)
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MiddleButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
        if buttons & QtCore.Qt.BackButton:
            button |= 0x8
        if buttons & QtCore.Qt.ForwardButton:
            button |= 0x10
        self.logger.debug("button down event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-press', button,
                                            data_x, data_y)

    def button_release_event(self, widget, event):
        # note: for mouseRelease this needs to be button(), not buttons()!
        buttons = event.button()
        x, y = self._get_pos(event)
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MiddleButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
        if buttons & QtCore.Qt.BackButton:
            button |= 0x8
        if buttons & QtCore.Qt.ForwardButton:
            button |= 0x10

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'button-release', button,
                                            data_x, data_y)

    def motion_notify_event(self, widget, event):

        if self.is_redraw_pending():
            # NOTE: this hack works around a bug in Qt5 (ver < 5.6.2)
            # where mouse motion events are not compressed properly,
            # causing many events to build up in the queue and slowing
            # down the viewer due to each one forcing a redraw.
            # This test tells us there is a deferred redraw waiting;
            # discard any motion events until the redraw happens.
            return True

        buttons = event.buttons()
        x, y = self._get_pos(event)
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MiddleButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def scroll_event(self, widget, event):
        x, y = self._get_pos(event)
        # accept event here so it doesn't get propagated to parent
        event.accept()
        self.last_win_x, self.last_win_y = x, y

        data_x, data_y = self.check_cursor_location()

        # NOTE: for future use in distinguishing mouse wheel vs.
        # trackpad events
        src = 'wheel'
        if hasattr(event, 'source'):
            # Qt5 only, it seems
            _src = event.source()
            if _src == QtCore.Qt.MouseEventNotSynthesized:
                src = 'wheel'
            else:
                src = 'trackpad'  # noqa
                point = event.pixelDelta()
                dx, dy = point.x(), point.y()

                # Synthesize this as a pan gesture event
                self.make_ui_callback_viewer(self, 'pan', 'start', 0, 0)
                self.make_ui_callback_viewer(self, 'pan', 'move', dx, dy)
                return self.make_ui_callback_viewer(self, 'pan', 'stop', 0, 0)

        num_degrees, direction = get_scroll_info(event)
        self.logger.debug("scroll deg={} direction={}".format(
            num_degrees, direction))

        return self.make_ui_callback_viewer(self, 'scroll', direction,
                                            num_degrees, data_x, data_y)

    def gesture_event(self, widget, event):
        gesture = event.gestures()[0]
        state = gesture.state()
        if state == QtCore.Qt.GestureStarted:
            gstate = 'start'
        elif state == QtCore.Qt.GestureUpdated:
            gstate = 'move'
        elif state == QtCore.Qt.GestureFinished:
            gstate = 'stop'
        elif state == QtCore.Qt.GestureCancelled:
            gstate = 'stop'

        # dispatch on gesture type
        gtype = event.gesture(QtCore.Qt.SwipeGesture)
        if gtype:
            self.gs_swiping(event, gesture, gstate)
            return True
        gtype = event.gesture(QtCore.Qt.PanGesture)
        if gtype:
            self.gs_panning(event, gesture, gstate)
            return True
        gtype = event.gesture(QtCore.Qt.PinchGesture)
        if gtype:
            self.gs_pinching(event, gesture, gstate)
            return True
        # gtype = event.gesture(QtCore.Qt.TapGesture)
        # if gtype:
        #     self.gs_tapping(event, gesture, gstate)
        #     return True
        # gtype = event.gesture(QtCore.Qt.TapAndHoldGesture)
        # if gtype:
        #     self.gs_pressing(event, gesture, gstate)
        #     return True
        return True

    def gs_swiping(self, event, gesture, gstate):
        if gstate == 'stop':
            _hd = gesture.horizontalDirection()
            hdir = None
            if _hd == QtGui.QSwipeGesture.Left:
                hdir = 'left'
            elif _hd == QtGui.QSwipeGesture.Right:
                hdir = 'right'

            _vd = gesture.verticalDirection()
            vdir = None
            if _vd == QtGui.QSwipeGesture.Up:
                vdir = 'up'
            elif _vd == QtGui.QSwipeGesture.Down:
                vdir = 'down'

            self.logger.debug("swipe gesture hdir=%s vdir=%s" % (
                hdir, vdir))

            return self.make_ui_callback_viewer(self, 'swipe', gstate,
                                                hdir, vdir)

    def gs_pinching(self, event, gesture, gstate):
        rot = gesture.rotationAngle()
        scale = gesture.scaleFactor()
        self.logger.debug("pinch gesture rot=%f scale=%f state=%s" % (
            rot, scale, gstate))

        return self.make_ui_callback_viewer(self, 'pinch', gstate, rot, scale)

    def gs_panning(self, event, gesture, gstate):
        d = gesture.delta()
        dx, dy = d.x(), d.y()
        self.logger.debug("pan gesture dx=%f dy=%f state=%s" % (
            dx, dy, gstate))

        return self.make_ui_callback_viewer(self, 'pan', gstate, dx, dy)

    def gs_tapping(self, event, gesture, gstate):
        self.logger.debug("tapping gesture state=%s" % (
            gstate))

    def gs_pressing(self, event, gesture, gstate):
        self.logger.debug("pressing gesture state=%s" % (
            gstate))

    def drop_event(self, widget, event):
        dropdata = event.mimeData()
        formats = list(map(str, list(dropdata.formats())))
        self.logger.debug("available formats of dropped data are %s" % (
            formats))
        if "text/thumb" in formats:
            thumbstr = str(dropdata.data("text/thumb"), encoding='ascii')
            data = [thumbstr]
            self.logger.debug("dropped thumb(s): %s" % (str(data)))
        elif dropdata.hasUrls():
            urls = list(dropdata.urls())
            data = [str(url.toString()) for url in urls]
            self.logger.debug("dropped filename(s): %s" % (str(data)))
        elif "text/plain" in formats:
            data = [dropdata.text()]
            self.logger.debug("dropped filename(s): %s" % (str(data)))
        else:
            # No format that we understand--just pass it along
            ## data = dropdata.data(formats[0])
            ## self.logger.debug("dropped data of len %d" % (len(data)))
            event.setAccepted(False)
            return

        event.setAccepted(True)
        #event.acceptProposedAction()
        self.make_ui_callback_viewer(self, 'drag-drop', data)


class ImageViewEvent(QtEventMixin, ImageViewQt):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageViewQt.__init__(self, logger=logger, rgbmap=rgbmap,
                             settings=settings, render=render)

        # replace the widget our parent provided
        if self.wtype == 'opengl':
            imgwin = RenderGLWidgetZoom()
        elif self.wtype == 'scene':
            imgwin = RenderGraphicsViewZoom()
            imgwin.setScene(self.scene)
        else:
            imgwin = RenderWidgetZoom()

        imgwin.viewer = self
        self.imgwin = imgwin

        QtEventMixin.__init__(self)


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
                 render='widget',
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, settings=settings,
                                rgbmap=rgbmap, render=render)
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
    """A Ginga viewer for viewing 2D slices of image data."""

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 render='widget',
                 bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger, settings=settings,
                               rgbmap=rgbmap, render=render,
                               bindmap=bindmap, bindings=bindings)

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas


class ScrolledView(QtGui.QAbstractScrollArea):
    """A class that can take a viewer as a parameter and add scroll bars
    that respond to the pan/zoom levels.
    """

    def __init__(self, viewer, parent=None):
        self.viewer = viewer
        super(ScrolledView, self).__init__(parent=parent)

        self._bar_status = dict(horizontal='on', vertical='on')
        # the window jiggles annoyingly as the scrollbar is alternately
        # shown and hidden if we use the default "as needed" policy, so
        # default to always showing them (user can change this after
        # calling the constructor, if desired)
        self.scroll_bars(horizontal='on', vertical='on')

        self._adjusting = False
        self._scrolling = False
        self.pad = 20
        self.range_h = 10000
        self.range_v = 10000
        self.upper_h = self.range_h
        self.upper_v = self.range_v

        # reparent the viewer widget
        vp = self.viewport()
        self.v_w = viewer.get_widget()
        self.v_w.setParent(vp)

        hsb = self.horizontalScrollBar()
        hsb.setTracking(True)
        hsb.setRange(0, self.upper_h)
        hsb.setSingleStep(1)
        vsb = self.verticalScrollBar()
        vsb.setRange(0, self.upper_v)
        vsb.setSingleStep(1)
        vsb.setTracking(True)

        self.viewer.add_callback('redraw', self._calc_scrollbars)
        self.viewer.add_callback('limits-set',
                                 lambda v, l: self._calc_scrollbars(v, 0))

    def get_widget(self):
        return self

    def resizeEvent(self, event):
        """Override from QAbstractScrollArea.
        Resize the viewer widget when the viewport is resized."""
        vp = self.viewport()
        rect = vp.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1 + 1
        height = y2 - y1 + 1

        self.v_w.resize(width, height)

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

            hsb = self.horizontalScrollBar()
            vsb = self.verticalScrollBar()

            page_h, page_v = (int(round(res.thm_pct_x * self.range_h)),
                              int(round(res.thm_pct_y * self.range_v)))
            hsb.setPageStep(page_h)
            vsb.setPageStep(page_v)

            upper_h = max(1, self.range_h - page_h)
            upper_v = max(1, self.range_v - page_v)
            hsb.setRange(0, upper_h)
            vsb.setRange(0, upper_v)
            self.upper_h, self.upper_v = upper_h, upper_v

            val_h, val_v = (int(round(res.pan_pct_x * self.upper_h)),
                            int(round((1.0 - res.pan_pct_y) * self.upper_v)))
            hsb.setValue(val_h)
            vsb.setValue(val_v)

        finally:
            self._adjusting = False

    def scrollContentsBy(self, dx, dy):
        """Override from QAbstractScrollArea.
        Called when the scroll bars are adjusted by the user.
        """
        if self._adjusting:
            return

        self._scrolling = True
        try:
            bd = self.viewer.get_bindings()
            res = bd.calc_pan_pct(self.viewer, pad=self.pad)
            if res is None:
                return
            pct_x, pct_y = res.pan_pct_x, res.pan_pct_y

            # Only adjust pan setting for axes that have changed
            if dx != 0:
                hsb = self.horizontalScrollBar()
                pos_x = float(hsb.value())
                pct_x = pos_x / float(self.upper_h)
            if dy != 0:
                vsb = self.verticalScrollBar()
                pos_y = float(vsb.value())
                # invert Y pct because of orientation of scrollbar
                pct_y = 1.0 - (pos_y / float(self.upper_v))

            bd = self.viewer.get_bindings()
            bd.pan_by_pct(self.viewer, pct_x, pct_y, pad=self.pad)

            # This shouldn't be necessary, but seems to be
            self.viewer.redraw(whence=0)

        finally:
            self._scrolling = False

    def scroll_bars(self, horizontal='on', vertical='on'):
        self._bar_status.update(dict(horizontal=horizontal,
                                     vertical=vertical))
        if horizontal == 'on':
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        elif horizontal == 'off':
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        elif horizontal == 'auto':
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (horizontal))

        if vertical == 'on':
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        elif vertical == 'off':
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        elif vertical == 'auto':
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (vertical))

    def get_scroll_bars_status(self):
        return self._bar_status


def save_debug_image(qimage, filename, format='png'):
    path = os.path.join(tempfile.gettempdir(), filename)
    qimage.save(path, format=format)
