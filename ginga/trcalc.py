#
# trcalc.py -- transformation calculations for image data
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy as np

interpolation_methods = ['basic']


def use(pkgname):
    global have_opencv, cv2, cv2_resize
    global have_opencl, trcalc_cl

    if pkgname == 'opencv':
        import cv2
        have_opencv = True
        cv2_resize = {
            'nearest': cv2.INTER_NEAREST,
            'linear': cv2.INTER_LINEAR,
            'area': cv2.INTER_AREA,
            'bicubic': cv2.INTER_CUBIC,
            'lanczos': cv2.INTER_LANCZOS4,
        }
        if 'nearest' not in interpolation_methods:
            interpolation_methods.extend(cv2_resize.keys())
            interpolation_methods.sort()

    elif pkgname == 'opencl':
        try:
            from ginga.opencl import CL
            have_opencl = True

            trcalc_cl = CL.CL('trcalc.cl')
        except Exception as e:
            raise ImportError(e)


have_opencv = False
try:
    # optional opencv package speeds up certain operations, especially
    # rotation
    # TEMP: opencv broken on older anaconda mac (importing causes segv)
    # --> temporarily disable, can enable using use() function above
    #use('opencv')
    pass

except ImportError:
    pass

have_opencl = False
trcalc_cl = None
try:
    # optional opencl package speeds up certain operations, especially
    # rotation
    # TEMP: pyopencl prompts users if it can't determine which device
    #       to use for acceleration.
    # --> temporarily disable, can enable using use() function above
    #use('opencl')
    pass

except ImportError:
    pass

have_numexpr = False
try:
    # optional numexpr package speeds up certain combined numpy array
    # operations, especially rotation
    import numexpr as ne
    have_numexpr = True

except ImportError:
    pass

# For testing
#have_numexpr = False
#have_opencv = False
#have_opencl = False


