#
# mixins.py -- classes for basic shapes drawn on ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy

from ginga.canvas.CanvasObject import (CanvasObjectBase, Point,
                                       MovePoint, ScalePoint, RotatePoint)
from ginga import trcalc
from ginga.util.six.moves import map

#
#   ==== MIXIN CLASSES FOR BASE OBJECTS ====
#
class OnePointMixin(object):

    def __get_points(self):
        return numpy.asarray([(self.x, self.y)])

    def __set_points(self, pts):
        pts = numpy.asarray(pts)
        self.x, self.y = pts[0, 0], pts[0, 1]

    points = property(__get_points, __set_points)

    def get_center_pt(self):
        points = self.get_data_points(points=[(self.x, self.y)])
        return points[0]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.points = self.get_data_points()

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        return [MovePoint(*self.get_center_pt())]

    def get_llur(self):
        x, y = self.crdmap.to_data(self.x, self.y)
        return (x-0.5, y-0.5, x+0.5, y+0.5)

    def rotate_by(self, theta_deg):
        pass

    def scale_by(self, scale_x, scale_y):
        pass


class TwoPointMixin(object):

    def __get_points(self):
        return numpy.asarray([(self.x1, self.y1), (self.x2, self.y2)])

    def __set_points(self, pts):
        pts = numpy.asarray(pts)
        self.x1, self.y1 = pts[0, 0], pts[0, 1]
        self.x2, self.y2 = pts[1, 0], pts[1, 1]

    points = property(__get_points, __set_points)

    def get_point_by_index(self, i):
        return self.points[i]

    def get_center_pt(self):
        points = self.get_data_points(points=[
            ((self.x1 + self.x2) / 2., (self.y1 + self.y2) / 2.),
            ])
        return points[0]

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i in (1, 2):
            self.set_point_by_index(i-1, pt)
        elif i == 3:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.rescale_by(scalef, scalef, detail)
        elif i == 4:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rerotate_by(delta_deg, detail)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        points = self.get_data_points()
        return [move_pt,
                Point(*points[0]),
                Point(*points[1]),
                scale_pt,
                rotate_pt,
                ]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.points = self.get_data_points()

    def get_llur(self):
        points = self.get_data_points()
        x1, y1 = points[0]
        x2, y2 = points[1]
        return self.swapxy(x1, y1, x2, y2)


class OnePointOneRadiusMixin(OnePointMixin):

    def __init__(self):
        OnePointMixin.__init__(self)

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i == 1:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.radius = detail.radius * scalef
        elif i == 2:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rotate_by(delta_deg)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y), self.radius, 0),
            ))
        return [move_pt,
                ScalePoint(*points[0]),
                rotate_pt,
                ]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.radius = self.radius
        detail.points = numpy.array(self.get_data_points())

    def get_llur(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        -self.radius, -self.radius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.radius, -self.radius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.radius, self.radius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        -self.radius, self.radius))
        mpts = numpy.asarray(self.get_data_points(points=points))

        if hasattr(self, 'rot_deg'):
            xd, yd = self.crdmap.to_data(self.x, self.y)
            mpts = trcalc.rotate_coord(mpts, self.rot_deg, [xd, yd])

        t_ = mpts.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)

    def rotate_by(self, theta_deg):
        pass

    def scale_by(self, scale_x, scale_y):
        self.radius *= max(scale_x, scale_y)


