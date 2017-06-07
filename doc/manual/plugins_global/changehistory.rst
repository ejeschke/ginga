.. _sec-plugins-changehistory:

ChangeHistory
=============

.. image:: figures/changehistory-plugin.png
   :align: center
   :width: 400px
   :alt: ChangeHistory plugin

This global plugin is used to log any changes to data buffer. For example,
a change log would appear here if a new image is added to a mosaic via the
Mosaic plugin. Like :ref:`sec-plugins-contents`, the log is sorted by channel,
and then by image name.

.. exec::

    from ginga.util.toolbox import generate_cfg_example
    print(generate_cfg_example('plugin_ChangeHistory', package='ginga'))
