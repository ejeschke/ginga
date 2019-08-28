#
# io_base.py -- Base class for I/O handling.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import logging


__all__ = ['BaseIOHandler']


class BaseIOHandler(object):

    # a short string that identifies this kind of opener
    # subclass should override this
    name = 'baseiohandler'

    def __init__(self, logger):
        super(BaseIOHandler, self).__init__()

        # we need a valid logger.  If one is not provided, make a
        # null logger
        if logger is None:
            logger = logging.getLogger('io_base')
            logger.addHandler(logging.NullHandler())

        self.logger = logger

    def load_file(self, filepath, idx=None, **kwargs):
        """
        Load a single data object from a file.

        Parameters
        ----------
        idx : :py:Object
            A Python value that matches describes the path or index to a
            single data data object in the file

        kwargs : optional keyword arguments
            Any optional keyword arguments are passed to the code that
            loads the data from the file

        Returns
        -------
        data_obj : subclass of `~ginga.BaseImage.ViewerObjectBase`
            A supported data wrapper object for a Ginga viewer
        """
        raise NotImplementedError("subclass should override this")

    def open_file(self, filespec, **kwargs):
        raise NotImplementedError("subclass should override this")
        # subclass should return self

    def close(self):
        raise NotImplementedError("subclass should override this")

    def __len__(self):
        raise NotImplementedError("subclass should override this")

    def __enter__(self):
        # subclass should override as needed
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # subclass should override as needed
        self.close()
        return False

    def load_idx(self, idx, **kwargs):
        """
        Parameters
        ----------
        idx : :py:class:object or None
            A Python value that matches describes the path or index to a
            single data data object in the file.  Can be None to indicate
            opening the default (or first usable) object. Acceptable formats
            are defined by the subclass.

        kwargs : optional keyword arguments
            Any optional keyword arguments are passed to the code that
            loads the data from the file

        Returns
        -------
        data_obj : subclass of `~ginga.BaseImage.ViewerObjectBase`
            A supported data wrapper object for a Ginga viewer
        """
        raise NotImplementedError("subclass should override this")

    def load_idx_cont(self, idx_spec, loader_cont_fn, **kwargs):
        # subclass can inherit this if open_file(), __len__(), load_idx() and
        # get_matching_indexes() methods are implemented properly
        """
        Parameters
        ----------
        idx_spec : str
            A string in the form of a pair of brackets enclosing some
            index expression matching data objects in the file

        loader_cont_fn : func (data_obj) -> None
            A loader continuation function that takes a data object
            generated from loading an HDU and does something with it

        kwargs : optional keyword arguments
            Any optional keyword arguments are passed to the code that
            loads the data from the file
        """
        if len(self) == 0:
            raise ValueError("Please call open_file() first!")

        idx_lst = list(self.get_matching_indexes(idx_spec))
        if len(idx_lst) == 0:
            raise ValueError("Spec {} matches no data objects in file".format(idx_spec))

        for idx in idx_lst:
            try:
                dst_obj = self.load_idx(idx, **kwargs)

                loader_cont_fn(dst_obj)

            except Exception as e:
                self.logger.error("Error loading index '{}': {}".format(idx, str(e)))

    def get_matching_indexes(self, idx_spec):
        """
        Parameters
        ----------
        idx_spec : str or None
            A string in the form of a pair of brackets enclosing some
            index expression matching data objects in the file

        Returns
        -------
        result : iterable
            An iterable of indexes that can be used to access each data object
            matching the pattern. Should contain one index if the
            `idx_spec` was empty or None (some default) or an empty sequence
            if no indexes could be found matching the pattern.
        """
        raise NotImplementedError("subclass should override this")

    def get_directory(self):
        """
        Returns
        -------
        db_dct : dict-like
            A mapping of indexes to Bunches that contain information
            about the data objects to which they map
        """
        raise NotImplementedError("subclass should override this")

    def get_info_idx(self, idx):
        """
        Parameters
        ----------
        idx : :py:class:object
            A Python value that matches describes the path or index to a
            single data data object in the file. Acceptable formats
            are defined by the subclass.

        Returns
        -------
        info_dct : dict-like
            A Bunch that contains attributes about the data objects to
            which this index maps.
        """
        raise NotImplementedError("subclass should override this")

    # subclass should only implement this if it can produce an RGBImage
    # representing the data object at the correct thumb size

    ## def get_thumb(self, filepath):
    ##     pass
