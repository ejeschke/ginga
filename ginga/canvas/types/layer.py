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
    """Compound object on a Ginga canvas.
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


class ConstructedCanvas(DrawingMixin, Canvas):
    """Constructed canvas from a list of specifications.

    Parameters are specifications of child objects, where each specification
    is a map specifying 'type' and (optionally) 'args' and 'kwargs'.
    If present, 'args' is a sequence of arguments and 'kwargs' is a map
    of keyword arguments to provide to the constructor of the child.

    Example:

    .. code-block: Python

        ConstructedCanvas([dict(type='point', args=(x, y, radius),
                                kwargs=dict(color='red')),
                           dict(type='circle', args=(x, y, radius),
                                kwargs=dict(color='yellow'))])

    This makes a point inside a circle.
    """
    def __init__(self, spec_list, **kwdargs):
        Canvas.__init__(self, **kwdargs)
        DrawingMixin.__init__(self)
        self.objects = self.build_objects(spec_list)

        self.kind = 'constructed'
        self.editable = False

    def build_objects(self, spec_list):
        return [self.build_object(spec) for spec in spec_list]

    def build_object(self, spec):
        ctype = spec.get('type', None)
        if ctype is None:
            raise ValueError("Item specification needs a 'type' designator: %s" % (
                str(spec)))

        # TODO: we need to be a subclass of DrawingMixin in order to get
        # access to the get_draw_class() method.  Otherwise we could just
        # be a subclass of CompoundObject. See if this can be fixed.
        draw_class = self.get_draw_class(ctype)

        args = spec.get('args', [])
        kwargs = spec.get('kwargs', {})

        if isinstance(draw_class, CompoundObject):
            # special case for compound objects: need to have actual objects
            # in constructor args, not specifications
            args = self.build_objects(args)

        return draw_class(*args, **kwargs)


catalog = dict(compoundobject=CompoundObject, canvas=Canvas,
               drawingcanvas=DrawingCanvas,
               constructedcanvas=ConstructedCanvas)
register_canvas_types(catalog)

# END
