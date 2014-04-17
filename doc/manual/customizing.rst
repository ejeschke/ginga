.. _ch-customization:

+++++++++++++++++
Customizing Ginga
+++++++++++++++++
This chapter explains how you can customize the Ginga reference viewer
in various ways. 

=====================
Configuration Options
=====================

Ginga creates a `.ginga` subdirectory in the user's home directory in
which various configuration settings can be saved.

general.cfg::

    # General preferences
    
    # Preference for fixed and sans fonts
    fixedFont = 'Monospace'
    sansFont = 'Sans Serif'
    
    # Import matplotlib colormaps in addition to our own set if matplotlib
    # is installed
    useMatplotlibColormaps = True
    channelFollowsFocus = False
    showBanner = False
    numImages = 10

.. _sec-bindings:

==================
Rebinding Controls
==================

Example: ds9 bindings
---------------------

This example shows a way to use ds9-like mouse bindings for colormap
stretch (right mouse button) and setting pan position (scroll
button). This is taken verbatim from a file called "bindings.cfg.ds9"
in the "examples/bindings" directory in the source download.  This file
can be installed in the user's $HOME/.ginga folder as "bindings.cfg".

bindings.cfg::

    #
    # bindings.cfg -- Ginga user interface bindings customization
    #
    # Put this in your $HOME/.ginga directory as "bindings.cfg"
    #
    # Troubleshooting:
    # Run the scripts/example2_xyz.py, where "xyz" is the toolkit you want
    # to use.  Run it from a terminal like this:
    #    ./examples/xyz/example2_xyz.py --loglevel=10 --stderr
    # Further commentary in sections below.
    #
    
    # BUTTON SET UP
    # You should rarely have to change these, but if you have a non-standard
    # mouse or setup it might be useful.
    # To find out what buttons are generating what codes, start up things as
    # described in "Troubleshooting" above and look for messages like this as
    # you click around in the window:
    #  ... | D | Bindings.py:1260 (window_button_press) | x,y=70,-69 btncode=0x1
    btn_nobtn = 0x0
    btn_left  = 0x1
    btn_middle= 0x2
    btn_right = 0x4
    
    # Set up our standard modifiers.
    # These should not contain "normal" keys--they should be valid modifier
    # keys for your platform.
    # To find out what symbol is used for a keystroke on your platform,
    # start up things as described above in "Troubleshooting" and look for
    # messages like this as you press keys while focus is in the window:
    #  ... | D | Bindings.py:1203 (window_key_press) | keyname=shift_l
    mod_shift = ['shift_l', 'shift_r']
    # same setting ends up as "Ctrl" on a pc and "Command" on a mac:
    mod_ctrl = ['control_l', 'control_r']
    # "Control" key on a mac:
    mod_draw = ['meta_right']
    
    # KEYPRESS commands
    kp_zoom_in = ['+', '=']
    kp_zoom_out = ['-', '_']
    kp_zoom = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
    kp_zoom_inv = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')']
    kp_zoom_fit = ['backquote']
    kp_autozoom_on = ['doublequote']
    kp_autozoom_override = ['singlequote']
    kp_draw = ['space']
    kp_dist = ['s']
    kp_dist_reset = ['S']
    kp_freepan = ['q']
    kp_pan_set = ['p']
    kp_center = ['c']
    kp_cut_low = ['<']
    kp_cut_high = ['>']
    kp_cut_all = ['.']
    kp_cut_255 = ['A']
    kp_cut_auto = ['a']
    kp_autocuts_on = [':']
    kp_autocuts_override = [';']
    kp_cmap_warp = ['/']
    kp_cmap_restore = ['?']
    kp_flip_x = ['[', '{']
    kp_flip_y = [']', '}']
    kp_swap_xy = ['backslash', '|']
    #kp_rotate = ['r']
    kp_rotate_reset = ['R']
    kp_reset = ['escape']
    
    # SCROLLING/WHEEL commands
    sc_pan = ['ctrl+scroll', 'shift+scroll']
    sc_pan_fine = []
    sc_pan_coarse = []
    sc_zoom = ['scroll']
    sc_zoom_fine = []
    sc_zoom_coarse = []
    sc_contrast_fine = []
    sc_contrast_coarse = []
    sc_dist = []
    
    # This controls how fast panning occurs with the sc_pan* functions.
    # Increase to speed up panning
    scroll_pan_acceleration = 1.0
    # For trackpads you can adjust this down if it seems too sensitive.
    scroll_zoom_acceleration = 1.0
    
    
    # MOUSE/BUTTON commands
    # NOTE: most plugins in the reference viewer need "none", "cursor" and "draw"
    # events to work!  If you want to use them you need to provide a valid
    # non-conflicting binding
    ms_none = ['nobtn']
    ms_cursor = ['left']
    ms_wheel = []
    ms_draw = ['draw+left']
    
    # mouse commands initiated by a preceeding keystroke (see above)
    ms_rotate = ['rotate+left']
    ms_cmapwarp = ['cmapwarp+left', 'right']
    ms_cmaprest = ['ctrl+middle']
    ms_pan = ['ctrl+left']
    ms_freepan = ['freepan+left', 'shift+middle']
    ms_cutlo = ['cutlo+left']
    ms_cuthi = ['cuthi+left']
    ms_cutall = ['cutall+left']
    ms_panset = ['shift+left', 'middle']
    
    # GESTURES (Qt version only)
    # Uncomment to enable pinch gensture on touchpads.
    # NOTE: if you enable this, it is *highly* recommended to disable any
    # "scroll zoom" (sc_zoom*) features above because the two kinds don't play
    # well together.  A good combination for trackpads is enabling pinch with
    # zoom and the sc_pan functions.
    #gs_pinch = ['pinch']
    
    # This controls what operations the pinch gesture controls.  Possibilities are
    # (empty list or) some combination of 'zoom' and 'rotate'.
    pinch_actions = ['zoom']
    pinch_zoom_acceleration = 1.0
    pinch_rotate_acceleration = 1.0
    
    # ds9 uses opposite sense of panning direction
    pan_reverse = True
    
    # ds9 uses opposite sense of zooming scroll wheel
    zoom_scroll_reverse = True
    
    # No messages for color map warps or setting pan position
    msg_cmap = False
    msg_panset = False
    
    #END

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
        Bunch(module='Pan', tab='Pan', ws='uleft', raisekey='I'),
        Bunch(module='Info', tab='Info', ws='lleft', raisekey='I'),
        Bunch(module='Header', tab='Header', ws='left', raisekey='H'),
        Bunch(module='Zoom', tab='Zoom', ws='left', raisekey='Z'),
        Bunch(module='Thumbs', tab='Thumbs', ws='right', raisekey='T'),
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

    default_layout = ['seq', {},
                       ['vbox', dict(name='top', width=1500, height=900),
                        dict(row=['hbox', dict(name='menu')],
                             stretch=0),
                        dict(row=['hpanel', {},
                         ['ws', dict(name='left', width=340, group=2),
                          # (tabname, layout), ...
                          [("Info", ['vpanel', {},
                                     ['ws', dict(name='uleft', height=300,
                                                 show_tabs=False, group=3)],
                                     ['ws', dict(name='lleft', height=430,
                                                 show_tabs=False, group=3)],
                                     ]
                            )]],
                         ['vbox', dict(name='main', width=700),
                          dict(row=['ws', dict(name='channels', group=1)], stretch=1)],
                         ['ws', dict(name='right', width=350, group=2),
                          # (tabname, layout), ...
                          [("Dialogs", ['ws', dict(name='dialogs', group=2)
                                        ]
                            )]
                          ],
                         ], stretch=1),
                        dict(row=['hbox', dict(name='status')], stretch=0),
                        ]]

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

