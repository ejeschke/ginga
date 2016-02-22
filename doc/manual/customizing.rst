.. _ch-customization:

+++++++++++++++++
Customizing Ginga
+++++++++++++++++
One of the primary guiding concepts behind the Ginga project is to
provide convenient ways to build custom viewers.  The reference viewer
embodies this concept through the use of a flexible layout engine and
the use of plugins to implement all the major user interface features.
By modifying or replacing the layout and adding, subclassing or removing
plugins you can completely change the look, feel and operation of the 
reference viewer.

This chapter explains how you can customize the Ginga reference viewer
in various ways, as a user or a developer.

=====================
Configuration Options
=====================

Ginga examines a configuration directory on startup to check for any
configuration files or customization of the default behavior.

.. note:: The configuration area is determined first by examining the
          environment variable `GINGA_HOME`.  If that is not set, then 
          `$HOME/.ginga` (Mac OS X, Linux) or
          `$HOMEDRIVE:$HOMEPATH\\.ginga` (Windows) will be used.

Examples of the types of configuration files with comments describing the
effects of the parameters can be found in `.../ginga/examples/configs`.
Many of the plugins have their own configuration file, with preferences
that are only changed via that file.  You can copy an example
configuration file to your Ginga settings area and change the settings  
to your liking.

Usually it is sufficient to simply close the plugin and open it again to
pick up any settings changes, but some changes may require a viewer
restart to take effect.

Channels also use configuration files to store many different settings
for the channel viewer windows.  When a channel is created, the
reference viewer looks to see if there is a configuration file for that
channel in the configuration area; if so, the settings therein are used
to configure it.  If not, the settings for the generic startup channel
"Image" are used to configure the new channel.  The "Preferences" plugin
can be used to set many of the channel settings.  If you set these for
the "Image" channel and use the "Save" button, other channels will
inherit them.  You can also manually copy the example file from 
`.../ginga/examples/configs/channel_Image.cfg` to your configuration
area and edit it if you prefer.

.. _sec-bindings:

==================
Rebinding Controls
==================

One configuration file that many users will be interested in is the one
controlling how keyboard and mouse/touch bindings are assigned.  This is
handled by the configuration file `bindings.cfg`.  Several examples 
are stored in `.../ginga/examples/bindings`, including an example for
users familiar with the ds9 mouse controls, and an example for users
using a touchpad without a mouse (pinch zoom and scroll panning).
Simply copy the appropriate file to your Ginga settings area as
`bindings.cfg`. 

.. _sec-workspaceconfig:

======================================================
Customizing the Reference Viewer During Initialization
======================================================

The reference viewer can be customized during viewer initialization
using a module called `ginga_config`, which can be anywhere in the
user's Python import path, including in the Ginga configuration folder
described above (e.g. `$HOME/.ginga/ginga_config.py`).

Specifically, this file will be imported and two methods will be run if
defined: `pre_gui_config(ginga_shell)` and
`post_gui_config(ginga_shell)`.
The parameter to each function is the main viewer shell.  These functions
can be used to define a different viewer layout, add or remove plugins,
add menu entries, add custom image or star catalogs, etc.  We will refer
back to these functions in the sections below.

=======================
Workspace configuration
=======================

Ginga has a flexible table-driven layout scheme for dynamically creating
workspaces and mapping the available plugins to workspaces.  By changing
a couple of tables via `ginga_config.pre_gui_config()` you can change
the way Ginga looks and presents its content.

If you examine the module `ginga.main` you will find a layout table
called `default_layout`::

    default_layout = ['seq', {},
                       ['vbox', dict(name='top', width=1520, height=900),
                        dict(row=['hbox', dict(name='menu')],
                             stretch=0),
                        dict(row=['hpanel', dict(name='hpnl'),
                         ['ws', dict(name='left', wstype='tabs',
                                     width=300, height=-1, group=2),
                          # (tabname, layout), ...
                          [("Info", ['vpanel', {},
                                     ['ws', dict(name='uleft', wstype='stack',
                                                 height=300, group=3)],
                                     ['ws', dict(name='lleft', wstype='tabs',
                                                 height=430, group=3)],
                                     ]
                            )]],
                         ['vbox', dict(name='main', width=700),
                          dict(row=['ws', dict(name='channels', wstype='tabs',
                                               group=1)], stretch=1),
                          dict(row=['ws', dict(name='cbar', wstype='stack',
                                               group=99)], stretch=0),
                          dict(row=['ws', dict(name='readout', wstype='stack',
                                               group=99)], stretch=0),
                                               dict(row=['ws', dict(name='operations', wstype='stack',
                                               group=99)], stretch=0),
                          ],
                         ['ws', dict(name='right', wstype='tabs',
                                     width=400, height=-1, group=2),
                          # (tabname, layout), ...
                          [("Dialogs", ['ws', dict(name='dialogs', wstype='tabs',
                                                   group=2)
                                        ]
                            )]
                          ],
                         ], stretch=1),
                        dict(row=['ws', dict(name='toolbar', wstype='stack',
                                             height=40, group=2)],
                             stretch=0),
                        dict(row=['hbox', dict(name='status')], stretch=0),
                        ]]


