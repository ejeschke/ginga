"""Tests for viewers that render their own thumbnails.

An image viewer's thumbnail is made by the Thumbs plugin's thumb
generator, but a plot or a table is not something that generator can
draw.  Those used to be handled by screenshotting the viewer's widget,
which only works on some backends, only while the widget is realized and
on screen, and so only while the object happens to be the one the viewer
is showing.  Each viewer now renders its own thumbnail from its data
instead; these tests pin down that contract.
"""

import numpy as np
import pytest

from ginga.misc import log
from ginga.util.viewer import ViewerBase
from ginga.table import AstroTable
from ginga.table.TableView import (TableViewBase, draw_table_thumbnail,
                                   table_preview)

try:
    from astropy.table import Table
    HAVE_ASTROPY = True
except ImportError:
    HAVE_ASTROPY = False

try:
    from matplotlib.figure import Figure
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False


def mk_logger():
    return log.get_logger("test_viewer_thumbs", null=True)


def mk_table(n_rows=50, n_cols=4, prefix='col', seed=0):
    rng = np.random.default_rng(seed)
    dct = {}
    for j in range(n_cols):
        name = '%s%d' % (prefix, j)
        if j % 3 == 0:
            dct[name] = np.arange(n_rows) + j
        elif j % 3 == 1:
            dct[name] = rng.random(n_rows) * 10.0
        else:
            dct[name] = np.array(['src_%04d' % i for i in range(n_rows)])
    tbl = AstroTable.AstroTable(logger=mk_logger())
    tbl.set_data(Table(dct))
    return tbl


# -------------------------------------------------------------- protocol

def test_a_plain_viewer_declines_to_draw_a_thumbnail():
    """The default is "I can't" -- the caller shows a placeholder."""
    vwr = ViewerBase(logger=mk_logger())
    assert vwr.get_thumbnail_array(object(), (64, 64)) is None


# ----------------------------------------------------------------- table

@pytest.mark.skipif(not HAVE_ASTROPY, reason="astropy is required")
class TestTableThumbnail:

    def test_it_draws_something_the_right_shape(self):
        arr = draw_table_thumbnail(mk_table(), (240, 240))

        assert arr.shape == (240, 240, 3)
        assert arr.dtype == np.uint8
        assert arr.min() != arr.max(), "nothing was drawn"

    @pytest.mark.parametrize('size', [(240, 240), (120, 120), (240, 150),
                                      (150, 240), (32, 32), (1, 1)])
    def test_it_stays_inside_the_box(self, size):
        arr = draw_table_thumbnail(mk_table(), size)

        wd, ht = size
        # a minimum is enforced, below which there is no point drawing
        assert arr.shape[1] <= max(wd, 24)
        assert arr.shape[0] <= max(ht, 24)

    def test_different_tables_look_different(self):
        """The whole point over a generic icon: which table is this?"""
        a = draw_table_thumbnail(mk_table(50, 4, seed=1), (240, 240))
        b = draw_table_thumbnail(mk_table(50, 4, seed=2), (240, 240))
        c = draw_table_thumbnail(mk_table(50, 4, prefix='flux'), (240, 240))

        assert not np.array_equal(a, b), "different values drew the same"
        assert not np.array_equal(a, c), "different columns drew the same"

    def test_tables_differing_only_in_size_look_different(self):
        """Only a corner is drawn, so the shape has to be shown too."""
        a = draw_table_thumbnail(mk_table(10, 3), (240, 240))
        b = draw_table_thumbnail(mk_table(100000, 3), (240, 240))

        assert not np.array_equal(a, b)

    def test_the_same_table_draws_the_same_way_twice(self):
        tbl = mk_table()
        assert np.array_equal(draw_table_thumbnail(tbl, (240, 240)),
                              draw_table_thumbnail(tbl, (240, 240)))

    @pytest.mark.parametrize('n_rows,n_cols', [(0, 3), (1, 1), (3, 40)])
    def test_awkward_tables_still_draw(self, n_rows, n_cols):
        arr = draw_table_thumbnail(mk_table(n_rows, n_cols), (240, 240))
        assert arr.shape == (240, 240, 3)

    def test_a_table_it_cannot_read_does_not_raise(self):
        """A thumbnail is never worth raising over."""

        class Hostile:
            def get_data(self):
                raise ValueError("no data for you")

        for tbl in (None, Hostile(), object()):
            arr = draw_table_thumbnail(tbl, (240, 240))
            assert arr.shape == (240, 240, 3)

    def test_preview_reports_the_full_shape_not_the_drawn_corner(self):
        tbl = mk_table(5000, 12)
        cols, cells, n_rows, n_cols = table_preview(tbl, 10, 3)

        assert len(cols) == 3 and len(cells) == 10      # what we drew
        assert (n_rows, n_cols) == (5000, 12)           # what is there

    def test_the_viewer_draws_any_table_not_only_its_current_one(self):
        """The case the widget screenshot could never handle."""
        vwr = TableViewBase(logger=mk_logger())
        showing, other = mk_table(seed=1), mk_table(seed=2)
        vwr.set_table(showing)

        arr = vwr.get_thumbnail_array(other, (240, 240))

        assert arr is not None
        assert np.array_equal(arr, draw_table_thumbnail(other, (240, 240)))
        assert not np.array_equal(arr, vwr.get_thumbnail_array(showing,
                                                               (240, 240)))

    def test_the_viewer_declines_a_non_table(self):
        vwr = TableViewBase(logger=mk_logger())
        assert vwr.get_thumbnail_array(object(), (240, 240)) is None
        assert vwr.get_thumbnail_array(None, (240, 240)) is None


