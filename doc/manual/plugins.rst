.. _ch-plugins:

+++++++
Plugins
+++++++

Ginga is written so that most of the functionality of the program is
achieved through the use of plugins.  This modular approach allows a
large degree of flexiblity and customization, as well as making overall
design and maintenance of the program simpler.

Plugins are divided into two types: *global* and *local*.
A global plugin has a single instance shared by all channels, while a
local plugin creates a unique instance for each channel.  If you switch
channels, a global plugin will respond to the change by updating itself,
while a local plugin will remain unchanged if the channel is switched,
because its operation is specific to a given channel.  (Ginga's concept
of channels is discussed in :ref:`concepts-channels`.)

This chapter describes the set of plugins that come with Ginga.  Those
interested in writing their own custom plugins should refer to
:ref:`sec-writing-global-plugins` or :ref:`sec-writing-local-plugins`.

.. _sec-globalplugins:

==============
Global plugins
==============

.. toctree::
   :maxdepth: 1

   plugins_global/toolbar
   plugins_global/pan
   plugins_global/info
   plugins_global/header
   plugins_global/zoom
   plugins_global/thumbs
   plugins_global/contents
   plugins_global/colorbar
   plugins_global/cursor
   plugins_global/operations
   plugins_global/wbrowser
   plugins_global/fbrowser
   plugins_global/saveimage
   plugins_global/errors
   plugins_global/rc
   plugins_global/wcsmatch
   plugins_global/changehistory
   plugins_global/samp
   plugins_global/iraf
   plugins_global/log
   plugins_global/command


.. _sec-localplugins:

=============
Local plugins
=============

An *operation* is the activation of a local plugin to perform some
function.  The plugin manager toolbar at the bottom of the center pane
is the graphical way to start an operation.

.. toctree::
   :maxdepth: 1

   plugins_local/pick
   plugins_local/ruler
   plugins_local/multidim
   plugins_local/cuts
   plugins_local/histogram
   plugins_local/crosshair
   plugins_local/overlays
   plugins_local/tvmark
   plugins_local/tvmask
   plugins_local/blink
   plugins_local/lineprofile
   plugins_local/pixtable
   plugins_local/preferences
   plugins_local/catalogs
   plugins_local/mosaic
   plugins_local/drawing
   plugins_local/fbrowser
   plugins_local/compose
   plugins_local/pipeline
