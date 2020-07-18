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
          command line option ``--basedir``. If that is not set, then
          the environment variable ``GINGA_HOME`` is checked.  If that
          is not set, then ``$HOME/.ginga`` (Mac OS X, Linux) or
          ``$HOMEDRIVE:$HOMEPATH\\.ginga`` (Windows) will be used.

Examples of the types of configuration files with comments describing the
effects of the parameters can be found in
``.../ginga/examples/configs``.

The config files that end in ``.cfg`` use a stripped down Pythonic
format consisting of comments, blank lines and ``keyword = value`` pairs,
where values are specified using Python literal syntax.

General Config Files
--------------------
There is general top-level configuration file ``general.cfg`` in the
configuration area.  You can find an example in the examples area
described above.
               
.. _sec-bindings:

Binding Config File
-------------------

One configuration file that many users will be interested in is the one
controlling how keyboard and mouse/touch bindings are assigned.  This is
handled by the configuration file ``bindings.cfg``.  Several examples
are stored in ``.../ginga/examples/bindings``, including an example for
users familiar with the ds9 mouse controls, and an example for users
using a touchpad without a mouse (pinch zoom and scroll panning).
Simply copy the appropriate file to your Ginga settings area as
``bindings.cfg``.


Plugin Config Files
-------------------

Many of the plugins have their own configuration file, with preferences
that are only changed via that file.  You can copy an example
configuration file to your Ginga settings area and change the settings
to your liking.

Here is an example of a plugin configuration file for the ``Ruler``
plugin:

.. literalinclude:: ../../ginga/examples/configs/plugin_Ruler.cfg
    :language: python

Usually it is sufficient to simply close the plugin and open it again to
pick up any settings changes, but some changes may require a viewer
restart to take effect.

Channel Config Files
--------------------

Channels also use configuration files to store many different settings
for the channel viewer windows.  When a channel is created, the
reference viewer looks to see if there is a configuration file for that
channel in the configuration area; if so, the settings therein are used
to configure it.  If not, the settings for the generic startup channel
"Image" are used to configure the new channel.  The "Preferences" plugin
can be used to set many of the channel settings.  If you set these for
the "Image" channel and use the "Save" button, other channels will
inherit them.  You can also manually copy the example file from
``.../ginga/examples/configs/channel_Image.cfg`` to your configuration
area and edit it if you prefer.

.. _sec-workspaceconfig:

======================
Customizing the Layout
======================

Ginga has a flexible table-driven layout scheme for dynamically creating
workspaces and mapping the available plugins to workspaces.  This layout
can be specified with a Python structure (`layout`) in the configuration
area.  If there is no file initially, Ginga will use the built in
default layout.  Ginga will will update its window size, position and
some layout information to the layout file when the program is closed,
creating a new custom layout.  Upon a subsequent startup Ginga will
attempt to restore the window to the saved configuration.

.. note:: The name of the layout file is set in the general
          configuration file (``general.cfg``) as the value for
          ``layout_file``.  Set it to "layout.json" if you prefer to use
          the JSON format or "layout" if you prefer to use the Python
          format (the default).
          
.. note:: If you don't want Ginga to remember your changes to the window
          size or position, you can add the option ``save_layout =
          False`` to your general configuration file. Ginga will still
          read the layout from the file (if it exists--otherwise it will
          use the default, built-in layout), but will not update it when
          closing. 

.. note:: Invoking the program with the ``--norestore`` option 
          prevents it from reading the saved layout file, and forces use
          of the internal default layout table.  This may be needed in
          some cases when the layout changes in an incompatible way
          between when the program was last stopped and when it was
          started again.

Format of the Layout Table
--------------------------

The table consists of a list containing nested lists.  Each list
represents a container or a non-container endpoint, and has the
following format: 

.. code-block:: python

    [type  config-dict  optional-content0 ... optional-contentN]  


The first item in a list indicates the type of the container or object
to be constructed.  The following types are available:

* ``seq``: defines a sequence of top-level windows to be created
* ``hpanel``: a horizontal panel of containers, with handles to size them
* ``vpanel``: a vertical panel of containers, with handles to size them
* ``hbox``: a horizontal panel of containers of fixed size
* ``vbox``: a vertical panel of containers of fixed size
* ``ws``: a workspace that allows a plugin or a channel viewer to be
  loaded into it. A workspace can be configured in four ways: as a
  tabbed notebook (``wstype="tabs"``), as a stack (``wstype="stack"``), as
  an MDI (Multiple Document Interface, ``wstype="mdi"``) or a grid
  (``wstype="grid"``).

