#
# MplHelp.py -- help classes for Matplotlib drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga import colors
from ginga.misc import Bunch, Callback
from ginga.fonts import font_asst

import matplotlib.textpath as textpath


class Pen(object):
    def __init__(self, color='black', linewidth=1, linestyle='solid'):
        self.color = color
        self.linewidth = linewidth
        if linestyle == 'dash':
            linestyle = 'dashdot'
        self.linestyle = linestyle


class Brush(object):
    def __init__(self, color='black', fill=False):
        self.color = color
        self.fill = fill


class Font(object):
    def __init__(self, fontname='sans', fontsize=12.0, color='black'):
        fontname = font_asst.resolve_alias(fontname, fontname)
        self.fontname = fontname
        self.fontsize = fontsize
        self.color = color

    def get_fontdict(self):
        fontdict = dict(color=self.color, family=self.fontname,
                        size=self.fontsize, transform=None)
        return fontdict


def load_font(font_name, font_file):
    # TODO!
    ## raise ValueError("Loading fonts dynamically is an unimplemented"
    ##                  " feature for matplotlib back end")
    return font_name


class MplContext(object):

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

    def update_fill(self, brush):
        if brush is None:
            self.kwdargs['fill'] = False
            return

        self.kwdargs['fill'] = True
        self.kwdargs['facecolor'] = brush.color

    def update_line(self, pen):
        self.kwdargs['color'] = pen.color
        self.kwdargs['linewidth'] = pen.linewidth
        self.kwdargs['linestyle'] = pen.linestyle

    def update_patch(self, pen, brush):
        self.update_fill(brush)

        if self.kwdargs['fill']:
            line_color_attr = 'facecolor'
            if 'facecolor' in self.kwdargs:
                line_color_attr = 'edgecolor'
        else:
            line_color_attr = 'color'

        self.kwdargs[line_color_attr] = pen.color
        self.kwdargs['linewidth'] = pen.linewidth
        self.kwdargs['linestyle'] = pen.linestyle

    def get_color(self, color, alpha):
        if isinstance(color, str) or isinstance(color, type(u"")):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGBA values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        return (r, g, b, alpha)

    def get_pen(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        color = self.get_color(color, alpha=alpha)
        return Pen(color=color, linewidth=linewidth, linestyle=linestyle)

    def get_brush(self, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Brush(color=color, fill=True)

    def get_font(self, name, size, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Font(fontname=name, fontsize=size, color=color)

    def text_extents(self, text, font):
        # This is not completely accurate because it depends a lot
        # on the renderer used, but that is complicated under Mpl
        t = textpath.TextPath((0, 0), text, size=font.fontsize,
                              prop=font.fontname)
        bb = t.get_extents()
        wd, ht = bb.width, bb.height
        return (wd, ht)


class Timer(Callback.Callbacks):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, duration=0.0, mplcanvas=None):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

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

        # Matplotlib timer set in milliseconds
        time_ms = int(duration * 1000.0)
        self._timer.interval = time_ms
        self._timer.start()

    def _redirect_cb(self):
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
