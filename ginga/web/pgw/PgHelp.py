#
# PgHelp.py -- web application threading help routines.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import re
import binascii
from io import BytesIO

from PIL import Image

from ginga.misc import Bunch
from ginga.fonts import font_asst
from ginga.util import icon_helper

font_regex = re.compile(r'^(.+)\s+(\d+)$')


def get_image_src_from_buffer(img_buf, imgtype='png'):
    if not isinstance(img_buf, bytes):
        img_buf = img_buf.encode('latin1')
    img_string = binascii.b2a_base64(img_buf)
    if isinstance(img_string, bytes):
        img_string = img_string.decode("utf-8")
    return f'data:image/{imgtype};base64,' + img_string


def get_icon(iconpath, size=None, format='png'):

    if size is not None:
        wd, ht = size
    else:
        wd, ht = 24, 24

    if iconpath.lower().endswith('.svg'):
        # Scalable Vector Graphics should be scalable on the browser side
        # svg_buf = icon_helper.load_svg_to_svgbuf(iconpath, wd_px=wd, ht_px=ht)
        # icon_uri = get_image_src_from_buffer(svg_buf.getvalue(), imgtype='svg')
        # return icon_uri
        img_buf = icon_helper.load_svg_to_pngbuf(iconpath, wd_px=wd, ht_px=ht)
        icon_uri = get_image_src_from_buffer(img_buf.getvalue(), imgtype=format)
        return icon_uri

    # other types handled by pillow
    image = Image.open(iconpath)
    image = image.resize((wd, ht))

    img_buf = BytesIO()
    image.save(img_buf, format=format)

    icon_uri = get_image_src_from_buffer(img_buf.getvalue(), imgtype=format)
    return icon_uri


def get_image(imgpath, size=None, format='png'):
    if size is not None:
        wd, ht = size
    else:
        wd, ht = 24, 24
    if imgpath.endswith('.svg'):
        # Scalable Vector Graphics
        img_buf = icon_helper.load_svg_to_pngbuf(imgpath, wd_px=wd, ht_px=ht)
        img = get_image_src_from_buffer(img_buf.getvalue(), imgtype=format)
        return img

    else:
        return get_icon(imgpath, size=size, format=format)


def font_info(font_str):
    """Extract font information from a font string, such as supplied to the
    'font' argument to a widget.
    """
    vals = font_str.split(';')
    point_size, style, weight = 8, 'normal', 'normal'
    family = vals[0]
    if len(vals) > 1:
        style = vals[1]
    if len(vals) > 2:
        weight = vals[2]

    match = font_regex.match(family)
    if match:
        family, point_size = match.groups()
        point_size = int(point_size)

    return Bunch.Bunch(family=family, point_size=point_size,
                       style=style, weight=weight)


def get_font(font_family, point_size):
    font_family = font_asst.resolve_alias(font_family, font_family)
    font_str = '%s %d' % (font_family, point_size)
    return font_info(font_str)


def load_font(font_name, font_file):
    # TODO!
    ## raise ValueError("Loading fonts dynamically is an unimplemented"
    ##                  " feature for pg back end")
    return font_name

# END
