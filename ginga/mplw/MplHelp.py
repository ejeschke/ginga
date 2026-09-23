#
# MplHelp.py -- help classes for Matplotlib drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import time

import numpy as np

from ginga.misc import Bunch, Callback
from ginga.fonts import font_asst

import matplotlib.textpath as textpath
from matplotlib.font_manager import FontProperties


def get_font(font_spec, font_size):
    """Function to obtain a native font for the matplotlib backend.

    Parameters
    ----------
    font_spec : str or `~ginga.fonts.font_asst.Font`
        The desired font

    font_size : int
        The point size requested for the given font

    Returns
    -------
    font : matplotlib font
        The desired font in native backend form
    """
    key = ('mpl', font_spec, font_size)
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

    # font not loaded? try and load it
    font_name = None
    if font_asst.have_loadable_font(font_tup):
        try:
            font_name = load_font(font_tup, font_size)

        except Exception:
            pass

    if font_name is None:
        # try to create the font from the family name directly, plus in any
        # other substitute fonts
        families = font_asst.get_substitutes(font_tup.family)
        for family in families:
            font_tup2 = font_asst.Font(family=family, style=font_tup.style,
                                       weight=font_tup.weight)
            if font_asst.have_loadable_font(font_tup2):
                try:
                    font_name = load_font(font_tup2, font_size)
                    break
                except Exception:
                    continue

    if font_name is None:
        # Nothing registered for this family could be loaded.  Rather than
        # raising -- which leaves the caller with no text drawn at all --
        # fall back to a font we do have, keeping the generic class
        # (serif / sans-serif / monospace) and the requested style and
        # weight as closely as we can.
        font_name = get_fallback_font(font_tup, font_size)

    font_asst.add_cache(key, font_name)
    if isinstance(font_spec, str):
        # also store the font under a secondary key
        key2 = ('mpl', font_tup, font_size)
        font_asst.add_cache(key2, font_name)
    return font_name


def get_generic_family(family):
    """Map a font family name onto the CSS generic class it belongs to.

    Matplotlib always resolves the generic keywords ('serif', 'sans-serif',
    'monospace', ...) through its rcParams, so they make a dependable last
    resort.  Returns 'sans-serif' for anything unrecognized.
    """
    fam = family.lower()
    if fam in font_asst.css_generic_families:
        return fam
    # a registered substitute may name a generic class directly
    for sub in font_asst.get_substitutes(fam):
        if sub.lower() in font_asst.css_generic_families:
            return sub.lower()
    # NOTE: 'sans' is tested before 'serif' -- "sans serif" contains both
    for keywords, generic in ((('sans',), 'sans-serif'),
                              (('mono', 'courier', 'console', 'typewriter'),
                               'monospace'),
                              (('serif', 'times', 'georgia', 'roman'),
                               'serif'),
                              (('cursive', 'script'), 'cursive'),
                              (('fantasy', 'decorative'), 'fantasy')):
        if any(kw in fam for kw in keywords):
            return generic
    return 'sans-serif'


def get_fallback_font(font_tup, font_size):
    """Return the name of a usable font as close as possible to `font_tup`.

    Prefers one of our own loadable fonts in the same generic class, ranked
    by how well its style and weight match the request; failing that, falls
    back to the generic class name itself, which matplotlib resolves to
    whatever it has configured for that class.
    """
    generic = get_generic_family(font_tup.family)

    def rank(ft):
        # exact style first, then exact weight, then a stable name order
        return (ft.style != font_tup.style,
                ft.weight != font_tup.weight,
                ft.family)

    candidates = [ft for ft in font_asst.get_loadable_fonts()
                  if get_generic_family(ft.family) == generic]
    for ft in sorted(candidates, key=rank):
        try:
            return load_font(ft, font_size)
        except Exception:
            continue

    return generic


def load_font(font_tup, font_size):
    from matplotlib import font_manager
    # may raise an exception
    info = font_asst.get_font_info(font_tup)
    font_manager.fontManager.addfont(info.font_path)
    # NOTE: the registry's Bunch carries the family under 'name' (see
    # font_asst.add_loadable_font); there is no 'family' attribute
    font_name = info.name
    return font_name


