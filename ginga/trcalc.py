#
# trcalc.py -- transformation calculations for image data
# 
# Eric Jeschke (eric@naoj.org) 
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy
import time

try:
    # optional numexpr package speeds up certain combined numpy array
    # operations, especially rotation
    import numexpr as ne
    have_numexpr = True

except ImportError:
    have_numexpr = False

# For testing
#have_numexpr = False

def get_center(data_np):
    ht, wd = data_np.shape[:2]

    ctr_x = wd // 2
    ctr_y = ht // 2
    return (ctr_x, ctr_y)
    

def rotate_pt(x, y, theta_deg, xoff=0, yoff=0):
    """
    Rotate a point (x, y) by theta_deg offsetted from a center point
    by (xoff, yoff).
    """
    a = x - xoff
    b = y - yoff
    cos_t = math.cos(math.radians(theta_deg))
    sin_t = math.sin(math.radians(theta_deg))
    ap = (a * cos_t) - (b * sin_t)
    bp = (a * sin_t) + (b * cos_t)
    return (ap + xoff, bp + yoff)


def rotate_clip(data_np, theta_deg, rotctr_x=None, rotctr_y=None,
                out=None):
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

    if rotctr_x == None:
        rotctr_x = wd // 2
    if rotctr_y == None:
        rotctr_y = ht // 2

    yi, xi = numpy.mgrid[0:ht, 0:wd]
    xi -= rotctr_x
    yi -= rotctr_y
    cos_t = numpy.cos(numpy.radians(theta_deg))
    sin_t = numpy.sin(numpy.radians(theta_deg))

    #t1 = time.time()
    if have_numexpr:
        ap = ne.evaluate("(xi * cos_t) - (yi * sin_t) + rotctr_x")
        bp = ne.evaluate("(xi * sin_t) + (yi * cos_t) + rotctr_y")
    else:
        ap = (xi * cos_t) - (yi * sin_t) + rotctr_x
        bp = (xi * sin_t) + (yi * cos_t) + rotctr_y
    #print "rotation in %.5f sec" % (time.time() - t1)

    #ap = numpy.rint(ap).astype('int').clip(0, wd-1)
    #bp = numpy.rint(bp).astype('int').clip(0, ht-1)
    # Optomizations to reuse existing intermediate arrays
    numpy.rint(ap, out=ap)
    ap = ap.astype('int')
    ap.clip(0, wd-1, out=ap)
    numpy.rint(bp, out=bp)
    bp = bp.astype('int')
    bp.clip(0, ht-1, out=bp)

    if out != None:
        out[:, :, ...] = data_np[bp, ap]
        newdata = out
    else:
        newdata = data_np[bp, ap]
        new_ht, new_wd = newdata.shape[:2]

        assert (wd == new_wd) and (ht == new_ht), \
               Exception("rotated cutout is %dx%d original=%dx%d" % (
            new_wd, new_ht, wd, ht))

    return newdata


def rotate(data_np, theta_deg, rotctr_x=None, rotctr_y=None):

    # If there is no rotation, then we are done
    if math.fmod(theta_deg, 360.0) == 0.0:
        return data_np

    ht, wd = data_np.shape[:2]

    ## ocx, ocy = rotctr_x, rotctr_y
    ## if ocx == None:
    ##     ocx = wd // 2
    ## if ocy == None:
    ##     ocy = ht // 2
    ocx, ocy = wd // 2, ht // 2

    # Make a square with room to rotate
    slop = 20
    side = int(math.sqrt(wd**2 + ht**2) + slop)
    new_wd = new_ht = side
    dims = (new_ht, new_wd) + data_np.shape[2:]
    # TODO: fill with a different value?
    newdata = numpy.zeros(dims)
    # Find center of new data array 
    ncx, ncy = new_wd // 2, new_ht // 2

    # Overlay the old image on the new (blank) image
    ldx, rdx = min(ocx, ncx), min(wd - ocx, ncx)
    bdy, tdy = min(ocy, ncy), min(ht - ocy, ncy)

    newdata[ncy-bdy:ncy+tdy, ncx-ldx:ncx+rdx] = \
                             data_np[ocy-bdy:ocy+tdy, ocx-ldx:ocx+rdx]

    # find offsets of old image in new image
    #dx, dy = ncx - ocx, ncy - ocy

    # Now rotate as usual
    newdata = rotate_clip(newdata, theta_deg,
                          rotctr_x=rotctr_x, rotctr_y=rotctr_y,
                          out=newdata)
    return newdata

                     
def get_scaled_cutout_wdht(data_np, x1, y1, x2, y2, new_wd, new_ht):

    # calculate dimensions of NON-scaled cutout
    old_wd = x2 - x1 + 1
    old_ht = y2 - y1 + 1

    if (new_wd != old_wd) or (new_ht != old_ht):
        # Is there a more efficient way to do this?
        # Make indexes and scale them
        yi, xi = numpy.mgrid[0:new_ht, 0:new_wd]
        iscale_x = float(old_wd) / float(new_wd)
        iscale_y = float(old_ht) / float(new_ht)

        xi *= iscale_x 
        yi *= iscale_y

        # Cut out the data according to region desired
        cutout = data_np[y1:y2+1, x1:x2+1]

        # Now index cutout by scaled indexes
        ht, wd = cutout.shape[:2]
        xi = xi.astype('int').clip(0, wd-1)
        yi = yi.astype('int').clip(0, ht-1)
        newdata = cutout[yi, xi]

    else:
        newdata = data_np[y1:y2+1, x1:x2+1]

    # Calculate actual scale used (vs. desired)
    ht, wd = newdata.shape[:2]
    old_wd, old_ht = max(old_wd, 1), max(old_ht, 1)
    scale_x = float(wd) / old_wd
    scale_y = float(ht) / old_ht

    # return newdata + actual scale factors used
    return (newdata, (scale_x, scale_y))


