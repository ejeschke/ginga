"""
Skeleton example of a Ginga global plugin called 'MyGlobalPlugin'

To enable it, run ginga with the command
    $ ginga --modules=MyLocalPlugin

it should become active in the right panel.
"""

from ginga import GingaPlugin
from ginga.gw import Widgets

# import any other modules you want here--it's a python world!

class MyGlobalPlugin(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        """
        This method is called when the plugin is loaded for the  first
        time.  ``fv`` is a reference to the Ginga (reference viewer) shell.

        You need to call the superclass initializer and then do any local
        initialization.
        """
        super(MyGlobalPlugin, self).__init__(fv)

        # Your initialization here

        # Create some variables to keep track of what is happening
        # with which channel
        self.active = None

        # Subscribe to some interesting callbacks that will inform us
        # of channel events.  You may not need these depending on what
        # your plugin does
        fv.set_callback('add-channel', self.add_channel)
        fv.set_callback('delete-channel', self.delete_channel)
        fv.set_callback('active-image', self.focus_cb)

    def build_gui(self, container):
        """
        This method is called when the plugin is invoked.  It builds the
        GUI used by the plugin into the widget layout passed as
        ``container``.
        This method could be called several times if the plugin is opened
        and closed.  The method may be omitted if there is no GUI for the
        plugin.

        This specific example uses the GUI widget set agnostic wrappers
        to build the GUI, but you can also just as easily use explicit
        toolkit calls here if you only want to support one widget set.
        """
        top = Widgets.VBox()
        top.set_border_width(4)

        # this is a little trick for making plugins that work either in
        # a vertical or horizontal orientation.  It returns a box container,
        # a scroll widget and an orientation ('vertical', 'horizontal')
        vbox, sw, orientation = Widgets.get_oriented_box(container)
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        # Take a text widget to show some instructions
        self.msgFont = self.fv.getFont("sansFont", 12)
        tw = Widgets.TextArea(wrap=True, editable=False)
        tw.set_font(self.msgFont)
        self.tw = tw

        # Frame for instructions and add the text widget with another
        # blank widget to stretch as needed to fill emp
        fr = Widgets.Frame("Status")
        fr.set_widget(tw)
        vbox.add_widget(fr, stretch=0)

        # Add a spacer to stretch the rest of the way to the end of the
        # plugin space
        spacer = Widgets.Label('')
        vbox.add_widget(spacer, stretch=1)

        # scroll bars will allow lots of content to be accessed
        top.add_widget(sw, stretch=1)

        # A button box that is always visible at the bottom
        btns = Widgets.HBox()
        btns.set_spacing(3)

        # Add a close button for the convenience of the user
        btn = Widgets.Button("Close")
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)
        top.add_widget(btns, stretch=0)

        # Add our GUI to the container
        container.add_widget(top, stretch=1)
        # NOTE: if you are building a GUI using a specific widget toolkit
        # (e.g. Qt) GUI calls, you need to extract the widget or layout
        # from the non-toolkit specific container wrapper and call on that
        # to pack your widget, e.g.:
        #cw = container.get_widget()
        #cw.addWidget(widget, stretch=1)

    def get_channel_info(self, fitsimage):
        chname = self.fv.get_channelName(fitsimage)
        chinfo = self.fv.get_channelInfo(chname)
        return chinfo

    def set_info(self, text):
        self.tw.set_text(text)

    # CALLBACKS

    def add_channel(self, viewer, chinfo):
        """
        Callback from the reference viewer shell when a channel is added.
        """
        self.set_info("Channel '%s' has been added" % (
                chinfo.name))
        # Register for new image callbacks on this channel's canvas
        fitsimage = chinfo.fitsimage
        fitsimage.set_callback('image-set', self.new_image_cb)

    def delete_channel(self, viewer, chinfo):
        """
        Callback from the reference viewer shell when a channel is deleted.
        """
        self.set_info("Channel '%s' has been deleted" % (
                chinfo.name))
        return True

    def focus_cb(self, viewer, fitsimage):
        """
        Callback from the reference viewer shell when the focus changes
        between channels.
        """
        chinfo = self.get_channel_info(fitsimage)
        chname = chinfo.name

        if self.active != chname:
            # focus has shifted to a different channel than our idea
            # of the active one
            self.active = chname
            self.set_info("Focus is now in channel '%s'" % (
                self.active))
        return True

    def new_image_cb(self, fitsimage, image):
        """
        Callback from the reference viewer shell when a new image has
        been added to a channel.
        """
        chinfo = self.get_channel_info(fitsimage)
        chname = chinfo.name

        # Only update our GUI if the activity is in the focused
        # channel
        if self.active == chname:
            imname = image.get('name', 'NONAME')
            self.set_info("A new image '%s' has been added to channel %s" % (
                imname, chname))
        return True

    def start(self):
        """
        This method is called just after ``build_gui()`` when the plugin
        is invoked.  This method could be called more than once if the
        plugin is opened and closed.  This method may be omitted
        in many cases.
        """
        pass

    def stop(self):
        """
        This method is called when the plugin is stopped.
        It should perform any special clean up necessary to terminate
        the operation.  This method could be called more than once if
        the plugin is opened and closed, and may be omitted if there is no
        special cleanup required when stopping.
        """
        pass

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        """
        This method should be provided and should return the lower case
        name of the plugin.
        """
        return 'myglobalplugin'
