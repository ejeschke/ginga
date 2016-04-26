#
# ColorBar.py -- color bar widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Callback
from ginga import RGBMap

from ginga.gw import Viewers
from ginga.canvas.types import utils

class ColorBarError(Exception):
    pass

class ColorBar(Callback.Callbacks):

    def __init__(self, logger, rgbmap=None, link=False):
        Callback.Callbacks.__init__(self)

        self.logger = logger
        self.link_rgbmap = link
        if not rgbmap:
            rgbmap = RGBMap.RGBMapper(logger)

        self._start_x = 0
        self._sarr = None

        cbar = Viewers.CanvasView(logger=self.logger)
        width, height = 1, 16
        cbar.set_desired_size(width, height)
        cbar.enable_autozoom('off')
        cbar.enable_autocuts('off')

        # JPEG rendering makes for mushy text
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
        cbar.add_callback('none-move', self.none_move_cb)
        cbar.add_callback('zoom-scroll', self.scroll_cb)

        #cbar.configure(width, height)
        iw = Viewers.GingaViewerWidget(viewer=cbar)
        self.widget = iw
        iw.resize(width, height)

        canvas = self.cbar_view.get_canvas()
        self.cbar = utils.ColorBar(offset=0, height=height, rgbmap=rgbmap)
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
        self.redraw()

    def set_cmap(self, cm):
        self.rgbmap.set_cmap(cm)
        self.redraw()

    def set_imap(self, im, reset=False):
        self.rgbmap.set_imap(im)
        self.redraw()

    def set_range(self, loval, hival):
        self.cbar_view.cut_levels(loval, hival)
        self.redraw()

    def resize_cb(self, viewer, width, height):
        self.logger.info("colorbar resized to %dx%d" % (width, height))
        self.cbar.height = height
        self.cbar_view.redraw(whence=0)

    def redraw(self):
        self.cbar_view.redraw()

    def shift_colormap(self, pct):
        if self._sarr is None:
            return
        self.rgbmap.set_sarr(self._sarr, callback=False)
        self.rgbmap.shift(pct)
        self.redraw()

    def stretch_colormap(self, pct):
        self.rgbmap.stretch(pct)
        self.redraw()

    def rgbmap_cb(self, rgbmap):
        self.redraw()

    def cursor_press_cb(self, canvas, event, data_x, data_y):
        x, y = event.viewer.get_last_win_xy()
        self._start_x = x
        sarr = self.rgbmap.get_sarr()
        self._sarr = sarr.copy()
        return True

    def cursor_release_cb(self, canvas, event, data_x, data_y):
        x, y = event.viewer.get_last_win_xy()
        dx = x - self._start_x
        wd, ht = event.viewer.get_window_size()
        pct = float(dx) / float(wd)
        #print "dx=%f wd=%d pct=%f" % (dx, wd, pct)
        self.shift_colormap(pct)
        return True

    def draw_release_cb(self, canvas, event, data_x, data_y):
        self.rgbmap.reset_cmap()
        return True

    def cursor_drag_cb(self, canvas, event, data_x, data_y):
        x, y = event.viewer.get_last_win_xy()
        wd, ht = event.viewer.get_window_size()

        dx = x - self._start_x
        pct = float(dx) / float(wd)
        #print "dx=%f wd=%d pct=%f" % (dx, wd, pct)
        self.shift_colormap(pct)
        return True

    def none_move_cb(self, canvas, event, data_x, data_y):
        x, y = event.viewer.get_last_win_xy()
        wd, ht = event.viewer.get_window_size()
        dist = self.rgbmap.get_dist()
        pct = float(x) / float(wd)
        rng_pct = dist.get_dist_pct(pct)
        loval, hival = event.viewer.get_cut_levels()
        value = float(loval + (rng_pct * (hival - loval)))
        self.make_callback('motion', value, event)
        return True

    def scroll_cb(self, viewer, event):
        direction = event.direction
        if (direction < 90.0) or (direction > 270.0):
            # up
            scale_factor = 1.1
        else:
            # not up!
            scale_factor = 0.9

        self.stretch_colormap(scale_factor)

        self.make_callback('scroll', event)

#END