This rather arcane-looking table defines the precise layout of the
reference viewer shell, including how many workspaces it will have, their
characteristics, how they are organized, and their names.

The key point in this section is that you can modify this table or
replace it entirely with one of your own design and set it in the
`pre_gui_config()` method described above::

    my_layout = [
                  ...
                 ]

    def pre_gui_config(ginga_shell):
        ...

        ginga_shell.set_layout(my_layout)

If done in the `pre_gui_config()` method (as shown) the new layout will
be the one that is used when the GUI is constructed.

Format of the Layout Table
--------------------------

The table consists of a nested list of sublists, tuples and/or dictionaries.
The first item in a sublist indicates the type of the container to be
constructed.  The following types are available:

* `seq`: defines a sequence of top-level windows to be created

* `hpanel`: a horizontal panel of containers, with handles to size them

* `vpanel`: a vertical panel of containers, with handles to size them

* `hbox`: a horizontal panel of containers of fixed size

* `vbox`: a vertical panel of containers of fixed size

* `ws`: a workspace that allows a plugin or a channel viewer to be
  loaded into it. A workspace can be configured in four ways: as a
  tabbed notebook (`wstype="tabs"`), as a stack (`wstype="stack"`), as
  an MDI (Multiple Document Interface, `wstype="mdi"`) or a grid
  (`wstype="grid"`).

* `widget`: a preconstructed widget passed in.

In every case the second item in the sublist is a dictionary that
provides some optional parameters that modify the characteristics of the
container.  If there is no need to override the default parameters the
dictionary can simply be empty. The optional third and following items
are specifications for nested content.

All types of containers honor the following parameters:

* width: can specify a desired width in pixels for the container.

* height: can specify a desired height in pixels for the container.

* name: specifies a mapping of a name to the created container
  widget.  The name is important especially for workspaces, as they may
  be referred to as an output destination when registering plugins.

.. note:: In the above example, we define a top-level window consisting
          of a vbox (named "top") with 4 layers: a hbox ("menu"), hpanel
          ("hpnl"), a workspace ("toolbar") and another hbox ("status").
          The main horizontal panel of three containers: a workspace
          ("left") with a width of 300 pixels, a vbox ("main", 700
          pixels) and a workspace ("right", 400 pixels).
          The "left" workspace is pre-populated
          with an "Info" tab containing a vertical panel of two
          workspaces: "uleft" and "lleft" with heights of 300 and 430
          pixels, respectively.  The "right" workspace is pre-populated
          with a "Dialogs" tab containing an empty workspace.
          The "main" vbox is configured with three rows of workspaces:
          "channels", "cbar" and "readout".

Ginga uses some container names in special ways.
For example, Ginga looks for a "channels" workspace as the default
workspace for creating channels, and the "dialogs" workspace is where
most local plugins are instantiated (when activated), by default.
These two names should at least be defined somewhere in default_layout.

==========================
Adding or Removing Plugins
==========================

A plugin can be added to the reference viewer in `pre_gui_config()`
using one of two methods.  The first method is using the
`add_local_plugin()` or `add_global_plugin()` methods, 
depending on whether it is a local or global plugin, respectively::

    def pre_gui_config(ginga_shell):
        ...

        ginga_shell.add_local_plugin('DQCheck', "dialogs")

The above call would try to load a local plugin called "DQCheck" from a
module called "DQCheck".  When invoked from the Operations menu it would
occupy a spot in the "dialogs" workspace (see layout discussion above).

.. note:: It is a convention in Ginga plugins that the module name and
          plugin name (a class name) are the same.

Global plugins are similar, except that some of them are considered
critical to the viewers basic operation and so should be started when
the program starts::

    def pre_gui_config(ginga_shell):
        ...

        ginga_shell.add_global_plugin('SpecScope', "left",
                                      tab_name="Spec Scope", start_plugin=True)


==============================
Making a Custom Startup Script
==============================

You can make a custom startup script to make the same reference viewer
configuration available without relying on the `ginga_config` module in
a personal settings area.  To do this we make use of the `main` module::

    import sys
    from ginga.main import ReferenceViewer
    from optparse import OptionParser

    my_layout = [ ... ]

    if __name__ == "__main__":
        viewer = ReferenceViewer(layout=my_layout)
        # add global plugins
        viewer.add_global_plugin(...)
        viewer.add_global_plugin(...)

        # add local plugins
        viewer.add_local_plugin(...)
        viewer.add_local_plugin(...)

        # Parse command line options with optparse module
        usage = "usage: %prog [options] cmd [args]"
        optprs = OptionParser(usage=usage)
        viewer.add_default_options(optprs)

        (options, args) = optprs.parse_args(sys_argv[1:])

        viewer.main(options, args)

