#
# CanvasRenderGL.py -- for rendering into a OpenGL widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy
from OpenGL import GL as gl
from OpenGL import GLU as glu
from . import GlHelp

from ginga import colors
from ginga.util.six.moves import map, zip
# force registration of all canvas types
import ginga.canvas.types.all


class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer

        # TODO: encapsulate this drawable
        self.cr = GlHelp.GlContext(viewer.get_widget())

        self.pen = None
        self.brush = None
        self.font = None

    def set_line_from_shape(self, shape):
        alpha = getattr(shape, 'alpha', 1.0)
        linewidth = getattr(shape, 'linewidth', 1.0)
        linestyle = getattr(shape, 'linestyle', 'solid')
        self.pen = self.cr.get_pen(shape.color, linewidth=linewidth,
                                   linestyle=linestyle, alpha=alpha)

    def set_fill_from_shape(self, shape):
        fill = getattr(shape, 'fill', False)
        if fill:
            if hasattr(shape, 'fillcolor') and shape.fillcolor:
                color = shape.fillcolor
            else:
                color = shape.color
            alpha = getattr(shape, 'alpha', 1.0)
            alpha = getattr(shape, 'fillalpha', alpha)
            self.brush = self.cr.get_brush(color, alpha=alpha)
        else:
            self.brush = None

    def set_font_from_shape(self, shape):
        if hasattr(shape, 'font'):
            if hasattr(shape, 'fontsize') and shape.fontsize is not None:
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            alpha = getattr(shape, 'alpha', 1.0)
            self.font = self.cr.get_font(shape.font, fontsize, shape.color,
                                         alpha=alpha)
        else:
            self.font = None

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)
        if font:
            self.set_font_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):
        self.pen = self.cr.get_pen(color, linewidth=linewidth,
                                   linestyle=style, alpha=alpha)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(color, alpha=alpha)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        self.font = self.cr.get_font(fontname, fontsize, color,
                                     alpha=alpha)

    def text_extents(self, text):
        return self.cr.text_extents(text, self.font)


    ##### DRAWING OPERATIONS #####

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        # TODO
        pass

    def _scale(self, pt):
        x, y = pt
        widget = self.cr.widget
        sx, sy = x - widget.lim_x, widget.lim_y - y
        sz = 1 if not widget.mode3d else 10
        return (sx, sy, sz)

    def _draw_pts(self, shape, cpoints):
        if not self.cr.widget._drawing:
            return

        # set the OpenGL context if not already set
        self.cr.widget.makeCurrent()

        #print('drawing canvas')

        z_pts = numpy.array(list(map(self._scale, cpoints)))

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)

        # draw fill, if any
        if self.brush is not None:
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
            gl.glColor4f(*self.brush.color)

            gl.glVertexPointerf(z_pts)
            gl.glDrawArrays(shape, 0, len(z_pts))

        # draw outline
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
        gl.glColor4f(*self.pen.color)
        gl.glLineWidth(self.pen.linewidth)

        if self.pen.linestyle == 'dash':
            gl.glEnable(gl.GL_LINE_STIPPLE)
            gl.glLineStipple(3, 0x1C47)

        gl.glVertexPointerf(z_pts)
        gl.glDrawArrays(shape, 0, len(z_pts))

        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)

        if self.pen.linestyle == 'dash':
            gl.glDisable(gl.GL_LINE_STIPPLE)

    def draw_polygon(self, cpoints):
        self._draw_pts(gl.GL_POLYGON, cpoints)

    def draw_circle(self, cx, cy, cradius):
        # we have to approximate a circle in OpenGL
        # TODO: there is a more efficient algorithm described here:
        # http://slabode.exofire.net/circle_draw.shtml
        num_segments = 360
        z_pts = []
        for i in range(0, num_segments):
            theta = 2.0 * math.pi * i / float(num_segments)
            dx = cradius * math.cos(theta)
            dy = cradius * math.sin(theta)
            z_pts.append((cx + dx, cy + dy))

        self._draw_pts(gl.GL_LINE_LOOP, z_pts)

    def draw_line(self, cx1, cy1, cx2, cy2):
        z_pts = [(cx1, cy1), (cx2, cy2)]
        self._draw_pts(gl.GL_LINES, z_pts)

    def draw_path(self, cpoints):
        self._draw_pts(gl.GL_LINE_STRIP, cpoints)

class CanvasRenderer(object):

    def __init__(self, viewer):
        self.viewer = viewer

    def setup_cr(self, shape):
        cr = RenderContext(self.viewer)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

#END
