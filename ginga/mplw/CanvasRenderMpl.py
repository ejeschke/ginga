#
# CanvasRenderMpl.py -- for rendering into a ImageViewMpl widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import matplotlib.patches as patches
import matplotlib.lines as lines
from matplotlib.path import Path as MplPath
#import matplotlib.patheffects as path_effects

from . import MplHelp
from ginga.canvas.mixins import *  # noqa
from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)
        self.shape = None

        # TODO: encapsulate this drawable
        self.ctx = MplHelp.MplContext(surface)

        # special scaling for Mpl text drawing to normalize it relative
        # to other backends
        self._font_scale_factor = 1.5

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        return self.ctx.text_extents(text, font)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        return

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        fontdict = self.ctx.get_fontdict(font, fill)
        self.ctx.push(allow=['alpha', 'color'])
        self.ctx.set(rotation=rot_deg)

        text = self.ctx.axes.text(cx, cy, text, fontdict=fontdict,
                                  **self.ctx.kwdargs)
        # See: https://github.com/matplotlib/matplotlib/issues/7227/
        # text.set_path_effects([path_effects.Stroke(linewidth=self.pen.linewidth,
        #                                            foreground='black'),
        #                        path_effects.Normal()])
        self.ctx.pop()

    def draw_polygon(self, cpoints, line=None, fill=None):
        self.ctx.init(closed=True, transform=None)
        self.ctx.update_patch(line, fill)

        xy = trcalc.strip_z(cpoints)

        p = patches.Polygon(xy, **self.ctx.kwdargs)
        self.ctx.axes.add_patch(p)

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        self.ctx.init(radius=cradius, transform=None)
        self.ctx.update_patch(line, fill)

        xy = (cx, cy)

        p = patches.Circle(xy, **self.ctx.kwdargs)
        self.ctx.axes.add_patch(p)

    def draw_bezier_curve(self, verts, line=None):
        self.ctx.init(transform=None)
        self.ctx.update_patch(line, None)

        codes = [MplPath.MOVETO,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 ]
        path = MplPath(verts, codes)

        p = patches.PathPatch(path, **self.ctx.kwdargs)
        self.ctx.axes.add_patch(p)

    def draw_ellipse_bezier(self, verts, line=None, fill=None):
        self.ctx.init(transform=None)
        self.ctx.update_patch(line, fill)

        # draw 4 bezier curves to make the ellipse
        codes = [MplPath.MOVETO,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                 ]
        path = MplPath(verts, codes)

        p = patches.PathPatch(path, **self.ctx.kwdargs)
        self.ctx.axes.add_patch(p)

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        self.ctx.init(transform=None)
        self.ctx.update_line(line)

        l = lines.Line2D((cx1, cx2), (cy1, cy2), **self.ctx.kwdargs)
        self.ctx.axes.add_line(l)

    def draw_path(self, cpoints, line=None):
        self.ctx.init(closed=False, transform=None)
        self.ctx.update_patch(line, None)

        xy = trcalc.strip_z(cpoints)

        p = patches.Polygon(xy, **self.ctx.kwdargs)
        self.ctx.axes.add_patch(p)


class CanvasRenderer(render.StandardPipelineRenderer):

    def __init__(self, viewer):
        render.StandardPipelineRenderer.__init__(self, viewer)

        self.kind = 'mpl'
        self.rgb_order = viewer.rgb_order
        self.surface = None

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        super(CanvasRenderer, self).resize(dims)

    def render_image(self, data, order, win_coord):
        # for compatibility with the other renderers
        return self.viewer.render_image(data, order, win_coord)

    def get_surface_as_array(self, order=None):
        raise render.RenderError("This renderer can only be used with a matplotlib viewer")

    def setup_cr(self, shape):
        cr = RenderContext(self, self.viewer, self.viewer.ax_util)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        font = cr.get_font_from_shape(shape)
        return cr.text_extents(shape.text, font=font)

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.viewer.ax_util)
        return cr.text_extents(text, font=font)


#END