def get_scaled_cutout_basic(data_np, x1, y1, x2, y2, scale_x, scale_y):

    # calculate dimensions of NON-scaled cutout
    old_wd = x2 - x1 + 1
    old_ht = y2 - y1 + 1
    # calculate dimensions of scaled cutout
    new_wd = int(round(scale_x * old_wd))
    new_ht = int(round(scale_y * old_ht))

    return get_scaled_cutout_wdht(data_np, x1, y1, x2, y2, new_wd, new_ht)


def transform(data_np, flip_x=False, flip_y=False, swap_xy=False):

    # Do transforms as necessary
    if flip_y:
        data_np = numpy.flipud(data_np)
    if flip_x:
        data_np = numpy.fliplr(data_np)
    if swap_xy:
        data_np = data_np.swapaxes(0, 1)

    return data_np


def calc_image_merge_clip(x1, y1, x2, y2,
                          dst_x, dst_y, a1, b1, a2, b2):
    """
    (x1, y1) and (x2, y2) define the extent of the (non-scaled) data
    shown.  The image, defined by region (a1, b1), (a2, b2) is to be
    placed at (dst_x, dst_y) in the image (destination may be outside
    of the actual data array).

    Refines the tuple (a1, b1, a2, b2) defining the clipped rectangle
    needed to be cut from the source array and scaled.
    """
    #print "calc clip in dst", x1, y1, x2, y2
    #print "calc clip in src", dst_x, dst_y, a1, b1, a2, b2

    src_wd, src_ht = a2 - a1, b2 - b1

    # Trim off parts of srcarr that would be "hidden"
    # to the left and above the dstarr edge.
    ex = y1 - dst_y
    if ex > 0:
        src_ht -= ex
        dst_y += ex
        #b2 -= ex
        b1 += ex

    ex = x1 - dst_x
    if ex > 0:
        src_wd -= ex
        dst_x += ex
        a1 += ex

    # Trim off parts of srcarr that would be "hidden"
    # to the right and below the dstarr edge.
    ex = dst_y + src_ht - y2
    if ex > 0:
        src_ht -= ex
        #b1 += ex
        b2 -= ex

    ex = dst_x + src_wd - x2
    if ex > 0:
        src_wd -= ex
        a2 -= ex

    #print "calc clip out", dst_x, dst_y, a1, b1, a2, b2
    return (dst_x, dst_y, a1, b1, a2, b2)


def overlay_image(dstarr, dst_x, dst_y, srcarr, order='RGBA',
                  alpha=1.0, copy=False, fill=True, flipy=False):

    dst_ht, dst_wd, dst_dp = dstarr.shape
    src_ht, src_wd, src_dp = srcarr.shape

    if flipy:
        srcarr = numpy.flipud(srcarr)

    ## print "1. dst_x, dst_y, dst_wd, dst_ht", dst_x, dst_y, dst_wd, dst_ht
    ## print "2. src_wd, src_ht, shape", src_wd, src_ht, srcarr.shape
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

    ## print "2. dst_x, dst_y", dst_x, dst_y
    ## print "2. src_wd, src_ht, shape", src_wd, src_ht, srcarr.shape

    if copy:
        dstarr = numpy.copy(dstarr, order='C')
        
    # fill alpha channel in destination in the area we will be dropping
    # the image
    if fill:
        dstarr[dst_y:dst_y+src_ht, dst_x:dst_x+src_wd, 3] = 255

    if src_dp > 3:
        # if overlay source contains an alpha channel, extract it
        # and use it, otherwise use scalar keyword parameter
        alpha = srcarr[0:src_ht, 0:src_wd, 3] / 255.0
        alpha = numpy.dstack((alpha, alpha, alpha))
    #print "alpha is", alpha
    #print "src_dp", src_dp

    # calculate alpha blending
    #   Co = CaAa + CbAb(1 - Aa)
    a_arr = (alpha * srcarr[0:src_ht, 0:src_wd, 0:3]).astype(numpy.uint8)
    b_arr = ((1.0 - alpha) * dstarr[dst_y:dst_y+src_ht,
                                    dst_x:dst_x+src_wd,
                                    0:3]).astype(numpy.uint8)

    # Place our srcarr into this dstarr at dst offsets
    #dstarr[dst_y:dst_y+src_ht, dst_x:dst_x+src_wd, 0:3] += addarr[0:src_ht, 0:src_wd, 0:3]
    dstarr[dst_y:dst_y+src_ht, dst_x:dst_x+src_wd, 0:3] = \
             a_arr[0:src_ht, 0:src_wd, 0:3] + b_arr[0:src_ht, 0:src_wd, 0:3]

    return dstarr


#END
