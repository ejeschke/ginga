.. _ch-core-concepts:

+++++++++++++
Core Concepts
+++++++++++++

Ginga reference viewer operation is organized around several basic 
concepts: *workspaces*, *channels*, *plugins*, *modes*.
Understanding these will greatly aid in using and/or modifying Ginga.

.. _concepts-workspaces:

==========
Workspaces
==========

Ginga has a flexible panel/workspace layout algorithm that allows a
lot of customization into the appearance of the program.  The majority
of the interface is constructed as hierarchical series of horizontally or
vertically-adjustable panels.  At the terminus of each panel is a
*workspace*.
Each workspace is implemented by a GUI toolkit container widget such as
a notebook widget, where each item in the workspace is identified by a
tab.  But workspaces can also take the form of a stack (like a tabbed
widget, but with no tabs showing), a Multiple Document Interface (MDI)
style container (subwindow desktop-style layout), or a grid layout.

Workspaces typically contain either a channel *viewer*, a *plugin* UI or
another workspace. 
In its default configuration, Ginga starts up with a
single row (horizontal) panel of three workspaces, as shown in
the image below.
This panel is sandwiched vertically between a menu bar and a status bar.
The left workspace is further subdivided into an upper and lower, and
there are also thin horizontal workspaces below the central workspace.
The central workspace is mainly used for viewers, while the other
workspaces hold plugin UIs.

.. image:: figures/gingadefault.png
   :width: 1024px
   :align: center

The initial layout of the workspaces is controlled by a 
table in the Ginga startup script (see :ref:`ch-customization`).
By changing this table the layout can be substantially altered. 

Some workspaces can be converted dynamically between the different types. 
If the workspace contains a *workspace toolbar*, the workspace type
selector can be used to change the type: 

.. image:: figures/wstype_selector.png
   :width: 800px
   :align: center

In the example shown below, we show a cutout of the main workspace
(tabbed), which has two tabs: a channel viewer ("Image") and a second
workspace ("ws1").  The "ws1" workspace is configured as type "MDI" and
has two windows: a viewer ("Image0") and a third workspace ("ws2").  The
third workspace contains a grid of four viewers. 

.. image:: figures/nested_workspaces.png
   :width: 1024px
   :align: center

Depending on the the support of the back end widget set, tabs can be
dragged between workspaces, (or out onto the desktop if you are
using the Gtk widget set), forming a new, detached workspace.

.. _concepts-channels:

========
Channels
========

Another core tenet of Ginga is that image content is organized
into *channels*.  A channel can be thought of as simply a named
category under which similar types of images might be organized.

Examples: 

* a channel for each type of instrument at a telescope;
* a channel for each observation or calibration target;
* channels based on time or program or proposal identifier;
* etc.

If no channels are specified when Ginga starts up it simply creates a
default channel named "Image".  New channels can be created using the
"Channel/Add channel" menu item.  Pressing the "+" button in the
workspace menu also adds a new channel using a default name.

A channel always has an image viewer associated with it and may
additionally have a table viewer.  The viewer is what you see when you
show the window representing that channel.

.. image:: figures/channels.png
   :width: 800px
   :align: center

In the workspace toolbar, pressing "-" removes the currently selected
channel, while pressing the "up" or "down" arrows moves between images
in the selected channel. 

In the case where multiple channels are present, they are usually visually
organized as tabs/windows/grid within the central workspace of the
interface (as shown in the figure above) depending on how the workspace
is configured.
To change channels you simply click on the tab of the channel you want to
view, or press the "left"/"right" arrow buttons in the workspace menu.
There is also a channel selector in the plugin manager toolbar at
the bottom of the center pane.  Using the drop-down menu or by simply
scrolling the mouse wheel on the control you can change the channel:

.. image:: figures/channel_selector.png
   :width: 800px
   :align: center

Channels occupy a flat namespace; i.e. there is no sense of a hierarchy
of channels.
By default, images are loaded into the same channel you are currently
viewing (unless your viewer has been customized to load images according
to special rules).
To keep images organized, simply change to the desired channel before
opening a new image, or drag the image to the desired channel viewer.

