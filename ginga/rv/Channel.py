#
# Channel.py -- Channel class for the Ginga reference viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
from datetime import datetime

from ginga.misc import Bunch, Datasrc, Callback, Future


class ChannelError(Exception):
    pass


class Channel(Callback.Callbacks):
    """Class to manage a channel.

    Parameters
    ----------
    name : str
        Name of the channel.

    fv : `~ginga.rv.Control.GingaShell`
        The reference viewer shell.

    settings : `~ginga.misc.Settings.SettingGroup`
        Channel settings.

    datasrc : `~ginga.misc.Datasrc.Datasrc`
        Data cache.

    """
    def __init__(self, name, fv, settings, datasrc=None):
        super(Channel, self).__init__()

        self.logger = fv.logger
        self.fv = fv
        self.settings = settings
        self.logger = fv.logger

        # CHANNEL ATTRIBUTES
        self.name = name
        self.widget = None
        self.container = None
        self.workspace = None
        self.opmon = None
        # this is the image viewer we are connected to
        self.fitsimage = None
        # this is the currently active viewer
        self.viewer = None
        self.viewers = []
        self.viewer_dict = {}
        if datasrc is None:
            num_images = self.settings.get('numImages', 1)
            datasrc = Datasrc.Datasrc(num_images)
        self.datasrc = datasrc
        self.cursor = -1
        self.history = []
        self.image_index = {}
        # external entities can attach stuff via this attribute
        self.extdata = Bunch.Bunch()

        self._configure_sort()
        self.settings.get_setting('sort_order').add_callback(
            'set', self._sort_changed_ext_cb)

    def connect_viewer(self, viewer):
        if viewer not in self.viewers:
            self.viewers.append(viewer)
            self.viewer_dict[viewer.vname] = viewer

    def move_image_to(self, imname, channel):
        if self == channel:
            return

        self.copy_image_to(imname, channel)
        self.remove_image(imname)

    def copy_image_to(self, imname, channel, silent=False):
        if self == channel:
            return

        if imname in channel:
            # image with that name is already there
            return

        # transfer image info
        info = self.image_index[imname]
        was_not_there_already = channel._add_info(info)

        try:
            image = self.datasrc[imname]

        except KeyError:
            return

        if was_not_there_already:
            channel.datasrc[imname] = image
            image.add_callback('modified', channel._image_modified_cb)

            if not silent:
                self.fv.gui_do(channel._add_image_update, image, info)

    def remove_image(self, imname):
        info = self.image_index[imname]
        self.remove_history(imname)

        if imname in self.datasrc:
            image = self.datasrc[imname]
            self.datasrc.remove(imname)

            # update viewer if we are removing the currently displayed image
            cur_image = self.viewer.get_image()
            if cur_image == image:
                self.refresh_cursor_image()

        self.fv.make_async_gui_callback('remove-image', self.name,
                                        info.name, info.path)

        return info

    def get_image_names(self):
        return [info.name for info in self.history]

    def get_loaded_image(self, imname):
        """Get an image from memory.

        Parameters
        ----------
        imname : str
            Key, usually image name and extension.

        Returns
        -------
        image
            Image object.

        Raises
        ------
        KeyError
            Image is not in memory.

        """
        image = self.datasrc[imname]
        return image

    def add_image(self, image, silent=False, bulk_add=False):

        imname = image.get('name', None)
        if imname is None:
            raise ValueError("image has no name")

        self.logger.debug("Adding image '%s' in channel %s" % (
            imname, self.name))

        self.datasrc[imname] = image

        # Has this image been loaded into a channel before?
        info = image.get('image_info', None)
        if info is None:
            # No
            idx = image.get('idx', None)
            path = image.get('path', None)
            image_loader = image.get('image_loader', None)
            image_future = image.get('image_future', None)
            info = self.add_history(imname, path,
                                    image_loader=image_loader,
                                    image_future=image_future,
                                    idx=idx)
            image.set(image_info=info)

        # we'll get notified if an image changes and can update
        # metadata and make a chained callback
        image.add_callback('modified', self._image_modified_cb)

        if not silent:
            if not bulk_add:
                self._add_image_update(image, info)
                return

            # By using gui_do() here, more images may be bulk added
            # before the _add_image_update executes--it will then
            # only update the gui for the latest image, which saves
            # work
            self.fv.gui_do(self._add_image_update, image, info)

    def add_image_info(self, info):

        image_loader = info.get('image_loader', self.fv.load_image)

        # create an image_future if one does not exist
        image_future = info.get('image_future', None)
        if (image_future is None) and (info.path is not None):
            image_future = Future.Future()
            image_future.freeze(image_loader, info.path)

        info = self.add_history(info.name, info.path,
                                image_loader=image_loader,
                                image_future=image_future)

    def get_image_info(self, imname):
        return self.image_index[imname]

    def _add_image_update(self, image, info):
        self.fv.make_async_gui_callback('add-image', self.name, image, info)

        current = self.datasrc.youngest()
        curname = current.get('name')
        self.logger.debug("image=%s youngest=%s" % (image.get('name'), curname))
        if current != image:
            return

        # switch to current image?
        if self.settings['switchnew']:
            self.logger.debug("switching to new image '%s'" % (curname))
            self.switch_image(image)

        if self.settings['raisenew']:
            channel = self.fv.get_current_channel()
            if channel != self:
                self.fv.change_channel(self.name)

    def _image_modified_cb(self, image):
        imname = image.get('name', None)
        if (imname is None) or (imname not in self.image_index):
            # not one of ours apparently (maybe used to be, but got removed)
            return

        info = self.image_index[imname]
        info.time_modified = datetime.utcnow()
        self.logger.debug("image modified; making chained callback")

        self.fv.make_async_gui_callback('add-image-info', self, info)

    def refresh_cursor_image(self):
        if self.cursor < 0:
            self.viewer.clear()
            self.fv.channel_image_updated(self, None)
            return

        info = self.history[self.cursor]
        if info.name in self.datasrc:
            # image still in memory
            image = self.datasrc[info.name]
            self.switch_image(image)

        else:
            self.switch_name(info.name)

    def prev_image(self, loop=True):
        self.logger.debug("Previous image")
        if self.cursor <= 0:
            n = len(self.history) - 1
            if (not loop) or (n < 0):
                self.logger.error("No previous image!")
                return True
            self.cursor = n
        else:
            self.cursor -= 1

        self.refresh_cursor_image()

        return True

    def next_image(self, loop=True):
        self.logger.debug("Next image")
        n = len(self.history) - 1
        if self.cursor >= n:
            if (not loop) or (n < 0):
                self.logger.error("No next image!")
                return True
            self.cursor = 0
        else:
            self.cursor += 1

        self.refresh_cursor_image()

        return True

    def _add_info(self, info):
        if info in self.image_index:
            # image info is already present
            return False

        self.history.append(info)
        self.image_index[info.name] = info

        if self.hist_sort is not None:
            self.history.sort(key=self.hist_sort)

        self.fv.make_async_gui_callback('add-image-info', self, info)

        # image was newly added
        return True

    def add_history(self, imname, path, idx=None,
                    image_loader=None, image_future=None):

        if not (imname in self.image_index):

            if image_loader is None:
                image_loader = self.fv.load_image
            # create an image_future if one does not exist
            if (image_future is None) and (path is not None):
                image_future = Future.Future()
                image_future.freeze(image_loader, path)

            info = Bunch.Bunch(name=imname, path=path,
                               idx=idx,
                               image_loader=image_loader,
                               image_future=image_future,
                               time_added=time.time(),
                               time_modified=None)
            self._add_info(info)

        else:
            # already in history
            info = self.image_index[imname]

        return info

    def remove_history(self, imname):
        if imname in self.image_index:
            info = self.image_index[imname]
            del self.image_index[imname]
            i = self.history.index(info)
            self.history.remove(info)

            # adjust cursor as necessary
            if i < self.cursor:
                self.cursor -= 1
            if self.cursor >= len(self.history):
                # loop
                self.cursor = min(0, len(self.history) - 1)

            self.fv.make_async_gui_callback('remove-image-info', self, info)

    def get_current_image(self):
        return self.viewer.get_image()

    def view_object(self, dataobj):

        # find available viewers that can view this kind of object
        vnames = self.fv.get_viewer_names(dataobj)
        if len(vnames) == 0:
            raise ValueError("I don't know how to view objects of type '%s'" % (
                str(type(dataobj))))
        self.logger.debug("available viewers are: %s" % (str(vnames)))

        # for now, pick first available viewer that can view this type
        vname = vnames[0]

        # if we don't have this viewer type then install one in the channel
        if vname not in self.viewer_dict:
            self.fv.make_viewer(vname, self)

        self.viewer = self.viewer_dict[vname]
        # find this viewer and raise it
        idx = self.viewers.index(self.viewer)
        self.widget.set_index(idx)

        # and load the data
        self.viewer.set_image(dataobj)

    def switch_image(self, image):

        curimage = self.get_current_image()
        if curimage != image:
            self.logger.debug("updating viewer...")
            self.view_object(image)

            # update cursor to match image
            imname = image.get('name')
            if imname in self.image_index:
                info = self.image_index[imname]
                if info in self.history:
                    self.cursor = self.history.index(info)

            self.fv.channel_image_updated(self, image)

            # Check for preloading any images into memory
            preload = self.settings.get('preload_images', False)
            if not preload:
                return

            # queue next and previous files for preloading
            index = self.cursor
            if index < len(self.history) - 1:
                info = self.history[index + 1]
                if info.path is not None:
                    self.fv.add_preload(self.name, info)

            if index > 0:
                info = self.history[index - 1]
                if info.path is not None:
                    self.fv.add_preload(self.name, info)

        else:
            self.logger.debug("Apparently no need to set channel viewer.")

    def switch_name(self, imname):

        if imname in self.datasrc:
            # Image is still in the heap
            image = self.datasrc[imname]
            self.switch_image(image)
            return

        if not (imname in self.image_index):
            errmsg = "No image by the name '%s' found" % (imname)
            self.logger.error("Can't switch to image '%s': %s" % (
                imname, errmsg))
            raise ChannelError(errmsg)

        # Do we have a way to reconstruct this image from a future?
        info = self.image_index[imname]
        if info.image_future is not None:
            self.logger.info("Image '%s' is no longer in memory; attempting "
                             "image future" % (imname))

            # TODO: recode this--it's a bit messy
            def _switch(image):
                # this will be executed in the gui thread
                self.add_image(image, silent=True)
                self.switch_image(image)

                # reset modified timestamp
                info.time_modified = None
                self.fv.make_async_gui_callback('add-image-info', self, info)

            def _load_n_switch(imname, path, image_future):
                # this will be executed in a non-gui thread
                # reconstitute the image
                image = self.fv.error_wrap(image_future.thaw)
                if isinstance(image, Exception):
                    errmsg = "Error reconstituting image: %s" % (str(image))
                    self.logger.error(errmsg)
                    raise image

                # perpetuate the image_future
                image.set(image_future=image_future, name=imname, path=path)

                self.fv.gui_do(_switch, image)

            self.fv.nongui_do(_load_n_switch, imname, info.path,
                              info.image_future)

        elif info.path is not None:
            # Do we have a path? We can try to reload it
            self.logger.debug("Image '%s' is no longer in memory; attempting "
                              "to load from %s" % (imname, info.path))

            #self.fv.load_file(path, chname=chname)
            self.fv.nongui_do(self.load_file, info.path, chname=self.name)

        else:
            raise ChannelError("No way to recreate image '%s'" % (imname))

    def _configure_sort(self):
        self.hist_sort = lambda info: info.time_added
        # set sorting function
        sort_order = self.settings.get('sort_order', 'loadtime')
        if sort_order == 'alpha':
            # sort history alphabetically
            self.hist_sort = lambda info: info.name

    def _sort_changed_ext_cb(self, setting, value):
        self._configure_sort()

        self.history.sort(key=self.hist_sort)

    def __len__(self):
        return len(self.history)

    def __contains__(self, imname):
        return imname in self.image_index

    def __getitem__(self, imname):
        return self.image_index[imname]

# END
