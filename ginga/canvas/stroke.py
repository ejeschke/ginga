#
# stroke.py -- expand polylines into filled triangles (wide/dashed lines)
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Geometry helpers for drawing wide and dashed lines as filled triangles.

GPU renderers (OpenGL, Vulkan) cannot rely on ``lineWidth > 1`` or line
stippling, so wide/dashed lines are expanded into triangle geometry.  These
functions are pure numpy (renderer-agnostic): the caller supplies points in
whatever coordinate space it draws in, and the width/pattern in the same
units, and draws the returned vertices as a triangle list / line strips.
"""
import numpy as np


def dash_pattern(linewidth):
    """Return an ``[on, off]`` dash pattern scaled to the line width."""
    lw = max(1.0, float(linewidth))
    return [max(4.0, 3.0 * lw), max(3.0, 2.0 * lw)]


def stroke_polyline(pts, width, closed, join_segments=8):
    """Expand a polyline into filled triangles approximating a stroke of the
    given ``width``.  Each segment becomes a rectangle (2 triangles); a small
    disc is added at every join (and at all vertices when ``closed``) to fill
    the corners with round joins.  Returns an ``(N, 2)`` float32 array of
    triangle-list vertices.

    NOTE: overlapping triangles at joins double-blend a translucent line, so
    round joins are only exact for opaque lines.
    """
    pts = np.ascontiguousarray(pts, dtype=np.float32)[:, :2]
    n = len(pts)
    if n < 2 or width <= 0:
        return np.zeros((0, 2), dtype=np.float32)
    hw = 0.5 * float(width)

    # --- segment rectangles (vectorized) ---
    m = n if closed else n - 1
    a = pts[np.arange(m)]
    b = pts[(np.arange(m) + 1) % n]
    d = b - a
    length = np.hypot(d[:, 0], d[:, 1])
    ok = length > 1e-6
    a, b, d, length = a[ok], b[ok], d[ok], length[ok]
    parts = []
    if len(a) > 0:
        u = d / length[:, None]
        nrm = np.stack([-u[:, 1], u[:, 0]], axis=1) * hw     # perpendicular
        a0, a1 = a + nrm, a - nrm
        b0, b1 = b + nrm, b - nrm
        # two triangles per segment: (a0, a1, b1) and (a0, b1, b0)
        seg = np.stack([a0, a1, b1, a0, b1, b0], axis=1).reshape(-1, 2)
        parts.append(seg)

    # --- round joins (disc at each interior vertex; all vertices if closed) ---
    join_idx = np.arange(n) if closed else np.arange(1, n - 1)
    if len(join_idx) > 0 and join_segments >= 3:
        ang = np.linspace(0.0, 2.0 * np.pi, join_segments, endpoint=False)
        ring_off = np.stack([np.cos(ang), np.sin(ang)], axis=1) * hw  # (s,2)
        centers = pts[join_idx]                                       # (j,2)
        ring = centers[:, None, :] + ring_off[None, :, :]            # (j,s,2)
        r1 = np.roll(ring, -1, axis=1)
        c = np.broadcast_to(centers[:, None, :], ring.shape)
        disc = np.stack([c, ring, r1], axis=2).reshape(-1, 2)
        parts.append(disc)

    if len(parts) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    return np.ascontiguousarray(np.concatenate(parts, axis=0), dtype=np.float32)


def dash_polylines(pts, pattern, closed=False):
    """Split a polyline into the list of "on" sub-polylines for a dash
    ``pattern`` (``[on, off, ...]`` lengths).  Each returned item is an
    ``(M, 2)`` float32 array; solid runs that cross vertices stay connected.
    """
    pts = np.ascontiguousarray(pts, dtype=np.float32)[:, :2]
    if closed and len(pts) >= 2:
        pts = np.vstack([pts, pts[:1]])
    n = len(pts)
    if n < 2:
        return []
    npat = len(pattern)
    idx, rem, on = 0, float(pattern[0]), True
    runs, cur = [], []
    if on:
        cur = [tuple(pts[0])]
    for i in range(n - 1):
        a, b = pts[i], pts[i + 1]
        d = b - a
        seglen = float(np.hypot(d[0], d[1]))
        if seglen < 1e-9:
            continue
        dirv = d / seglen
        pos = 0.0
        while pos < seglen - 1e-9:
            step = min(rem, seglen - pos)
            pos += step
            rem -= step
            p = a + dirv * pos
            if on:
                cur.append(tuple(p))
            if rem <= 1e-9:
                if on and len(cur) >= 2:
                    runs.append(np.asarray(cur, dtype=np.float32))
                idx = (idx + 1) % npat
                rem = float(pattern[idx])
                on = not on
                cur = [tuple(p)] if on else []
    if on and len(cur) >= 2:
        runs.append(np.asarray(cur, dtype=np.float32))
    return runs
