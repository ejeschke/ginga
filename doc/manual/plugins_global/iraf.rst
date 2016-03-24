.. _sec-plugins-IRAF:

IRAF Interaction
----------------

.. image:: figures/IRAF-plugin.png
   :align: center

The IRAF plugin allows Ginga to interoperate with IRAF in a manner
similar to IRAF and ds9.  The following IRAF commands are supported:
`imexamine`, `rimcursor`, `display` and `tvmark`.

To use the IRAF plugin, first make sure the environment variable IMTDEV
is set appropriately, e.g.::

    $ export IMTDEV=inet:45005

or::

    $ export IMTDEV=unix:/tmp/.imtg45

If the environment variable is not set, Ginga will default to that used
by IRAF.

Then start Ginga and IRAF.  For Ginga, the IRAF module is not started by
default.  To start it when Ginga starts, specify the command line option::

    --modules=IRAF

or use the `Start IRAF` menu item from the `Plugins` menu.
The GUI for the IRAF plugin will appear in the tabs on the right.

It can be more convenient to load images via Ginga than IRAF.  From
Ginga you can load images via drag and drop or via the FBrowser
plugin and then use `imexamine` from IRAF to do analysis tasks on
them.  You can also use the `display` command from IRAF to show
images already loaded in IRAF in Ginga, and then use `imexamine` to
select areas graphically for analysis.

When using `imexamine` or `rimcursor`, the plugin disables
normal UI processing on the channel image so that keystrokes,
etc. normally caught by Ginga are passed through to IRAF.  You can
toggle back and forth between local Ginga control (e.g. keystrokes to
zoom and pan the image, or apply cut levels, etc.) and IRAF control
using the radio buttons at the top of the tab.

IRAF deals with images in enumerated "frames", whereas Ginga uses
named channels.  The bottom of the IRAF plugin GUI will show the mapping
from Ginga channels to IRAF frames.
