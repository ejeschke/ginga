# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""
The ``Contents`` plugin provides a table of contents-like interface for all
the images viewed since the program was started.  Unlike ``Thumbs``,
``Contents`` is sorted by channel.  The contents also shows some configurable
metadata from the image.

**Plugin Type: Global**

``Contents`` is a global plugin.  Only one instance can be opened.

**Usage**

Click on a column heading to sort the table by that column;
Click again to sort the other way.

.. note:: The columns and their values are drawn from the FITS header,
          if applicable.
          This can be customized by setting the "columns" parameter in
          the "plugin_Contents.cfg" settings file.

The active image in the currently focused channel will normally be
highlighted. Double-click on an image will force that image to be
shown in the associated channel. Single-click on any image to
activate the buttons at the bottom of the UI:

* "Display": Make the image the active image.
* "Move": Move the image to another channel.
* "Copy": Copy the image to another channel.
* "Remove": Remove the image from the channel.

If "Move" or "Copy" is done on an image that has been modified in Ginga
(which would have an entry under ``ChangeHistory``, if used), the
modification history will be retained as well. Removing an image from
a channel destroys any unsaved changes.

This plugin is not usually configured to be closeable, but the user can
make it so by setting the "closeable" setting to True in the configuration
file--then Close and Help buttons will be added to the bottom of the UI.

**Excluding images from Contents**

.. note:: This also controls the behavior of ``Thumbs``.

Although the default behavior is for every image that is loaded into the
reference viewer to show up in ``Contents``, there may be cases where this
is undesirable (e.g., when there are many images being loaded at a
periodic rate by some automated process).  In such cases there are two
mechanisms for suppressing certain images from showing up in ``Contents``:

* Assigning the "genthumb" setting to False in a channel's settings
  (for example from the ``Preferences`` plugin, under the "General"
  settings) will exclude the channel itself and any of its images.
* Setting the "nothumb" keyword in the metadata of an image wrapper
  (not the FITS header, but by e.g., ``image.set(nothumb=True)``)
  will exclude that particular image from ``Contents``, even if the
  "genthumb" setting is True for that channel.

