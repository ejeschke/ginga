#
# geometry_helper.py -- help module for Ginga OpenGL camera
#
# Credit:
#   Modified from code written by M. McGuffin
#   http://profs.etsmtl.ca/mmcguffin/code/python/example-3D_Python-Qt-OpenGL/
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

class Point3D(object):

    def __init__(self, x=0, y=0, z=0):
        self.coord = np.array([x, y, z], dtype=np.float32)

    @property
    def x(self):
        return self.coord[0]

    @property
    def y(self):
        return self.coord[1]

    @property
    def z(self):
        return self.coord[2]

    def __repr__(self):
        return "Point3D(%f, %f, %f)" % tuple(self.coord)

    def __str__(self):
        return "P(%f, %f, %f)" % tuple(self.coord)

    def get(self):
        return self.coord

    def copy(self):
        return Point3D(self.x, self.y, self.z)

    def as_Vector3D(self):
        return Vector3D(self.x, self.y, self.z)

    def distance(self, other):
        return (other - self).length()

    def average(self, other):
        return Point3D((self.x + other.x) * 0.5,
                       (self.y + other.y) * 0.5,
                       (self.z + other.z) * 0.5)

    def __add__(self, other):
        return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        if isinstance(other, Vector3D):
            return Point3D(self.x - other.x, self.y - other.y, self.z - other.z)

        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __ne__(self, other):
        return not (self == other)


class Vector3D(object):

    def __init__(self, x=0, y=0, z=0):
        self.coord = np.array([x, y, z], dtype=np.float32)

    @property
    def x(self):
        return self.coord[0]

    @property
    def y(self):
        return self.coord[1]

    @property
    def z(self):
        return self.coord[2]

    def __repr__(self):
        return "Vector3D(%f, %f, %f)" % tuple(self.coord)

    def __str__(self):
        return "V(%f, %f, %f)" % tuple(self.coord)

    def get(self):
        return self.coord

    def copy(self):
        return Vector3D(self.x, self.y, self.z)

    def as_Point3D(self):
        return Point3D(self.x, self.y, self.z)

    def length_squared(self):
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self):
        return np.sqrt(self.length_squared())

    def normalized(self):
        l = self.length()
        if l > 0:
            return Vector3D(self.x / l, self.y / l, self.z / l)
        return self.copy()

    def __neg__(self):
        return Vector3D(-self.x, -self.y, -self.z)

    def __add__(self, other):
        if isinstance(other, Point3D):
            return Point3D(self.x + other.x, self.y + other.y, self.z + other.z)

        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, other):
        if isinstance(other, Vector3D):
           # dot product
           return self.x * other.x + self.y * other.y + self.z * other.z

        # scalar product
        return Vector3D(self.x * other, self.y * other, self.z * other)

    def __rmul__(self, other):
        return self * other

    def __div__(self, other):
        return Vector3D(self.x / other, self.y / other, self.z / other)

    def __xor__(self, other):   # cross product
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x )

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __ne__(self, other):
        return not (self == other)


