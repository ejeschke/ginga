#
# ImageViewQt.py -- a backend for Ginga using Qt widgets
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import math
import numpy
from io import BytesIO

from ginga.qtw.QtHelp import QtGui, QtCore, QFont, QColor, QImage, \
     QPixmap, QCursor, QPainter, have_pyqt5, Timer, get_scroll_info
from ginga import ImageView, Mixins, Bindings
import ginga.util.six as six
from ginga.util.six.moves import map, zip
from ginga.qtw.CanvasRenderQt import CanvasRenderer
from ginga.util.paths import icondir


class ImageViewQtError(ImageView.ImageViewError):
    pass


class RenderGraphicsView(QtGui.QGraphicsView):

    def __init__(self, *args, **kwdargs):
        super(RenderGraphicsView, self).__init__(*args, **kwdargs)

        self.viewer = None
        self.pixmap = None

    def drawBackground(self, painter, rect):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        if not self.pixmap:
            return
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        # redraw the screen from backing pixmap
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, self.pixmap, rect)

    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        self.viewer.configure_window(width, height)

    def sizeHint(self):
        width, height = 300, 300
        if self.viewer is not None:
            width, height = self.viewer.get_desired_size()
        return QtCore.QSize(width, height)

    def set_pixmap(self, pixmap):
        self.pixmap = pixmap


class RenderWidget(QtGui.QWidget):

    def __init__(self, *args, **kwdargs):
        super(RenderWidget, self).__init__(*args, **kwdargs)

        self.viewer = None
        self.pixmap = None
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        if not self.pixmap:
            return
        rect = event.rect()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        # redraw the screen from backing pixmap
        painter = QPainter(self)
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, self.pixmap, rect)

    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        self.viewer.configure_window(width, height)
        #self.update()

    def sizeHint(self):
        width, height = 300, 300
        if self.viewer is not None:
            width, height = self.viewer.get_desired_size()
        return QtCore.QSize(width, height)

    def set_pixmap(self, pixmap):
        self.pixmap = pixmap


class ImageViewQt(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)

        if render is None:
            render = 'widget'
        self.wtype = render
        if self.wtype == 'widget':
            self.imgwin = RenderWidget()
        elif self.wtype == 'scene':
            self.scene = QtGui.QGraphicsScene()
            self.imgwin = RenderGraphicsView(self.scene)
        else:
            raise ImageViewQtError("Undefined render type: '%s'" % (render))
        self.imgwin.viewer = self
        self.pixmap = None
        # Qt expects 32bit BGRA data for color images
        self._rgb_order = 'BGRA'

        self.renderer = CanvasRenderer(self)

        self.msgtimer = Timer(0.0, lambda timer: self.onscreen_message_off())

        # For optomized redrawing
        self._defer_task = Timer(0.0, lambda timer: self.delayed_redraw())

    def get_widget(self):
        return self.imgwin

    def _render_offscreen(self, drawable, data, dst_x, dst_y,
                          width, height):
        # NOTE [A]
        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        # Get qimage for copying pixel data
        qimage = self._get_qimage(data)

        painter = QPainter(drawable)
        painter.setWorldMatrixEnabled(True)

        # fill pixmap with background color
        imgwin_wd, imgwin_ht = self.get_window_size()
        bgclr = self._get_color(*self.img_bg)
        painter.fillRect(QtCore.QRect(0, 0, imgwin_wd, imgwin_ht),
                         bgclr)

        # draw image data from buffer to offscreen pixmap
        painter.drawImage(QtCore.QRect(dst_x, dst_y, width, height),
                          qimage,
                          QtCore.QRect(0, 0, width, height))


    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
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
        self.logger.debug("window size reconfigured to %dx%d" % (
            width, height))
        if hasattr(self, 'scene'):
            # By default, a QGraphicsView comes with a 1-pixel margin
            # You will get scrollbars unless you account for this
            # See http://stackoverflow.com/questions/3513788/qt-qgraphicsview-without-scrollbar
            width, height = width - 2, height - 2
            self.scene.setSceneRect(1, 1, width-2, height-2)
        # If we need to build a new pixmap do it here.  We allocate one
        # twice as big as necessary to prevent having to reinstantiate it
        # all the time.  On Qt this causes unpleasant flashing in the display.
        if (self.pixmap is None) or (self.pixmap.width() < width) or \
           (self.pixmap.height() < height):
            pixmap = QPixmap(width*2, height*2)
            #pixmap.fill(QColor("black"))
            self.pixmap = pixmap
            self.imgwin.set_pixmap(pixmap)

        self.configure(width, height)

    def get_rgb_image_as_buffer(self, output=None, format='png',
                                quality=90):
        ibuf = output
        if ibuf is None:
            ibuf = BytesIO()
        imgwin_wd, imgwin_ht = self.get_window_size()
        qpix = self.pixmap.copy(0, 0,
                                imgwin_wd, imgwin_ht)
        qbuf = QtCore.QBuffer()
        qbuf.open(QtCore.QIODevice.ReadWrite)
        qpix.save(qbuf, format=format, quality=quality)
        ibuf.write(bytes(qbuf.data()))
        qbuf.close()
        return ibuf

    def get_rgb_image_as_widget(self, output=None, format='png',
                                quality=90):
        imgwin_wd, imgwin_ht = self.get_window_size()
        qpix = self.pixmap.copy(0, 0,
                                imgwin_wd, imgwin_ht)
        return qpix.toImage()

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        qimg = self.get_rgb_image_as_widget()
        res = qimg.save(filepath, format=format, quality=quality)

    def get_plain_image_as_widget(self):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        arr = self.getwin_array(order=self._rgb_order)
        image = self._get_qimage(arr)
        return image

    def save_plain_image_as_file(self, filepath, format='png', quality=90):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        qimg = self.get_plain_image_as_widget()
        res = qimg.save(filepath, format=format, quality=quality)

    def reschedule_redraw(self, time_sec):
        self._defer_task.cancel()
        self._defer_task.start(time_sec)

    def update_image(self):
        if (not self.pixmap) or (not self.imgwin):
            return

        self.logger.debug("updating window from pixmap")
        if hasattr(self, 'scene'):
            imgwin_wd, imgwin_ht = self.get_window_size()
            self.scene.invalidate(0, 0, imgwin_wd, imgwin_ht,
                                  QtGui.QGraphicsScene.BackgroundLayer)
        else:
            self.imgwin.update()
            #self.imgwin.show()

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

    def get_rgb_order(self):
        return self._rgb_order

    def _get_qimage(self, bgra):
        h, w, channels = bgra.shape

        fmt = QImage.Format_ARGB32
        result = QImage(bgra.data, w, h, fmt)
        # Need to hang on to a reference to the array
        result.ndarray = bgra
        return result

    def _get_color(self, r, g, b):
        n = 255.0
        clr = QColor(int(r*n), int(g*n), int(b*n))
        return clr

    def onscreen_message(self, text, delay=None, redraw=True):
        self.msgtimer.cancel()
        self.set_onscreen_message(text, redraw=redraw)
        if delay is not None:
            self.msgtimer.start(delay)


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
#         if event.mimeData().hasFormat('text/plain'):
#             event.accept()
#         else:
#             event.ignore()
        event.accept()

    def dragMoveEvent(self, event):
