#
# ImageViewQt.py -- classes for the display of Ginga canvases in Qt widgets
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import math
import numpy
from io import BytesIO

from ginga.qtw.QtHelp import QtGui, QtCore, QFont, QColor, QImage, \
     QPixmap, QCursor, QPainter, have_pyqt5, get_scroll_info
from ginga import ImageView, Mixins, Bindings
import ginga.util.six as six
from ginga.util.six.moves import map, zip
from ginga.qtw.CanvasRenderQt import CanvasRenderer

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
icon_dir = os.path.abspath(os.path.join(moduleHome, '..', 'icons'))


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

        self.t_.setDefaults(show_pan_position=False,
                            onscreen_ff='Sans Serif')

        self.message = None
        self.msgtimer = QtCore.QTimer()
        self.msgtimer.timeout.connect(self.onscreen_message_off)
        self.msgfont = QFont(self.t_['onscreen_ff'],
                                   pointSize=24)
        # cursors
        self.cursor = {}

        # For optomized redrawing
        self._defer_task = QtCore.QTimer()
        self._defer_task.setSingleShot(True)
        self._defer_task.timeout.connect(self.delayed_redraw)


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

        # Draw a cross in the center of the window in debug mode
        if self.t_['show_pan_position']:
            clr = QColor()
            clr.setRgbF(1.0, 0.0, 0.0)
            painter.setPen(clr)
            ctr_x, ctr_y = self.get_center()
            painter.drawLine(ctr_x - 10, ctr_y, ctr_x + 10, ctr_y)
            painter.drawLine(ctr_x, ctr_y - 10, ctr_x, ctr_y + 10)

        # render self.message
        if self.message:
            self._draw_message(painter, imgwin_wd, imgwin_ht,
                               self.message)

    def _draw_message(self, painter, width, height, message):
        fgclr = self._get_color(*self.img_fg)
        painter.setPen(fgclr)
        painter.setBrush(fgclr)
        painter.setFont(self.msgfont)
        rect = painter.boundingRect(0, 0, 1000, 1000, 0, message)
        x1, y1, x2, y2 = rect.getCoords()
        wd = x2 - x1
        ht = y2 - y1
        y = ((height // 3) * 2) - (ht // 2)
        x = (width // 2) - (wd // 2)
        painter.drawText(x, y, message)


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
            self.scene.setSceneRect(0, 0, width, height)
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

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        ibuf = self.get_rgb_image_as_buffer(format=format, quality=quality)
        return bytes(ibuf.getvalue())

    def get_rgb_image_as_widget(self, output=None, format='png',
                                quality=90):
        imgwin_wd, imgwin_ht = self.get_window_size()
        qpix = self.pixmap.copy(0, 0,
                                imgwin_wd, imgwin_ht)
        return qpix.toImage()

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        qimg = self.get_rgb_image_as_widget()
        res = qimg.save(filepath, format=format, quality=quality)

    def get_image_as_widget(self):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        arr = self.getwin_array(order=self._rgb_order)
        image = self._get_qimage(arr)
        return image

    def save_image_as_file(self, filepath, format='png', quality=90):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        qimg = self.get_image_as_widget()
        res = qimg.save(filepath, format=format, quality=quality)

    def reschedule_redraw(self, time_sec):
        try:
            self._defer_task.stop()
        except:
            pass

        time_ms = int(time_sec * 1000)
        self._defer_task.start(time_ms)

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
        if self.imgwin:
            self.imgwin.setCursor(cursor)

    def define_cursor(self, ctype, cursor):
        self.cursor[ctype] = cursor

    def get_cursor(self, ctype):
        return self.cursor[ctype]

    def get_rgb_order(self):
        return self._rgb_order

    def switch_cursor(self, ctype):
        self.set_cursor(self.cursor[ctype])

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

    def onscreen_message(self, text, delay=None):
        try:
            self.msgtimer.stop()
        except:
            pass
        self.message = text
        self.redraw(whence=3)
        if delay:
            ms = int(delay * 1000.0)
            self.msgtimer.start(ms)

    def onscreen_message_off(self):
        return self.onscreen_message(None)

    def show_pan_mark(self, tf):
        self.t_.set(show_pan_position=tf)
        self.redraw(whence=3)


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
        self.grabKeyboard()
        self.viewer.key_press_event(self, event)

    def keyReleaseEvent(self, event):
        self.releaseKeyboard()
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

    def set_follow_focus(self, tf):
        self.follow_focus = tf

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
        if self.follow_focus:
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

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4
        self.logger.debug("button down event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, widget, event):
        # note: for mouseRelease this needs to be button(), not buttons()!
        buttons = event.button()
        x, y = event.x(), event.y()

        button = 0
        if buttons & QtCore.Qt.LeftButton:
            button |= 0x1
        if buttons & QtCore.Qt.MidButton:
            button |= 0x2
        if buttons & QtCore.Qt.RightButton:
            button |= 0x4

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-release', button, data_x, data_y)

    def get_last_win_xy(self):
        return (self.last_win_x, self.last_win_y)

    def get_last_data_xy(self):
        return (self.last_data_x, self.last_data_y)

    def motion_notify_event(self, widget, event):
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

        numDegrees, direction = get_scroll_info(event)
        self.logger.debug("scroll deg=%f direction=%f" % (
            numDegrees, direction))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('scroll', direction, numDegrees,
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


def make_cursor(iconpath, x, y):
    image = QImage()
    image.load(iconpath)
    pm = QPixmap(image)
    return QCursor(pm, x, y)


#END
