"""
Tests of Ginga canvas objects.

"""
import pytest
import logging

import numpy as np

from ginga.pilw.ImageViewPil import CanvasView
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.AstroImage import AstroImage


class TestCanvas(object):

    def setup_class(self):
        self.logger = logging.getLogger("TestCanvas")
        self.viewer = CanvasView(logger=self.logger)
        self.dc = get_canvas_types()
        self.canvas = self.dc.DrawingCanvas()
        # NOTE: canvas needs to be added to a viewer otherwise lots
        # of operations do not work!
        # add our canvas to the viewer's default canvas
        self.viewer.get_canvas().add(self.canvas)

    def test_add_to_canvas(self):
        """Test adding an object to a canvas."""
        o = self.dc.Line(10, 10, -200, -300)
        self.canvas.add(o)
        assert o in self.canvas

    def test_delete_from_canvas(self):
        """Test deleting an object from a canvas."""
        o = self.dc.Line(10, 10, -200, -300)
        self.canvas.add(o)
        assert o in self.canvas
        self.canvas.delete_object(o)
        assert o not in self.canvas

    def test_delete_from_empty_canvas(self):
        """Test deleting an object that does not exist on a canvas."""
        o = self.dc.Line(10, 10, -200, -300)
        with pytest.raises(ValueError) as e:
            self.canvas.delete_object(o)

    def test_clear_canvas(self):
        """Test clearing a canvas."""
        o = self.dc.Line(10, 10, -200, -300)
        self.canvas.add(o)
        o2 = self.dc.Line(-10, -10, 200, 300)
        self.canvas.add(o2)
        self.canvas.delete_all_objects()
        assert o not in self.canvas
        assert o2 not in self.canvas

    def test_copy_simple(self):
        """Test copying a simple object on a canvas."""
        r = self.dc.Rectangle(10, 20, 110, 210)
        self.canvas.add(r)
        r2 = r.copy()
        assert isinstance(r2, self.dc.Rectangle)
        assert r2 is not r

    def test_copy_compound(self):
        """Test copying a compound object on a canvas."""
        a = self.dc.Annulus(100, 200, 10, width=5, atype='circle')
        self.canvas.add(a)
        a2 = a.copy()
        assert isinstance(a2, self.dc.Annulus)
        assert a2 is not a
        # check that children are copied as well, and not shared
        for o1, o2 in zip(a.get_objects(), a2.get_objects()):
            assert o1 is not o2

    def test_move_delta_pt(self):
        """Test moving an object by a delta."""
        o = self.dc.Box(50, 60, 100, 200)
        self.canvas.add(o)
        assert tuple(o.get_center_pt()) == (50, 60)
        o.move_delta_pt((-10, 15))
        assert tuple(o.get_center_pt()) == (40, 75)

    def _setup_color_test(self, obj):
        img = AstroImage(data_np=np.zeros((100, 100), dtype=int))
        self.viewer.set_image(img)
        self.canvas.add(obj)
        mask = img.get_shape_mask(obj)
        data = img.get_data()
        data[mask] = 1
        return np.sum(data)

    def test_color_object_circle(self):
        """Test coloring a circle."""
        res = self._setup_color_test(self.dc.Circle(49.5, 49.5, 12.0))
        assert res == 448

    def test_color_object_box(self):
        """Test coloring a box."""
        res = self._setup_color_test(self.dc.Box(49.5, 49.5, 12.0, 14.0))
        assert res == 672

    def test_color_object_ellipse(self):
        """Test coloring an ellipse."""
        res = self._setup_color_test(self.dc.Ellipse(49.5, 49.5, 12.0, 30.0))
        assert res == 1136

    def test_color_object_line(self):
        """Test coloring a line."""
        res = self._setup_color_test(self.dc.Line(10.0, 10.0, 88.0, 63.0))
        assert res == 196

    def _setup_cutout_test(self, obj):
        img = AstroImage(data_np=np.zeros((100, 100), dtype=int))
        self.viewer.set_image(img)
        self.canvas.add(obj)
        data = img.cutout_shape(obj)
        return data

    def test_cutout_object_circle(self):
        """Test cutting out a circle."""
        data = self._setup_cutout_test(self.dc.Circle(49.5, 49.5, 12.0))
        assert data.shape == (25, 25)
        assert np.ma.count_masked(data) == 177

    def test_cutout_object_box(self):
        """Test cutting out a box."""
        data = self._setup_cutout_test(self.dc.Box(49.5, 49.5, 12.0, 14.0))
        assert data.shape == (29, 25)
        assert np.ma.count_masked(data) == 53

    def test_cutout_object_ellipse(self):
        """Test cutting out an ellipse."""
        data = self._setup_cutout_test(self.dc.Ellipse(49.5, 49.5, 12.0, 30.0))
        assert data.shape == (61, 25)
        assert np.ma.count_masked(data) == 389
