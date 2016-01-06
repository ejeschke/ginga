.. _ch-customization:

+++++++++++++++++
Customizing Ginga
+++++++++++++++++
One of the primary guiding concepts behind the Ginga project is to
provide easy ways to build custom viewers, whether that is by using the
viewer class by itself in your project or by customizing the reference
viewer.  

The reference viewer embodies this concept of configurability through
the use of a flexible layout engine and the use of plugins to implement
all the major user interface features.  By modifying or replacing the
layout and adding, subclassing or removing plugins you can completely
change the look, feel and operation and make your own version of a
viewer that has exactly the features you want. 

This chapter explains how you can customize the Ginga reference viewer
in various ways, as a user or a developer.

=====================
Configuration Options
=====================

Ginga uses a configuration directory in which various configuration
settings can be saved and loaded as individual configuration files.   

.. note:: The configuration area is determined first by examining the
          environment variable `GINGA_HOME`.  If that is not set, then 
          `$HOME/.ginga` (Mac OS X, Linux) or
          `$HOMEDRIVE:$HOMEPATH\\.ginga` (Windows) will be used.

Examples of these configuration files with comments describing the
effects of the parameters can be found in `.../ginga/examples/configs`.
Many of the plugins have preferences that are only changed via a
plugin-specific configuration file (e.g. `plugin_Pick.cfg`).
You can copy an example configuration file to your Ginga settings area
and change the settings to your liking.

.. note:: Usually it is sufficient to simply close the plugin and open
          it again to pick up any settings changes, but some changes may
          require a viewer restart to take effect.

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
via a module called `ginga_config`, which can be anywhere in the
user's Python import path, including in the Ginga settings folder
described above (e.g. `$HOME/.ginga/ginga_config.py`).

Specifically, this file will be imported and two methods will be run if
defined: `pre_gui_config(ginga)` and `post_gui_config(ginga)`.  The
parameter to each function is the main viewer shell.  These functions
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
called `default_layout`.  It should look something like this::

    my_layout = ['seq', {},
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

This (admittedly arcane-looking) table defines the precise layout
of the reference viewer shell, including how many workspaces it will
have, their characteristics, how they are organized, how they are
divided into (fixed or resizable) rows and columns and their names.

The key point here is that you can modify this table or replace it
entirely with one of your own design and set it in the
`pre_gui_config()` method described above::

    my_layout = [
                  ...
                 ]

    def pre_gui_config(ginga):
        ...

        ginga.set_layout(my_layout)

If done in the `pre_gui_config()` method (as shown) the new layout will
be the one that is used when the GUI is constructed.

Format of the Layout Table
--------------------------

The table consists of a nested list of sublists, tuples and/or dictionaries.
The lists are structured as::

    [ <Type of item>  <Dict of item attributes>
      <Optional Dict or sublist defining sub-item>
      ...
    ]

The following types of items can be constructed:

* `seq`: defines a sequence of top-level windows to be created

* `hpanel`: a horizontal panel of containers, with handles to size them

* `vpanel`: a vertical panel of containers, with handles to size them

* `hbox`: a horizontal panel of containers of fixed size

* `vbox`: a vertical panel of containers of fixed size

* `ws`: a workspace container that allows a plugin or a channel viewer
  to be loaded into it. 

* `widget`: a preconstructed widget passed in.  This allows extremely
  fine control when customizing.

In every case the second item in the sublist is a dictionary that
provides some optional parameters that modify the characteristics of the
container.  If there is no need to override the default parameters the
dictionary can simply be empty.  These attributes include:

* `name`: key that this item should get stored under in the widget
  dictionary that is constructed as part of building the layout (this is
  described elsewhere).  The name is mostly important for workspaces,
  as it provides the reference for where a plugin should be loaded. 
  Because of this workspace names should really be unique.

* `wstype`: used when the item type is "ws", and specifies the type of
  workspace to be constructed.  A workspace can be configured in four
  ways: as a tabbed notebook (`wstype="tabs"`), as a stack
  (`wstype="stack"`), as a Multiple Document Interface (`wstype="mdi"`)
  or as a grid (`wstype="grid"`).

* width: can specify a desired width in pixels for the container.

* height: can specify a desired height in pixels for the container.

The optional third and following items are specifications for nested
content.  These are usually also sublists, but can also be specified as
dictionaries for types `hbox` and `vbox`.

==========================
Adding or Removing Plugins
==========================

A plugin can be added to the reference viewer in `pre_gui_config()`
using one of two methods.  The first method is using the
`add_local_plugin()` or `add_global_plugin()` methods, 
depending on whether it is a local or global plugin, respectively::

    def pre_gui_config(ginga):
        ...

        ginga.add_local_plugin('DQCheck', "dialogs")

The above call would try to load a local plugin called "DQCheck" from a
module called "DQCheck".  When invoked from the Operations menu it would
occupy a spot in the "dialogs" workspace (see layout discussion above).

.. note:: It is a convention in Ginga plugins that the module name and
          plugin name (a class name) are the same.

Global plugins are similar, except that some of them are considered
critical to the viewers basic operation and so should be started when
the program starts::

    def pre_gui_config(ginga):
        ...

        ginga.add_global_plugin('SpecScope', "left",
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