In every case the second item in the sublist is a dictionary that
provides some optional parameters that modify the characteristics of the
widget.  If there is no need to override the default parameters the
dictionary can simply be empty.  All types of containers honor the
following parameters in this ``dict``:

* ``width``: can specify a desired width in pixels for the container.
* ``height``: can specify a desired height in pixels for the container.
* ``name``: specifies a mapping of a name to the created container
  widget.  The name is important especially for workspaces, as they may
  be referred to as an output destination when registering plugins.

The optional third and following items in a list are specifications for
nested content.  The format for nested content depends on the type of the
container:

* ``seq``, ``hpanel`` and ``vpanel`` types expect the nested content items to
  be lists, as described above.
* ``hbox`` and ``vbox`` content items can be lists (as described above) or
  ``dict`` s. A ``vbox`` ``dict`` should have a ``row`` value and optionally a
  ``stretch`` value; an ``hbox`` ``dict`` should have a ``col`` value and
  optionally a ``stretch`` value.  The ``row`` and ``col`` values should be
  lists as described above.
* The ``ws`` (workspace) type takes one optional content item, which
  should be a sublist containing 2-item lists (or tuples) with the format
  ``(name, content)``, where ``content`` is a list as described above.  The
  ``name`` is used to identify each content item in the way appropriate
  for the workspace type, whether that is a notebook tab, MDI window
  titlebar, etc.

Here is the standard layout (Python format), as an example:

.. literalinclude:: ../../ginga/examples/layouts/standard/layout
    :language: python

In the above example, we define a top-level window consisting of a vbox
(named "top") with 4 layers: a hbox ("menu"), hpanel ("hpnl"), a
workspace ("toolbar") and another hbox ("status").  The main horizontal
panel ("hpnl") has three containers: a workspace ("left"), a vbox
("main") and a workspace ("right").  The "left" workspace is
pre-populated with an "Info" tab containing a vertical panel of two
workspaces: "uleft" and "lleft" (upper and lower left).  The "right"
workspace is pre-populated with a "Dialogs" tab containing an empty
workspace.  The "main" vbox is configured with four rows of workspaces:
"channels", "cbar", "readout" and "operations". 

.. note:: The workspace that has as a configuration option ``default:
          True`` (in this example, "channels") will be used as the
          default workspace where new channels should be created.


.. _sec-pluginconfig:

==============================
Customizing the set of plugins
==============================

In the configuration directory, the presence of a file ``plugins.json``
will override the built-in configuration of plugins.  The file format is
a JSON array containing JSON objects, each of which configures a plugin.
Example:

.. code-block::

    [
        {
            "__bunch__": true,
            "module": "Info",
            "tab": "Synopsis",
            "workspace": "lleft",
            "start": true,
            "hidden": true,
            "category": "System",
            "menu": "Info [G]",
            "ptype": "global"
       },
       ...
   ]
    
                 
The keys for each object are defined as follows:

* ``__bunch__``: should be present and set to ``true`` to force
  deserialization to a `~ginga.misc.Bunch.Bunch`.
* ``module``: The name of the module in the ``$PYTHONPATH`` containing
  the plugin.
* ``class``: if present, indicates the name of the class within the
  module that denotes the plugin (if not present the class is assumed
  to be named identically to the module).
* ``tab``: the name that the plugin should appear as when opened in a
  workspace (usually as a tab, but it depends on the type of
  workspace). Often the same name as the class, but can be different.
  If not present, defaults to the class or module name of the plugin.
* ``workspace``: the name of the workspace defined in the layout file
  (or default layout) where the plugin should be started (see section
  below on workspace customization).
* ``start``: ``true`` if the module is of the global type and should
  be started at program startup. Defaults to ``false``.
* ``hidden``: ``true`` if the plugin should be hidden from the
  "Operation" and "Plugins" menus. Often paired with ``hidden`` being
  ``true`` for plugins that are considered to be a necessary part of
  continuous operation from program startup to shutdown. Defaults to
  ``false``. 
* ``category``: an arbitrary organizational name under which plugins
  are organized in the ``Operation`` and ``Plugins`` menus.
* ``menu``: a name for how the plugin should appear under the category
  in the menu structure.  The convention is to append "[G]" if it is
  a global plugin.
* ``ptype``: either "local" or "global", depending on whether the
  plugin is a local or global one.
* ``optray``: to prevent a control icon from appearing in the
  ``Operations`` plugin manager tray specify ``false``.  The default for
  non-hidden plugins is ``true`` and for hidden plugins ``false``.