"""
from ginga import GingaPlugin
from ginga.misc import Bunch

from ginga.gw import Widgets

__all__ = ['Contents']


class Contents(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(Contents, self).__init__(fv)

        columns = [('Name', 'NAME'), ('Object', 'OBJECT'),
                   ('Date', 'DATE-OBS'), ('Time UT', 'UT'),
                   ('Modified', 'MODIFIED')]

        spec = self.fv.get_plugin_spec(str(self))

        prefs = self.fv.get_preferences()
        self.settings = prefs.create_category('plugin_Contents')
        self.settings.add_defaults(columns=columns,
                                   always_expand=True,
                                   highlight_tracks_keyboard_focus=True,
                                   color_alternate_rows=True,
                                   row_font_color='green',
                                   closeable=not spec.get('hidden', False),
                                   max_rows_for_col_resize=100)
        self.settings.load(onError='silent')

        # For table-of-contents pane
        self.name_dict = Bunch.caselessDict()
        # TODO: this ought to be customizable by channel
        self.columns = self.settings.get('columns', columns)
        self.treeview = None
        # paths of highlighted entries, by channel
        self.highlight_tracks_keyboard_focus = self.settings.get(
            'highlight_tracks_keyboard_focus', True)
        self._hl_path = set([])
        self.chnames = []

        fv.add_callback('add-image', self.add_image_cb)
        fv.add_callback('remove-image', self.remove_image_cb)
        fv.add_callback('add-image-info', self.add_image_info_cb)
        fv.add_callback('remove-image-info', self.remove_image_info_cb)
        fv.add_callback('add-channel', self.add_channel_cb)
        fv.add_callback('delete-channel', self.delete_channel_cb)
        fv.add_callback('channel-change', self.focus_cb)

        self.gui_up = False

    def build_gui(self, container):
        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(4)

        # create the Treeview
        always_expand = self.settings.get('always_expand', False)
        color_alternate = self.settings.get('color_alternate_rows', True)
        treeview = Widgets.TreeView(auto_expand=always_expand,
                                    sortable=True,
                                    selection='multiple',
                                    use_alt_row_color=color_alternate)
        self.treeview = treeview
        treeview.setup_table(self.columns, 2, 'NAME')

        treeview.add_callback('activated', self.dblclick_cb)
        treeview.add_callback('selected', self.select_cb)
        vbox.add_widget(treeview, stretch=1)

        btns = Widgets.HBox()
        btns.set_spacing(4)
        b1 = Widgets.Button('Display')
        b1.add_callback('activated', self.display_cb)
        b1.set_tooltip("Display the selected object in its channel viewer")
        b1.set_enabled(False)
        btns.add_widget(b1)
        b2 = Widgets.Button('Move')
        b2.add_callback('activated', lambda w: self.ask_action_images('move'))
        b2.set_tooltip("Move the selected objects to a channel")
        b2.set_enabled(False)
        btns.add_widget(b2)
        b3 = Widgets.Button('Copy')
        b3.add_callback('activated', lambda w: self.ask_action_images('copy'))
        b3.set_tooltip("Copy the selected objects to a channel")
        b3.set_enabled(False)
        btns.add_widget(b3)
        b4 = Widgets.Button('Remove')
        b4.add_callback('activated', lambda w: self.ask_action_images('remove'))
        b4.set_tooltip("Remove the selected objects from a channel")
        b4.set_enabled(False)
        btns.add_widget(b4)
        btns.add_widget(Widgets.Label(''), stretch=1)
        self.btn_list = [b1, b2, b3, b4]

        self._rebuild_channels()

        vbox.add_widget(btns, stretch=0)

        if self.settings.get('closeable', False):
            btns = Widgets.HBox()
            btns.set_border_width(4)
            btns.set_spacing(4)

            btn = Widgets.Button("Close")
            btn.add_callback('activated', lambda w: self.close())
            btns.add_widget(btn)
            btn = Widgets.Button("Help")
            btn.add_callback('activated', lambda w: self.help())
            btns.add_widget(btn, stretch=0)
            btns.add_widget(Widgets.Label(''), stretch=1)
            vbox.add_widget(btns, stretch=0)

        container.add_widget(vbox, stretch=1)
        self.gui_up = True

    def get_selected(self):
        res = []
        res_dict = self.treeview.get_selected()
        if len(res_dict) == 0:
            return res
        for chname in res_dict.keys():
            img_dict = res_dict[chname]
            if len(img_dict) == 0:
                continue
            for imname in img_dict.keys():
                bnch = img_dict[imname]
                res.append((chname, bnch))
        return res

    def dblclick_cb(self, widget, d):
        chname = list(d.keys())[0]
        names = list(d[chname].keys())
        if len(names) == 0:
            # empty channel
            return
        imname = names[0]
        bnch = d[chname][imname]
        if 'node' in bnch.keys():
            # double-clicked on header
            return
        path = bnch.path
        self.logger.debug("chname=%s name=%s path=%s" % (
            chname, imname, path))

        self.fv.switch_name(chname, imname, path=path,
                            image_future=bnch.image_future)

    def select_cb(self, widget, d):
        res = self.get_selected()
        tf = (len(res) > 0)
        for btn in self.btn_list:
            btn.set_enabled(tf)

    def display_cb(self, widget):
        res = self.get_selected()
        if len(res) != 1:
            self.fv.show_error("Please select just one file to display!")
            return

        chname, bnch = res[0]

        if 'path' not in bnch:
            # may be a top-level channel node, e.g. in gtk
            return
        path = bnch.path
        imname = bnch.imname
        self.logger.debug("chname=%s name=%s path=%s" % (
            chname, imname, path))

        self.fv.switch_name(chname, imname, path=path,
                            image_future=bnch.image_future)

    def get_info(self, chname, name, image, info):
        path = info.get('path', None)
        future = info.get('image_future', None)

        bnch = Bunch.Bunch(CHNAME=chname, imname=name, path=path,
                           image_future=future)

        # Get header keywords of interest
        if image is not None:
            header = image.get_header()
        else:
            header = {}

        for hdr, key in self.columns:
            bnch[key] = str(header.get(key, 'N/A'))

        # name should always be available
        bnch.NAME = name

        # Modified timestamp will be set if image data is modified
        timestamp = info.time_modified
        if timestamp is not None:
            # Z: Zulu time, GMT, UTC
            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%SZ')
        bnch.MODIFIED = timestamp

        return bnch

    def recreate_toc(self):
        self.logger.debug("Recreating table of contents...")
        self.treeview.set_tree(self.name_dict)

        # re-highlight as necessary
        if self.highlight_tracks_keyboard_focus:
            new_highlight = self._hl_path
        else:
            new_highlight = set([])
            for chname in self.name_dict:
                channel = self.fv.get_channel_info(chname)
                new_highlight |= channel.extdata.contents_old_highlight
        self.update_highlights(set([]), new_highlight)

        # Resize column widths
        n_rows = sum(map(len, self.name_dict.values()))
        if n_rows < self.settings.get('max_rows_for_col_resize', 100):
            self.treeview.set_optimal_column_widths()
            self.logger.debug("Resized columns for {0} row(s)".format(n_rows))

    def is_in_contents(self, chname, imname):
        if chname not in self.name_dict:
            return False

        file_dict = self.name_dict[chname]
        if imname not in file_dict:
            return False

        return True

    def add_image_cb(self, viewer, chname, image, image_info):
        name = image_info.name
        self.logger.debug("name=%s" % (name))

        if image is not None:
            channel = self.fv.get_channel(chname)
            nothumb = (image.get('nothumb', False) or
                       not channel.settings.get('genthumb', True))
            if nothumb:
                return

        bnch = self.get_info(chname, name, image, image_info)

        if chname not in self.name_dict:
            # channel does not exist yet in contents
            # Note: this typically shouldn't happen, because add_channel_cb()
            # will have added an empty dict
            file_dict = {}
            self.name_dict[chname] = file_dict
        else:
            file_dict = self.name_dict[chname]

        if name not in file_dict:
            # new image
            file_dict[name] = bnch
        else:
            # old image
            file_dict[name].update(bnch)

        if self.gui_up:
            # TODO: either make add_tree() merge updates or make an
            #    update_tree() method--shouldn't need to recreate entire
            #    tree, just add new entry and possibly rehighlight
            ## tree_dict = { chname: { name: bnch } }
            ## self.treeview.add_tree(tree_dict)
            self.recreate_toc()

        self.logger.debug("%s added to Contents" % (name))

    def add_image_info_cb(self, viewer, channel, image_info):
        """Almost the same as add_image_cb(), except that the image
        may not be loaded in memory.
        """
        if not channel.settings.get('genthumb', True):
            return

        chname = channel.name
        name = image_info.name
        self.logger.debug("name=%s" % (name))

        # Updates of any extant information
        try:
            image = channel.get_loaded_image(name)
        except KeyError:
            # images that are not yet loaded will show "N/A" for keywords
            image = None

        self.add_image_cb(viewer, chname, image, image_info)

    def remove_image_cb(self, viewer, chname, name, path):
        if not self.gui_up:
            return False

        if chname not in self.name_dict:
            return

        file_dict = self.name_dict[chname]

        if name not in file_dict:
            return

        del file_dict[name]

        # Unhighlight
        channel = self.fv.get_channel_info(chname)
        key = (chname, name)
        self._hl_path.discard(key)
        channel.extdata.contents_old_highlight.discard(key)

        if self.gui_up:
            self.recreate_toc()
        self.logger.debug("%s removed from Contents" % (name))

    def remove_image_info_cb(self, viewer, channel, image_info):
        """Almost the same as remove_image_cb().
        """
        return self.remove_image_cb(viewer, channel.name,
                                    image_info.name, image_info.path)

    def clear(self):
        self.name_dict = Bunch.caselessDict()
        self._hl_path = set([])
        if self.gui_up:
            self.recreate_toc()

    def add_channel_cb(self, viewer, channel):
        """Called when a channel is added from the main interface.
        Parameter is a channel (a Channel object)."""
        if not channel.settings.get('genthumb', True):
            return

        chname = channel.name

        # add old highlight set to channel external data
        channel.extdata.setdefault('contents_old_highlight', set([]))

        # Add the channel to the treeview
        file_dict = {}
        self.name_dict.setdefault(chname, file_dict)

        if not self.gui_up:
            return False

        tree_dict = {chname: {}}
        if self.gui_up:
            self.treeview.add_tree(tree_dict)

        self._rebuild_channels()

    def delete_channel_cb(self, viewer, channel):
        """Called when a channel is deleted from the main interface.
        Parameter is a channel (a Channel object)."""
        if not channel.settings.get('genthumb', True):
            return

        chname = channel.name
        del self.name_dict[chname]

        # Unhighlight
        un_hilite_set = set([])
        for path in self._hl_path:
            if path[0] == chname:
                un_hilite_set.add(path)
        self._hl_path -= un_hilite_set

        if self.gui_up:
            self.recreate_toc()

        self._rebuild_channels()

    def _rebuild_channels(self):
        self.chnames = self.fv.get_channel_names()

    def _get_hl_key(self, chname, image):
        return (chname, image.get('name', 'none'))

    def _highlight_path(self, hl_path, tf):
        """Highlight or unhighlight a single entry.

        Examples
        --------
        >>> hl_path = self._get_hl_key(chname, image)
        >>> self._highlight_path(hl_path, True)

        """
        fc = self.settings.get('row_font_color', 'green')

        try:
            self.treeview.highlight_path(hl_path, tf, font_color=fc)
        except Exception as e:
            self.logger.info('Error changing highlight on treeview path '
                             '({0}): {1}'.format(hl_path, str(e)))

    def update_highlights(self, old_highlight_set, new_highlight_set):
        """Unhighlight the entries represented by ``old_highlight_set``
        and highlight the ones represented by ``new_highlight_set``.

        Both are sets of keys.

        """
        if not self.gui_up:
            return

        un_hilite_set = old_highlight_set - new_highlight_set
        re_hilite_set = new_highlight_set - old_highlight_set

        # unhighlight entries that should NOT be highlighted any more
        for key in un_hilite_set:
            self._highlight_path(key, False)

        # highlight new entries that should be
        for key in re_hilite_set:
            self._highlight_path(key, True)

    def redo(self, channel, image):
        """This method is called when an image is set in a channel."""
        if not channel.settings.get('genthumb', True):
            return

        imname = image.get('name', 'none')
        chname = channel.name
        # is image in contents tree yet?
        in_contents = self.is_in_contents(chname, imname)

        # get old highlighted entries for this channel -- will be
        # an empty set or one key
        old_highlight = channel.extdata.contents_old_highlight

        # calculate new highlight keys -- again, an empty set or one key
        if image is not None:
            key = self._get_hl_key(chname, image)
            new_highlight = set([key])
        else:
            # no image has the focus
            new_highlight = set([])

        # Only highlights active image in the current channel
        if self.highlight_tracks_keyboard_focus:
            if in_contents:
                self.update_highlights(self._hl_path, new_highlight)
            self._hl_path = new_highlight

        # Highlight all active images in all channels
        else:
            if in_contents:
                self.update_highlights(old_highlight, new_highlight)
            channel.extdata.contents_old_highlight = new_highlight

        return True

    def focus_cb(self, viewer, channel):
        if not self.gui_up:
            return False

        chname = channel.name
        image = channel.get_current_image()

        if image is not None:
            key = self._get_hl_key(chname, image)
            new_highlight = set([key])
        else:
            # no image has the focus
            new_highlight = set([])

        if self.highlight_tracks_keyboard_focus:
            self.update_highlights(self._hl_path, new_highlight)
            self._hl_path = new_highlight

    def ask_action_images(self, action):

        images = self.get_selected()
        if len(images) == 0:
            self.fv.show_error("Please select some images first")
            return

        l_img = ["%s/%s" % (tup[0], tup[1].imname) for tup in images]

        verb = action.capitalize()
        l_img.insert(0, "%s images\n" % (verb))

        # build dialog
        dialog = Widgets.Dialog(title="%s Images" % (verb),
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.treeview)
        box = dialog.get_content_area()
        box.set_border_width(6)
        if len(l_img) < 12:
            text = Widgets.Label("\n".join(l_img))
        else:
            text = Widgets.TextArea(wrap=None)
            text.set_text("\n".join(l_img))
        box.add_widget(text, stretch=1)

        if action != 'remove':
            hbox = Widgets.HBox()
            hbox.add_widget(Widgets.Label("To channel: "))
            chnl = Widgets.ComboBox()
            for chname in self.chnames:
                chnl.append_text(chname)
            hbox.add_widget(chnl)
            hbox.add_widget(Widgets.Label(''), stretch=1)
            box.add_widget(hbox)
        else:
            chnl = None

        dialog.add_callback('activated',
                            lambda w, rsp: self.action_images_cb(w, rsp,
                                                                 chnl,
                                                                 images,
                                                                 action))

        self.fv.ds.show_dialog(dialog)

    def action_images_cb(self, w, rsp, chnl_w, images, action):
        # dst channel
        if chnl_w is not None:
            idx = chnl_w.get_index()
            chname = self.chnames[idx]
            dst_channel = self.fv.get_channel(chname)

        self.fv.ds.remove_dialog(w)
        if rsp == 0:
            # user canceled
            return

        for chname, info in images:
            src_channel = self.fv.get_channel(chname)
            if action == 'copy':
                src_channel.copy_image_to(info.imname, dst_channel)
            elif action == 'move':
                src_channel.move_image_to(info.imname, dst_channel)
            elif action == 'remove':
                src_channel.remove_image(info.imname)

    def start(self):
        self.recreate_toc()

    def stop(self):
        self.treeview = None
        self.gui_up = False

    def close(self):
        self.fv.stop_global_plugin(str(self))
        return True

    def __str__(self):
        return 'contents'


# Append module docstring with config doc for auto insert by Sphinx.
from ginga.util.toolbox import generate_cfg_example  # noqa
if __doc__ is not None:
    __doc__ += generate_cfg_example('plugin_Contents', package='ginga')

# END
