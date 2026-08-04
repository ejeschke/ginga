#
# CanvasRenderAgg.py -- for rendering into a Ginga widget with matplotlib's
#                       Anti-Grain Geometry (AGG) rasterizer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""AGG canvas renderer for Ginga.

This backend draws the vector overlays (canvas objects) on top of the
color-mapped image using the low-level AGG rasterizer bundled with
matplotlib (``matplotlib.backends.backend_agg.RendererAgg``).  It replaces
the previous implementation built on the unmaintained ``aggdraw`` package;
the pixel output is equivalent (both are the same AGG library) while the
dependency (matplotlib) is one Ginga already requires.

Coordinate systems
------------------
Ginga's window coordinates put the origin at the top-left with y growing
*downward*.  matplotlib's AGG drawing coordinates put the origin at the
bottom-left with y growing *upward*, but ``buffer_rgba()`` returns rows
top-to-bottom.  We therefore draw every path/marker through a single
y-flip affine (``self.flip``) so that a Ginga point (x, y) lands on output
row y.  Text is positioned by passing the flipped y directly (glyphs are
always rasterized upright in screen space).
"""

import numpy as np

from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.transforms import Affine2D
from matplotlib.path import Path

from . import AggHelp
from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc


def _rgba(color4):
    """Convert a ginga 8-bpp (0..255) color 4-tuple to matplotlib's
    (r, g, b, a) floats in 0..1."""
    r, g, b, a = color4
    return (r / 255.0, g / 255.0, b / 255.0, a / 255.0)


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        # TODO: encapsulate this drawable
        self.ctx = AggHelp.AggContext(surface)

        # special scaling for Agg text drawing to normalize it relative
        # to the other backends (matches the pilw backend's convention)
        self._font_scale_factor = 1.75

        # y-flip: map Ginga top-left/y-down window coords into matplotlib's
        # bottom-left/y-up drawing frame.  Rebuilt from the live surface so
        # it always matches the current window height.
        if surface is not None:
            ht = surface.height
        else:
            ht = 0
        self.flip = Affine2D().scale(1.0, -1.0).translate(0.0, ht)

    def get_line(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        line = super().get_line(color, alpha=alpha, linewidth=linewidth,
                                linestyle=linestyle)
        line.render.rgba = _rgba(line.get_bpp_color(8))
        return line

    def get_fill(self, color, alpha=1.0):
        fill = super().get_fill(color, alpha=alpha)
        fill.render.rgba = _rgba(fill.get_bpp_color(8))
        return fill

    def get_font(self, fontname, **kwargs):
        font = super().get_font(fontname, **kwargs)
        font.render.prop = self.ctx._get_font(font)
        return font

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        if getattr(font.render, 'prop', None) is None:
            font.render.prop = self.ctx._get_font(font)
        return self.ctx.text_extents(text, font.render.prop)

    # --- graphics-context / path helpers -----------------------------------

    def _get_gc(self, line):
        """Build a matplotlib GraphicsContext from a ginga Line (or None)."""
        gc = self.ctx.canvas.new_gc()
        if line is None:
            # invisible stroke (used when only a fill is wanted)
            gc.set_linewidth(0)
            gc.set_foreground((0, 0, 0, 0), isRGBA=True)
            return gc
        gc.set_linewidth(line.linewidth)
        # carry alpha in the RGBA foreground/face colors rather than via
        # gc.set_alpha(): set_alpha() sets a *forced* alpha that overrides
        # the per-color alpha of both the stroke and the rgbFace fill.
        gc.set_foreground(line.render.rgba, isRGBA=True)
        if line.linestyle in ('dash', 'dashed'):
            # (offset, on/off sequence) in points; 1pt == 1px at dpi=72
            gc.set_dashes(0, [4, 4])
        return gc

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        if font is None:
            font = self.font
        if getattr(font.render, 'prop', None) is None:
            font.render.prop = self.ctx._get_font(font)
        prop = font.render.prop
        rgba = (fill.render.rgba if fill is not None else (0, 0, 0, 1))

        gc = self.ctx.canvas.new_gc()
        gc.set_foreground(rgba, isRGBA=True)

        # Unlike draw_path (which we feed y-up coords via self.flip),
        # RendererAgg.draw_text positions glyphs in top-left/y-down window
        # space directly (buffer row ~= the y passed in), so we do NOT apply
        # the flip here.  Ginga's (cx, cy) anchors the bottom-left of the
        # text box; matplotlib positions by the baseline, so drop by the
        # descent to put the box bottom on the anchor (matching the other
        # backends).
        _wd, _ht, descent = self.ctx.canvas.get_text_width_height_descent(
            text, prop, False)
        y = cy - descent
        self.ctx.canvas.draw_text(gc, cx, y, text, prop, rot_deg,
                                  ismath=False)

    def draw_polygon(self, cpoints, line=None, fill=None):
        cpoints = trcalc.strip_z(cpoints)
        verts = list(cpoints) + [cpoints[0]]
        codes = ([Path.MOVETO] +
                 [Path.LINETO] * (len(cpoints) - 1) +
                 [Path.CLOSEPOLY])
        path = Path(verts, codes)
        rgb_face = fill.render.rgba if fill is not None else None
        self.ctx.canvas.draw_path(self._get_gc(line), path, self.flip,
                                  rgbFace=rgb_face)

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        if line is None and fill is None:
            return
        # unit circle placed and scaled, then y-flipped into the AGG frame
        tform = (Affine2D().scale(cradius).translate(cx, cy) + self.flip)
        path = Path.unit_circle()
        rgb_face = fill.render.rgba if fill is not None else None
        self.ctx.canvas.draw_path(self._get_gc(line), path, tform,
                                  rgbFace=rgb_face)

    def draw_ellipse(self, cx, cy, cxradius, cyradius, rot_deg,
                     line=None, fill=None):
        if line is None and fill is None:
            return
        # a unit circle scaled to the two radii, rotated, moved to the
        # center, then y-flipped into the AGG frame.  Lets the Ellipse canvas
        # type take the direct-draw branch instead of building 13 bezier
        # control points every redraw.
        # NOTE: self.flip (scale 1,-1) reverses rotation handedness, so negate
        # the angle to match the y-down window convention used elsewhere.
        tform = (Affine2D().scale(cxradius, cyradius).rotate_deg(-rot_deg)
                 .translate(cx, cy) + self.flip)
        path = Path.unit_circle()
        rgb_face = fill.render.rgba if fill is not None else None
        self.ctx.canvas.draw_path(self._get_gc(line), path, tform,
                                  rgbFace=rgb_face)

    def draw_bezier_curve(self, cpoints, line=None):
        if line is None:
            return
        cp = trcalc.strip_z(cpoints)
        if len(cp) < 4:
            return
        # a single cubic from the first 4 control points.  This matches the
        # other backends' fallback (ginga.util.bezier.get_4pt_bezier only
        # consumes points[0:4]) so the BezierCurve type renders identically
        # across backends.
        path = Path([cp[0], cp[1], cp[2], cp[3]],
                    [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4])
        self.ctx.canvas.draw_path(self._get_gc(line), path, self.flip,
                                  rgbFace=None)

    def draw_ellipse_bezier(self, cpoints, line=None, fill=None):
        # 13 control points == 4 closed cubic segments (see
        # ginga.util.bezier.get_bezier_ellipse)
        cp = trcalc.strip_z(cpoints)
        n_seg = (len(cp) - 1) // 3
        if n_seg < 1:
            return
        verts = [cp[0]]
        codes = [Path.MOVETO]
        for i in range(n_seg):
            base = 1 + i * 3
            verts.extend([cp[base], cp[base + 1], cp[base + 2]])
            codes.extend([Path.CURVE4, Path.CURVE4, Path.CURVE4])
        verts.append(cp[0])
        codes.append(Path.CLOSEPOLY)
        path = Path(verts, codes)
        rgb_face = fill.render.rgba if fill is not None else None
        self.ctx.canvas.draw_path(self._get_gc(line), path, self.flip,
                                  rgbFace=rgb_face)

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        if line is None:
            return
        path = Path([(cx1, cy1), (cx2, cy2)],
                    [Path.MOVETO, Path.LINETO])
        self.ctx.canvas.draw_path(self._get_gc(line), path, self.flip,
                                  rgbFace=None)

    def draw_path(self, cpoints, line=None):
        if line is None:
            return
        cp = trcalc.strip_z(cpoints)
        codes = [Path.MOVETO] + [Path.LINETO] * (len(cp) - 1)
        path = Path(list(cp), codes)
        self.ctx.canvas.draw_path(self._get_gc(line), path, self.flip,
                                  rgbFace=None)


class CanvasRenderer(render.StandardPipelineRenderer):

    def __init__(self, viewer):
        render.StandardPipelineRenderer.__init__(self, viewer)

        self.kind = 'agg'
        self.rgb_order = 'RGBA'
        self.surface = None
        # color-mapped background image (RGBA, top-left origin), composited
        # under the vector overlays in get_surface_as_array()
        self.image_arr = None
        self.dims = ()

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        width, height = dims[:2]
        self.logger.debug("renderer reconfigured to %dx%d" % (
            width, height))
        # create AGG surface the size of the window
        self.surface = RendererAgg(width, height, AggHelp.dpi)
        self.image_arr = None

        super(CanvasRenderer, self).resize(dims)

    def render_image(self, data, order, win_coord):
        """Render the image represented by (data) at (win_coord)
        in the pixel space.
        *** internal method-- do not use ***
        """
        if self.surface is None:
            return
        self.logger.debug("redraw surface")

        # Stash the color-mapped background and clear the overlay surface for
        # this frame.  The vector overlays are drawn on the (now transparent)
        # AGG surface afterward and composited over this array on readout.
        self.surface.clear()
        self.image_arr = np.ascontiguousarray(data)

    def get_surface_as_array(self, order=None):
        if self.surface is None:
            raise render.RenderError("No AGG surface defined")

        wd, ht = self.dims[:2]

        # AGG overlay buffer (straight-alpha RGBA, top-left origin)
        overlay = np.asarray(self.surface.buffer_rgba()).reshape((ht, wd, 4))

        if self.image_arr is None:
            arr8 = overlay
        else:
            # alpha-composite the overlay over the background image
            base = self.image_arr
            oa = overlay[..., 3:4].astype(np.float32) / 255.0
            out = np.empty((ht, wd, 4), dtype=np.uint8)
            out[..., :3] = (overlay[..., :3].astype(np.float32) * oa +
                            base[..., :3].astype(np.float32) * (1.0 - oa)
                            ).astype(np.uint8)
            out[..., 3] = 255
            arr8 = out

        # adjust according to viewer's needed order
        return self.reorder(order, arr8, 'RGBA')

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
