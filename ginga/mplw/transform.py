#
# transform.py -- a custom projection for supporting matplotlib plotting
#                          on ginga
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# NOTE: this code is based on "custom_projection_example.py", an example
# script developed by matplotlib developers
# See http://matplotlib.org/examples/api/custom_projection_example.html
#
from __future__ import print_function

import matplotlib
from matplotlib.axes import Axes
from matplotlib.path import Path
from matplotlib.transforms import Affine2D, BboxTransformTo, Transform, \
     blended_transform_factory
from matplotlib.projections import register_projection

import numpy as np
from ginga.util.six.moves import map, zip


class GingaAxes(Axes):
    """
    This is a custom matplotlib projection to support matplotlib plotting
    on a ginga-rendered image in a matplotlib Figure.

    This code is based on 'custom_projection_example.py', an example
    script developed by matplotlib developers.
    """
    # The projection must specify a name.  This will be used be the
    # user to select the projection, i.e. ``subplot(111,
    # projection='ginga')``.
    name = 'ginga'

    def __init__(self, *args, **kwargs):
        # this is the Ginga object
        self.viewer = kwargs.pop('viewer', None)
        Axes.__init__(self, *args, **kwargs)
        ## self.set_aspect(0.5, adjustable='box', anchor='C')
        self.cla()

    def set_viewer(self, viewer):
        self.viewer = viewer
        self.transData.viewer = viewer

    def _set_lim_and_transforms(self):
        """
        This is called once when the plot is created to set up all the
        transforms for the data, text and grids.
        """
        # There are three important coordinate spaces going on here:
        #
        #    1. Data space: The space of the data itself
        #
        #    2. Axes space: The unit rectangle (0, 0) to (1, 1)
        #       covering the entire plot area.
        #
        #    3. Display space: The coordinates of the resulting image,
        #       often in pixels or dpi/inch.

        # This function makes heavy use of the Transform classes in
        # ``lib/matplotlib/transforms.py.`` For more information, see
        # the inline documentation there.

        # The goal of the first two transformations is to get from the
        # data space to axes space.  It is separated into a non-affine
        # and affine part so that the non-affine part does not have to be
        # recomputed when a simple affine change to the figure has been
        # made (such as resizing the window or changing the dpi).

        # 3) This is the transformation from axes space to display
        # space.
        self.transAxes = BboxTransformTo(self.bbox)

        # Now put these 3 transforms together -- from data all the way
        # to display coordinates.  Using the '+' operator, these
        # transforms will be applied "in order".  The transforms are
        # automatically simplified, if possible, by the underlying
        # transformation framework.
        #self.transData = \
        #    self.transProjection + self.transAffine + self.transAxes
        self.transData = self.GingaTransform()
        self.transData.viewer = self.viewer

        # self._xaxis_transform = blended_transform_factory(
        #         self.transData, self.transAxes)
        # self._yaxis_transform = blended_transform_factory(
        #         self.transAxes, self.transData)
        self._xaxis_transform = self.transData
        self._yaxis_transform = self.transData

    # Prevent the user from applying scales to one or both of the
    # axes.  In this particular case, scaling the axes wouldn't make
    # sense, so we don't allow it.
    def set_xscale(self, *args, **kwargs):
        if args[0] != 'linear':
            raise NotImplementedError
        Axes.set_xscale(self, *args, **kwargs)

    def set_yscale(self, *args, **kwargs):
        if args[0] != 'linear':
            raise NotImplementedError
        Axes.set_yscale(self, *args, **kwargs)

    # Prevent the user from changing the axes limits.  This also
    # applies to interactive panning and zooming in the GUI interfaces.
    ## def set_xlim(self, *args, **kwargs):
    ##     print "Setting xlim!", args

    ## def set_ylim(self, *args, **kwargs):
    ##     print "Setting ylim!", args

    def format_coord(self, x, y):
        """
        Override this method to change how the values are displayed in
        the status bar.
        """
        return 'x=%f, y=%f' % (x, y)

    def get_data_ratio(self):
        """
        Return the aspect ratio of the data itself.

        This method should be overridden by any Axes that have a
        fixed data ratio.
        """
        return 1.0

    def can_zoom(self):
        """
        Return True if this axes support the zoom box
        """
        # TODO: get zoom box working
        return False

    def can_pan(self):
        """
        Return True if this axes support the zoom box
        """
        return True

    def start_pan(self, x, y, button):
        """
        Called when a pan operation has started.

        *x*, *y* are the mouse coordinates in display coords.
        button is the mouse button number:

        * 1: LEFT
        * 2: MIDDLE
        * 3: RIGHT

        .. note::

            Intended to be overridden by new projection types.

        """
        bd = self.viewer.get_bindings()
        data_x, data_y = self.viewer.get_data_xy(x, y)
        bd.ms_pan(self.viewer, 'down', data_x, data_y)

    def end_pan(self):
        """
        Called when a pan operation completes (when the mouse button
        is up.)

        .. note::

            Intended to be overridden by new projection types.

        """
        bd = self.viewer.get_bindings()
        data_x, data_y = self.viewer.get_last_data_xy()
        bd.ms_pan(self.viewer, 'up', data_x, data_y)

    def drag_pan(self, button, key, x, y):
        """
        Called when the mouse moves during a pan operation.

        *button* is the mouse button number:

        * 1: LEFT
        * 2: MIDDLE
        * 3: RIGHT

        *key* is a "shift" key

        *x*, *y* are the mouse coordinates in display coords.

        .. note::

            Intended to be overridden by new projection types.

        """
        bd = self.viewer.get_bindings()
        data_x, data_y = self.viewer.get_data_xy(x, y)
        bd.ms_pan(self.viewer, 'move', data_x, data_y)

    # Now, the transforms themselves.

    class GingaTransform(Transform):
        """
        The base Ginga transform.
        """
        input_dims = 2
        output_dims = 2
        is_separable = False
        viewer = None
        #pass_through = True

        def invalidate(self):
            #print("I don't feel validated! (%s)" % (self.pass_through))
            return Transform.invalidate(self)

        def transform_non_affine(self, xy):
            """
            Override the transform_non_affine method to implement the custom
            transform.

            The input and output are Nx2 numpy arrays.
            """
            #print(("transform in:", xy))
            if self.viewer is None:
                return xy

            res = np.dstack(self.viewer.get_canvas_xy(xy.T[0], xy.T[1]))[0]
            #print(("transform out:", res))
            return res

        # This is where things get interesting.  With this projection,
        # straight lines in data space become curves in display space.
        # This is done by interpolating new values between the input
        # values of the data.  Since ``transform`` must not return a
        # differently-sized array, any transform that requires
        # changing the length of the data array must happen within
        # ``transform_path``.
        def transform_path_non_affine(self, path):
            ipath = path.interpolated(path._interpolation_steps)
            return Path(self.transform(ipath.vertices), ipath.codes)
        transform_path_non_affine.__doc__ = \
                Transform.transform_path_non_affine.__doc__

        if matplotlib.__version__ < '1.2':
            # Note: For compatibility with matplotlib v1.1 and older, you'll
            # need to explicitly implement a ``transform`` method as well.
            # Otherwise a ``NotImplementedError`` will be raised. This isn't
            # necessary for v1.2 and newer, however.
            transform = transform_non_affine

            # Similarly, we need to explicitly override ``transform_path`` if
            # compatibility with older matplotlib versions is needed. With v1.2
            # and newer, only overriding the ``transform_path_non_affine``
            # method is sufficient.
            transform_path = transform_path_non_affine
            transform_path.__doc__ = Transform.transform_path.__doc__

        def inverted(self):
            tform = GingaAxes.InvertedGingaTransform()
            tform.viewer = self.viewer
            return tform

        inverted.__doc__ = Transform.inverted.__doc__

    class InvertedGingaTransform(Transform):
        input_dims = 2
        output_dims = 2
        is_separable = False
        viewer = None

        def transform_non_affine(self, xy):
            #print "transform in:", xy
            if self.viewer is None:
                return xy

            res = np.dstack(self.viewer.get_data_xy(xy.T[0], xy.T[1]))[0]
            #print "transform out:", res
            return res

        transform_non_affine.__doc__ = Transform.transform_non_affine.__doc__

        # As before, we need to implement the "transform" method for
        # compatibility with matplotlib v1.1 and older.
        if matplotlib.__version__ < '1.2':
            transform = transform_non_affine

        def inverted(self):
            # The inverse of the inverse is the original transform... ;)
            tform = GingaAxes.GingaTransform()
            tform.viewer = self.viewer
            return tform

        inverted.__doc__ = Transform.inverted.__doc__

# Now register the projection with matplotlib so the user can select
# it.
register_projection(GingaAxes)

#END
