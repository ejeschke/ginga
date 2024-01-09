#
# events.py -- Event classes for Ginga viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#


class UIEvent:
    """Base class for user interface events."""
    def __init__(self, viewer=None):
        self.viewer = viewer
        self.handled = False

    def accept(self):
        self.handled = True

    def was_handled(self):
        return self.handled


class KeyEvent(UIEvent):
    """A key press or release event in a Ginga viewer.

    Attributes
    ----------
    key : str
        The key as it is known to Ginga

    state: str
        'down' if a key press, 'up' if a key release

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, key=None, state=None, mode=None, modifiers=None,
                 data_x=None, data_y=None, viewer=None):
        super().__init__(viewer=viewer)
        self.key = key
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.data_x = data_x
        self.data_y = data_y


class PointEvent(UIEvent):
    """A mouse/pointer/cursor event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        'down' if a press, 'move' if being dragged, 'up' if a release

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 data_x=None, data_y=None, viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.data_x = data_x
        self.data_y = data_y


class ScrollEvent(UIEvent):
    """A mouse or trackpad scroll event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        Always 'scroll'

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    direction : float
        A direction in compass degrees of the scroll

    amount : float
        The amount of the scroll

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 direction=None, amount=None, data_x=None, data_y=None,
                 viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.direction = direction
        self.amount = amount
        self.data_x = data_x
        self.data_y = data_y


class PinchEvent(UIEvent):
    """A pinch event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        'start' (gesture starting), 'move' (in action) or 'stop' (done)

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    rot_deg : float
        Amount of rotation in degrees

    scale : float
        Scale of the pinch shrink or enlargement

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 rot_deg=None, scale=None, data_x=None, data_y=None,
                 viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.rot_deg = rot_deg
        self.scale = scale
        self.data_x = data_x
        self.data_y = data_y


class PanEvent(UIEvent):
    """A pinch event in a Ginga viewer.

    Attributes
    ----------
    button : str
        The name of the button as set up in the configuration

    state: str
        'start' (gesture starting), 'move' (in action) or 'stop' (done)

    mode : str
        The mode name of the mode that was active when the event happened

    modifiers : set of str
        A set of names of modifier keys that were pressed at the time

    delta_x : float
        Amount of scroll movement in the X direction

    delta_y : float
        Amount of scroll movement in the Y direction

    data_x : float
        X part of the data coordinates of the viewer under the cursor

    data_y : float
        Y part of the data coordinates of the viewer under the cursor

    viewer : subclass of `~ginga.ImageView.ImageViewBase`
        The viewer in which the event happened
    """
    def __init__(self, button=None, state=None, mode=None, modifiers=None,
                 delta_x=None, delta_y=None, data_x=None, data_y=None,
                 viewer=None):
        super().__init__(viewer=viewer)
        self.button = button
        self.state = state
        self.mode = mode
        self.modifiers = modifiers
        self.delta_x = delta_x
        self.delta_y = delta_y
        self.data_x = data_x
        self.data_y = data_y
