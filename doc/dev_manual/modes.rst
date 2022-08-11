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
the default bindings that come with Ginga in the
Quick Reference :ref:`ginga-quick-reference`.

==============
Writing a mode
==============
Writing a mode is somewhat similar to writing a plugin for the
Ginga reference viewer.  A mode is a subclass class derived from
``~ginga.modes.mode_base.Mode``.

As far as the class structure goes, there should be an ``__init__()``
constructor that calls the superclass, as well as ``start()`` and ``stop()``
methods.  The ``start()`` method 
