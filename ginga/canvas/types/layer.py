#
# layers.py -- classes for special compound objects layered on
#                   ginga canvases.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.canvas.CanvasObject import (CanvasObjectBase,
                                       register_canvas_types)
from ginga import Mixins
from ginga.misc.log import get_logger

from ..CompoundMixin import CompoundMixin
from ..CanvasMixin import CanvasMixin
from ..DrawingMixin import DrawingMixin

__all__ = ['CompoundObject', 'Canvas', 'DrawingCanvas']


class CompoundObject(CompoundMixin, CanvasObjectBase):
    """Compound object on a ImageViewCanvas.
    Parameters are the child objects making up the compound object.
    Objects are drawn in the order listed. Example:

    .. code-block: Python

        CompoundObject(Point(x, y, radius, ...),
                       Circle(x, y, radius, ...))

    This makes a point inside a circle.
    """

    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
        ]

    def __init__(self, *objects, **kwdargs):
        CanvasObjectBase.__init__(self, **kwdargs)
        CompoundMixin.__init__(self)
        self.objects = list(objects)
        self.logger = get_logger('foo', log_stderr=True, level=10)

        self.kind = 'compound'
        self.editable = False


class Canvas(CanvasMixin, CompoundObject):
    """Class to handle canvas in Ginga."""
    @classmethod
    def get_params_metadata(cls):
        return [
            ## Param(name='coord', type=str, default='data',
            ##       valid=['data', 'wcs'],
            ##       description="Set type of coordinates"),
        ]

    def __init__(self, *objects, **kwdargs):
        CompoundObject.__init__(self, *objects, **kwdargs)
        CanvasMixin.__init__(self)

        self.kind = 'canvas'
        self.editable = False


class DrawingCanvas(Mixins.UIMixin, DrawingMixin, Canvas):
    """Drawing canvas."""
    def __init__(self, **kwdargs):
        Canvas.__init__(self, **kwdargs)
        DrawingMixin.__init__(self)
        Mixins.UIMixin.__init__(self)

        self.kind = 'drawingcanvas'
        self.editable = False


catalog = dict(compoundobject=CompoundObject, canvas=Canvas,
               drawingcanvas=DrawingCanvas)
register_canvas_types(catalog)

# END
