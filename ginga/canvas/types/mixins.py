#
# mixins.py -- classes for basic shapes drawn on ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy as np
from copy import deepcopy

from ginga.canvas.CanvasObject import Point, MovePoint, ScalePoint
from ginga import trcalc


#
#   ==== MIXIN CLASSES FOR BASE OBJECTS ====
#
class OnePointMixin(object):

    # --- For backward compatibility ---
    def __get_x(self):
        return self.points[0][0]

    def __set_x(self, val):
        self.points[0][0] = val

    x = property(__get_x, __set_x)

    def __get_y(self):
        return self.points[0][1]

    def __set_y(self, val):
        self.points[0][1] = val

    y = property(__get_y, __set_y)
    # ----------------------------------

    def get_center_pt(self):
        points = self.get_data_points()
        return points[0]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.points = deepcopy(self.get_data_points())

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.move_to_pt(pt)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        return [MovePoint(*self.get_center_pt())]

    def get_llur(self):
        x, y = self.crdmap.to_data((self.x, self.y))
        return (x - 0.5, y - 0.5, x + 0.5, y + 0.5)

    def rotate_by_deg(self, thetas):
        pass

    def scale_by_factors(self, factors):
        pass

    def scale_by(self, scale_x, scale_y):
        pass


class TwoPointMixin(object):

    # --- For backward compatibility ---
    def __get_x1(self):
        return self.points[0][0]

    def __set_x1(self, val):
        self.points[0][0] = val

    x1 = property(__get_x1, __set_x1)

    def __get_y1(self):
        return self.points[0][1]

    def __set_y1(self, val):
        self.points[0][1] = val

    y1 = property(__get_y1, __set_y1)

    def __get_x2(self):
        return self.points[1][0]

    def __set_x2(self, val):
        self.points[1][0] = val

    x2 = property(__get_x2, __set_x2)

    def __get_y2(self):
        return self.points[1][1]

    def __set_y2(self, val):
        self.points[1][1] = val

    y2 = property(__get_y2, __set_y2)
    # ----------------------------------

    def get_center_pt(self):
        points = self.get_data_points(points=[
            ((self.x1 + self.x2) / 2., (self.y1 + self.y2) / 2.),
        ])
        return points[0]

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.move_to_pt(pt)
        elif i in (1, 2):
            self.set_point_by_index(i - 1, pt)
        elif i == 3:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.rescale_by_factors((scalef, scalef), detail)
        elif i == 4:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rerotate_by_deg([delta_deg], detail)
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
        detail.points = deepcopy(self.get_data_points())

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
            self.move_to_pt(pt)
        elif i == 1:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.radius = detail.radius * scalef
        elif i == 2:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rotate_by_deg([delta_deg])
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        points = self.get_data_points(points=(
            self.crdmap.offset_pt((self.x, self.y), (self.radius, 0)),
        ))
        return [move_pt,
                ScalePoint(*points[0]),
                rotate_pt,
                ]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.radius = self.radius
        detail.points = deepcopy(self.get_data_points())

    def get_llur(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        (-self.radius, -self.radius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.radius, -self.radius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.radius, self.radius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (-self.radius, self.radius)))
        mpts = np.asarray(self.get_data_points(points=points))

        if hasattr(self, 'rot_deg'):
            xd, yd = self.crdmap.to_data((self.x, self.y))
            mpts = trcalc.rotate_coord(mpts, [self.rot_deg], [xd, yd])

        a, b = trcalc.get_bounds(mpts)
        return (a[0], a[1], b[0], b[1])

    def rotate_by_deg(self, thetas):
        pass

    def scale_by_factors(self, factors):
        self.radius *= np.asarray(factors).max()

    def scale_by(self, scale_x, scale_y):
        self.radius *= max(scale_x, scale_y)


