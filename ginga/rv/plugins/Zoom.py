# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Zoom`` plugin shows an enlarged image of a cutout region centered
under the cursor position in the associated channel image.  As the
cursor is moved around the image, the zoom image updates to allow close
inspection of the pixels or precise control in conjunction with other
plugin operations.

**Plugin Type: Global**

``Zoom`` is a global plugin.  Only one instance can be opened.

**Usage**

The magnification of the zoom window can be changed by adjusting the
"Zoom Amount" slider.

Two modes of operation are possible -- absolute and relative zoom:

* In absolute mode, the zoom amount controls exactly the zoom level
  shown in the cutout; For example, the channel image may be zoomed into
  10X, but the zoom image will only show a 3X image if the zoom amount
  is set to 3X.

* In relative mode, the zoom amount setting is interpreted as relative
  to the zoom setting of the channel image.  If the zoom amount is set
  to 3X and the channel image is zoomed to 10X then the zoom image shown
  will be 13X (10X + 3X).  Note that the zoom amount setting can be < 1,
  so a setting of 1/3X with a 3X zoom in the channel image will produce
  a 1X zoom image.

The "Refresh Interval" setting controls how quickly the ``Zoom`` plugin
responds to the movement of the cursor in updating the zoom image.  The
value is specified in milliseconds.

.. tip:: Usually setting a small refresh interval *improves* the overall
         responsiveness of the zoom image, and the default value of 20 is
         a reasonable one.  You can experiment with the value if the zoom
         image seems too jerky or out of sync with the mouse movement in
         the channel image window.

The "Defaults" button restores the default settings of the controls.

