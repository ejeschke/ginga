#
# PgHelp.py -- web application threading help routines.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import binascii
from io import BytesIO

from PIL import Image

from ginga.fonts import font_asst
from ginga.util import icon_helper


def get_image_src_from_buffer(img_buf, imgtype='png'):
    if not isinstance(img_buf, bytes):
        img_buf = img_buf.encode('latin1')
    img_string = binascii.b2a_base64(img_buf)
    if isinstance(img_string, bytes):
        img_string = img_string.decode("utf-8")
    return f'data:image/{imgtype};base64,' + img_string


def get_icon(iconpath, size=None, format='svg'):

    if size is not None:
        wd, ht = size
    else:
        wd, ht = 24, 24

    if iconpath.lower().endswith('.svg'):
        if format.startswith('svg'):
            # TEMP?
            # Scalable Vector Graphics should be scalable on the browser side
            with open(iconpath, 'rb') as icon_f:
                svg_buf = icon_f.read()
                icon_uri = get_image_src_from_buffer(svg_buf, imgtype='svg+xml')
                return icon_uri

        if format == 'png':
            img_buf = icon_helper.load_svg_to_pngbuf(iconpath,
                                                     wd_px=wd, ht_px=ht)
            icon_uri = get_image_src_from_buffer(img_buf.getvalue(),
                                                 imgtype=format)
            return icon_uri

    # other types (raster images: png, gif, jpg, ...).
    if size is None:
        # no resize requested -- pass the original bytes straight through as
        # a data URI (already a browser-renderable format).
        ext = os.path.splitext(iconpath)[1].lower().lstrip('.') or 'png'
        imgtype = 'jpeg' if ext in ('jpg', 'jpeg') else ext
        with open(iconpath, 'rb') as icon_f:
            buf = icon_f.read()
        return get_image_src_from_buffer(buf, imgtype=imgtype)

    # resize to the requested (wd, ht).  Convert to RGBA first: resizing a
    # palette ('P') image and re-saving as 'P' can drop the transparent
    # color (rendering the icon blank), so work in RGBA to keep transparency.
    image = Image.open(iconpath).convert('RGBA')
    image = image.resize((wd, ht))
    img_buf = BytesIO()
    image.save(img_buf, format='PNG')
    return get_image_src_from_buffer(img_buf.getvalue(), imgtype='png')


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


def get_font(font_spec, font_size):
    """Function to obtain a font for the Pg backend.

    Parameters
    ----------
    font_spec : str or `~ginga.fonts.font_asst.Font`
        The desired font

    font_size : int
        The point size requested for the given font

    Returns
    -------
    font : dict
        The desired font information in native backend form
    """
    key = ('pg', font_spec, font_size)
    try:
        return font_asst.get_cache(key)

    except KeyError:
        pass

    if isinstance(font_spec, str):
        font_tup = font_asst.parse_font(font_spec)
    elif isinstance(font_spec, font_asst.Font):
        font_tup = font_spec
    else:
        raise ValueError("not a valid font spec: {}".format(str(font_spec)))

    font_dct = font_tup._asdict()
    # emit a CSS font-family fallback list (e.g. '"ubuntu mono",
    # monospace') rather than a single family, so the browser can fall
    # back gracefully when the preferred face isn't available
    font_dct['family'] = font_asst.get_css_family_list(font_tup.family)
    font_dct['size'] = font_size
    # cache this dict for faster lookups hence
    font_asst.add_cache(key, font_dct)
    if isinstance(font_spec, str):
        # also store the font under a secondary key
        key2 = ('pg', font_tup, font_size)
        font_asst.add_cache(key2, font_dct)

    return font_dct


# END
