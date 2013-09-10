.. _ch-customization:

+++++++++++++++++
Customizing Ginga
+++++++++++++++++
This chapter explains how you can customize the Ginga reference viewer
in various ways. 

.. _sec-bindings:

==================
Rebinding Controls
==================

Example: ds9 bindings
---------------------

This example shows some code you can use to give ds9-like mouse bindings
to for colormap stretch (right mouse button) and setting pan position
(scroll button). This code can be added to the startup customization
script in $HOME/.ginga/ginga_config.py .

The standard Bindings class is subclassed, and we override the method
for the setup of the standard button events.  Two new methods are
provided for doing colormap tweaking and setting the pan position, both
without the usual onscreen message.  Care is taken to make sure that the
standard events used for plugins are not disrupted.

::

    from ginga.Bindings import FitsImageBindings
    # uncomment the right one for your platform
    #from ginga.gtkw.FitsImageGtk import FitsImageZoom
    from ginga.qtw.FitsImageQt import FitsImageZoom
    
    # subclass the standard bindings and rewire some things
    # changes are NOTED
    
    class MyGingaBindings(FitsImageBindings):
    
        def setup_default_btn_events(self, fitsimage, bindmap):
    
            # Generate standard symbolic mouse events for unmodified buttons:
            # xxxxx-{down, move, up}
            # e.g. 'left' button down generates 'cursor-down', moving the mouse
            # with no button pressed generates 'none-move', etc.
            for btnname, evtname in (('nobtn', 'none'), ('left', 'cursor'),
                                     ('middle', 'wheel'), ('right', 'draw')):
                bindmap.map_event(None, btnname, evtname)
    
            # standard bindings
            bindmap.map_event('shift', 'left', 'panset')
            bindmap.map_event('ctrl', 'left', 'pan')
            # NOTE: disable standard free panning, because we want middle click
            # to set pan position
            #bindmap.map_event(None, 'middle', 'freepan')
            bindmap.map_event(None, 'middle', 'panset')
            bindmap.map_event('ctrl', 'right', 'cmapwarp')
            bindmap.map_event('ctrl', 'middle', 'cmaprest')
            # name 'scroll' is hardwired for the scrolling action
            bindmap.map_event(None, 'scroll', 'zoom')
            bindmap.map_event('shift', 'scroll', 'zoom-fine')
            bindmap.map_event('ctrl', 'scroll', 'zoom-coarse')
    
            # Mouse operations that are invoked by a preceeding key
            for name in ('rotate', 'cmapwarp', 'cutlo', 'cuthi', 'cutall',
                            'draw', 'pan', 'freepan'):
                bindmap.map_event(name, 'left', name)
    
            # Now register our actions for these symbolic events
            # NOTE: disable standard cmapwarp, we want to call our own callback
            for name in ('cursor', 'wheel', 'draw', 'rotate', #'cmapwarp',
                         'pan', 'freepan', 'cutlo', 'cuthi', 'cutall'):
                method = getattr(self, 'ms_'+name)
                for action in ('down', 'move', 'up'):
                    fitsimage.set_callback('%s-%s' % (name, action), method)
            # NOTE:
            # 1. bind draw to color map warp when it isn't captured by a plugin
            # 2. color warping is bound to my callback (below) to
            #    disable onscreen message
            for action in ('down', 'move', 'up'):
                fitsimage.set_callback('draw-%s' % (action), self.my_cmapwarp)
                # bind normal cmapwarp to my version (sans message)
                fitsimage.set_callback('cmapwarp-%s' % (action), self.my_cmapwarp)
    
            # NOTE: I don't want to see the onscreen pan position set message
            fitsimage.set_callback('panset-down', self.my_panset)
            fitsimage.set_callback('cmaprest-down', self.ms_cmaprest)
    
            fitsimage.set_callback('zoom-scroll', self.ms_zoom)
            fitsimage.set_callback('zoom-coarse-scroll',
                                   self.ms_zoom_coarse)
            fitsimage.set_callback('zoom-fine-scroll', self.ms_zoom_fine)
    
        def my_panset(self, fitsimage, action, data_x, data_y):
            # set pan position, but suppress onscreen message
            return self.ms_panset(fitsimage, action, data_x, data_y,
                                  msg=False)
    
        def my_cmapwarp(self, fitsimage, action, data_x, data_y):
            # warp color map, but suppress onscreen message
            return self.ms_cmapwarp(fitsimage, action, data_x, data_y,
                                    msg=False)
    
    def pre_gui_config(ginga):
        # this method is called before the GUI is brought up
        # custom configuration can be done here
        FitsImageZoom.set_bindingsClass(MyGingaBindings)


.. _sec-workspaceconfig:

=======================
Workspace configuration
=======================

