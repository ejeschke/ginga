#
# icon_helper.py -- helper module for loading icons
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from io import BytesIO

have_cairosvg = False
try:
    import cairosvg
    have_cairosvg = True

except ImportError:
    pass


def load_svg_to_pngbuf(filepath, wd_px=None, ht_px=None, out=None):
    """Load an SVG icon into a PNG image in a buffer.

    Parameters
    ----------
    filepath : str
        Path to the SVG icon file

    wd_px : int or None (optional, default: None)
        Width to constrain the output in pixels

    ht_px : int or None (optional, default: None)
        Height to constrain the output in pixels

    out : io.BytesIO object or None (optional, default: None)
        The buffer object to use for the output

    Returns
    -------
    out : io.BytesIO object
        The PNG image in a Python buffered I/O object
    """
    if not have_cairosvg:
        raise RuntimeError("Please install module 'cairosvg' to use this function")

    if out is None:
        out = BytesIO()
    kwargs = dict(url=filepath, write_to=out)
    if wd_px is not None:
        kwargs['output_width'] = wd_px
    if ht_px is not None:
        kwargs['output_height'] = ht_px

    cairosvg.svg2png(**kwargs)
    return out
