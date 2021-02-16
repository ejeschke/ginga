# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
Keep track of buffer change history.

**Plugin Type: Global**

``ChangeHistory`` is a global plugin.  Only one instance can be opened.

This plugin is used to log any changes to data buffer. For example,
a change log would appear here if a new image is added to a mosaic via the
``Mosaic`` plugin. Like ``Contents``,
the log is sorted by channel, and then by image name.

**Usage**

History should stay no matter what channel or image is active.
New history can be added, but old history cannot be deleted,
unless the image/channel itself is deleted.

The ``redo()`` method picks up an ``'add-image-info'`` event and displays
related metadata here. The metadata is obtained as follows::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

Both ``'time_modified'`` and ``'reason_modified'`` have to be explicitly set
by the calling plugin in the same method that issues the
``'add-image-info'`` callback, like this::

        # This changes the data buffer
        image.set_data(new_data, ...)
        # Add description for ChangeHistory
        info = dict(time_modified=datetime.utcnow(),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)

"""
from ginga import GingaPlugin
from ginga.gw import Widgets
from ginga.misc import Bunch
from ginga.util.iohelper import shorten_name

__all__ = ['ChangeHistory']


class ChangeHistory(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(ChangeHistory, self).__init__(fv)

        self.columns = [('Timestamp (UTC)', 'MODIFIED'),
                        ('Description', 'DESCRIP'),
                        ]
        # For table-of-contents pane
        self.name_dict = Bunch.caselessDict()
        self.treeview = None

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_ChangeHistory')
        self.settings.add_defaults(always_expand=True,
                                   color_alternate_rows=True,
                                   ts_colwidth=250)
        self.settings.load(onError='silent')

        fv.add_callback('add-image-info', self.add_image_info_cb)
        fv.add_callback('remove-image-info', self.remove_image_info_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)

        self.gui_up = False

    def build_gui(self, container):
        """This method is called when the plugin is invoked.  It builds the
        GUI used by the plugin into the widget layout passed as
        ``container``.

        This method could be called several times if the plugin is opened
        and closed.

        """
        vbox, sw, self.orientation = Widgets.get_oriented_box(container,
                                                              orientation=self.settings.get('orientation', None))
        vbox.set_border_width(4)
        vbox.set_spacing(2)

        # create the Treeview
        always_expand = self.settings.get('always_expand', True)
        color_alternate = self.settings.get('color_alternate_rows', True)
        treeview = Widgets.TreeView(auto_expand=always_expand,
                                    sortable=True,
                                    use_alt_row_color=color_alternate)
        self.treeview = treeview
        treeview.setup_table(self.columns, 3, 'MODIFIED')
        treeview.set_column_width(0, self.settings.get('ts_colwidth', 250))
        treeview.add_callback('selected', self.show_more)
        vbox.add_widget(treeview, stretch=1)

        fr = Widgets.Frame('Selected History')

        captions = (('Channel:', 'label', 'chname', 'llabel'),
                    ('Image:', 'label', 'imname', 'llabel'),
                    ('Timestamp:', 'label', 'modified', 'llabel'))
        w, b = Widgets.build_info(captions)
        self.w.update(b)

        b.chname.set_text('')
        b.chname.set_tooltip('Channel name')

        b.imname.set_text('')
        b.imname.set_tooltip('Image name')

        b.modified.set_text('')
        b.modified.set_tooltip('Timestamp (UTC)')

        captions = (('Description:-', 'llabel'), ('descrip', 'textarea'))
        w2, b = Widgets.build_info(captions)
        self.w.update(b)

        b.descrip.set_editable(False)
        b.descrip.set_wrap(True)
        b.descrip.set_text('')
        b.descrip.set_tooltip('Displays selected history entry')

        vbox2 = Widgets.VBox()
        vbox2.set_border_width(4)
        vbox2.add_widget(w)
        vbox2.add_widget(w2)

        fr.set_widget(vbox2, stretch=0)
        vbox.add_widget(fr, stretch=0)

        container.add_widget(vbox, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(3)

        btn = Widgets.Button('Close')
        btn.add_callback('activated', lambda w: self.close())
        btns.add_widget(btn, stretch=0)
        btn = Widgets.Button("Help")
        btn.add_callback('activated', lambda w: self.help())
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        container.add_widget(btns, stretch=0)

        self.gui_up = True

    def clear_selected_history(self):
        if not self.gui_up:
            return

        self.w.chname.set_text('')
        self.w.imname.set_text('')
        self.w.modified.set_text('')
        self.w.descrip.set_text('')

    def recreate_toc(self):
        self.logger.debug("Recreating table of contents...")
        self.treeview.set_tree(self.name_dict)

    def show_more(self, widget, res_dict):
        try:
            chname = list(res_dict.keys())[0]
            img_dict = res_dict[chname]
            imname = list(img_dict.keys())[0]
            entries = img_dict[imname]
            timestamp = list(entries.keys())[0]
            bnch = entries[timestamp]
        except Exception:  # The drop-down row is selected, nothing to show
            return

        # Display on GUI
        self.w.chname.set_text(chname)
        self.w.imname.set_text(shorten_name(imname, 25))
        self.w.modified.set_text(timestamp)
        self.w.descrip.set_text(bnch.DESCRIP)

    def redo(self, channel, image):
        """Add an entry with image modification info."""
        chname = channel.name
        if image is None:
            # shouldn't happen, but let's play it safe
            return

        imname = image.get('name', 'none')
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified

        if timestamp is None:
            reason = iminfo.get('reason_modified', None)
            if reason is not None:
                self.fv.show_error(
                    "{0} invoked 'modified' callback to ChangeHistory with a "
                    "reason but without a timestamp. The plugin invoking the "
                    "callback is no longer be compatible with Ginga. "
                    "Please contact plugin developer to update the plugin "
                    "to use self.fv.update_image_info() like Mosaic "
                    "plugin.".format(imname))

            # Image somehow lost its history
            self.remove_image_info_cb(self.fv, channel, iminfo)
            return

        self.add_entry(chname, iminfo)

    def add_entry(self, chname, iminfo):

        # Add info to internal log
        if chname not in self.name_dict:
            self.name_dict[chname] = {}

        fileDict = self.name_dict[chname]

        imname = iminfo.name
        if imname not in fileDict:
            fileDict[imname] = {}

        # Z: Zulu time, GMT, UTC
        timestamp = iminfo.time_modified
        timestamp = timestamp.strftime('%Y-%m-%dZ %H:%M:%SZ')
        reason = iminfo.get('reason_modified', 'Not given')
        bnch = Bunch.Bunch(CHNAME=chname, NAME=imname, MODIFIED=timestamp,
                           DESCRIP=reason)
        entries = fileDict[imname]

        # timestamp is guaranteed to be unique?
        entries[timestamp] = bnch

        self.logger.debug("Added history for chname='{0}' imname='{1}' "
                          "timestamp='{2}'".format(chname, imname, timestamp))

        if self.gui_up:
            self.recreate_toc()

    def remove_image_info_cb(self, gshell, channel, iminfo):
        """Delete entries related to deleted image."""
        chname = channel.name
        if chname not in self.name_dict:
            return

        fileDict = self.name_dict[chname]

        name = iminfo.name
        if name not in fileDict:
            return

        del fileDict[name]
        self.logger.debug('{0} removed from ChangeHistory'.format(name))

        if not self.gui_up:
            return False

        self.clear_selected_history()
        self.recreate_toc()

    def add_image_info_cb(self, gshell, channel, iminfo):
        """Add entries related to an added image."""

        timestamp = iminfo.time_modified
        if timestamp is None:
            # Not an image we are interested in tracking
            return

        self.add_entry(channel.name, iminfo)

    def delete_channel_cb(self, gshell, chinfo):
        """Called when a channel is deleted from the main interface.
        Parameter is chinfo (a bunch)."""
        chname = chinfo.name

        if chname not in self.name_dict:
            return

        del self.name_dict[chname]
        self.logger.debug('{0} removed from ChangeHistory'.format(chname))

        if not self.gui_up:
            return False

        self.clear_selected_history()
        self.recreate_toc()

    def clear(self):
        self.name_dict = Bunch.caselessDict()
        self.clear_selected_history()
        self.recreate_toc()

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def stop(self):
        self.gui_up = False
        self.fv.show_status('')

    def start(self):
        self.recreate_toc()

    def __str__(self):
        return 'changehistory'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_ChangeHistory', package='ginga')