class MplContext:

    def __init__(self, axes):
        self.axes = axes
        self.kwdargs = dict()
        self.stack = []

    def set_canvas(self, axes):
        self.axes = axes

    def init(self, **kwdargs):
        self.kwdargs = dict()
        self.kwdargs.update(kwdargs)

    def set(self, **kwdargs):
        self.kwdargs.update(kwdargs)

    def push(self, allow=[]):
        self.stack.append(self.kwdargs.copy())
        d = {name: self.kwdargs[name]
             for name in allow if name in self.kwdargs}
        self.kwdargs = d

    def pop(self):
        self.kwdargs = self.stack.pop()

    def update_fill(self, fill):
        if fill is None:
            self.kwdargs['fill'] = False
            return

        self.kwdargs['fill'] = True
        self.kwdargs['facecolor'] = fill._color_4tup

    def update_line(self, line):
        if line is not None:
            self.kwdargs['color'] = line._color_4tup
            self.kwdargs['linewidth'] = line.linewidth
            style = 'dashdot' if line.linestyle == 'dash' else 'solid'
            self.kwdargs['linestyle'] = style

    def update_patch(self, line, fill):
        self.update_fill(fill)

        if self.kwdargs['fill']:
            line_color_attr = 'facecolor'
            if 'facecolor' in self.kwdargs:
                line_color_attr = 'edgecolor'
        else:
            line_color_attr = 'color'

        if line is not None:
            self.kwdargs[line_color_attr] = line._color_4tup
            self.kwdargs['linewidth'] = line.linewidth
            style = 'dashdot' if line.linestyle == 'dash' else 'solid'
            self.kwdargs['linestyle'] = style

    def get_fontdict(self, font, fill):
        _font = get_font(font.fontname, font.fontsize)
        fontdict = dict(color=fill._color_4tup, family=_font,
                        size=font.fontsize, transform=None)
        return fontdict

    def text_extents(self, text, font):
        wd, ascent, descent = self.text_metrics(text, font)
        return wd, ascent + descent

    def text_metrics(self, text, font):
        x0, y0, x1, y1 = self.text_ink_bbox(text, font)
        return x1 - x0, max(0, -y0), max(0, y1)

    def text_ink_bbox(self, text, font):
        # This is not completely accurate because it depends a lot
        # on the renderer used, but that is complicated under Mpl.
        # TextPath's origin is the baseline and its y runs *up*, so the
        # extents are negated to report y downward (screen orientation).
        # NOTE: measure with the *resolved* font (what get_font() found for
        # this family), not the requested name, or the metrics describe a
        # different face than the one drawn.  The family goes in as a list:
        # a bare string is parsed as a fontconfig pattern, which chokes on
        # the hyphen in 'sans-serif'.
        prop = FontProperties(family=[get_font(font.fontname, font.fontsize)],
                              size=font.fontsize)
        t = textpath.TextPath((0, 0), text, size=font.fontsize, prop=prop)
        bb = t.get_extents()
        # TextPath measures in points; the drawing happens in device pixels,
        # so scale by the figure's dpi or the box drawn around the text comes
        # out dpi/72 too small
        sc = self.get_dpi() / 72.0
        return (int(np.floor(bb.x0 * sc)), int(np.floor(-bb.y1 * sc)),
                int(np.ceil(bb.x1 * sc)), int(np.ceil(-bb.y0 * sc)))

    def get_dpi(self):
        axes = getattr(self, 'axes', None)
        figure = getattr(axes, 'figure', None)
        return float(getattr(figure, 'dpi', 72.0))


class Timer(Callback.Callbacks):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, duration=0.0, mplcanvas=None):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()
        self.deadline = None
        self.start_time = 0.0
        self.end_time = 0.0

        self._timer = mplcanvas.new_timer()
        self._timer.single_shot = True
        self._timer.add_callback(self._redirect_cb)

        for name in ('expired', 'canceled'):
            self.enable_callback(name)

    def start(self, duration=None):
        """Start the timer.  If `duration` is not None, it should
        specify the time to expiration in seconds.
        """
        if duration is None:
            duration = self.duration

        self.set(duration)

    def set(self, duration):

        self.stop()

        self.start_time = time.time()
        self.deadline = self.start_time + duration
        self.end_time = self.deadline
        # Matplotlib timer set in milliseconds
        time_ms = int(duration * 1000.0)
        self._timer.interval = time_ms
        self._timer.start()

    def _redirect_cb(self):
        self.make_callback('expired')

    def is_set(self):
        return self.deadline is not None

    def cond_set(self, time_sec):
        if not self.is_set():
            # TODO: probably a race condition here
            self.set(time_sec)

    def elapsed_time(self):
        return time.time() - self.start_time

    def time_left(self):
        return max(0.0, self.time_end - time.time())

    def get_deadline(self):
        return self.time_end

    def expire(self):
        """This method is called externally to expire the timer."""
        self.stop()
        self.make_callback('expired')

    def stop(self):
        try:
            self._timer.stop()
        except Exception:
            pass

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        self.stop()
        self.make_callback('canceled')

    clear = cancel

# END