"""
import time

from ginga.gw import Widgets, Viewers
from ginga import GingaPlugin

__all__ = ['Zoom']


class Zoom(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Zoom, self).__init__(fv)

        self.zoomimage = None
        self.default_radius = 30
        self.default_zoom = 3
        self.zoom_x = 0
        self.zoom_y = 0
        self.t_abszoom = True
        self.zoomtask = fv.get_backend_timer()
        self.zoomtask.set_callback('expired', self.showzoom_timer_cb)
        self.fitsimage_focus = None
        self.layer_tag = 'shared-canvas'
        self.update_time = time.time()

        spec = self.fv.get_plugin_spec(str(self))

        # read preferences for this plugin
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Zoom')
        self.settings.add_defaults(zoom_amount=self.default_zoom,
                                   closeable=not spec.get('hidden', False),
                                   refresh_interval=0.02)
        self.settings.load(onError='silent')

        self.zoom_amount = self.settings.get('zoom_amount', self.default_zoom)
        self.refresh_interval = self.settings.get('refresh_interval', 0.02)
        self.copy_attrs = ['transforms', 'cutlevels', 'rotation', 'rgbmap',
                           'icc']  # , 'interpolation']

        self._wd = 300
        self._ht = 300
        _sz = max(self._wd, self._ht)
        # hack to set a reasonable starting position for the splitter
        self._split_sizes = [_sz, _sz]

        fv.add_callback('add-channel', self.add_channel)
        fv.add_callback('channel-change', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):

        vtop = Widgets.VBox()
        vtop.set_border_width(4)

        box, sw, orientation = Widgets.get_oriented_box(container,
                                                        orientation=self.settings.get('orientation', None))
        # Uncomment to debug; passing parent logger generates too
        # much noise in the main logger
        #zi = Viewers.CanvasView(logger=self.logger)
        zi = Viewers.CanvasView(logger=None)
        zi.set_desired_size(self._wd, self._ht)
        zi.enable_autozoom('off')
        zi.enable_autocuts('off')
        zi.zoom_to(self.default_zoom)
        settings = zi.get_settings()
        settings.get_setting('zoomlevel').add_callback(
            'set', self.zoomset, zi)
        zi.set_bg(0.4, 0.4, 0.4)
        zi.show_pan_mark(True)
        # for debugging
        zi.set_name('zoomimage')
        self.zoomimage = zi

        bd = zi.get_bindings()
        bd.enable_zoom(False)
        bd.enable_pan(False)
        bd.enable_cmap(False)

        iw = Viewers.GingaViewerWidget(zi)
        iw.resize(self._wd, self._ht)
        paned = Widgets.Splitter(orientation=orientation)
        paned.add_widget(iw)
        self.w.splitter = paned

        vbox2 = Widgets.VBox()
        captions = (("Zoom Amount:", 'label', 'Zoom Amount', 'hscale'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)
        vbox2.add_widget(w, stretch=0)

        self.w.zoom_amount.set_limits(-20, 30, incr_value=1)
        self.w.zoom_amount.set_value(self.zoom_amount)
        self.w.zoom_amount.add_callback('value-changed', self.set_amount_cb)
        self.w.zoom_amount.set_tracking(True)

        captions = (("Zoom:", 'label', 'Zoom', 'label'),
                    ("Relative Zoom", 'checkbutton'),
                    ("Refresh Interval", 'label',
                     'Refresh Interval', 'spinbutton'),
                    ("Defaults", 'button'),
                    )
        w, b = Widgets.build_info(captions, orientation=orientation)
        self.w.update(b)

        b.zoom.set_text(self.fv.scale2text(zi.get_scale()))
        b.relative_zoom.set_state(not self.t_abszoom)
        b.relative_zoom.add_callback("activated", self.set_absrel_cb)
        b.defaults.add_callback("activated", lambda w: self.set_defaults())
        b.refresh_interval.set_limits(0, 200, incr_value=1)
        b.refresh_interval.set_value(int(self.refresh_interval * 1000))
        b.refresh_interval.add_callback('value-changed', self.set_refresh_cb)

        row = Widgets.HBox()
        row.add_widget(w, stretch=0)
        row.add_widget(Widgets.Label(''), stretch=1)
        vbox2.add_widget(row, stretch=0)

        # stretch
        spacer = Widgets.Label('')
        vbox2.add_widget(spacer, stretch=1)

        box.add_widget(vbox2, stretch=1)

        paned.add_widget(sw)
        paned.set_sizes(self._split_sizes)

        vtop.add_widget(paned, stretch=5)

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
            vtop.add_widget(btns, stretch=0)

        container.add_widget(vtop, stretch=5)
        self.gui_up = True

    def prepare(self, fitsimage):
        fitssettings = fitsimage.get_settings()
        fitsimage.add_callback('cursor-changed', self.motion_cb)
        fitsimage.add_callback('redraw', self.redraw_cb)
        fitssettings.get_setting('zoomlevel').add_callback(
            'set', self.zoomset_cb, fitsimage)

    def add_channel(self, viewer, chinfo):
        if not self.gui_up:
            return
        self.prepare(chinfo.fitsimage)

    def start(self):
        names = self.fv.get_channel_names()
        for name in names:
            channel = self.fv.get_channel(name)
            self.add_channel(self.fv, channel)

        # set up for currently focused channel
        channel = self.fv.get_channel_info()
        if channel is not None:
            self.focus_cb(self.fv, channel)

    def stop(self):
        self.gui_up = False
        self._split_sizes = self.w.splitter.get_sizes()
        return True

    # CALLBACKS

    def update_zoomviewer(self, channel):
        fitsimage = channel.fitsimage
        self.fitsimage_focus = fitsimage
        # Reflect transforms, colormap, etc.
        fitsimage.copy_attributes(self.zoomimage, self.copy_attrs)

        p_canvas = self.zoomimage.get_private_canvas()
        try:
            p_canvas.delete_object_by_tag(self.layer_tag)
        except Exception:
            pass
        canvas = fitsimage.get_canvas()
        p_canvas.add(canvas, tag=self.layer_tag)
        # NOTE: necessary for zoom viewer to correctly handle some settings
        # TODO: see if there is a cleaner way to do this
        self.zoomimage._imgobj = fitsimage._imgobj

        self.zoomimage.redraw(whence=0)

    def redo(self, channel, image):
        if not self.gui_up:
            return
        fitsimage = channel.fitsimage
        if fitsimage != self.fv.getfocus_viewer():
            return True

        self.update_zoomviewer(channel)

    def focus_cb(self, viewer, channel):
        if not self.gui_up:
            return
        self.update_zoomviewer(channel)

    def _zoomset(self, fitsimage, zoomlevel):
        if fitsimage != self.fitsimage_focus:
            return True
        if self.t_abszoom:
            # Did user set to absolute zoom?
            myzoomlevel = self.zoom_amount

        else:
            # Amount of zoom is a relative amount
            myzoomlevel = zoomlevel + self.zoom_amount

        self.logger.debug("zoomlevel=%d myzoom=%d" % (
            zoomlevel, myzoomlevel))
        self.zoomimage.zoom_to(myzoomlevel)
        return True

    def zoomset_cb(self, setting, zoomlevel, fitsimage):
        """This method is called when a main FITS widget changes zoom level.
        """
        if not self.gui_up:
            return
        fac_x, fac_y = fitsimage.get_scale_base_xy()
        fac_x_me, fac_y_me = self.zoomimage.get_scale_base_xy()
        if (fac_x != fac_x_me) or (fac_y != fac_y_me):
            alg = fitsimage.get_zoom_algorithm()
            self.zoomimage.set_zoom_algorithm(alg)
            self.zoomimage.set_scale_base_xy(fac_x, fac_y)
        return self._zoomset(self.fitsimage_focus, zoomlevel)

    # LOGIC

    def magnify_xy(self, fitsimage, data_x, data_y):
        # Show zoom image in zoom window
        self.zoom_x, self.zoom_y = data_x, data_y

        # If this is a new source, then update our widget with the
        # attributes of the source
        if self.fitsimage_focus != fitsimage:
            chname = self.fv.get_channel_name(fitsimage)
            channel = self.fv.get_channel(chname)
            self.focus_cb(self.fv, channel)

        # If the refresh interval has expired then update the zoom image;
        # otherwise (re)set the timer until the end of the interval.
        cur_time = time.time()
        elapsed = cur_time - self.update_time
        if elapsed > self.refresh_interval:
            # cancel timer
            self.zoomtask.clear()
            self.showzoom(data_x, data_y)
        else:
            # store needed data into the timer
            self.zoomtask.data.setvals(data_x=data_x, data_y=data_y)
            # calculate delta until end of refresh interval
            period = self.refresh_interval - elapsed
            # set timer
            self.zoomtask.cond_set(period)
        return True

    def motion_cb(self, fitsimage, button, data_x, data_y):
        if not self.gui_up:
            return
        self.magnify_xy(fitsimage, data_x, data_y)
        return False

    def redraw_cb(self, fitsimage, whence):
        if not self.gui_up:
            return
        if self.fitsimage_focus != fitsimage:
            return
        self.fitsimage_focus = None
        data_x, data_y = fitsimage.get_last_data_xy()[:2]
        self.magnify_xy(fitsimage, data_x, data_y)
        return False

    def showzoom_timer_cb(self, timer):
        if not self.gui_up:
            return
        data = timer.data
        self._zoom_data(self.zoomimage, data.data_x, data.data_y)

    def _zoom_data(self, fitsimage, data_x, data_y):
        fitsimage.set_pan(data_x, data_y)

    def showzoom(self, data_x, data_y):
        # set the zoom image
        self.fv.gui_do(self._zoom_data, self.zoomimage, data_x, data_y)

    def set_amount_cb(self, widget, val):
        """This method is called when 'Zoom Amount' control is adjusted.
        """
        self.zoom_amount = val
        zoomlevel = self.fitsimage_focus.get_zoom()
        self._zoomset(self.fitsimage_focus, zoomlevel)

    def set_absrel_cb(self, w, val):
        self.t_abszoom = not val
        zoomlevel = self.fitsimage_focus.get_zoom()
        return self._zoomset(self.fitsimage_focus, zoomlevel)

    def set_defaults(self):
        self.t_abszoom = True
        self.w.relative_zoom.set_state(not self.t_abszoom)
        self.w.zoom_amount.set_value(self.default_zoom)
        self.zoomimage.zoom_to(self.default_zoom)

    def zoomset(self, setting, zoomlevel, fitsimage):
        text = self.fv.scale2text(self.zoomimage.get_scale())
        self.w.zoom.set_text(text)

    def set_refresh_cb(self, w, val):
        self.refresh_interval = val / 1000.0
        self.logger.debug("Setting refresh time to %.4f sec" % (
            self.refresh_interval))

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'zoom'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Zoom', package='ginga')

# END
