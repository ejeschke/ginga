#
# grc.py -- Ginga Remote Control module
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading
from io import BytesIO

import ginga.util.six as six
from ginga.util.six.moves import map, zip
from ginga.misc import Task, log

if six.PY2:
    import xmlrpclib
    import SimpleXMLRPCServer
else:
    import xmlrpc.client as xmlrpclib
    import xmlrpc.server as SimpleXMLRPCServer

# undefined passed value--for a data type that cannot be converted
undefined = '#UNDEFINED'


class _ginga_proxy(object):

    def __init__(self, client):
        self._client = client
        self._fn = client.lookup_attr('ginga')

    def __getattr__(self, name):
        def _call(*args, **kwdargs):
            return self._fn(name, *args, **kwdargs)
        return _call


class _canvas_proxy(object):
    """ Links to the canvas method in ginga.rv.plugins.RC.GingaWrapper
    User has to be savvy on the objects that can be passed through
    the XMLRPC service (e.g. lists, not arrays)
    """

    def __init__(self, client, chname):
        self._client = client
        self._chname = chname
        self._fn = client.lookup_attr('canvas')

    def __getattr__(self, command):
        def _call(*args, **kwdargs):
            return self._fn(self._chname, command, *args, **kwdargs)
        return _call


class _channel_proxy(object):

    def __init__(self, client, chname):
        self._client = client
        self._chname = chname
        self._fn = client.lookup_attr('channel')

    def __getattr__(self, name):
        def _call(*args, **kwdargs):
            return self._fn(self._chname, name, *args, **kwdargs)
        return _call

    def load_np(self, imname, data_np, imtype, header):
        """Display a numpy image buffer in a remote Ginga reference viewer.

        Parameters
        ----------
        imname : str
            A name to use for the image in the reference viewer.

        data_np : ndarray
            This should be at least a 2D Numpy array.

        imtype : str
            Image type--currently ignored.

        header : dict
            Fits header as a dictionary, or other keyword metadata.

        Returns
        -------
        0

        Notes
        -----
        * The "RC" plugin needs to be started in the viewer for this to work.
        """
        # future: handle imtype

        load_buffer = self._client.lookup_attr('load_buffer')

        return load_buffer(imname, self._chname,
                           Blob(data_np.tobytes()),
                           data_np.shape, str(data_np.dtype),
                           header, {}, False)

    def load_hdu(self, imname, hdulist, num_hdu):
        """Display an astropy.io.fits HDU in a remote Ginga reference viewer.

        Parameters
        ----------
        imname : str
            A name to use for the image in the reference viewer.

        hdulist : `~astropy.io.fits.HDUList`
            This should be a valid HDUList loaded via the `astropy.io.fits` module.

        num_hdu : int or 2-tuple
            Number or key of the HDU to open from the `HDUList`.

        Returns
        -------
        0

        Notes
        -----
        * The "RC" plugin needs to be started in the viewer for this to work.
        """
        buf_io = BytesIO()
        hdulist.writeto(buf_io)

        load_fits_buffer = self._client.lookup_attr('load_fits_buffer')

        return load_fits_buffer(imname, self._chname,
                                Blob(buf_io.getvalue()),
                                num_hdu, {})

    def load_fitsbuf(self, imname, fitsbuf, num_hdu):
        """Display a FITS file buffer in a remote Ginga reference viewer.

        Parameters
        ----------
        imname : str
            A name to use for the image in the reference viewer.

        chname : str
            Name of a channel in which to load the image.

        fitsbuf : str
            This should be a valid FITS file, read in as a complete buffer.

        num_hdu : int or 2-tuple
            Number or key of the HDU to open from the buffer.

        Returns
        -------
        0

        Notes
        -----
        * The "RC" plugin needs to be started in the viewer for this to work.
        """
        load_fits_buffer = self._client_.lookup_attr('load_fits_buffer')

        return load_fits_buffer(imname, self._chname,
                                Blob(fitsbuf),
                                num_hdu, {})


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

    def shell(self):
        return _ginga_proxy(self)

    def channel(self, chname):
        return _channel_proxy(self, chname)

    def canvas(self, chname):
        return _canvas_proxy(self, chname)

    def lookup_attr(self, method_name):
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
            return marshall(res)

        raise AttributeError("No such method: '%s'" % (method_name))


# List of XML-RPC types
base_types = [str, int, float, bool]
compound_types = [list, tuple, dict]


class Blob(object):
    """A class used to wrap objects like buffers and so on in a way that
    can be recognized in both python 2 and 3 during marshalling and
    unmarshalling.
    """
    def __init__(self, buf):
        self.buf = buf


def marshall(obj):
    typ = type(obj)

    # take care of compound types
    if isinstance(obj, list):
        return list(map(marshall, obj))
    if isinstance(obj, tuple):
        return tuple(map(marshall, obj))
    if isinstance(obj, dict):
        return dict(zip(obj.keys(), map(marshall, obj.values())))

    # check if object is a large binary object
    if isinstance(obj, Blob):
        return xmlrpclib.Binary(obj.buf)

    if typ not in base_types:
        obj = undefined

    return obj


def unmarshall(obj):

    # take care of compound types
    if isinstance(obj, list):
        return list(map(unmarshall, obj))
    if isinstance(obj, tuple):
        return tuple(map(unmarshall, obj))
    if isinstance(obj, dict):
        return dict(zip(obj.keys(), map(unmarshall, obj.values())))

    if isinstance(obj, xmlrpclib.Binary):
        obj = obj.data

    return obj


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


def get_exitcode_stdout_stderr(cmd):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """
    from subprocess import Popen, PIPE
    import shlex
    args = shlex.split(cmd)

    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode

    return exitcode, out, err


#END
