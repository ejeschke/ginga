.. _ch-programming-ginga:

+++++++++++++++++++++
Developing with Ginga
+++++++++++++++++++++

* :ref:`modindex`

======================================
Using the basic widget in new programs
======================================

.. _sec-writing-global-plugins:

=======================
Writing a global plugin
=======================
Global plugins are basically treated like mini programs that get loaded
into Ginga and are started when the program starts [#f1]_.
A global plugin does not need to have a user interface associated with
it.  

Global plugins are best suited for adding features to Ginga that
should operate "across channels"; i.e. some visible interface that
continuously updates itself in response to events happening in the
viewer.

The API for a global plugin is pretty simple.  This template shows the
relevant class definition::

    class Foo(GingaPlugin.GlobalPlugin):
        """
        NOTE: *** All these methods are running in the GUI thread, unless
        otherwise noted. Do not block!! ***  
        """
    
        def __init__(self, fv):
            super(Foo, self).__init__(fv)
    
            # Hereafter, in this object we can refer to:
            # self.fv -- the main Ginga control object
            # self.logger -- a logger
    
        def initialize(self, container):
            """This method will be called with a container widget if the global
            plugin was requested to be loaded into a workspace.  The plugin should
            construct its GUI and pack it into the container.  If there is
            no GUI for the global plugin this method can be omitted.
            """
            pass
    
        def start(self):
            """This method is called just after build_gui() when the plugin is
            activated (for global plugins this is usually at program start up).
            For global plugins this method can often be omitted.
            """
            pass
    
        def stop(self):
            """This method is called when the plugin is deactivated.
            For global plugins this method can usually be omitted.
            """
            pass
    
        def pause(self):
            """If present, this method can be called to defocus the plugin
            without stopping it.  
            For global plugins this method can usually be omitted.
            """
            pass
    
        def resume(self):
            """If present, this method can be called to focus the plugin
            subsequent to a previous pause() call.  
            For global plugins this method can usually be omitted.
            """
            pass

There is the object constructor, a `build_gui` method and `start` and
`stop` methods.  
Global plugins register with the main ginga object for events they
are interested in, like when a channel is added, or a new image arrives
in a channel, and define their own callbacks to deal with them.  This is
typically done in the constructor, although it can also be done in the
build_gui method.  The start, stop, pause and resume methods are
currently reserved for future use and can be omitted. 

The best way to learn how a global plugin interacts with the main Ginga
control object (represented by the `fv` parameter in the
constructor) is to examine some of the global plugins that ship with
Ginga.  Start with a simple one, like Header, and work up to more
complicated examples like Info.

.. _sec-writing-local-plugins:

======================
Writing a local plugin
======================

Local plugins are also more or less independent modules that are loaded
into Ginga at program startup, but there is a unique instance of a local
plugin for each channel.  Local plugins are also more tightly controlled
by Ginga: they create their user interface (if any) when the plugin
is activated, and it disappears when the plugin is deactivated.
Furthermore, while the plugin is activated it may lose or regain the
focus, which generally serves to multiplex the keyboard and mouse
operations amongst the different active local plugins.  
Local plugins are activated, deactivated and focus-controlled via the 
plugin manager bar that appears at the bottom of the main FITS window.

Here is a template for a local plugin.  As you can see, the API is a
little more complicated than for a global plugin, but not by much::

    class Goo(GingaPlugin.LocalPlugin):
        """
        NOTE: *** All these methods are running in the GUI thread, unless
        otherwise noted. Do not block!! ***  
        """
    
        def __init__(self, fv, fitsimage):
            super(Goo, self).__init__(fv, fitsimage)
    
            # Hereafter, in this object we can refer to:
            # self.fv -- the main Ginga control object
            # self.fitsimage -- the channel viewer object we are associated with
            # self.logger -- a logger
    
        # def build_gui(self, container):
        #     """If a plugin defines this method, it will be called with a
        #     container object in which to build its GUI. It should finish
        #     by packing into this container.  This will be called every
        #     time the local plugin is activated.
        #     """
        #     pass
    
        def start(self):
            """This method is called just after build_gui() when the plugin is
            activated.
            """
            pass
            
        def stop(self):
            """This method is called when the plugin is deactivated.
            """
            pass
    
        def pause(self):
            """This method is called when the plugin is defocused.  The plugin
            should disable any user input that it responds to.
            """
            pass
    
        def resume(self):
            """This method is called when the plugin is focused.  The plugin
            should enable any user input that it responds to.
            """
            pass
    
        def redo(self):
            """This method is called when a new image arrives in the channel
               associated with the plugin.  It can optionally redo
	       whatever operation it is doing.
            """
            pass

The best way to learn how a local plugin interacts with the main Ginga
control object (the `fv` parameter in the constructor) and the local
channel image (`fitsimage`) is to examine some of the local plugins
that ship with Ginga.  Start with a simple one, like Ruler or Drawing,
and work up to more complicated examples like Pick or Catalogs.

.. rubric:: Footnotes

.. [#f1] If the plugin is not listed in the default_tabs table
	 described in section :ref:`sec-workspaceconfig` it won't be
	 started at program startup. 
