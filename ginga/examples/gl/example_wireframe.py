#! /usr/bin/env python
#
# example_wireframe.py -- Example of a 3D plot with octahedron and wireframe
#
"""
Example of 3D plotting in Ginga

Plots an octahedron within a wireframe sphere.

Run with no parameters.  Scroll to zoom in/out, click and drag to orbit.

Requirements: Qt5, OpenGL, numpy
"""

import sys

import numpy as np

from ginga import toolkit
toolkit.use('qt5')

from ginga.gw import Widgets  # noqa
from ginga.qtw.ImageViewQt import CanvasView  # noqa
from ginga.canvas.CanvasObject import get_canvas_types  # noqa
from ginga.canvas import transform  # noqa
from ginga.misc import log  # noqa


class Viewer(object):

    def __init__(self, app):
        super(Viewer, self).__init__()
        self.logger = app.logger
        self.dc = get_canvas_types()

        self.top = app.make_window(title="Simple Ginga 3D Viewer")

        vw = CanvasView(self.logger, render='opengl')
        vw.ui_set_active(True)
        self.vw = vw

        # quick hack to get 'u' to invoke hidden camera mode
        bm = vw.get_bindmap()
        bm.mode_map['u'] = bm.mode_map['mode_camera']

        bd = vw.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.set_surface(vw)
        self.canvas = canvas
        # add canvas to view
        private_canvas = vw.get_canvas()
        private_canvas.add(canvas)

        # little hack because we don't have a way yet to ask for this
        # variation of back end through ginga.toolkit
        ww = Widgets.wrap(vw.get_widget())

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)
        vbox.add_widget(ww, stretch=1)

        hbox = Widgets.HBox()
        hbox.set_border_width(4)

        wquit = Widgets.Button("Quit")
        wquit.add_callback('activated', self.quit)
        hbox.add_widget(Widgets.Label(''), stretch=1)
        hbox.add_widget(wquit)

        vbox.add_widget(hbox)

        self.top.set_widget(vbox)

    def quit(self, w):
        self.top.delete()
        sys.exit(0)


def plot_octahedron(viewer, r):
    # octahedron
    A = [0.17770898, 0.72315927, 0.66742804]
    B = [-0.65327074, -0.4196453, 0.63018661]
    C = [0.65382635, 0.42081934, -0.62882604]
    D = [-0.17907021, -0.72084723, -0.66956189]
    E = [-0.73452809, 0.5495376, -0.39809158]
    F = [0.73451554, -0.55094017, 0.39617148]
    octo = [[E, A, B],
            [E, B, D],
            [E, D, C],
            [E, C, A],
            [F, A, B],
            [F, B, D],
            [F, D, C],
            [F, C, A],
            ]
    clrs = [('gray%d' % (i * 10 + 5)) for i in range(8)]
    for i, tri in enumerate(octo):
        new_tri = [np.asarray(pt) * r for pt in tri]
        viewer.canvas.add(viewer.dc.Polygon(new_tri, color='yellow',
                                            fill=True, fillcolor=clrs[i],
                                            fillalpha=0.4))


def get_wireframe(viewer, x, y, z, **kwargs):
    """Produce a compound object of paths implementing a wireframe.
    x, y, z are expected to be 2D arrays of points making up the mesh.
    """
    # TODO: something like this would make a great utility function
    # for ginga
    n, m = x.shape
    objs = []
    for i in range(n):
        pts = np.asarray([(x[i][j], y[i][j], z[i][j])
                          for j in range(m)])
        objs.append(viewer.dc.Path(pts, **kwargs))

    for j in range(m):
        pts = np.asarray([(x[i][j], y[i][j], z[i][j])
                          for i in range(n)])
        objs.append(viewer.dc.Path(pts, **kwargs))

    return viewer.dc.CompoundObject(*objs)


def plot_sphere(viewer, r):
    # sphere
    u = np.linspace(0, np.pi, 30)
    v = np.linspace(0, 2 * np.pi, 30)
    x = np.outer(np.sin(u), np.sin(v)) * r
    y = np.outer(np.sin(u), np.cos(v)) * r
    z = np.outer(np.cos(u), np.ones_like(v)) * r

    wf = get_wireframe(viewer, x, y, z, color='cyan', alpha=0.3)
    viewer.canvas.add(wf)


logger = log.get_logger('example', level=20, log_stderr=True)

app = Widgets.Application(logger)

v = Viewer(app)
v.top.resize(512, 512)
v.top.show()

# put viewer in camera mode
bm = v.vw.get_bindmap()
bm.set_mode('camera', mode_type='locked')

# toggle 3D view
bd = v.vw.get_bindings()
bd.kp_camera_toggle3d(v.vw, None, 0, 0)

r = 100
plot_octahedron(v, r)
plot_sphere(v, r)

app.mainloop()

# END