class Matrix4x4(object):

    def __init__(self):
        self.set_to_identity()

    def __str__(self):
        return str(self.m)

    @property
    def f(self):
        return self.m.flat

    def get(self):
        return self.m

    def copy(self):
        M = Matrix4x4()
        M.m = self.m.copy()
        return M

    def set_to_identity(self):
        self.m = np.eye(4)

    @staticmethod
    def translation(vector3D):
        M = Matrix4x4()
        M.f[12] = vector3D.x
        M.f[13] = vector3D.y
        M.f[14] = vector3D.z
        return M

    @staticmethod
    def rotation_around_origin(angle_rad, axis_vector):
        # Note: assumes axis_vector is normalized
        c = np.cos(angle_rad)
        s = np.sin(angle_rad)
        one_minus_c = 1 - c
        M = Matrix4x4()
        M.f[ 0] = c + one_minus_c * axis_vector.x * axis_vector.x
        M.f[ 5] = c + one_minus_c * axis_vector.y * axis_vector.y
        M.f[10] = c + one_minus_c * axis_vector.z * axis_vector.z
        M.f[ 1] = M.f[ 4] = one_minus_c * axis_vector.x * axis_vector.y
        M.f[ 2] = M.f[ 8] = one_minus_c * axis_vector.x * axis_vector.z
        M.f[ 6] = M.f[ 9] = one_minus_c * axis_vector.y * axis_vector.z
        xs = axis_vector.x * s
        ys = axis_vector.y * s
        zs = axis_vector.z * s
        M.f[ 1] += zs;  M.f[ 4] -= zs
        M.f[ 2] -= ys;  M.f[ 8] += ys
        M.f[ 6] += xs;  M.f[ 9] -= xs

        M.f[12] = 0.0
        M.f[13] = 0.0
        M.f[14] = 0.0
        M.f[ 3] = 0.0;   M.f[ 7] = 0.0;   M.f[11] = 0.0;   M.f[15] = 1.0
        return M

    @staticmethod
    def rotation(angle_rad, axis_vector, origin_point):
        v = origin_point.as_Vector3D()
        return Matrix4x4.translation(v) * Matrix4x4.rotation_around_origin(angle_rad, axis_vector) * Matrix4x4.translation(- v)

    @staticmethod
    def uniform_scale_around_origin(scale_factor):
        M = Matrix4x4()
        M.m *= scale_factor
        M.f[15] = 1.0
        return M

    @staticmethod
    def uniform_scale(scale_factor, origin_point):
        v = origin_point.as_Vector3D()
        return Matrix4x4.translation(v) * Matrix4x4.uniform_scale_around_origin(scale_factor) * Matrix4x4.translation(- v)

    @staticmethod
    def look_at(eye_point, target_point, up_vector, is_inverted):
        # step one: generate a rotation matrix

        z = (eye_point - target_point).normalized()
        y = up_vector
        x = y ^ z   # cross product
        y = z ^ x   # cross product

        # Cross product gives area of parallelogram, which is < 1 for
        # non-perpendicular unit-length vectors; so normalize x and y.
        x = x.normalized()
        y = y.normalized()

        M = Matrix4x4()

        if is_inverted:
            # the rotation matrix
            M.f[ 0] = x.x;   M.f[ 4] = y.x;   M.f[ 8] = z.x;   M.f[12] = 0.0
            M.f[ 1] = x.y;   M.f[ 5] = y.y;   M.f[ 9] = z.y;   M.f[13] = 0.0
            M.f[ 2] = x.z;   M.f[ 6] = y.z;   M.f[10] = z.z;   M.f[14] = 0.0
            M.f[ 3] = 0.0;   M.f[ 7] = 0.0;   M.f[11] = 0.0;   M.f[15] = 1.0

            # step two: premultiply by a translation matrix
            return Matrix4x4.translation(eye_point.as_Vector3D()) * M

        else:
            # the rotation matrix
            M.f[ 0] = x.x;   M.f[ 4] = x.y;   M.f[ 8] = x.z;   M.f[12] = 0.0
            M.f[ 1] = y.x;   M.f[ 5] = y.y;   M.f[ 9] = y.z;   M.f[13] = 0.0
            M.f[ 2] = z.x;   M.f[ 6] = z.y;   M.f[10] = z.z;   M.f[14] = 0.0
            M.f[ 3] = 0.0;   M.f[ 7] = 0.0;   M.f[11] = 0.0;   M.f[15] = 1.0

            # step two: postmultiply by a translation matrix
            return M * Matrix4x4.translation(- eye_point.as_Vector3D())

    def __mul__(self, b):
        a = self
        if isinstance(b, Matrix4x4):
            M = Matrix4x4()
            M.f[ 0] = a.f[ 0]*b.f[ 0] + a.f[ 4]*b.f[ 1] + a.f[ 8]*b.f[ 2] + a.f[12]*b.f[ 3];
            M.f[ 1] = a.f[ 1]*b.f[ 0] + a.f[ 5]*b.f[ 1] + a.f[ 9]*b.f[ 2] + a.f[13]*b.f[ 3];
            M.f[ 2] = a.f[ 2]*b.f[ 0] + a.f[ 6]*b.f[ 1] + a.f[10]*b.f[ 2] + a.f[14]*b.f[ 3];
            M.f[ 3] = a.f[ 3]*b.f[ 0] + a.f[ 7]*b.f[ 1] + a.f[11]*b.f[ 2] + a.f[15]*b.f[ 3];

            M.f[ 4] = a.f[ 0]*b.f[ 4] + a.f[ 4]*b.f[ 5] + a.f[ 8]*b.f[ 6] + a.f[12]*b.f[ 7];
            M.f[ 5] = a.f[ 1]*b.f[ 4] + a.f[ 5]*b.f[ 5] + a.f[ 9]*b.f[ 6] + a.f[13]*b.f[ 7];
            M.f[ 6] = a.f[ 2]*b.f[ 4] + a.f[ 6]*b.f[ 5] + a.f[10]*b.f[ 6] + a.f[14]*b.f[ 7];
            M.f[ 7] = a.f[ 3]*b.f[ 4] + a.f[ 7]*b.f[ 5] + a.f[11]*b.f[ 6] + a.f[15]*b.f[ 7];

            M.f[ 8] = a.f[ 0]*b.f[ 8] + a.f[ 4]*b.f[ 9] + a.f[ 8]*b.f[10] + a.f[12]*b.f[11];
            M.f[ 9] = a.f[ 1]*b.f[ 8] + a.f[ 5]*b.f[ 9] + a.f[ 9]*b.f[10] + a.f[13]*b.f[11];
            M.f[10] = a.f[ 2]*b.f[ 8] + a.f[ 6]*b.f[ 9] + a.f[10]*b.f[10] + a.f[14]*b.f[11];
            M.f[11] = a.f[ 3]*b.f[ 8] + a.f[ 7]*b.f[ 9] + a.f[11]*b.f[10] + a.f[15]*b.f[11];

            M.f[12] = a.f[ 0]*b.f[12] + a.f[ 4]*b.f[13] + a.f[ 8]*b.f[14] + a.f[12]*b.f[15];
            M.f[13] = a.f[ 1]*b.f[12] + a.f[ 5]*b.f[13] + a.f[ 9]*b.f[14] + a.f[13]*b.f[15];
            M.f[14] = a.f[ 2]*b.f[12] + a.f[ 6]*b.f[13] + a.f[10]*b.f[14] + a.f[14]*b.f[15];
            M.f[15] = a.f[ 3]*b.f[12] + a.f[ 7]*b.f[13] + a.f[11]*b.f[14] + a.f[15]*b.f[15];
            return M

        elif isinstance(b, Vector3D):
            # We treat the vector as if its (homogeneous) 4th component were zero.
            return Vector3D(
                a.f[ 0]*b.x + a.f[ 4]*b.y + a.f[ 8]*b.z, # + a.f[12]*b.w(),
                a.f[ 1]*b.x + a.f[ 5]*b.y + a.f[ 9]*b.z, # + a.f[13]*b.w(),
                a.f[ 2]*b.x + a.f[ 6]*b.y + a.f[10]*b.z  # + a.f[14]*b.w(),
                # a.f[ 3]*b.x + a.f[ 7]*b.y + a.f[11]*b.z + a.f[15]*b.w()
                )

        elif isinstance(b, Point3D):
            # We treat the point as if its (homogeneous) 4th component were one.
            return Point3D(
                a.f[ 0]*b.x + a.f[ 4]*b.y + a.f[ 8]*b.z + a.f[12],
                a.f[ 1]*b.x + a.f[ 5]*b.y + a.f[ 9]*b.z + a.f[13],
                a.f[ 2]*b.x + a.f[ 6]*b.y + a.f[10]*b.z + a.f[14]
                )

# END