#         if event.mimeData().hasFormat('text/plain'):
#             event.accept()
#         else:
#             event.ignore()
        event.accept()

    def dropEvent(self, event):
        self.viewer.drop_event(self, event)


class RenderWidgetZoom(RenderMixin, RenderWidget):
    pass

class RenderGraphicsViewZoom(RenderMixin, RenderGraphicsView):
    pass

class ImageViewEvent(ImageViewQt):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageViewQt.__init__(self, logger=logger, rgbmap=rgbmap,
                             settings=settings, render=render)

        # replace the widget our parent provided
        if self.wtype == 'scene':
            imgwin = RenderGraphicsViewZoom()
            imgwin.setScene(self.scene)
        else:
            imgwin = RenderWidgetZoom()

        imgwin.viewer = self
        self.imgwin = imgwin
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

        # Does widget accept focus when mouse enters window
        self.enter_focus = self.t_.get('enter_focus', True)

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
                     'pinch', 'pan', 'swipe', 'tap'):
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
            return 'f%d' % (index+1)

        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def get_keyTable(self):
        return self._keytbl

    def set_enter_focus(self, tf):
        self.enter_focus = tf

    def map_event(self, widget, event):
        rect = widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        self.configure_window(width, height)
        return self.make_callback('map')

    def focus_event(self, widget, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, widget, event):
        if self.enter_focus:
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
        return self.make_ui_callback('key-press', keyname)

    def key_release_event(self, widget, event):
        keyname = event.key()
        keyname2 = "%s" % (event.text())
        keyname = self.transkey(keyname, keyname2)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback('key-release', keyname)

    def button_press_event(self, widget, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
        self.logger.debug("button down event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, widget, event):
        # note: for mouseRelease this needs to be button(), not buttons()!
        buttons = event.button()
        x, y = event.x(), event.y()
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('button-release', button, data_x, data_y)

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
        x, y = event.x(), event.y()
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('motion', button, data_x, data_y)

    def scroll_event(self, widget, event):
        x, y = event.x(), event.y()
        self.last_win_x, self.last_win_y = x, y

        num_degrees, direction = get_scroll_info(event)
        self.logger.debug("scroll deg={} direction={}".format(
            num_degrees, direction))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('scroll', direction, num_degrees,
                                     data_x, data_y)

    def gesture_event(self, widget, event):
        gesture = event.gestures()[0]
        state = gesture.state()
        if state == QtCore.Qt.GestureStarted:
            gstate = 'start'
        elif state == QtCore.Qt.GestureUpdated:
            gstate = 'move'
        elif state == QtCore.Qt.GestureFinished:
            gstate = 'end'
        elif state == QtCore.Qt.GestureCancelled:
            gstate = 'end'

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
        if gstate == 'end':
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

            return self.make_ui_callback('swipe', gstate, hdir, vdir)

    def gs_pinching(self, event, gesture, gstate):
        #print("PINCHING")
        rot = gesture.rotationAngle()
        scale = gesture.scaleFactor()
        self.logger.debug("pinch gesture rot=%f scale=%f state=%s" % (
            rot, scale, gstate))

        return self.make_ui_callback('pinch', gstate, rot, scale)

    def gs_panning(self, event, gesture, gstate):
        #print("PANNING")
        # x, y = event.x(), event.y()
        # self.last_win_x, self.last_win_y = x, y

        # data_x, data_y = self.get_data_xy(x, y)
        # self.last_data_x, self.last_data_y = data_x, data_y

        d = gesture.delta()
        dx, dy = d.x(), d.y()
        self.logger.debug("pan gesture dx=%f dy=%f state=%s" % (
            dx, dy, gstate))

        return self.make_ui_callback('pan', gstate, dx, dy)

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
            if six.PY2:
                thumbstr = str(dropdata.data("text/thumb"))
            else:
                thumbstr = str(dropdata.data("text/thumb"), encoding='ascii')
            data = [ thumbstr ]
            self.logger.debug("dropped thumb(s): %s" % (str(data)))
        elif dropdata.hasUrls():
            urls = list(dropdata.urls())
            data = [ str(url.toString()) for url in urls ]
            self.logger.debug("dropped filename(s): %s" % (str(data)))
        elif "text/plain" in formats:
            data = [ dropdata.text() ]
            self.logger.debug("dropped filename(s): %s" % (str(data)))
        else:
            # No format that we understand--just pass it along
            ## data = dropdata.data(formats[0])
            ## self.logger.debug("dropped data of len %d" % (len(data)))
            event.setAccepted(False)
            return

        event.setAccepted(True)
        #event.acceptProposedAction()
        self.make_ui_callback('drag-drop', data)

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

        # the window jiggles annoyingly as the scrollbar is alternately
        # shown and hidden if we use the default "as needed" policy, so
        # default to always showing them (user can change this after
        # calling the constructor, if desired)
        self.scroll_bars(horizontal='on', vertical='on')

        self._adjusting = False
        self._scrolling = False
        self.pad = 20
        self.upper_h = 100
        self.upper_v = 100

        # reparent the viewer widget
        vp = self.viewport()
        self.v_w = viewer.get_widget()
        self.v_w.setParent(vp)

        hsb = self.horizontalScrollBar()
        hsb.setTracking(True)
        hsb.setRange(0, 100)
        hsb.setSingleStep(1)
        vsb = self.verticalScrollBar()
        vsb.setRange(0, 100)
        vsb.setSingleStep(1)
        vsb.setTracking(True)

        self.viewer.add_callback('redraw', self._calc_scrollbars)
        self.viewer.add_callback('limits-set',
                                 lambda v, l: self._calc_scrollbars(v))

    def get_widget(self):
        return self

    def resizeEvent(self, event):
        """Override from QAbstractScrollArea.
        Resize the viewer widget when the viewport is resized."""
        vp = self.viewport()
        rect = vp.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        self.v_w.resize(width, height)

    def _calc_scrollbars(self, viewer):
        """Calculate and set the scrollbar handles from the pan and
        zoom positions.
        """
        if self._scrolling:
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

            page_h, page_v = (int(round(res.thm_pct_x * 100)),
                              int(round(res.thm_pct_y * 100)))
            hsb.setPageStep(page_h)
            vsb.setPageStep(page_v)

            upper_h, upper_v = max(1, 100 - page_h), max(1, 100 - page_v)
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
            hsb = self.horizontalScrollBar()
            vsb = self.verticalScrollBar()

            pct_x = hsb.value() / float(self.upper_h)
            # invert Y pct because of orientation of scrollbar
            pct_y = 1.0 - (vsb.value() / float(self.upper_v))

            bd = self.viewer.get_bindings()
            bd.pan_by_pct(self.viewer, pct_x, pct_y, pad=self.pad)

        finally:
            self._scrolling = False

    def scroll_bars(self, horizontal='on', vertical='on'):
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


#END
