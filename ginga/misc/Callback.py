#
# Callback.py -- Mixin class for programmed callbacks.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, traceback

class CallbackError(Exception):
    pass

class Callbacks(object):

    def __init__(self):
        self.cb = {}

    def clear_callback(self, name):
        self.cb[name] = []

    def enable_callback(self, name):
        if not self.has_callback(name):
            self.clear_callback(name)

    def has_callback(self, name):
        #return self.cb.has_key(name) and (len(self.cb[name]) > 0)
        return name in self.cb

    def delete_callback(self, name):
        del self.cb[name]

    def add_callback(self, name, fn, *args, **kwdargs):
        try:
            tup = (fn, args, kwdargs)
            if not tup in self.cb[name]:
                self.cb[name].append(tup)
        except KeyError:
            raise CallbackError("No callback category of '%s'" % (
                name))

    # TODO: to be deprecated ?
    def set_callback(self, name, fn, *args, **kwdargs):
        if not self.has_callback(name):
            self.enable_callback(name)
        return self.add_callback(name, fn, *args, **kwdargs)

    def make_callback(self, name, *args, **kwdargs):
        if not self.has_callback(name):
            return None
            ## raise CallbackError("No callback category of '%s'" % (
            ##     name))

        # might save some slow code setting up for iteration/blocks
        if len(self.cb[name]) == 0:
            #print "no callbacks registered for '%s'" % (name)
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
                #print "calling %s(%s, %s)" % (method, cb_args, cb_kwdargs)
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

        return result

#END
