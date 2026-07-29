"""Tests for ginga.canvas.stroke -- the renderer-agnostic wide/dashed line
geometry helpers (used by the OpenGL and Vulkan renderers)."""
import numpy as np

from ginga.canvas.stroke import stroke_polyline, dash_polylines, dash_pattern


def test_stroke_polyline_geometry():
    """The wide-line expander produces filled triangles spanning the width."""
    # horizontal segment (10,20)->(40,20), width 6 -> y in [17, 23]
    tris = stroke_polyline([(10, 20), (40, 20)], 6.0, closed=False)
    assert tris.ndim == 2 and tris.shape[1] == 2
    assert len(tris) % 3 == 0 and len(tris) >= 6      # >= 2 triangles
    ys = tris[:, 1]
    assert abs(ys.min() - 17.0) < 1e-4
    assert abs(ys.max() - 23.0) < 1e-4
    xs = tris[:, 0]
    assert xs.min() >= 10.0 - 1e-4 and xs.max() <= 40.0 + 1e-4


def test_stroke_closed_has_more_geometry():
    """A closed loop adds join discs at every vertex, so it has more geometry
    than the equivalent open polyline."""
    pts = [(0, 0), (10, 0), (10, 10)]
    open_n = len(stroke_polyline(pts, 4.0, closed=False))
    closed_n = len(stroke_polyline(pts, 4.0, closed=True))
    assert closed_n > open_n


def test_stroke_degenerate():
    assert len(stroke_polyline([(1, 1)], 4.0, closed=False)) == 0
    assert len(stroke_polyline([(1, 1), (1, 1)], 4.0, closed=False)) == 0


def test_dash_polylines_gaps():
    """A dashed line is split into several 'on' runs whose total length is
    less than the full line (gaps removed)."""
    runs = dash_polylines([(0, 0), (60, 0)], dash_pattern(1.0), closed=False)
    assert len(runs) >= 3
    on_len = sum(float(np.hypot(*(r[-1] - r[0]))) for r in runs)
    assert 0 < on_len < 60


def test_dash_pattern_scales_with_width():
    thin = dash_pattern(1.0)
    thick = dash_pattern(10.0)
    assert thick[0] > thin[0] and thick[1] > thin[1]