def get_center(data_np):
    ht, wd = data_np.shape[:2]

    ctr_x = wd // 2
    ctr_y = ht // 2
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
                out=None, use_opencl=True, logger=None):
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

    if rotctr_x is None:
        rotctr_x = wd // 2
    if rotctr_y is None:
        rotctr_y = ht // 2

    if have_opencv:
        if logger is not None:
            logger.debug("rotating with OpenCv")
        # opencv is fastest
        M = cv2.getRotationMatrix2D((rotctr_y, rotctr_x), theta_deg, 1)
        if out is not None:
            out[:, :, ...] = cv2.warpAffine(data_np, M, (wd, ht))
            newdata = out

        else:
            newdata = cv2.warpAffine(data_np, M, (wd, ht))
            new_ht, new_wd = newdata.shape[:2]

            assert (wd == new_wd) and (ht == new_ht), \
                Exception("rotated cutout is %dx%d original=%dx%d" % (
                    new_wd, new_ht, wd, ht))

    elif have_opencl and use_opencl:
        if logger is not None:
            logger.debug("rotating with OpenCL")
        # opencl is very close, sometimes better, sometimes worse
        if (data_np.dtype == np.uint8) and (len(data_np.shape) == 3):
            # special case for 3D RGB images
            newdata = trcalc_cl.rotate_clip_uint32(data_np, theta_deg,
                                                   rotctr_x, rotctr_y,
                                                   out=out)
        else:
            newdata = trcalc_cl.rotate_clip(data_np, theta_deg,
                                            rotctr_x, rotctr_y,
                                            out=out)

    else:
        if logger is not None:
            logger.debug("rotating with numpy")
        yi, xi = np.mgrid[0:ht, 0:wd]
        xi -= rotctr_x
        yi -= rotctr_y
        cos_t = np.cos(np.radians(theta_deg))
        sin_t = np.sin(np.radians(theta_deg))

        if have_numexpr:
            ap = ne.evaluate("(xi * cos_t) - (yi * sin_t) + rotctr_x")
            bp = ne.evaluate("(xi * sin_t) + (yi * cos_t) + rotctr_y")
        else:
            ap = (xi * cos_t) - (yi * sin_t) + rotctr_x
            bp = (xi * sin_t) + (yi * cos_t) + rotctr_y

        #ap = np.rint(ap).astype('int').clip(0, wd-1)
        #bp = np.rint(bp).astype('int').clip(0, ht-1)
        # Optomizations to reuse existing intermediate arrays
        np.rint(ap, out=ap)
        ap = ap.astype('int')
        ap.clip(0, wd - 1, out=ap)
        np.rint(bp, out=bp)
        bp = bp.astype('int')
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
           use_opencl=True, logger=None):

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

    if have_opencl and use_opencl:
        if logger is not None:
            logger.debug("rotating with OpenCL")
        # find offsets of old image in new image
        dx, dy = ncx - ocx, ncy - ocy

        newdata = trcalc_cl.rotate(data_np, theta_deg,
                                   rotctr_x=rotctr_x, rotctr_y=rotctr_y,
                                   clip_val=0, out=None,
                                   out_wd=new_wd, out_ht=new_ht,
                                   out_dx=dx, out_dy=dy)
    else:
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
    """
    Like get_scaled_cutout_wdht, but returns the view/slice to extract
    from an image instead of the extraction itself.
    """
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    new_wd, new_ht = int(new_wd), int(new_ht)

    # calculate dimensions of NON-scaled cutout
    old_wd = x2 - x1 + 1
    old_ht = y2 - y1 + 1
    max_x, max_y = shp[1] - 1, shp[0] - 1

    if (new_wd != old_wd) or (new_ht != old_ht):
        # Make indexes and scale them
        # Is there a more efficient way to do this?
        yi = np.mgrid[0:new_ht].reshape(-1, 1)
        xi = np.mgrid[0:new_wd].reshape(1, -1)
        iscale_x = float(old_wd) / float(new_wd)
        iscale_y = float(old_ht) / float(new_ht)

        xi = (x1 + xi * iscale_x).clip(0, max_x).astype('int')
        yi = (y1 + yi * iscale_y).clip(0, max_y).astype('int')
        wd, ht = xi.shape[1], yi.shape[0]

        # bounds check against shape (to protect future data access)
        xi_max, yi_max = xi[0, -1], yi[-1, 0]
        assert xi_max <= max_x, ValueError("X index (%d) exceeds shape bounds (%d)" % (xi_max, max_x))
        assert yi_max <= max_y, ValueError("Y index (%d) exceeds shape bounds (%d)" % (yi_max, max_y))

        view = np.s_[yi, xi]

    else:
        # simple stepped view will do, because new view is same as old
        wd, ht = old_wd, old_ht
        view = np.s_[y1:y2 + 1, x1:x2 + 1]

    # Calculate actual scale used (vs. desired)
    old_wd, old_ht = max(old_wd, 1), max(old_ht, 1)
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

    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2), int(z1), int(z2)
    z1, z2, new_wd, new_ht = int(z1), int(z2), int(new_wd), int(new_ht)

    # calculate dimensions of NON-scaled cutout
    old_wd = x2 - x1 + 1
    old_ht = y2 - y1 + 1
    old_dp = z2 - z1 + 1
    max_x, max_y, max_z = shp[1] - 1, shp[0] - 1, shp[2] - 1

    if (new_wd != old_wd) or (new_ht != old_ht) or (new_dp != old_dp):
        # Make indexes and scale them
        # Is there a more efficient way to do this?
        yi = np.mgrid[0:new_ht].reshape(-1, 1, 1)
        xi = np.mgrid[0:new_wd].reshape(1, -1, 1)
        zi = np.mgrid[0:new_dp].reshape(1, 1, -1)
        iscale_x = float(old_wd) / float(new_wd)
        iscale_y = float(old_ht) / float(new_ht)
        iscale_z = float(old_dp) / float(new_dp)

        xi = (x1 + xi * iscale_x).clip(0, max_x).astype('int')
        yi = (y1 + yi * iscale_y).clip(0, max_y).astype('int')
        zi = (z1 + zi * iscale_z).clip(0, max_z).astype('int')
        wd, ht, dp = xi.shape[1], yi.shape[0], zi.shape[2]

        # bounds check against shape (to protect future data access)
        xi_max, yi_max, zi_max = xi[0, -1, 0], yi[-1, 0, 0], zi[0, 0, -1]
        assert xi_max <= max_x, ValueError("X index (%d) exceeds shape bounds (%d)" % (xi_max, max_x))
        assert yi_max <= max_y, ValueError("Y index (%d) exceeds shape bounds (%d)" % (yi_max, max_y))
        assert zi_max <= max_z, ValueError("Z index (%d) exceeds shape bounds (%d)" % (zi_max, max_z))

        view = np.s_[yi, xi, zi]

    else:
        # simple stepped view will do, because new view is same as old
        wd, ht, dp = old_wd, old_ht, old_dp
        view = np.s_[y1:y2 + 1, x1:x2 + 1, z1:z2 + 1]

    # Calculate actual scale used (vs. desired)
    old_wd, old_ht, old_dp = max(old_wd, 1), max(old_ht, 1), max(old_dp, 1)
    scale_x = float(wd) / old_wd
    scale_y = float(ht) / old_ht
    scale_z = float(dp) / old_dp

    # return view + actual scale factors used
    return (view, (scale_x, scale_y, scale_z))


