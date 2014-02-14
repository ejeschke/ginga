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


#END
