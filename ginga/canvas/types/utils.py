#
# utils.py -- classes for special shapes added to Ginga canvases.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       register_canvas_types, get_canvas_type,
                                       colors_plus_none)
from ginga.misc.ParamSet import Param


class ColorBar(CanvasObjectBase):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='height', type=int, default=14,
                  min=0, max=200, widget='spinbutton', incr=1,
                  description="Height of colorbar in pixels"),
            Param(name='offset', type=int, default=10,
                  min=0, max=200, widget='spinbutton', incr=1,
                  description="Offset in pixels from the top or bottom of the window"),
            Param(name='side', type=str,
                  default='bottom', valid=['top', 'bottom'],
                  description="Choose side of window to anchor color bar"),
            Param(name='showrange', type=_bool,
                  default=True, valid=[False, True],
                  description="Show the range in the colorbar"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=8,
                  min=8, max=72,
                  description="Font size of text (default: 8)"),
            Param(name='linewidth', type=int, default=1,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='solid',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: solid)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='black',
                  description="Color of outline"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            ]

    def __init__(self, height=14, offset=10, side='bottom', showrange=True,
                 font='Sans Serif', fontsize=8,
                 color='black', linewidth=1, linestyle='solid', alpha=1.0,
                 fillalpha=1.0, rgbmap=None, optimize=True, **kwdargs):
        super(ColorBar, self).__init__(height=height, offset=offset, side=side,
                                       showrange=showrange,
                                       font=font, fontsize=fontsize,
                                       color=color, linewidth=linewidth,
                                       linestyle=linestyle, alpha=alpha,
                                       fillalpha=fillalpha, **kwdargs)
        self.rgbmap = rgbmap
        self.kind = 'colorbar'

        # for drawing range
        self.t_spacing = 40
        self.tick_ht = 4


    def draw(self, viewer):
        rgbmap = self.rgbmap
        if rgbmap is None:
            rgbmap = viewer.get_rgbmap()

        width, height = viewer.get_window_size()

        loval, hival = viewer.get_cut_levels()

        cr = viewer.renderer.setup_cr(self)

        # Calculate reasonable spacing for range numbers
        cr.set_font(self.font, self.fontsize, color=self.color,
                    alpha=self.alpha)
        text = "%.4g" % (hival)
        txt_wd, txt_ht = cr.text_extents(text)
        avg_pixels_per_range_num = self.t_spacing + txt_wd

        pxwd, pxht = width, max(self.height, txt_ht + self.tick_ht + 2)
        #print("colormap size is %d,%d" % (pxwd, pxht))

        # calculate intervals for range numbers
        nums = max(int(pxwd // avg_pixels_per_range_num), 1)
        spacing = 256 // nums
        _interval = { i*spacing: True for i in range(nums) }
        #self.logger.debug("nums=%d spacing=%d intervals=%s" % (
        #    nums, spacing, _interval))

        y_base = self.offset
        if self.side == 'bottom':
            y_base = height - self.offset - pxht

        x1 = 0; x2 = pxwd
        clr_wd = pxwd // 256
        rem_px = x2 - (clr_wd * 256)
        if rem_px > 0:
            ival = 256 // rem_px
        else:
            ival = 0
        clr_ht = pxht
        #print("clr is %dx%d width=%d rem=%d ival=%d" % (
        #       width, height, clr_wd, rem_px, ival))

        dist = rgbmap.get_dist()

        j = ival; off = 0
        range_pts = []
        for i in range(256):

            wd = clr_wd
            if rem_px > 0:
                j -= 1
                if j == 0:
                    rem_px -= 1
                    j = ival
                    wd += 1
            x = off

            (r, g, b) = rgbmap.get_rgbval(i)
            color = (r/255., g/255., b/255.)

            cr.set_line(color, linewidth=0)
            cr.set_fill(color, alpha=self.fillalpha)

            cx1, cy1, cx2, cy2 = x, y_base, x+wd, y_base+pxht
            cr.draw_polygon(((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2)))

            # Draw range scale if we are supposed to
            if self.showrange and i in _interval:
                cb_pct = float(x) / pxwd
                # get inverse of distribution function and calculate value
                # at this position
                rng_pct = dist.get_dist_pct(cb_pct)
                val = float(loval + (rng_pct * (hival - loval)))
                text = "%.4g" % (val)

                rx = x
                ry = y_base + self.tick_ht + txt_ht
                ryy = y_base
                range_pts.append((rx, ry, ryy, text))

            off += wd

        cr.set_line(color=self.color, linewidth=1, alpha=self.alpha)

        # draw optional border
        if self.linewidth > 0:
            cx1, cy1, cx2, cy2 = 0, y_base, wd, y_base+pxht
            cpoints = ((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2))
            cr.draw_polygon(cpoints)

        # draw range
        if self.showrange:
            cr.set_font(self.font, self.fontsize, color=self.color,
                    alpha=self.alpha)
            for (cx, cy, cyy, text) in range_pts:
                # tick
                cr.draw_line(cx, cyy, cx, cyy+self.tick_ht)
                # number
                cr.draw_text(cx, cy, text)


class ModeIndicator(CanvasObjectBase):
    """
    Shows a mode indicator.

    NOTE: to get this to work properly, you need to add a callback to your viewer's
    bindmapper like so:

        bm = viewer.get_bindmap()
        bm.add_callback('mode-set', lambda *args: viewer.redraw(whence=3))

    """
    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='corner', type=str,
                  default='lr', valid=['ll', 'lr', 'ul', 'ur'],
                  description="Choose corner of window to anchor mode indicator"),
            Param(name='offset', type=int, default=10,
                  min=0, max=200, widget='spinbutton', incr=1,
                  description="Offset in pixels from the right and bottom of the window"),
            Param(name='font', type=str, default='Sans Serif',
                  description="Font family for text"),
            Param(name='fontsize', type=int, default=None,
                  min=8, max=72,
                  description="Font size of text (default: vary by scale)"),
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='yellow',
                  description="Color of text"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
            ]

    def __init__(self, corner='lr', offset=10, font='Sans Serif', fontsize=12,
                 color='yellow', alpha=1.0, fillalpha=1.0, **kwdargs):
        super(ModeIndicator, self).__init__(corner=corner, offset=offset,
                                            font=font, fontsize=fontsize,
                                            color=color, alpha=alpha,
                                            fillalpha=fillalpha, **kwdargs)
        self.kind = 'modeindicator'
        self.xpad = 8
        self.ypad = 4

    def draw(self, viewer):

        win_wd, win_ht = self.viewer.get_window_size()

        bm = viewer.get_bindmap()
        mode, mode_type = bm.current_mode()

        if mode is None:
            return

        cr = viewer.renderer.setup_cr(self)

        if mode_type == 'locked':
            text = '%s [L]' % (mode)
        else:
            text = mode

        cr.set_font(self.font, self.fontsize, color=self.color,
                    alpha=self.alpha)
        txt_wd, txt_ht = cr.text_extents(text)

        # draw bg
        box_wd, box_ht = 2 * self.xpad + txt_wd, 2 * self.ypad + txt_ht
        if self.corner == 'lr':
            x_base, y_base = win_wd - self.offset - box_wd, win_ht - self.offset - box_ht
        elif self.corner == 'll':
            x_base, y_base = self.offset, win_ht - self.offset - box_ht
        if self.corner == 'ur':
            x_base, y_base = win_wd - self.offset - box_wd, self.offset
        if self.corner == 'ul':
            x_base, y_base = self.offset, self.offset

        cr.set_line('black', linewidth=0)
        cr.set_fill('black', alpha=self.fillalpha)

        cx1, cy1, cx2, cy2 = x_base, y_base, x_base + box_wd, y_base + box_ht
        cr.draw_polygon(((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2)))

        # draw fg
        cr.set_line(color=self.color, linewidth=1, alpha=self.alpha)

        cx, cy = x_base + self.xpad, y_base + txt_ht + self.ypad
        cr.draw_text(cx, cy, text)



# register our types
register_canvas_types(dict(colorbar=ColorBar, modeindicator=ModeIndicator))
