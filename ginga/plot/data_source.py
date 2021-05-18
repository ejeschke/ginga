#
# data_source.py -- utilities to assist in making time-series plots
#
from collections import deque

import numpy as np


class XYDataSource:
    """Monitor a data source efficiently.

    Uses a static array circular queue and a sliding window algorithm to
    efficiently keep track of the current set of points and it's minmax.
    """

    def __init__(self, arr_src, points=[], overwrite=False,
                 none_for_empty=False):
        """Constructor for Data Source

        Parameters
        ----------
        arr_src : ndarray
            (x, y) points to initialize the data source with

        points : array, list, tuple or sequence-like (optional)
            An array of points to initialize the data source with

        overwrite : bool (optional)
            If ``True`` the buffer will eventually overwrite old entries

        none_for_empty : bool (optional)
            If ``True`` then don't raise a ValueError for an empty buffer

        """
        self.buf = arr_src
        self.length = len(arr_src)
        self.overwrite = overwrite
        self.none_for_empty = none_for_empty

        # for circular queue
        self.front = self.length - 1
        self.rear = None

        self.limits = np.array([[0.0, 0.0], [0.0, 0.0]])

        self.set_points(points)

    def get_limits(self):
        """Return the limits of this current data source.  The return value
        looks like: [(xmin, ymin), (xmax, ymax)]
        """
        return np.copy(self.limits)

    def update_limits(self):
        """Mostly internal routine to update the limits.  Shouldn't need to
        be called explicitly in most cases.
        """
        if len(self) == 0:
            self.limits = np.array([[0.0, 0.0], [0.0, 0.0]])
        else:
            x_min, x_max = self.buf[self.rear][0], self.buf[self.front][0]
            y_min, y_max = self.slmm.get_minmax()
            self.limits = np.array([[x_min, y_min], [x_max, y_max]])

    def set_points(self, points):
        """Initialize the data source with a series of points.
        `points` should be a list/array/sequence of (x, y)
        """
        self.slmm = SlidingWindowMinMax()
        self.front = self.length - 1
        self.rear = None

        self.add_points(points)

    def add_points(self, points):
        """Add a series of points.
        `points` should be a list/array/sequence of (x, y)
        """
        for pt in points:
            self._add(pt)
        self.update_limits()

    def is_fullp(self):
        """Returns True if there is no more room in the buffer."""
        front = (self.front + 1) % self.length
        return front == self.rear

    def _add(self, pt):
        x, y = pt
        front = (self.front + 1) % self.length

        if front == self.rear:
            if not self.overwrite:
                raise ValueError("Buffer is full")
            # circular queue full, need to expunge an old element
            _x, _y = self.buf[self.rear]
            if not np.isnan(_y):
                self.slmm.remove_head(_y)
            self.rear = (self.rear + 1) % self.length

        self.front = front
        if self.rear is None:
            self.rear = self.front

        self.buf[self.front, :] = pt
        if not np.isnan(y):
            self.slmm.add_tail(y)

    def add(self, pt, update_limits=True):
        """Add a single data point and update the plot.
        If the number of points exceeds the `length` of the data source,
        the oldest point will be ejected.
        If `update_limits` is `True` (the default) then the limits of the
        current data set are updated.
        """
        self._add(pt)
        if update_limits:
            self.update_limits()

    append = add
    push = add

    def peek(self):
        """Get the latest data point.  Will return `None` if there are no
        points recorded.
        """
        if len(self) == 0:
            if self.none_for_empty:
                return None
            raise ValueError("Buffer is empty")
        return self.buf[self.front]

    get_latest = peek

    def pop(self):
        """Get and remove the latest data point.
        Will return `None` if there are no points recorded.
        """
        if len(self) == 0:
            if self.none_for_empty:
                return None
            raise ValueError("Buffer is empty")
        pt = self.buf[self.front]
        if self.rear == self.front:
            self.rear = None
        else:
            self.front = self.length - 1 if self.front == 0 else self.front - 1
        return pt

    def peek_rear(self):
        """Get the earliest data point.  Will return `None` if there are no
        points recorded.
        """
        if len(self) == 0:
            if self.none_for_empty:
                return None
            raise ValueError("Buffer is empty")
        return self.buf[self.rear]

    def pop_rear(self):
        """Get and remove the earliest data point.
        Will return `None` if there are no points recorded.
        """
        if len(self) == 0:
            if self.none_for_empty:
                return None
            raise ValueError("Buffer is empty")
        pt = self.buf[self.rear]
        if self.rear == self.front:
            self.rear = None
        else:
            self.rear = (self.rear + 1) % self.length
        return pt

    def get_points(self):
        """Get the entire set of data points as an `ndarray`.
        """
        n = len(self)
        arr = np.zeros((n, 2), dtype=float)
        if n == 0:
            return arr
        if self.front >= self.rear:
            arr[:n, :] = self.buf[self.rear:self.front + 1, :]
        else:
            m = self.length - self.rear
            arr[0:m, :] = self.buf[self.rear:self.length, :]
            arr[m:n, :] = self.buf[0:self.front + 1, :]
        return arr

    @property
    def points(self):
        return self.get_points()

    def __len__(self):
        if self.rear is None:
            return 0
        if self.front >= self.rear:
            return self.front - self.rear + 1
        else:
            return self.length - self.rear + self.front + 1


class SlidingWindowMinMax:
    """Class to efficiently keep track of the minmax values of a changing
    data set.
    """

    def __init__(self):
        self.min_deque = deque()
        self.max_deque = deque()

    def get_minmax(self):
        return (self.min_deque[0], self.max_deque[0])

    def add_tail(self, val):
        while len(self.min_deque) > 0 and val < self.min_deque[-1]:
            self.min_deque.pop()
        self.min_deque.append(val)

        while len(self.max_deque) > 0 and val > self.max_deque[-1]:
            self.max_deque.pop()
        self.max_deque.append(val)

    def remove_head(self, val):
        if val < self.min_deque[0]:
            raise ValueError("Wrong value")
        elif val == self.min_deque[0]:
            self.min_deque.popleft()

        if val > self.max_deque[0]:
            raise ValueError("Wrong value")
        elif val == self.max_deque[0]:
            self.max_deque.popleft()


def update_plot_from_source(dsrc, xyplot, update_limits=False):
    """Update the associated plot with the current set of points.
    If `update_limits` is `True` then the plot limits will be updated
    with the current limits of the data.
    """
    arr = dsrc.get_points()
    if update_limits:
        limits = dsrc.get_limits()
        xyplot.plot(arr, limits=limits)
    else:
        xyplot.plot(arr)