class OnePointTwoRadiusMixin(OnePointMixin):

    def __init__(self):
        OnePointMixin.__init__(self)

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i == 1:
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.xradius = detail.xradius * scale_x
        elif i == 2:
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.yradius = detail.yradius * scale_y
        elif i == 3:
            scale_x, scale_y = self.calc_dual_scale_from_pt(pt, detail)
            self.xradius = detail.xradius * scale_x
            self.yradius = detail.yradius * scale_y
        elif i == 4:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.xradius = detail.xradius * scalef
            self.yradius = detail.yradius * scalef
        elif i == 5:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rotate_by(delta_deg)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)

        points = (self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, 0),
                  self.crdmap.offset_pt((self.x, self.y),
                                        0, self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, self.yradius),
                  )
        points = self.get_data_points(points=points)
        return [move_pt,    # location
                Point(*points[0]),  # adj xradius
                Point(*points[1]),  # adj yradius
                Point(*points[2]),  # adj both
                scale_pt,
                rotate_pt,
                ]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.xradius = self.xradius
        detail.yradius = self.yradius
        detail.points = self.get_data_points()

    def rotate_by(self, theta_deg):
        new_rot = math.fmod(self.rot_deg + theta_deg, 360.0)
        self.rot_deg = new_rot
        return new_rot

    def scale_by(self, scale_x, scale_y):
        self.xradius *= scale_x
        self.yradius *= scale_y

    def get_llur(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        -self.xradius, -self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, -self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        self.xradius, self.yradius),
                  self.crdmap.offset_pt((self.x, self.y),
                                        -self.xradius, self.yradius))
        mpts = numpy.asarray(self.get_data_points(points=points))

        if hasattr(self, 'rot_deg'):
            xd, yd = self.crdmap.to_data(self.x, self.y)
            mpts = trcalc.rotate_coord(mpts, self.rot_deg, [xd, yd])

        t_ = mpts.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)


class PolygonMixin(object):
    """Mixin for polygon-based objects.
    """
    def __init__(self):
        pass

    def insert_pt(self, idx, pt):
        self.points.insert(idx, pt)

    def delete_pt(self, idx):
        self.points.pop(idx)

    def get_center_pt(self):
        # default is geometric average of points
        P = numpy.asarray(self.get_data_points())
        x = P[:, 0]
        y = P[:, 1]
        ctr_x = numpy.sum(x) / float(len(x))
        ctr_y = numpy.sum(y) / float(len(y))
        return ctr_x, ctr_y

    def get_llur(self):
        points = numpy.asarray(self.get_data_points())
        t_ = points.T
        x1, y1 = t_[0].min(), t_[1].min()
        x2, y2 = t_[0].max(), t_[1].max()
        return (x1, y1, x2, y2)

    def contains_arr(self, x_arr, y_arr):
        # NOTE: we use a version of the ray casting algorithm
        # See: http://alienryderflex.com/polygon/
        xa, ya = x_arr, y_arr

        # promote input arrays dimension cardinality, if necessary
        promoted = False
        if len(xa.shape) == 1:
            xa = xa.reshape(1, -1)
            promoted = True
        if len(ya.shape) == 1:
            ya = ya.reshape(-1, 1)
            promoted = True

        result = numpy.empty((ya.size, xa.size), dtype=numpy.bool)
        result.fill(False)

        points = self.get_data_points()

        xj, yj = points[-1]
        for point in points:
            xi, yi = point
            tf = numpy.logical_and(
                numpy.logical_or(numpy.logical_and(yi < ya, yj >= ya),
                                 numpy.logical_and(yj < ya, yi >= ya)),
                numpy.logical_or(xi <= xa, xj <= xa))
            # NOTE: get a divide by zero here for some elements whose tf=False
            # Need to figure out a way to conditionally do those w/tf=True
            # Till then we use the warnings module to suppress the warning.
            ## with warnings.catch_warnings():
            ##     warnings.simplefilter('default', RuntimeWarning)
            # NOTE postscript: warnings context manager causes this computation
            # to fail silently sometimes where it previously worked with a
            # warning--commenting out the warning manager for now
            cross = ((xi + (ya - yi).astype(numpy.float) /
                          (yj - yi) * (xj - xi)) < xa)

            result[tf == True] ^= cross[tf == True]
            xj, yj = xi, yi

        if promoted:
            # de-promote result
            result = result[numpy.eye(len(y_arr), len(x_arr), dtype=numpy.bool)]

        return result

    def contains(self, xp, yp):
        x_arr, y_arr = numpy.array([xp]), numpy.array([yp])
        res = self.contains_arr(x_arr, y_arr)
        return res[0]

    def set_edit_point(self, i, pt, detail):
        num_points = len(self.points)
        if i == 0:
            x, y = pt
            self.move_to(x, y)
        elif i-1 < num_points:
            self.set_point_by_index(i-1, pt)
        elif i == num_points + 1:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.rescale_by(scalef, scalef, detail)
        elif i == num_points + 2:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rerotate_by(delta_deg, detail)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        points = self.get_data_points()
        return [move_pt] + list(points) + [scale_pt, rotate_pt]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.points = self.get_data_points()


#END
