#
# CanvasRenderVec.py -- for rendering into a vector of drawing operations
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from .VecHelp import (IMAGE, LINE, CIRCLE, BEZIER, ELLIPSE_BEZIER, POLYGON,
                      PATH, TEXT)

from ginga.canvas import render


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        return self.renderer.text_extents(text, font)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, image_id, cpoints, rgb_arr, whence, order='RGB'):
        self.renderer.rl.append((IMAGE, (image_id, cpoints, rgb_arr, whence,
                                         order)))

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        self.renderer.rl.append((TEXT, (cx, cy, text, rot_deg),
                                 line, fill, font))

    def draw_polygon(self, cpoints, line=None, fill=None):
        self.renderer.rl.append((POLYGON, cpoints, line, fill))

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        self.renderer.rl.append((CIRCLE, (cx, cy, cradius),
                                 line, fill))

    ## def draw_bezier_curve(self, cpoints, line=None):
    ##     self.renderer.rl.append((BEZIER, cpoints, line))

    ## def draw_ellipse_bezier(self, cpoints, line=None, fill=None):
    ##     # draw 4 bezier curves to make the ellipse
    ##     self.renderer.rl.append((ELLIPSE_BEZIER, cpoints, line, fill))

    ## def draw_ellipse(self, cx, cy, cxradius, cyradius, rot_deg,
    ##                  line=None, fill=None):
    ##     self.renderer.rl.append((ELLIPSE,
    ##                              (cx, cy, cxradius, cyradius, rot_deg),
    ##                              line, fill))

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        self.renderer.rl.append((LINE, (cx1, cy1, cx2, cy2), line))

    def draw_path(self, cpoints, line=None):
        self.renderer.rl.append((PATH, cpoints, line))


class VectorRenderMixin:

    def __init__(self):
        # the render list
        self.rl = []

    def initialize(self):
        wd, ht = self.dims
        cpoints = ((0, 0), (wd, 0), (wd, ht), (ht, 0))
        bg = self.viewer.get_bg()
        line = self.get_line(color=bg)
        fill = self.get_fill(color=bg, alpha=1.0)
        self.rl = [(POLYGON, cpoints, line, fill)]

    def draw_vector(self, cr):
        for tup in self.rl:
            dtyp, line, fill, font = None, None, None, None
            try:
                dtyp = tup[0]
                if dtyp == IMAGE:
                    (image_id, cpoints, rgb_arr, whence, order) = tup[1]
                    cr.draw_image(image_id, cpoints, rgb_arr, whence,
                                  order=self.rgb_order)

                elif dtyp == LINE:
                    (cx1, cy1, cx2, cy2) = tup[1]
                    line = tup[2]
                    cr.draw_line(cx1, cy1, cx2, cy2, line=line)

                elif dtyp == CIRCLE:
                    cx, cy, cradius = tup[1]
                    line, fill = tup[2:4]
                    cr.draw_circle(cx, cy, cradius, line=line, fill=fill)

                elif dtyp == BEZIER:
                    cpoints = tup[1]
                    line = tup[2]
                    cr.draw_bezier_curve(cpoints, line=line)

                elif dtyp == ELLIPSE_BEZIER:
                    cpoints = tup[1]
                    line, fill = tup[2:4]
                    cr.draw_ellipse_bezier(cpoints, line=line, fill=fill)

                elif dtyp == POLYGON:
                    cpoints = tup[1]
                    line, fill = tup[2:4]
                    cr.draw_polygon(cpoints, line=line, fill=fill)

                elif dtyp == PATH:
                    cpoints = tup[1]
                    line = tup[2]
                    cr.draw_path(cpoints, line=line)

                elif dtyp == TEXT:
                    (cx, cy, text, rot_deg) = tup[1]
                    line, fill, font = tup[2:5]
                    cr.draw_text(cx, cy, text, rot_deg=rot_deg,
                                 font=font, fill=fill, line=line)

            except Exception as e:
                self.logger.error("Error drawing '{}': {}".format(dtyp, e),
                                  exc_info=True)

#END
