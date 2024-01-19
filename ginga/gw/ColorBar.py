#
# ColorBar.py -- color bar widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.misc import Callback, Settings
from ginga import RGBMap

from ginga.gw import Viewers
from ginga.canvas.types import utils


class ColorBarError(Exception):
    pass


class ColorBar(Callback.Callbacks):

    def __init__(self, logger, rgbmap=None, link=False, settings=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger
        self.link_rgbmap = link
        if not rgbmap:
            rgbmap = RGBMap.RGBMapper(logger)
        # Create settings and set defaults
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings

        self._start_x = 0
        self._brightness = 0.5

        cbar = Viewers.CanvasView(logger=self.logger)
        width, height = 1, self.settings.get('cbar_height', 36)
        cbar.set_desired_size(width, height)
        cbar.enable_autozoom('off')
        cbar.enable_autocuts('off')

        # In web backend, JPEG rendering makes for mushy text
        ## settings = cbar.get_settings()
        ## settings.set(html5_canvas_format='png')

        # to respond quickly to contrast adjustment
        #cbar.defer_lagtime = 0.005
        cbar.set_bg(0.4, 0.4, 0.4)
        # for debugging
        cbar.set_name('colorbar')
        self.cbar_view = cbar

        # add callbacks for contrast adjustment, etc.
        cbar.add_callback('configure', self.resize_cb)
        cbar.add_callback('cursor-down', self.cursor_press_cb)
        cbar.add_callback('cursor-move', self.cursor_drag_cb)
        cbar.add_callback('cursor-up', self.cursor_release_cb)
        cbar.add_callback('draw-up', self.draw_release_cb)
        cbar.add_callback('btn-move-none', self.none_move_cb)
        cbar.add_callback('scroll-none', self.scroll_cb)
        cbar.add_callback('pinch-none', self.pinch_cb)

        #cbar.configure(width, height)
        iw = Viewers.GingaViewerWidget(viewer=cbar)
        self.widget = iw
        # NOTE: this resize causes the widget to lose it's height somehow
        # under Gtk due to the hack to allow resize down (see gtk3w/Widget.py)
        #iw.resize(width, height)

        fontsize = self.settings.get('fontsize', 12)
        canvas = self.cbar_view.get_canvas()
        self.cbar = utils.ColorBar(offset=0, height=height, rgbmap=rgbmap,
                                   fontsize=fontsize)
        canvas.add(self.cbar, tag='colorbar')

        self.set_rgbmap(rgbmap)

        # For callbacks
        for name in ('motion', 'scroll'):
            self.enable_callback(name)

    def get_widget(self):
        return self.widget

    def get_rgbmap(self):
        return self.rgbmap

    def set_rgbmap(self, rgbmap):
        self.rgbmap = rgbmap
        self.cbar.rgbmap = rgbmap
        # TODO: figure out if we can get rid of this link option
        if self.link_rgbmap:
            rgbmap.add_callback('changed', self.rgbmap_cb)
        self.redraw(whence=2)

    def set_cmap(self, cm):
        self.rgbmap.set_cmap(cm)
        self.redraw(whence=2)

    def set_imap(self, im, reset=False):
        self.rgbmap.set_imap(im)
        self.redraw(whence=2)

    def set_range(self, loval, hival):
        self.cbar_view.cut_levels(loval, hival)
        self.redraw(whence=2)

    def resize_cb(self, viewer, width, height):
        self.logger.debug("colorbar resized to %dx%d" % (width, height))
        self.cbar.height = height
        self.cbar_view.redraw(whence=0)

    def redraw(self, whence=0):
        self.cbar_view.redraw(whence=whence)

    def shift_colormap(self, delta_pct):
        t_ = self.rgbmap.get_settings()
        pct = np.clip(self._brightness - delta_pct, 0.0, 1.0)
        t_.set(brightness=pct)

    def stretch_colormap(self, pct):
        t_ = self.rgbmap.get_settings()
        pct = np.clip(t_['contrast'] * pct, 0.0, 1.0)
        t_.set(contrast=pct)

    def rgbmap_cb(self, rgbmap):
        self.redraw(whence=2)

    def cursor_press_cb(self, canvas, event, data_x, data_y):
        x, y = event.viewer.get_last_win_xy()
        self._start_x = x
        self._brightness = self.rgbmap.get_settings().get('brightness', 0.5)
        return True

    def cursor_release_cb(self, canvas, event, data_x, data_y):
        x, y = event.viewer.get_last_win_xy()
        dx = x - self._start_x
        wd, ht = event.viewer.get_window_size()
        pct = float(dx) / float(wd)
        self.shift_colormap(pct)
        return True

    def draw_release_cb(self, canvas, event, data_x, data_y):
        self.rgbmap.restore_cmap()
        return True

    def cursor_drag_cb(self, canvas, event, data_x, data_y):
        x, y = event.viewer.get_last_win_xy()
        wd, ht = event.viewer.get_window_size()

        dx = x - self._start_x
        pct = float(dx) / float(wd)
        self.shift_colormap(pct)
        return True

    def none_move_cb(self, canvas, event, data_x, data_y):
        if event.button == 'nobtn':
            x, y = event.viewer.get_last_win_xy()
            wd, ht = event.viewer.get_window_size()
            dist = self.rgbmap.get_dist()
            pct = float(x) / float(wd)
            rng_pct = dist.get_dist_pct(pct)
            loval, hival = event.viewer.get_cut_levels()
            value = float(loval + (rng_pct * (hival - loval)))
            self.make_callback('motion', value, event)
            return True
        return False

    def scroll_cb(self, viewer, event):
        direction = event.direction
        if (direction < 90.0) or (direction > 270.0):
            # up
            scale_factor = 0.9
        else:
            # not up!
            scale_factor = 1.1

        self.stretch_colormap(scale_factor)

        self.make_callback('scroll', event)

    def pinch_cb(self, viewer, event):
        scale_factor = event.scale
        self.stretch_colormap(scale_factor)
