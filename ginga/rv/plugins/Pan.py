#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
The ``Pan`` plugin provides a small panning image that gives an overall
"birds-eye" view of the channel image that last had the focus.  If the
channel image is zoomed in 2X or greater, then the pan region is shown
graphically in the ``Pan`` image by a rectangle.

**Plugin Type: Global**

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
from ginga.misc import Bunch
from ginga.util import wcs
from ginga import GingaPlugin

__all__ = ['Pan']


class Pan(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Pan, self).__init__(fv)

        self.active = None
        self.info = None

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('delete-channel', self.delete_channel)
        fv.set_callback('channel-change', self.focus_cb)

        self.dc = fv.get_draw_classes()

        spec = self.fv.get_plugin_spec(str(self))

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Pan')
        self.settings.add_defaults(closeable=not spec.get('hidden', False),
                                   pan_position_color='yellow',
                                   pan_rectangle_color='red',
                                   compass_color='skyblue',
                                   rotate_pan_image=True)
        self.settings.load(onError='silent')

        self._wd = 200
        self._ht = 200
        self.copy_attrs = ['transforms', 'cutlevels', 'rotation', 'rgbmap',
                           'limits', 'icc', 'interpolation']
        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(2)

        nb = Widgets.StackWidget()
        self.nb = nb
        vbox.add_widget(self.nb, stretch=1)

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
            vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)
        self.gui_up = True

    def _create_pan_viewer(self, fitsimage):
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

        my_canvas = pi.get_private_canvas()
        my_canvas.enable_draw(True)
        my_canvas.set_drawtype('rectangle', linestyle='dash', color='green')
        my_canvas.set_callback('draw-event', self.draw_cb)

        canvas = fitsimage.get_canvas()
        pi.set_canvas(canvas)

        bd = pi.get_bindings()
        bd.enable_pan(False)
        bd.enable_zoom(False)

        return pi

    def add_channel(self, viewer, channel):
        if not self.gui_up:
            return
        fitsimage = channel.fitsimage
        panimage = self._create_pan_viewer(fitsimage)
        p_canvas = panimage.get_private_canvas()

        # add X/Y compass
        x, y = 0.5, 0.5
        radius = 0.1

        compass_xy = p_canvas.add(self.dc.Compass(
            x, y, radius,
            color=self.settings.get('xy_compass_color', 'yellow'),
            fontsize=14, ctype='pixel', coord='percentage'))

        iw = Viewers.GingaViewerWidget(panimage)
        iw.resize(self._wd, self._ht)
        self.nb.add_widget(iw)
        #index = self.nb.index_of(iw)
        paninfo = Bunch.Bunch(panimage=panimage, widget=iw,
                              compass_wcs=None, compass_xy=compass_xy,
                              panrect=None)
        channel.extdata._pan_info = paninfo

        fitsimage.copy_attributes(panimage, self.copy_attrs)

        fitsimage.add_callback('redraw', self.redraw_cb, channel)
        fitsimage.add_callback('image-set',
                               lambda viewer, image: self._redo(channel, image))

        self.logger.debug("channel '%s' added." % (channel.name))

    def delete_channel(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name
        self.logger.debug("deleting channel %s" % (chname))
        widget = channel.extdata._pan_info.widget
        channel.extdata._pan_info.widget = None
        self.nb.remove(widget, delete=True)
        self.active = None
        self.info = None

    def start(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            self.add_channel(self.fv, channel)

        channel = self.fv.get_channel_info()
        if channel is not None:
            viewer = channel.fitsimage

            image = viewer.get_image()
            if image is not None:
                self.redo(channel, image)

            self.focus_cb(viewer, channel)

    def stop(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            channel.extdata._pan_info = None

        self.active = None
        self.nb = None
        self.info = None
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    # CALLBACKS

    def _redo(self, channel, image):
        """NOTE: this plugin is triggered not by a CHANNEL getting a new
        image, but by the VIEWER getting a new image, OR the viewer redrawing.
        """
        if not self.gui_up:
            return
        self.logger.debug("redo")
        paninfo = channel.extdata._pan_info

        if (image is None) or not paninfo.panimage.viewable(image):
            self.logger.debug("no main image--clearing Pan viewer")
            paninfo.panimage.clear()
            return

        self.set_image(channel, paninfo, image)

    def blank(self, channel):
        if not self.gui_up:
            return
        paninfo = channel.extdata._pan_info
        paninfo.panimage.clear()

    def focus_cb(self, viewer, channel):
        if not self.gui_up:
            return
        chname = channel.name

        # If the active widget has changed, then raise our Info widget
        # that corresponds to it
        if self.active != chname:
            if '_pan_info' not in channel.extdata:
                self.add_channel(viewer, channel)
            paninfo = channel.extdata._pan_info
            iw = paninfo.widget
            index = self.nb.index_of(iw)
            self.nb.set_index(index)
            self.active = chname
            self.info = paninfo

        # TODO: this check should not be necessary.  But under some
        # circumstances it seems to be needed.
        image = channel.fitsimage.get_image()
        p_image = self.info.panimage.get_image()
        if image != p_image:
            self.logger.debug("pan viewer seems to be missing image--calling redo()")
            self.redo(channel, image)

    def reconfigure(self, panimage, width, height):
        self.logger.debug("new pan image dimensions are %dx%d" % (
            width, height))

        panimage.zoom_fit()
        panimage.redraw(whence=0)
        return True

    def redraw_cb(self, fitsimage, whence, channel):
        if not self.gui_up:
            return
        paninfo = channel.extdata._pan_info
        if paninfo is not None:
            if whence < 3:
                fitsimage.copy_attributes(paninfo.panimage, self.copy_attrs,
                                          whence=whence)
                paninfo.panimage.zoom_fit()
                self.panset(channel.fitsimage, channel, paninfo)
                pass
        return True

    # LOGIC

    def clear(self):
        if self.info is not None:
            self.info.panimage.clear()

    def set_image(self, channel, paninfo, image):
        if image is None or not paninfo.panimage.viewable(image):
            self.logger.debug("no main image--clearing Pan viewer")
            paninfo.panimage.clear()
            return

        paninfo.panimage.zoom_fit()

        p_canvas = paninfo.panimage.get_private_canvas()
        # remove old compasses
        try:
            p_canvas.delete_object_by_tag(paninfo.compass_wcs)
        except Exception:
            pass

        # create compass
        if image.has_valid_wcs():
            try:
                x, y = 0.5, 0.5
                # HACK: force a wcs error here if one is going to happen
                wcs.add_offset_xy(image, x, y, 1.0, 1.0)

                radius = 0.2
                paninfo.compass_wcs = p_canvas.add(self.dc.Compass(
                    x, y, radius,
                    color=self.settings.get('compass_color', 'skyblue'),
                    fontsize=14, ctype='wcs', coord='percentage'))

            except Exception as e:
                paninfo.compass_wcs = None
                self.logger.warning("Can't calculate wcs compass: {}".format(e))
                try:
                    # log traceback, if possible
                    (type_, value_, tb) = sys.exc_info()
                    tb_str = "".join(traceback.format_tb(tb))
                    self.logger.debug("Traceback:\n%s" % (tb_str))
                except Exception:
                    tb_str = "Traceback information unavailable."
                    self.logger.debug(tb_str)

        self.panset(channel.fitsimage, channel, paninfo)

    def panset(self, fitsimage, channel, paninfo):
        image = fitsimage.get_image()
        if image is None or not paninfo.panimage.viewable(image):
            paninfo.panimage.clear()

        x, y = fitsimage.get_pan()
        points = fitsimage.get_pan_rect()

        limits = fitsimage.get_limits()
        width = limits[1][0] - limits[0][0]
        height = limits[1][1] - limits[0][1]
        edgew = math.sqrt(width**2 + height**2)
        radius = int(0.015 * edgew)

        # Mark pan rectangle and pan position
        p_canvas = paninfo.panimage.get_private_canvas()
        try:
            obj = p_canvas.get_object_by_tag(paninfo.panrect)
            if obj.kind != 'compound':
                return False
            point, bbox = obj.objects
            self.logger.debug("starting panset")
            point.x, point.y = x, y
            point.radius = radius
            bbox.points = points
            p_canvas.update_canvas(whence=3)

        except KeyError:
            paninfo.panrect = p_canvas.add(self.dc.CompoundObject(
                self.dc.Point(
                    x, y, radius, style='plus',
                    color=self.settings.get('pan_position_color', 'yellow')),
                self.dc.Polygon(
                    points,
                    color=self.settings.get('pan_rectangle_color', 'red'))))

        #paninfo.panimage.zoom_fit()
        return True

    def motion_cb(self, fitsimage, event, data_x, data_y):
        chviewer = self.fv.getfocus_viewer()
        self.fv.showxy(chviewer, data_x, data_y)
        return True

    def drag_cb(self, fitsimage, event, data_x, data_y):
        # this is a panning move in the small
        # window for the big window
        chviewer = self.fv.getfocus_viewer()
        chviewer.panset_xy(data_x, data_y)
        return True

    def btndown(self, fitsimage, event, data_x, data_y):
        chviewer = self.fv.getfocus_viewer()
        chviewer.panset_xy(data_x, data_y)
        return True

    def zoom_cb(self, fitsimage, event):
        """Zoom event in the pan window.  Just zoom the channel viewer.
        """
        chviewer = self.fv.getfocus_viewer()
        bd = chviewer.get_bindings()

        if hasattr(bd, 'sc_zoom'):
            return bd.sc_zoom(chviewer, event)

        return False

    def zoom_pinch_cb(self, fitsimage, event):
        """Pinch event in the pan window.  Just zoom the channel viewer.
        """
        chviewer = self.fv.getfocus_viewer()
        bd = chviewer.get_bindings()

        if hasattr(bd, 'pi_zoom'):
            return bd.pi_zoom(chviewer, event)

        return False

    def pan_pan_cb(self, fitsimage, event):
        """Pan event in the pan window.  Just pan the channel viewer.
        """
        chviewer = self.fv.getfocus_viewer()
        bd = chviewer.get_bindings()

        if hasattr(bd, 'pa_pan'):
            return bd.pa_pan(chviewer, event)

        return False

    def draw_cb(self, canvas, tag):
        # Get and delete the drawn object
        obj = canvas.get_object_by_tag(tag)
        canvas.delete_object_by_tag(tag)

        # determine center of drawn rectangle and set pan position
        if obj.kind != 'rectangle':
            return False
        xc = (obj.x1 + obj.x2) / 2.0
        yc = (obj.y1 + obj.y2) / 2.0
        chviewer = self.fv.getfocus_viewer()
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
        return 'pan'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Pan', package='ginga')

# END