class OnePointTwoRadiusMixin(OnePointMixin):

    def __init__(self):
        OnePointMixin.__init__(self)

    def set_edit_point(self, i, pt, detail):
        if i == 0:
            self.move_to_pt(pt)
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
            self.rotate_by_deg([delta_deg])
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)

        points = (self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, 0)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (0, self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, self.yradius)),
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
        detail.points = deepcopy(self.get_data_points())

    def rotate_by_deg(self, thetas):
        new_rot = math.fmod(self.rot_deg + thetas[0], 360.0)
        self.rot_deg = new_rot
        return new_rot

    def scale_by(self, scale_x, scale_y):
        self.xradius *= scale_x
        self.yradius *= scale_y

    def get_llur(self):
        points = (self.crdmap.offset_pt((self.x, self.y),
                                        (-self.xradius, -self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, -self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (self.xradius, self.yradius)),
                  self.crdmap.offset_pt((self.x, self.y),
                                        (-self.xradius, self.yradius)))
        mpts = np.asarray(self.get_data_points(points=points))

        if hasattr(self, 'rot_deg'):
            xd, yd = self.crdmap.to_data((self.x, self.y))
            mpts = trcalc.rotate_coord(mpts, [self.rot_deg], [xd, yd])

        a, b = trcalc.get_bounds(mpts)
        return (a[0], a[1], b[0], b[1])


class PolygonMixin(object):
    """Mixin for polygon-based objects.
    """
    def __init__(self):
        pass

    def insert_pt(self, idx, pt):
        points = np.asarray(self.points)
        self.points = np.insert(points, idx, pt, axis=0)

    def delete_pt(self, idx):
        points = np.asarray(self.points)
        self.points = np.delete(points, idx, axis=0)

    def get_center_pt(self):
        # default is geometric average of points
        P = np.asarray(self.get_data_points())
        x = P[:, 0]
        y = P[:, 1]
        ctr_x = np.sum(x) / float(len(x))
        ctr_y = np.sum(y) / float(len(y))
        return ctr_x, ctr_y

    def get_llur(self):
        a, b = trcalc.get_bounds(self.get_data_points())
        return (a[0], a[1], b[0], b[1])

    def contains_pts(self, pts):
        # NOTE: we use a version of the ray casting algorithm
        # See: http://alienryderflex.com/polygon/
        x_arr, y_arr = np.asarray(pts).T
        x_arr, y_arr = (x_arr.astype(float, copy=False),
                        y_arr.astype(float, copy=False))
        xa, ya = x_arr, y_arr

        result = np.empty(y_arr.shape, dtype=np.bool)
        result.fill(False)

        points = self.get_data_points()

        xj, yj = points[-1]
        for point in points:
            xi, yi = point
            tf = np.logical_and(
                np.logical_or(np.logical_and(yi < ya, yj >= ya),
                              np.logical_and(yj < ya, yi >= ya)),
                np.logical_or(xi <= xa, xj <= xa))
            # NOTE: get a divide by zero here for some elements whose tf=False
            # Need to figure out a way to conditionally do those w/tf=True
            # Till then we use the warnings module to suppress the warning.
            ## with warnings.catch_warnings():
            ##     warnings.simplefilter('default', RuntimeWarning)
            # NOTE postscript: warnings context manager causes this computation
            # to fail silently sometimes where it previously worked with a
            # warning--commenting out the warning manager for now
            cross = ((xi + (ya - yi).astype(float, copy=False) /
                      (yj - yi) * (xj - xi)) < xa)

            idx = np.nonzero(tf)
            result[idx] ^= cross[idx]
            xj, yj = xi, yi

        return result

    def set_edit_point(self, i, pt, detail):
        num_points = len(self.points)
        if i == 0:
            self.move_to_pt(pt)
        elif i - 1 < num_points:
            self.set_point_by_index(i - 1, pt)
        elif i == num_points + 1:
            scalef = self.calc_scale_from_pt(pt, detail)
            self.rescale_by(scalef, scalef, detail)
        elif i == num_points + 2:
            delta_deg = self.calc_rotation_from_pt(pt, detail)
            self.rerotate_by_deg([delta_deg], detail)
        else:
            raise ValueError("No point corresponding to index %d" % (i))

    def get_edit_points(self, viewer):
        move_pt, scale_pt, rotate_pt = self.get_move_scale_rotate_pts(viewer)
        points = self.get_data_points()
        return [move_pt] + list(points) + [scale_pt, rotate_pt]

    def setup_edit(self, detail):
        detail.center_pos = self.get_center_pt()
        detail.points = deepcopy(self.get_data_points())


# END