Ginga has a flexible table-driven layout scheme for dynamically creating
workspaces and mapping the plugins to workspaces.  By changing a couple
of tables you can change the way Ginga looks and presents its content. 
If you examine the top-level startup script `ginga.py` you will find
the tables: `default_layout`, `global_plugins` and
`local_plugins`.
global_plugins and local_plugins define the mapping of plugins to
workspaces and the titles on the tabs in the workspaces (if the
workspace has tabs--some don't).  
Here is an example of these two tables::

    global_plugins = [
        Bunch(module='Pan', tab='Pan', ws='uleft', raisekey='i'),
        Bunch(module='Info', tab='Info', ws='lleft', raisekey='i'),
        Bunch(module='Header', tab='Header', ws='left', raisekey='h'),
        Bunch(module='Zoom', tab='Zoom', ws='left', raisekey='z'),
        Bunch(module='Thumbs', tab='Thumbs', ws='right', raisekey='t'),
        Bunch(module='Contents', tab='Contents', ws='right', raisekey='c'),
        Bunch(module='WBrowser', tab='Help', ws='right', raisekey='?'),
        Bunch(module='Errors', tab='Errors', ws='right'),
        Bunch(module='Log', tab='Log', ws='right'),
        Bunch(module='Debug', tab='Debug', ws='right'),
        ]
    
    local_plugins = [
        Bunch(module='Pick', ws='dialogs', shortkey='f1'),
        Bunch(module='Ruler', ws='dialogs', shortkey='f2'),
        Bunch(module='MultiDim', ws='dialogs', shortkey='f4'), 
        Bunch(module='Cuts', ws='dialogs', shortkey='f5'),
        Bunch(module='Histogram', ws='dialogs', shortkey='f6'),
        Bunch(module='PixTable', ws='dialogs', shortkey='f7'),
        Bunch(module='Preferences', ws='dialogs', shortkey='f9'),
        Bunch(module='Catalogs', ws='dialogs', shortkey='f10'),
        Bunch(module='Drawing', ws='dialogs', shortkey='f11'),
        Bunch(module='FBrowser', ws='dialogs', shortkey='f12'), 
        ]

The format of this table is simply a series of tuples"bunches".
In the case of global_plugins, each bunch specifies a module, 
a title for the tab, the workspace that it should occupy, and an
optional key to raise that tab when pressed.
We can see that the "Pan" plugin will occupy the "uleft" workspace
and have a tab name of "Pan" (if that workspace has tabs).

Next we look at the default_layout table::

    default_layout = ['hpanel', {},
                      ['ws', dict(name='left', width=320),
                       # (tabname, layout), ...
                       [("Info", ['vpanel', {},
                                  ['ws', dict(name='uleft', height=300,
                                              show_tabs=False)],
                                  ['ws', dict(name='lleft', height=430,
                                              show_tabs=False)],
                                  ]
                         )]
                         ],
                      ['vbox', dict(name='main', width=700)],
                      ['ws', dict(name='right', width=400),
                       # (tabname, layout), ...
                       [("Dialogs", ['ws', dict(name='dialogs')
                                     ]
                         )]
                        ],
                      ]

This table defines how many workspaces we will have, their
characteristics, how they are organized, and their names.
The table consists again of a series of sublists or tuples, but in this
case they can be nested.
The first item in a sublist indicates the type of the container to be
constructed.  The following types are available:

* hpanel: a horizontal panel of containers, with handles to size them

* vpanel: a vertical panel of containers, with handles to size
  them

* hbox: a horizontal panel of containers of fixed size

* vbox: a vertical panel of containers of fixed size

* ws: a workspace that allows a plugin gui or other items, usually
  implemented by a notebook-type widget

* widget: a preconstructed widget passed in

In every case the second item in the sublist is a dictionary that
provides some optional parameters that modify the characteristics of the
container.
If there is no need to override the default parameters the dictionary
can simply be empty.
The optional third and following items are specifications for nested
content.

All types of containers honor the following parameters:

* width: can specify a desired width in pixels for the container.

* height: can specify a desired height in pixels for the container.

* name: specifies a mapping of a name to the created container
  widget.  The name is important especially for workspaces, as they may
  be referred to in the default_tabs table.

In the above example, we define a top-level horizontal panel of three
containers: a workspace named "left" with a width of 320 pixels, a
vertical fixed container named "main" with a width of 700 pixels and a
workspace called "right" with a width of 400 pixels.  The "left"
workspace is pre-populated with an "Info" tab containing a vertical
panel of two workspaces: "uleft" and "lleft" with heights of 300 and
430 pixels, respectively, and neither one should show tabs.  The "right"
workspace is pre-populated with a "Dialogs" tab containing an empty
workspace.  Looking back at the  default_tabs table you can now more 
clearly see how the mapping of plugins to workspaces is handled through
the names.

Ginga uses some container names in special ways.
For example, the "main" container is populated by Ginga with the tabs
for each channel, and the "dialogs" workspace is where all of the
local plugins are instantiated (when activated).
These two names should at least be defined somewhere in default_layout.

