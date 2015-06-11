#
# grc.py -- Ginga Remote Control module
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading

import ginga.util.six as six
if six.PY2:
    import xmlrpclib
    import SimpleXMLRPCServer
    import cPickle as pickle
else:
    import xmlrpc.client as xmlrpclib
    import xmlrpc.server as SimpleXMLRPCServer
    import pickle
from ginga.util.six.moves import map
from ginga.misc import Task, log

# undefined passed value--for a data type that cannot be converted
undefined = '#UNDEFINED'


class RemoteClient(object):

    def __init__(self, host, port):
        self.host = host
        self.port = port

        self._proxy = None

    def __connect(self):
        # Get proxy to server
        url = "http://%s:%d" % (self.host, self.port)
        self._proxy = xmlrpclib.ServerProxy(url, allow_none=True)
        return self._proxy

    def __getattr__(self, method_name):
        def call(*args, **kwdargs):
            if self._proxy is None:
                self.__connect()

            # marshall args and kwdargs
            p_args = marshall(args)
            p_kwdargs = marshall(kwdargs)

            res = self._proxy.dispatch_call(method_name, p_args, p_kwdargs)

            return unmarshall(res)
        return call


class RemoteServer(object):

    def __init__(self, obj, host='localhost', port=9000, ev_quit=None,
                 logger=None):
        super(RemoteServer, self).__init__()

        self.robj = obj
        # What port to listen for requests
        self.port = port
        # If blank, listens on all interfaces
        self.host = host

        if logger is None:
            logger = log.get_logger(null=True)
        self.logger = logger

        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit

    def start(self, thread_pool=None):
        self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((self.host,
                                                             self.port),
                                                            allow_none=True)
        self.server.register_function(self.dispatch_call)
        if thread_pool is not None:
            t1 = Task.FuncTask2(self.monitor_shutdown)
            thread_pool.addTask(t1)
            t2 = Task.FuncTask2(self.server.serve_forever, poll_interval=0.1)
            thread_pool.addTask(t2)
        else:
            self.server.serve_forever(poll_interval=0.1)

    def stop(self):
        self.server.shutdown()

    def restart(self):
        # restart server
        self.server.shutdown()
        self.start()

    def monitor_shutdown(self):
        # the thread running this method waits until the entire viewer
        # is exiting and then shuts down the XML-RPC server which is
        # running in a different thread
        self.ev_quit.wait()
        self.server.shutdown()

    def dispatch_call(self, method_name, p_args, p_kwdargs):
        if hasattr(self.robj, method_name):
            method = getattr(self.robj, method_name)

            # unmarshall args, kwdargs
            self.logger.debug("unmarshalling params")
            args = unmarshall(p_args)
            kwdargs = unmarshall(p_kwdargs)

            self.logger.debug("calling method '%s'" % (method_name))
            res = method(*args, **kwdargs)

            self.logger.debug("marshalling return val")
            return marshall(method(*args, **kwdargs))

        raise AttributeError("No such method: '%s'" % (method_name))



# List of XML-RPC acceptable return types
ok_types = [str, int, float, bool, list, tuple, dict]

## def marshall(res):
##     """Transform results into XML-RPC friendy ones.
##     """
##     ptype = type(res)

##     if ptype in ok_types:
##         return (0, res)

##     raise ValueError("Don't know how to marshall this type of argument (%s)" % (
##         ptype))
##     ## pkl = pickle.dumps(res)
##     ## return ('pickle', pkl)


## def unmarshall(rtnval):
##     (kind, res) = rtnval

##     if kind == 0:
##         # this is a type passable by the transport
##         return res

##     raise ValueError("Don't know how to marshall this kind of argument (%s)" % (
##         kind))
##     ## if kind == 'pickle':
##     ##     return pickle.loads(res)


## def marshall(res):
##     pkl = pickle.dumps(res)
##     return ('pickle', pkl)

## def unmarshall(rtnval):
##     (kind, res) = rtnval
##     return pickle.loads(res)

def marshall(res):
    if not type(res) in ok_types:
        res = undefined
    return res

def unmarshall(rtnval):
    return rtnval

def prep_arg(arg):
    try:
        return float(arg)
    except ValueError:
        try:
            return int(arg)
        except ValueError:
            return arg

def prep_args(args):
    a, k = [], {}
    for arg in args:
        if '=' in arg:
            key, arg = arg.split('=')
            k[key] = prep_arg(arg)
        else:
            a.append(prep_arg(arg))
    return a, k
