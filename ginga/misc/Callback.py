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
        self._cb_block[name] = []

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
        self._cb_block[name].append(True)

    def unblock_callback(self, name):
        self._cb_block[name].pop()

    def suppress_callback(self, name):
        return SuppressCallback(self, name)

    # TODO: Add a argument validation function for a callback
    # Pointers:
    #      * Check the name of the event for which callback added
    #      * Check that fn is a function
    #      * Check fn accepts at least one argument, the calling object
    #      * Check fn takes:
    #           - at least len(args) + len(kwdargs) number of args
    #           - variable number of args or keyword args
    #      * Does and what value the callback function return
    #
    def add_callback(self, name, fn, *args, **kwdargs):
        try:
            tup = (fn, args, kwdargs)
            if tup not in self.cb[name]:
                self.cb[name].append(tup)
        except KeyError:
            raise CallbackError("No callback category of '%s'" % (
                name))

    def remove_callback(self, name, fn, *args, **kwdargs):
        """Remove a specific callback that was added.
        """
        try:
            tup = (fn, args, kwdargs)
            if tup in self.cb[name]:
                self.cb[name].remove(tup)
        except KeyError:
            raise CallbackError("No callback category of '%s'" % (
                name))

    # TODO: to be deprecated ?
    def set_callback(self, name, fn, *args, **kwdargs):
        if not self.has_callback(name):
            self.enable_callback(name)
        return self.add_callback(name, fn, *args, **kwdargs)

    # TODO: Returns True even if any one of the callback succeeds...Is that
    # desired?
    def make_callback(self, name, *args, **kwdargs):
        if not self.has_callback(name):
            return None
            # raise CallbackError("No callback category of '%s'" % (
            #                       name))

        # might save some slow code setting up for iteration/blocks
        if len(self.cb[name]) == 0:
            return False

        if (name in self._cb_block) and (len(self._cb_block[name]) > 0):
            # callback temporarily blocked
            return False

        result = False
        for tup in self.cb[name]:
            method = tup[0]
            # Extend callback args and keyword args by saved parameters
            cb_args = [self]
            cb_args.extend(args)
            cb_args.extend(tup[1])
            cb_kwdargs = kwdargs.copy()
            cb_kwdargs.update(tup[2])

            try:
                # print "calling %s(%s, %s)" % (method, cb_args, cb_kwdargs)
                res = method(*cb_args, **cb_kwdargs)
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
    def __init__(self, cb_obj, cb_name):
        self.cb_obj = cb_obj
        self.cb_name = cb_name

    def __enter__(self):
        self.cb_obj._cb_block[self.cb_name].append(True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cb_obj._cb_block[self.cb_name].pop()
        return False


# END
