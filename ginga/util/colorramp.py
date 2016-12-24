#
# colorramp.py -- utility functions for making ginga colormaps
#
from __future__ import print_function
import sys

def hue_sat_to_cmap(hue, sat):
    """Mkae a color map from a hue and saturation value.
    """
    import colorsys

    # normalize to floats
    hue = float(hue) / 360.0
    sat = float(sat) / 100.0

    res = []
    for val in range(256):
        hsv_val = float(val) / 255.0
        r, g, b = colorsys.hsv_to_rgb(hue, sat, hsv_val)
        res.append((r, g, b))

    return res

def rgbarr_to_colormap(rgb_data_np):

    data = rgb_data_np

    ht, wd, dp = data.shape
    assert dp == 3

    mid_y = ht // 2

    slc = data[mid_y, :, :]
    l = [ tuple(slc[int(float(i) / 256 * wd), :]) for i in range(0, 256) ]
    assert len(l) == 256

    clst = [ (r / 255., g / 255., b / 255.) for r, g, b in l ]
    return clst

def png_to_colormap(png_file):

    from ginga.RGBImage import RGBImage
    img = RGBImage()
    img.load_file(png_file)
    data = img.get_data()

    return rgbarr_to_colormap(data)


def print_colorramp(name, clst):
    print("cmap_%s = (")

    for r, g, b in clst:
        print("                (%f, %f, %f)," % (r, g, b))

    print("                )")
    print("")

#END
