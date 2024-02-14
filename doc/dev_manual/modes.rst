.. _ch-dev-modes:

++++++++++++++++
Developing Modes
++++++++++++++++

Modes are associated with the basic Ginga viewer widget and are used to
make bindings between keyboard, mouse, trackpad and gesture events and
certain operations on the viewer.  There are lots of operations
possible, but only a limited number of key and cursor events; by
invoking a mode, certain keystrokes and cursor operations are enabled.
These same keystrokes and cursor events might do something
different in another mode.  You can read about the standard modes and
the default bindings that come with Ginga in :ref:`concepts-modes`
"concepts", "about" :ref:`ch-modes` and in the :ref:`ginga-quick-reference`.

==============
Writing a mode
==============
If you are familiar with the Reference Viewer you may know about its
plugin architecture. You can think of modes as mini-plugins that don't
know about channels or other Reference Viewer entities, but only know
about the Ginga viewer widget with which they are associated. The mode
functions manipulate the viewer according to key and cursor bindings
that they register.

Methods of a mode
=================
A mode is a subclass derived from `~ginga.modes.mode_base.Mode`.
As far as the class structure goes, the following methods are required
and explained below.

__init__
--------
The constructor is called when the mode is first instantiated for a
viewer; it should at a minimum call the superclass, and define an
attribute named ``actions`` that is assigned a dictionary of bindings.

start
-----
``start()`` is called when the mode is activated by the user.
It should do any initialization necessary since the constructor or the
last call to ``stop()``.  For many cases, this may be nothing, since the
purpose of most modes is simply to enable the new bindings for the
duration of the mode.

stop
-----
``stop()`` is called when a mode is deactivated.  It does any cleanup
necessary and puts the mode in a state where it will be ready for a
future call to ``start()``.

__str__
-------
The ``__str__`` method should be set to return a unique, lower-case string
that is used to identify the mode and indicate the mode in the viewer
mode indicator.

Other methods
-------------
All other methods are typically event callback bindings for cursor and key
actions that are being handled by the mode, or helper functions used by
those callbacks.

================================
Bindings DSL and Event Callbacks
================================
Ginga actions for binding cursor and key events is specified as a kind
of Domain Specific Language that is compatible with the format for Ginga
settings files.
This is to allow the user to customize the bindings completely by
providing a ``bindings.cfg`` file in their ``$HOME/.ginga`` folder.
In the modes, this takes the form of a dictionary defined in the
constructor and assigned to the attribute ``actions``.

The key of each element of the dictionary usually matches the name of a
method defined in the mode, and the value is a list of triggers
(specified as strings) that should invoke the method.  There are
conventions that must be followed for both the name and the triggers.

Method names
============
For handling events, the (method) name must start with one of the
following prefixes, which indicate the type of binding that will be made
and the event handling:

* kp\_ : a key press and release
* ms\_ : a cursor (mouse, trackpad, etc) action: button down, button up, move
* sc\_ : a scrolling (mouse, trackpad) action
* pi\_ : a pinch gesture action
* pa\_ : a pan gesture action

.. note:: Gestures are not supported equally on all platforms and
          toolkits.  For example, under Qt on Mac OSX, a pan gesture
          is supported using the trackpad, but on Linux, that same
          gesture on a trackpad is handled as a scrolling action.

It is typical (but not essential) to have the next part of the method
name match the mode in which it is implemented.  Then, the suffix makes
the purpose of the callback known.

Triggers
========
Triggers are spelled out as a string of the form: ``<mode>+<modifier>+<action>``
where either of the ``<mode>`` and ``<modifier>`` are optional (if omitted,
then the preceding plus sign is also omitted).

``<mode>`` is simply the name of the mode for which the binding should be
active.  This will match the name returned by the ``__str__`` method in
the class implementation.  If ``<mode>`` is omitted, the binding is assigned
to the "modeless" operation, which means that it can be activated if no
mode is currently activated and the event is not handled by some active
canvas.  This is mechanism by which "default" actions are handled by a
mode for certain events even when no mode is currently active.

``<modifier>`` stands for a keyboard modifier key.  The usual defined ones
are "shift" and "ctrl".  An asterisk can be used as a wildcard in this
position to indicate that the event should be bound for any combination
of modifiers or lack of a modifier.

The ``<action>`` describes what is happening in combination with the ``<mode>``
and ``<modifier>`` to trigger the event.  It is a key symbol, the name of a
mouse button (usually "left",  "middle", or "right"), "scroll" for the
scroll action, and "pinch" or "pan" for the two gestures, respectively.

Examples
========
Assume that these are part of a :py:obj:`dict` being defined, or in a user's
``bindings.cfg``.

kp_pan_page_up=['pan+*+page_up']

    The method that will be called is ``kp_pan_page_up()``.  The action
    that will trigger this is being in the "pan" mode, pressing any or
    no combinations of modifier keys with the key "page_up".

sc_zoom=['scroll']

    The method is ``sc_zoom()``. It will be called when scrolling happens
    and the scrolling is not handled by any mode or an active canvas.

kp_zoom_fit=['backquote', 'pan+backquote']

    The method is ``kp_zoom_fit()`` and it will be called if the
    backquote key is pressed while in "pan" mode, and also any other
    time backquote is pressed and a mode or an active canvas does not
    handle it.

ms_rotate=['rotate+left']

    The method is ``ms_rotate()`` and it will be called when in the
    "rotate" mode and the left mouse button or trackpad is pressed,
    moved while pressed (a drag motion), and when released.

Event handler method signatures
===============================

Keyboard and cursor events both have the same callback method signature:

.. code-block:: python

    def kp_handler(self, viewer, event, data_x, data_y)
    def ms_handler(self, viewer, event, data_x, data_y)

These are instance methods, as evidenced by the presence of ``self``.
The other parameters in the callback are:

* ``viewer`` : the viewer in which the action happened
* ``event`` : the event which was caught by the trigger
* ``data_x``, ``data_y`` : the X/Y data coordinates where the cursor was
  when the event happened (this is also available in the ``event``)

.. note:: The ``data_x`` and ``data_y`` parameters are for backward
          compatibility.  It is recommended *not* to use them as they
          may be removed from the callback in a future version.
          Instead, use the values found in the ``event`` object.

Scroll, pinch, and pan events have a slightly different method signature:

.. code-block:: python

    def sc_handler(self, viewer, event)
    def pi_handler(self, viewer, event)
    def pa_handler(self, viewer, event)

These just receive the ``viewer`` and the ``event`` which precipitated the
callback.

.. note:: To see what attributes are available in each event, see the
          ``KeyEvent``, ``PointEvent``, ``ScrollEvent``, ``PanEvent``, and
          ``PinchEvent`` in the :ref:`api` (look under `ginga.events`).