def get_scaled_cutout_wdht(data_np, x1, y1, x2, y2, new_wd, new_ht,
                           interpolation='basic', logger=None):

    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    new_wd, new_ht = int(new_wd), int(new_ht)

    rdim = data_np.shape[2:]
    open_cl_ok = (len(rdim) == 0 or (len(rdim) == 1 and rdim[0] == 4))

    if have_opencv:
        if logger is not None:
            logger.debug("resizing with OpenCv")
        # opencv is fastest and supports many methods
        if interpolation == 'basic':
            interpolation = 'nearest'
        method = cv2_resize[interpolation]
        newdata = cv2.resize(data_np[y1:y2 + 1, x1:x2 + 1], (new_wd, new_ht),
                             interpolation=method)

        old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
        ht, wd = newdata.shape[:2]
        scale_x, scale_y = float(wd) / old_wd, float(ht) / old_ht

    elif (have_opencl and interpolation in ('basic', 'nearest') and
            open_cl_ok):
        # opencl is almost as fast or sometimes faster, but currently
        # we only support nearest neighbor
        if logger is not None:
            logger.debug("resizing with OpenCL")
        old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
        scale_x, scale_y = float(new_wd) / old_wd, float(new_ht) / old_ht

        newdata, (scale_x, scale_y) = trcalc_cl.get_scaled_cutout_basic(data_np,
                                                                        x1, y1, x2, y2,
                                                                        scale_x, scale_y)

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

    x1, y1 = p1[:2]
    x2, y2 = p2[:2]
    scale_x, scale_y = scales[:2]
    # calculate dimensions of NON-scaled cutout
    old_wd = x2 - x1 + 1
    old_ht = y2 - y1 + 1
    # calculate dimensions of scaled cutout
    new_wd = int(round(scale_x * old_wd))
    new_ht = int(round(scale_y * old_ht))

    if len(scales) == 2:
        return get_scaled_cutout_wdht_view(shp, x1, y1, x2, y2, new_wd, new_ht)

    z1, z2, scale_z = p1[2], p2[2], scales[2]
    old_dp = z2 - z1 + 1
    new_dp = int(round(scale_z * old_dp))
    return get_scaled_cutout_wdhtdp_view(shp, p1, p2, (new_wd, new_ht, new_dp))


def get_scaled_cutout_basic(data_np, x1, y1, x2, y2, scale_x, scale_y,
                            interpolation='basic', logger=None):

    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

    rdim = data_np.shape[2:]
    open_cl_ok = (len(rdim) == 0 or (len(rdim) == 1 and rdim[0] == 4))

    if have_opencv:
        if logger is not None:
            logger.debug("resizing with OpenCv")
        # opencv is fastest
        if interpolation == 'basic':
            interpolation = 'nearest'
        method = cv2_resize[interpolation]
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        newdata = cv2.resize(data_np[y1:y2 + 1, x1:x2 + 1], None,
                             fx=scale_x, fy=scale_y,
                             interpolation=method)
        old_wd, old_ht = max(x2 - x1 + 1, 1), max(y2 - y1 + 1, 1)
        ht, wd = newdata.shape[:2]
        scale_x, scale_y = float(wd) / old_wd, float(ht) / old_ht

    elif (have_opencl and interpolation in ('basic', 'nearest') and
            open_cl_ok):
        if logger is not None:
            logger.debug("resizing with OpenCL")
        newdata, (scale_x, scale_y) = trcalc_cl.get_scaled_cutout_basic(
            data_np, x1, y1, x2, y2, scale_x, scale_y)

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

    return newdata, (scale_x, scale_y)


def get_scaled_cutout_basic2(data_np, p1, p2, scales,
                             interpolation='basic', logger=None):

    if interpolation not in ('basic', 'nearest'):
        raise ValueError("Interpolation method not supported: '%s'" % (
            interpolation))

    if logger is not None:
        logger.debug('resizing by slicing')
    view, scales = get_scaled_cutout_basic_view(data_np.shape,
                                                p1, p2, scales)
    newdata = data_np[view]

    return newdata, scales


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


