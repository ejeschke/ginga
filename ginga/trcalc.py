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


def rotate_nd(data_np, theta_deg, rotctr_x=None, rotctr_y=None):
    """
    Rotate numpy array `data_np` by `theta_deg` around rotation center
    (rotctr_x, rotctr_y).  If the rotation center is omitted it defaults
    to the center of the array.
    """
    
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

    newdata = data_np[bp, ap]
    new_ht, new_wd = newdata.shape[:2]

    assert (wd == new_wd) and (ht == new_ht), \
           Exception("rotated cutout is %dx%d original=%dx%d" % (
        new_wd, new_ht, wd, ht))

    return newdata

#END
