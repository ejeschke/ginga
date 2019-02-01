#
# Callback.py -- Mixin class for programmed callbacks.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import traceback


class CallbackError(Exception):
    pass


class Callbacks(object):

    def __init__(self):
        self.cb = {}
        self._cb_block = {}

    # TODO: This should raise KeyError or simply do nothing if unknown key
    # passed
    def clear_callback(self, name):
        try:
            self.cb[name][:] = []
        except KeyError:
            self.cb[name] = []
        self._cb_block[name] = dict(count=0, defer_list=[], defer_type=None)

    # TODO: Should this call clear_callback()? Should create empty list here
    # only
    def enable_callback(self, name):
        if not self.has_callback(name):
            self.clear_callback(name)

    def has_callback(self, name):
        return name in self.cb

    def num_callbacks(self, name):
        return len(self.cb[name])

    def will_callback(self, name):
        return self.has_callback(name) and self.num_callbacks(name) > 0

    def delete_callback(self, name):
        try:
            del self.cb[name]

            if name in self._cb_block:
                del self._cb_block[name]
        except KeyError:
            raise CallbackError("No callback category of '%s'" % (
                name))

    def block_callback(self, name):
        self._cb_block[name]['count'] += 1

    def unblock_callback(self, name):
        self._cb_block[name]['count'] -= 1

    def suppress_callback(self, name, defer_type=None):
        return SuppressCallback(self, name, defer_type=defer_type)

    # TODO: Add a argument validation function for a callback
    # Pointers:
    #      * Check the name of the event for which callback added
    #      * Check that fn is a function
    #      * Check fn accepts at least one argument, the calling object
    #      * Check fn takes:
    #           - at least len(args) + len(kwargs) number of args
    #           - variable number of args or keyword args
    #      * Does and what value the callback function return
    #
    def add_callback(self, name, fn, *args, **kwargs):
        try:
            tup = (fn, args, kwargs)
            if tup not in self.cb[name]:
                self.cb[name].append(tup)
        except KeyError:
            raise CallbackError("No callback category of '%s'" % (
                name))

    def remove_callback(self, name, fn, *args, **kwargs):
        """Remove a specific callback that was added.
        """
        try:
            tup = (fn, args, kwargs)
            if tup in self.cb[name]:
                self.cb[name].remove(tup)
        except KeyError:
            raise CallbackError("No callback category of '%s'" % (
                name))

    def merge_callbacks_to(self, other):
        for name, cb_tups in self.cb.items():
            for tup in cb_tups:
                if tup not in other.cb[name]:
                    other.cb[name].append(tup)

    # TODO: to be deprecated ?
    def set_callback(self, name, fn, *args, **kwargs):
        if not self.has_callback(name):
            self.enable_callback(name)
        return self.add_callback(name, fn, *args, **kwargs)

    # TODO: Returns True even if any one of the callback succeeds...Is that
    # desired?
    def make_callback(self, name, *args, **kwargs):
        if not self.has_callback(name):
            return None
            # raise CallbackError("No callback category of '%s'" % (
            #                       name))

        # might save some slow code setting up for iteration/blocks
        if len(self.cb[name]) == 0:
            return False

        if self._cb_block[name]['count'] > 0:
            # callback temporarily blocked
            d = self._cb_block[name]
            defer_list = d['defer_list']
            defer_type = d['defer_type']
            if defer_type == 'all':
                # defer every suppressed call
                defer_list.append((name, args, kwargs))
            elif defer_type == 'last':
                # suppress all calls except last
                defer_list[:] = [(name, args, kwargs)]
            return False

        return self._do_callbacks(name, args, kwargs)

    def do_suppressed_callbacks(self, name):
        if self._cb_block[name]['count'] == 0:
            d = self._cb_block[name]
            defer_list = d['defer_list']
            d['defer_list'] = []
            d['defer_type'] = None

            for tup in defer_list:
                self._do_callbacks(*tup)

    def _do_callbacks(self, name, args, kwargs):
        result = False
        for tup in self.cb[name]:
            method = tup[0]
            # Extend callback args and keyword args by saved parameters
            cb_args = [self]
            cb_args.extend(args)
            cb_args.extend(tup[1])
            cb_kwargs = kwargs.copy()
            cb_kwargs.update(tup[2])

            try:
                # print("calling %s(%s, %s)" % (method, cb_args, cb_kwargs))
                res = method(*cb_args, **cb_kwargs)
                if res:
                    result = True

            except Exception as e:
                # Catch exception because we need to iterate to the other
                # callbacks
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "\n".join(traceback.format_tb(tb))

                except Exception:
                    tb_str = "Traceback information unavailable."

                if hasattr(self, 'logger'):
                    self.logger.error("Error making callback '%s': %s" % (
                        name, str(e)))
                    self.logger.error("Traceback:\n%s" % (tb_str))
                else:
                    print("Error making callback '%s': %s" % (
                        name, str(e)))
                    print("Traceback:\n%s" % (tb_str))

        return result

    # this can be overridden by a mixin
    make_ui_callback = make_callback


class SuppressCallback(object):
    def __init__(self, cb_obj, cb_name, defer_type=None):
        self.cb_obj = cb_obj
        self.cb_name = cb_name
        self.defer_type = defer_type

    def __enter__(self):
        try:
            d = self.cb_obj._cb_block[self.cb_name]
            d['count'] += 1
            d['defer_type'] = self.defer_type
        except KeyError:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            d = self.cb_obj._cb_block[self.cb_name]
            d['count'] -= 1

            self.cb_obj.do_suppressed_callbacks(self.cb_name)
        except KeyError:
            pass
        return False


# END
