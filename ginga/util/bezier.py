#
# bezier.py -- module for generating rasters of bezier curves
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math

# "reasonable" number of steps to make a smooth bezier curve
bezier_steps = 30

#
# See: http://caffeineoncode.com/2010/12/joining-multiple-bezier-curves/
#

#   calculates points for a simple bezier curve with 4 control points
#            
def get_4pt_bezier(steps, points):
    """Gets a series of bezier curve points with 1 set of 4
    control points."""
    for i in range(steps): 
        t = i / float(steps)

        xloc = (math.pow(1-t, 3) * points[0][0] +
                3 * t * math.pow(1-t, 2) * points[1][0] +
                3 * (1-t) * math.pow(t, 2) * points[2][0] +
                math.pow(t, 3) * points[3][0])
        yloc = (math.pow(1-t, 3) * points[0][1] +
                3 * t * math.pow(1-t, 2) * points[1][1] +
                3 * (1-t) * math.pow(t, 2) * points[2][1] +
                math.pow(t, 3) * points[3][1])

        yield (xloc, yloc)
    
def get_bezier(steps, points):
    """Gets a series of bezier curve points with any number of sets
    of 4 control points."""
    res = []
    num_pts = len(points)
    for i in range(0, num_pts+1, 3):
        if i + 4 < num_pts+1:
            res.extend(list(get_4pt_bezier(steps, points[i:i+4])))
    return res

def get_bezier_ellipse(x, y, xradius, yradius, kappa=0.5522848):
    """Get a set of 12 bezier control points necessary to form an
    ellipse."""

    xs, ys = x - xradius, y - yradius
    ox, oy = xradius * kappa, yradius * kappa
    xe, ye = x + xradius, y + yradius

    pts = [(xs, y),
           (xs, y - oy), (x - ox, ys), (x, ys),
           (x + ox, ys), (xe, y - oy), (xe, y),
           (xe, y + oy), (x + ox, ye), (x, ye),
           (x - ox, ye), (xs, y + oy), (xs, y)]
    return pts

#   draws a smooth bezier curve by adding points that
#   force smoothness
#
def get_smooth_bezier(steps, points):

    newpoints = []
    for i in range(len(points)):

        # add the next point
        newpoints.append(points[i])

        if i % 2 == 0 and i > 0 and i+1 < len(points):

            # calculate the midpoint
            xloc = (points[i][0] + points[i+1][0]) / 2.0
            yloc = (points[i][1] + points[i+1][1]) / 2.0

            # add the new point
            newpoints.append((xloc, yloc))

    return get_bezier(steps, newpoints)

#END
