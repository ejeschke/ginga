#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.misc import Callback

__all__ = ['WidgetError', 'WidgetBase']


class WidgetError(Exception):
    """For errors thrown in this module."""
    pass


# This is needed by aggw/Plot.py
class WidgetBase(Callback.Callbacks):
    pass
