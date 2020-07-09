#
# mock_sky.py -- functions for creating mock sky images
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from astropy.modeling.functional_models import Gaussian2D


def add_bg(arr, bg_mean, bg_sdev):
    """
    Add a background level to an image.

    Parameters
    ----------
    arr : ndarray
        2D array of number, usually zeros

    bg_mean : float
        Mean value of the supposed sky background

    bg_sdev : float
        The standard deviation of the sky background

    Side-effects ``arr`` to add the background.
    """
    bg = np.random.normal(loc=bg_mean, scale=bg_sdev,
                          size=arr.shape).astype(arr.dtype)
    arr += bg


def add_star(arr, pos, amp, sdev=2.0, ellip=0.8, blur=None):
    """
    Add a fake star to an image.

    Parameters
    ----------
    arr : ndarray
        sky image as a 2D numpy array

    pos : (x, y) tuple of floats
        Position of the star within the field

    amp : float
        The amplitude of the gaussian above the background median

    sdev : float, optional, defaults to 2.0
        The base standard deviation of the gaussian, defaults to 2

    ellip : float, optional
        A measure of the ellipticity of the star (0-1, 1 is perfect)

    blur : float or None, optional, defaults to None
        If not None, specifies a sigma to blur the gaussian

    Side-effects ``arr`` to add the fake stellar image with the given
    parameters.
    """
    ylen, xlen = arr.shape
    x_stddev = sdev + np.random.random() * (1.0 - ellip)
    y_stddev = sdev + np.random.random() * (1.0 - ellip)

    g = Gaussian2D(amplitude=amp, x_mean=pos[1], y_mean=pos[0],
                   x_stddev=x_stddev, y_stddev=y_stddev)

    xx, yy = np.mgrid[:ylen, :xlen]
    gauss = g(xx, yy).astype(arr.dtype)

    if blur is not None:
        from scipy.ndimage.filters import gaussian_filter
        gauss = gaussian_filter(gauss, sigma=blur)

    arr += gauss


def mk_star_image(arr, num_stars, amp_rng=None, sdev=None,
                  ellip=0.8, edge=0.6, blur=None,
                  bg_mean=2000.0, bg_sdev=15.0):
    """
    Make a fake stellar image.

    Parameters
    ----------
    arr : ndarray
        2D array to hold the stellar image, usually zeros

    num_stars : int
        Number of fake stars to add to the image

    amp_rng : (lo, hi) tuple of float
        The range of the brightness of stars to be added, default: (50, 1000)

    ellip : float, optional, defaults to 0.8
        A measure of the ellipticity of the star (0-1, 1 is perfect)

    edge : float, optional, defaults to 0.6
        The range of the allowed distance to the edge (0-1, 1 allows anywhere)

    blur : float or None, optional, defaults to None
        If not None, specifies a sigma to blur the gaussian

    bg_mean : float, optional, defaults to 2000.0
        The background mean of the sky image, before adding stars

    bg_sdev : float, optional, defaults to 15.0
        The standard deviation of the background

    Returns
    -------
    locs : list of tuple
        The list of star positions
    """

    if amp_rng is None:
        amp_rng = (50, 1000)

    # create array of size and initialize background
    add_bg(arr, bg_mean, bg_sdev)

    # calculate edge limits of stars within image
    ht, wd = arr.shape
    ctr_x, ctr_y = (wd // 2, ht // 2)
    x_l, x_h = ctr_x - int(ctr_x * edge), ctr_x + int(ctr_x * edge)
    y_l, y_h = ctr_y - int(ctr_y * edge), ctr_y + int(ctr_y * edge)

    # add stars within brightness levels
    locs = []
    for i in range(num_stars):
        x = (x_h - x_l) * np.random.random_sample() + x_l
        y = (y_h - y_l) * np.random.random_sample() + y_l
        amp = ((amp_rng[1] - amp_rng[0]) * np.random.random_sample() +
               amp_rng[0])
        pos = (x, y)
        locs.append(pos)
        add_star(arr, pos, amp, ellip=ellip, blur=blur)

    return locs
