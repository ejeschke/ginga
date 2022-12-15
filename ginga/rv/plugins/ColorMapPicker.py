# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``ColorMapPicker`` plugin is used to graphically browse and select a
colormap for a channel image viewer.

**Plugin Type: Global or Local**

``ColorMapPicker`` is a hybrid global/local plugin, which means it can
be invoked in either fashion.  If invoked as a local plugin then it is
associated with a channel, and an instance can be opened for each channel.
It can also be opened as a global plugin.

**Usage**

Operation of the plugin is very simple: the colormaps are displayed in
the form of colorbars and labels in the main view pane of the plugin.
Click on any one of the bars to set the colormap of the associated
channel (if invoked as a local plugin) or the currently active channel
(if invoked as a global plugin).

You can scroll vertically or use the scroll bars to move through the
colorbar samples.

.. note:: When the plugin starts for the first time, it will generate
          a bitmap RGB image of colorbars and labels corresponding to
          all the available colormaps.  This can take a few seconds
          depending on the number of colormaps installed.

          Colormaps are shown with the "ramp" intensity map applied.

"""
from ginga.pilw.ImageViewPil import CanvasView
from ginga.gw import Widgets, Viewers
from ginga import GingaPlugin
from ginga import cmap, RGBMap, RGBImage

__all__ = ['ColorMapPicker']


class ColorMapPicker(GingaPlugin.LocalPlugin):

    # this will be a shared image of all the colormaps, shared by all
    # instances
    cmaps_rgb_image = None
    max_y = 0

    def __init__(self, *args):
        # superclass defines some variables for us, like logger
        if len(args) == 2:
            super().__init__(*args)
        else:
            super().__init__(args[0], None)

        # read preferences for this plugin
        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_ColorMapPicker')
        self.settings.add_defaults(cbar_ht=20, cbar_wd=300, cbar_sep=10,
                                   cbar_pan_accel=1.0)
        self.settings.load(onError='silent')

        self._cmht = self.settings.get('cbar_ht', 20)
        self._cmwd = self.settings.get('cbar_wd', 300)
        self._cmsep = self.settings.get('cbar_sep', 10)
        self._cmxoff = 20
        self._wd = 300
        self._ht = 400

        # this will hold the resulting RGB image
        self.r_image = RGBImage.RGBImage(logger=self.logger)
        self.c_view = None
        self.cm_names = list(cmap.get_names())

    def build_gui(self, container):

        vbox = Widgets.VBox()
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        # construct an interactive viewer to view and scroll
        # the RGB image, and to let the user pick the cmap
        self.c_view = Viewers.CanvasView(logger=self.logger)
        c_v = self.c_view
        c_v.set_desired_size(self._wd, self._ht)
        c_v.enable_autozoom('off')
        c_v.enable_autocuts('off')
        c_v.set_pan(0, 0)
        c_v.scale_to(1, 1)
        c_v.transform(False, True, False)
        c_v.cut_levels(0, 255)
        c_v.set_bg(0.4, 0.4, 0.4)
        # for debugging
        c_v.set_name('cmimage')

        canvas = c_v.get_canvas()
        canvas.register_for_cursor_drawing(c_v)
        c_v.add_callback('cursor-down', self.select_cb)
        c_v.add_callback('scroll', self.scroll_cb)

        bd = c_v.get_bindings()
        bd.enable_pan(True)
        # disable zooming so scrolling can be used to pan up/down
        bd.enable_zoom(False)
        bd.enable_cmap(False)

        iw = Viewers.GingaScrolledViewerWidget(c_v)
        iw.resize(self._wd, self._ht)

        vbox.add_widget(iw, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(4)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)

    def select_cb(self, viewer, event, data_x, data_y):
        """Called when the user clicks on the color bar viewer.
        Calculate the index of the color bar they clicked on and
        set that color map in the current channel viewer.
        """
        if not (self._cmxoff <= data_x < self._cmwd):
            # need to click within the width of the bar
            return

        i = int(data_y / (self._cmht + self._cmsep))
        if 0 <= i < len(self.cm_names):
            name = self.cm_names[i]
            msg = "cmap => '%s'" % (name)
            self.logger.info(msg)

            if self.fitsimage is not None:
                # local plugin
                #self.fitsimage.onscreen_message(msg, delay=0.5)
                self.fitsimage.set_color_map(name)
            else:
                channel = self.fv.get_channel_info()
                if channel is not None:
                    viewer = channel.fitsimage
                    #viewer.onscreen_message(msg, delay=0.5)
                    viewer.set_color_map(name)

    def scroll_cb(self, viewer, direction, amt, data_x, data_y):
        """Called when the user scrolls in the color bar viewer.
        Pan up or down to show additional bars.
        """
        bd = viewer.get_bindings()
        direction = bd.get_direction(direction)
        pan_x, pan_y = viewer.get_pan()[:2]
        qty = self._cmsep * amt * self.settings.get('cbar_pan_accel', 1.0)
        if direction == 'up':
            pan_y -= qty
        else:
            pan_y += qty

        pan_y = min(max(pan_y, 0), ColorMapPicker._max_y)

        viewer.set_pan(pan_x, pan_y)

    def rebuild_cmaps(self, cm_names):
        """Builds a color RGB image containing color bars of all the
        possible color maps and their labels.
        """
        self.logger.info("building color maps image")
        ht, wd, sep = self._cmht, self._cmwd, self._cmsep
        # create a PIL viewer that we use to construct an RGB image
        # containing all the possible color bars and their labels
        p_v = CanvasView(logger=self.logger)
        p_v.configure_surface(self._wd, self._ht)
        p_v.enable_autozoom('off')
        p_v.enable_autocuts('off')
        p_v.set_scale_limits(1.0, 1.0)
        p_v.set_pan(0, 0)
        p_v.scale_to(1, 1)
        p_v.cut_levels(0, 255)
        p_v.set_bg(0.4, 0.4, 0.4)

        canvas = p_v.get_canvas()
        canvas.delete_all_objects()

        # get the list of color maps
        num_cmaps = len(cm_names)
        p_v.configure_surface(500, (ht + sep) * num_cmaps)

        # create a bunch of color bars and make one large compound object
        # with callbacks for clicking on individual color bars
        l2 = []
        ColorBar = canvas.get_draw_class('drawablecolorbar')
        Text = canvas.get_draw_class('text')
        dist = None
        #imap = ch_rgbmap.get_imap()
        logger = p_v.get_logger()

        for i, name in enumerate(cm_names):
            rgbmap = RGBMap.RGBMapper(logger, dist=dist)
            rgbmap.set_cmap(cmap.get_cmap(name))
            #rgbmap.set_imap(imap)
            x1, y1 = self._cmxoff, i * (ht + sep)
            x2, y2 = x1 + wd, y1 + ht
            cbar = ColorBar(x1, y1, x2, y2, cm_name=name, showrange=False,
                            rgbmap=rgbmap, coord='window')
            l2.append(cbar)
            l2.append(Text(x2 + sep, y2, name, color='white', fontsize=16,
                           coord='window'))

        Compound = canvas.get_draw_class('compoundobject')
        obj = Compound(*l2)
        canvas.add(obj)

        # set class vars used by all instances
        ColorMapPicker._max_y = y2
        ColorMapPicker.cmaps_rgb_image = p_v.get_image_as_array()

    # CALLBACKS

    def start(self):
        if self.fitsimage is None:
            channel = self.fv.get_channel_info()
            if channel is not None:
                viewer = channel.fitsimage
            else:
                viewer = self.c_view
        else:
            viewer = self.fitsimage
        if ColorMapPicker.cmaps_rgb_image is None:
            try:
                viewer.onscreen_message("building color maps...")
                self.fv.update_pending()
                self.rebuild_cmaps(self.cm_names)
            finally:
                viewer.onscreen_message(None)
        self.r_image.set_data(ColorMapPicker.cmaps_rgb_image)
        self.c_view.set_image(self.r_image)

    def close(self):
        if self.fitsimage is None:
            self.fv.stop_global_plugin(str(self))
        else:
            self.fv.stop_local_plugin(self.chname, str(self))
        return True

    def __str__(self):
        return 'colormappicker'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_ColorMapPicker', package='ginga')

# END
