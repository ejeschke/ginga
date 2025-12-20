#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
The ``Pan`` plugin provides a small panning image that gives an overall
"birds-eye" view of the channel image that last had the focus.  If the
channel image is zoomed in 2X or greater, then the pan region is shown
graphically in the ``Pan`` image by a rectangle.

**Plugin Type: Local**

``Pan`` is a global plugin.  Only one instance can be opened.

**Usage**

The channel image can be panned by clicking and/or dragging to place
the rectangle.  Using the right mouse button to drag a rectangle will
force the channel image viewer to try to match the region (taking into
account the differences in the aspect ratio between the drawn rectangle
and the window dimensions).  Scrolling in the ``Pan`` image will zoom the
channel image.

The color/intensity map and cut levels of the ``Pan`` image are updated
when they are changed in the corresponding channel image.
The ``Pan`` image also displays the World Coordinate System (WCS) compass, if
valid WCS metadata is present in the FITS HDU being viewed in the
channel.

The ``Pan`` plugin usually appears as a sub-pane under the "Info" tab, next
to the ``Info`` plugin.

This plugin is not usually configured to be closeable, but the user can
make it so by setting the "closeable" setting to True in the configuration
file--then Close and Help buttons will be added to the bottom of the UI.

"""
import sys
import traceback
import math

from ginga.gw import Widgets, Viewers
from ginga.util import wcs
from ginga import GingaPlugin

__all__ = ['Pan']


class Pan(GingaPlugin.ParentPlugin):
    # Pan uses the ParentPlugin class to share the same window amongst
    # a bunch of local plugins

    def __init__(self, fv):
        super().__init__(fv)

        # the child plugin class we will start for each channel opened
        self.class_childplugin = PanChild

        spec = self.fv.get_plugin_spec(str(self))
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Pan')
        self.settings.add_defaults(closeable=not spec.get('hidden', False))
        self.settings.load(onError='silent')

        self.gui_up = False

    def build_gui(self, container):
        super().build_gui(container)

        if self.settings.get('closeable', False):
            btns = Widgets.HBox()
            btns.set_border_width(4)
            btns.set_spacing(4)

            btn = Widgets.Button("Close")
            btn.add_callback('activated', lambda w: self.close())
            btns.add_widget(btn)
            btn = Widgets.Button("Help")
            btn.add_callback('activated', lambda w: self.help())
            btns.add_widget(btn, stretch=0)
            btns.add_widget(Widgets.Label(''), stretch=1)

            container.add_widget(btns, stretch=0)
        self.gui_up = True

    def __str__(self):
        return 'pan'


class PanChild(GingaPlugin.ChildPlugin):
    # This local plugin actually does all the work, but only has to be
    # concerned with tracking a single channel

    def __init__(self, fv, image_viewer, parent_plugin):
        # superclass defines some variables for us, like logger
        super().__init__(fv, image_viewer, parent_plugin)

        self.dc = fv.get_draw_classes()

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Pan')
        self.settings.add_defaults(pan_position_color='yellow',
                                   pan_rectangle_color='red',
                                   compass_color='skyblue',
                                   rotate_pan_image=True)
        self.settings.load(onError='silent')

        self._wd = 200
        self._ht = 200
        self.copy_attrs = ['transforms', 'cutlevels', 'rotation', 'rgbmap',
                           'limits', 'icc', 'interpolation']

        self.compass_xy = None
        self.compass_wcs = None
        self.panrect = None

        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(2)

        pi = Viewers.CanvasView(logger=self.logger)
        pi.enable_autozoom('on')
        pi.enable_autocuts('off')
        hand = pi.get_cursor('pan')
        pi.define_cursor('pick', hand)
        pi.set_bg(0.4, 0.4, 0.4)
        pi.set_desired_size(self._wd, self._ht)
        pi.set_callback('cursor-down', self.btndown)
        pi.set_callback('cursor-move', self.drag_cb)
        pi.set_callback('none-move', self.motion_cb)
        pi.set_callback('zoom-scroll', self.zoom_cb)
        pi.set_callback('zoom-pinch', self.zoom_pinch_cb)
        pi.set_callback('pan-pan', self.pan_pan_cb)
        pi.set_callback('configure', self.reconfigure)
        # for debugging
        pi.set_name('panimage')
        self.panimage = pi

        my_canvas = pi.get_private_canvas()
        my_canvas.enable_draw(True)
        my_canvas.set_drawtype('rectangle', linestyle='dash', color='green')
        my_canvas.set_callback('draw-event', self.draw_cb)

        # we share a canvas with the main channel image viewer
        canvas = self.fitsimage.get_canvas()
        pi.set_canvas(canvas)

        bd = pi.get_bindings()
        bd.enable_pan(False)
        bd.enable_zoom(False)

        p_canvas = pi.get_private_canvas()

        # add X/Y compass
        x, y = 0.5, 0.5
        radius = 0.1

        self.compass_xy = self.dc.Compass(x, y, radius,
                                          color=self.settings.get('xy_compass_color',
                                                                  'yellow'),
                                          fontsize=14, ctype='pixel',
                                          coord='percentage')
        p_canvas.add_object(self.compass_xy)

        self.compass_wcs = self.dc.Compass(x, y, radius * 2.0,
                                           color=self.settings.get('compass_color',
                                                                   'skyblue'),
                                           fontsize=14, ctype='wcs',
                                           coord='percentage')

        pw = Viewers.GingaViewerWidget(pi)
        pw.resize(self._wd, self._ht)

        self.fitsimage.copy_attributes(pi, self.copy_attrs)
        self.fitsimage.add_callback('redraw', self.redraw_cb)

        vbox.add_widget(pw, stretch=1)
        container.add_widget(vbox, stretch=1)
        self.gui_up = True

    def start(self):
        pass

    def stop(self):
        self.gui_up = False

    # CALLBACKS

    def redo(self):
        if not self.gui_up:
            return

        image = self.fitsimage.get_image()

        if (image is None) or not self.panimage.viewable(image):
            self.logger.debug("no main image--clearing Pan viewer")
            self.panimage.clear()
            return

        self.set_image(image)

    def blank(self, channel):
        if not self.gui_up:
            return
        self.panimage.clear()

    def reconfigure(self, panimage, width, height):
        self.logger.debug("new pan image dimensions are %dx%d" % (
            width, height))

        panimage.zoom_fit()
        panimage.redraw(whence=0)
        return True

    def redraw_cb(self, fitsimage, whence):
        if not self.gui_up:
            return
        if whence < 3:
            self.fitsimage.copy_attributes(self.panimage, self.copy_attrs,
                                           whence=whence)
            self.panimage.zoom_fit()
            self.panset()
        else:
            # nothing except a graphical overlay change, so simply
            # redraw to keep pace
            self.panimage.redraw(whence=whence)
        return True

    # LOGIC

    def clear(self):
        self.panimage.clear()

    def set_image(self, image):
        if image is None or not self.panimage.viewable(image):
            self.logger.debug("no main image--clearing Pan viewer")
            self.panimage.clear()
            return

        self.panimage.zoom_fit()

        p_canvas = self.panimage.get_private_canvas()
        # remove old WCS compass
        try:
            p_canvas.delete_object(self.compass_wcs)
        except Exception:
            pass

        # create compass
        if image.has_valid_wcs():
            try:
                x, y = 0.5, 0.5
                # HACK: force a wcs error here if one is going to happen
                wcs.add_offset_xy(image, x, y, 1.0, 1.0)

                p_canvas.add_object(self.compass_wcs)
            except Exception as e:
                self.logger.warning("Can't calculate wcs compass: {}".format(e))
                try:
                    # log traceback, if possible
                    (type_, value_, tb) = sys.exc_info()
                    tb_str = "".join(traceback.format_tb(tb))
                    self.logger.debug("Traceback:\n%s" % (tb_str))
                except Exception:
                    tb_str = "Traceback information unavailable."
                    self.logger.debug(tb_str)

        self.panset()

    def panset(self):
        image = self.fitsimage.get_image()
        if image is None or not self.panimage.viewable(image):
            self.panimage.clear()

        x, y = self.fitsimage.get_pan()
        points = self.fitsimage.get_pan_bbox()

        limits = self.fitsimage.get_limits()
        width = limits[1][0] - limits[0][0]
        height = limits[1][1] - limits[0][1]
        edgew = math.sqrt(width**2 + height**2)
        radius = int(0.015 * edgew)

        # Mark pan rectangle and pan position
        self.logger.debug("starting panset")
        p_canvas = self.panimage.get_private_canvas()
        if self.panrect is None:
            self.panrect = self.dc.CompoundObject(
                self.dc.Point(
                    x, y, radius, style='plus',
                    color=self.settings.get('pan_position_color', 'yellow')),
                self.dc.Polygon(
                    points,
                    color=self.settings.get('pan_rectangle_color', 'red')))
            p_canvas.add_object(self.panrect)
        else:
            point, bbox = self.panrect.objects
            point.x, point.y = x, y
            point.radius = radius
            bbox.points = points

        p_canvas.update_canvas(whence=3)

        #paninfo.panimage.zoom_fit()
        return True

    def get_channel_viewer(self):
        return self.channel.get_viewer('Ginga Image')

    def motion_cb(self, fitsimage, event, data_x, data_y):
        chviewer = self.get_channel_viewer()
        self.fv.showxy(chviewer, data_x, data_y)
        return True

    def drag_cb(self, fitsimage, event, data_x, data_y):
        # this is a panning move in the small
        # window for the big window
        chviewer = self.get_channel_viewer()
        chviewer.panset_xy(data_x, data_y)
        return True

    def btndown(self, fitsimage, event, data_x, data_y):
        chviewer = self.get_channel_viewer()
        chviewer.panset_xy(data_x, data_y)
        return True

    def zoom_cb(self, fitsimage, event):
        """Zoom event in the pan window.  Just zoom the channel viewer.
        """
        chviewer = self.get_channel_viewer()
        bd = chviewer.get_bindings()

        mode = bd.get_mode_obj('pan')
        return mode.sc_zoom(chviewer, event)

    def zoom_pinch_cb(self, fitsimage, event):
        """Pinch event in the pan window.  Just zoom the channel viewer.
        """
        chviewer = self.get_channel_viewer()
        bd = chviewer.get_bindings()

        mode = bd.get_mode_obj('pan')
        return mode.pi_zoom(chviewer, event)

    def pan_pan_cb(self, fitsimage, event):
        """Pan event in the pan window.  Just pan the channel viewer.
        """
        chviewer = self.get_channel_viewer()
        bd = chviewer.get_bindings()

        mode = bd.get_mode_obj('pan')
        return mode.pa_pan(chviewer, event)

    def draw_cb(self, canvas, tag):
        # Get and delete the drawn object
        obj = canvas.get_object_by_tag(tag)
        canvas.delete_object_by_tag(tag)

        # determine center of drawn rectangle and set pan position
        if obj.kind != 'rectangle':
            return False
        xc = (obj.x1 + obj.x2) / 2.0
        yc = (obj.y1 + obj.y2) / 2.0
        chviewer = self.get_channel_viewer()
        # note: chviewer <-- referring to channel viewer
        with chviewer.suppress_redraw:
            chviewer.panset_xy(xc, yc)

            # Determine appropriate zoom level to fit this rect
            wd = obj.x2 - obj.x1
            ht = obj.y2 - obj.y1
            wwidth, wheight = chviewer.get_window_size()
            wd_scale = float(wwidth) / float(wd)
            ht_scale = float(wheight) / float(ht)
            scale = min(wd_scale, ht_scale)
            self.logger.debug("wd_scale=%f ht_scale=%f scale=%f" % (
                wd_scale, ht_scale, scale))
            if scale < 1.0:
                zoomlevel = - max(2, int(math.ceil(1.0 / scale)))
            else:
                zoomlevel = max(1, int(math.floor(scale)))
            self.logger.debug("zoomlevel=%d" % (zoomlevel))

            chviewer.zoom_to(zoomlevel)

        return True

    def __str__(self):
        return 'panchild'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Pan', package='ginga')

# END
