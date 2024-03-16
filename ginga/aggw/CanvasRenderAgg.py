#
# CanvasRenderAgg.py -- for rendering into Ginga widget with aggdraw
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
from itertools import chain
import numpy as np

import aggdraw as agg

from . import AggHelp
from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        # TODO: encapsulate this drawable
        self.ctx = AggHelp.AggContext(surface)

        # special scaling for Agg text drawing to normalize it relative
        # to other backends
        self._font_scale_factor = 1.75

    def get_line(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        line = super().get_line(color, alpha=alpha, linewidth=linewidth,
                                linestyle=linestyle)

        _color = line.get_bpp_color(8)
        line.render.color = _color
        line.render.pen = agg.Pen(_color[:3], width=line.linewidth,
                                  opacity=_color[3])
        return line

    def get_fill(self, color, alpha=1.0):
        fill = super().get_fill(color, alpha=alpha)

        _color = fill.get_bpp_color(8)
        fill.render.color = _color
        fill.render.brush = agg.Brush(_color[:3], opacity=_color[3])
        return fill

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        fill = self.get_fill('black')
        _font = self.ctx._get_font(font, fill)
        return self.ctx.text_extents(text, _font)

    def get_affine_transform(self, cx, cy, rot_deg):
        x, y = cx, cy        # old center
        nx, ny = cx, cy      # new center
        sx = sy = 1.0        # new scale
        cosine = math.cos(math.radians(rot_deg))
        sine = math.sin(math.radians(rot_deg))
        a = cosine / sx
        b = sine / sx
        c = x - nx * a - ny * b
        d = -sine / sy
        e = cosine / sy
        f = y - nx * d - ny * e
        return (a, b, c, d, e, f)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):

        _font = self.ctx._get_font(font, fill)
        wd, ht = self.ctx.text_extents(text, _font)

        affine = self.get_affine_transform(cx, cy, rot_deg)
        self.ctx.canvas.settransform(affine)
        try:
            self.ctx.canvas.text((cx, cy - ht), text, _font)
        finally:
            # reset default transform
            self.ctx.canvas.settransform()

    def draw_polygon(self, cpoints, line=None, fill=None):
        pen = None if line is None else line.render.pen
        brush = None if fill is None else fill.render.brush

        cpoints = trcalc.strip_z(cpoints)
        self.ctx.canvas.polygon(list(chain.from_iterable(cpoints)),
                                pen, brush)

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        pen = None if line is None else line.render.pen
        brush = None if fill is None else fill.render.brush

        if line is not None and fill is not None:
            self.ctx.canvas.ellipse(
                (cx - cradius, cy - cradius, cx + cradius, cy + cradius),
                pen, brush)

    # NOTE: recent versions of aggdraw are not rendering Bezier curves
    # correctly--we comment out these temporarily so that we fall back to
    # a version that generates our own Beziers
    #
    # def draw_bezier_curve(self, cp, line=None):
    #     pen = None if line is None else line.render.pen
    #     brush = None if fill is None else fill.render.brush
    #
    #     path = agg.Path()
    #     path.moveto(cp[0][0], cp[0][1])
    #     path.curveto(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
    #     self.ctx.canvas.path(path, pen, brush)

    # def draw_ellipse_bezier(self, cp, line=None, fill=None):
    #     # draw 4 bezier curves to make the ellipse because there seems
    #     # to be a bug in aggdraw ellipse drawing function
    #     pen = None if line is None else line.render.pen
    #     brush = None if fill is None else fill.render.brush

    #     path = agg.Path()
    #     path.moveto(cp[0][0], cp[0][1])
    #     path.curveto(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
    #     path.curveto(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
    #     path.curveto(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
    #     path.curveto(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
    #     self.ctx.canvas.path(path, pen, brush)

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        if line is not None:
            self.ctx.canvas.line((cx1, cy1, cx2, cy2), line.render.pen)

    def draw_path(self, cpoints, line=None):
        if line is not None:
            cp = trcalc.strip_z(cpoints)
            # TODO: is there a more efficient way in aggdraw to do this?
            path = agg.Path()
            path.moveto(cp[0][0], cp[0][1])
            for pt in cp[1:]:
                path.lineto(pt[0], pt[1])
            #brush = agg.Brush(line._color[:3], opacity=line._color[3])
            brush = agg.Brush(line._color[:3], opacity=0)
            self.ctx.canvas.path(path, line.render.pen, brush)


class CanvasRenderer(render.StandardPipelineRenderer):

    def __init__(self, viewer):
        render.StandardPipelineRenderer.__init__(self, viewer)

        self.kind = 'agg'
        self.rgb_order = 'RGBA'
        self.surface = None
        self.dims = ()

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        width, height = dims[:2]
        self.logger.debug("renderer reconfigured to %dx%d" % (
            width, height))
        # create agg surface the size of the window
        self.surface = agg.Draw(self.rgb_order, (width, height), 'black')

        super(CanvasRenderer, self).resize(dims)

    def render_image(self, data, order, win_coord):
        """Render the image represented by (data) at (win_coord)
        in the pixel space.
        *** internal method-- do not use ***
        """
        if self.surface is None:
            return
        self.logger.debug("redraw surface")

        # get window contents as a buffer and load it into the AGG surface
        rgb_buf = data.tobytes(order='C')
        self.surface.frombytes(rgb_buf)

        # for debugging
        # import os.path, tempfile
        # self.save_rgb_image_as_file(os.path.join(tempfile.gettempdir(),
        #                                          'agg_out.png', format='png'))

    def get_surface_as_array(self, order=None):
        if self.surface is None:
            raise render.RenderError("No AGG surface defined")

        # TODO: could these have changed between the time that self.surface
        # was last updated?
        wd, ht = self.dims

        # Get agg surface as a numpy array
        arr8 = np.frombuffer(self.surface.tobytes(), dtype=np.uint8)
        arr8 = arr8.reshape((ht, wd, len(self.rgb_order)))

        # adjust according to viewer's needed order
        return self.reorder(order, arr8)

    def setup_cr(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        font = cr.get_font_from_shape(shape)
        return cr.text_extents(shape.text, font=font)

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.surface)
        return cr.text_extents(text, font=font)

#END
