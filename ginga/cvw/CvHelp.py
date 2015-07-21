#
# CvHelp.py -- help classes for the Cv drawing
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
import numpy
import cv2

from ginga import colors


class Pen(object):
    def __init__(self, color='black', linewidth=1, alpha=1.0):
        self.color = color
        self.linewidth = linewidth
        self.alpha = alpha

class Brush(object):
    def __init__(self, color='black', fill=False, alpha=1.0):
        self.color = color
        self.fill = fill
        self.alpha = alpha

class Font(object):
    def __init__(self, fontname='ariel', fontsize=12.0, color='black',
                 linewidth=1, alpha=1.0):
        self.fontname = fontname
        self.fontsize = fontsize
        self.color = color
        self.linewidth = linewidth
        # scale relative to a 12pt font
        self.scale = fontsize / 12.0
        self.alpha = alpha
        # TODO: currently there is only support for some simple built-in
        # fonts.  What kind of fonts/lookup can we use for this?
        self.font = cv2.FONT_HERSHEY_SIMPLEX


class CvContext(object):

    def __init__(self, canvas):
        self.canvas = canvas

    def set_canvas(self, canvas):
        self.canvas = canvas

    def get_color(self, color, alpha=1.0):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        # According to documentation, OpenCV expects colors as BGRA tuple
        # BUT, seems we need to specify RGBA--I suppose we need to match
        # what is defined as _rgb_order attribute in ImageViewCv class
        #return (int(alpha*255), int(b*255), int(g*255), int(r*255))
        return (int(r*255), int(g*255), int(b*255), int(alpha*255))

    def get_pen(self, color, linewidth=1, alpha=1.0):
        # if hasattr(self, 'linestyle'):
        #     if self.linestyle == 'dash':
        #         cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
        #op = int(alpha * 255)
        color = self.get_color(color, alpha=alpha)
        return Pen(color=color, linewidth=linewidth, alpha=alpha)

    def get_brush(self, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Brush(color=color, fill=True, alpha=alpha)

    def get_font(self, name, size, color, linewidth=1, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Font(fontname=name, fontsize=size, color=color,
                    linewidth=linewidth, alpha=alpha)

    def text_extents(self, text, font):
        ## retval, baseline = cv2.getTextSize(text, font.font, font.fontsize,
        ##                                    font.linewidth)
        retval, baseline = cv2.getTextSize(text, font.font, font.scale,
                                           font.linewidth)
        wd, ht = retval
        return wd, ht

    def text(self, pt, text, font):
        x, y = pt
        ## cv2.putText(self.canvas, text, (x, y), font.font, font.scale,
        ##             font.color, thickness=font.linewidth,
        ##             lineType=cv2.CV_AA)
        cv2.putText(self.canvas, text, (x, y), font.font, font.scale,
                    font.color, thickness=font.linewidth)

    def line(self, pt1, pt2, pen):
        x1, y1 = int(round(pt1[0])), int(round(pt1[1]))
        x2, y2 = int(round(pt2[0])), int(round(pt2[1]))
        cv2.line(self.canvas, (x1, y1), (x2, y2), pen.color, pen.linewidth)

    def circle(self, pt, radius, pen, brush):
        x, y = pt
        radius = int(radius)
        if (brush is not None) and brush.fill:
            cv2.circle(self.canvas, (x, y), radius, brush.color, -1)
        cv2.circle(self.canvas, (x, y), radius, pen.color, pen.linewidth)

    def rectangle(self, pt1, pt2, pen, brush):
        x1, y1 = pt1
        x2, y2 = pt2
        cv2.rectangle(self.canvas, (x1, y1), (x2, y2), pen.color, pen.linewidth)

    def ellipse(self, pt, xr, yr, theta, pen, brush):
        x, y = pt
        if (brush is not None) and brush.fill:
            cv2.ellipse(self.canvas, (x, y), (xr, yr), theta, 0.0, 360.0,
                        brush.color, -1)
        cv2.ellipse(self.canvas, (x, y), (xr, yr), theta, 0.0, 360.0,
                    pen.color, pen.linewidth)

    def polygon(self, points, pen, brush):
        pts = numpy.array(points, numpy.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(self.canvas, [pts], True, pen.color, pen.linewidth)
        if (brush is not None) and brush.fill:
            cv2.fillPoly(self.canvas, [pts], brush.color)

    def path(self, points, pen):
        pts = numpy.array(points, numpy.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(self.canvas, [pts], False, pen.color, pen.linewidth)


# Help functions for drawing Bezier curves
# Basis at:
#   https://gist.github.com/Alquimista/1274149
#

## def binomial(i, n):
##     """Binomial coefficient"""
##     return math.factorial(n) / float(
##         math.factorial(i) * math.factorial(n - i))

## def bernstein(t, i, n):
##     """Bernstein polynomial"""
##     return binomial(i, n) * (t ** i) * ((1 - t) ** (n - i))

## def bezier(t, points):
##     """Calculate coordinate of a point in the bezier curve"""
##     n = len(points) - 1
##     x = y = 0
##     for j, pos in enumerate(points):
##         bern = bernstein(t, j, n)
##         x += pos[0] * bern
##         y += pos[1] * bern
##     return x, y

## def bezier_curve_range(steps, points):
##     """Range of points in a curve bezier"""
##     for i in xrange(steps):
##         t = i / float(steps - 1)
##         yield bezier(t, points)

#END