Many preferences in Ginga are set on a per-channel basis.
Some per-channel settings include:

* color distribution algorithm
* color map
* intensity map
* cut levels
* auto cut levels algorihm
* transforms (flip, swap)
* rotation
* WCS display coordinates
* zoom algorithm
* scale
* interpolation type
* pan position
* etc.

A new channel will generally "inherit" the settings for the generic "Image"
channel until new preferences are defined and saved. If you create a 
new channel and have already saved preferences for a channel with that
name, it will adopt those preferences. Thus you can set up channels 
configured for certain telescopes or types of data and easily reuse
them in later sessions.

Another idea embodied in the channel concept is that the user should not
have to manage memory usage too explicitly.  Each channel has a setting
that limits how many images it should keep in memory: if the number
exceeds the limit Ginga will remove older images and load them back in as
needed without user intervention.

.. _concepts_plugins:

=======
Plugins
=======

Almost all functionality in Ginga is achieved through the use of a plugin
architecture.  Plugins are quasi-independent python modules that can
optionally have a Graphical User Interface.  If they do have a UI, it
can be loaded at program startup or dynamically opened and closed during
the duration of the viewer's execution.  Plugins can be *global*, in
which case they don't have any particular affiliation with a channel and
are generally invoked singularly, or *local* in which case they can be
invoked in multiple instances--one per channel.

In this manual we will also use the word *operation* to describe activating
a plugin.  For example, a pick operation would invoke and use the Pick
plugin.  The plugins are each described in more detail in Chapter 
:ref:`ch-plugins`.  Plugins are written as encapsulated Python modules
that are loaded dynamically when Ginga starts.  There is an API for
programming plugins (see :ref:`ch-programming-ginga`).  

For those plugins that do have a visible interface, the Ginga startup
script can map them to certain workspaces.  By manipulating this mapping
(along with the workspace layout) extremely customized and flexible
layouts can be achieved.  
In the image at the top, the left workspace contains three
global plugin UIs: the Info, Header and Zoom panes.  The middle workspace
holds all the viewing panes for each channel.  The right workspace has
the Dialogs, Thumbs, Contents and Error panes.  The operation of these
plugins is described in Chapter :ref:`ch-plugins`. 

.. rubric:: Footnotes

.. [#f1] Note that workspaces may be implemented by several types of 
	 container widgets such as fixed position subwindows, sliding panes,
	 MDI-style subwindows, etc.  A notebook widget is simply the most
	 common (default) case.


.. _concepts-modes:

===========
About modes
===========
Ginga provides a number of default bindings for key and pointer actions.
But there are too many different actions to bind to a limited set of
keys and pointer buttons.
*Modes* are a mechanism that allow Ginga to accommodate many key and
pointer bindings for a large number of operations. 

Modes are set on a per-channel basis.  Pressing a particular
mode key in a channel viewer puts that viewer into that mode, 
in which *some* special key, cursor and scroll bindings will override
the default ones (if a mode does not override a particular binding, the
default one will still be active).  An adjacent viewer for a different
channel may be in a different mode, or no mode.

Modes have an associated *mode type* which can be set to one of:

* `held`: the mode is active while the activating key is held down
* `oneshot`: the mode is released by initiating and finishing a cursor drag,
  or when `Esc` is pressed, if no cursor drag is performed
* `locked`: the mode is locked until the mode key is pressed again (or `Esc`)
* `softlock`: the mode is locked until another mode key is pressed (or `Esc`)

By default most modes are activated in "oneshot" type, unless the mode
lock is toggled.  The mode lock is typically toggled in and out of
softlock by the "l" key and "locked" with the (capital) "L".

Modes are usually indicated by a small black rectangle with the mode
name in one corner of the viewer. 
When the lock is active it is signified by an additional "[SL]" (softlock) or
"[L]" (locked) appearing in the mode indicator.

.. image:: figures/mode_indicator.png
   :width: 800px
   :align: center

In the above figure, you can see the mode indicator showing that
the viewer is in "contrast" mode, with the softlock on.  The same
information can be seen in the Toolbar plugin.  On the Toolbar plugin
you can click to set the mode and toggle the lock on/off.