* ``enabled``: ``false`` to disable the plugin from being loaded.
    
See the standard set of plugins in
``.../ginga/examples/layouts/standard/plugins.json``


Custom plugin directory
-----------------------

If there is a ``plugins`` directory in the configuration area, it is added
to the ``PYTHONPATH`` for the purpose of loading plugins.  You can put
plugin modules in this directory, and then add entries to the
``plugins.json`` file described above to add new, custom plugins.

====================================================================
Customizing the Reference Viewer (with Python) During Initialization
====================================================================

For the ultimate flexibility, the reference viewer can be customized
during viewer initialization using a Python module called ``ginga_config``,
which can be anywhere in the user's Python import path, including in the
Ginga configuration folder described above.

Specifically, this file will be imported and two methods will be run if
defined: ``pre_gui_config(ginga_shell)`` and
``post_gui_config(ginga_shell)``.
The parameter to each function is the main viewer shell.  These functions
can be used to define a different viewer layout, add or remove plugins,
add menu entries, add custom image or star catalogs, etc.  We will refer
back to these functions in the sections below.

Workspace configuration
-----------------------

You can create a layout table (as described above in "Customizing the
Workspace") as a Python data structure, and then replace the default
layout table in the ``pre_gui_config()`` method described above::

    my_layout = [
                  ...
                 ]

    def pre_gui_config(ginga_shell):
        ...

        ginga_shell.set_layout(my_layout)

If done in the ``pre_gui_config()`` method (as shown) the new layout will
be the one that is used when the GUI is constructed.  See the default
layout in ``~ginga.rv.main`` as an example.

Start Plugins and Create Channels
---------------------------------

You can create channels and start plugins using the
``post_gui_config()`` method.

A plugin can be started automatically in ``post_gui_config()`` using the
``start_global_plugin()`` or ``start_local_plugin()`` methods, as appropriate::

    def post_gui_config(ginga_shell):
        # Auto start global plugins
        ginga_shell.start_global_plugin('Zoom')
        ginga_shell.start_global_plugin('Header')

        # Auto start local plugin
        ginga_shell.add_channel('Image')
        ginga_shell.start_local_plugin('Image', 'Histogram', None)

Alternately, you can also start plugins via the command line interface using
``--plugins`` and ``-modules`` for local and global plugins, respectively.
To load multiple plugins at once, use a comma-separated list. For example::

    ginga --plugins=MyLocalPlugin,Imexam --modules=MyGlobalPlugin

Adding Plugins
==============

A plugin can be added to the reference viewer in ``pre_gui_config()``
using the ``add_plugin()`` method with a specification ("spec") for
the plugin::

    from ginga.misc.Bunch import Bunch

    def pre_gui_config(ginga_shell):
        ...

        spec = Bunch(module='DQCheck', klass='DQCheck', workspace='dialogs',
                     category='Utils', ptype='local')
        ginga_shell.add_plugin(spec)

The above call would try to load a local plugin called "DQCheck" from a
module called "DQCheck".  When invoked from the Operations menu it would
occupy a spot in the "dialogs" workspace (see layout discussion above).

Disabling Plugins
=================

Both local and global plugins can be disabled (thus, not shown in the
reference viewer) using the ``--disable-plugins`` option in the
command line interface. To remove multiple plugins at once,
use a comma-separated list. For example::

    ginga --disable-plugins=Zoom,Compose

Alternately, plugins can also be disabled via ``general.cfg`` configuration
file. For example::

    disable_plugins = "Zoom,Compose"

Finally, if you are using a custom "plugins.json" file as described
above, you can simply set the ``enabled`` attribute to ``False`` in the
JSON object for that plugin in the file.

Some plugins, like ``Operations``, when disabled, may result in
inconvenient GUI experience.

==============================
Making a Custom Startup Script
==============================

You can make a custom startup script to make the same reference viewer
configuration available without relying on a custom set of startup files
or the ``ginga_config`` module.  To do this we make use of the
`~ginga.rv.main` module: 

.. code-block:: python

    import sys
    from argparse import ArgumentParser

    from ginga.rv.main import ReferenceViewer

    # define your custom layout 
    my_layout = [ ... ]

    # define your custom plugin list
    plugins = [ ... ]

    if __name__ == "__main__":
        viewer = ReferenceViewer(layout=my_layout)
        # add plugins
        for spec in plugins:
            viewer.add_plugin(spec)

        argprs = ArgumentParser(description="Run my custom viewer.")
        viewer.add_default_options(argprs)
        (options, args) = argprs.parse_known_args(sys_argv[1:])

        viewer.main(options, args)

