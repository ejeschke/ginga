.. _ch-core-concepts:

+++++++++++++
Core Concepts
+++++++++++++

Ginga operation and documentation is organized around a few core
concepts and associated nomenclature.  Knowing these may aid in
understanding the rest of the documentation. 

.. _concepts-workspaces:

==========
Workspaces
==========

Ginga has a flexible panel/workspace layout algorithm that allows a
lot of customization into the appearance of the program.  The majority
of the interface is constructed as hierchical series of horizontally or
vertically-adjustable panels.  At the terminus of each panel is a
*workspace*.
Each workspace is typically
implemented by a GUI toolkit container widget such as a notebook widget,
where each item in the workspace is identified by a tab.  Workspaces can
be nested, so a tab might contain yet another nested set of tabs, and so
on [#f1]_. 
Tabs can be freely dragged between workspaces, (or out onto the desktop if you are using
the Gtk widget set), forming a new, detached workspace.

In its default configuration, Ginga starts up with a
single row (horizontal) panel of three workspaces, as shown in
the image below.
This panel is sandwiched vertically between a menu bar and a status bar.

.. image:: figures/gingadefault.png
   :width: 100%
   :align: center

The layout of the workspaces is controlled by a 
table in the Ginga startup script (see :ref:`ch-customization`).
By changing this table the layout can be substantially altered. 

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
"Channel/Add channel" menu item.

In the case where multiple channels are present, they are usually visually
organized as tabs within the central workspace of the interface.  To
change channels you simply click on the tab of the channel you want to
view.  There is also a channel selector in the plugin manager toolbar at
the bottom of the center pane.  Using the drop-down menu or by simply
scrolling the mouse wheel on the control you can change the channel.

Channels occupy a flat namespace; i.e. there is no sense of a hierarchy
of channels.
By default, images are loaded into the same channel you are currently
viewing (unless your viewer has been customized to load images according
to special rules).
To keep images organized, simply change to the desired channel before
opening a new image. 

Many preferences in Ginga are set on a per-channel basis.  A new channel
will generally "inherit" the settings for the generic "Image"
channel until new preferences are defined and saved. If you create a 
new channel and have already saved preferences for a channel with that
name, it will adopt those preferences. Thus you can set up channels 
configured for certain telescopes or types of data and easily reuse
them in later sessions.

.. _concepts_plugins:

=======
Plugins
=======

Most functionality in Ginga is achieved through the use of a plugin
architecture.
In this manual we will also use the word *operation* to describe activating
a plugin.  For example, a pick operation would invoke and use the Pick
plugin.  The plugins are each described in more detail in Chapter 
:ref:`ch-plugins`.  Plugins are written as encapsulated Python modules
that are loaded dynamically when Ginga starts.  There is an API for
programming plugins (see :ref:`ch-programming-ginga`).  

A plugin may or may not have an associated Graphical User Interface (GUI).
For those that do have a visible interface, the Ginga startup script
can map them to certain workspaces.  By manipulating this mapping (along
with the workspace layout) extremely customized and flexible layouts can
be achieved.  
In the image at the top, the left workspace contains three
global plugin UIs: the Info, Header and Zoom panes.  The middle workspace
holds all the viewing panes for each channel.  The right workspace has
the Dialogs, Thumbs, Contents and Help panes.  The operation of these
plugins is described in Chapter :ref:`ch-plugins`. 

.. rubric:: Footnotes

.. [#f1] Note that workspaces may be implemented by several types of 
	 container widgets such as fixed position subwindows, sliding panes,
	 MDI-style subwindows, etc.  A notebook widget is simply the most
	 common (default) case.

