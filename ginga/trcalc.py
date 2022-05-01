#
# trcalc.py -- transformation calculations for image data
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import math
import numpy as np

from ginga.util.toolbox import PIL_LT_9_1

_use = None


def use(pkgname):
    global _use

    if pkgname == 'opencv':
        _use = 'opencv'

    elif pkgname == 'pillow':
        _use = 'pillow'


# Python Imaging Library
from PIL import Image
if PIL_LT_9_1:
    pil_resize = dict(nearest=Image.NEAREST,
                      linear=Image.BILINEAR,
                      area=Image.HAMMING,
                      bicubic=Image.BICUBIC,
                      lanczos=Image.LANCZOS)
else:
    pil_resize = dict(nearest=Image.Resampling.NEAREST,
                      linear=Image.Resampling.BILINEAR,
                      area=Image.Resampling.HAMMING,
                      bicubic=Image.Resampling.BICUBIC,
                      lanczos=Image.Resampling.LANCZOS)

interpolation_methods = sorted(set(['basic'] + list(pil_resize.keys())))

have_opencv = False
try:
    # optional opencv package speeds up certain operations, especially
    # rotation
    import cv2
    cv2_resize = dict(nearest=cv2.INTER_NEAREST,
                      linear=cv2.INTER_LINEAR,
                      area=cv2.INTER_AREA,
                      bicubic=cv2.INTER_CUBIC,
                      lanczos=cv2.INTER_LANCZOS4)
    have_opencv = True

    interpolation_methods = sorted(set(['basic'] + list(cv2_resize.keys())))

except ImportError:
    pass

# For testing
#have_opencv = False

_dtype_uint8 = np.dtype(np.uint8)
_dtype_uint16 = np.dtype(np.uint16)


