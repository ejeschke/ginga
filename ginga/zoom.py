#
# zoom.py -- Zoom algorithms
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Algorithms for mapping zoom levels to scale factors.

NOTE:
  A zoom algorithm should assume that a "0" zoom level corresponds to
  a 1:1 scale (image is unscaled).  A value greater than 0 scales up the
  image and a value less than 0 scales down the image.

"""
import math


class ZoomError(Exception):
    pass


class ZoomBase(object):

    def __init__(self, viewer):
        super(ZoomBase, self).__init__()

        self.t_ = viewer.get_settings()

    def set_settings(self, settings):
        self.t_ = settings

    def calc_scale(self, level):
        """
        Return a tuple of scales that match the desired zoom level.

        Parameters
        ----------
        level : int or float
            Zoom level desired.

        Returns
        -------
        (x_scale, y_scale) : tuple of float
            scales for each axis to achieve this zoom level

        """
        raise ZoomError("subclass should override this method!")

    def calc_level(self, scale):
        """
        Return a zoom level corresponding to the maximum scale.

        Parameters
        ----------
        scale : tuple (x_scale, y_scale) of float
            Scale for which we want to calculate zoom level.

        Returns
        -------
        level : float
            zoom level corresponding to the maximum scale

        """
        raise ZoomError("subclass should override this method!")


class StepZoom(ZoomBase):
    """
    A zoom algorithm based on integral multiples of the pixels.
    e.g. ..., 1/4, 1/3, 1/2, 1/1, 2/1, 3/1, 4/1 ...
    """

    def calc_scale(self, level):
        if level >= 0.0:
            scale = level + 1
        else:
            scale = 1.0 / float(abs(level - 1))

        return scale, scale

    def calc_level(self, scale):
        scale_x, scale_y = scale[:2]

        maxscale = max(scale_x, scale_y)
        if maxscale >= 1.0:
            level = maxscale - 1
        else:
            level = 1 - (1.0 / maxscale)

        return level

    def __str__(self):
        return 'step'


class RateZoom(ZoomBase):
    """
    A zoom algorithm based on changing the scale by a constant rate.
    """

    def calc_scale(self, level):
        scale_x = self.t_['scale_x_base'] * (
            self.t_['zoom_rate'] ** level)
        scale_y = self.t_['scale_y_base'] * (
            self.t_['zoom_rate'] ** level)

        return scale_x, scale_y

    def calc_level(self, scale):
        scale_x, scale_y = scale[:2]

        zoom_x = math.log(scale_x / self.t_['scale_x_base'],
                          self.t_['zoom_rate'])
        zoom_y = math.log(scale_y / self.t_['scale_y_base'],
                          self.t_['zoom_rate'])

        # TODO: avg, max?
        level = min(zoom_x, zoom_y)
        return level

    def __str__(self):
        return 'rate'


algorithms = {
    'step': StepZoom,
    'rate': RateZoom,
}


def add_zoom_alg(name, zoom_class):
    global algorithms
    algorithms[name.lower()] = zoom_class


def get_zoom_alg_names():
    all_names = set(algorithms.keys())
    std_names = ['step', 'rate']
    rest = all_names - set(std_names)
    if len(rest) > 0:
        std_names = std_names + list(rest)
    return std_names


def get_zoom_alg(name):
    if name not in algorithms:
        raise ZoomError("Invalid zoom algorithm '%s'" % (name))
    return algorithms[name]

# END