def overlay_image_2d(dstarr, pos, srcarr, dst_order='RGBA',
                     src_order='RGBA',
                     alpha=1.0, copy=False, fill=True, flipy=False):

    dst_ht, dst_wd, dst_ch = dstarr.shape
    src_ht, src_wd, src_ch = srcarr.shape
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

    if src_wd <= 0 or src_ht <= 0:
        return dstarr

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
        dstarr[dst_y:dst_y + src_ht, dst_x:dst_x + src_wd, da_idx] = 255

    if src_ch > 3:
        sa_idx = src_order.index('A')
        # if overlay source contains an alpha channel, extract it
        # and use it, otherwise use scalar keyword parameter
        alpha = srcarr[0:src_ht, 0:src_wd, sa_idx] / 255.0
        alpha = np.dstack((alpha, alpha, alpha))

    # reorder srcarr if necessary to match dstarr for alpha merge
    get_order = dst_order
    if ('A' in dst_order) and not ('A' in src_order):
        get_order = dst_order.replace('A', '')
    if get_order != src_order:
        srcarr = reorder_image(get_order, srcarr, src_order)

    # calculate alpha blending
    #   Co = CaAa + CbAb(1 - Aa)
    a_arr = (alpha * srcarr[0:src_ht, 0:src_wd, slc]).astype(np.uint8)
    b_arr = ((1.0 - alpha) * dstarr[dst_y:dst_y + src_ht,
                                    dst_x:dst_x + src_wd,
                                    slc]).astype(np.uint8)

    # Place our srcarr into this dstarr at dst offsets
    #dstarr[dst_y:dst_y+src_ht, dst_x:dst_x+src_wd, slc] += addarr[0:src_ht, 0:src_wd, slc]
    dstarr[dst_y:dst_y + src_ht, dst_x:dst_x + src_wd, slc] = \
        a_arr[0:src_ht, 0:src_wd, slc] + b_arr[0:src_ht, 0:src_wd, slc]

    return dstarr


def overlay_image_3d(dstarr, pos, srcarr, dst_order='RGBA', src_order='RGBA',
                     alpha=1.0, copy=False, fill=True, flipy=False):

    dst_x, dst_y, dst_z = pos
    dst_ht, dst_wd, dst_dp, dst_ch = dstarr.shape
    src_ht, src_wd, src_dp, src_ch = srcarr.shape

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

    if dst_z < 0:
        dz = abs(dst_z)
        srcarr = srcarr[:, :, dz:]
        src_dp -= dz
        dst_z = 0

    if src_wd <= 0 or src_ht <= 0 or src_dp <= 0:
        return dstarr

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

    ex = dst_z + src_dp - dst_dp
    if ex > 0:
        srcarr = srcarr[:, :, :dst_dp]
        src_dp -= ex

    if src_wd <= 0 or src_ht <= 0 or src_dp <= 0:
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
               dst_z:dst_z + src_dp, da_idx] = 255

    if src_ch > 3:
        sa_idx = src_order.index('A')
        # if overlay source contains an alpha channel, extract it
        # and use it, otherwise use scalar keyword parameter
        alpha = srcarr[0:src_ht, 0:src_wd, 0:src_dp, sa_idx] / 255.0
        #alpha = np.dstack((alpha, alpha, alpha))
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

    # calculate alpha blending
    #   Co = CaAa + CbAb(1 - Aa)
    a_arr = (alpha * srcarr[0:src_ht, 0:src_wd,
                            0:src_dp, slc]).astype(np.uint8)
    b_arr = ((1.0 - alpha) * dstarr[dst_y:dst_y + src_ht,
                                    dst_x:dst_x + src_wd,
                                    dst_z:dst_z + src_dp,
                                    slc]).astype(np.uint8)

    # Place our srcarr into this dstarr at dst offsets
    dstarr[dst_y:dst_y + src_ht, dst_x:dst_x + src_wd,
           dst_z:dst_z + src_dp, slc] = \
        a_arr[0:src_ht, 0:src_wd, 0:src_dp, slc] + \
        b_arr[0:src_ht, 0:src_wd, 0:src_dp, slc]

    return dstarr


def overlay_image(dstarr, pos, srcarr, **kwargs):
    method = overlay_image_2d
    if len(srcarr.shape) > 3:
        method = overlay_image_3d

    return method(dstarr, pos, srcarr, **kwargs)


def reorder_image(dst_order, src_arr, src_order):
    indexes = [src_order.index(c) for c in dst_order]
    #return np.dstack([ src_arr[..., idx] for idx in indexes ])
    return np.concatenate([src_arr[..., idx, np.newaxis]
                           for idx in indexes], axis=-1)


def strip_z(pts):
    """Strips a Z component from `pts` if it is present."""
    pts = np.asarray(pts)
    if pts.shape[-1] > 2:
        pts = np.asarray((pts.T[0], pts.T[1])).T
    return pts


def pad_z(pts, value=0.0):
    """Adds a Z component from `pts` if it is missing.
    The value defaults to `value` (0.0)"""
    pts = np.asarray(pts)
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


# END
