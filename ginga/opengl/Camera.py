#
# Camera.py -- Ginga 3D viewer OpenGL camera
#
# Credit:
#   Modified from code written by M. McGuffin
#   http://profs.etsmtl.ca/mmcguffin/code/python/example-3D_Python-Qt-OpenGL/
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np
from OpenGL import GL as gl

from .geometry_helper import Point3D, Vector3D, Matrix4x4

class Camera(object):

    def __init__(self):
        self.fov_deg = 30.0
        # Orbiting speed in degrees per radius of viewport
        self.orbit_speed = 300.0

        # These are in world-space units.
        self.near_plane = 1.0
        self.far_plane = 10000.0

        # During dollying (i.e. when the camera is translating into
        # the scene), if the camera gets too close to the target
        # point, we push the target point away.
        # The threshold distance at which such "pushing" of the
        # target point begins is this fraction of near_plane.
        # To prevent the target point from ever being clipped,
        # this fraction should be chosen to be greater than 1.0.
        self.push_threshold = 1.3

        # Viewport dimensions and radius (in pixels)
        # We give these some initial values just as a safeguard
        # against division by zero when computing their ratio.
        self.vport_wd_px = 10
        self.vport_ht_px = 10
        self.vport_radius_px = 5

        self.scene_radius = 10

        # point of view, or center of camera; the ego-center; the eye-point
        self.position = Point3D()

        # point of interest; what the camera is looking at; the exo-center
        self.target = Point3D()

        # This is the up vector for the (local) camera space
        self.up = Vector3D()

        # This is the up vector for the (global) world space;
        # it is perpendicular to the horizontal (x,z)-plane
        self.ground = Vector3D(0, 1, 0)

        # this is the default eye position to reset the camera
        self.home_position = Point3D(0, 0, 1)

        # this is the default target position to reset the camera
        self.tgt_position = Point3D(0, 0, 0)

        self.reset()

    def reset(self):
        #self.position = Point3D(0, 0, -distance_from_target)
        self.position = self.home_position.copy()
        self.target = self.tgt_position.copy()
        self.up = self.ground.copy()

    def set_viewport_dimensions(self, wd_px, ht_px):
        self.vport_wd_px = wd_px
        self.vport_ht_px = ht_px
        self.vport_radius_px = 0.5 * wd_px if (wd_px < ht_px) else 0.5 * ht_px

    def get_viewport_dimensions(self):
        return (self.vport_wd_px, self.vport_ht_px)

    def set_scene_radius(self, radius):
        self.scene_radius = radius

        # recalculate home position
        x, y, z = self.home_position.get()

        tangent = np.tan(self.fov_deg / 2.0 / 180.0 * np.pi)
        distance_from_target = self.scene_radius / tangent
        self.home_position = Point3D(x, y, distance_from_target)

    def set_camera_home_position(self, pt):
        self.home_position = Point3D(*pt)

    def set_target_home_position(self, pt):
        self.tgt_position = Point3D(*pt)

    def save_positions(self):
        self.home_position = self.position.copy()
        self.tgt_position = self.target.copy()

    def set_gl_transform(self):
        """This side effects the OpenGL context to set the view to match
        the camera.
        """
        tangent = np.tan(self.fov_deg / 2.0 / 180.0 * np.pi)
        vport_radius = self.near_plane * tangent
        # calculate aspect of the viewport
        if self.vport_wd_px < self.vport_ht_px:
            vport_wd = 2.0 * vport_radius
            vport_ht = vport_wd * self.vport_ht_px / float(self.vport_wd_px)

        else:
            vport_ht = 2.0 * vport_radius
            vport_wd = vport_ht * self.vport_wd_px / float(self.vport_ht_px)

        gl.glFrustum(
            -0.5 * vport_wd, 0.5 * vport_wd,    # left, right
            -0.5 * vport_ht, 0.5 * vport_ht,    # bottom, top
            self.near_plane, self.far_plane
            )

        M = Matrix4x4.look_at(self.position, self.target, self.up, False)
        gl.glMultMatrixf(M.get())

    def get_translation_speed(self, distance_from_target):
        """Returns the translation speed for ``distance_from_target``
        in units per radius.
        """
        return (distance_from_target *
                np.tan(self.fov_deg / 2.0 / 180.0 * np.pi))

    def orbit(self, x1_px, y1_px, x2_px, y2_px):
        """
        Causes the camera to "orbit" around the target point.
        This is also called "tumbling" in some software packages.
        """
        px_per_deg = self.vport_radius_px / float(self.orbit_speed)
        radians_per_px = 1.0 / px_per_deg * np.pi / 180.0

        t2p = self.position - self.target

        M = Matrix4x4.rotation_around_origin((x1_px - x2_px) * radians_per_px,
                                             self.ground)
        t2p = M * t2p
        self.up = M * self.up

        right = (self.up ^ t2p).normalized()
        M = Matrix4x4.rotation_around_origin((y1_px - y2_px) * radians_per_px,
                                             right)
        t2p = M * t2p
        self.up = M * self.up

        self.position = self.target + t2p

    def pan_delta(self, dx_px, dy_px):
        """
        This causes the scene to appear to translate right and up
        (i.e., what really happens is the camera is translated left and down).
        This is also called "panning" in some software packages.
        Passing in negative delta values causes the opposite motion.
        """
        direction = self.target - self.position
        distance_from_target = direction.length()
        direction = direction.normalized()

        speed_per_radius = self.get_translation_speed(distance_from_target)
        px_per_unit = self.vport_radius_px / speed_per_radius

        right = direction ^ self.up

        translation = (right * (-dx_px / px_per_unit) +
                       self.up * (-dy_px / px_per_unit))

        self.position = self.position + translation
        self.target = self.target + translation

    def track(self, delta_pixels, push_target=False, adj_fov=False):
        """
        This causes the camera to translate forward into the scene.
        This is also called "dollying" or "tracking" in some software packages.
        Passing in a negative delta causes the opposite motion.

        If ``push_target'' is True, the point of interest translates forward
        (or backward) *with* the camera, i.e. it's "pushed" along with the
        camera; otherwise it remains stationary.

        if ``adj_fov`` is True then the camera's FOV is adjusted to keep the
        target at the same size as before (so called "dolly zoom" or
        "trombone effect").
        """
        direction = self.target - self.position
        distance_from_target = direction.length()
        direction = direction.normalized()

        initial_ht = frustum_height_at_distance(self.fov_deg,
                                                distance_from_target)
        ## print("frustum height at distance %.4f is %.4f" % (
        ##     distance_from_target, initial_ht))

        speed_per_radius = self.get_translation_speed(distance_from_target)
        px_per_unit = self.vport_radius_px / speed_per_radius

        dolly_distance = delta_pixels / px_per_unit

        if not push_target:
            distance_from_target -= dolly_distance
            if distance_from_target < self.push_threshold * self.near_plane:
                distance_from_target = self.push_threshold * self.near_plane

        self.position += direction * dolly_distance
        self.target = self.position + direction * distance_from_target

        if adj_fov:
            # adjust FOV to match the size of the target before the dolly
            direction = self.target - self.position
            distance_from_target = direction.length()
            fov_deg = fov_for_height_and_distance(initial_ht,
                                                  distance_from_target)
            #print("fov is now %.4f" % fov_deg)
            self.fov_deg = fov_deg


    def frustum_dimensions_at_target(self, vfov_deg=None):
        if vfov_deg is None:
            vfov_deg = self.fov_deg

        direction = self.target - self.position
        distance_from_target = direction.length()

        height = frustum_height_at_distance(vfov_deg, distance_from_target)

        vp_wd, vp_ht = self.get_viewport_dimensions()
        aspect = float(vp_wd) / vp_ht

        hfov_rad = 2.0 * np.arctan(np.tan(np.radians(vfov_deg) * 0.5) * aspect)
        hfov_deg = np.degrees(hfov_rad)
        width = 2.0 * np.tan(hfov_rad * 0.5) * distance_from_target

        return (distance_from_target, hfov_deg, vfov_deg, width, height)


def frustum_height_at_distance(vfov_deg, distance):
    """Calculate the frustum height (in world units) at a given distance
    (in world units) from the camera.
    """
    height = 2.0 * distance * np.tan(np.radians(vfov_deg * 0.5))
    return height

def fov_for_height_and_distance(height, distance):
    """Calculate the FOV needed to get a given frustum height at a
    given distance.
    """
    vfov_deg = np.degrees(2.0 * np.arctan(height * 0.5 / distance))
    return vfov_deg


# END
