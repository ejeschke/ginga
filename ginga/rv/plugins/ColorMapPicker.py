#
# ColorMapPicker.py -- ColorMapPicker plugin for Ginga reference viewer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.pilw.ImageViewPil import CanvasView
from ginga.gw import Widgets, Viewers
from ginga import GingaPlugin
from ginga import cmap, RGBMap, RGBImage


class ColorMapPicker(GingaPlugin.GlobalPlugin):
    """
    A plugin for graphically browsing and selecting a color map.

    USAGE:
    When the plugin starts for the first time, it will generate a
    bitmap RGB image of color bars and labels corresponding to all
    the available color maps.  This can take a few seconds depending
    on the number of color maps installed.

    The color maps are displayed in the view pane of the plugin.
    Click on any one of the bars to set the color map of the currently
    active channel image viewer.
    """

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(ColorMapPicker, self).__init__(fv)

        # read preferences for this plugin
        prefs = self.fv.get_preferences()
        self.settings = prefs.createCategory('plugin_ColorMapPicker')
        self.settings.addDefaults(cbar_ht=20, cbar_wd=300, cbar_sep=10,
                                  cbar_pan_accel=1.0)
        self.settings.load(onError='silent')

        self._cmht = self.settings.get('cbar_ht', 20)
        self._cmwd = self.settings.get('cbar_wd', 300)
        self._cmsep = self.settings.get('cbar_sep', 10)
        self._cmxoff = 20
        self._wd = 300
        self._ht = 400
        self._max_y = 0

        # create a PIL viewer that we use to construct an RGB image
        # containing all the possible color bars and their labels
        self.p_view = CanvasView(logger=self.logger)
        p_v = self.p_view
        p_v.configure_surface(self._wd, self._ht)
        p_v.enable_autozoom('off')
        p_v.enable_autocuts('off')
        p_v.set_scale_limits(1.0, 1.0)
        p_v.set_pan(0, 0)
        p_v.zoom_to(1)
        p_v.cut_levels(0, 255)
        p_v.set_bg(0.4, 0.4, 0.4)

        # this will hold the resulting RGB image
        self.r_image = RGBImage.RGBImage(logger=self.logger)
        self.c_view = None
        self.cm_names = []

    def build_gui(self, container):

        vbox = Widgets.VBox()
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        # construct an interaactive viewer to view and scroll
        # the RGB image, and to let the user pick the cmap
        self.c_view = Viewers.CanvasView(logger=self.logger)
        c_v = self.c_view
        c_v.set_desired_size(self._wd, self._ht)
        c_v.enable_autozoom('off')
        c_v.enable_autocuts('off')
        c_v.set_pan(0, 0)
        c_v.zoom_to(1)
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
        bd.enable_pan(False)
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
        btns.add_widget(btn)
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

        pan_y = min(max(pan_y, 0), self._max_y)

        viewer.set_pan(pan_x, pan_y)

    def rebuild_cmaps(self):
        """Builds a color RGB image containing color bars of all the
        possible color maps and their labels.
        """
        self.logger.info("building color maps image")
        ht, wd, sep = self._cmht, self._cmwd, self._cmsep
        viewer = self.p_view

        # put the canvas into pick mode
        canvas = viewer.get_canvas()
        canvas.delete_all_objects()

        # get the list of color maps
        cm_names = self.cm_names
        num_cmaps = len(cm_names)
        viewer.configure_surface(500, (ht + sep) * num_cmaps)

        # create a bunch of color bars and make one large compound object
        # with callbacks for clicking on individual color bars
        l2 = []
        ColorBar = canvas.get_draw_class('drawablecolorbar')
        Text = canvas.get_draw_class('text')
        #ch_rgbmap = chviewer.get_rgbmap()
        #dist = ch_rgbmap.get_dist()
        dist = None
        #imap = ch_rgbmap.get_imap()
        logger = viewer.get_logger()

        for i, name in enumerate(cm_names):
            rgbmap = RGBMap.RGBMapper(logger, dist=dist)
            rgbmap.set_cmap(cmap.get_cmap(name))
            #rgbmap.set_imap(imap)
            x1, y1 = self._cmxoff, i * (ht + sep)
            x2, y2 = x1 + wd, y1 + ht
            cbar = ColorBar(x1, y1, x2, y2, cm_name=name, showrange=False,
                            rgbmap=rgbmap, coord='canvas')
            l2.append(cbar)
            l2.append(Text(x2+sep, y2, name, color='white', fontsize=16,
                           coord='canvas'))

        Compound = canvas.get_draw_class('compoundobject')
        obj = Compound(*l2)
        canvas.add(obj)

        self._max_y = y2

        rgb_img = self.p_view.get_image_as_array()
        self.r_image.set_data(rgb_img)

    def start(self):
        if len(self.cm_names) == 0:
            self.cm_names = list(cmap.get_names())
            self.c_view.onscreen_message("building color maps...")
            self.fv.update_pending()
            self.rebuild_cmaps()
            self.c_view.onscreen_message(None)
        self.c_view.set_image(self.r_image)

    # CALLBACKS

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'colormappicker'

#END