def get_center(data_np):
    ht, wd = data_np.shape[:2]

    ctr_x = int(wd // 2)
    ctr_y = int(ht // 2)
    ## ctr_x = wd * 0.5
    ## ctr_y = ht * 0.5
    return (ctr_x, ctr_y)


def rotate_pt(x_arr, y_arr, theta_deg, xoff=0, yoff=0):
    """
    Rotate an array of points (x_arr, y_arr) by theta_deg offsetted
    from a center point by (xoff, yoff).
    """
    # TODO: use opencv acceleration if available
    a_arr = x_arr - xoff
    b_arr = y_arr - yoff
    cos_t = np.cos(np.radians(theta_deg))
    sin_t = np.sin(np.radians(theta_deg))
    ap = (a_arr * cos_t) - (b_arr * sin_t)
    bp = (a_arr * sin_t) + (b_arr * cos_t)
    return np.asarray((ap + xoff, bp + yoff))


rotate_arr = rotate_pt


def rotate_coord(coord, thetas, offsets):
    arr_t = np.asarray(coord).T
    # TODO: handle dimensional rotation N>2
    arr = rotate_pt(arr_t[0], arr_t[1], thetas[0],
                    xoff=offsets[0], yoff=offsets[1])

    if len(arr_t) > 2:
        # just copy unrotated Z coords
        arr = np.asarray([arr[0], arr[1]] + list(arr_t[2:]))

    return arr.T


def rotate_clip(data_np, theta_deg, rotctr_x=None, rotctr_y=None,
                out=None, logger=None):
    """
    Rotate numpy array `data_np` by `theta_deg` around rotation center
    (rotctr_x, rotctr_y).  If the rotation center is omitted it defaults
    to the center of the array.

    No adjustment is done to the data array beforehand, so the result will
    be clipped according to the size of the array (the output array will be
    the same size as the input array).
    """

    # If there is no rotation, then we are done
    if math.fmod(theta_deg, 360.0) == 0.0:
        return data_np

    ht, wd = data_np.shape[:2]
    dtype = data_np.dtype

    if rotctr_x is None:
        rotctr_x = wd // 2
    if rotctr_y is None:
        rotctr_y = ht // 2

    if dtype == _dtype_uint8 and have_opencv and _use in (None, 'opencv'):
        if logger is not None:
            logger.debug("rotating with OpenCv")
        # opencv is fastest
        M = cv2.getRotationMatrix2D((rotctr_x, rotctr_y), theta_deg, 1)

        newdata = cv2.warpAffine(data_np, M, (wd, ht))
        new_ht, new_wd = newdata.shape[:2]
        assert (wd == new_wd) and (ht == new_ht), \
            Exception("rotated cutout is %dx%d original=%dx%d" % (
                new_wd, new_ht, wd, ht))

        newdata = newdata.astype(dtype, copy=False)

        if out is not None:
            out[:, :, ...] = newdata
            newdata = out

    elif dtype == _dtype_uint8 and _use in (None, 'pillow'):
        if logger is not None:
            logger.debug("rotating with pillow")
        img = Image.fromarray(data_np)
        img_rot = img.rotate(theta_deg, resample=False, expand=False,
                             center=(rotctr_x, rotctr_y))
        newdata = np.array(img_rot, dtype=data_np.dtype)
        new_ht, new_wd = newdata.shape[:2]
        assert (wd == new_wd) and (ht == new_ht), \
            Exception("rotated cutout is %dx%d original=%dx%d" % (
                new_wd, new_ht, wd, ht))

    else:
        if logger is not None:
            logger.debug("rotating with numpy")
        yi, xi = np.mgrid[0:ht, 0:wd]
        xi -= rotctr_x
        yi -= rotctr_y
        cos_t = np.cos(np.radians(theta_deg))
        sin_t = np.sin(np.radians(theta_deg))

        ap = (xi * cos_t) - (yi * sin_t) + rotctr_x
        bp = (xi * sin_t) + (yi * cos_t) + rotctr_y

        #ap = np.rint(ap).clip(0, wd-1).astype(int)
        #bp = np.rint(bp).clip(0, ht-1).astype(int)
        # Optomizations to reuse existing intermediate arrays
        np.rint(ap, out=ap)
        ap = ap.astype(int, copy=False)
        ap.clip(0, wd - 1, out=ap)
        np.rint(bp, out=bp)
        bp = bp.astype(int, copy=False)
        bp.clip(0, ht - 1, out=bp)

        if out is not None:
            out[:, :, ...] = data_np[bp, ap]
            newdata = out
        else:
            newdata = data_np[bp, ap]
            new_ht, new_wd = newdata.shape[:2]

            assert (wd == new_wd) and (ht == new_ht), \
                Exception("rotated cutout is %dx%d original=%dx%d" % (
                    new_wd, new_ht, wd, ht))

    return newdata


def rotate(data_np, theta_deg, rotctr_x=None, rotctr_y=None, pad=20,
           logger=None):

    # If there is no rotation, then we are done
    if math.fmod(theta_deg, 360.0) == 0.0:
        return data_np

    ht, wd = data_np.shape[:2]

    ocx, ocy = wd // 2, ht // 2

    # Make a square with room to rotate
    side = int(math.sqrt(wd**2 + ht**2) + pad)
    new_wd = new_ht = side
    dims = (new_ht, new_wd) + data_np.shape[2:]
    # Find center of new data array
    ncx, ncy = new_wd // 2, new_ht // 2

    # Overlay the old image on the new (blank) image
    ldx, rdx = min(ocx, ncx), min(wd - ocx, ncx)
    bdy, tdy = min(ocy, ncy), min(ht - ocy, ncy)

    # TODO: fill with a different value?
    newdata = np.zeros(dims, dtype=data_np.dtype)
    newdata[ncy - bdy:ncy + tdy, ncx - ldx:ncx + rdx] = \
        data_np[ocy - bdy:ocy + tdy, ocx - ldx:ocx + rdx]

    # Now rotate with clip as usual
    newdata = rotate_clip(newdata, theta_deg,
                          rotctr_x=rotctr_x, rotctr_y=rotctr_y,
                          out=newdata)
    return newdata


def get_scaled_cutout_wdht_view(shp, x1, y1, x2, y2, new_wd, new_ht):
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

    # calculate dimensions of NON-scaled cutout
    old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)

    if new_wd == 0:
        iscale_x = 0.0
    else:
        iscale_x = float(old_wd) / float(new_wd)

    if new_ht == 0:
        iscale_y = 0.0
    else:
        iscale_y = float(old_ht) / float(new_ht)

    max_x, max_y = shp[1] - 1, shp[0] - 1

    # Make indexes and scale them
    # Is there a more efficient way to do this?
    xi = np.clip(x1 + np.arange(0, new_wd) * iscale_x,
                 0, max_x).astype(int, copy=False)
    yi = np.clip(y1 + np.arange(0, new_ht) * iscale_y,
                 0, max_y).astype(int, copy=False)
    wd, ht = xi.size, yi.size

    # bounds check against shape (to protect future data access)
    if new_wd > 0:
        xi_max = xi[-1]
        if xi_max > max_x:
            raise ValueError("X index (%d) exceeds shape bounds (%d)" % (xi_max, max_x))
    if new_ht > 0:
        yi_max = yi[-1]
        if yi_max > max_y:
            raise ValueError("Y index (%d) exceeds shape bounds (%d)" % (yi_max, max_y))

    view = np.ix_(yi, xi)

    # Calculate actual scale used (vs. desired)
    scale_x = float(wd) / old_wd
    scale_y = float(ht) / old_ht

    # return view + actual scale factors used
    return (view, (scale_x, scale_y))


def get_scaled_cutout_wdhtdp_view(shp, p1, p2, new_dims):
    """
    Like get_scaled_cutout_wdht, but returns the view/slice to extract
    from an image instead of the extraction itself.
    """
    x1, y1, z1 = p1
    x2, y2, z2 = p2
    new_wd, new_ht, new_dp = new_dims

    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    z1, z2, new_wd, new_ht = int(z1), int(z2), int(new_wd), int(new_ht)

    # calculate dimensions of NON-scaled cutout
    old_wd = max(x2 - x1 + 1, 1)
    old_ht = max(y2 - y1 + 1, 1)
    old_dp = max(z2 - z1 + 1, 1)
    max_x, max_y, max_z = shp[1] - 1, shp[0] - 1, shp[2] - 1

    # Make indexes and scale them
    # Is there a more efficient way to do this?
    if new_wd == 0:
        iscale_x = 0.0
    else:
        iscale_x = float(old_wd) / float(new_wd)

    if new_ht == 0:
        iscale_y = 0.0
    else:
        iscale_y = float(old_ht) / float(new_ht)

    if new_dp == 0:
        iscale_z = 0.0
    else:
        iscale_z = float(old_dp) / float(new_dp)

    xi = np.clip(x1 + np.arange(0, new_wd) * iscale_x,
                 0, max_x).astype(int, copy=False)
    yi = np.clip(y1 + np.arange(0, new_ht) * iscale_y,
                 0, max_y).astype(int, copy=False)
    zi = np.clip(z1 + np.arange(0, new_dp) * iscale_z,
                 0, max_z).astype(int, copy=False)
    wd, ht, dp = xi.size, yi.size, zi.size

    # bounds check against shape (to protect future data access)
    if new_wd > 0:
        xi_max = xi[-1]
        if xi_max > max_x:
            raise ValueError("X index (%d) exceeds shape bounds (%d)" % (xi_max, max_x))

    if new_ht > 0:
        yi_max = yi[-1]
        if yi_max > max_y:
            raise ValueError("Y index (%d) exceeds shape bounds (%d)" % (yi_max, max_y))

    if new_dp > 0:
        zi_max = zi[-1]
        if zi_max > max_z:
            raise ValueError("Z index (%d) exceeds shape bounds (%d)" % (zi_max, max_z))

    view = np.ix_(yi, xi, zi)

    # Calculate actual scale used (vs. desired)
    scale_x = float(wd) / old_wd
    scale_y = float(ht) / old_ht
    scale_z = float(dp) / old_dp

    # return view + actual scale factors used
    return (view, (scale_x, scale_y, scale_z))


def get_scaled_cutout_wdht(data_np, x1, y1, x2, y2, new_wd, new_ht,
                           interpolation='basic', logger=None,
                           dtype=None):
    """Extract a region of the `data_np` defined by corners (x1, y1) and
    (x2, y2) and resample it to fit dimensions (new_wd, new_ht).

    `interpolation` describes the method of interpolation used, where the
    default "basic" is nearest neighbor.  If `logger` is not `None` it will
    be used for logging messages.  If `dtype` is defined then the output
    array will be converted to that type; the default is the same as the
    input type.
    """
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    new_wd, new_ht = int(new_wd), int(new_ht)

    rdim = data_np.shape[2:]
    open_cl_ok = (len(rdim) == 0 or (len(rdim) == 1 and rdim[0] == 4))
    if dtype is None:
        dtype = data_np.dtype

    if have_opencv and _use in (None, 'opencv'):
        if logger is not None:
            logger.debug("resizing with OpenCv")
        # opencv is fastest and supports many methods
        if interpolation == 'basic':
            interpolation = 'nearest'
        method = cv2_resize[interpolation]

        cutout = data_np[y1:y2 + 1, x1:x2 + 1]
        if cutout.dtype not in (_dtype_uint8, _dtype_uint16):
            # special hack for OpenCv resize on certain numpy array types
            cutout = cutout.astype(np.float64)

        newdata = cv2.resize(cutout, (new_wd, new_ht),
                             interpolation=method)

        old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
        ht, wd = newdata.shape[:2]
        scale_x, scale_y = float(wd) / old_wd, float(ht) / old_ht

    elif data_np.dtype == _dtype_uint8 and _use in (None, 'pillow'):
        if logger is not None:
            logger.info("resizing with pillow")
        if interpolation == 'basic':
            interpolation = 'nearest'
        method = pil_resize[interpolation]
        img = Image.fromarray(data_np[y1:y2 + 1, x1:x2 + 1])
        img_siz = img.resize((new_wd, new_ht), resample=method)
        newdata = np.array(img_siz, dtype=dtype)

        old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
        ht, wd = newdata.shape[:2]
        scale_x, scale_y = float(wd) / old_wd, float(ht) / old_ht

    elif interpolation not in ('basic', 'nearest'):
        raise ValueError("Interpolation method not supported: '%s'" % (
            interpolation))

    else:
        if logger is not None:
            logger.debug('resizing by slicing')
        view, (scale_x, scale_y) = get_scaled_cutout_wdht_view(data_np.shape,
                                                               x1, y1, x2, y2,
                                                               new_wd, new_ht)
        newdata = data_np[view]

    newdata = newdata.astype(dtype, copy=False)

    return newdata, (scale_x, scale_y)


def get_scaled_cutout_wdhtdp(data_np, p1, p2, new_dims, logger=None):
    if logger is not None:
        logger.debug('resizing by slicing')
    view, scales = get_scaled_cutout_wdhtdp_view(data_np.shape,
                                                 p1, p2, new_dims)
    newdata = data_np[view]

    return newdata, scales


def get_scaled_cutout_basic_view(shp, p1, p2, scales):
    """
    Like get_scaled_cutout_basic, but returns the view/slice to extract
    from an image, instead of the extraction itself
    """

    x1, y1, x2, y2 = int(p1[0]), int(p1[1]), int(p2[0]), int(p2[1])
    scale_x, scale_y = scales[:2]

    # calculate dimensions of NON-scaled cutout
    old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
    new_wd, new_ht = int(scale_x * old_wd), int(scale_y * old_ht)

    if len(scales) == 2:
        return get_scaled_cutout_wdht_view(shp, x1, y1, x2, y2, new_wd, new_ht)

    z1, z2, scale_z = p1[2], p2[2], scales[2]
    old_dp = max(z2 - z1 + 1, 1)
    new_dp = int(scale_z * old_dp)
    return get_scaled_cutout_wdhtdp_view(shp, p1, p2, (new_wd, new_ht, new_dp))


def get_scaled_cutout_basic(data_np, x1, y1, x2, y2, scale_x, scale_y,
                            interpolation='basic', logger=None,
                            dtype=None):

    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

    rdim = data_np.shape[2:]
    open_cl_ok = (len(rdim) == 0 or (len(rdim) == 1 and rdim[0] == 4))
    if dtype is None:
        dtype = data_np.dtype

    if have_opencv and _use in (None, 'opencv'):
        if logger is not None:
            logger.debug("resizing with OpenCv")
        # opencv is fastest
        if interpolation == 'basic':
            interpolation = 'nearest'
        method = cv2_resize[interpolation]

        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        cutout = data_np[y1:y2 + 1, x1:x2 + 1]

        if cutout.dtype not in (_dtype_uint8, _dtype_uint16):
            # special hack for OpenCv resize on certain numpy array types
            cutout = cutout.astype(np.float64)
        newdata = cv2.resize(cutout, None,
                             fx=scale_x, fy=scale_y,
                             interpolation=method)

        old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
        ht, wd = newdata.shape[:2]
        scale_x, scale_y = float(wd) / old_wd, float(ht) / old_ht

    elif data_np.dtype == _dtype_uint8 and _use in (None, 'pillow'):
        if logger is not None:
            logger.info("resizing with pillow")
        if interpolation == 'basic':
            interpolation = 'nearest'
        method = pil_resize[interpolation]
        img = Image.fromarray(data_np[y1:y2 + 1, x1:x2 + 1])
        old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
        new_wd, new_ht = int(scale_x * old_wd), int(scale_y * old_ht)
        img_siz = img.resize((new_wd, new_ht), resample=method)
        newdata = np.array(img_siz, dtype=dtype)

        ht, wd = newdata.shape[:2]
        scale_x, scale_y = float(wd) / old_wd, float(ht) / old_ht

    elif interpolation not in ('basic', 'nearest'):
        raise ValueError("Interpolation method not supported: '%s'" % (
            interpolation))

    else:
        if logger is not None:
            logger.debug('resizing by slicing')
        view, scales = get_scaled_cutout_basic_view(data_np.shape,
                                                    (x1, y1), (x2, y2),
                                                    (scale_x, scale_y))
        scale_x, scale_y = scales
        newdata = data_np[view]

    newdata = newdata.astype(dtype, copy=False)

    return newdata, (scale_x, scale_y)


def get_scaled_cutout_basic2(data_np, p1, p2, scales,
                             interpolation='basic', logger=None):

    if interpolation not in ('basic', 'view'):
        if len(scales) != 2:
            raise ValueError("Interpolation method not supported: '%s'" % (
                interpolation))
        return get_scaled_cutout_basic(data_np, p1[0], p1[1],
                                       p2[0], p2[1],
                                       scales[0], scales[1],
                                       interpolation=interpolation,
                                       logger=logger)

    if logger is not None:
        logger.debug('resizing by slicing')
    view, oscales = get_scaled_cutout_basic_view(data_np.shape,
                                                 p1, p2, scales)
    newdata = data_np[view]

    return newdata, oscales


def transform(data_np, flip_x=False, flip_y=False, swap_xy=False):

    # Do transforms as necessary
    if flip_y:
        data_np = np.flipud(data_np)
    if flip_x:
        data_np = np.fliplr(data_np)
    if swap_xy:
        data_np = data_np.swapaxes(0, 1)

    return data_np


def calc_image_merge_clip(p1, p2, dst, q1, q2):
    """
    p1 (x1, y1, z1) and p2 (x2, y2, z2) define the extent of the (non-scaled)
    data shown.  The image, defined by region q1, q2 is to be placed at dst
    in the image (destination may be outside of the actual data array).

    Refines the modified points (q1', q2') defining the clipped rectangle
    needed to be cut from the source array and scaled.
    """
    x1, y1 = p1[:2]
    x2, y2 = p2[:2]
    dst_x, dst_y = dst[:2]
    a1, b1 = q1[:2]
    a2, b2 = q2[:2]
    src_wd, src_ht = a2 - a1, b2 - b1

    # Trim off parts of srcarr that would be "hidden"
    # to the left and above the dstarr edge.
    ex = y1 - dst_y
    if ex > 0:
        src_ht -= ex
        dst_y += ex
        b1 += ex

    ex = x1 - dst_x
    if ex > 0:
        src_wd -= ex
        dst_x += ex
        a1 += ex

    # Trim off parts of srcarr that would be "hidden"
    # to the right and below dstarr edge.
    ex = dst_y + src_ht - y2
    if ex > 0:
        src_ht -= ex
        b2 -= ex

    ex = dst_x + src_wd - x2
    if ex > 0:
        src_wd -= ex
        a2 -= ex

    if len(p1) > 2:
        # 3D image
        z1, z2, dst_z, c1, c2 = p1[2], p2[2], dst[2], q1[2], q2[2]
        src_dp = c2 - c1

        ex = z1 - dst_z
        if ex > 0:
            src_dp -= ex
            dst_z += ex
            c1 += ex

        ex = dst_z + src_dp - z2
        if ex > 0:
            src_dp -= ex
            c2 -= ex

        return ((dst_x, dst_y, dst_z), (a1, b1, c1), (a2, b2, c2))

    else:
        return ((dst_x, dst_y), (a1, b1), (a2, b2))


def overlay_image_2d_pil(dstarr, pos, srcarr, dst_order='RGBA',
                         src_order='RGBA',
                         alpha=1.0, copy=False, fill=False, flipy=False):

    dst_x, dst_y = int(round(pos[0])), int(round(pos[1]))

    if flipy:
        srcarr = np.flipud(srcarr)

    if dst_order != src_order:
        srcarr = reorder_image(dst_order, srcarr, src_order)
    img_dst = Image.fromarray(dstarr)
    img_src = Image.fromarray(srcarr)

    mask = img_src
    if 'A' not in src_order:
        mask = None
    img_dst.paste(img_src, (dst_x, dst_y), mask=mask)

    res_arr = np.array(img_dst, dtype=dstarr.dtype)
    if copy:
        return res_arr

    dstarr[:, :, :] = res_arr


def overlay_image_2d_np(dstarr, pos, srcarr, dst_order='RGBA',
                        src_order='RGBA',
                        alpha=1.0, copy=False, fill=False, flipy=False):

    dst_ht, dst_wd, dst_ch = dstarr.shape
    dst_type = dstarr.dtype
    dst_max_val = np.iinfo(dst_type).max
    src_ht, src_wd, src_ch = srcarr.shape
    src_type = srcarr.dtype
    src_max_val = np.iinfo(src_type).max
    dst_x, dst_y = int(round(pos[0])), int(round(pos[1]))

    if flipy:
        srcarr = np.flipud(srcarr)

    # Trim off parts of srcarr that would be "hidden"
    # to the left and above the dstarr edge.
    if dst_y < 0:
        dy = abs(dst_y)
        srcarr = srcarr[dy:, :, :]
        src_ht -= dy
        dst_y = 0

    if dst_x < 0:
        dx = abs(dst_x)
        srcarr = srcarr[:, dx:, :]
        src_wd -= dx
        dst_x = 0

    # Trim off parts of srcarr that would be "hidden"
    # to the right and below the dstarr edge.
    ex = dst_y + src_ht - dst_ht
    if ex > 0:
        srcarr = srcarr[:dst_ht, :, :]
        src_ht -= ex

    ex = dst_x + src_wd - dst_wd
    if ex > 0:
        srcarr = srcarr[:, :dst_wd, :]
        src_wd -= ex

    if src_wd <= 0 or src_ht <= 0:
        # nothing to do
        return dstarr

    if copy:
        dstarr = np.copy(dstarr, order='C')

    da_idx = -1
    slc = slice(0, 3)
    if 'A' in dst_order:
        da_idx = dst_order.index('A')

        # Currently we assume that alpha channel is in position 0 or 3 in dstarr
        if da_idx == 0:
            slc = slice(1, 4)
        elif da_idx != 3:
            raise ValueError("Alpha channel not in expected position (0 or 4) in dstarr")

    # fill alpha channel in destination in the area we will be dropping
    # the image
    if fill and (da_idx >= 0):
        dstarr[dst_y:dst_y + src_ht, dst_x:dst_x + src_wd, da_idx] = dst_max_val

    # if overlay source contains an alpha channel, extract it
    # and use it, otherwise use scalar keyword parameter
    if (src_ch > 3) and ('A' in src_order):
        sa_idx = src_order.index('A')
        alpha = srcarr[:src_ht, :src_wd, sa_idx]
        if np.all(np.isclose(alpha, src_max_val)):
            # optimization to avoid blending if all alpha elements are max
            alpha = 1.0
        else:
            alpha = alpha / float(src_max_val)
            alpha = np.dstack((alpha, alpha, alpha))

    # reorder srcarr if necessary to match dstarr for alpha merge
    get_order = dst_order
    if ('A' in dst_order) and ('A' not in src_order):
        get_order = dst_order.replace('A', '')
    if get_order != src_order:
        srcarr = reorder_image(get_order, srcarr, src_order)

    # define the two subarrays we are blending
    _dst = dstarr[dst_y:dst_y + src_ht, dst_x:dst_x + src_wd, slc]
    _src = srcarr[:src_ht, :src_wd, slc]

    if np.isscalar(alpha) and alpha == 1.0:
        # optimization to avoid alpha blending
        # Place our srcarr into this dstarr at dst offsets
        _dst[:, :, :] = _src
    else:
        # calculate alpha blending
        #   Co = CaAa + CbAb(1 - Aa)
        _dst[:, :, :] = (alpha * _src) + (1.0 - alpha) * _dst

    return dstarr


def overlay_image_2d(dstarr, pos, srcarr, dst_order='RGBA',
                     src_order='RGBA',
                     alpha=1.0, copy=False, fill=False, flipy=False):
    # NOTE: not tested yet thoroughly enough to use
    # return overlay_image_2d_pil(dstarr, pos, srcarr, dst_order=dst_order,
    #                             src_order=src_order, alpha=alpha,
    #                             copy=copy, fill=fill, flipy=flipy)

    return overlay_image_2d_np(dstarr, pos, srcarr, dst_order=dst_order,
                               src_order=src_order, alpha=alpha,
                               copy=copy, fill=fill, flipy=flipy)


def overlay_image_3d(dstarr, pos, srcarr, dst_order='RGBA', src_order='RGBA',
                     alpha=1.0, copy=False, fill=True, flipy=False):

    dst_x, dst_y, dst_z = [int(round(pos[n])) for n in range(3)]
    dst_ht, dst_wd, dst_dp, dst_ch = dstarr.shape
    dst_type = dstarr.dtype
    dst_max_val = np.iinfo(dst_type).max
    src_ht, src_wd, src_dp, src_ch = srcarr.shape
    src_type = srcarr.dtype
    src_max_val = np.iinfo(src_type).max

    if flipy:
        srcarr = np.flipud(srcarr)

    # Trim off parts of srcarr that would be "hidden"
    # to the left and above the dstarr edge.
    if dst_y < 0:
        dy = abs(dst_y)
        srcarr = srcarr[dy:, :, :, :]
        src_ht -= dy
        dst_y = 0

    if dst_x < 0:
        dx = abs(dst_x)
        srcarr = srcarr[:, dx:, :, :]
        src_wd -= dx
        dst_x = 0

    if dst_z < 0:
        dz = abs(dst_z)
        srcarr = srcarr[:, :, dz:, :]
        src_dp -= dz
        dst_z = 0

    # Trim off parts of srcarr that would be "hidden"
    # to the right and below the dstarr edge.
    ex = dst_y + src_ht - dst_ht
    if ex > 0:
        srcarr = srcarr[:dst_ht, :, :, :]
        src_ht -= ex

    ex = dst_x + src_wd - dst_wd
    if ex > 0:
        srcarr = srcarr[:, :dst_wd, :, :]
        src_wd -= ex

    ex = dst_z + src_dp - dst_dp
    if ex > 0:
        srcarr = srcarr[:, :, :dst_dp, :]
        src_dp -= ex

    if src_wd <= 0 or src_ht <= 0 or src_dp <= 0:
        # nothing to do
        return dstarr

    if copy:
        dstarr = np.copy(dstarr, order='C')

    da_idx = -1
    slc = slice(0, 3)
    if 'A' in dst_order:
        da_idx = dst_order.index('A')

        # Currently we assume that alpha channel is in position 0 or 3 in dstarr
        if da_idx == 0:
            slc = slice(1, 4)
        elif da_idx != 3:
            raise ValueError("Alpha channel not in expected position (0 or 4) in dstarr")

    # fill alpha channel in destination in the area we will be dropping
    # the image
    if fill and (da_idx >= 0):
        dstarr[dst_y:dst_y + src_ht, dst_x:dst_x + src_wd,
               dst_z:dst_z + src_dp, da_idx] = dst_max_val

    # if overlay source contains an alpha channel, extract it
    # and use it, otherwise use scalar keyword parameter
    if (src_ch > 3) and ('A' in src_order):
        sa_idx = src_order.index('A')
        alpha = srcarr[:src_ht, :src_wd, :src_dp, sa_idx]
        if np.all(np.isclose(alpha, src_max_val)):
            # optimization to avoid blending if all alpha elements are max
            alpha = 1.0
        else:
            alpha = srcarr[0:src_ht, 0:src_wd, 0:src_dp, sa_idx] / float(src_max_val)
            alpha = np.concatenate([alpha[..., np.newaxis],
                                    alpha[..., np.newaxis],
                                    alpha[..., np.newaxis]],
                                   axis=-1)

    # reorder srcarr if necessary to match dstarr for alpha merge
    get_order = dst_order
    if ('A' in dst_order) and not ('A' in src_order):
        get_order = dst_order.replace('A', '')
    if get_order != src_order:
        srcarr = reorder_image(get_order, srcarr, src_order)

    # define the two subarrays we are blending
    _dst = dstarr[dst_y:dst_y + src_ht, dst_x:dst_x + src_wd,
                  dst_z:dst_z + src_dp, slc]
    _src = srcarr[:src_ht, :src_wd, :src_dp, slc]

    if np.isscalar(alpha) and alpha == 1.0:
        # optimization to avoid alpha blending
        # Place our srcarr into this dstarr at dst offsets
        _dst[:, :, :, :] = _src
    else:
        # calculate alpha blending
        #   Co = CaAa + CbAb(1 - Aa)
        _dst[:, :, :, :] = (alpha * _src) + (1.0 - alpha) * _dst

    return dstarr


def overlay_image(dstarr, pos, srcarr, **kwargs):
    method = overlay_image_2d
    if len(srcarr.shape) > 3:
        method = overlay_image_3d

    return method(dstarr, pos, srcarr, **kwargs)


def reorder_image(dst_order, src_arr, src_order):
    """Reorder src_arr, with order of color planes in src_order, as
    dst_order.
    """
    depth = src_arr.shape[2]
    if depth != len(src_order):
        if len(dst_order.replace('A', '')) != len(src_order.replace('A', '')):
            raise ValueError("src_order (%s) does not match array depth (%d)" % (
                src_order, depth))

    bands = []
    if dst_order == src_order:
        return np.ascontiguousarray(src_arr)

    missing = set(dst_order) - set(src_order)
    if len(missing) == 0:
        # <-- we don't have to add an alpha plane, just create a new view
        idx = np.array([src_order.index(c) for c in dst_order])
        return np.ascontiguousarray(src_arr[..., idx])

    if missing != set(['A']):
        missing = list(missing - set(['A']))
        raise ValueError("source array missing channels ({}) needed in "
                         "destination array ({})".format(src_order, dst_order))

    # <-- dst order requires missing alpha channel
    indexes = [src_order.index(c) for c in dst_order.replace('A', '')]
    bands = [src_arr[..., idx, np.newaxis] for idx in indexes]
    ht, wd = src_arr.shape[:2]
    dst_type = src_arr.dtype
    dst_max_val = np.iinfo(dst_type).max
    alpha = np.full((ht, wd, 1), dst_max_val, dtype=dst_type)
    bands.insert(dst_order.index('A'), alpha)

    return np.concatenate(bands, axis=-1)


def strip_z(pts):
    """Strips a Z component from `pts` if it is present."""
    pts = np.asarray(pts)
    if pts.shape[-1] > 2:
        pts = np.asarray((pts.T[0], pts.T[1])).T
    return pts


def pad_z(pts, value=0.0, dtype=np.float32):
    """Adds a Z component from `pts` if it is missing.
    The value defaults to `value` (0.0)"""
    pts = np.asarray(pts, dtype=dtype)
    if pts.shape[-1] < 3:
        if len(pts.shape) < 2:
            return np.asarray((pts[0], pts[1], value), dtype=pts.dtype)
        pad_col = np.full(len(pts), value, dtype=pts.dtype)
        pts = np.asarray((pts.T[0], pts.T[1], pad_col)).T
    return pts


def get_bounds(pts):
    """Return the minimum point and maximum point bounding a
    set of points."""
    pts_t = np.asarray(pts).T
    return np.asarray(([np.min(_pts) for _pts in pts_t],
                       [np.max(_pts) for _pts in pts_t]))


def sort_xy(x1, y1, x2, y2):
    """Sort a set of bounding box parameters."""
    pmn, pmx = get_bounds(((x1, y1), (x2, y2)))
    return (pmn[0], pmn[1], pmx[0], pmx[1])


def fill_array(dstarr, order, r, g, b, a):
    """Fill array dstarr with a color value. order defines the color planes
    in the array.  (r, g, b, a) are expected to be in the range 0..1 and
    are scaled to the appropriate values.

    dstarr can be a 2D or 3D array.
    """
    # TODO: can we make this more efficient?
    dtype = dstarr.dtype
    maxv = np.iinfo(dtype).max
    bgval = dict(A=int(maxv * a), R=int(maxv * r), G=int(maxv * g),
                 B=int(maxv * b))
    bgtup = tuple([bgval[order[i]] for i in range(len(order))])
    if dtype == _dtype_uint8 and len(bgtup) == 4:
        # optimiztion
        bgtup = np.array(bgtup, dtype=dtype).view(np.uint32)[0]
        dstarr = dstarr.view(np.uint32)

    dstarr[..., :] = bgtup


def make_filled_array(shp, dtype, order, r, g, b, a):
    """Return a filled array with a color value. order defines the color
    planes in the array.  (r, g, b, a) are expected to be in the range
    0..1 and are scaled to the appropriate values.

    shp can define a 2D or 3D array.
    """
    # TODO: can we make this more efficient?
    maxv = np.iinfo(dtype).max
    bgval = dict(A=int(maxv * a), R=int(maxv * r), G=int(maxv * g),
                 B=int(maxv * b))
    bgtup = tuple([bgval[order[i]] for i in range(len(order))])
    if dtype == _dtype_uint8 and len(bgtup) == 4:
        # optimization when dealing with 32-bit RGBA arrays
        fill_val = np.array(bgtup, dtype=dtype).view(np.uint32)
        rgba = np.zeros(shp, dtype=dtype)
        rgba_i = rgba.view(np.uint32)
        rgba_i[:] = fill_val
        return rgba
    return np.full(shp, bgtup, dtype=dtype)


def remove_alpha(arr):
    """Takes an array and removes an alpha layer from it if it has one.

    Parameters
    ----------
    arr : ndarray
        The input array

    Returns
    -------
    new_arr, alpha_arr : both ndarray
        The input array with the alpha layer removed, and the alpha array
        None is returned for the alpha array if there was none.
    """
    if len(arr.shape) == 2:
        return arr, None

    if arr.shape[2] in (2, 4):
        alpha = arr[..., -1]
        arr = arr[..., 0:-1]
        return arr, alpha

    return arr, None


def add_alpha(arr, alpha=None):
    """Takes an array and adds an alpha layer to it if it doesn't already
    exist.

    Parameters
    ----------
    arr : ndarray
        The input array

    alpha : int, float, ndarray or None (optional)
        A single value or array of values for the alpha layer to be added

    Returns
    -------
    new_arr : ndarray
        The input array with the alpha layer added.
    """
    if len(arr.shape) == 2:
        arr = arr[..., np.newaxis]

    if arr.shape[2] in (1, 3):
        a_arr = np.zeros(arr.shape[:2], dtype=arr.dtype)
        if alpha is not None:
            a_arr[:, :] = alpha
        arr = np.dstack((arr, a_arr))

    return arr


def get_minmax_dtype(dtype):
    if issubclass(dtype.type, np.integer):
        info = np.iinfo(dtype)
    else:
        info = np.finfo(dtype)

    return info.min, info.max


def array_convert(arr_np, to_dtype):
    """Convert an array from one datatype to another, preserving relative value.

    Parameters
    ----------
    arr_np : ndarray
        A numpy array of data

    to_dtype : numpy dtype (e.g. np.dtype(np.uint16))
        the ndarray data type to convert to

    Returns
    -------
    res_np : ndarray
       The converted array
    """
    if arr_np.dtype == to_dtype:
        # we are already in the desired datatype--no action
        return arr_np
    mn_f, mx_f = get_minmax_dtype(arr_np.dtype)
    mn_t, mx_t = get_minmax_dtype(to_dtype)
    arr_np = (arr_np / mx_f * mx_t).astype(to_dtype)
    return arr_np


def check_native_byteorder(data_np):
    dt = str(data_np.dtype)

    return ((dt.startswith('>') and sys.byteorder == 'little') or
            (dt.startswith('<') and sys.byteorder == 'big'))


def cutout_data(data, x1, y1, x2, y2, xstep=1, ystep=1, z=None,
                astype=None):
    """Cut out data area based on bounded coordinates.

    Parameters
    ----------
    x1, y1 : int
        Coordinates defining the minimum corner to be cut out

    x2, y2 : int
        Coordinates *one greater* than the maximum corner

    xstep, ystep : int
        Step values for skip intervals in the cutout region

    z : int
        Value for a depth (slice) component for color images

    astype :

    Note that the coordinates for `x2`, `y2` are *outside* the
    cutout region, similar to slicing parameters in Python.
    """
    view = np.s_[y1:y2:ystep, x1:x2:xstep]
    data_np = data[view]
    if z is not None and len(data_np.shape) > 2:
        data_np = data_np[..., z]
    if astype:
        data_np = data_np.astype(astype, copy=False)
    return data_np


def cutout_adjust(data, x1, y1, x2, y2, xstep=1, ystep=1, z=0, astype=None):
    """Like `cutout_data`, but adjusts coordinates `x1`, `y1`, `x2`, `y2`
    to be inside the data area if they are not already.  It tries to
    preserve the width and height of the region, so e.g. (-2, -2, 5, 5)
    could become (0, 0, 7, 7)
    """
    height, width = data.shape[:2]
    dx = x2 - x1
    dy = y2 - y1

    if x1 < 0:
        x1, x2 = 0, dx
    else:
        if x2 >= width:
            x2 = width
            x1 = x2 - dx

    if y1 < 0:
        y1, y2 = 0, dy
    else:
        if y2 >= height:
            y2 = height
            y1 = y2 - dy

    data = cutout_data(data, x1, y1, x2, y2, xstep=xstep, ystep=ystep,
                       z=z, astype=astype)
    return (data, x1, y1, x2, y2)


def cutout_radius(data, x, y, radius, xstep=1, ystep=1, astype=None):
    return cutout_adjust(data, x - radius, y - radius,
                         x + radius + 1, y + radius + 1,
                         xstep=xstep, ystep=ystep, astype=astype)


def guess_order(shape):
    if len(shape) <= 2:
        order = 'M'
    else:
        depth = shape[-1]
        if depth == 1:
            order = 'M'
        elif depth == 2:
            order = 'MA'
        elif depth == 3:
            order = 'RGB'
        elif depth == 4:
            order = 'RGBA'

    return order


def get_aspect(shape):
    return shape[1] / shape[0]


def calc_aspect_str(wd, ht):
    # calculate the aspect ratio given by width and height and make
    # string of the form "x:y"
    gcd = np.gcd(wd, ht)
    _wd, _ht = int(wd / gcd), int(ht / gcd)
    _as = str(_wd) + ':' + str(_ht)
    return _as
