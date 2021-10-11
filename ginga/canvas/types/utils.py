#
# utils.py -- classes for special shapes added to Ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.canvas.CanvasObject import (CanvasObjectBase, _bool, _color,
                                       register_canvas_types,
                                       colors_plus_none, coord_names)
from .basic import RectangleP
from ginga.misc.ParamSet import Param


class ColorBar(CanvasObjectBase):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='height', type=int, default=36,
                  min=0, max=200, widget='spinbutton', incr=1,
                  description="Height of colorbar in pixels"),
            Param(name='offset', type=int, default=40,
                  min=0, max=200, widget='spinbutton', incr=1,
                  description="Offset in pixels from the top or bottom of the window"),
            Param(name='side', type=str,
                  default='bottom', valid=['top', 'bottom'],
                  description="Choose side of window to anchor color bar"),
            Param(name='showrange', type=_bool,
                  default=True, valid=[False, True],
                  description="Show the range in the colorbar"),
            Param(name='font', type=str, default='fixed',
                  description="Font family for text"),
            Param(name='fontsize', type=float, default=8.0,
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
                  description="Color of text"),
            Param(name='bgcolor',
                  valid=colors_plus_none, type=_color, default='white',
                  description="Color of text background"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
        ]

    def __init__(self, height=36, offset=40, side='bottom', showrange=True,
                 font='fixed', fontsize=8,
                 color='black', bgcolor='white',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 fillalpha=1.0, rgbmap=None, optimize=True, **kwdargs):
        super(ColorBar, self).__init__(height=height, offset=offset, side=side,
                                       showrange=showrange,
                                       font=font, fontsize=fontsize,
                                       color=color, bgcolor=bgcolor,
                                       linewidth=linewidth,
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
        tr = viewer.tform['window_to_native']

        # Calculate reasonable spacing for range numbers
        cr.set_font(self.font, self.fontsize, color=self.color,
                    alpha=self.alpha)
        hitxt = "%.4g" % (hival)
        lotxt = "%.4g" % (loval)
        txt_wdh, txt_hth = cr.text_extents(hitxt)
        txt_wdl, txt_htl = cr.text_extents(lotxt)
        txt_wd = max(txt_wdh, txt_wdl)
        avg_pixels_per_range_num = self.t_spacing + txt_wd
        scale_ht = 0
        if self.showrange:
            scale_ht = txt_hth + self.tick_ht + 2

        pxwd, pxht = width, max(self.height, scale_ht)

        maxc = max(rgbmap.maxc + 1, 256)
        maxf = float(maxc)

        # calculate intervals for range numbers
        nums = max(int(pxwd // avg_pixels_per_range_num), 1)
        spacing = maxc // nums
        start = spacing // 2
        _interval = {start + i * spacing: True for i in range(0, nums - 1)}
        ## self.logger.debug("nums=%d spacing=%d intervals=%s" % (
        ##     nums, spacing, _interval))

        y_base = self.offset
        if self.side == 'bottom':
            y_base = height - self.offset - pxht
        y_top = y_base + self.height

        x2 = pxwd
        clr_wd = pxwd // maxc
        rem_px = x2 - (clr_wd * maxc)
        if rem_px > 0:
            ival = maxc // rem_px
        else:
            ival = 0
        clr_ht = pxht - scale_ht

        dist = rgbmap.get_dist()

        j = ival
        off = 0
        range_pts = []
        for i in range(maxc):

            wd = clr_wd
            if rem_px > 0:
                j -= 1
                if j == 0:
                    rem_px -= 1
                    j = ival
                    wd += 1
            x = off

            (r, g, b) = rgbmap.get_rgbval(i)
            color = (r / maxf, g / maxf, b / maxf)

            cr.set_line(color, linewidth=0)
            cr.set_fill(color, alpha=self.fillalpha)

            cx1, cy1, cx2, cy2 = x, y_base, x + wd, y_base + clr_ht
            cr.draw_polygon(tr.to_(((cx1, cy1), (cx2, cy1),
                                    (cx2, cy2), (cx1, cy2))))

            # Draw range scale if we are supposed to
            if self.showrange and i in _interval:
                cb_pct = float(x) / pxwd
                # get inverse of distribution function and calculate value
                # at this position
                rng_pct = dist.get_dist_pct(cb_pct)
                val = float(loval + (rng_pct * (hival - loval)))
                text = "%.4g" % (val)

                rx = x
                ry = y_top - scale_ht
                ryy = y_top
                range_pts.append((rx, ry, ryy, text))

            off += wd

        # draw range
        if self.showrange:
            # draw background
            cr.set_fill(self.bgcolor, alpha=self.fillalpha)
            cr.set_line(self.bgcolor, linewidth=0)

            x = 0
            cx1, cy1, cx2, cy2 = x, y_top - scale_ht, x + pxwd, y_top
            cp = tr.to_(((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2)))
            cr.draw_polygon(cp)

            cr.set_line(color=self.color, linewidth=1, alpha=self.alpha)
            cr.draw_line(cp[0][0], cp[0][1], cp[1][0], cp[1][1])

            cr.set_font(self.font, self.fontsize, color=self.color,
                        alpha=self.alpha)
            for (cx, cy, cyy, text) in range_pts:
                cp = tr.to_(((cx, cy), (cx, cy + self.tick_ht), (cx, cyy - 2)))
                # tick
                cr.draw_line(cp[0][0], cp[0][1], cp[1][0], cp[1][1])
                # number
                cr.draw_text(cp[2][0], cp[2][1], text)

        # draw optional border
        if self.linewidth > 0:
            cr.set_fill(self.bgcolor, alpha=0.0)
            cx1, cy1, cx2, cy2 = 0, y_base, wd, y_top
            cpoints = ((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2))
            cr.draw_polygon(tr.to_(cpoints))


class DrawableColorBarP(RectangleP):

    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='coord', type=str, default='data',
                  valid=coord_names,
                  description="Set type of coordinates"),
            Param(name='x1', type=float, default=0.0, argpos=0,
                  description="First X coordinate of object"),
            Param(name='y1', type=float, default=0.0, argpos=1,
                  description="First Y coordinate of object"),
            Param(name='x2', type=float, default=0.0, argpos=2,
                  description="Second X coordinate of object"),
            Param(name='y2', type=float, default=0.0, argpos=3,
                  description="Second Y coordinate of object"),
            Param(name='cm_name', type=str, default='gray',
                  description="Color map name to draw"),
            Param(name='showrange', type=_bool,
                  default=True, valid=[False, True],
                  description="Show the range in the colorbar"),
            Param(name='font', type=str, default='fixed',
                  description="Font family for text"),
            Param(name='fontsize', type=float, default=8,
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
            Param(name='bgcolor',
                  valid=colors_plus_none, type=_color, default='white',
                  description="Color of text background"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='fillalpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of fill"),
        ]

    def __init__(self, p1, p2, showrange=True,
                 font='fixed', fontsize=8,
                 color='black', bgcolor='white',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 fillalpha=1.0, rgbmap=None, optimize=True, **kwdargs):
        RectangleP.__init__(self, p1, p2,
                            font=font, fontsize=fontsize,
                            color=color, bgcolor=bgcolor, linewidth=linewidth,
                            linestyle=linestyle, alpha=alpha,
                            fillalpha=fillalpha, **kwdargs)
        self.showrange = showrange
        self.rgbmap = rgbmap
        self.kind = 'drawablecolorbar'

        # for drawing range
        self.t_spacing = 40
        self.tick_ht = 4

    def draw(self, viewer):
        rgbmap = self.rgbmap
        if rgbmap is None:
            rgbmap = viewer.get_rgbmap()

        cpoints = self.get_cpoints(viewer)
        cx1, cy1 = cpoints[0]
        cx2, cy2 = cpoints[2]
        cx1, cy1, cx2, cy2 = self.swapxy(cx1, cy1, cx2, cy2)
        width, height = abs(cx2 - cx1), abs(cy2 - cy1)

        loval, hival = viewer.get_cut_levels()

        cr = viewer.renderer.setup_cr(self)
        tr = viewer.tform['window_to_native']

        # Calculate reasonable spacing for range numbers
        cr.set_font(self.font, self.fontsize, color=self.color,
                    alpha=self.alpha)
        hitxt = "%.4g" % (hival)
        lotxt = "%.4g" % (loval)
        txt_wdh, txt_hth = cr.text_extents(hitxt)
        txt_wdl, txt_htl = cr.text_extents(lotxt)
        txt_wd = max(txt_wdh, txt_wdl)
        avg_pixels_per_range_num = self.t_spacing + txt_wd
        scale_ht = 0
        if self.showrange:
            scale_ht = txt_hth + self.tick_ht + 2

        pxwd, pxht = width, max(height, scale_ht)
        pxwd, pxht = max(pxwd, 1), max(pxht, 1)

        maxc = max(rgbmap.maxc + 1, 256)
        maxf = float(maxc)

        # calculate intervals for range numbers
        nums = max(int(pxwd // avg_pixels_per_range_num), 1)
        spacing = maxc // nums
        start = spacing // 2
        _interval = {start + i * spacing: True for i in range(0, nums - 1)}

        x_base, y_base, x_top, y_top = cx1, cy1, cx2, cy2

        x2 = pxwd
        clr_wd = pxwd // maxc
        rem_px = x2 - (clr_wd * maxc)
        if rem_px > 0:
            ival = maxc // rem_px
        else:
            ival = 0
        clr_ht = pxht - scale_ht

        dist = rgbmap.get_dist()

        j = ival
        off = cx1
        range_pts = []
        for i in range(maxc):

            wd = clr_wd
            if rem_px > 0:
                j -= 1
                if j == 0:
                    rem_px -= 1
                    j = ival
                    wd += 1
            x = off

            (r, g, b) = rgbmap.get_rgbval(i)
            color = (r / maxf, g / maxf, b / maxf)

            cr.set_line(color, linewidth=0)
            cr.set_fill(color, alpha=self.fillalpha)

            cx1, cy1, cx2, cy2 = x, y_base, x + wd, y_base + clr_ht
            cr.draw_polygon(tr.to_(((cx1, cy1), (cx2, cy1),
                                    (cx2, cy2), (cx1, cy2))))

            # Draw range scale if we are supposed to
            if self.showrange and i in _interval:
                cb_pct = float(x) / pxwd
                # get inverse of distribution function and calculate value
                # at this position
                rng_pct = dist.get_dist_pct(cb_pct)
                val = float(loval + (rng_pct * (hival - loval)))
                text = "%.4g" % (val)

                rx = x
                ry = y_top - scale_ht
                ryy = y_top
                range_pts.append((rx, ry, ryy, text))

            off += wd

        # draw range
        if self.showrange:
            # draw background
            cr.set_fill(self.bgcolor, alpha=self.fillalpha)
            cr.set_line(self.bgcolor, linewidth=0)

            cx1, cy1, cx2, cy2 = x_base, y_top - scale_ht, x_top, y_top
            cp = tr.to_(((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2)))
            cr.draw_polygon(cp)

            cr.set_line(color=self.color, linewidth=1, alpha=self.alpha)
            cr.draw_line(cp[0][0], cp[0][1], cp[1][0], cp[1][1])

            cr.set_font(self.font, self.fontsize, color=self.color,
                        alpha=self.alpha)
            for (cx, cy, cyy, text) in range_pts:
                cp = tr.to_(((cx, cy), (cx, cy + self.tick_ht), (cx, cyy - 2)))
                # tick
                cr.draw_line(cp[0][0], cp[0][1], cp[1][0], cp[1][1])
                # number
                cr.draw_text(cp[2][0], cp[2][1], text)

        # draw optional border
        if self.linewidth > 0:
            cr.set_fill(self.bgcolor, alpha=0.0)
            cx1, cy1, cx2, cy2 = x_base, y_base, x_top, y_top
            cpoints = ((cx1, cy1), (cx2, cy1), (cx2, cy2), (cx1, cy2))
            cr.draw_polygon(tr.to_(cpoints))


class DrawableColorBar(DrawableColorBarP):

    @classmethod
    def idraw(cls, canvas, cxt):
        return cls(cxt.start_x, cxt.start_y, cxt.x, cxt.y, **cxt.drawparams)

    def __init__(self, x1, y1, x2, y2, showrange=True,
                 font='fixed', fontsize=8,
                 color='black', bgcolor='white',
                 linewidth=1, linestyle='solid', alpha=1.0,
                 fillalpha=1.0, rgbmap=None, optimize=True, **kwdargs):
        DrawableColorBarP.__init__(self, (x1, y1), (x2, y2),
                                   showrange=showrange, font=font,
                                   fontsize=fontsize,
                                   color=color, bgcolor=bgcolor,
                                   linewidth=linewidth, linestyle=linestyle,
                                   alpha=alpha, fillalpha=fillalpha,
                                   rgbmap=rgbmap, optimize=optimize, **kwdargs)


class ModeIndicator(CanvasObjectBase):
    """
    Shows a mode indicator.

    NOTE: to get this to work properly, you need to add a callback to your
    viewer's bindmapper like so:

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
            Param(name='fontsize', type=float, default=None,
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
        self.modetbl = dict(locked='L', softlock='S', held='H', oneshot='O')

    def draw(self, viewer):

        win_wd, win_ht = viewer.get_window_size()

        bm = viewer.get_bindmap()
        mode, mode_type = bm.current_mode()

        if mode is None:
            return

        cr = viewer.renderer.setup_cr(self)
        tr = viewer.tform['window_to_native']

        text = mode
        if mode_type in self.modetbl:
            text += ' [%s]' % self.modetbl[mode_type]

        color = 'cyan' if mode == 'meta' else self.color

        cr.set_font(self.font, self.fontsize, color=color,
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
        cr.draw_polygon(tr.to_(((cx1, cy1), (cx2, cy1),
                                (cx2, cy2), (cx1, cy2))))

        # draw fg
        cr.set_line(color=color, linewidth=1, alpha=self.alpha)

        cx, cy = x_base + self.xpad, y_base + txt_ht + self.ypad
        cx, cy = tr.to_((cx, cy))
        cr.draw_text(cx, cy, text)


class FocusIndicator(CanvasObjectBase):
    """
    Shows an indicator that the canvas has the keyboard/mouse focus.
    This is shown by a rectangle around the perimeter of the window.

    NOTE: to get this to work properly, you need to add a callback to your
    viewer like so:

        viewer.add_callback('focus', focus_obj.focus_cb)

    """
    @classmethod
    def get_params_metadata(cls):
        return [
            Param(name='color',
                  valid=colors_plus_none, type=_color, default='white',
                  description="Color of text"),
            Param(name='alpha', type=float, default=1.0,
                  min=0.0, max=1.0, widget='spinfloat', incr=0.05,
                  description="Opacity of outline"),
            Param(name='linewidth', type=int, default=2,
                  min=0, max=20, widget='spinbutton', incr=1,
                  description="Width of outline"),
            Param(name='linestyle', type=str, default='dash',
                  valid=['solid', 'dash'],
                  description="Style of outline (default: dash)"),
        ]

    def __init__(self, color='white', linewidth=2, linestyle='dash',
                 alpha=1.0, **kwdargs):
        super(FocusIndicator, self).__init__(color=color, linewidth=linewidth,
                                             linestyle=linestyle,
                                             alpha=alpha, **kwdargs)
        self.kind = 'focusindicator'
        self.has_focus = False
        self.enabled = True

    def draw(self, viewer):

        if (not self.has_focus) or (not self.enabled):
            return

        cr = viewer.renderer.setup_cr(self)
        tr = viewer.tform['window_to_native']

        wd, ht = viewer.get_window_size()
        lw = self.linewidth
        off = lw // 2

        # draw a rectangle around the perimeter
        cr.set_line(color=self.color, linewidth=lw, alpha=self.alpha,
                    style=self.linestyle)

        cpoints = ((off, off), (wd - off, off), (wd - off, ht - off),
                   (off, ht - off))
        cr.draw_polygon(tr.to_(cpoints))

    def focus_cb(self, viewer, onoff):
        has_focus = self.has_focus
        self.has_focus = onoff

        if has_focus != self.has_focus:
            viewer.redraw(whence=3)


# register our types
register_canvas_types(dict(colorbar=ColorBar, drawablecolorbar=DrawableColorBar,
                           modeindicator=ModeIndicator,
                           focusindicator=FocusIndicator))
