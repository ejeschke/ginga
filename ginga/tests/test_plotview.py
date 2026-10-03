#
# test_plotview.py -- drawing a plot that has no area to draw in
#
"""A widget can report a size of zero -- a web canvas does so until the page
has laid it out -- and a figure sized from that has no area.  matplotlib
does not refuse to draw it: the layout engine warns that "axes sizes
collapsed to zero", and the degenerate transforms it leaves behind make the
tick locator fail on a NaN ("cannot convert float NaN to integer"), once per
redraw, for as long as the widget stays that size.  None of it tells the
user anything, because there is nothing to look at until the real size
arrives -- so the viewer declines to draw until then.
"""

import logging
import threading

import numpy as np
import pytest

matplotlib = pytest.importorskip('matplotlib')
matplotlib.use('Agg')
from matplotlib.figure import Figure                      # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402

from ginga.plot.PlotView import PlotViewBase              # noqa: E402


def _viewer(wd_in=8.0, ht_in=6.0, dpi=100):
    """A PlotViewBase with just the attributes these methods touch.

    Built without __init__ on purpose: the real constructor makes a widget,
    which needs a live GUI session.
    """
    fig = Figure(figsize=(wd_in, ht_in), dpi=dpi, layout='constrained')
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot(np.arange(50), np.arange(50))
    ax.set_title('t')
    ax.set_xlabel('x')
    ax.set_ylabel('y')

    pv = PlotViewBase.__new__(PlotViewBase)
    pv.figure = fig
    pv.ax = ax
    pv.name = 'test'
    pv.logger = logging.getLogger('test_plotview')
    pv._resize_lock = threading.RLock()
    pv.time_last_resize = 0.0
    pv.made = []
    pv.make_callback = lambda name, *args: pv.made.append((name, args))
    return pv


# ------------------------------------------------------- the predicate --

def test_a_normal_figure_is_drawable():
    assert _viewer().has_drawable_area()


@pytest.mark.parametrize('wd_in,ht_in', [(0.001, 0.001),   # under a pixel
                                         (0.001, 6.0),     # no width
                                         (8.0, 0.001)])    # no height
def test_a_figure_smaller_than_a_pixel_is_not(wd_in, ht_in):
    pv = _viewer()
    pv.figure.set_size_inches(wd_in, ht_in)
    assert not pv.has_drawable_area()


def test_a_figure_with_a_broken_dpi_is_not():
    """dpi scales the transform the tick locator measures through; a
    non-finite one is what turns its arithmetic into NaN."""
    pv = _viewer()
    pv.figure.dpi = float('nan')
    assert not pv.has_drawable_area()


# ------------------------------------------------------------ the draw --

def test_redraw_skips_a_figure_with_no_area(capsys):
    pv = _viewer()
    pv.figure.set_size_inches(0.001, 0.001)
    drew = []
    pv.figure.canvas.draw = lambda: drew.append(True)

    pv.redraw_now()

    assert drew == [], "should not have drawn"
    assert capsys.readouterr().err == ''


def test_redraw_draws_once_there_is_room():
    pv = _viewer()
    drew = []
    pv.figure.canvas.draw = lambda: drew.append(True)

    pv.redraw_now()

    assert drew == [True]
    assert ('redraw', (0,)) in pv.made


def test_font_sizing_skips_a_figure_with_no_area():
    """Reading the tick labels runs the locator, which is one of the
    places the NaN surfaced."""
    pv = _viewer()
    pv.figure.set_size_inches(0.001, 0.001)
    redrawn = []
    pv.redraw = lambda *a, **k: redrawn.append(True)

    pv._set_variable_font_sizes()        # must not raise

    assert redrawn == []


# ---------------------------------------------------------- the resize --

@pytest.mark.parametrize('wd_px,ht_px', [(0, 0), (0, 600), (800, 0), (-5, 10)])
def test_a_degenerate_resize_is_ignored(wd_px, ht_px):
    """The widget reports 0 before it is laid out; adopting that is what
    makes the figure undrawable in the first place."""
    pv = _viewer()
    before = tuple(pv.figure.get_size_inches())

    pv.set_window_size(wd_px, ht_px)

    assert tuple(pv.figure.get_size_inches()) == before
    assert pv.made == [], "no configure callback for a size we refused"


def test_a_real_resize_is_applied():
    pv = _viewer()

    pv.set_window_size(800, 600)

    wd_in, ht_in = pv.figure.get_size_inches()
    assert (wd_in * pv.figure.dpi, ht_in * pv.figure.dpi) == (800, 600)
    assert pv.made == [('configure', (800, 600))]
