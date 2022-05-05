#
# dp.py -- Data pipeline and reduction routines
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from collections import OrderedDict

from ginga import AstroImage, colors
from ginga.RGBImage import RGBImage
from ginga.util import wcs

# counter used to name anonymous images
prefixes = dict(dp=0)


def get_image_name(image, pfx='dp'):
    global prefixes
    name = image.get('name', None)
    if name is None:
        if pfx not in prefixes:
            prefixes[pfx] = 0
        name = '{0}{1:d}'.format(pfx, prefixes[pfx])
        prefixes[pfx] += 1
        image.set(name=name)
    return name


def make_image(data_np, oldimage, header, pfx='dp'):
    # Prepare a new image with the numpy array as data
    image = AstroImage.AstroImage()
    image.set_data(data_np)
    # Set the header to be the old image header updated
    # with items from the new header
    oldhdr = oldimage.get_header()
    oldhdr.update(header)
    image.update_keywords(oldhdr)
    # give the image a name
    get_image_name(image, pfx=pfx)
    return image


def create_blank_image(ra_deg, dec_deg, fov_deg, px_scale, rot_deg,
                       cdbase=[1, 1], dtype=None, logger=None, pfx='dp',
                       mmap_path=None, mmap_mode='w+', fill=0,
                       alpha=None):

    # ra and dec in traditional format
    ra_txt = wcs.ra_deg_to_str(ra_deg)
    dec_txt = wcs.dec_deg_to_str(dec_deg)

    if np.isscalar(px_scale):
        px_wd_scale, px_ht_scale = (px_scale, px_scale)
    else:
        px_wd_scale, px_ht_scale = px_scale

    # Create an empty image
    if np.isscalar(fov_deg):
        fov_wd_deg, fov_ht_deg = (fov_deg, fov_deg)
    else:
        fov_wd_deg, fov_ht_deg = fov_deg

    width = int(round(fov_wd_deg / px_wd_scale))
    height = int(round(fov_ht_deg / px_ht_scale))
    # round to an even size
    if width % 2 != 0:
        width += 1
    if height % 2 != 0:
        height += 1

    shape = (height, width)
    if alpha is not None:
        shape = (height, width, 2)
    if dtype is None:
        dtype = np.float32
    if mmap_path is None:
        data = np.full(shape, fill, dtype=dtype)
        if alpha is not None:
            data[..., 1].fill(alpha)
    else:
        data = np.memmap(mmap_path, dtype=dtype, mode=mmap_mode,
                         shape=shape)

    crpix1 = float(width // 2)
    crpix2 = float(height // 2)
    header = OrderedDict((('SIMPLE', True),
                          ('BITPIX', -32),
                          ('EXTEND', True),
                          ('NAXIS', 2),
                          ('NAXIS1', width),
                          ('NAXIS2', height),
                          ('RA', ra_txt),
                          ('DEC', dec_txt),
                          ('EQUINOX', 2000.0),
                          ('OBJECT', 'MOSAIC'),
                          ('LONPOLE', 180.0),
                          ))

    # Add basic WCS keywords
    wcshdr = wcs.simple_wcs(crpix1, crpix2, ra_deg, dec_deg,
                            (px_wd_scale, px_ht_scale),
                            rot_deg, cdbase=cdbase)
    header.update(wcshdr)

    # Create image container
    image = AstroImage.AstroImage(data, logger=logger)
    if alpha is not None:
        image.set(ignore_alpha=True)

    image.update_keywords(header)
    # give the image a name
    get_image_name(image, pfx=pfx)

    return image


def recycle_image(image, ra_deg, dec_deg, fov_deg, px_scale, rot_deg,
                  cdbase=[1, 1], logger=None, pfx='dp', fill=0,
                  alpha=None):

    # ra and dec in traditional format
    ra_txt = wcs.ra_deg_to_str(ra_deg)
    dec_txt = wcs.dec_deg_to_str(dec_deg)

    header = image.get_header()
    pointing = OrderedDict((('RA', ra_txt),
                            ('DEC', dec_txt),
                            ))
    header.update(pointing)

    # Update WCS keywords and internal wcs objects
    wd, ht = image.get_size()
    crpix1 = wd // 2
    crpix2 = ht // 2
    wcshdr = wcs.simple_wcs(crpix1, crpix2, ra_deg, dec_deg, px_scale,
                            rot_deg, cdbase=cdbase)
    header.update(wcshdr)
    # this should update the wcs
    image.update_keywords(header)

    # zero out data array
    data = image.get_data()
    if len(data.shape) <= 2:
        data.fill(fill)
    else:
        data[..., 0].fill(fill)
    if alpha is not None:
        data[..., 1].fill(alpha)

    return image


def make_flat(imglist, bias=None):

    flats = [image.get_data() for image in imglist]
    flatarr = np.array(flats)
    # Take the median of the individual frames
    flat = np.median(flatarr, axis=0)

    # Normalize flat
    # mean or median?
    #norm = np.mean(flat.flat)
    norm = np.median(flat.flat)
    flat = flat / norm
    # no zero divisors
    flat[flat == 0.0] = 1.0

    img_flat = make_image(flat, imglist[0], {}, pfx='flat')
    return img_flat


def make_bias(imglist):

    biases = [image.get_data() for image in imglist]
    biasarr = np.array(biases)
    # Take the median of the individual frames
    bias = np.median(biasarr, axis=0)

    img_bias = make_image(bias, imglist[0], {}, pfx='bias')
    return img_bias


def add(image1, image2):
    data1_np = image1.get_data()
    data2_np = image2.get_data()

    result = data1_np + data2_np
    image = make_image(result, image1, {}, pfx='add')
    return image


def subtract(image1, image2):
    data1_np = image1.get_data()
    data2_np = image2.get_data()

    result = data1_np - data2_np
    image = make_image(result, image1, {}, pfx='sub')
    return image


def divide(image1, image2):
    data1_np = image1.get_data()
    data2_np = image2.get_data()

    result = data1_np / data2_np
    image = make_image(result, image1, {}, pfx='div')
    return image


# https://gist.github.com/stscieisenhamer/25bf6287c2c724cb9cc7
def masktorgb(mask, color='lightgreen', alpha=1.0):
    """Convert boolean mask to RGB image object for canvas overlay.

    Parameters
    ----------
    mask : ndarray
        Boolean mask to overlay. 2D image only.

    color : str
        Color name accepted by Ginga.

    alpha : float
        Opacity. Unmasked data are always transparent.

    Returns
    -------
    rgbobj : RGBImage
        RGB image for canvas Image object.

    Raises
    ------
    ValueError
        Invalid mask dimension.

    """
    mask = np.asarray(mask)

    if mask.ndim != 2:
        raise ValueError('ndim={0} is not supported'.format(mask.ndim))

    ht, wd = mask.shape
    r, g, b = colors.lookup_color(color)
    rgbobj = RGBImage(data_np=np.zeros((ht, wd, 4), dtype=np.uint8))

    rc = rgbobj.get_slice('R')
    gc = rgbobj.get_slice('G')
    bc = rgbobj.get_slice('B')
    ac = rgbobj.get_slice('A')
    ac[:] = 0  # Transparent background

    rc[mask] = int(r * 255)
    gc[mask] = int(g * 255)
    bc[mask] = int(b * 255)
    ac[mask] = int(alpha * 255)

    # For debugging
    #rgbobj.save_as_file('ztmp_rgbobj.png')

    return rgbobj


def split_n(lst, sz):
    n = len(lst)
    k, m = n // sz, n % sz
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)]
            for i in range(sz)]

# END