# ------------------------------------------------------------------ plot

class FakePlotViewer:
    """Enough of PlotViewBase to drive its figure rendering.

    PlotViewBase.__init__ builds a PlotWidget, so a real one cannot be
    constructed without a toolkit; the rendering under test does not need
    one, which is the entire point of the change.
    """

    def __init__(self, figure, dataobj=None):
        self.figure = figure
        self.dataobj = dataobj
        self.logger = mk_logger()

    def get_figure(self):
        return self.figure

    def get_dataobj(self):
        return self.dataobj

    def _render_figure(self, size=None):
        from ginga.plot.PlotView import PlotViewBase
        return PlotViewBase._render_figure(self, size=size)


@pytest.mark.skipif(not HAVE_MPL, reason="matplotlib is required")
class TestPlotThumbnail:

    def _render(self, shim, **kwargs):
        from ginga.plot.PlotView import PlotViewBase
        return PlotViewBase._render_figure(shim, **kwargs)

    def mk_figure(self, seed=0):
        fig = Figure(figsize=(4.0, 3.0), dpi=100)
        ax = fig.add_subplot(111)
        rng = np.random.default_rng(seed)
        ax.plot(np.arange(50), rng.random(50))
        return fig

    def test_it_renders_without_any_widget(self):
        """No toolkit, no canvas, nothing on screen."""
        arr = self._render(FakePlotViewer(self.mk_figure()))

        assert arr.ndim == 3 and arr.shape[2] == 3
        assert arr.dtype == np.uint8
        assert arr.min() != arr.max(), "nothing was drawn"

    def test_it_fits_the_requested_box_keeping_aspect(self):
        fig = self.mk_figure()          # 4:3
        arr = self._render(FakePlotViewer(fig), size=(240, 240))

        ht, wd = arr.shape[:2]
        assert wd <= 240 and ht <= 240
        assert abs((wd / ht) - (4.0 / 3.0)) < 0.05

    def test_rendering_leaves_the_live_figure_alone(self):
        """savefig() borrows the figure; it must give it back."""
        fig = self.mk_figure()
        before = (fig.get_dpi(), tuple(fig.get_size_inches()), fig.canvas)

        self._render(FakePlotViewer(fig), size=(64, 64))

        assert (fig.get_dpi(), tuple(fig.get_size_inches()),
                fig.canvas) == before

    def test_a_figure_with_no_area_renders_nothing(self):
        fig = Figure(figsize=(0, 0), dpi=100)
        assert self._render(FakePlotViewer(fig), size=(240, 240)) is None

    def test_it_only_draws_the_plot_it_is_showing(self):
        from ginga.plot.PlotView import PlotViewBase

        showing, other = object(), object()
        shim = FakePlotViewer(self.mk_figure(), dataobj=showing)

        assert PlotViewBase.get_thumbnail_array(shim, showing,
                                                (240, 240)) is not None
        # the figure holds the current plot, so there is nothing to draw
        # for any other one
        assert PlotViewBase.get_thumbnail_array(shim, other,
                                                (240, 240)) is None


# ---------------------------------------------- the vestigial get_thumbnail

@pytest.mark.parametrize('mk_obj, name', [
    (lambda: AstroTable.AstroTable(logger=mk_logger()), 'AstroTable'),
    pytest.param(
        lambda: __import__('ginga.plot.Plotable', fromlist=['Plotable']
                           ).Plotable(logger=mk_logger()),
        'Plotable',
        marks=pytest.mark.skipif(not HAVE_MPL,
                                 reason="matplotlib is required")),
])
def test_the_old_get_thumbnail_warns_that_it_is_going(mk_obj, name):
    """It returns an identity matrix -- a diagonal line, not a thumbnail."""
    obj = mk_obj()

    with pytest.warns(PendingDeprecationWarning, match='get_thumbnail'):
        arr = obj.get_thumbnail(8)

    # behaviour is unchanged for anyone still calling it
    assert np.array_equal(arr, np.eye(8))


if __name__ == '__main__':
    pytest.main([__file__])
